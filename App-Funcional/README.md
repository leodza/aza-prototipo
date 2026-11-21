# AZA Analyzer — Prototipo funcional

Sistema Web de Monitoreo y Trazabilidad del Trefilado (Aceros AZA / Robotic Systems Chile).
Este prototipo **funciona de punta a punta**: captura una ráfaga, la analiza con el pipeline de
visión real, registra la inspección por API, la persiste y la publica en el tablero.

> **Estado del proyecto:** estos cambios salen de la reunión con Robotic Systems Chile.
> El despliegue en la nube queda para la etapa siguiente, una vez validada esta versión.

---

## 1. Cómo se inicia

**Opción rápida:** doble clic en `INICIAR.bat`.
Abre el navegador en <http://127.0.0.1:8000> y arranca el servidor. Para detenerlo, `Ctrl + C`.

**Opción manual:**

```powershell
cd App-Funcional
..\APP-AZA\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Usuarios de demostración

| Usuario | PIN | Rol | Ve en el menú | Puede |
|---|---|---|---|---|
| `ldaza` | `1234` | Operador | Dashboard · Histórico · Detalle · Simulador · Recetas | Ver el turno en curso y simular inspecciones |
| `jsarabia` | `1234` | Supervisor | + Auditoría | Histórico completo, auditoría |
| `dparedes` | `1234` | Administrador | + Usuarios | Todo, incluidos usuarios, recetas y materiales |
| `servicio` | `servicio` | Integrador | (sin acceso web) | Solo registrar inspecciones por API |

> El menú se arma según el rol y el servidor valida lo mismo en cada endpoint (403).
> Cinco intentos fallidos bloquean la cuenta 15 minutos.

---

## 2. Cambios incorporados en esta versión

Ajustes pedidos en la reunión con la contraparte:

| # | Cambio | Dónde se ve |
|---|---|---|
| 1 | **IDs asociados a receta y batch** en cada registro | Histórico, dashboard y detalle muestran `A-36 #1` y `L-2026-0410 · B1 #1` |
| 2 | **Orden por lote y después batch** | Selector «Ordenar por» en el histórico: `Lote → batch` (por defecto) o `Más recientes` |
| 3 | **Fecha en formato año-mes-día** | Todo el sistema usa `2026-11-17 21:22:26` |
| 4 | **Catálogo de materiales** (no solo acero) | Nueva tabla en Recetas: Acero (SAE 1010, SAE 1045, inox 304, inox 316), Cobre, Latón, Aluminio, Bronce… Cada receta se asocia a un material |
| 5 | **Velocidad del tren regulable** en el simulador | Control deslizante 4–30 m/min. Por sobre la nominal (12) el ángulo crece; por debajo, disminuye. Permite corregir la diferencia de grados |
| 6 | **Modo aleatorio** en el simulador | Tercera condición: puede salir aprobado o rechazado, sin forzar el resultado |

### Cómo se usa la velocidad (punto 5)

El simulador modela el efecto del estiramiento del material: **cada m/min sobre la velocidad
nominal de 12 m/min desplaza el ángulo ≈2,8°**.

| Velocidad | Efecto sobre el ángulo | Resultado esperado en A-36 (45°–90°) |
|---|---|---|
| 4 m/min | −22° | puede caer bajo el mínimo |
| **12 m/min** | 0° | dentro de tolerancia (centro de la receta) |
| 20 m/min | +22° | cerca del máximo |
| 30 m/min | +50° | fuera de tolerancia → rechazo y alarma |

Si una pieza sale rechazada, la aplicación indica si conviene **acelerar o desacelerar** para
volver al rango: es exactamente la corrección que se hace en planta.

---

## 3. Qué es real y qué es simulado

