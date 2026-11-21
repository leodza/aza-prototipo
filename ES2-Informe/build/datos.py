"""Datos compartidos del informe ES2: equipo, cronograma, backlog, seguridad y pruebas."""

PROYECTO = "Sistema Web de Monitoreo y Trazabilidad del Trefilado"
EMPRESA = "Aceros AZA"
CONTRAPARTE = "Robotic Systems Chile"
DOCUMENTO = "ES2 — Diseño de la solución de software"
VERSION = "1.0"
FECHA = "Octubre de 2026"
ASIGNATURA = "[Nombre de la asignatura]"
DOCENTE = "[Nombre del docente]"
INSTITUCION = "[Nombre de la institución]"
SECCION = "[Sección / jornada]"

EQUIPO = [
    ("Leonardo Daza", "Product Owner · Analista de negocio y UX",
     "Dueño del backlog, levantamiento de requisitos, prototipado y validación con usuarios"),
    ("José Sarabia", "Scrum Master · Arquitecto y desarrollador backend",
     "Facilitación de ceremonias, arquitectura 4+1, modelo de datos, API y seguridad"),
    ("Daniel Paredes", "Desarrollador frontend · Responsable de calidad (QA)",
     "Interfaz React, guía visual, plan de pruebas y automatización"),
]

# --------------------------------------------------------------------------- #
# 2.1.1.1 — Metodología
# --------------------------------------------------------------------------- #
METODOLOGIAS = [
    ("Cascada (waterfall)",
     "Fases secuenciales con documentación extensa al inicio",
     "El alcance es estable y los requisitos no cambian",
     "2,60",
     "Descartada: el equipo necesita validar el diseño con usuarios reales antes de construir; los "
     "cambios de tolerancias y recetas aparecerían tarde y con costo alto"),
    ("Kanban",
     "Flujo continuo con límite de trabajo en curso y sin iteraciones cerradas",
     "Operación y soporte con demanda variable y prioridades cambiantes",
     "3,35",
     "Descartada: optimiza el flujo (Anderson, 2010), pero no impone puntos de cierre ni "
     "documentación arquitectónica, y este proyecto se evalúa en cuatro hitos con fecha fija"),
    ("RUP puro",
     "Fases Inicio, Elaboración, Construcción y Transición; artefactos UML formales",
     "Proyectos medianos o grandes con arquitectura crítica y equipo experimentado",
     "3,05",
     "Parcialmente adoptada: se conservan las vistas 4+1 de Kruchten como marco de arquitectura, "
     "pero su gestión por fases es demasiado pesada para 3 personas en un semestre"),
    ("Scrum + XP",
     "Sprints con TDD, pair programming e integración continua estricta",
     "Equipos con alta madurez técnica y requisitos muy volátiles",
     "3,10",
     "Descartada como marco principal: las prácticas de XP se usan como técnicas de apoyo, no como "
     "metodología completa, porque el equipo es de tres integrantes"),
    ("Scrum + vistas 4+1 de RUP (adoptada)",
     "Sprints de 2 a 3 semanas, backlog priorizado y revisión con el PO; la arquitectura se documenta "
     "con las cinco vistas de Kruchten",
     "Equipos pequeños, requisitos parcialmente conocidos y entregas frecuentes",
     "4,50",
     "Adoptada: combina la agilidad para iterar el diseño con un marco de arquitectura que la rúbrica "
     "exige y que permite justificar las decisiones técnicas"),
]


SPRINTS_TABLA = [
    ("Sprint 0", "10 – 21 ago 2026", "Inicio",
     "Conformar el equipo, fijar metodología y levantar actores y necesidades del proceso",
     "Acta de constitución, matriz de necesidades"),
    ("Sprint 1", "24 ago – 11 sep 2026", "Diagnóstico y arquitectura",
     "Cerrar historias de usuario, catálogo RF/RNF y trazabilidad; seleccionar el stack, construir "
     "las vistas 4+1 y validar el prototipo v1 con usuarios. (hito: entrega ES1 el 07-09-2026)",
     "Informe ES1, documento de arquitectura, prototipo v1, registro de feedback"),
    ("Sprint 2", "14 sep – 2 oct 2026", "Datos y seguridad",
     "Modelo entidad-relación, diccionario de datos, DDL, políticas de autenticación y autorización, "
     "análisis de amenazas y estándares de codificación segura",
     "DER validado, DDL ejecutable, matriz RBAC, catálogo de amenazas"),
    ("Sprint 3", "5 – 16 oct 2026", "Pruebas y entrega ES2",
     "Plan de pruebas por niveles, umbrales de rendimiento, prototipo v2 con el feedback aplicado y "
     "redacción del informe. (hito: entrega ES2 el 19-10-2026)",
     "Informe ES2, prototipo v2, plan de pruebas aprobado por el PO"),
    ("Sprint 4", "20 oct – 6 nov 2026", "Construcción",
     "Implementar backend (API REST), modelo de datos en PostgreSQL y frontend React",
     "API funcional, esquema migrado, interfaz conectada"),
    ("Sprint 5", "9 – 20 nov 2026", "Cloud y calidad",
     "Dashboard e indicadores, despliegue en el VPS con Docker, pipeline CI/CD y pruebas de "
     "integración, rendimiento y aceptación. (hito: entrega ES3 el 23-11-2026)",
     "Sistema desplegado, evidencia de pruebas, entrega ES3"),
    ("Sprint 6", "23 nov – 11 dic 2026", "Cierre",
     "Documentación final, manual de operación y mantención, ensayo y defensa del proyecto. "
     "(hito: defensa ES4 el 14-12-2026)",
     "Informe final, manual, defensa ES4"),
]


# (id, actividad, sprint, inicio, fin, responsable, entregable)
ACTIVIDADES = [
    ("A01", "Conformación del equipo y acta de constitución", "S0", "10-08", "12-08", "LD", "Acta firmada"),
    ("A02", "Definición y justificación de la metodología", "S0", "11-08", "13-08", "JS", "Sección 2.1.1 del informe"),
    ("A03", "Levantamiento de actores y necesidades", "S0", "12-08", "19-08", "LD", "Matriz de necesidades"),
    ("A04", "Historias de usuario y criterios de aceptación", "S1", "24-08", "02-09", "LD", "Backlog con 14 HU"),
    ("A05", "Catálogo RF/RNF y matriz de trazabilidad v1", "S1", "31-08", "04-09", "DP", "Catálogo RF/RNF — ES1"),
    ("A06", "Priorización del backlog con MoSCoW", "S1", "24-08", "27-08", "LD", "Backlog priorizado"),
    ("A07", "Selección y justificación del stack tecnológico", "S1", "25-08", "31-08", "JS", "Tabla de tecnologías"),
    ("A08", "Arquitectura general y vistas 4+1", "S1", "26-08", "08-09", "JS", "Cinco vistas documentadas"),
    ("A09", "Prototipo navegable v1 (wireframes)", "S1", "27-08", "10-09", "DP", "Prototipo v1"),
    ("A10", "Validación con usuarios y registro de feedback", "S1", "07-09", "11-09", "LD", "Bitácora de feedback"),
    ("A11", "Modelo de datos y DER", "S2", "14-09", "24-09", "JS", "DER normalizado"),
    ("A12", "Diccionario de datos y DDL de PostgreSQL", "S2", "21-09", "28-09", "JS", "Script DDL + diccionario"),
    ("A13", "Políticas de autenticación y autorización", "S2", "15-09", "25-09", "JS", "Política + matriz RBAC"),
    ("A14", "Análisis de amenazas y medidas de mitigación", "S2", "18-09", "29-09", "JS", "Catálogo de amenazas"),
    ("A15", "Estándares de codificación segura", "S2", "22-09", "30-09", "DP", "Guía de codificación"),
    ("A16", "Prototipo v2 con el feedback aplicado", "S2", "21-09", "02-10", "DP", "Prototipo v2"),
    ("A17", "Guía visual y adaptabilidad responsive", "S2", "24-09", "02-10", "DP", "Guía visual + capturas"),
    ("A18", "Plan de pruebas (unitarias, integrales, rendimiento)", "S3", "05-10", "12-10", "DP", "Plan de pruebas"),
    ("A19", "Definición de herramientas manuales y automatizadas", "S3", "07-10", "13-10", "DP", "Matriz de herramientas"),
    ("A20", "Umbrales de rendimiento y ensayo de consultas", "S3", "09-10", "15-10", "JS", "Tabla de umbrales"),
    ("A21", "Redacción del informe ES2 y anexos", "S3", "08-10", "16-10", "LD", "Informe ES2"),
    ("A22", "Revisión interna y entrega ES2", "S3", "15-10", "16-10", "LD", "Entrega ES2 — 19-10"),
    ("A23", "Implementación de backend y API REST", "S4", "20-10", "05-11", "JS", "API documentada"),
    ("A24", "Implementación de frontend React", "S4", "20-10", "06-11", "DP", "Interfaz conectada"),
    ("A25", "Dashboard, consultas e indicadores", "S5", "09-11", "17-11", "DP", "Dashboard operativo"),
    ("A26", "Despliegue cloud y pipeline CI/CD", "S5", "09-11", "18-11", "JS", "Sistema en producción"),
    ("A27", "Pruebas de integración, rendimiento y UAT", "S5", "16-11", "20-11", "LD", "Informe de pruebas — ES3"),
    ("A28", "Documentación final y manual de operación", "S6", "23-11", "04-12", "LD", "Manual de operación"),
    ("A29", "Ensayo de demostración y defensa", "S6", "07-12", "11-12", "LD", "Guion de defensa — ES4"),
]


