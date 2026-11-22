# Sistema Web de Monitoreo y Trazabilidad del Trefilado

**Aceros AZA · Robotic Systems Chile** — Proyecto Integrado (INACAP, Santiago Centro)
Equipo: **Leonardo Daza** (Product Owner) · **José Sarabia** (Scrum Master / backend) · **Daniel Paredes** (frontend / QA)

Prototipo funcional que mide el ángulo del trefilado a partir de una ráfaga de imágenes,
evalúa la pieza contra la tolerancia de su receta y deja todo trazado por lote, batch y material.

---

## 🚀 Demo en vivo

| Servicio | URL | Acceso |
|---|---|---|
| Aplicación | <http://13.223.49.56:8000> | `ldaza` / `jsarabia` / `dparedes` · PIN `1234` |
| Base de datos (pgweb) | <http://13.223.49.56:8081> | `aza` / `AzaLab2026Db` |

> El entorno es un laboratorio de AWS Academy que se reinicia al terminar la sesión del curso.
> Para levantarlo de nuevo: ver [`App-Funcional/GUIA-AWS.md`](App-Funcional/GUIA-AWS.md).

---

## 📁 Estructura

| Carpeta | Contenido |
|---|---|
| [`App-Funcional/`](App-Funcional/) | **Prototipo funcional**: API FastAPI, interfaz web, simulador de cámara, pruebas y despliegue |
| [`APP-AZA/`](APP-AZA/) | Aplicación de planta original; de aquí proviene el pipeline de visión reutilizado |
| [`ES2-Informe/`](ES2-Informe/) | Informe ES2 (arquitectura, UML, Scrum, presupuesto) y sus diagramas |
| [`documentos/`](documentos/) | Descriptor del proyecto y material de referencia |
| `main.cpp` | Firmware del indicador físico (Arduino / NeoPixel / OLED) |

---

## ⚙️ Qué hace el prototipo

1. **Simula una ráfaga** de 16 imágenes BMP (como la cámara al recibir el trigger).
2. **Analiza** las imágenes con el mismo pipeline de visión de la planta (`sequence_analysis`).
3. **Evalúa** el ángulo contra la receta (aprobado / rechazado) y genera alarma si corresponde.
4. **Persiste** la inspección en PostgreSQL y las imágenes en un almacenamiento de objetos (S3).
5. **Trazabilidad**: cada registro guarda receta, lote, batch, material, velocidad del tren y
   la clave del objeto en el bucket.

Incluye **velocidad del tren regulable** (12 m/min nominal, 2,8° por m/min), **modo aleatorio**
y **catálogo de materiales** (acero, cobre, latón, aluminio) — los últimos ajustes pedidos
en la reunión con la contraparte.

---

## 🧪 Pruebas

```powershell
cd App-Funcional
..\APP-AZA\.venv\Scripts\python.exe -m pytest tests -q
```

**28 pruebas** aprobadas: autenticación y bloqueo, rotación de tokens, RBAC, validación,
registro por API, filtros, orden lote → batch, materiales, velocidad y modos del simulador.

---

## 🐳 Despliegue

```bash
cd App-Funcional
cp .env.example .env      # cambiar claves
docker compose up -d --build
```

PostgreSQL 16 + pgweb + la aplicación. El almacenamiento apunta a S3 (o a cualquier
servidor compatible con MinIO definiendo `AZA_S3_ENDPOINT`).

---

## 📸 Evidencias

En [`App-Funcional/evidencias/`](App-Funcional/evidencias/) hay 24 capturas reales:
interfaz en local, sistema desplegado en AWS, contenido de PostgreSQL, objetos en S3,
consultas SQL y el historial de commits.