| Componente | Estado | Detalle |
|---|---|---|
| **Análisis de la imagen** | **Real** | Mismo módulo que la app de planta: `APP-AZA/src/vision/sequence_analysis.py`. Detecta frame de salida, círculo (Hough/contornos) y ángulo. 4–10 s por ráfaga. |
| **Cámara** | Simulada | 16 imágenes BMP de 640×480: 6 de fondo y 10 con la pieza y su arco brillante. |
| **Base de datos** | Simulada (local) | SQLite en `data/aza.db`. Para PostgreSQL basta cambiar `AZA_DB_URL`. |
| **Histórico inicial** | Simulado | 46 registros distribuidos en el día, marcados con origen «histórico demo». |
| **Autenticación** | Real | PIN con PBKDF2-SHA256 (200 000 iteraciones), JWT HS256 de 15 min, refresh rotatorio y bloqueo por intentos. |
| **Autorización** | Real | RBAC verificado en el servidor en cada endpoint. |
| **Gestión de usuarios** | Real | Alta, activación, desactivación y baja lógica. |
| **Materiales y recetas** | Real | Catálogo de familias/tipos y recetas asociadas a un material. |
| **Auditoría** | Real | Cada alta, cambio, baja o inicio de sesión queda registrado. |
| **Correo de alertas** | No implementado | La alarma se registra; el envío de correo queda para el despliegue. |

---

## 4. Recorrido sugerido para la presentación (5 minutos)

1. **Login** como `ldaza` (operador): el menú es más corto.
2. **Simulador** con velocidad **12 m/min** y condición **Normal** → ráfaga aprobada.
   Explicar: *«está generando las 16 imágenes y ejecutando el mismo algoritmo de visión de la planta»*.
3. Subir la velocidad a **28 m/min** y repetir con condición **Aleatorio**: el ángulo se desplaza y
   el resultado puede salir rechazado, con el consejo de corregir la velocidad.
4. **Dashboard**: el registro aparece con su receta `#1` y su lote/batch.
5. **Detalle**: imagen del diagnóstico, trazabilidad técnica y velocidad/desviación del proceso.
6. **Histórico**: cambiar el orden a «Más recientes» y volver a «Lote → batch»; exportar el CSV.
7. **Recetas** (como `dparedes`): mostrar el **catálogo de materiales** y crear una receta nueva
   eligiendo un material distinto del acero (por ejemplo Cobre o Aluminio).
8. **Auditoría**: se ven los inicios de sesión y cada cambio.

---