RESPONSABLES = {"LD": "Leonardo Daza", "JS": "José Sarabia", "DP": "Daniel Paredes"}

# (actividad, predecesora, tipo, holgura_dias, ruta_critica)
DEPENDENCIAS = [
    ("A02", "A01", "FS", 0, "Sí"),
    ("A03", "A02", "FS", 0, "Sí"),
    ("A04", "A03", "FS", 0, "Sí"),
    ("A05", "A04", "FS", 0, "Sí"),
    ("A06", "A05", "FS", 0, "Sí"),
    ("A07", "A05", "SS +1 día", 0, "Sí"),
    ("A08", "A07", "FS", 0, "Sí"),
    ("A09", "A06", "SS +2 días", 2, "No"),
    ("A10", "A09", "FS", 2, "No"),
    ("A11", "A08", "FS", 0, "Sí"),
    ("A12", "A11", "FS", 0, "Sí"),
    ("A13", "A08", "SS +1 día", 3, "No"),
    ("A14", "A13", "FS", 3, "No"),
    ("A15", "A14", "SS +2 días", 4, "No"),
    ("A16", "A10", "FS", 4, "No"),
    ("A17", "A16", "SS +1 día", 4, "No"),
    ("A18", "A12", "FS", 0, "Sí"),
    ("A18", "A17", "FS", 0, "Sí"),
    ("A19", "A18", "SS +1 día", 0, "Sí"),
    ("A20", "A18", "FS", 0, "Sí"),
    ("A21", "A20", "FS", 0, "Sí"),
    ("A22", "A21", "FS", 0, "Sí"),
    ("A23", "A22", "FS", 0, "Sí"),
    ("A24", "A22", "SS +1 día", 0, "Sí"),
    ("A25", "A24", "FS", 0, "Sí"),
    ("A26", "A23", "SS +3 días", 0, "Sí"),
    ("A27", "A25", "FS", 0, "Sí"),
    ("A27", "A26", "FS", 0, "Sí"),
    ("A28", "A27", "FS", 0, "Sí"),
    ("A29", "A28", "SS +2 días", 0, "Sí"),
]

# --------------------------------------------------------------------------- #
# Backlog (HU) y requisitos
# --------------------------------------------------------------------------- #
HU = [
    ("HU-OP-01", "Ver la última inspección en tiempo real", "Operador de planta",
     "Como operador de planta quiero visualizar en tiempo real el resultado de la inspección "
     "actual (ángulo y estado aprobado/rechazado) para saber si debo ajustar el siguiente batch",
     "El dashboard muestra la última inspección registrada, el ángulo se ve con claridad, el "
     "estado se indica con color e ícono y la información se actualiza al llegar un registro nuevo",
     "Must"),
    ("HU-OP-02", "Consultar el historial de las últimas 24 horas", "Operador de planta",
     "Como operador de planta quiero consultar el historial de inspecciones de las últimas 24 "
     "horas para revisar la consistencia del proceso",
     "Existe una vista de historial reciente, se puede filtrar por fecha y hora y la tabla muestra "
     "fecha/hora, lote, receta, ángulo y estado",
     "Must"),
    ("HU-OP-03", "Recibir alerta temprana cerca del límite", "Operador de planta",
     "Como operador de planta quiero recibir una alerta visual cuando el ángulo medido esté cerca "
     "del límite de tolerancia para actuar antes de que ocurra un rechazo",
     "Se muestra una notificación o cambio de color cuando el ángulo está a menos del 10 % del "
     "límite, visible en el dashboard sin navegar",
     "Should"),
    ("HU-SU-01", "Dashboard con indicadores clave", "Supervisor de producción",
     "Como supervisor quiero acceder a un dashboard con indicadores clave (tasa de aprobación, "
     "tendencia de ángulo y producción por turno) para monitorear el rendimiento del proceso",
     "Al menos 4 KPI visibles, gráficos interactivos y filtrado por rango de fechas",
     "Must"),
    ("HU-SU-02", "Historial completo con filtros avanzados", "Supervisor de producción",
     "Como supervisor quiero consultar el historial completo de inspecciones con filtros avanzados "
     "(fecha, lote, receta, estado y operador) para analizar tendencias y problemas",
     "Filtros combinables, exportación a CSV o Excel y consulta en menos de 5 s para 10 000 registros",
     "Must"),
    ("HU-SU-03", "Trazabilidad completa de un lote", "Supervisor de producción",
     "Como supervisor quiero ver la trazabilidad completa de un lote específico con todas sus "
     "inspecciones para identificar si hubo variaciones en el proceso",
     "Existe una vista de detalle de lote con ángulo, fecha/hora, receta y operador, y permite "
     "comparar visualmente las mediciones",
     "Should"),
    ("HU-SU-04", "Reportes automáticos por correo", "Supervisor de producción",
     "Como supervisor quiero recibir reportes automáticos por correo con resúmenes diarios y "
     "semanales para estar informado sin ingresar al sistema",
     "Correo diario a las 8:00 y semanal los lunes a las 9:00 con tasa de aprobación, total de "
     "inspecciones y las tres recetas con más rechazos",
     "Could"),
    ("HU-AD-01", "Gestionar usuarios y roles", "Administrador del sistema",
     "Como administrador quiero gestionar los usuarios del sistema (crear, editar y desactivar) "
     "para controlar quién tiene acceso a la plataforma",
     "Panel de administración de usuarios, asignación de roles, aplicación inmediata del cambio de "
     "estado y almacenamiento del PIN con hash",
     "Must"),
    ("HU-AD-02", "Gestionar recetas y tolerancias", "Administrador del sistema",
     "Como administrador quiero crear y modificar recetas con sus parámetros (espesor, materialidad "
     "y límites de tolerancia) para que las inspecciones se evalúen correctamente",
     "Formulario CRUD de recetas con nombre, espesor, materialidad, límite mínimo y máximo; solo el "
     "administrador puede crear, editar o eliminar",
     "Must"),
    ("HU-AD-03", "Gestionar lotes y batches", "Administrador del sistema",
     "Como administrador quiero gestionar lotes y batches para mantener la estructura organizacional "
     "de la producción",
     "Se crean lotes y batches asociados a una receta, se puede cerrar un lote manualmente y cada "
     "lote tiene nombre, fecha de inicio, fecha de fin y estado",
     "Must"),
    ("HU-AD-04", "Configurar parámetros generales", "Administrador del sistema",
     "Como administrador quiero definir parámetros generales del sistema (límites de alerta y "
     "configuración de correos) para personalizar el comportamiento de la plataforma",
     "Sección de configuración general, porcentaje de alerta temprana editable y direcciones de "
     "correo para reportes",
     "Could"),
    ("HU-SC-01", "Enviar la inspección mediante API", "Sistema de visión artificial",
     "Como sistema de visión artificial quiero enviar los resultados de la inspección (ángulo, "
     "batch y receta) a la plataforma mediante una API para registrar automáticamente las mediciones",
     "Endpoint POST /api/inspecciones que acepta JSON con angulo, id_batch, id_receta y fecha_hora; "
     "valida los datos y responde 201 o 400/500 con mensaje claro",
     "Must"),
    ("HU-SC-02", "Recibir confirmación del registro", "Sistema de visión artificial",
     "Como sistema de visión artificial quiero recibir confirmación de que el registro fue "
     "almacenado correctamente para asegurar que no se pierdan datos",
     "La respuesta incluye el identificador único de la inspección creada y, si falla, un mensaje "
     "de error descriptivo",
     "Must"),
    ("HU-CA-01", "Generar reportes personalizados", "Área de calidad",
     "Como analista de calidad quiero generar reportes personalizados con filtros avanzados para "
     "auditar procesos y preparar informes de mejora",
     "Reportes en PDF o Excel seleccionando rango de fechas, recetas, lotes y estados, con "
     "estadísticas agregadas (totales, promedios y desviación)",
     "Should"),
]



