"""Pruebas del prototipo funcional (pytest).

Cubren autenticación, bloqueo de cuenta, RBAC, registro por API, consultas,
inmutabilidad de límites y una simulación completa de ráfaga.
"""
import os
import tempfile

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["AZA_DB_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["AZA_CAPTURAS"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _login(c, usuario="ldaza", pin="1234"):
    r = c.post("/api/auth/login", json={"username": usuario, "pin": pin})
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# autenticación
# --------------------------------------------------------------------------- #
def test_login_correcto(cliente):
    d = _login(cliente)
    assert d["usuario"]["rol"] == "operador"
    assert d["access"].count(".") == 2          # JWT de tres segmentos
    assert len(d["refresh"]) > 20


def test_login_pin_incorrecto(cliente):
    r = cliente.post("/api/auth/login", json={"username": "ldaza", "pin": "9999"})
    assert r.status_code == 401


def test_bloqueo_tras_cinco_intentos(cliente):
    for _ in range(5):
        cliente.post("/api/auth/login", json={"username": "jsarabia", "pin": "0000"})
    r = cliente.post("/api/auth/login", json={"username": "jsarabia", "pin": "1234"})
    assert r.status_code == 423                    # cuenta bloqueada
    # se desbloquea para el resto de las pruebas
    with db.SesionLocal() as s:
        u = s.query(db.Usuario).filter_by(username="jsarabia").one()
        u.bloqueado_hasta = None
        u.intentos_fallidos = 0
        s.commit()


def test_token_invalido(cliente):
    r = cliente.get("/api/health")
    assert r.status_code == 200
    r = cliente.get("/api/dashboard", headers={"Authorization": "Bearer firma.falsa.token"})
    assert r.status_code == 401


def test_refresh_rota_y_revoca(cliente):
    d = _login(cliente)
    r = cliente.post("/api/auth/refresh", json={"refresh": d["refresh"]})
    assert r.status_code == 200
    nuevo = r.json()
    assert nuevo["refresh"] != d["refresh"]
    # el token de refresco anterior ya no sirve
    r = cliente.post("/api/auth/refresh", json={"refresh": d["refresh"]})
    assert r.status_code == 401


def test_logout_revoca_la_sesion(cliente):
    d = _login(cliente)
    cab = {"Authorization": "Bearer " + d["access"]}
    assert cliente.get("/api/auth/me", headers=cab).status_code == 200
    assert cliente.post("/api/auth/logout", headers=cab).status_code == 200
    assert cliente.get("/api/auth/me", headers=cab).status_code == 401


# --------------------------------------------------------------------------- #
# autorización (RBAC)
# --------------------------------------------------------------------------- #
def test_operador_no_puede_listar_usuarios(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.get("/api/usuarios", headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 403


def test_operador_no_puede_crear_recetas(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.post("/api/recetas", headers={"Authorization": "Bearer " + d["access"]},
                     json={"nombre": "X", "min_tol": 10, "max_tol": 20})
    assert r.status_code == 403


def test_administrador_si_puede(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    assert cliente.get("/api/usuarios", headers=cab).status_code == 200
    r = cliente.post("/api/recetas", headers=cab,
                     json={"nombre": "Prueba 99", "min_tol": 30, "max_tol": 70})
    assert r.status_code == 201


def test_receta_con_rango_invalido(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/recetas", headers=cab,
                     json={"nombre": "Mala", "min_tol": 80, "max_tol": 40})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# registro por API (sistema de visión)
# --------------------------------------------------------------------------- #
def test_registro_por_api(cliente):
    d = _login(cliente, "servicio", "servicio")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/inspecciones", headers=cab,
                     json={"angulo": 58.4, "id_receta": 1})
    assert r.status_code == 201
    assert r.json()["estado"] == "aprobado"


def test_registro_fuera_de_tolerancia(cliente):
    d = _login(cliente, "servicio", "servicio")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/inspecciones", headers=cab,
                     json={"angulo": 5.0, "id_receta": 1})
    assert r.status_code == 201
    assert r.json()["estado"] == "rechazado"


def test_angulo_fuera_de_rango(cliente):
    d = _login(cliente, "servicio", "servicio")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/inspecciones", headers=cab, json={"angulo": 400, "id_receta": 1})
    assert r.status_code == 422


def test_receta_inexistente(cliente):
    d = _login(cliente, "servicio", "servicio")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/inspecciones", headers=cab, json={"angulo": 50, "id_receta": 999})
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# consultas
# --------------------------------------------------------------------------- #
def test_dashboard(cliente):
    d = _login(cliente)
    r = cliente.get("/api/dashboard", headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 200
    cuerpo = r.json()
    assert "kpis" in cuerpo and cuerpo["kpis"]["total"] >= 1


def test_filtro_por_estado(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.get("/api/inspecciones?estado=rechazado", headers=cab)
    assert r.status_code == 200
    assert all(i["estado"] == "rechazado" for i in r.json()["items"])


def test_inmutabilidad_de_limites(cliente):
    """Cambiar la receta no altera los límites de una inspección ya registrada."""
    d = _login(cliente, "servicio", "servicio")
    cab = {"Authorization": "Bearer " + d["access"]}
    nueva = cliente.post("/api/inspecciones", headers=cab,
                         json={"angulo": 50, "id_receta": 2}).json()["id"]
    with db.SesionLocal() as s:
        antes = s.get(db.Inspeccion, nueva).limite_max
        s.get(db.Receta, 2).max_tol = 179
        s.commit()
        despues = s.get(db.Inspeccion, nueva).limite_max
        s.get(db.Receta, 2).max_tol = 95
        s.commit()
    assert float(antes) == float(despues)


# --------------------------------------------------------------------------- #
# simulación de ráfaga (pipeline de visión real)
# --------------------------------------------------------------------------- #
def test_simulacion_completa(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/simular?receta_id=1", headers=cab)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["rafaga"]["frames"] == 16
    assert cuerpo["inspeccion"]["angulo"] is not None
    assert cuerpo["inspeccion"]["estado"] in ("aprobado", "rechazado", "sin_receta")
    assert cuerpo["medicion"]["angulo"] is not None
    # la inspección simulada queda asociada a receta, batch y material
    insp = cuerpo["inspeccion"]
    assert insp["receta_id"] == 1
    assert insp["batch_id"] is not None
    assert insp["materialidad"]
    assert insp["velocidad_m_min"] == 12.0


def test_simulacion_forzada_fuera_de_tolerancia(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/simular?receta_id=1&modo=fuera", headers=cab)
    assert r.status_code == 200
    assert r.json()["inspeccion"]["estado"] == "rechazado"


# --------------------------------------------------------------------------- #
# catálogo de materiales
# --------------------------------------------------------------------------- #
def test_materiales_catalogo(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.get("/api/materiales", headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo) >= 7
    familias = {m["familia"] for m in cuerpo}
    assert {"Acero", "Cobre", "Aluminio"} <= familias


def test_crear_material_y_duplicado(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/materiales", headers=cab,
                     json={"familia": "Bronce", "tipo": "SAE 65", "descripcion": "Prueba"})
    assert r.status_code == 201
    r2 = cliente.post("/api/materiales", headers=cab, json={"familia": "Bronce", "tipo": "SAE 65"})
    assert r2.status_code == 409


def test_operador_no_crea_materiales(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.post("/api/materiales", headers={"Authorization": "Bearer " + d["access"]},
                     json={"familia": "Acero", "tipo": "SAE 9999"})
    assert r.status_code == 403


def test_receta_con_material(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    materiales = cliente.get("/api/materiales", headers=cab).json()
    material = next(m for m in materiales if m["familia"] == "Aluminio")
    r = cliente.post("/api/recetas", headers=cab,
                     json={"nombre": "Perfil X", "min_tol": 20, "max_tol": 80,
                           "material_id": material["id"]})
    assert r.status_code == 201
    assert "Aluminio" in r.json()["material"]
    recetas = cliente.get("/api/recetas", headers=cab).json()
    perfil = next(x for x in recetas if x["nombre"] == "Perfil X")
    assert perfil["material_id"] == material["id"]
    assert perfil["material_familia"] == "Aluminio"


# --------------------------------------------------------------------------- #
# orden y trazabilidad de IDs
# --------------------------------------------------------------------------- #
def test_orden_por_lote_y_batch(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.get("/api/inspecciones?orden=lote&tamano=200", headers=cab)
    assert r.status_code == 200
    items = r.json()["items"]
    claves = [(i["lote"] or "", i["batch"] or 0) for i in items]
    assert claves == sorted(claves)
    assert r.json()["orden"] == "lote"


def test_los_registros_llevan_ids(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    items = cliente.get("/api/inspecciones?tamano=5", headers=cab).json()["items"]
    assert items
    for i in items:
        assert "receta_id" in i and i["receta_id"] is not None
        assert "batch_id" in i          # puede venir nulo si el integrador no lo envía
        assert i["materialidad"]


# --------------------------------------------------------------------------- #
# velocidad y aleatoriedad del simulador
# --------------------------------------------------------------------------- #
def test_velocidad_alta_desplaza_el_angulo(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    lento = cliente.post("/api/simular?receta_id=1&velocidad=6&modo=dentro", headers=cab).json()
    rapido = cliente.post("/api/simular?receta_id=1&velocidad=30&modo=dentro", headers=cab).json()
    assert lento["proceso"]["velocidad_m_min"] == 6
    assert rapido["proceso"]["velocidad_m_min"] == 30
    # a mayor velocidad, mayor ángulo medido
    assert rapido["medicion"]["angulo"] > lento["medicion"]["angulo"]
    # y la velocidad alta debe sacarlo de tolerancia de la receta A-36 (45–90)
    assert rapido["inspeccion"]["estado"] == "rechazado"


def test_modo_aleatorio_es_valido(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/simular?receta_id=1&modo=aleatorio", headers=cab)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["proceso"]["modo"] == "aleatorio"
    assert cuerpo["inspeccion"]["estado"] in ("aprobado", "rechazado")


def test_modo_invalido(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/simular?modo=inventado", headers=cab)
    assert r.status_code == 422
