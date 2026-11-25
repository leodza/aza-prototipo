"""Modelo de datos del prototipo funcional (SQLAlchemy + SQLite).

Refleja el modelo entidad-relación del informe ES2. SQLite se usa como base
local para la demostración; el cambio a PostgreSQL consiste en sustituir la
URL de conexión (ver README).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String,
    Text, UniqueConstraint, create_engine, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

# En PostgreSQL la bitácora usa JSONB (como declara el informe ES2); en SQLite,
# que solo se usa para las pruebas, el mismo campo se guarda como JSON de texto.
DETALLE_JSON = JSON().with_variant(JSONB(), "postgresql")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CAPTURAS_DIR = os.getenv("AZA_CAPTURAS", os.path.join(DATA_DIR, "capturas"))
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CAPTURAS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "aza.db")
URL = os.getenv("AZA_DB_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(URL, connect_args={"check_same_thread": False}
                       if URL.startswith("sqlite") else {})
SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Rol(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), index=True)
    pin_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permisos: Mapped[str | None] = mapped_column(Text)   # lista JSON de poderes extra
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    rol: Mapped[Rol] = relationship(back_populates="usuarios")

    @property
    def rol_nombre(self) -> str:
        return self.rol.nombre if self.rol else ""


class Sesion(Base):
    __tablename__ = "sesiones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    refresh_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Material(Base):
    """Catálogo de materiales del trazado (no solo acero: familias y tipos)."""
    __tablename__ = "materiales"
    __table_args__ = (UniqueConstraint("familia", "tipo", name="uq_material"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    familia: Mapped[str] = mapped_column(String(40), nullable=False)   # Acero, Cobre, Aluminio…
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)      # SAE 1010, inox 304…
    descripcion: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def nombre(self) -> str:
        return f"{self.familia} {self.tipo}".strip()


class Receta(Base):
    __tablename__ = "recetas"
    __table_args__ = (CheckConstraint("min_tol < max_tol", name="chk_tolerancia"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    espesor_mm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materiales.id"))
    materialidad: Mapped[str | None] = mapped_column(String(60))
    min_tol: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    max_tol: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    material: Mapped[Material | None] = relationship()


class Lote(Base):
    __tablename__ = "lotes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    receta_id: Mapped[int | None] = mapped_column(ForeignKey("recetas.id"))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    turno: Mapped[str | None] = mapped_column(String(1))
    receta: Mapped[Receta | None] = relationship()


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (UniqueConstraint("lote_id", "numero", name="uq_lote_numero"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Inspeccion(Base):
    __tablename__ = "inspecciones"
    __table_args__ = (
        CheckConstraint("angulo IS NULL OR (angulo >= 0 AND angulo <= 360)",
                        name="chk_angulo"),
        # Índice compuesto para el histórico y el tablero, que ordenan por fecha e id
        Index("ix_inspecciones_fecha_id", "fecha_hora", "id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora,
                                                index=True)
    receta_id: Mapped[int | None] = mapped_column(ForeignKey("recetas.id"), index=True)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), index=True)
    operador_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    angulo: Mapped[float | None] = mapped_column(Numeric(5, 2))
    limite_min: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    limite_max: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    observacion: Mapped[str | None] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String(20), default="simulador")
    carpeta: Mapped[str | None] = mapped_column(Text)
    imagen: Mapped[str | None] = mapped_column(Text)
    imagen_clave: Mapped[str | None] = mapped_column(Text)   # clave del objeto en MinIO/S3
    confianza: Mapped[str | None] = mapped_column(String(10))
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    frame_salida: Mapped[int | None] = mapped_column(Integer)
    centro_x: Mapped[float | None] = mapped_column(Numeric(6, 1))
    centro_y: Mapped[float | None] = mapped_column(Numeric(6, 1))
    radio: Mapped[float | None] = mapped_column(Numeric(6, 1))
    motor: Mapped[str | None] = mapped_column(String(80))
    material: Mapped[str | None] = mapped_column(String(60))          # copia del material usado
    velocidad_m_min: Mapped[float | None] = mapped_column(Numeric(6, 1))
    desviacion_deg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    receta: Mapped[Receta | None] = relationship()
    lote: Mapped[Lote | None] = relationship()
    batch: Mapped["Batch | None"] = relationship()
    operador: Mapped[Usuario | None] = relationship()


class Alarma(Base):
    __tablename__ = "alarmas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inspeccion_id: Mapped[int | None] = mapped_column(ForeignKey("inspecciones.id"))
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    severidad: Mapped[str] = mapped_column(String(10), nullable=False)
    mensaje: Mapped[str | None] = mapped_column(Text)
    notificada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    # Flujo de revisión: pendiente -> en_revision -> solucionada
    estado: Mapped[str] = mapped_column(String(15), default="pendiente", nullable=False)
    solucion: Mapped[str | None] = mapped_column(Text)
    resuelto_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Configuracion(Base):
    """Parámetros que el administrador puede ajustar desde la interfaz."""
    __tablename__ = "configuracion"
    clave: Mapped[str] = mapped_column(String(40), primary_key=True)
    valor: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(160))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class SolicitudClave(Base):
    """Pedido de restablecimiento de contraseña que atiende el administrador."""
    __tablename__ = "solicitudes_clave"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    identificador: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), default="pendiente", nullable=False)
    nota: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    atendida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usuario: Mapped[Usuario | None] = relationship()


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    entidad: Mapped[str] = mapped_column(String(30), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, index=True)
    ip: Mapped[str | None] = mapped_column(String(45))
    detalle: Mapped[dict | None] = mapped_column(DETALLE_JSON)


CONFIG_DEFECTOS = {
    "max_intentos": ("5", "Intentos fallidos antes de bloquear la cuenta"),
    "bloqueo_min": ("15", "Minutos que dura el bloqueo de la cuenta"),
    "inactividad_min": ("20", "Minutos de inactividad antes de cerrar la sesión"),
    "sesion_unica": ("1", "1 = una sola sesión activa por usuario"),
    "respaldo_horas": ("24", "Horas entre respaldos automáticos (0 = desactivado)"),
    "respaldo_max": ("10", "Cuántos respaldos se conservan"),
}


def _columnas(s, tabla: str) -> set[str]:
    """Devuelve las columnas reales de una tabla ya creada."""
    if s.bind.dialect.name == "sqlite":
        return {f[1] for f in s.execute(text(f"PRAGMA table_info({tabla})"))}
    filas = s.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"), {"t": tabla})
    return {f[0] for f in filas}


def migrar_columnas() -> list[str]:
    """Agrega las columnas nuevas a bases ya existentes (create_all no lo hace)."""
    nuevas = {
        "usuarios": {"email": "VARCHAR(120)", "permisos": "TEXT"},
        "alarmas": {"estado": "VARCHAR(15) DEFAULT 'pendiente'",
                    "solucion": "TEXT",
                    "resuelto_por": "INTEGER",
                    "resuelto_en": "TIMESTAMP"},
    }
    aplicadas = []
    with SesionLocal() as s:
        for tabla, columnas in nuevas.items():
            existentes = _columnas(s, tabla)
            if not existentes:
                continue
            for nombre, tipo in columnas.items():
                if nombre not in existentes:
                    s.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))
                    aplicadas.append(f"{tabla}.{nombre}")
        s.commit()
    return aplicadas


def crear_tablas() -> None:
    Base.metadata.create_all(engine)
    migrar_columnas()
    with SesionLocal() as s:
        for clave, (valor, desc) in CONFIG_DEFECTOS.items():
            if not s.get(Configuracion, clave):
                s.add(Configuracion(clave=clave, valor=valor, descripcion=desc))
        s.commit()