RF = [
    ("RF-01", "Registrar inspecciones mediante una API REST que reciba ángulo, batch, receta y "
              "fecha/hora", "Captura de datos", "HU-SC-01, HU-SC-02"),
    ("RF-02", "Almacenar los registros de inspección en una base de datos relacional con integridad "
              "referencial", "Persistencia", "HU-OP-01, HU-SU-03"),
    ("RF-03", "Mostrar un dashboard principal con la última inspección, indicadores visuales y "
              "gráficos de tendencia", "Visualización", "HU-OP-01, HU-SU-01"),
    ("RF-04", "Consultar el historial de inspecciones con filtros por fecha, lote, receta, estado y "
              "operador", "Consulta y búsqueda", "HU-OP-02, HU-SU-02, HU-CA-01"),
    ("RF-05", "Administrar usuarios con roles y permisos (operador, supervisor y administrador)",
     "Gestión de usuarios", "HU-AD-01"),
    ("RF-06", "Gestionar (CRUD) recetas, lotes y batches", "Gestión de catálogos",
     "HU-AD-02, HU-AD-03"),
    ("RF-07", "Enviar alertas visuales cuando el ángulo esté cerca del límite de tolerancia",
     "Notificaciones", "HU-OP-03"),
    ("RF-08", "Generar reportes en formato PDF o Excel con datos filtrados", "Reportes",
     "HU-SU-04, HU-CA-01"),
    ("RF-09", "Exportar el historial a CSV", "Exportación de datos", "HU-SU-02, HU-CA-01"),
    ("RF-10", "Registrar eventos de trazabilidad (quién y cuándo creó o modificó un registro)",
     "Auditoría y trazabilidad", "Transversal"),
    ("RF-11", "Proporcionar autenticación con credenciales seguras", "Seguridad y autenticación",
     "HU-AD-01"),
    ("RF-12", "Mostrar una vista de detalle de lote con todas sus inspecciones asociadas",
     "Visualización y consulta", "HU-SU-03"),
]



RNF = [
    ("RNF-01", "Rendimiento",
     "Las consultas con filtros no deben superar los 5 s para hasta 10 000 registros",
     "HU-SU-02 · N2, N9"),
    ("RNF-02", "Disponibilidad",
     "La plataforma debe estar disponible el 99,5 % del tiempo en horario productivo (7:00 a 20:00)",
     "N8"),
    ("RNF-03", "Seguridad",
     "Credenciales almacenadas con hash y comunicaciones cifradas mediante HTTPS",
     "HU-AD-01 · N5, N8"),
    ("RNF-04", "Usabilidad",
     "Interfaz intuitiva con diseño responsive adaptado a pantallas de planta (1024×768) y móviles",
     "HU-OP-01, HU-SU-01 · N3"),
    ("RNF-05", "Mantenibilidad",
     "Código conforme a estándares de la industria (PEP 8, convenciones de nomenclatura) y comentado",
     "N10"),
    ("RNF-06", "Escalabilidad",
     "Base de datos normalizada y con índices para optimizar las consultas más frecuentes",
     "N1, N2 · N9"),
    ("RNF-07", "Portabilidad",
     "Despliegue en entorno cloud mediante contenedores Docker",
     "N9"),
    ("RNF-08", "Pruebas",
     "Pruebas unitarias que cubran al menos el 70 % de los módulos críticos", "—"),
    ("RNF-09", "Documentación",
     "README con instrucciones claras de instalación, despliegue y uso", "N10"),
    ("RNF-10", "Integridad de datos",
     "Restricciones de clave foránea y validaciones de aplicación para evitar datos inconsistentes",
     "N1, N4"),
    ("RNF-11", "Auditoría",
     "Toda creación, modificación o eliminación registra usuario, fecha y hora", "N4"),
    ("RNF-12", "Accesibilidad",
     "Contraste de colores adecuado y navegación completa por teclado", "—"),
]



# --------------------------------------------------------------------------- #
# 2.1.2.3 — Vistas 4+1 y casos de uso
# --------------------------------------------------------------------------- #
VISTAS = [
    ("Escenarios", "Describir los casos de uso que dan sentido a la arquitectura y sirven para "
                   "validarla", "Diagrama de casos de uso + 6 escenarios expandidos",
     "HU-OP-01 a HU-CA-01 · UC-01 a UC-12"),
    ("Lógica", "Mostrar los componentes funcionales, sus responsabilidades y sus dependencias",
     "Diagrama de componentes en capas", "RF-01 a RF-12"),
    ("Desarrollo", "Explicar cómo se organiza el código y qué reglas de dependencia lo mantienen",
     "Diagrama de paquetes y estructura del repositorio", "RF-01, RF-02, RF-03"),
    ("Procesos", "Describir el comportamiento en tiempo de ejecución: concurrencia, transacciones "
                 "y trabajo asíncrono", "Diagrama de secuencia del registro de inspección",
     "RNF-01, RNF-10, RF-01"),
    ("Física", "Indicar dónde se ejecuta el software y cómo se despliega",
     "Diagrama de despliegue con contenedores y respaldo", "RNF-02, RNF-07"),
]



CASOS_USO = [
    ("UC-01", "Iniciar sesión", "Operador, Supervisor, Administrador",
     "El usuario ingresa con usuario y PIN y recibe un token de sesión",
     "RF-11, RNF-03", "Login"),
    ("UC-02", "Ver última inspección y alerta temprana", "Operador de planta",
     "Se muestra la última inspección con su ángulo, estado y aviso al acercarse al límite",
     "RF-03, RF-07", "Dashboard"),
    ("UC-03", "Consultar historial de 24 horas", "Operador de planta",
     "El operador revisa las inspecciones del turno en curso",
     "RF-04", "Histórico"),
    ("UC-04", "Dashboard de indicadores", "Supervisor de producción, Área de calidad",
     "Se muestran los KPI del proceso y la tendencia del ángulo por receta",
     "RF-03", "Dashboard"),
    ("UC-05", "Consultar histórico con filtros y exportar", "Supervisor de producción, Área de calidad",
     "El usuario acota el histórico con varios filtros y descarga el resultado",
     "RF-04, RF-09, RF-08", "Histórico"),
    ("UC-06", "Ver trazabilidad de un lote", "Supervisor de producción",
     "Se listan todas las inspecciones de un lote con su receta y operador",
     "RF-12", "Detalle"),
    ("UC-07", "Gestionar usuarios y roles", "Administrador del sistema",
     "Se da de alta, baja y cambia el rol de los usuarios",
     "RF-05, RF-11", "Usuarios"),
    ("UC-08", "Gestionar recetas, lotes y batches", "Administrador del sistema",
     "Se administran los catálogos que dan contexto a cada inspección",
     "RF-06", "Recetas"),
    ("UC-09", "Configurar parámetros y alertas", "Administrador del sistema",
     "Se define el porcentaje de alerta temprana y los destinatarios de reportes",
     "RF-07, RF-08", "Recetas"),
    ("UC-10", "Registrar inspección", "Sistema de visión artificial",
     "La API recibe la medición, valida, evalúa y persiste la inspección",
     "RF-01, RF-02", "Sección 2.1.2.3 (procesos)"),
    ("UC-11", "Evaluar estado por tolerancia", "Sistema (incluido en UC-10)",
     "Se busca la receta vigente y se compara el ángulo con sus límites",
     "RF-02, RF-07", "Sección 2.1.2.3 (procesos)"),
    ("UC-12", "Generar y enviar reportes", "Sistema de visión artificial / Supervisor",
     "Se compone el reporte y se envía por correo al destinatario configurado",
     "RF-08", "Sección 2.1.2.3 (procesos)"),
]



ESCENARIOS = [
    ("E-01", "Registro de una inspección aprobada", "Sistema de visión artificial",
     "Existe una receta activa con rango 45°–90° y el dato llega con ángulo 58,4° (HU-SC-01)",
     "1) La API valida el token de servicio y el formato del JSON. 2) Busca la receta vigente "
     "(UC-11). 3) Compara el ángulo con los límites. 4) Persiste la inspección con estado aprobado "
     "(RF-02). 5) Devuelve 201 con el identificador (HU-SC-02). 6) Registra la auditoría (RF-10).",
     "La inspección aparece en el dashboard del operador en menos de 2 s (HU-OP-01)"),
    ("E-02", "Registro de una inspección rechazada", "Sistema de visión artificial",
     "La receta activa es 45°–90° y el ángulo recibido es 41,8°",
     "Igual que E-01, pero el estado calculado es rechazado; se conserva la diferencia respecto del "
     "límite para el análisis posterior y se dispara la alerta visual (RF-07)",
     "El dashboard muestra el estado en rojo y la tendencia marca el punto (HU-OP-03)"),
    ("E-03", "Alerta temprana cerca del límite", "Operador de planta",
     "El ángulo medido está a menos del 10 % del límite inferior de la receta",
     "El servicio detecta la proximidad al límite al evaluar el estado (UC-11) y el dashboard "
     "destaca el valor sin que el operador deba navegar (RF-07)",
     "El operador advierte la condición antes de que se produzca un rechazo"),
    ("E-04", "Consulta histórica filtrada y exportada", "Supervisor de producción",
     "El supervisor filtra por lote L-2026-0412 y estado rechazado",
     "El sistema aplica los filtros combinados (RF-04), pagina los resultados y permite exportar a "
     "CSV (RF-09) o generar un reporte (RF-08)",
     "La consulta se resuelve dentro del umbral de RNF-01 e incluye la evidencia exportable"),
    ("E-05", "Cambio de tolerancia en una receta", "Administrador del sistema",
     "La receta A-36 pasa de 45°–90° a 50°–90° mediante el CRUD de recetas (HU-AD-02)",
     "El sistema versiona la receta y registra el cambio en auditoría (RF-10, RNF-11); las "
     "inspecciones anteriores conservan los límites con que fueron evaluadas (RNF-10)",
     "El histórico no se altera; solo cambian las evaluaciones nuevas"),
    ("E-06", "Acceso denegado a una función", "Operador de planta",
     "Un operador intenta editar una receta",
     "El sistema valida el rol en el servidor (RF-05, RNF-03), rechaza la operación con 403 y "
     "registra el intento en la bitácora (RF-10)",
     "El usuario ve un mensaje comprensible y no accede al formulario"),
]



