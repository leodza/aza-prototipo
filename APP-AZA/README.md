# AZA Analyzer

Sistema de inspección visual automatizada para control de calidad industrial. Analiza ángulos de piezas mediante procesamiento de imágenes (detección de círculos, clustering K-Means, detección de bordes Canny) y evalúa aprobación/rechazo comparando contra tolerancias configuradas por receta.

## Estructura del Proyecto

```
APP-AZA/
│
├── src/                          # Código fuente principal
│   ├── main.py                   # Entry point de la aplicación
│   ├── utils.py                  # Helpers compartidos (resource_path)
│   │
│   ├── core/                     # Configuración e infraestructura
│   │   ├── config.py             # DB_PATH, constantes de cámara
│   │   └── logger.py             # Configuración de logging
│   │
│   ├── database/                 # Capa de datos
│   │   ├── models.py             # Schema SQLite, migraciones
│   │   └── auth.py               # Autenticación (PBKDF2), CRUD usuarios
│   │
│   ├── vision/                   # Procesamiento de imágenes
│   │   ├── detection.py          # Detección de círculos, cálculo de ángulos, ROI
│   │   ├── pipeline.py           # Pipeline completo (Hough → K-Means → Canny)
│   │   └── industrial.py         # Lógica de aprobación/rechazo por receta
│   │
│   ├── ui/                       # Interfaz gráfica (PySide6)
│   │   ├── app.py                # Ventana principal AnalizadorApp
│   │   ├── components.py         # HMIOverlay, ResultViewer, WelcomeScreen
│   │   ├── dashboard.py          # Panel de control con gráfico de tendencias
│   │   ├── login.py              # Dialogo de login
│   │   ├── users.py              # Gestión de usuarios (CRUD, roles)
│   │   └── video.py              # Ventana de vista de cámara
│   │
│   └── workers/                  # Hilos de fondo
│       ├── camera.py             # Thread de cámara NeoAPI (continuous/trigger)
│       ├── analysis.py           # Thread de análisis de directorio
│       └── capture.py            # Manager de captura por trigger externo
│
├── tests/                        # Tests unitarios
│   ├── conftest.py               # Fixtures (DB temporal)
│   ├── test_auth.py              # Tests de autenticación
│   ├── test_analisis.py          # Tests de geometría angular
│   ├── test_database.py          # Tests de schema y migraciones
│   └── test_utils.py             # Tests de utilidades
│
├── assets/                       # Recursos estáticos
│   └── logo.png
│
├── data/                         # Datos de runtime (gitignored)
│   └── analisis_datos.db
│
├── CAPTURAS/                     # Imágenes capturadas por trigger (gitignored)
├── RESULTADO_ANALISIS/           # Resultados del pipeline (gitignored)
│
├── AZA.spec                      # Configuración PyInstaller
├── requirements.txt
├── .gitignore
└── README.md
```

## Ejecutar

### Desarrollo

```bash
# Desde el directorio APP-AZA/
python -m src.main
```

### Monitor web LAN (solo lectura)

Al iniciar sesion, la aplicacion publica una copia del monitor en:

```text
http://IP-DEL-EQUIPO:8080
```

La URL exacta se muestra en la consola y en `app.log`. El visor transmite
imagenes del monitor, pero no expone controles para operar la aplicacion.
El equipo cliente debe estar en la misma red LAN y el puerto TCP 8080 debe
estar permitido por el firewall.

Configuracion opcional mediante variables de entorno:

```bash
AZA_WEB_MONITOR=0                 # Desactivar el visor
AZA_WEB_MONITOR_PORT=8080         # Cambiar puerto
AZA_WEB_MONITOR_SCREEN=0          # Indice del monitor fisico o virtual
AZA_WEB_MONITOR_FPS=5             # Capturas por segundo (1-30)
AZA_WEB_MONITOR_JPEG_QUALITY=70   # Calidad JPEG (20-95)
```

Por ejemplo, para publicar el segundo monitor en el puerto 8090:

```bash
AZA_WEB_MONITOR_SCREEN=1 AZA_WEB_MONITOR_PORT=8090 python -m src.main
```

### Producción (PyInstaller)

```bash
pyinstaller AZA.spec
```

El ejecutable se genera en `dist/AZA/`.

## Requisitos

```
matplotlib>=3.8
numpy>=1.26
opencv-python>=4.9
scikit-learn>=1.4
PySide6>=6.6
Pillow>=10.0
```

Además se requiere la librería `neoapi` para cámaras Daheng/Baumer.

```bash
pip install -r requirements.txt
```

## Tests

```bash
python -m pytest tests/ -v
```

## Flujo de Uso

1. **Login** - El operador ingresa usuario y PIN.
2. **Seleccionar Directorio** - Define la carpeta raíz donde se guardarán los resultados.
3. **Ejecutar Análisis** - Conecta la cámara y queda esperando un flanco de subida en `Line0`.
4. Al recibir la señal, captura 100 imágenes a 100 FPS, guarda la ráfaga y ejecuta automáticamente el análisis de salida, círculo y ángulo.
5. El diagnóstico más reciente permanece visible en la pantalla hasta que termina la siguiente ráfaga.
6. **Analizar Ráfaga Guardada** - Permite seleccionar una carpeta que ya contenga imágenes `img_*.bmp`. El análisis se ejecuta sin conectar la cámara y guarda o actualiza `metricas.json` y `resultado_analisis.png` en esa carpeta.
7. **Ver Resultados** - Muestra los diagnósticos históricos ordenados por número de trigger y fecha.
8. **Descargar** - Copia el directorio completo de resultados a una carpeta seleccionada, por ejemplo una unidad USB, bajo el nombre `AZA_Resultados_YYYYMMDD_HHMMSS`.

Cada trigger genera una carpeta con este formato:

```text
DIRECTORIO_SELECCIONADO/
└── YYYY-MM-DD/
    └── Trigger_0001_YYYYMMDD_HHMMSS/
        ├── img_001.bmp
        ├── ...
        ├── img_100.bmp
        ├── metricas.json
        └── resultado_analisis.png
```

## Recetas

Las recetas se definen en la base de datos (`configuracion_recetas`) con nombre, tolerancia mínima y máxima. Se cargan dinámicamente en el combo de la interfaz. Si no hay recetas configuradas, se usan valores por defecto.

## Base de Datos

SQLite (`data/analisis_datos.db`) con tablas:
- **usuarios** — Operadores con PIN (hash PBKDF2), rol admin/operador
- **configuracion_recetas** — Tolerancias por producto
- **registros** — Historial de inspecciones (fecha, operador, receta, ángulo, estado, lote)

## Licencia

Realizado por Robotic Systems Chile | soporte@roboticsystems.cl
