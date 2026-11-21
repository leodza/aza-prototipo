# Montar el prototipo en AWS (PostgreSQL + MinIO)

**Respuesta corta: sí, es posible, y sale barato.** Todo el sistema cabe en **un solo
servidor** con Docker: PostgreSQL + MinIO + la aplicación + un explorador de base de datos
para las evidencias. No se necesita RDS ni nada administrado.

> Los precios son referenciales (región `us-east-1`, tarifa bajo demanda). Conviene
> confirmarlos en la calculadora de AWS antes de contratar, porque cambian con el tiempo
> y con el tipo de cambio.

---

## 1. Comparación de opciones

| Opción | Qué incluye | Costo mensual aprox. | Cuándo conviene |
|---|---|---|---|
| **A. Lightsail 2 GB** ⭐ recomendada | 2 vCPU, 2 GB RAM, 60 GB SSD, 3 TB de transferencia. Precio fijo. | **USD 7** | Es la más barata y la más simple: factura predecible y todo en una máquina |
| **B. EC2 t4g.small** | 2 vCPU ARM, 2 GB RAM + 20 GB EBS gp3 | **USD 12 – 14** (puede ser USD 0 el primer año si la cuenta entra en la capa gratuita) | Si el curso exige usar la consola de EC2 con grupos de seguridad |
| **C. RDS + S3 + EC2** | Base administrada + almacenamiento S3 + app | **USD 22 – 28** | Si pidieran servicios administrados; es la más cara y no aporta nada nuevo aquí |

**Recomendación:** Opción A. Con 2 GB de RAM corren los cuatro contenedores sin problema
(la app usa ~250 MB, PostgreSQL ~150 MB y MinIO ~120 MB).

### ¿Y si en vez de MinIO usamos S3?

Técnicamente es un cambio de una variable (`AZA_S3_ENDPOINT` vacío). S3 cuesta
**USD 0,023 por GB/mes**: con 10 GB de imágenes son ~USD 0,23 al mes. Pero el diseño del
informe ES2 especifica **MinIO**, y dentro del mismo servidor no cuesta nada extra.
Se puede dejar MinIO para la entrega y migrar a S3 después sin tocar código.

### Costos que conviene vigilar