# --------------------------------------------------------------------------- #
# 2.1.2.4 — Tecnologías
# --------------------------------------------------------------------------- #
TECNOLOGIAS = [
    ("Frontend", "React 18 + TypeScript", "SPA",
     "Ecosistema maduro, componentes reutilizables y tipado que reduce errores en el cliente; "
     "permite construir el dashboard y el histórico con una sola base de código",
     "Vue 3 (descartado por menor experiencia del equipo)"),
    ("Frontend", "Tailwind CSS 3", "Estilos",
     "Tokens de diseño y utilidades que garantizan consistencia visual y permiten definir los "
     "puntos de quiebre responsive sin hojas de estilo paralelas",
     "Bootstrap (descartado por rigidez del sistema de grillas)"),
    ("Frontend", "Vite 5", "Build",
     "Compilación rápida y empaquetado optimizado; integración directa con el pipeline de CI",
     "Webpack (más lento de configurar para un equipo pequeño)"),
    ("Backend", "Python 3.12 + FastAPI", "API REST",
     "Documentación OpenAPI automática, validación de datos con tipado y alto rendimiento; el equipo "
     "ya domina Python por la aplicación de planta existente",
     "Django REST (más pesado para una API centrada en datos)"),
    ("Backend", "SQLAlchemy 2.0 + Alembic", "Persistencia",
     "ORM maduro con migraciones versionadas y control explícito de transacciones",
     "Consultas SQL crudas (descartado por mantenibilidad)"),
    ("Backend", "Pydantic 2", "Validación",
     "Valida la entrada antes de tocar la base de datos y genera los esquemas del contrato de API",
     "Validación manual (propensa a omisiones)"),
    ("Backend", "Celery + Redis", "Trabajo asíncrono",
     "Envía alertas y genera exportaciones fuera del ciclo de la petición, manteniendo el tiempo de "
     "respuesta bajo el umbral de RNF-01",
     "Hilos internos (no escalan entre réplicas)"),
    ("Datos", "PostgreSQL 16", "BD estructurada",
     "Integridad referencial, transacciones ACID, tipos JSONB para datos semiestructurados e índices "
     "avanzados para las consultas históricas",
     "MySQL (menor soporte de JSONB e índices parciales)"),
    ("Datos", "MinIO (compatible con S3)", "Datos no estructurados",
     "Almacena las imágenes de ráfaga y las exportaciones fuera de la base de datos, con respaldo "
     "hacia un bucket externo",
     "Guardar imágenes como BLOB (degrada el rendimiento de la BD)"),
    ("Infraestructura", "Docker + Docker Compose", "Contenedores",
     "Despliegue reproducible en un solo archivo, aislamiento de servicios y facilidad de réplica",
     "Instalación directa en el sistema operativo (no reproducible)"),
    ("Infraestructura", "Nginx", "Proxy inverso",
     "Terminación TLS, compresión, cabeceras de seguridad y límite de peticiones",
     "Exponer la API directamente (sin control de perímetro)"),
    ("Infraestructura", "VPS Ubuntu 24.04", "Hosting",
     "Costo controlado y control total del entorno; suficiente para la carga académica estimada",
     "PaaS administrado (menor control para la defensa técnica)"),
    ("Calidad", "pytest + httpx + Testcontainers", "Pruebas backend",
     "Pruebas unitarias e integrales contra un PostgreSQL real en contenedor",
     "Mocks de base de datos (no validan SQL real)"),
    ("Calidad", "Vitest + Testing Library", "Pruebas frontend",
     "Pruebas de componentes y de interacción en el navegador simulado",
     "Solo pruebas manuales (no repetibles)"),
    ("Calidad", "k6", "Rendimiento",
     "Escenarios de carga con métricas de percentiles y umbrales automatizados",
     "JMeter (más pesado de operar)"),
    ("Calidad", "Ruff + ESLint + pip-audit", "Análisis estático",
     "Detecta errores de estilo, código muerto y dependencias vulnerables en el pipeline",
     "Revisión manual (no sistemática)"),
    ("Operación", "GitHub Actions", "CI/CD",
     "Ejecuta lint, pruebas y despliegue en cada integración, con historial auditable",
     "Despliegue manual por SSH (riesgo de error humano)"),
]

# --------------------------------------------------------------------------- #
# 2.1.3 — Guía visual y responsive
# --------------------------------------------------------------------------- #
GUIA_VISUAL = [
    ("Color primario", "--verde-700", "#2E7D32", "Encabezados, botones principales, barra lateral",
     "7,1:1 sobre blanco"),
    ("Color primario oscuro", "--verde-800", "#1B5E20", "Barra lateral, texto sobre fondo claro",
     "9,6:1 sobre blanco"),
    ("Acento de estado correcto", "--verde-100 / --verde-800", "#E8F5E9 / #1B5E20",
     "Etiqueta de estado aprobado", "8,4:1"),
    ("Acento de estado crítico", "--rojo-100 / --rojo", "#FFEBEE / #C62828",
     "Etiqueta de estado rechazado", "5,9:1"),
    ("Acento de advertencia", "--ambar-100 / #8D6E00", "#FFF8E1 / #8D6E00",
     "Etiqueta de estado sin receta", "6,2:1"),
    ("Fondo de aplicación", "--gris-100", "#F1F4F5", "Fondo general", "—"),
    ("Superficie de tarjeta", "--blanco", "#FFFFFF", "Tarjetas, tablas, formularios", "—"),
    ("Tipografía base", "Segoe UI / system-ui", "15 px", "Texto general", "—"),
    ("Escala tipográfica", "1,55 / 1,2 / 1 / 0,87 rem", "—", "Título, sección, subtítulo, tabla", "—"),
    ("Radio de esquina", "--radio", "10 px", "Tarjetas; 6 px en controles", "—"),
    ("Elevación", "--sombra", "0 1px 3px rgba(16,24,40,.10)", "Tarjetas en reposo", "—"),
    ("Espaciado", "base 4 px", "8 / 12 / 16 / 22 px", "Separación entre bloques", "—"),
]

RESPONSIVE = [
    ("Escritorio amplio", "≥ 1181 px", "Barra lateral fija de 236 px; 4 tarjetas KPI por fila; "
                                       "tablas completas", "Puesto de supervisión en oficina"),
    ("Escritorio / tablet horizontal", "861 – 1180 px", "2 tarjetas KPI por fila; una columna en "
                                                       "las vistas de dos paneles", "Notebook del supervisor"),
    ("Tablet vertical / móvil grande", "521 – 860 px", "Barra lateral se convierte en barra "
                                                       "superior; tablas pasan a tarjetas apiladas", "Tablet en sala de control"),
    ("Móvil", "≤ 520 px", "Una tarjeta KPI por fila; filtros a una columna; tipografía reducida",
     "Teléfono del supervisor en terreno"),
]

FEEDBACK = [
    ("FB-01", "R1", "Operador de planta",
     "El ángulo no se lee a distancia; el número se pierde entre los textos",
     "Aumentar la jerarquía tipográfica y añadir el estado con color al lado del valor",
     "Medidor circular con cifra grande y etiqueta de estado", "Aplicado en v2"),
    ("FB-02", "R1", "Operador de planta",
     "No queda claro si el valor está dentro del rango permitido",
     "Mostrar la tolerancia de la receta junto al ángulo",
     "Barra de rango con mínimo, máximo y marcador de posición", "Aplicado en v2"),
    ("FB-03", "R1", "Operador de planta",
     "Hay que entrar a otra pantalla para ver la última inspección",
     "Dejar el resultado más reciente en la pantalla de inicio",
     "Tarjeta «Última inspección» en el dashboard", "Aplicado en v2"),
    ("FB-04", "R1", "Operador de planta",
     "Los colores de estado no se distinguen bien con luz de planta",
     "Reforzar el contraste y no depender solo del color",
     "Etiquetas con texto y punto de color; contraste AA verificado", "Aplicado en v2"),
    ("FB-05", "R1", "Supervisor de calidad",
     "El filtro por lote estaba escondido en un panel lateral",
     "Dejar los filtros visibles sobre la tabla",
     "Barra de filtros permanente sobre el listado", "Aplicado en v2"),
    ("FB-06", "R1", "Supervisor de calidad",
     "Se necesitaba comparar la tendencia entre dos recetas",
     "Permitir seleccionar la receta del gráfico y comparar períodos",
     "Selector de receta y período en la tarjeta de tendencia", "Aplicado en v2"),
    ("FB-07", "R1", "Supervisor de calidad",
     "La tabla no se podía leer en el teléfono",
     "Adaptar las tablas a pantallas pequeñas",
     "Filas convertidas en tarjetas bajo 860 px", "Aplicado en v2"),
    ("FB-08", "R2", "Administrador",
     "Al editar una receta no quedaba claro si se alteraba el histórico",
     "Añadir un aviso explícito de inmutabilidad",
     "Mensaje de advertencia en la pantalla de recetas", "Aplicado en v2"),
    ("FB-09", "R2", "Administrador",
     "Faltaba ver qué permisos tiene cada rol antes de asignarlo",
     "Mostrar la matriz de permisos junto a la gestión de usuarios",
     "Tabla de matriz RBAC en la vista de usuarios", "Aplicado en v2"),
    ("FB-10", "R2", "Docente contraparte",
     "La pantalla de detalle no mostraba de dónde venía el dato",
     "Explicitar el origen y el checksum de las imágenes",
     "Bloque de bitácora y metadatos en el detalle", "En revisión"),
    ("FB-11", "R2", "Docente contraparte",
     "Conviene evidenciar el estado de la conexión con la base de datos",
     "Mostrar el estado del sistema en la barra superior",
     "Indicadores de cámara y base de datos en la barra superior", "En revisión"),
]

