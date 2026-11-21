"""Servidor del prototipo funcional — API REST + interfaz web.

Implementa el diseño del informe ES2: autenticación con JWT, RBAC verificado en
el servidor, registro de inspecciones por API, simulación de ráfagas con el
pipeline de visión real, auditoría y dashboard.

Ejecutar:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
import random
import threading
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import almacenamiento, db, simulador
from .seguridad import (MAX_INTENTOS, BLOQUEO_MIN, crear_jwt, hash_pin, hash_refresh,
                        iguales, leer_jwt, nuevo_refresh, verificar_pin)

BASE_DIR = db.BASE_DIR
WEB_DIR = os.path.join(BASE_DIR, "web")
ESTADOS = ("aprobado", "rechazado", "sin_receta")


# --------------------------------------------------------------------------- #
# arranque
# --------------------------------------------------------------------------- #
def _precalentar():
    """Ejecuta una ráfaga de prueba para que el primer clic sea rápido."""
    try:
        carpeta = os.path.join(db.CAPTURAS_DIR, "_precalentamiento")
        simulador.generar_rafaga(carpeta, desde=50.0, semilla=1)
        simulador.medir_angulo(carpeta)
    except Exception:
        traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.crear_tablas()
    with db.SesionLocal() as s:
        sembrar(s)
    threading.Thread(target=_precalentar, daemon=True).start()
    yield


app = FastAPI(title="AZA · Prototipo funcional", version="1.0", lifespan=lifespan)
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


# --------------------------------------------------------------------------- #
# datos iniciales
# --------------------------------------------------------------------------- #
def sembrar(s):
    if s.scalar(select(func.count()).select_from(db.Rol)) > 0:
        return

    roles = {n: db.Rol(nombre=n, descripcion=d) for n, d in [
        ("operador", "Consulta el resultado y el historial del turno"),
        ("supervisor", "Analiza históricos e indicadores"),
        ("administrador", "Gestiona usuarios, recetas y parámetros"),
        ("integrador", "Cuenta de servicio del sistema de visión"),
    ]}
    s.add_all(roles.values())
    s.flush()

    usuarios = [
        db.Usuario(username="ldaza", nombre="Leonardo Daza", pin_hash=hash_pin("1234"),
                   rol_id=roles["operador"].id),
        db.Usuario(username="jsarabia", nombre="José Sarabia", pin_hash=hash_pin("1234"),
                   rol_id=roles["supervisor"].id),
        db.Usuario(username="dparedes", nombre="Daniel Paredes", pin_hash=hash_pin("1234"),
                   rol_id=roles["administrador"].id),
        db.Usuario(username="servicio", nombre="Sistema de visión", pin_hash=hash_pin("servicio"),
                   rol_id=roles["integrador"].id),
    ]
    s.add_all(usuarios)

    materiales = [
        db.Material(familia="Acero", tipo="SAE 1010", descripcion="Acero al carbono, bajo contenido"),
        db.Material(familia="Acero", tipo="SAE 1045", descripcion="Acero al carbono, medio contenido"),
        db.Material(familia="Acero", tipo="Inoxidable 304", descripcion="Austenítico, uso general"),
        db.Material(familia="Acero", tipo="Inoxidable 316", descripcion="Austenítico con molibdeno"),
        db.Material(familia="Cobre", tipo="Electrolítico", descripcion="Alta conductividad"),
        db.Material(familia="Latón", tipo="CW614N", descripcion="Cobre-zinc, mecanizado"),
        db.Material(familia="Aluminio", tipo="6061-T6", descripcion="Aleación estructural"),
    ]
    s.add_all(materiales)
    s.flush()
    mat = {(m.familia, m.tipo): m for m in materiales}

    def _material(familia, tipo):
        m = mat[(familia, tipo)]
        return m.id, m.nombre

    recetas = []
    for nombre, espesor, fam, tipo, minimo, maximo in [
        ("A-36", 5.5, "Acero", "SAE 1010", 45, 90),
        ("Barra 12", 12.0, "Acero", "SAE 1045", 40, 95),
        ("Roll 50", 8.0, "Acero", "Inoxidable 304", 60, 110),
        ("Roll 63", 6.5, "Cobre", "Electrolítico", 50, 100),
        ("Perfil 8", 8.0, "Aluminio", "6061-T6", 55, 105),
        ("Buje 25", 4.0, "Latón", "CW614N", 40, 85),
    ]:
        material_id, nombre_material = _material(fam, tipo)
        recetas.append(db.Receta(nombre=nombre, espesor_mm=espesor, material_id=material_id,
                                 materialidad=nombre_material, min_tol=minimo, max_tol=maximo))
    s.add_all(recetas)
    s.flush()

    azar = random.Random(2026)
    lotes = []
    for i, (cod, rec, turno) in enumerate([("L-2026-0410", recetas[0], "A"),
                                          ("L-2026-0411", recetas[1], "A"),
                                          ("L-2026-0412", recetas[2], "B"),
                                          ("L-2026-0413", recetas[3], "B"),
                                          ("L-2026-0414", recetas[4], "C"),
                                          ("L-2026-0415", recetas[5], "C")]):
        lote = db.Lote(codigo=cod, receta_id=rec.id, turno=turno,
                       fecha_inicio=datetime.now(timezone.utc) - timedelta(hours=12 - i))
        s.add(lote)
        s.flush()
        lotes_batch = [db.Batch(lote_id=lote.id, numero=n) for n in (1, 2, 3)]
        s.add_all(lotes_batch)
        s.flush()
        lotes.append((lote, rec, lotes_batch))

    # histórico de demostración (valores simulados, no medidos):
    # se distribuye dentro del día local en curso para que el dashboard muestre el turno
    ahora_local = datetime.now()
    inicio_dia = ahora_local.replace(hour=0, minute=0, second=0, microsecond=0)
    transcurrido = max(45, int((ahora_local - inicio_dia).total_seconds() // 60))
    for i in range(46):
        lote, rec, batches = azar.choice(lotes)
        batch = azar.choice(batches)
        min_t, max_t = float(rec.min_tol), float(rec.max_tol)
        if azar.random() < 0.16:
            angulo = round(azar.uniform(max(0, min_t - 18), min_t - 2), 1)
        elif azar.random() < 0.12:
            angulo = None
        else:
            centro = (min_t + max_t) / 2
            angulo = round(min(180, max(1, azar.gauss(centro, (max_t - min_t) / 5))), 2)
        estado = _evaluar(angulo, min_t, max_t)
        minutos = int(transcurrido * (46 - i) / 47) + azar.randint(0, 2)
        fecha_local = ahora_local - timedelta(minutes=minutos)
        s.add(db.Inspeccion(
            fecha_hora=_a_utc_naive(fecha_local),
            receta_id=rec.id, lote_id=lote.id, batch_id=batch.id,
            operador_id=usuarios[0].id, material=rec.materialidad,
            angulo=angulo, limite_min=min_t, limite_max=max_t, estado=estado,
            origen="historico_demo", confianza="ALTA", duracion_ms=azar.randint(1500, 2600)))
    s.commit()


def _evaluar(angulo, minimo, maximo) -> str:
    if angulo is None:
        return "sin_receta"
    if minimo <= angulo <= maximo:
        return "aprobado"
    return "rechazado"


def _iso(d: datetime | None) -> str | None:
    """Serializa como UTC explícito para que el navegador muestre la hora local."""
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.isoformat()


def _a_utc_naive(d: datetime) -> datetime:
    """Convierte una fecha local (naive) al UTC naive con que se guarda en SQLite."""
    if d.tzinfo is None:
        d = d.astimezone()
    return d.astimezone(timezone.utc).replace(tzinfo=None)


def _serializar(i: db.Inspeccion) -> dict:
    return {
        "id": i.id,
        "fecha_hora": _iso(i.fecha_hora),
        "receta": i.receta.nombre if i.receta else None,
        "receta_id": i.receta_id,
        "lote": i.lote.codigo if i.lote else None,
        "operador": i.operador.nombre if i.operador else None,
        "angulo": float(i.angulo) if i.angulo is not None else None,
        "limite_min": float(i.limite_min),
        "limite_max": float(i.limite_max),
        "estado": i.estado,
        "origen": i.origen,
        "confianza": i.confianza,
        "duracion_ms": i.duracion_ms,
        "frame_salida": i.frame_salida,
        "centro_x": float(i.centro_x) if i.centro_x is not None else None,
        "centro_y": float(i.centro_y) if i.centro_y is not None else None,
        "radio": float(i.radio) if i.radio is not None else None,
        "motor": i.motor,
        "batch": i.batch.numero if i.batch else None,
        "batch_id": i.batch_id,
        "turno": i.lote.turno if i.lote else None,
        "espesor_mm": float(i.receta.espesor_mm) if i.receta and i.receta.espesor_mm else None,
        "materialidad": i.material or (i.receta.materialidad if i.receta else None),
        "material_id": i.receta.material_id if i.receta else None,
        "material_familia": i.receta.material.familia if i.receta and i.receta.material else None,
        "velocidad_m_min": float(i.velocidad_m_min) if i.velocidad_m_min is not None else None,
        "desviacion_deg": float(i.desviacion_deg) if i.desviacion_deg is not None else None,
        "carpeta": i.carpeta,
        "imagen_clave": i.imagen_clave,
        "imagen_url": almacenamiento.url(i.imagen_clave) if i.imagen_clave else None,
        "tiene_imagen": bool(i.imagen_clave or (i.imagen and os.path.exists(i.imagen))),
        "observacion": i.observacion,
    }


# --------------------------------------------------------------------------- #
# autenticación
# --------------------------------------------------------------------------- #
class LoginIn(BaseModel):
    username: str
    pin: str


class RefreshIn(BaseModel):
    refresh: str


def _auditar(s, usuario_id, accion, entidad, entidad_id=None, ip=None, detalle=None):
    s.add(db.Auditoria(usuario_id=usuario_id, accion=accion, entidad=entidad,
                       entidad_id=entidad_id, ip=ip, detalle=detalle))


@app.post("/api/auth/login")
def login(datos: LoginIn):
    with db.SesionLocal() as s:
        u = s.scalar(select(db.Usuario).where(db.Usuario.username == datos.username.strip()))
        if not u or not u.activo:
            raise HTTPException(401, "Usuario o PIN incorrecto")

        ahora = datetime.now(timezone.utc)
        if u.bloqueado_hasta and u.bloqueado_hasta.replace(tzinfo=timezone.utc) > ahora:
            restante = int((u.bloqueado_hasta.replace(tzinfo=timezone.utc) - ahora).seconds / 60)
            raise HTTPException(423, f"Cuenta bloqueada por intentos fallidos. "
                                     f"Reintente en {restante + 1} minutos.")

        if not verificar_pin(datos.pin, u.pin_hash):
            u.intentos_fallidos += 1
            if u.intentos_fallidos >= MAX_INTENTOS:
                u.bloqueado_hasta = ahora + timedelta(minutes=BLOQUEO_MIN)
                u.intentos_fallidos = 0
                _auditar(s, u.id, "bloqueo", "usuarios", u.id,
                         detalle=f"Bloqueo tras {MAX_INTENTOS} intentos fallidos")
            s.commit()
            raise HTTPException(401, "Usuario o PIN incorrecto")

        u.intentos_fallidos = 0
        u.bloqueado_hasta = None
        claro, hashed, expira = nuevo_refresh()
        sesion = db.Sesion(usuario_id=u.id, refresh_hash=hashed, expira_en=expira)
        s.add(sesion)
        s.flush()
        _auditar(s, u.id, "login", "usuarios", u.id)
        s.commit()

        token = crear_jwt({"sub": u.username, "rol": u.rol.nombre, "sid": sesion.id,
                           "uid": u.id})
        return {
            "access": token,
            "refresh": claro,
            "usuario": {"username": u.username, "nombre": u.nombre, "rol": u.rol.nombre},
            "expira_en_seg": 900,
        }


@app.post("/api/auth/refresh")
def refrescar(datos: RefreshIn):
    with db.SesionLocal() as s:
        hashed = hash_refresh(datos.refresh)
        sesion = s.scalar(select(db.Sesion).where(db.Sesion.refresh_hash == hashed))
        if not sesion or sesion.revocado:
            raise HTTPException(401, "Token de refresco inválido o revocado")
        if sesion.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(401, "Token de refresco expirado")
        u = s.get(db.Usuario, sesion.usuario_id)
        sesion.revocado = True                      # rotación: el anterior no se reutiliza
        claro, hashed2, expira = nuevo_refresh()
        nueva = db.Sesion(usuario_id=u.id, refresh_hash=hashed2, expira_en=expira)
        s.add(nueva)
        s.flush()
        s.commit()
        token = crear_jwt({"sub": u.username, "rol": u.rol.nombre, "sid": nueva.id, "uid": u.id})
        return {"access": token, "refresh": claro, "expira_en_seg": 900}


def usuario_actual(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Falta el token de acceso")
    payload = leer_jwt(authorization[7:])
    if not payload:
        raise HTTPException(401, "Token inválido o expirado")
    with db.SesionLocal() as s:
        sesion = s.get(db.Sesion, payload.get("sid"))
        if not sesion or sesion.revocado:
            raise HTTPException(401, "Sesión revocada")
    return payload


def requiere(*roles: str):
    def _dep(usuario: dict = Depends(usuario_actual)) -> dict:
        if roles and usuario.get("rol") not in roles:
            raise HTTPException(403, f"El rol «{usuario.get('rol')}» no tiene permiso para esta acción")
        return usuario
    return _dep


@app.post("/api/auth/logout")
def logout(usuario: dict = Depends(usuario_actual)):
    with db.SesionLocal() as s:
        sesion = s.get(db.Sesion, usuario["sid"])
        if sesion:
            sesion.revocado = True
            _auditar(s, usuario["uid"], "logout", "sesiones", sesion.id)
            s.commit()
    return {"ok": True, "mensaje": "Sesión revocada"}


@app.get("/api/auth/me")
def yo(usuario: dict = Depends(usuario_actual)):
    return usuario


# --------------------------------------------------------------------------- #
# consultas
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    with db.SesionLocal() as s:
        n = s.scalar(select(func.count()).select_from(db.Inspeccion)) or 0
    motor_base = "PostgreSQL" if "postgres" in str(db.URL) else "SQLite local"
    return {"estado": "ok", "inspecciones": n, "motor": simulador._origen_pipeline,
            "base": motor_base, "almacen": almacenamiento.descripcion(),
            "objetos": almacenamiento.contar_objetos()}


def _rango(fecha: datetime | None = None) -> tuple[datetime, datetime]:
    """Devuelve el día local en curso expresado en UTC naive (como se guarda)."""
    base = fecha or datetime.now()
    inicio = base.replace(hour=0, minute=0, second=0, microsecond=0)
    return _a_utc_naive(inicio), _a_utc_naive(inicio + timedelta(days=1))


@app.get("/api/dashboard")
def dashboard(usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        ini, fin = _rango()
        filas = s.scalars(select(db.Inspeccion)
                          .where(db.Inspeccion.fecha_hora >= ini, db.Inspeccion.fecha_hora < fin)
                          .order_by(db.Inspeccion.fecha_hora.desc(), db.Inspeccion.id.desc())).all()
        total = len(filas)
        aprob = sum(1 for f in filas if f.estado == "aprobado")
        rech = sum(1 for f in filas if f.estado == "rechazado")
        sin = sum(1 for f in filas if f.estado == "sin_receta")
        tendencia = list(reversed(filas[:20]))
        ultima = filas[0] if filas else None
        alarmas = s.scalar(select(func.count()).select_from(db.Alarma)
                           .where(db.Alarma.notificada.is_(False))) or 0
        return {
            "kpis": {"total": total, "aprobadas": aprob, "rechazadas": rech,
                     "sin_receta": sin,
                     "tasa": round(aprob * 100 / total, 1) if total else 0.0,
                     "alarmas": alarmas},
            "ultima": _serializar(ultima) if ultima else None,
            "tendencia": [{"angulo": float(t.angulo) if t.angulo is not None else None,
                           "estado": t.estado,
                           "hora": t.fecha_hora.strftime("%H:%M:%S")} for t in tendencia],
            "recientes": [_serializar(x) for x in filas[:8]],
        }


@app.get("/api/inspecciones")
def listar(desde: str | None = None, hasta: str | None = None, receta: str | None = None,
           lote: str | None = None, estado: str | None = None,
           orden: str = "lote",
           pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=200),
           usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        q = select(db.Inspeccion).join(db.Receta, db.Inspeccion.receta_id == db.Receta.id,
                                       isouter=True).join(db.Lote, db.Inspeccion.lote_id == db.Lote.id,
                                                          isouter=True).join(
                                       db.Batch, db.Inspeccion.batch_id == db.Batch.id, isouter=True)
        if desde:
            q = q.where(db.Inspeccion.fecha_hora >= _a_utc_naive(datetime.fromisoformat(desde)))
        if hasta:
            q = q.where(db.Inspeccion.fecha_hora
                        < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
        if receta:
            q = q.where(db.Receta.nombre == receta)
        if lote:
            q = q.where(db.Lote.codigo == lote)
        if estado:
            q = q.where(db.Inspeccion.estado == estado)
        if usuario.get("rol") == "operador":
            ini, fin = _rango()
            q = q.where(db.Inspeccion.fecha_hora >= ini, db.Inspeccion.fecha_hora < fin)
        total = len(s.scalars(q).all())
        # El trazado se lee por lote y, dentro del lote, por batch
        if orden == "fecha":
            ordenamiento = (db.Inspeccion.fecha_hora.desc(), db.Inspeccion.id.desc())
        else:
            ordenamiento = (db.Lote.codigo.asc(), db.Batch.numero.asc(),
                            db.Inspeccion.fecha_hora.desc(), db.Inspeccion.id.desc())
        filas = s.scalars(q.order_by(*ordenamiento)
                          .offset((pagina - 1) * tamano).limit(tamano)).all()
        return {"total": total, "pagina": pagina, "tamano": tamano, "orden": orden,
                "items": [_serializar(x) for x in filas]}


@app.get("/api/inspecciones/{id}")
def detalle(id: int, usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        i = s.get(db.Inspeccion, id)
        if not i:
            raise HTTPException(404, "Inspección no encontrada")
        eventos = s.scalars(
            select(db.Auditoria)
            .where(db.Auditoria.entidad == "inspecciones", db.Auditoria.entidad_id == id)
            .order_by(db.Auditoria.fecha.desc()).limit(8)).all()
        return {"inspeccion": _serializar(i),
                "auditoria": [{"accion": e.accion, "entidad": e.entidad,
                               "fecha": _iso(e.fecha)} for e in eventos]}


@app.get("/api/inspecciones/{id}/imagen")
def imagen(id: int):
    with db.SesionLocal() as s:
        i = s.get(db.Inspeccion, id)
        clave = i.imagen_clave if i else None
        ruta = i.imagen if i else None
    if clave:
        datos = almacenamiento.leer(clave)
        if datos:
            return Response(content=datos, media_type="image/png")
    if ruta and os.path.exists(ruta):
        return FileResponse(ruta, media_type="image/png")
    raise HTTPException(404, "Esta inspección no tiene imagen de diagnóstico")


@app.get("/api/almacenamiento")
def estado_almacenamiento(usuario: dict = Depends(requiere("supervisor", "administrador"))):
    """Estado del almacenamiento de objetos (MinIO/S3) para la demostración."""
    info = {"modo": "s3" if almacenamiento.activo() else "local",
            "descripcion": almacenamiento.descripcion(),
            "endpoint": almacenamiento.ENDPOINT if almacenamiento.activo() else None,
            "bucket": almacenamiento.BUCKET if almacenamiento.activo() else None,
            "objetos": almacenamiento.contar_objetos()}
    if almacenamiento.activo():
        info["detalle"] = almacenamiento.asegurar_bucket()
    return info


@app.get("/api/recetas")
def recetas(usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Receta).order_by(db.Receta.nombre)).all()
        conteo = dict(s.execute(select(db.Inspeccion.receta_id, func.count())
                                .group_by(db.Inspeccion.receta_id)).all())
        return [{"id": r.id, "nombre": r.nombre, "min_tol": float(r.min_tol),
                 "max_tol": float(r.max_tol), "activa": r.activa,
                 "espesor_mm": float(r.espesor_mm) if r.espesor_mm else None,
                 "materialidad": r.materialidad,
                 "material_id": r.material_id,
                 "material_familia": r.material.familia if r.material else None,
                 "material_tipo": r.material.tipo if r.material else None,
                 "registros": conteo.get(r.id, 0)} for r in filas]


class RecetaIn(BaseModel):
    nombre: str
    min_tol: float = Field(ge=0, le=360)
    max_tol: float = Field(ge=0, le=360)
    espesor_mm: float | None = None
    material_id: int | None = None
    materialidad: str | None = None


@app.post("/api/recetas", status_code=201)
def crear_receta(datos: RecetaIn, usuario: dict = Depends(requiere("administrador"))):
    if datos.min_tol >= datos.max_tol:
        raise HTTPException(422, "El límite mínimo debe ser menor que el máximo")
    with db.SesionLocal() as s:
        if s.scalar(select(db.Receta).where(db.Receta.nombre == datos.nombre)):
            raise HTTPException(409, "Ya existe una receta con ese nombre")
        campos = datos.model_dump()
        if datos.material_id:
            material = s.get(db.Material, datos.material_id)
            if not material:
                raise HTTPException(422, "El material indicado no existe")
            campos["materialidad"] = material.nombre
        else:
            campos.pop("material_id", None)
        r = db.Receta(**{k: v for k, v in campos.items() if v is not None or k == "materialidad"})
        s.add(r)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "recetas", r.id, detalle=f"Receta {r.nombre}")
        s.commit()
        return {"id": r.id, "nombre": r.nombre, "material": r.materialidad}


# --------------------------------------------------------------------------- #
# materiales (catálogo de familias y tipos del trazado)
# --------------------------------------------------------------------------- #
class MaterialIn(BaseModel):
    familia: str = Field(min_length=2, max_length=40)
    tipo: str = Field(min_length=1, max_length=40)
    descripcion: str | None = None


@app.get("/api/materiales")
def materiales(usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        usos = dict(s.execute(select(db.Receta.material_id, func.count())
                              .group_by(db.Receta.material_id)).all())
        filas = s.scalars(select(db.Material).order_by(db.Material.familia,
                                                       db.Material.tipo)).all()
        return [{"id": m.id, "familia": m.familia, "tipo": m.tipo, "nombre": m.nombre,
                 "descripcion": m.descripcion, "activo": m.activo,
                 "recetas": usos.get(m.id, 0)} for m in filas]


@app.post("/api/materiales", status_code=201)
def crear_material(datos: MaterialIn, usuario: dict = Depends(requiere("administrador"))):
    with db.SesionLocal() as s:
        familia, tipo = datos.familia.strip().title(), datos.tipo.strip()
        if s.scalar(select(db.Material).where(db.Material.familia == familia,
                                              db.Material.tipo == tipo)):
            raise HTTPException(409, "Ese material ya existe en el catálogo")
        m = db.Material(familia=familia, tipo=tipo, descripcion=datos.descripcion)
        s.add(m)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "materiales", m.id, detalle=f"Material {m.nombre}")
        s.commit()
        return {"id": m.id, "nombre": m.nombre}


@app.get("/api/lotes")
def lotes(usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Lote).order_by(db.Lote.codigo.desc())).all()
        batches = s.scalars(select(db.Batch).order_by(db.Batch.numero)).all()
        por_lote: dict[int, list[dict]] = {}
        for b in batches:
            por_lote.setdefault(b.lote_id, []).append({"id": b.id, "numero": b.numero})
        return [{"id": l.id, "codigo": l.codigo,
                 "receta": l.receta.nombre if l.receta else None,
                 "receta_id": l.receta_id, "turno": l.turno,
                 "batches": por_lote.get(l.id, [])} for l in filas]


@app.get("/api/usuarios")
def usuarios(usuario: dict = Depends(requiere("administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Usuario).order_by(db.Usuario.username)).all()
        return [{"id": u.id, "username": u.username, "nombre": u.nombre,
                 "rol": u.rol.nombre, "activo": u.activo} for u in filas]


class UsuarioIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=3, max_length=80)
    rol: str
    pin: str = Field(min_length=4, max_length=32)


def _admins_activos(s, excluir: int | None = None) -> int:
    q = select(func.count()).select_from(db.Usuario).join(db.Rol).where(
        db.Rol.nombre == "administrador", db.Usuario.activo.is_(True))
    if excluir:
        q = q.where(db.Usuario.id != excluir)
    return s.scalar(q) or 0


@app.post("/api/usuarios", status_code=201)
def crear_usuario(datos: UsuarioIn, usuario: dict = Depends(requiere("administrador"))):
    with db.SesionLocal() as s:
        rol = s.scalar(select(db.Rol).where(db.Rol.nombre == datos.rol.strip().lower()))
        if not rol:
            raise HTTPException(422, "Rol inválido: use operador, supervisor o administrador")
        nombre_usuario = datos.username.strip().lower()
        if s.scalar(select(db.Usuario).where(db.Usuario.username == nombre_usuario)):
            raise HTTPException(409, "Ese nombre de usuario ya existe")
        u = db.Usuario(username=nombre_usuario, nombre=datos.nombre.strip(),
                       pin_hash=hash_pin(datos.pin), rol_id=rol.id)
        s.add(u)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "usuarios", u.id,
                 detalle=f"Alta de {u.username} con rol {rol.nombre}")
        s.commit()
        return {"id": u.id, "username": u.username, "rol": rol.nombre}


@app.patch("/api/usuarios/{id}")
def activar_usuario(id: int, activo: bool,
                    usuario: dict = Depends(requiere("administrador"))):
    with db.SesionLocal() as s:
        u = s.get(db.Usuario, id)
        if not u:
            raise HTTPException(404, "Usuario no encontrado")
        if id == usuario["uid"] and not activo:
            raise HTTPException(409, "No puede desactivar su propia cuenta")
        if not activo and u.rol.nombre == "administrador" and _admins_activos(s, id) == 0:
            raise HTTPException(409, "Debe quedar al menos un administrador activo")
        u.activo = activo
        if not activo:
            for sesion in s.scalars(select(db.Sesion).where(
                    db.Sesion.usuario_id == id, db.Sesion.revocado.is_(False))):
                sesion.revocado = True
        _auditar(s, usuario["uid"], "actualizar", "usuarios", u.id,
                 detalle=("Activación" if activo else "Desactivación") + f" de {u.username}")
        s.commit()
        return {"id": u.id, "activo": u.activo}


@app.delete("/api/usuarios/{id}", status_code=200)
def borrar_usuario(id: int, usuario: dict = Depends(requiere("administrador"))):
    """Baja lógica: la cuenta deja de poder ingresar, pero su historial se conserva."""
    with db.SesionLocal() as s:
        u = s.get(db.Usuario, id)
        if not u:
            raise HTTPException(404, "Usuario no encontrado")
        if id == usuario["uid"]:
            raise HTTPException(409, "No puede borrar su propia cuenta")
        if u.rol.nombre == "administrador" and _admins_activos(s, id) == 0:
            raise HTTPException(409, "Debe quedar al menos un administrador activo")
        u.activo = False
        for sesion in s.scalars(select(db.Sesion).where(
                db.Sesion.usuario_id == id, db.Sesion.revocado.is_(False))):
            sesion.revocado = True
        _auditar(s, usuario["uid"], "desactivar", "usuarios", u.id,
                 detalle=f"Baja lógica de {u.username}; el historial se conserva")
        s.commit()
        return {"id": u.id, "activo": False,
                "mensaje": "Cuenta desactivada; sus registros históricos se conservan"}


@app.get("/api/auditoria")
def auditoria(usuario: dict = Depends(requiere("supervisor", "administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Auditoria).order_by(db.Auditoria.fecha.desc()).limit(50)).all()
        return [{"fecha": _iso(a.fecha), "accion": a.accion, "entidad": a.entidad,
                 "entidad_id": a.entidad_id, "usuario_id": a.usuario_id,
                 "detalle": a.detalle} for a in filas]


# --------------------------------------------------------------------------- #
# registro por API (simula el sistema de visión externo)
# --------------------------------------------------------------------------- #
class InspeccionIn(BaseModel):
    angulo: float = Field(ge=0, le=360)
    id_receta: int
    id_lote: int | None = None
    id_batch: int | None = None
    fecha_hora: str | None = None
    observacion: str | None = None


@app.post("/api/inspecciones", status_code=201)
def registrar(datos: InspeccionIn, usuario: dict = Depends(requiere("integrador"))):
    with db.SesionLocal() as s:
        rec = s.get(db.Receta, datos.id_receta)
        if not rec:
            raise HTTPException(409, "La receta indicada no existe")
        estado = _evaluar(datos.angulo, float(rec.min_tol), float(rec.max_tol))
        insp = db.Inspeccion(receta_id=rec.id, lote_id=datos.id_lote, batch_id=datos.id_batch,
                             operador_id=usuario["uid"], angulo=datos.angulo,
                             limite_min=float(rec.min_tol), limite_max=float(rec.max_tol),
                             estado=estado, origen="api", confianza="ALTA",
                             observacion=datos.observacion)
        s.add(insp)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "inspecciones", insp.id,
                 detalle=f"Ángulo {datos.angulo}° → {estado}")
        s.commit()
        return {"id": insp.id, "estado": estado}


# --------------------------------------------------------------------------- #
# simulación de una ráfaga completa
# --------------------------------------------------------------------------- #
@app.post("/api/simular")
def simular(receta_id: int | None = None,
            velocidad: float = simulador.VELOCIDAD_NOMINAL,
            modo: str = "dentro",
            forzar_fuera: bool = False,
            usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    if modo not in ("dentro", "fuera", "aleatorio"):
        raise HTTPException(422, "Modo inválido: use dentro, fuera o aleatorio")
    if forzar_fuera:                       # compatibilidad con la versión anterior
        modo = "fuera"
    velocidad = max(simulador.VELOCIDAD_MIN, min(simulador.VELOCIDAD_MAX, float(velocidad)))

    with db.SesionLocal() as s:
        if receta_id:
            rec = s.get(db.Receta, receta_id)
        else:
            rec = s.scalar(select(db.Receta).where(db.Receta.activa.is_(True)))
        if not rec:
            raise HTTPException(409, "No hay recetas activas configuradas")
        lote = s.scalar(select(db.Lote).where(db.Lote.receta_id == rec.id)
                        .order_by(db.Lote.codigo.desc())) \
            or s.scalar(select(db.Lote).order_by(db.Lote.codigo.desc()))
        batch = s.scalar(select(db.Batch).where(db.Batch.lote_id == lote.id)) if lote else None
        usuario_id = usuario["uid"]

        ahora = datetime.now()
        sub = os.path.join(db.CAPTURAS_DIR, ahora.strftime("%Y-%m-%d"))
        os.makedirs(sub, exist_ok=True)
        n = len([d for d in os.listdir(sub) if d.startswith("Trigger_")]) + 1
        carpeta = os.path.join(sub, f"Trigger_{n:04d}_{ahora.strftime('%Y%m%d_%H%M%S')}")

    # El ángulo depende del centro de la receta, de la velocidad del tren
    # y del modo elegido (dentro / fuera / aleatorio).
    minimo, maximo = float(rec.min_tol), float(rec.max_tol)
    centro = (minimo + maximo) / 2
    desde, desviacion = simulador.calcular_objetivo(centro, maximo - minimo, velocidad, modo)

    t0 = time.perf_counter()
    info, resultado, angulo, estado = None, None, None, "sin_receta"
    # El pipeline puede no encontrar señal si el arco cae justo sobre una zona
    # ciega (p. ej. los 90°). Si ocurre, se recaptura con un pequeño ajuste.
    for intento, delta in enumerate((0, 12, -18)):
        try:
            info = simulador.generar_rafaga(carpeta, desde=round((desde + delta) % 360, 1))
            resultado = simulador.medir_angulo(carpeta)
        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(500, f"Error al analizar la ráfaga: {exc}")
        angulo = resultado.get("angulo")
        estado = _evaluar(angulo, minimo, maximo)
        if angulo is not None and (modo != "fuera" or estado == "rechazado"):
            break
    total_ms = int((time.perf_counter() - t0) * 1000)
    desviacion_real = round(float(angulo) - centro, 1) if angulo is not None else None
    imagen = resultado.get("imagen")
    if imagen and not os.path.isabs(imagen):
        imagen = os.path.abspath(imagen)

    # Si hay almacenamiento de objetos (MinIO/S3), se suben la ráfaga y el
    # diagnóstico; la base guarda solo la clave del objeto.
    clave_diagnostico = None
    if almacenamiento.activo():
        try:
            prefijo = f"capturas/{ahora:%Y-%m-%d}/{os.path.basename(carpeta)}"
            archivos = [(os.path.join(carpeta, n), f"{prefijo}/{n}")
                        for n in sorted(os.listdir(carpeta))
                        if os.path.isfile(os.path.join(carpeta, n))]
            almacenamiento.subir_carpeta(archivos)
            clave_diagnostico = f"{prefijo}/resultado_analisis.png"
        except Exception:
            traceback.print_exc()   # el registro no se pierde si falla la subida

    with db.SesionLocal() as s:
        insp = db.Inspeccion(
            fecha_hora=datetime.now(timezone.utc), receta_id=rec.id,
            lote_id=lote.id if lote else None, batch_id=batch.id if batch else None,
            operador_id=usuario_id, angulo=angulo, limite_min=minimo, limite_max=maximo,
            estado=estado, origen="camara_simulada", carpeta=carpeta, imagen=imagen,
            imagen_clave=clave_diagnostico,
            confianza=resultado.get("confianza"), duracion_ms=total_ms,
            frame_salida=resultado.get("frame_salida"),
            centro_x=(resultado.get("centro") or [None, None])[0],
            centro_y=(resultado.get("centro") or [None, None])[1],
            radio=resultado.get("radio"),
            motor=resultado.get("motor"),
            material=rec.materialidad,
            velocidad_m_min=velocidad,
            desviacion_deg=desviacion_real)
        s.add(insp)
        s.flush()
        if estado != "aprobado":
            s.add(db.Alarma(inspeccion_id=insp.id, tipo="fuera_tolerancia"
                            if estado == "rechazado" else "sin_receta",
                            severidad="alta" if estado == "rechazado" else "media",
                            mensaje=f"Ángulo {angulo}° fuera del rango {minimo}–{maximo}° "
                                    f"de la receta {rec.nombre}"))
        _auditar(s, usuario_id, "crear", "inspecciones", insp.id,
                 detalle=f"Ráfaga simulada · {info['frames']} frames · {velocidad} m/min · "
                         f"{total_ms} ms · ángulo {angulo}° → {estado}")
        s.commit()
        return {"inspeccion": _serializar(insp), "rafaga": info,
                "proceso": {"velocidad_m_min": velocidad, "modo": modo,
                            "desviacion_esperada": desviacion,
                            "desviacion_medida": desviacion_real,
                            "centro_receta": centro,
                            "velocidad_nominal": simulador.VELOCIDAD_NOMINAL,
                            "grados_por_m_min": simulador.DESVIACION_POR_M_MIN},
                "medicion": {k: resultado.get(k) for k in
                             ("angulo", "confianza", "frame_salida", "centro", "radio",
                              "motor", "total_frames")},
                "duracion_ms": total_ms}


@app.get("/")
def raiz():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/favicon.ico")
def favicon():
    return JSONResponse({}, status_code=204)