| Concepto | Detalle | Costo |
|---|---|---|
| Transferencia de salida | 100 GB/mes gratis, luego ~USD 0,09/GB | Normalmente USD 0 |
| IP elástica (EC2) | Gratis mientras esté asociada a una instancia encendida | USD 0 |
| Snapshots / respaldos | Lightsail: 7 días automáticos incluidos | USD 0 |
| Dominio + HTTPS | Opcional; con un dominio propio, el certificado es gratis (Let's Encrypt) | ~USD 10/año el dominio |

---

## 2. Arquitectura del despliegue

```
                    ┌──────────────────────── Servidor (Lightsail / EC2) ──────────────────────┐
   Internet  ──────▶│  :8000  app (FastAPI + interfaz)   ─┐                                  │
   (operadores)     │                                     │ SQLAlchemy                       │
                    │  :8081  pgweb (evidencia de la BD)  │                                  │
                    │                                     ▼                                  │
                    │                            :5432  PostgreSQL 16   ◀── usuarios, lotes, │
                    │                                       materiales, inspecciones, auditoría│
                    │                                     ▲                                  │
                    │  :9001  consola MinIO               │ boto3 (S3)                       │
                    │                            :9000  MinIO  ◀── imágenes de ráfaga (.bmp,  │
                    └───────────────────────────────────────┼──────── resultado_analisis.png) ─┘
                                                            │
                                                    Volumen Docker (persistente)
```

- **PostgreSQL** = base estructurada (lo que el profesor pidió: usuarios, lotes, materiales…).
- **MinIO** = base no estructurada (las imágenes de cada ráfaga + el diagnóstico).
- La aplicación guarda en PostgreSQL **solo la clave** del objeto; el archivo vive en MinIO.

---

## 3. Despliegue paso a paso (Opción A: Lightsail)

### 3.1 Crear la instancia

1. Entrar a <https://lightsail.aws.amazon.com> → *Create instance*.
2. Región: **us-east-1** (o la más cercana) · Plataforma **Linux/Unix** · Blueprint **Ubuntu 24.04**.
3. Plan: **USD 7** (2 GB RAM).
4. Nombre: `aza-prototipo`. Crear.

### 3.2 Abrir los puertos

En *Networking → IPv4 Firewall* agregar:

| Aplicación | Puerto | Para qué |
|---|---|---|
| HTTP | 80 | (opcional) redirección a HTTPS |
| Custom | 8000 | interfaz y API |
| Custom | 9001 | consola MinIO (solo para la demo) |
| Custom | 8081 | pgweb (solo para evidencia) |

> Los puertos 5432 (PostgreSQL) y 9000 (API de MinIO) **no se abren**: el
> `docker-compose.yml` los deja escuchando solo en `127.0.0.1`.

### 3.3 Instalar Docker

```bash
ssh -i ~/clave.pem ubuntu@IP_DEL_SERVIDOR
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker
```

### 3.4 Subir el proyecto

Desde el computador local:

```bash
scp -i ~/clave.pem -r App-Funcional ubuntu@IP_DEL_SERVIDOR:/home/ubuntu/
```

O bien, si se sube a GitHub (recomendado para tener los commits como evidencia):

```bash
git clone https://github.com/USUARIO/aza-prototipo.git App-Funcional
```

### 3.5 Configurar y levantar

```bash
cd App-Funcional
cp .env.example .env
nano .env        # cambiar POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD y AZA_SECRETO
docker compose up -d --build
docker compose ps
```

La primera construcción tarda unos minutos (instala OpenCV y matplotlib en la imagen).

### 3.6 Verificar

| Servicio | URL | Qué se ve |
|---|---|---|
| Aplicación | `http://IP:8000` | Login, dashboard, simulador |
| Base de datos | `http://IP:8081` | pgweb con las tablas y filas |
| Objetos | `http://IP:9001` | Consola MinIO con el bucket `aza-capturas` |

Usuarios de prueba: `ldaza` / `jsarabia` / `dparedes` con PIN `1234`
(**cambiar antes de entregar**).

---

## 4. Evidencias que pide el profesor

Con el despliegue arriba se obtienen en minutos:

1. **Base de datos con datos reales**
   - `http://IP:8081` → abrir `usuarios`, `lotes`, `batches`, `materiales`, `recetas`,
     `inspecciones`, `auditoria` y capturar cada tabla.
   - Alternativa por consola: `docker exec -it aza-db psql -U aza -d aza -c "\dt"`.

2. **Integraciones (cargas) hechas en la base**
   - Ejecutar el **simulador** varias veces y volver a pgweb: la tabla `inspecciones`
     crece y `auditoria` registra quién creó cada registro.
   - Capturar la tabla `inspecciones` ordenada por `id desc` antes y después.

3. **Objetos en MinIO**
   - `http://IP:9001` → *Buckets* → `aza-capturas` → `capturas/AAAA-MM-DD/Trigger_…`
   - Se ven las 16 imágenes BMP, `metricas.json` y `resultado_analisis.png`.

4. **Commits (Git)**
   - `git log --oneline --graph --all` o la pestaña *Commits* del repositorio en GitHub.
   - Conviene que los commits cuenten la historia: modelo de datos, API, interfaz,
     seguridad, pruebas, despliegue.

5. **Pruebas automatizadas**
   - `docker compose exec app pytest tests -q` → 28 pruebas aprobadas.

---

## 5. Endurecer antes de la entrega

- Cambiar las claves de `.env` (PostgreSQL, MinIO y `AZA_SECRETO`).
- Cambiar los PIN de demostración (`1234`) o desactivar las cuentas de prueba.
- Cerrar los puertos 8081 y 9001 en el firewall cuando ya no se necesiten.
- HTTPS: agregar un contenedor **Caddy** como proxy con dominio propio (certificado
  automático y gratis) delante de la app.
- Respaldos: `docker exec aza-db pg_dump -U aza aza > respaldo_$(date +%F).sql`
  y `mc mirror` o `rclone` para el bucket de MinIO.

---

## 6. Qué se necesita para ejecutarlo (y qué no puedo hacer yo desde aquí)

Para crear la instancia real hace falta:

1. Una **cuenta de AWS** con método de pago activo.
2. **Permiso explícito** para contratar el plan de USD 7/mes.
3. La **clave SSH** (.pem) o acceso a la consola.
4. Decidir si se usa **Lightsail** (más simple y barato) o **EC2** (si el curso lo exige).

Todo el código, la configuración y los pasos ya están listos: en cuanto haya cuenta y
clave, el despliegue son tres comandos.

---

## 7. Si MinIO diera problemas de licencia

En 2025 MinIO pasó a un modelo **AIStor** con licencia comercial para los binarios nuevos.
Por eso el `docker-compose.yml` fija la **última imagen comunitaria**:

```
minio/minio:RELEASE.2025-04-22T22-12-26Z
```

Es software libre (AGPL) y funciona sin licencia. Si en el futuro esa imagen no estuviera
disponible, hay dos alternativas que **no requieren cambiar código** (la app usa la API S3):

- **AWS S3** (administrado): vaciar `AZA_S3_ENDPOINT` y usar un rol IAM.
- **SeaweedFS**: servidor S3 compatible, binario único y open source.