# --------------------------------------------------------------------------- #
# 2.1.4 — Datos
# --------------------------------------------------------------------------- #
ENTIDADES = [
    ("roles", "Catálogo de roles del sistema", [
        ("id", "SERIAL", "PK", "Identificador del rol"),
        ("nombre", "VARCHAR(30)", "UK", "operador, supervisor, administrador, integrador"),
        ("descripcion", "TEXT", "—", "Alcance del rol"),
    ]),
    ("usuarios", "Personas y cuentas de servicio", [
        ("id", "SERIAL", "PK", "Identificador del usuario"),
        ("username", "VARCHAR(40)", "UK", "Nombre de acceso, único"),
        ("pin_hash", "TEXT", "NOT NULL", "Hash Argon2id del PIN (nunca el PIN)"),
        ("rol_id", "INTEGER", "FK → roles", "Rol asignado"),
        ("activo", "BOOLEAN", "DEFAULT true", "Baja lógica sin borrar historial"),
        ("creado_en", "TIMESTAMPTZ", "DEFAULT now()", "Fecha de alta"),
    ]),
    ("sesiones", "Tokens de refresco emitidos", [
        ("id", "SERIAL", "PK", "Identificador de la sesión"),
        ("usuario_id", "INTEGER", "FK → usuarios", "Dueño de la sesión"),
        ("refresh_hash", "TEXT", "NOT NULL", "Hash del token de refresco"),
        ("expira_en", "TIMESTAMPTZ", "NOT NULL", "Caducidad del token"),
        ("revocado", "BOOLEAN", "DEFAULT false", "Cierre de sesión o compromiso"),
    ]),
    ("recetas", "Parámetros y tolerancias por producto", [
        ("id", "SERIAL", "PK", "Identificador de la receta"),
        ("nombre", "VARCHAR(40)", "UK", "A-36, Barra 12, Roll 50"),
        ("min_tol", "NUMERIC(5,2)", "NOT NULL", "Límite inferior del ángulo"),
        ("max_tol", "NUMERIC(5,2)", "NOT NULL", "Límite superior del ángulo"),
        ("activa", "BOOLEAN", "DEFAULT true", "Solo una versión activa por nombre"),
        ("creado_por", "INTEGER", "FK → usuarios", "Administrador responsable"),
        ("creado_en", "TIMESTAMPTZ", "DEFAULT now()", "Fecha de creación"),
    ]),
    ("lotes", "Lotes de producción", [
        ("id", "SERIAL", "PK", "Identificador del lote"),
        ("codigo", "VARCHAR(30)", "UK", "Código visible en planta (L-2026-0412)"),
        ("receta_id", "INTEGER", "FK → recetas", "Receta prevista para el lote"),
        ("fecha_inicio", "DATE", "NOT NULL", "Inicio de producción"),
        ("fecha_fin", "DATE", "NULL", "Cierre del lote"),
        ("turno", "CHAR(1)", "CHECK A/B/C", "Turno de producción"),
    ]),
    ("batches", "Subdivisiones del lote", [
        ("id", "SERIAL", "PK", "Identificador del batch"),
        ("lote_id", "INTEGER", "FK → lotes", "Lote al que pertenece"),
        ("numero", "INTEGER", "NOT NULL", "Número correlativo dentro del lote"),
        ("iniciado_en", "TIMESTAMPTZ", "DEFAULT now()", "Inicio del batch"),
    ]),
    ("inspecciones", "Resultado de cada ráfaga procesada", [
        ("id", "BIGSERIAL", "PK", "Identificador de la inspección"),
        ("fecha_hora", "TIMESTAMPTZ", "NOT NULL", "Momento de la medición"),
        ("receta_id", "INTEGER", "FK → recetas", "Receta aplicada"),
        ("lote_id", "INTEGER", "FK → lotes", "Lote asociado"),
        ("batch_id", "INTEGER", "FK → batches", "Batch asociado"),
        ("operador_id", "INTEGER", "FK → usuarios", "Operador o cuenta de servicio"),
        ("angulo", "NUMERIC(5,2)", "NULL", "Medición angular; nulo si el análisis falló"),
        ("limite_min", "NUMERIC(5,2)", "NOT NULL", "Copia del mínimo de la receta al momento del registro"),
        ("limite_max", "NUMERIC(5,2)", "NOT NULL", "Copia del máximo de la receta al momento del registro"),
        ("estado", "VARCHAR(12)", "CHECK", "aprobado, rechazado o sin_receta"),
        ("observacion", "TEXT", "NULL", "Comentario del operador"),
        ("origen", "VARCHAR(20)", "DEFAULT 'api'", "api, simulador o manual"),
        ("creado_en", "TIMESTAMPTZ", "DEFAULT now()", "Fecha de inserción"),
    ]),
    ("imagenes", "Imágenes asociadas a la ráfaga", [
        ("id", "BIGSERIAL", "PK", "Identificador de la imagen"),
        ("inspeccion_id", "BIGINT", "FK → inspecciones", "Inspección a la que pertenece"),
        ("objeto_key", "TEXT", "NOT NULL", "Ruta en MinIO/S3"),
        ("tamano_bytes", "BIGINT", "NOT NULL", "Tamaño del archivo"),
        ("sha256", "CHAR(64)", "NOT NULL", "Huella para verificar integridad"),
        ("capturada_en", "TIMESTAMPTZ", "NOT NULL", "Momento de captura"),
    ]),
    ("alarmas", "Eventos relevantes generados", [
        ("id", "BIGSERIAL", "PK", "Identificador de la alerta"),
        ("inspeccion_id", "BIGINT", "FK → inspecciones", "Inspección que originó la alerta"),
        ("tipo", "VARCHAR(30)", "NOT NULL", "sin_receta, fuera_tolerancia, error_captura"),
        ("severidad", "VARCHAR(10)", "CHECK", "baja, media, alta"),
        ("notificada", "BOOLEAN", "DEFAULT false", "Marca de envío exitoso"),
        ("creada_en", "TIMESTAMPTZ", "DEFAULT now()", "Fecha de creación"),
    ]),
    ("auditoria", "Bitácora de cambios del sistema", [
        ("id", "BIGSERIAL", "PK", "Identificador del evento"),
        ("usuario_id", "INTEGER", "FK → usuarios", "Autor de la acción"),
        ("accion", "VARCHAR(20)", "NOT NULL", "crear, actualizar, desactivar, login"),
        ("entidad", "VARCHAR(30)", "NOT NULL", "Tabla afectada"),
        ("entidad_id", "BIGINT", "NULL", "Identificador del registro afectado"),
        ("fecha", "TIMESTAMPTZ", "DEFAULT now()", "Momento del evento"),
        ("ip", "INET", "NULL", "Origen de la petición"),
        ("detalle", "JSONB", "NULL", "Valores anteriores y nuevos"),
    ]),
]

NORMALIZACION = [
    ("1FN", "Atributos atómicos y sin grupos repetidos",
     "Los datos del operador, la receta y el lote se separaron en tablas propias; "
     "no existen campos como «receta1, receta2» ni listas dentro de una columna"),
    ("2FN", "Sin dependencias parciales de la clave primaria",
     "En «inspecciones» los atributos dependen del id completo de la inspección, no de una parte; "
     "los datos del lote viven en «lotes» y no se repiten en cada registro"),
    ("3FN", "Sin dependencias transitivas",
     "El nombre del rol está en «roles» y no en «usuarios»; las tolerancias viven en «recetas» y las "
     "inspecciones guardan solo una copia histórica de los límites aplicados, que es un dato propio "
     "del hecho registrado"),
    ("Excepción justificada", "Copia de limite_min y limite_max en «inspecciones»",
     "Se desnormaliza de forma deliberada para garantizar RNF-07: la inspección debe conservar los "
     "límites vigentes al momento del registro aunque la receta cambie después"),
    ("JSONB", "Columna «detalle» en «auditoria»",
     "Los valores anteriores y nuevos de cada entidad son heterogéneos; un tipo JSONB evita una tabla "
     "por cada entidad auditada y se puede consultar con operadores JSON en PostgreSQL"),
]