## 5. API implementada

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/api/auth/login` | público | Devuelve access + refresh |
| POST | `/api/auth/refresh` | público | Rota el token de refresco |
| POST | `/api/auth/logout` | autenticado | Revoca la sesión |
| GET | `/api/health` | público | Estado, registros y motor de visión |
| GET | `/api/dashboard` | operador+ | KPI, última inspección y tendencia |
| GET | `/api/inspecciones` | operador+ | Filtros, paginación y `orden=lote\|fecha` |
| GET | `/api/inspecciones/{id}` | operador+ | Detalle con trazabilidad técnica |
| GET | `/api/inspecciones/{id}/imagen` | autenticado | PNG del diagnóstico |
| POST | `/api/inspecciones` | **integrador** | Registro desde el sistema de visión |
| POST | `/api/simular` | operador+ | `receta_id`, `velocidad` (4–30), `modo` (dentro/fuera/aleatorio) |
| GET | `/api/materiales` | operador+ | Catálogo de familias y tipos |
| POST | `/api/materiales` | administrador | Agregar material |
| GET/POST | `/api/recetas` | lectura: operador+ · alta: admin | Recetas con `material_id` |
| GET | `/api/lotes` | operador+ | Lotes con sus batches e IDs |
| GET | `/api/usuarios` | administrador | Listado de cuentas |
| POST | `/api/usuarios` | administrador | Crear cuenta con rol y PIN |
| PATCH | `/api/usuarios/{id}` | administrador | Activar o desactivar |
| DELETE | `/api/usuarios/{id}` | administrador | Baja lógica (conserva el historial) |
| GET | `/api/auditoria` | supervisor+ | Bitácora |

Documentación interactiva: <http://127.0.0.1:8000/docs>

---

## 6. Pruebas automatizadas

```powershell
cd App-Funcional
..\APP-AZA\.venv\Scripts\python.exe -m pytest tests -q
```

**28 pruebas**: autenticación y bloqueo, rotación/revocación de tokens, RBAC, validación de datos,
registro por API, filtros, orden lote→batch, IDs en los registros, catálogo de materiales,
receta con material, inmutabilidad de límites, velocidad que desplaza el ángulo y modos del simulador.

---

## 7. Estructura

```
App-Funcional/
├── INICIAR.bat            arranque rápido
├── REINICIAR-DATOS.bat    borra la base y vuelve a sembrar los datos de demo
├── requirements.txt
├── app/
│   ├── main.py            API REST + servidor de la interfaz
│   ├── db.py              modelo (incluye materiales y snapshots de trazabilidad)
│   ├── seguridad.py       PIN, JWT, refresh y bloqueo
│   └── simulador.py       cámara sintética, modelo de velocidad y pipeline real
├── web/                   interfaz (HTML + CSS + JS, sin compilación)
├── tests/test_api.py
├── evidencias/            capturas reales del sistema en ejecución
└── data/                  base SQLite y carpetas de ráfagas
```

---

## 8. Despliegue en la nube (AWS)

El sistema completo —**PostgreSQL + MinIO + la aplicación**— cabe en un solo servidor con
Docker. El detalle, los costos y el paso a paso están en **[GUIA-AWS.md](GUIA-AWS.md)**.

| Pieza | Archivo | Qué hace |
|---|---|---|
| Imagen de la app | `Dockerfile` | Python 3.12 + OpenCV + el pipeline de visión incluido |
| Orquestación | `docker-compose.yml` | PostgreSQL 16, S3, pgweb y la app |
| Secretos | `.env.example` | Claves que hay que cambiar antes de publicar |
| Almacenamiento | `app/almacenamiento.py` | Sube las ráfagas a S3/MinIO (o disco local) |
| Pipeline | `vision_aza/` | Copia del algoritmo de visión para que el contenedor sea autocontenido |
| Despliegue | `deploy/desplegar_aws.py` | Crea llave, security group e instancia; inventario y estado |

### Estado del despliegue (21-11-2026)

| Elemento | Valor |
|---|---|
| Instancia | `i-0c419b17a438a912c` · t3.micro · Ubuntu 24.04 · us-east-1 |
| IP pública | **http://13.223.49.56:8000** |
| Base de datos | PostgreSQL 16 en contenedor (`aza-db`), 10 tablas |
| Objetos | Bucket **S3** `aza-capturas-166178700885` (18 objetos por ráfaga) |
| Explorador de BD | http://13.223.49.56:8081 (pgweb) |
| Llave SSH | `deploy/aza-llave.pem` |

> **Nota sobre MinIO:** MinIO dejó de publicar binarios e imágenes comunitarias
> (solo distribuye AIStor, que exige licencia comercial; `minio/minio` ya no existe
> en Docker Hub). Se usa el **S3 nativo de AWS**, que habla el mismo protocolo:
> el código no cambió y sigue siendo compatible con MinIO. Para apuntar a un MinIO
> propio basta con definir `AZA_S3_ENDPOINT=http://host:9000`.

Se levanta con:

```bash
cp .env.example .env && nano .env      # cambiar claves
docker compose up -d --build
```

**Costo estimado: USD 7/mes** (Lightsail 2 GB) o USD 12–14 (EC2 t4g.small).
En el laboratorio de AWS Academy se paga con los créditos del curso.
Ver la comparación completa en la guía.

### Cambiar entre local y nube

| Variable | Local | Nube |
|---|---|---|
| `AZA_DB_URL` | `sqlite:///data/aza.db` | `postgresql+psycopg://usuario:clave@db:5432/aza` |
| `AZA_ALMACEN` | `local` | `s3` |
| `AZA_S3_ENDPOINT` | (vacío) | vacío = S3 de AWS · `http://minio:9000` = MinIO |

El código no cambia: solo el archivo de configuración.

---

## 9. Límites conocidos (para declarar en la presentación)

- La base es SQLite local: sirve para la demostración, no para concurrencia real.
- El envío de correos de alerta no está implementado; la alarma sí queda registrada.
- El histórico inicial son datos simulados; solo las ráfagas disparadas desde el simulador
  tienen imagen y medición real.
- No hay HTTPS: el servidor escucha solo en `127.0.0.1`.
- El pipeline puede no encontrar señal si el arco cae justo sobre los 90°; en ese caso el
  simulador recaptura automáticamente con un pequeño ajuste.
- El modelo de velocidad es una aproximación lineal (2,8° por m/min); en planta la relación
  se calibraría con mediciones reales.

---

## 10. Control de versiones (Git)

