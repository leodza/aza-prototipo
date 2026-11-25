"""Servidor del prototipo funcional — API REST + interfaz web.

Implementa el diseño del informe ES2: autenticación con JWT, RBAC verificado en
el servidor, registro de inspecciones por API, simulación de ráfagas con el
pipeline de visión real, auditoría y dashboard.

Ejecutar:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import json
import os
import random
import shutil
import threading
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from sqlalchemy import case

from . import almacenamiento, db, respaldos, simulador
from .seguridad import (MAX_INTENTOS, BLOQUEO_MIN, crear_jwt, hash_pin, hash_refresh,
                        iguales, leer_jwt, nuevo_refresh, validar_clave,
                        verificar_pin)

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
    finally:
        # No se deja nada en disco: los datos viven en la nube.
        shutil.rmtree(carpeta, ignore_errors=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.crear_tablas()
    with db.SesionLocal() as s:
        sembrar(s)
    threading.Thread(target=_precalentar, daemon=True).start()
    threading.Thread(target=_respaldo_automatico, daemon=True).start()
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
        db.Usuario(username="ldaza", nombre="Leonardo Daza", email="ldaza@aza.cl",
                   pin_hash=hash_pin("1234"),
                   rol_id=roles["operador"].id),
        db.Usuario(username="jsarabia", nombre="José Sarabia", email="jsarabia@aza.cl",
                   pin_hash=hash_pin("1234"),
                   rol_id=roles["supervisor"].id),
        db.Usuario(username="dparedes", nombre="Daniel Paredes", email="dparedes@aza.cl",
                   pin_hash=hash_pin("1234"),
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
            operador_id=azar.choice(usuarios[:3]).id, material=rec.materialidad,
            angulo=angulo, limite_min=min_t, limite_max=max_t, estado=estado,
            origen="historico_demo", confianza="ALTA", duracion_ms=azar.randint(1500, 2600)))
    s.commit()

    # alarmas de demostración para las inspecciones rechazadas del histórico
    with db.SesionLocal() as s:
        rechazadas = s.scalars(select(db.Inspeccion)
                               .where(db.Inspeccion.estado == "rechazado").limit(6)).all()
        for insp_demo in rechazadas:
            s.add(db.Alarma(inspeccion_id=insp_demo.id, tipo="fuera_tolerancia",
                            severidad="alta",
                            mensaje=f"Ángulo {float(insp_demo.angulo)}° fuera del rango "
                                    f"{float(insp_demo.limite_min)}–{float(insp_demo.limite_max)}°"))
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
    username: str          # usuario, correo o nombre completo
    pin: str


class RefreshIn(BaseModel):
    refresh: str


def _auditar(s, usuario_id, accion, entidad, entidad_id=None, ip=None,
             detalle=None, antes=None, despues=None):
    """Registra un evento en la bitácora.

    `detalle` admite texto o diccionario; `antes` y `despues` guardan el estado
    anterior y nuevo del registro. Por eso la columna es JSONB en PostgreSQL:
    el contenido es heterogéneo según la entidad auditada.
    """
    if isinstance(detalle, dict):
        payload = dict(detalle)
    elif detalle:
        payload = {"mensaje": detalle}
    else:
        payload = {}
    if antes is not None:
        payload["antes"] = antes
    if despues is not None:
        payload["despues"] = despues
    s.add(db.Auditoria(usuario_id=usuario_id, accion=accion, entidad=entidad,
                       entidad_id=entidad_id, ip=ip, detalle=payload or None))


def _config(s) -> dict:
    """Lee los parametros ajustables; si falta alguno usa el valor por defecto."""
    valores = {c: int(v) for c, (v, _) in db.CONFIG_DEFECTOS.items()}
    for fila in s.scalars(select(db.Configuracion)).all():
        try:
            valores[fila.clave] = int(fila.valor)
        except (TypeError, ValueError):
            pass
    return valores


@app.post("/api/auth/login")
def login(datos: LoginIn):
    with db.SesionLocal() as s:
        cfg = _config(s)
        ident = (datos.username or "").strip().lower()
        u = s.scalar(select(db.Usuario).where(or_(
            func.lower(db.Usuario.username) == ident,
            func.lower(db.Usuario.nombre) == ident,
            func.lower(func.coalesce(db.Usuario.email, "")) == ident)))
        if not u or not u.activo:
            raise HTTPException(401, "Usuario o contraseña incorrectos")

        ahora = datetime.now(timezone.utc)
        if u.bloqueado_hasta and u.bloqueado_hasta.replace(tzinfo=timezone.utc) > ahora:
            restante = int((u.bloqueado_hasta.replace(tzinfo=timezone.utc) - ahora).seconds / 60)
            raise HTTPException(423, f"Cuenta bloqueada por intentos fallidos. "
                                     f"Reintente en {restante + 1} minutos.")

        if not verificar_pin(datos.pin, u.pin_hash):
            u.intentos_fallidos += 1
            if u.intentos_fallidos >= cfg["max_intentos"]:
                u.bloqueado_hasta = ahora + timedelta(minutes=cfg["bloqueo_min"])
                u.intentos_fallidos = 0
                _auditar(s, u.id, "bloqueo", "usuarios", u.id,
                         detalle={"intentos": cfg["max_intentos"],
                                  "minutos": cfg["bloqueo_min"]})
            s.commit()
            raise HTTPException(401, "Usuario o contraseña incorrectos")

        u.intentos_fallidos = 0
        u.bloqueado_hasta = None
        cerradas = 0
        if cfg.get("sesion_unica", 1):
            for previa in s.scalars(select(db.Sesion).where(
                    db.Sesion.usuario_id == u.id,
                    db.Sesion.revocado.is_(False))).all():
                previa.revocado = True
                cerradas += 1
        claro, hashed, expira = nuevo_refresh()
        sesion = db.Sesion(usuario_id=u.id, refresh_hash=hashed, expira_en=expira)
        s.add(sesion)
        s.flush()
        _auditar(s, u.id, "login", "usuarios", u.id,
                   detalle={"usuario": u.username, "rol": u.rol.nombre,
                            "sesiones_previas_cerradas": cerradas})
        s.commit()

        permisos = _permisos_de(u)
        token = crear_jwt({"sub": u.username, "rol": u.rol.nombre, "sid": sesion.id,
                           "uid": u.id, "perm": permisos})
        return {
            "access": token,
            "refresh": claro,
            "usuario": {"username": u.username, "nombre": u.nombre, "rol": u.rol.nombre,
                        "permisos": permisos},
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


def requiere(*roles: str, permiso: str | None = None):
    def _dep(usuario: dict = Depends(usuario_actual)) -> dict:
        if permiso and permiso in (usuario.get("perm") or []):
            return usuario
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
           operador: str | None = None,
           orden: str = "lote",
           pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=200),
           usuario: dict = Depends(requiere("operador", "supervisor", "administrador", permiso="ver_historico"))):
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
        if operador:
            q = q.join(db.Usuario, db.Inspeccion.operador_id == db.Usuario.id).where(
                or_(db.Usuario.username == operador, db.Usuario.nombre == operador))
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
def crear_receta(datos: RecetaIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_recetas"))):
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
        _auditar(s, usuario["uid"], "crear", "recetas", r.id,
                   despues={"nombre": r.nombre, "min_tol": float(r.min_tol),
                            "max_tol": float(r.max_tol),
                            "material": r.materialidad})
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
def crear_material(datos: MaterialIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_recetas"))):
    with db.SesionLocal() as s:
        familia, tipo = datos.familia.strip().title(), datos.tipo.strip()
        if s.scalar(select(db.Material).where(db.Material.familia == familia,
                                              db.Material.tipo == tipo)):
            raise HTTPException(409, "Ese material ya existe en el catálogo")
        m = db.Material(familia=familia, tipo=tipo, descripcion=datos.descripcion)
        s.add(m)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "materiales", m.id,
                   despues={"familia": m.familia, "tipo": m.tipo})
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


@app.get("/api/configuracion")
def leer_configuracion(usuario: dict = Depends(requiere("administrador", permiso="gestionar_configuracion"))):
    with db.SesionLocal() as s:
        valores = _config(s)
        descripciones = {c: d for c, (_v, d) in db.CONFIG_DEFECTOS.items()}
        return {c: {"valor": valores[c], "descripcion": descripciones[c]} for c in valores}


class ConfigIn(BaseModel):
    max_intentos: int = Field(ge=3, le=20)
    bloqueo_min: int = Field(ge=1, le=1440)
    inactividad_min: int = Field(ge=1, le=240)
    sesion_unica: int = Field(ge=0, le=1)
    respaldo_horas: int = Field(default=24, ge=0, le=168)
    respaldo_max: int = Field(default=10, ge=1, le=50)


@app.put("/api/configuracion")
def guardar_configuracion(datos: ConfigIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_configuracion"))):
    with db.SesionLocal() as s:
        antes = _config(s)
        for clave, valor in datos.model_dump().items():
            fila = s.get(db.Configuracion, clave)
            if fila:
                fila.valor = str(valor)
            else:
                s.add(db.Configuracion(clave=clave, valor=str(valor)))
        _auditar(s, usuario["uid"], "actualizar", "configuracion", None,
                 antes=antes, despues=datos.model_dump())
        s.commit()
        return {"ok": True, "configuracion": _config(s)}


class OlvidoIn(BaseModel):
    identificador: str = Field(min_length=3, max_length=120)


@app.post("/api/auth/olvido")
def olvido(datos: OlvidoIn):
    """Registra una solicitud de restablecimiento para que la atienda el administrador."""
    with db.SesionLocal() as s:
        ident = datos.identificador.strip().lower()
        u = s.scalar(select(db.Usuario).where(or_(
            func.lower(db.Usuario.username) == ident,
            func.lower(db.Usuario.nombre) == ident,
            func.lower(func.coalesce(db.Usuario.email, "")) == ident)))
        s.add(db.SolicitudClave(usuario_id=u.id if u else None, identificador=ident))
        s.commit()
    return {"ok": True,
            "mensaje": "Solicitud enviada. El administrador debe restablecer la contraseña."}


# --------------------------------------------------------------------------- #
# respaldos
# --------------------------------------------------------------------------- #
def _podar_respaldos(maximo: int) -> int:
    lista = respaldos.listar()
    borrados = 0
    for viejo in lista[maximo:]:
        try:
            os.remove(respaldos.ruta_de(viejo["archivo"]))
            borrados += 1
        except OSError:
            pass
    return borrados


def _respaldo_automatico():
    """Hilo que crea un respaldo cuando se cumple el intervalo configurado."""
    time.sleep(45)                       # dejar arrancar el servidor
    while True:
        try:
            with db.SesionLocal() as s:
                cfg = _config(s)
            horas = cfg.get("respaldo_horas", 24)
            if horas > 0:
                lista = respaldos.listar()
                vencido = True
                if lista and lista[0].get("generado"):
                    try:
                        ultimo = datetime.fromisoformat(lista[0]["generado"])
                        vencido = (datetime.now(timezone.utc) - ultimo).total_seconds() >= horas * 3600
                    except ValueError:
                        vencido = True
                if vencido:
                    meta = respaldos.generar("automatico")
                    _podar_respaldos(cfg.get("respaldo_max", 10))
                    with db.SesionLocal() as s:
                        _auditar(s, None, "respaldo", "sistema", None,
                                 detalle={"archivo": meta["archivo"],
                                          "total": meta["total"]})
                        s.commit()
        except Exception:                # noqa: BLE001
            traceback.print_exc()
        time.sleep(300)


@app.get("/api/respaldos")
def listar_respaldos(usuario: dict = Depends(requiere("administrador", permiso="gestionar_respaldos"))):
    with db.SesionLocal() as s:
        cfg = _config(s)
    return {"respaldos": respaldos.listar(),
            "configuracion": {"horas": cfg.get("respaldo_horas"),
                              "maximo": cfg.get("respaldo_max")}}


@app.post("/api/respaldos", status_code=201)
def crear_respaldo(usuario: dict = Depends(requiere("administrador", permiso="gestionar_respaldos"))):
    meta = respaldos.generar(f"manual-{usuario.get('sub') or usuario.get('uid')}")
    with db.SesionLocal() as s:
        cfg = _config(s)
    _podar_respaldos(cfg.get("respaldo_max", 10))
    with db.SesionLocal() as s:
        _auditar(s, usuario["uid"], "respaldo", "sistema", None,
                 detalle={"archivo": meta["archivo"], "total": meta["total"]})
        s.commit()
    return meta


class RestaurarIn(BaseModel):
    archivo: str


@app.post("/api/respaldos/restaurar")
def restaurar_respaldo(datos: RestaurarIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_respaldos"))):
    try:
        contenido = respaldos.leer(datos.archivo)
        insertados = respaldos.restaurar(contenido)
    except FileNotFoundError:
        raise HTTPException(404, "No existe ese respaldo")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with db.SesionLocal() as s:
        _auditar(s, usuario["uid"], "restaurar", "sistema", None,
                 detalle={"archivo": datos.archivo, "insertados": insertados})
        s.commit()
    return {"ok": True, "insertados": insertados}


class ImportarIn(BaseModel):
    nombre: str = "importado"
    respaldo: dict


@app.post("/api/respaldos/importar", status_code=201)
def importar_respaldo(datos: ImportarIn,
                      usuario: dict = Depends(requiere("administrador",
                                                       permiso="gestionar_respaldos"))):
    """Guarda un respaldo que viene de otro equipo para poder restaurarlo."""
    contenido = datos.respaldo or {}
    meta = contenido.get("meta") or {}
    if not isinstance(contenido.get("datos"), dict):
        raise HTTPException(422, "El archivo no tiene el formato de un respaldo de AZA")
    if meta.get("version") != respaldos.VERSION:
        raise HTTPException(422, "La versión del respaldo no es compatible")
    faltan = [tabla for tabla in respaldos.MODELOS if tabla not in contenido["datos"]]
    if faltan:
        raise HTTPException(422, "Al respaldo le faltan tablas: " + ", ".join(faltan))

    guardado = respaldos.guardar_externo(contenido, datos.nombre)
    with db.SesionLocal() as s:
        _auditar(s, usuario["uid"], "importar", "sistema", None,
                 detalle={"archivo": guardado["archivo"], "total": guardado["total"]})
        s.commit()
    return guardado


class CompararIn(BaseModel):
    a: str
    b: str


@app.post("/api/respaldos/comparar")
def comparar_respaldos(datos: CompararIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_respaldos"))):
    try:
        return respaldos.comparar(datos.a, datos.b)
    except FileNotFoundError:
        raise HTTPException(404, "Falta uno de los respaldos a comparar")


@app.get("/api/respaldos/{archivo}")
def descargar_respaldo(archivo: str, usuario: dict = Depends(requiere("administrador", permiso="gestionar_respaldos"))):
    ruta = respaldos.ruta_de(archivo)
    if not os.path.exists(ruta):
        raise HTTPException(404, "No existe ese respaldo")
    return FileResponse(ruta, media_type="application/json", filename=archivo)


# --------------------------------------------------------------------------- #
# estadísticas por operador
# --------------------------------------------------------------------------- #
@app.get("/api/estadisticas/operadores")
def estadisticas_operadores(desde: str | None = None, hasta: str | None = None,
                            usuario: dict = Depends(requiere("supervisor", "administrador", permiso="ver_estadisticas"))):
    with db.SesionLocal() as s:
        aprobadas = func.sum(case((db.Inspeccion.estado == "aprobado", 1), else_=0))
        rechazadas = func.sum(case((db.Inspeccion.estado == "rechazado", 1), else_=0))
        sin_receta = func.sum(case((db.Inspeccion.estado == "sin_receta", 1), else_=0))
        q = (select(db.Usuario.id, db.Usuario.nombre, db.Usuario.username,
                    func.count(db.Inspeccion.id).label("total"),
                    aprobadas.label("aprobadas"), rechazadas.label("rechazadas"),
                    sin_receta.label("sin_receta"),
                    func.avg(db.Inspeccion.angulo).label("angulo"),
                    func.avg(db.Inspeccion.duracion_ms).label("duracion"))
             .join(db.Inspeccion, db.Inspeccion.operador_id == db.Usuario.id)
             .group_by(db.Usuario.id, db.Usuario.nombre, db.Usuario.username))
        if desde:
            q = q.where(db.Inspeccion.fecha_hora >= _a_utc_naive(datetime.fromisoformat(desde)))
        if hasta:
            q = q.where(db.Inspeccion.fecha_hora
                        < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
        filas = s.execute(q).all()

    salida = []
    for f in filas:
        total = int(f.total or 0)
        aprob = int(f.aprobadas or 0)
        rech = int(f.rechazadas or 0)
        salida.append({
            "id": f.id, "nombre": f.nombre, "username": f.username,
            "total": total, "aprobadas": aprob, "rechazadas": rech,
            "sin_receta": int(f.sin_receta or 0),
            "aprobacion_pct": round(100 * aprob / total, 1) if total else 0,
            "angulo_medio": round(float(f.angulo), 1) if f.angulo is not None else None,
            "duracion_media_ms": int(f.duracion) if f.duracion else None,
        })
    salida.sort(key=lambda x: (-x["aprobacion_pct"], -x["total"]))
    return salida


@app.get("/api/permisos")
def catalogo_permisos(usuario: dict = Depends(requiere("administrador"))):
    return [{"clave": k, "descripcion": v} for k, v in CATALOGO_PERMISOS.items()]


class PermisosIn(BaseModel):
    permisos: list[str] = []


@app.put("/api/usuarios/{id}/permisos")
def guardar_permisos(id: int, datos: PermisosIn,
                     usuario: dict = Depends(requiere("administrador", permiso="gestionar_usuarios"))):
    with db.SesionLocal() as s:
        u = s.get(db.Usuario, id)
        if not u:
            raise HTTPException(404, "Usuario no encontrado")
        validos = [p for p in datos.permisos if p in CATALOGO_PERMISOS]
        antes = _permisos_de(u)
        u.permisos = json.dumps(sorted(set(validos)))
        _auditar(s, usuario["uid"], "actualizar", "usuarios", u.id,
                 antes={"permisos": antes}, despues={"permisos": validos})
        s.commit()
        return {"id": u.id, "permisos": validos}


CATALOGO_PERMISOS = {
    "simular": "Disparar inspecciones en el simulador",
    "ver_historico": "Consultar el histórico completo",
    "ver_auditoria": "Ver la bitácora de auditoría",
    "ver_estadisticas": "Ver estadísticas y comparar operadores",
    "editar_alarmas": "Revisar y cerrar alarmas",
    "gestionar_recetas": "Crear recetas y materiales",
    "gestionar_usuarios": "Crear, editar y dar de baja usuarios",
    "gestionar_respaldos": "Crear, restaurar y comparar respaldos",
    "gestionar_configuracion": "Cambiar los parámetros del sistema",
}


def _permisos_de(u) -> list[str]:
    try:
        return [p for p in json.loads(u.permisos or "[]") if p in CATALOGO_PERMISOS]
    except Exception:                    # noqa: BLE001
        return []


@app.get("/api/estadisticas/operador/{username}")
def ficha_operador(username: str, desde: str | None = None, hasta: str | None = None,
                   usuario: dict = Depends(requiere("supervisor", "administrador",
                                                    permiso="ver_estadisticas"))):
    """Ficha completa de un operador: métricas, recetas, evolución y últimos registros."""
    with db.SesionLocal() as s:
        u = s.scalar(select(db.Usuario).where(db.Usuario.username == username))
        if not u:
            raise HTTPException(404, f"No existe el operador {username}")

        def rango(q):
            if desde:
                q = q.where(db.Inspeccion.fecha_hora
                            >= _a_utc_naive(datetime.fromisoformat(desde)))
            if hasta:
                q = q.where(db.Inspeccion.fecha_hora
                            < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
            return q

        base = rango(select(db.Inspeccion).where(db.Inspeccion.operador_id == u.id))
        inspecciones = s.scalars(base).all()

        total = len(inspecciones)
        aprob = sum(1 for i in inspecciones if i.estado == "aprobado")
        rech = sum(1 for i in inspecciones if i.estado == "rechazado")
        sin = sum(1 for i in inspecciones if i.estado == "sin_receta")
        angulos = [float(i.angulo) for i in inspecciones if i.angulo is not None]
        duraciones = [i.duracion_ms for i in inspecciones if i.duracion_ms]

        # recetas usadas
        por_receta = {}
        for i in inspecciones:
            nombre = i.receta.nombre if i.receta else "Sin receta"
            fila = por_receta.setdefault(nombre, {"receta": nombre, "total": 0, "aprobadas": 0})
            fila["total"] += 1
            if i.estado == "aprobado":
                fila["aprobadas"] += 1
        recetas = []
        for f in sorted(por_receta.values(), key=lambda x: -x["total"]):
            f["pct"] = round(100 * f["aprobadas"] / f["total"], 1) if f["total"] else 0
            recetas.append(f)

        # lotes
        por_lote = {}
        for i in inspecciones:
            clave = i.lote.codigo if i.lote else "—"
            por_lote[clave] = por_lote.get(clave, 0) + 1
        lotes = [{"lote": k, "total": v}
                 for k, v in sorted(por_lote.items(), key=lambda x: -x[1])]

        # evolución por semana
        semanas = {}
        for i in inspecciones:
            fecha = i.fecha_hora
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            fecha = fecha.astimezone()
            iso = fecha.isocalendar()
            clave = (iso[0], iso[1])
            fila = semanas.setdefault(clave, {"etiqueta": f"S{iso[1]}/{str(iso[0])[2:]}",
                                              "total": 0, "aprobadas": 0})
            fila["total"] += 1
            if i.estado == "aprobado":
                fila["aprobadas"] += 1
        evolucion = [semanas[k] for k in sorted(semanas)][-12:]
        for f in evolucion:
            f["pct"] = round(100 * f["aprobadas"] / f["total"], 1) if f["total"] else 0

        # últimas inspecciones
        recientes = sorted(inspecciones, key=lambda i: i.fecha_hora, reverse=True)[:10]
        ultimas = [{
            "id": i.id, "fecha_hora": _iso(i.fecha_hora),
            "receta": i.receta.nombre if i.receta else None,
            "lote": i.lote.codigo if i.lote else None,
            "batch": f"B{i.batch.numero}" if i.batch else None,
            "angulo": float(i.angulo) if i.angulo is not None else None,
            "estado": i.estado,
        } for i in recientes]

        # alarmas de sus inspecciones
        alarmas = s.execute(
            select(func.count(db.Alarma.id),
                   func.sum(case((db.Alarma.estado == "solucionada", 1), else_=0)))
            .join(db.Inspeccion, db.Alarma.inspeccion_id == db.Inspeccion.id)
            .where(db.Inspeccion.operador_id == u.id)).one()

        # ranking entre operadores con datos
        q_rank = (select(db.Usuario.username,
                         func.count(db.Inspeccion.id).label("total"),
                         func.sum(case((db.Inspeccion.estado == "aprobado", 1), else_=0)).label("ok"))
                  .join(db.Inspeccion, db.Inspeccion.operador_id == db.Usuario.id)
                  .group_by(db.Usuario.username))
        ranking = s.execute(rango(q_rank)).all()
        tabla = [{"username": r.username, "total": int(r.total),
                  "pct": round(100 * int(r.ok or 0) / int(r.total), 1)}
                 for r in ranking if r.total]
        tabla.sort(key=lambda x: (-x["pct"], -x["total"]))
        puesto = next((n + 1 for n, x in enumerate(tabla) if x["username"] == username), None)

        return {
            "usuario": {"username": u.username, "nombre": u.nombre, "rol": u.rol.nombre,
                        "email": u.email, "activo": u.activo,
                        "permisos": _permisos_de(u)},
            "metricas": {
                "total": total, "aprobadas": aprob, "rechazadas": rech, "sin_receta": sin,
                "aprobacion_pct": round(100 * aprob / total, 1) if total else 0,
                "angulo_medio": round(sum(angulos) / len(angulos), 1) if angulos else None,
                "angulo_min": round(min(angulos), 1) if angulos else None,
                "angulo_max": round(max(angulos), 1) if angulos else None,
                "duracion_media_ms": int(sum(duraciones) / len(duraciones)) if duraciones else None,
            },
            "recetas": recetas,
            "lotes": lotes[:8],
            "evolucion": evolucion,
            "ultimas": ultimas,
            "alarmas": {"total": int(alarmas[0] or 0), "solucionadas": int(alarmas[1] or 0)},
            "ranking": {"puesto": puesto, "total": len(tabla), "tabla": tabla},
        }


@app.get("/api/estadisticas/periodos")
def informe_periodos(granularidad: str = "semana",
                     desde: str | None = None, hasta: str | None = None,
                     usuario: dict = Depends(requiere("supervisor", "administrador",
                                                      permiso="ver_estadisticas"))):
    """Agrupa las inspecciones por semana o mes y compara con el período anterior."""
    if granularidad not in ("semana", "mes"):
        raise HTTPException(422, "La granularidad debe ser «semana» o «mes»")
    fin = datetime.fromisoformat(hasta) if hasta else datetime.now()
    inicio = datetime.fromisoformat(desde) if desde else (fin - timedelta(days=84))

    def tramo(fecha: datetime) -> tuple:
        if granularidad == "semana":
            iso = fecha.isocalendar()
            clave = (iso[0], iso[1])
            etiqueta = f"Semana {iso[1]} · {iso[0]}"
        else:
            clave = (fecha.year, fecha.month)
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                     "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            etiqueta = f"{meses[fecha.month - 1].capitalize()} {fecha.year}"
        return clave, etiqueta

    def recolectar(ini: datetime, fin2: datetime) -> dict:
        with db.SesionLocal() as s:
            filas = s.scalars(select(db.Inspeccion).where(
                db.Inspeccion.fecha_hora >= _a_utc_naive(ini),
                db.Inspeccion.fecha_hora < _a_utc_naive(fin2))).all()
        cubos = {}
        for f in filas:
            fecha = f.fecha_hora
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            fecha = fecha.astimezone()
            clave, etiqueta = tramo(fecha)
            cubo = cubos.setdefault(clave, {"clave": list(clave), "etiqueta": etiqueta,
                                            "total": 0, "aprobadas": 0, "rechazadas": 0,
                                            "sin_receta": 0, "angulos": [], "desde": fecha,
                                            "hasta": fecha})
            cubo["total"] += 1
            cubo["desde"] = min(cubo["desde"], fecha)
            cubo["hasta"] = max(cubo["hasta"], fecha)
            if f.estado == "aprobado":
                cubo["aprobadas"] += 1
            elif f.estado == "rechazado":
                cubo["rechazadas"] += 1
            else:
                cubo["sin_receta"] += 1
            if f.angulo is not None:
                cubo["angulos"].append(float(f.angulo))
        salida = []
        for clave in sorted(cubos):
            c = cubos[clave]
            c["aprobacion_pct"] = round(100 * c["aprobadas"] / c["total"], 1) if c["total"] else 0
            c["angulo_medio"] = round(sum(c["angulos"]) / len(c["angulos"]), 1) if c["angulos"] else None
            c["desde"] = c["desde"].strftime("%Y-%m-%d")
            c["hasta"] = c["hasta"].strftime("%Y-%m-%d")
            c.pop("angulos", None)
            salida.append(c)
        return {"cubos": salida,
                "totales": {"total": len(filas),
                            "aprobadas": sum(1 for f in filas if f.estado == "aprobado"),
                            "rechazadas": sum(1 for f in filas if f.estado == "rechazado")}}

    actual = recolectar(inicio, fin)
    largo = (fin - inicio).days or 1
    previo = recolectar(inicio - timedelta(days=largo), inicio)

    def variacion(ahora: float, antes: float) -> float | None:
        if not antes:
            return None
        return round(100 * (ahora - antes) / antes, 1)

    tot_a, tot_p = actual["totales"], previo["totales"]
    return {
        "granularidad": granularidad,
        "rango": {"desde": inicio.strftime("%Y-%m-%d"), "hasta": fin.strftime("%Y-%m-%d")},
        "periodos": actual["cubos"],
        "totales": tot_a,
        "anterior": {
            "rango": {"desde": (inicio - timedelta(days=largo)).strftime("%Y-%m-%d"),
                      "hasta": inicio.strftime("%Y-%m-%d")},
            "totales": tot_p,
            "aprobacion_pct": round(100 * tot_p["aprobadas"] / tot_p["total"], 1) if tot_p["total"] else 0,
        },
        "variacion": {
            "total": variacion(tot_a["total"], tot_p["total"]),
            "aprobadas": variacion(tot_a["aprobadas"], tot_p["aprobadas"]),
            "rechazadas": variacion(tot_a["rechazadas"], tot_p["rechazadas"]),
        },
        "aprobacion_pct": round(100 * tot_a["aprobadas"] / tot_a["total"], 1) if tot_a["total"] else 0,
    }


@app.get("/api/estadisticas/comparar")
def comparar_operadores(a: str, b: str, desde: str | None = None, hasta: str | None = None,
                        usuario: dict = Depends(requiere("supervisor", "administrador",
                                                         permiso="ver_estadisticas"))):
    """Compara dos operadores: volumen, calidad, recetas usadas y consistencia."""
    def perfil(s, username: str) -> dict:
        u = s.scalar(select(db.Usuario).where(db.Usuario.username == username))
        if not u:
            raise HTTPException(404, f"No existe el operador {username}")
        q = (select(func.count(db.Inspeccion.id),
                    func.sum(case((db.Inspeccion.estado == "aprobado", 1), else_=0)),
                    func.sum(case((db.Inspeccion.estado == "rechazado", 1), else_=0)),
                    func.sum(case((db.Inspeccion.estado == "sin_receta", 1), else_=0)),
                    func.avg(db.Inspeccion.angulo), func.min(db.Inspeccion.angulo),
                    func.max(db.Inspeccion.angulo), func.avg(db.Inspeccion.duracion_ms))
             .where(db.Inspeccion.operador_id == u.id))
        if desde:
            q = q.where(db.Inspeccion.fecha_hora >= _a_utc_naive(datetime.fromisoformat(desde)))
        if hasta:
            q = q.where(db.Inspeccion.fecha_hora
                        < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
        total, aprob, rech, sin, ang, amin, amax, dur = s.execute(q).one()

        qr = (select(db.Receta.nombre, func.count(db.Inspeccion.id),
                     func.sum(case((db.Inspeccion.estado == "aprobado", 1), else_=0)))
              .join(db.Inspeccion, db.Inspeccion.receta_id == db.Receta.id)
              .where(db.Inspeccion.operador_id == u.id)
              .group_by(db.Receta.nombre)
              .order_by(func.count(db.Inspeccion.id).desc()))
        if desde:
            qr = qr.where(db.Inspeccion.fecha_hora >= _a_utc_naive(datetime.fromisoformat(desde)))
        if hasta:
            qr = qr.where(db.Inspeccion.fecha_hora
                          < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
        recetas = [{"receta": r[0], "total": int(r[1]), "aprobadas": int(r[2] or 0),
                    "pct": round(100 * int(r[2] or 0) / int(r[1]), 1) if r[1] else 0}
                   for r in s.execute(qr).all()]

        ql = (select(db.Lote.codigo, func.count(db.Inspeccion.id))
              .join(db.Inspeccion, db.Inspeccion.lote_id == db.Lote.id)
              .where(db.Inspeccion.operador_id == u.id)
              .group_by(db.Lote.codigo))
        if desde:
            ql = ql.where(db.Inspeccion.fecha_hora >= _a_utc_naive(datetime.fromisoformat(desde)))
        if hasta:
            ql = ql.where(db.Inspeccion.fecha_hora
                          < _a_utc_naive(datetime.fromisoformat(hasta) + timedelta(days=1)))
        lotes = [{"lote": r[0], "total": int(r[1])} for r in s.execute(ql).all()]

        total = int(total or 0)
        aprob = int(aprob or 0)
        return {
            "username": u.username, "nombre": u.nombre, "rol": u.rol.nombre,
            "total": total, "aprobadas": aprob,
            "rechazadas": int(rech or 0), "sin_receta": int(sin or 0),
            "aprobacion_pct": round(100 * aprob / total, 1) if total else 0,
            "angulo_medio": round(float(ang), 1) if ang is not None else None,
            "angulo_min": round(float(amin), 1) if amin is not None else None,
            "angulo_max": round(float(amax), 1) if amax is not None else None,
            "duracion_media_ms": int(dur) if dur else None,
            "recetas": recetas, "lotes": lotes,
        }

    with db.SesionLocal() as s:
        uno, otro = perfil(s, a), perfil(s, b)

    def mejor(clave, mayor=True):
        va, vb = uno.get(clave) or 0, otro.get(clave) or 0
        if va == vb:
            return "empate"
        return a if (va > vb) == mayor else b

    comunes = sorted({r["receta"] for r in uno["recetas"]} & {r["receta"] for r in otro["recetas"]})
    solo_a = sorted({r["receta"] for r in uno["recetas"]} - {r["receta"] for r in otro["recetas"]})
    solo_b = sorted({r["receta"] for r in otro["recetas"]} - {r["receta"] for r in uno["recetas"]})

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "operadores": [uno, otro],
        "veredicto": {
            "volumen": mejor("total"),
            "calidad": mejor("aprobacion_pct"),
            "velocidad": mejor("duracion_media_ms", mayor=False),
        },
        "recetas": {"comunes": comunes, "solo_a": solo_a, "solo_b": solo_b},
    }


def _detalle_legible(detalle) -> str:
    """Convierte el JSON de la bitacora en una línea que se pueda leer."""
    if not detalle:
        return ""
    if isinstance(detalle, str):
        return detalle
    partes = []
    if detalle.get("mensaje"):
        partes.append(str(detalle["mensaje"]))
    if detalle.get("antes") is not None:
        partes.append("antes: " + json.dumps(detalle["antes"], ensure_ascii=False))
    if detalle.get("despues") is not None:
        partes.append("después: " + json.dumps(detalle["despues"], ensure_ascii=False))
    for clave, valor in detalle.items():
        if clave not in ("mensaje", "antes", "despues"):
            partes.append(f"{clave}: {valor}")
    return " · ".join(partes)


@app.get("/api/solicitudes")
def solicitudes(usuario: dict = Depends(requiere("administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.SolicitudClave)
                          .order_by(db.SolicitudClave.creada_en.desc()).limit(50)).all()
        return [{"id": f.id, "identificador": f.identificador, "estado": f.estado,
                 "creada_en": _iso(f.creada_en), "atendida_en": _iso(f.atendida_en),
                 "usuario": f.usuario.nombre if f.usuario else None,
                 "username": f.usuario.username if f.usuario else None,
                 "nota": f.nota} for f in filas]


class ResolverIn(BaseModel):
    nueva_clave: str = Field(min_length=8, max_length=64)
    nota: str | None = None


@app.post("/api/solicitudes/{id}/resolver")
def resolver_solicitud(id: int, datos: ResolverIn,
                       usuario: dict = Depends(requiere("administrador"))):
    faltan = validar_clave(datos.nueva_clave)
    if faltan:
        raise HTTPException(422, "La contraseña debe tener " + ", ".join(faltan))
    with db.SesionLocal() as s:
        sol = s.get(db.SolicitudClave, id)
        if not sol:
            raise HTTPException(404, "Solicitud no encontrada")
        if sol.estado != "pendiente":
            raise HTTPException(409, "Esa solicitud ya fue atendida")
        if not sol.usuario_id:
            raise HTTPException(422, "La solicitud no identifica a un usuario existente")
        u = s.get(db.Usuario, sol.usuario_id)
        u.pin_hash = hash_pin(datos.nueva_clave)
        u.intentos_fallidos = 0
        u.bloqueado_hasta = None
        u.activo = True
        sol.estado = "atendida"
        sol.nota = datos.nota
        sol.atendida_en = datetime.now(timezone.utc)
        _auditar(s, usuario["uid"], "reset", "usuarios", u.id,
                 detalle={"solicitud": sol.id, "usuario": u.username})
        s.commit()
        return {"ok": True, "usuario": u.username}


# --------------------------------------------------------------------------- #
# alarmas con flujo de revisión
# --------------------------------------------------------------------------- #
@app.get("/api/alarmas")
def alarmas(usuario: dict = Depends(requiere("operador", "supervisor", "administrador"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Alarma)
                          .order_by(db.Alarma.creada_en.desc()).limit(120)).all()
        salida = []
        for a in filas:
            insp = s.get(db.Inspeccion, a.inspeccion_id) if a.inspeccion_id else None
            salida.append({
                "id": a.id, "tipo": a.tipo, "severidad": a.severidad,
                "mensaje": a.mensaje, "estado": a.estado, "solucion": a.solucion,
                "creada_en": _iso(a.creada_en), "resuelto_en": _iso(a.resuelto_en),
                "inspeccion_id": a.inspeccion_id,
                "angulo": float(insp.angulo) if insp and insp.angulo is not None else None,
                "receta": insp.receta.nombre if insp and insp.receta else None,
                "lote": insp.lote.codigo if insp and insp.lote else None,
                "batch": insp.batch.numero if insp and insp.batch else None,
                "operador": insp.operador.nombre if insp and insp.operador else None,
            })
        return salida


class AlarmaIn(BaseModel):
    estado: str
    solucion: str | None = None


@app.patch("/api/alarmas/{id}")
def revisar_alarma(id: int, datos: AlarmaIn,
                   usuario: dict = Depends(requiere("supervisor", "administrador", permiso="editar_alarmas"))):
    if datos.estado not in ("pendiente", "en_revision", "solucionada"):
        raise HTTPException(422, "Estado inválido: pendiente, en_revision o solucionada")
    if datos.estado == "solucionada" and not (datos.solucion or "").strip():
        raise HTTPException(422, "Para dar por solucionada una alarma indique la solución")
    with db.SesionLocal() as s:
        a = s.get(db.Alarma, id)
        if not a:
            raise HTTPException(404, "Alarma no encontrada")
        antes = {"estado": a.estado}
        a.estado = datos.estado
        if datos.solucion is not None:
            a.solucion = datos.solucion.strip() or None
        if datos.estado == "solucionada":
            a.resuelto_por = usuario["uid"]
            a.resuelto_en = datetime.now(timezone.utc)
            a.notificada = True
        _auditar(s, usuario["uid"], "actualizar", "alarmas", a.id,
                 antes=antes, despues={"estado": a.estado, "solucion": a.solucion})
        s.commit()
        return {"id": a.id, "estado": a.estado}


@app.get("/api/usuarios")
def usuarios(usuario: dict = Depends(requiere("administrador", permiso="gestionar_usuarios"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Usuario).order_by(db.Usuario.username)).all()
        ahora_utc = datetime.now(timezone.utc)
        salida = []
        for u in filas:
            bloqueado = bool(u.bloqueado_hasta and
                             u.bloqueado_hasta.replace(tzinfo=timezone.utc) > ahora_utc)
            salida.append({"id": u.id, "username": u.username, "nombre": u.nombre,
                           "email": u.email, "rol": u.rol.nombre, "activo": u.activo,
                           "bloqueado": bloqueado, "permisos": _permisos_de(u)})
        return salida


class UsuarioIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=3, max_length=80)
    rol: str
    pin: str = Field(min_length=8, max_length=64)
    email: str | None = None


def _admins_activos(s, excluir: int | None = None) -> int:
    q = select(func.count()).select_from(db.Usuario).join(db.Rol).where(
        db.Rol.nombre == "administrador", db.Usuario.activo.is_(True))
    if excluir:
        q = q.where(db.Usuario.id != excluir)
    return s.scalar(q) or 0


@app.post("/api/usuarios", status_code=201)
def crear_usuario(datos: UsuarioIn, usuario: dict = Depends(requiere("administrador", permiso="gestionar_usuarios"))):
    with db.SesionLocal() as s:
        rol = s.scalar(select(db.Rol).where(db.Rol.nombre == datos.rol.strip().lower()))
        if not rol:
            raise HTTPException(422, "Rol inválido: use operador, supervisor o administrador")
        nombre_usuario = datos.username.strip().lower()
        if s.scalar(select(db.Usuario).where(db.Usuario.username == nombre_usuario)):
            raise HTTPException(409, "Ese nombre de usuario ya existe")
        faltan = validar_clave(datos.pin)
        if faltan:
            raise HTTPException(422, "La contraseña debe tener " + ", ".join(faltan))
        email = (datos.email or "").strip().lower() or None
        if email and s.scalar(select(db.Usuario).where(db.Usuario.email == email)):
            raise HTTPException(409, "Ese correo ya está registrado")
        u = db.Usuario(username=nombre_usuario, nombre=datos.nombre.strip(),
                       email=email, pin_hash=hash_pin(datos.pin), rol_id=rol.id)
        s.add(u)
        s.flush()
        _auditar(s, usuario["uid"], "crear", "usuarios", u.id,
                   despues={"usuario": u.username, "rol": u.rol.nombre,
                            "activo": u.activo})
        s.commit()
        return {"id": u.id, "username": u.username, "rol": rol.nombre}


class ActivoIn(BaseModel):
    activo: bool


@app.patch("/api/usuarios/{id}")
def activar_usuario(id: int, datos: ActivoIn | None = None,
                    activo: bool | None = None,
                    usuario: dict = Depends(requiere("administrador", permiso="gestionar_usuarios"))):
    with db.SesionLocal() as s:
        valor = datos.activo if datos is not None else activo
        if valor is None:
            raise HTTPException(422, "Indique si la cuenta debe quedar activa")
        activo = valor
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
                   antes={"activo": not activo},
                   despues={"activo": activo},
                   detalle={"usuario": u.username})
        s.commit()
        return {"id": u.id, "activo": u.activo}


@app.delete("/api/usuarios/{id}", status_code=200)
def borrar_usuario(id: int, usuario: dict = Depends(requiere("administrador", permiso="gestionar_usuarios"))):
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
                   antes={"activo": True}, despues={"activo": False},
                   detalle={"usuario": u.username})
        s.commit()
        return {"id": u.id, "activo": False,
                "mensaje": "Cuenta desactivada; sus registros históricos se conservan"}


@app.get("/api/auditoria")
def auditoria(usuario: dict = Depends(requiere("supervisor", "administrador", permiso="ver_auditoria"))):
    with db.SesionLocal() as s:
        filas = s.scalars(select(db.Auditoria).order_by(db.Auditoria.fecha.desc()).limit(50)).all()
        return [{"fecha": _iso(a.fecha), "accion": a.accion, "entidad": a.entidad,
                 "entidad_id": a.entidad_id, "usuario_id": a.usuario_id,
                 "detalle": a.detalle,
                 "detalle_texto": _detalle_legible(a.detalle)} for a in filas]


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
            usuario: dict = Depends(requiere("operador", "supervisor", "administrador", permiso="simular"))):
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
            # La ruta en el bucket se ordena por lote y batch para que la
            # trazabilidad sea visible también en el almacenamiento.
            carpeta_lote = (f"lotes/{lote.codigo}/B{batch.numero}"
                            if lote and batch else f"capturas/{ahora:%Y-%m-%d}")
            prefijo = f"{carpeta_lote}/{os.path.basename(carpeta)}"
            archivos = [(os.path.join(carpeta, n), f"{prefijo}/{n}")
                        for n in sorted(os.listdir(carpeta))
                        if os.path.isfile(os.path.join(carpeta, n))]
            almacenamiento.subir_carpeta(archivos)
            clave_diagnostico = f"{prefijo}/resultado_analisis.png"
            # Todo queda en la nube: se elimina la copia local de trabajo.
            shutil.rmtree(carpeta, ignore_errors=True)
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
                 detalle={"frames": info["frames"], "duracion_ms": total_ms,
                          "velocidad_m_min": velocidad, "modo": modo},
                 despues={"angulo": angulo, "estado": estado,
                          "receta": rec.nombre, "material": rec.materialidad,
                          "lote": lote.codigo if lote else None,
                          "batch": batch.numero if batch else None,
                          "objeto": clave_diagnostico})
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