INDICES = [
    ("idx_inspecciones_fecha", "inspecciones (fecha_hora DESC)", "Consultas del histórico ordenadas "
                                                                  "por fecha, el filtro más usado"),
    ("idx_inspecciones_lote", "inspecciones (lote_id, fecha_hora DESC)", "Filtro por lote con orden "
                                                                          "cronológico"),
    ("idx_inspecciones_estado", "inspecciones (estado) WHERE estado <> 'aprobado'",
     "Índice parcial para localizar rechazadas y sin receta sin recorrer toda la tabla"),
    ("idx_inspecciones_receta", "inspecciones (receta_id, fecha_hora DESC)", "Serie de tendencia por "
                                                                             "receta"),
    ("idx_usuarios_username", "usuarios (username)", "Búsqueda en el login, única"),
    ("idx_alarmas_pendientes", "alarmas (creada_en) WHERE notificada = false",
     "Cola de alertas pendientes del trabajador asíncrono"),
]

SQL_VS_NO_SQL = [
    ("Usuarios, roles y sesiones", "PostgreSQL", "Estructurado",
     "Integridad referencial y control de acceso transaccional"),
    ("Recetas, lotes y batches", "PostgreSQL", "Estructurado",
     "Catálogos relacionales con claves únicas y restricciones"),
    ("Inspecciones y mediciones", "PostgreSQL", "Estructurado",
     "Datos numéricos y de fecha que se filtran y agregan con SQL; requieren índices y transacciones"),
    ("Bitácora de auditoría", "PostgreSQL con columna JSONB", "Semiestructurado",
     "La estructura común (autor, fecha, entidad) es fija; el detalle del cambio varía por entidad"),
    ("Imágenes de ráfaga", "MinIO / S3", "No estructurado",
     "Archivos binarios grandes: guardarlos en la BD degradaría las consultas y los respaldos"),
    ("Exportaciones CSV", "MinIO / S3", "No estructurado",
     "Archivos generados bajo demanda, con caducidad, sin necesidad de consulta relacional"),
    ("Caché de indicadores", "Redis", "Clave-valor",
     "Agregados costosos que se recalculan periódicamente y se sirven sin tocar PostgreSQL"),
    ("Logs de aplicación", "Archivos rotados + servicio de registro", "No estructurado",
     "Texto de diagnóstico que no requiere consultas relacionales"),
]

# --------------------------------------------------------------------------- #
# 2.1.5 — Seguridad
# --------------------------------------------------------------------------- #
ROLES_MATRIZ = [
    ("Ver última inspección", "✔", "✔", "✔"),
    ("Consultar histórico del turno", "✔", "✔", "✔"),
    ("Consultar histórico completo", "—", "✔", "✔"),
    ("Filtrar y exportar", "—", "✔", "✔"),
    ("Ver índice de tendencias", "—", "✔", "✔"),
    ("Crear y editar inspecciones manuales", "—", "—", "✔"),
    ("Crear y editar recetas", "—", "—", "✔"),
    ("Desactivar recetas", "—", "—", "✔"),
    ("Gestionar usuarios y roles", "—", "—", "✔"),
    ("Consultar auditoría", "—", "✔", "✔"),
    ("Configurar alertas", "—", "—", "✔"),
    ("Registrar inspecciones por API", "—", "—", "— (rol integrador)"),
]

AUTENTICACION = [
    ("Almacenamiento de credenciales", "Argon2id con sal única por usuario",
     "Es el algoritmo recomendado por OWASP para contraseñas y PIN; resistente a GPU y a ataques de "
     "diccionario"),
    ("Política de PIN", "Mínimo 6 dígitos, sin secuencias ni repeticiones; bloqueo tras 5 intentos "
                        "fallidos durante 15 minutos",
     "Equilibra la usabilidad en planta (teclado numérico) con la resistencia al fuerza bruta"),
    ("Sesión", "JWT de acceso de 15 minutos + token de refresco rotatorio de 8 horas almacenado con hash",
     "Limita la ventana de uso de un token robado; la rotación detecta reutilización"),
    ("Transporte", "TLS 1.3 obligatorio; redirección de HTTP a HTTPS; HSTS",
     "Evita la intercepción de credenciales y de datos en la red de planta"),
    ("Cuentas de servicio", "Token de larga duración con alcance limitado a POST /inspecciones",
     "El sistema de captura no puede leer ni modificar recetas ni usuarios (mínimo privilegio)"),
    ("Cierre de sesión", "Revocación del token de refresco en la base de datos",
     "Permite invalidar sesiones activas ante un incidente o cambio de rol"),
    ("Recuperación de acceso", "Solo el administrador puede restablecer un PIN; queda en auditoría",
     "Evita canales de recuperación autoservicio sin verificación de identidad"),
    ("Autorización", "RBAC verificado en el servidor en cada endpoint, no en el cliente",
     "El cliente puede ser manipulado; la decisión de acceso siempre es del backend"),
]

AUTORIZACION_ENDPOINTS = [
    ("POST", "/api/v1/auth/login", "Público", "Limitado por IP y por intentos fallidos"),
    ("POST", "/api/v1/auth/refresh", "Sesión válida", "Rotación del token de refresco"),
    ("GET", "/api/v1/inspecciones", "Operador, Supervisor, Administrador", "El operador solo ve el turno actual"),
    ("POST", "/api/v1/inspecciones", "Integrador", "Único endpoint con token de servicio"),
    ("GET", "/api/v1/inspecciones/{id}", "Supervisor, Administrador", "El operador accede solo a la última"),
    ("GET", "/api/v1/recetas", "Supervisor, Administrador", "El operador no requiere recetas completas"),
    ("POST", "/api/v1/recetas", "Administrador", "Registra autor y fecha"),
    ("PATCH", "/api/v1/recetas/{id}", "Administrador", "Versiona y audita el cambio"),
    ("GET", "/api/v1/usuarios", "Administrador", "Nunca devuelve hash ni PIN"),
    ("POST", "/api/v1/usuarios", "Administrador", "PIN inicial generado y entregado fuera de banda"),
    ("DELETE", "/api/v1/usuarios/{id}", "Administrador", "Baja lógica; no borra el historial"),
    ("GET", "/api/v1/auditoria", "Supervisor, Administrador", "Solo lectura, paginada"),
    ("GET", "/api/v1/exportaciones", "Supervisor, Administrador", "Genera el CSV en segundo plano"),
    ("GET", "/api/v1/health", "Público", "Sin datos de negocio"),
]

AMENAZAS = [
    ("Spoofing (suplantación)", "Robo de credenciales o de un token de sesión",
     "Hash Argon2id, JWT de vida corta, rotación de refresco, TLS 1.3 y bloqueo por intentos", "RF-11, RNF-03"),
    ("Tampering (manipulación)", "Alteración de una medición o de una tolerancia para forzar un "
                                 "resultado aprobado",
     "Inmutabilidad de la inspección (RNF-10), límites copiados al momento del registro, auditoría con valores "
     "anteriores y posteriores", "RNF-10, RF-10"),
    ("Repudiation (repudio)", "Un usuario niega haber modificado una receta",
     "Bitácora de auditoría con usuario, fecha, IP y detalle del cambio; registro no editable", "RF-10, RNF-11"),
    ("Information disclosure (fuga de información)", "Exposición de datos de producción o de la "
                                                     "bitácora fuera de la empresa",
     "RBAC por endpoint, token con alcance mínimo, cabeceras de seguridad, logs sin datos sensibles", "RF-05, RNF-03"),
    ("Denial of service", "Ráfagas masivas de peticiones al endpoint de registro que saturan la API",
     "Rate limit por IP y por token, límite de tamaño de payload, cola asíncrona y monitoreo de latencia", "RNF-02"),
    ("Elevation of privilege", "Un operador intenta acceder a la gestión de usuarios variando parámetros",
     "Verificación de rol en el servidor, no en el cliente; pruebas de permisos en CI", "RF-05, RNF-03"),
    ("Inyección SQL", "Manipulación de parámetros de filtro en el histórico",
     "ORM con parámetros vinculados, validación Pydantic y permisos mínimos del usuario de BD", "RF-04, RNF-10"),
    ("XSS y CSRF", "Inyección de script en una observación o falsificación de petición desde el navegador",
     "Escapado por defecto de React, Content-Security-Policy, cookies SameSite y token CSRF", "RF-03, RNF-03"),
    ("Dependencias vulnerables", "Librería de terceros con vulnerabilidad conocida",
     "Versiones fijadas, pip-audit y Dependabot en CI, actualización mensual planificada", "RNF-05"),
    ("Fuga de secretos", "Credenciales incluidas en el repositorio",
     "Variables de entorno y gestor de secretos; gitleaks en el pipeline; rotación al detectarse", "RNF-03"),
    ("Pérdida de datos", "Fallo del disco del VPS o borrado accidental",
     "Respaldo diario cifrado en región distinta, retención de 30 días y prueba de restauración mensual",
     "RNF-02"),
    ("Abuso de cuenta privilegiada", "Uso indebido de una cuenta de administrador",
     "Separación de roles, cuentas nominales (sin compartir), auditoría y revisión trimestral de accesos",
     "RF-05, RNF-11"),
]