El proyecto es un repositorio Git con **12 commits** agrupados por módulo (modelo, simulador,
API, interfaz, pruebas, despliegue, evidencias). Git quedó instalado en modo portátil y
agregado al `PATH` del usuario: `git` funciona desde cualquier terminal.

```powershell
cd "C:\Users\rootg\Desktop\Proyecto Robotic Systems Chile"
git log --oneline --graph --decorate     # historial
git status                               # qué falta por confirmar
git add . ; git commit -m "feat: ..."    # nuevo cambio
```

Excluidos por `.gitignore`: `APP-AZA/.venv/`, el ejecutable `AZA/`, `App-Funcional/data/`,
las claves `*.pem` y los archivos `.env`.

Evidencia del historial: `evidencias/27_git_commits.png`.

> Repositorio en línea: **<https://github.com/leodza/aza-prototipo>**
> (acceso por *deploy key* `notebook-leo` con permiso de escritura, solo para este repositorio).
> Para publicar cambios: `git push origin main`.

---

## 11. Ver la base de datos en vivo

| Acceso | URL / comando | Usuario | Clave |
|---|---|---|---|
| **Explorador web** (pgweb) | <http://13.223.49.56:8081> | `aza` | `AzaLab2026Db` |
| App | <http://13.223.49.56:8000> | `jsarabia` | PIN `1234` |
| PostgreSQL por terminal | ver túnel abajo | `aza` | `AzaLab2026Pg` |

En pgweb: la barra izquierda lista las 10 tablas (al hacer clic se ven las filas) y la
pestaña **Query** permite escribir SQL y ejecutarlo con **Run Query**.

### Consultas de prueba

**1. Cuántos registros hay en cada tabla**

```sql
SELECT 'usuarios' AS tabla, count(*) FROM usuarios
UNION ALL SELECT 'materiales', count(*) FROM materiales
UNION ALL SELECT 'recetas', count(*) FROM recetas
UNION ALL SELECT 'lotes', count(*) FROM lotes
UNION ALL SELECT 'batches', count(*) FROM batches
UNION ALL SELECT 'inspecciones', count(*) FROM inspecciones
UNION ALL SELECT 'auditoria', count(*) FROM auditoria;
```

**2. Últimas inspecciones con su receta, lote y objeto en S3**

```sql
SELECT i.id, i.fecha_hora, r.nombre AS receta, l.codigo AS lote, b.numero AS batch,
       i.material, i.angulo, i.estado, i.imagen_clave
FROM inspecciones i
LEFT JOIN recetas r ON r.id = i.receta_id
LEFT JOIN lotes   l ON l.id = i.lote_id
LEFT JOIN batches b ON b.id = i.batch_id
ORDER BY i.id DESC LIMIT 10;
```

**3. Porcentaje de aprobación por receta**

```sql
SELECT r.nombre, count(*) AS total,
       count(*) FILTER (WHERE i.estado = 'aprobado') AS aprobadas,
       round(100.0 * count(*) FILTER (WHERE i.estado = 'aprobado') / count(*), 1) AS pct
FROM inspecciones i JOIN recetas r ON r.id = i.receta_id
GROUP BY r.nombre ORDER BY total DESC;
```

**4. Insertar una inspección a mano (y verla aparecer en la app)**

```sql
INSERT INTO inspecciones (fecha_hora, receta_id, lote_id, batch_id, angulo,
                          limite_min, limite_max, estado, origen, material)
VALUES (now(), 1, 1, 1, 72.5, 45, 90, 'aprobado', 'prueba_manual', 'Acero SAE 1010')
RETURNING id, angulo, estado;
```

**5. Borrar la prueba**

```sql
DELETE FROM inspecciones WHERE origen = 'prueba_manual';
```

> ⚠️ Es la base real: un `DELETE` o `DROP` se ejecuta de inmediato. Para experimentar
> sin riesgo, usar `BEGIN; … ROLLBACK;`.

### Por terminal (psql)

```powershell
# 1) abrir el túnel (dejar esta ventana abierta)
ssh -i "deploy\aza-llave.pem" -N -L 5432:127.0.0.1:5432 ubuntu@13.223.49.56

# 2) en otra terminal
$env:PGPASSWORD = "AzaLab2026Pg"
psql -h 127.0.0.1 -U aza -d aza
```

Dentro de psql: `\dt` (tablas), `\d inspecciones` (estructura), `\x` (vista vertical).