ESTANDARES_SEGUROS = [
    ("Validación de entrada", "Todo dato externo se valida con esquemas Pydantic antes de la lógica de "
                              "negocio; se rechaza con 422",
     "Pydantic 2 · pytest", "Cada esquema tiene casos de prueba de datos inválidos"),
    ("Consultas a la base de datos", "Solo el repositorio ejecuta SQL; parámetros vinculados; prohibido "
                                     "concatenar cadenas",
     "SQLAlchemy 2.0 · Ruff (S608)", "Revisión por pull request y regla de lint activa"),
    ("Gestión de secretos", "Sin credenciales en el código ni en el repositorio; variables de entorno "
                            "o gestor de secretos",
     "gitleaks · .env.example", "El pipeline falla si detecta un secreto"),
    ("Manejo de errores", "Mensajes genéricos al cliente; el detalle va al log con identificador de "
                          "correlación",
     "Excepciones de dominio · middleware de errores", "Pruebas de respuesta ante error interno"),
    ("Dependencias", "Versiones fijadas en lockfile; auditoría automática; sin paquetes sin "
                     "mantenimiento",
     "pip-audit · Dependabot", "Ejecución en cada pull request"),
    ("Registro y trazabilidad", "Logs estructurados en JSON; nunca se registran PIN, tokens ni datos "
                                "personales",
     "logging + structlog", "Revisión de patrones prohibidos en el código"),
    ("Control de versiones", "Rama por historia, pull request con al menos una revisión, commits con "
                             "mensaje convencional",
     "GitHub · branch protection", "Historial auditable del repositorio"),
    ("Análisis estático", "Lint y análisis de seguridad antes de integrar",
     "Ruff · ESLint · Bandit", "Quality gate obligatorio en el pipeline"),
    ("Cifrado", "TLS 1.3 en tránsito; cifrado en reposo del volumen y de los respaldos",
     "Nginx · cifrado del proveedor", "Verificación de configuración en el despliegue"),
    ("Principio de mínimo privilegio", "El usuario de base de datos de la aplicación no es propietario "
                                       "del esquema ni puede alterar la estructura",
     "PostgreSQL roles", "Revisión de permisos en el script de despliegue"),
]

# --------------------------------------------------------------------------- #
# 2.1.6 — Pruebas
# --------------------------------------------------------------------------- #
PLAN_PRUEBAS = [
    ("TP-01", "Unitaria", "Cálculo del estado según tolerancias (aprobado, rechazado, alerta temprana)",
     "RF-02, RF-07", "pytest", "Los estados y los valores límite exactos", "Automatizada"),
    ("TP-02", "Unitaria", "Validación de campos obligatorios y rangos del DTO de inspección",
     "RF-01", "pytest + Pydantic", "Rechaza angulo no numérico, fuera de 0–360 y receta inexistente",
     "Automatizada"),
    ("TP-03", "Unitaria", "Generación y verificación del hash del PIN",
     "RF-11, RNF-03", "pytest", "Un PIN correcto valida; uno incorrecto falla; el hash cambia en cada alta",
     "Automatizada"),
    ("TP-04", "Unitaria", "Cálculo de los KPI del dashboard (tasa de aprobación y conteos)",
     "RF-03", "pytest", "Los agregados coinciden con un conjunto de datos conocido", "Automatizada"),
    ("TP-05", "Unitaria", "Componente de medidor de ángulo y etiqueta de estado",
     "RF-03", "Vitest + Testing Library", "Renderiza el valor y el estado correctos", "Automatizada"),
    ("TP-06", "Integración", "Login y obtención de token válido e inválido",
     "RF-11, RNF-03", "pytest + httpx", "200 con token; 401 con credenciales inválidas; 423 tras bloqueo",
     "Automatizada"),
    ("TP-07", "Integración", "Registro de inspección contra el endpoint POST /api/inspecciones",
     "RF-01, RF-02, HU-SC-01", "pytest + Testcontainers", "201 con identificador, registro persistido y estado correcto",
     "Automatizada"),
    ("TP-08", "Integración", "Registro con receta inexistente y generación de alerta",
     "RF-01, RF-07", "pytest + Testcontainers", "Se persiste con estado sin receta y se crea la alerta",
     "Automatizada"),
    ("TP-09", "Integración", "Filtros combinados del histórico",
     "RF-04", "pytest + Testcontainers", "La respuesta solo contiene los registros que cumplen los filtros",
     "Automatizada"),
    ("TP-10", "Integración", "Permisos por endpoint para cada uno de los tres roles",
     "RF-05, RNF-03", "pytest", "Matriz completa rol × endpoint: 403 donde corresponde", "Automatizada"),
    ("TP-11", "Integración", "Inmutabilidad del registro ante un cambio de receta",
     "RNF-10", "pytest", "Los límites guardados no cambian al modificar la receta", "Automatizada"),
    ("TP-12", "Integración", "Baja lógica de usuario y conservación del historial",
     "RF-05", "pytest", "El usuario inactivo no puede ingresar, pero sus registros permanecen",
     "Automatizada"),
    ("TP-13", "Rendimiento", "Consulta del histórico con filtros sobre 10 000 y 100 000 registros",
     "RNF-01, RNF-06", "k6 + EXPLAIN ANALYZE", "p95 < 300 ms con 50 usuarios concurrentes", "Automatizada"),
    ("TP-14", "Rendimiento", "Registro de inspecciones a 10 peticiones por segundo durante 5 minutos",
     "RNF-01", "k6", "Sin errores 5xx y p95 < 300 ms", "Automatizada"),
    ("TP-15", "Rendimiento", "Carga inicial del dashboard",
     "RNF-01, RNF-04", "Lighthouse + k6", "Respuesta < 500 ms y puntaje de rendimiento ≥ 85",
     "Automatizada"),
    ("TP-16", "Rendimiento", "Degradación controlada si la base de datos no responde",
     "RNF-02", "k6 + corte del contenedor", "La API responde 503 con mensaje claro en menos de 5 s",
     "Manual asistida"),
    ("TP-17", "Seguridad", "Intentos de inyección en los parámetros de filtro",
     "RF-04, RNF-10", "pytest + payloads OWASP", "No se ejecuta SQL inyectado; la respuesta es 400",
     "Automatizada"),
    ("TP-18", "Seguridad", "Ausencia de datos sensibles en respuestas y logs",
     "RNF-03, RNF-11", "Revisión + gitleaks", "No aparecen PIN, hash ni tokens en logs ni en JSON",
     "Manual"),
    ("TP-19", "UAT", "Flujo completo del operador en una jornada simulada",
     "HU-OP-01, HU-OP-02", "Checklist guiado", "Obtiene la última inspección y el historial sin ayuda",
     "Manual"),
    ("TP-20", "UAT", "Flujo del supervisor: filtrar, analizar y exportar",
     "HU-SU-01, HU-SU-02, RF-09", "Checklist guiado", "Completa la tarea sin ayuda del equipo",
     "Manual"),
    ("TP-21", "UAT", "Flujo del administrador: crear receta y usuario",
     "HU-AD-01, HU-AD-02", "Checklist guiado", "Crea ambos registros y comprende el aviso de inmutabilidad",
     "Manual"),
    ("TP-22", "UAT", "Uso desde tablet y teléfono en la sala de control",
     "RNF-04, RNF-12", "Checklist guiado", "Todas las vistas son legibles y operables desde 360 px",
     "Manual"),
]



HERRAMIENTAS = [
    ("Automatizada", "pytest", "Pruebas unitarias e integrales del backend", "Cada push y cada pull request"),
    ("Automatizada", "httpx + Testcontainers", "Pruebas de contrato de API contra PostgreSQL real",
     "Cada push"),
    ("Automatizada", "Vitest + Testing Library", "Pruebas de componentes React", "Cada push"),
    ("Automatizada", "k6", "Escenarios de carga y umbrales de rendimiento", "Antes de cada entrega"),
    ("Automatizada", "Ruff + ESLint + Bandit", "Análisis estático y de seguridad del código", "Cada push"),
    ("Automatizada", "pip-audit + gitleaks", "Auditoría de dependencias y búsqueda de secretos",
     "Cada push"),
    ("Automatizada", "Lighthouse CI", "Rendimiento y accesibilidad del frontend", "Antes de cada entrega"),
    ("Automatizada", "GitHub Actions", "Orquestación de todo el pipeline", "Automático"),
    ("Manual", "Checklist de UAT", "Validación de los flujos con el PO y usuarios simulados",
     "Al cierre de cada sprint"),
    ("Manual", "Prueba exploratoria", "Búsqueda de defectos no cubiertos por los casos formales",
     "Semanal"),
    ("Manual", "Revisión por pares", "Lectura del código antes de integrar", "Cada pull request"),
    ("Manual", "Revisión de accesibilidad", "Contraste, foco visible y navegación con teclado",
     "Al cambiar la interfaz"),
]

UMBRALES = [
    ("Consulta del histórico", "p95 < 300 ms", "50 usuarios concurrentes",
     "Refina el RNF-01 del ES1 (5 s con 10 000 registros); se exige más sobre 100 000 registros"),
    ("Registro de inspección", "p95 < 200 ms", "10 peticiones por segundo",
     "Basado en ráfagas por gatillo; no se dispone de la frecuencia real de planta"),
    ("Carga del dashboard", "p95 < 500 ms", "30 usuarios concurrentes",
     "Incluye indicadores y última inspección"),
    ("Disponibilidad", "≥ 99 % mensual", "Horario 06:00–23:00",
     "Se excluye la ventana de mantención planificada"),
    ("Tamaño de payload", "≤ 1 MB por petición", "—",
     "Las imágenes no viajan por la API; se referencian por clave de objeto"),
    ("Cobertura de pruebas", "≥ 70 % global y ≥ 80 % en servicios", "—",
     "Medida con coverage.py y c8"),
]

RESULTADOS_EQUIPO = [
    ("Suite de pruebas del componente de análisis de planta (APP-AZA)",
     "49 pruebas automatizadas con pytest sobre autenticación, base de datos, geometría angular, "
     "exportación y retención de resultados",
     "48 aprobadas y 1 fallo por una aserción de rutas específica de Linux al ejecutarse en Windows, "
     "atribuible al entorno y no al código de la aplicación",
     "Referencia de práctica del equipo: demuestra que el grupo ya aplica pruebas automatizadas sobre "
     "un sistema real en operación"),
    ("Análisis de una ráfaga real con el pipeline existente",
     "Detección de salida, círculo y ángulo sobre 16 imágenes sintéticas equivalentes a una ráfaga",
     "Salida detectada en el frame 7 de 16; círculo en (399,8; 249,8) con radio 149,6 px frente a "
     "(400; 250) y 150 px reales; ángulo 60,1° con confianza alta",
     "Valida el supuesto de que la medición angular llega como un valor numérico ya calculado, que es "
     "lo que la plataforma web debe persistir"),
]

# --------------------------------------------------------------------------- #
# Trazabilidad y riesgos
# --------------------------------------------------------------------------- #
TRAZABILIDAD = [
    ("N1 · Centralizar los resultados de inspección",
     "HU-SC-01, HU-OP-01", "RF-01, RF-02", "UC-10, UC-11",
     "Vista de procesos, DER", "TP-02, TP-07"),
    ("N2 · Consultas históricas con filtros",
     "HU-OP-02, HU-SU-02", "RF-04", "UC-03, UC-05",
     "Vistas lógica y de procesos", "TP-09, TP-13"),
    ("N3 · Dashboards con indicadores clave",
     "HU-OP-01, HU-SU-01", "RF-03", "UC-02, UC-04",
     "Vista lógica y prototipo", "TP-04, TP-05, TP-19"),
    ("N4 · Asociar inspección a lote, receta y operador",
     "HU-SC-01, HU-SU-03", "RF-02, RF-06, RF-12", "UC-06, UC-10",
     "DER y vista de procesos", "TP-07, TP-11"),
    ("N5 · Control de acceso basado en roles",
     "HU-AD-01", "RF-05, RF-11", "UC-01, UC-07",
     "Vista lógica (seguridad transversal)", "TP-06, TP-10, TP-12"),
    ("N6 · Simular el ingreso desde el sistema de visión",
     "HU-SC-01, HU-SC-02", "RF-01", "UC-10",
     "Vista de procesos y anexo B", "TP-02, TP-07"),
    ("N7 · Registrar eventos y alarmas",
     "HU-OP-03, HU-AD-04", "RF-07, RF-08", "UC-09, UC-12",
     "Vista de procesos (asíncrono)", "TP-01, TP-08"),
    ("N8 · Integridad, disponibilidad y respaldo",
     "Transversal", "RNF-02, RNF-10, RNF-11", "UC-01, UC-07",
     "Vista física y de seguridad", "TP-10, TP-17, TP-18"),
    ("N9 · Despliegue en la nube con acceso remoto",
     "Transversal", "RNF-06, RNF-07", "—",
     "Vista física", "TP-14, TP-15"),
    ("N10 · Documentación y mantenibilidad",
     "Transversal", "RNF-05, RNF-09", "—",
     "Anexos B y F, vista de desarrollo", "Revisión por pares"),
]



RIESGOS = [
    ("R-01", "No obtener datos reales de volumen y frecuencia de inspecciones",
     "Alta", "Alto", "Declarar un supuesto académico explícito y validar el rendimiento con ese "
                      "escenario", "Leonardo Daza"),
    ("R-02", "Cambio de alcance por parte de la contraparte",
     "Media", "Alto", "Backlog priorizado con MoSCoW y control de cambios en cada sprint",
     "Leonardo Daza"),
    ("R-03", "Baja disponibilidad de los integrantes por carga académica",
     "Media", "Medio", "Sprints cortos, tareas pequeñas y holgura identificada en la red de "
                       "dependencias", "José Sarabia"),
    ("R-04", "Dificultad para validar con usuarios de planta reales",
     "Media", "Medio", "Validación con el docente contraparte y simulación de roles",
     "Leonardo Daza"),
    ("R-05", "Complejidad del despliegue en la nube dentro del plazo",
     "Media", "Alto", "Docker Compose desde el Sprint 1 y despliegue temprano de una versión mínima",
     "José Sarabia"),
    ("R-06", "Deuda técnica por presión de entrega",
     "Baja", "Medio", "Análisis estático obligatorio, revisión por pares y refactorización planificada "
                      "en el sprint siguiente", "Daniel Paredes"),
    ("R-07", "Pérdida de información por fallo del VPS",
     "Baja", "Alto", "Respaldo diario cifrado en región distinta y prueba de restauración mensual",
     "José Sarabia"),
    ("R-08", "Credenciales expuestas en el repositorio",
     "Baja", "Alto", "gitleaks en el pipeline, secretos en variables de entorno y rotación inmediata",
     "Daniel Paredes"),
]

SUPUESTOS = [
    ("Volumen de registros", "10 000 registros como línea base (RNF-01 del ES1) y 100 000 como escenario de estrés; 350 inspecciones por turno",
     "La empresa no entregó cifras oficiales; el valor se usa solo para dimensionar pruebas"),
    ("Usuarios concurrentes", "50 simultáneos en el histórico y 30 en el dashboard",
     "Estimación académica a partir de dos turnos con supervisores y operadores"),
    ("Frecuencia de ráfagas", "10 inspecciones por minuto en el pico",
     "Derivado de la operación continua descrita; debe validarse en ES3"),
    ("Disponibilidad de la cámara", "El sistema de visión actual entrega el ángulo ya calculado",
     "El desafío excluye explícitamente la visión artificial"),
    ("Datos personales", "Solo se almacena nombre de usuario y rol, sin datos sensibles de personas",
     "Minimiza el impacto de la ley de protección de datos personales"),
    ("Conectividad de planta", "El operador accede desde la red interna; el supervisor puede hacerlo "
                               "de forma remota",
     "Justifica el despliegue en la nube con acceso mediante TLS"),
]


# --------------------------------------------------------------------------- #
# Catálogo heredado del ES1
# --------------------------------------------------------------------------- #
NECESIDADES = [
    ("N1", "Centralizar todos los resultados de inspección en una base de datos única",
     "Operador, Supervisor", "Alta", "P1, P2, P5"),
    ("N2", "Permitir consultas históricas con filtros por fecha, lote, receta y estado",
     "Operador, Supervisor, Calidad", "Alta", "P2, P3, P4"),
    ("N3", "Entregar visualizaciones con indicadores clave del proceso",
     "Supervisor, Área de calidad", "Alta", "P4"),
    ("N4", "Asociar cada inspección a batch, lote, receta y operador",
     "Supervisor, Calidad, Administrador", "Alta", "P5, P7"),
    ("N5", "Implementar control de acceso basado en roles",
     "Administrador, Seguridad TI", "Alta", "P6"),
    ("N6", "Simular el ingreso de datos desde el sistema de visión",
     "Equipo de desarrollo, Soporte TI", "Media", "Restricción de alcance académico"),
    ("N7", "Registrar eventos y alarmas para condiciones críticas",
     "Operador, Supervisor, Mantenimiento", "Media", "P7"),
    ("N8", "Garantizar integridad, disponibilidad y respaldo de los datos",
     "Administrador, Calidad, TI", "Alta", "Riesgo de pérdida de información"),
    ("N9", "Desplegar la solución en la nube para acceso remoto y escalabilidad",
     "Administrador, TI, Gerencia", "Media", "Necesidad de acceso fuera de planta"),
    ("N10", "Documentar el sistema y su funcionamiento para asegurar mantenibilidad",
     "Equipo de desarrollo, Soporte TI", "Media", "Ciclo de vida del software"),
]
