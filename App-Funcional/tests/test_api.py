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


# --------------------------------------------------------------------------- #
# funciones agregadas en la revisión de noviembre
# --------------------------------------------------------------------------- #
def test_login_por_correo_y_por_nombre(cliente):
    for ident in ("jsarabia@aza.cl", "José Sarabia"):
        r = cliente.post("/api/auth/login", json={"username": ident, "pin": "1234"})
        assert r.status_code == 200, f"falló con {ident}: {r.text}"


def test_reactivar_usuario_por_cuerpo(cliente):
    """Regresión: el PATCH recibía «activo» por URL y la interfaz lo manda en el cuerpo."""
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/usuarios", headers=cab,
                     json={"username": "temporal", "nombre": "Cuenta Temporal",
                           "rol": "operador", "pin": "AzaLab2026", "email": "temp@aza.cl"})
    assert r.status_code == 201
    uid = r.json()["id"]
    assert cliente.patch(f"/api/usuarios/{uid}", headers=cab,
                         json={"activo": False}).status_code == 200
    assert cliente.patch(f"/api/usuarios/{uid}", headers=cab,
                         json={"activo": True}).status_code == 200
    usuarios = cliente.get("/api/usuarios", headers=cab).json()
    assert next(u for u in usuarios if u["id"] == uid)["activo"] is True


def test_politica_de_contrasena(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    for i, debil in enumerate(("1234", "sololetras", "SINNUMEROS", "Corta1")):
        r = cliente.post("/api/usuarios", headers=cab,
                         json={"username": f"debil{i}", "nombre": "Prueba Clave",
                               "rol": "operador", "pin": debil})
        assert r.status_code == 422, f"{debil} debió rechazarse"
    r = cliente.post("/api/usuarios", headers=cab,
                     json={"username": "claveok", "nombre": "Clave Correcta",
                           "rol": "operador", "pin": "AzaLab2026"})
    assert r.status_code == 201


def test_configuracion_editable(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    antes = cliente.get("/api/configuracion", headers=cab).json()
    assert antes["max_intentos"]["valor"] >= 3
    r = cliente.put("/api/configuracion", headers=cab,
                    json={"max_intentos": 6, "bloqueo_min": 20,
                          "inactividad_min": 30, "sesion_unica": 1})
    assert r.status_code == 200
    despues = cliente.get("/api/configuracion", headers=cab).json()
    assert despues["max_intentos"]["valor"] == 6
    assert despues["bloqueo_min"]["valor"] == 20


def test_configuracion_solo_admin(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.get("/api/configuracion", headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 403


def test_solicitud_de_contrasena(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    # se usa una cuenta creada para la prueba, para no alterar las de demostración
    r = cliente.post("/api/usuarios", headers=cab,
                     json={"username": "olvidado", "nombre": "Cuenta Olvidada",
                           "rol": "operador", "pin": "AzaLab2026"})
    assert r.status_code == 201
    r = cliente.post("/api/auth/olvido", json={"identificador": "olvidado"})
    assert r.status_code == 200
    assert "solicitud" in r.json()["mensaje"].lower()
    lista = cliente.get("/api/solicitudes", headers=cab).json()
    pendiente = next(x for x in lista
                     if x["estado"] == "pendiente" and x["username"] == "olvidado")
    r = cliente.post(f"/api/solicitudes/{pendiente['id']}/resolver", headers=cab,
                     json={"nueva_clave": "NuevaClave2026", "nota": "Prueba"})
    assert r.status_code == 200
    assert cliente.post("/api/auth/login",
                        json={"username": "olvidado", "pin": "NuevaClave2026"}).status_code == 200


def test_alarmas_y_flujo_de_revision(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/simular?receta_id=1&modo=fuera", headers=cab)
    assert r.status_code == 200
    alarmas = cliente.get("/api/alarmas", headers=cab).json()
    assert alarmas, "debería existir al menos una alarma"
    alarma = next(a for a in alarmas if a["estado"] != "solucionada")
    assert cliente.patch(f"/api/alarmas/{alarma['id']}", headers=cab,
                         json={"estado": "en_revision"}).status_code == 200
    r = cliente.patch(f"/api/alarmas/{alarma['id']}", headers=cab,
                      json={"estado": "solucionada"})
    assert r.status_code == 422, "solucionar sin detalle debe fallar"
    r = cliente.patch(f"/api/alarmas/{alarma['id']}", headers=cab,
                      json={"estado": "solucionada", "solucion": "Se recalibró el cabezal"})
    assert r.status_code == 200
    resuelta = next(a for a in cliente.get("/api/alarmas", headers=cab).json()
                    if a["id"] == alarma["id"])
    assert resuelta["estado"] == "solucionada"
    assert "recalibró" in resuelta["solucion"]


def test_filtro_por_operador(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    todos = cliente.get("/api/inspecciones?tamano=200", headers=cab).json()["total"]
    filtrado = cliente.get("/api/inspecciones?operador=ldaza&tamano=200", headers=cab).json()
    assert filtrado["total"] <= todos
    assert all(i["operador"] == "Leonardo Daza" for i in filtrado["items"])


def test_auditoria_con_detalle_legible(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    eventos = cliente.get("/api/auditoria", headers=cab).json()
    con_detalle = [e for e in eventos if e.get("detalle_texto")]
    assert con_detalle, "la bitácora debe exponer el detalle en texto"
    assert "[object Object]" not in " ".join(e["detalle_texto"] for e in con_detalle)


# --------------------------------------------------------------------------- #
# respaldos y estadísticas
# --------------------------------------------------------------------------- #
def test_respaldo_crear_listar_y_restaurar(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.post("/api/respaldos", headers=cab)
    assert r.status_code == 201, r.text
    meta = r.json()
    assert meta["total"] > 0 and meta["huella"]
    lista = cliente.get("/api/respaldos", headers=cab).json()
    assert any(x["archivo"] == meta["archivo"] for x in lista["respaldos"])
    assert lista["configuracion"]["horas"] >= 1
    r = cliente.post("/api/respaldos/restaurar", headers=cab,
                     json={"archivo": meta["archivo"]})
    assert r.status_code == 200
    assert r.json()["insertados"]["inspecciones"] > 0


def test_respaldo_comparar(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    a = cliente.post("/api/respaldos", headers=cab).json()["archivo"]
    b = cliente.post("/api/respaldos", headers=cab).json()["archivo"]
    r = cliente.post("/api/respaldos/comparar", headers=cab, json={"a": a, "b": b})
    assert r.status_code == 200
    cuerpo = r.json()
    assert "tablas" in cuerpo and "iguales" in cuerpo


def test_respaldo_solo_admin(cliente):
    d = _login(cliente, "jsarabia")          # supervisor: no puede gestionar respaldos
    r = cliente.get("/api/respaldos", headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 403


def test_estadisticas_por_operador(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    datos = cliente.get("/api/estadisticas/operadores", headers=cab).json()
    assert datos, "debe devolver al menos un operador"
    primero = datos[0]
    for campo in ("nombre", "total", "aprobadas", "rechazadas", "aprobacion_pct"):
        assert campo in primero
    assert 0 <= primero["aprobacion_pct"] <= 100


def test_login_sin_credenciales_expuestas():
    """El login no debe traer usuario ni clave precargados."""
    import os
    html = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "web", "index.html"), encoding="utf-8").read()
    assert 'value="1234"' not in html
    assert "lista-usuarios" not in html
    assert 'autocomplete="new-password"' in html
    assert 'autocomplete="off"' in html


# --------------------------------------------------------------------------- #
# comparador por pares y permisos granulares
# --------------------------------------------------------------------------- #
def test_comparador_por_pares(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.get("/api/estadisticas/comparar?a=jsarabia&b=ldaza", headers=cab)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert len(cuerpo["operadores"]) == 2
    assert cuerpo["operadores"][0]["username"] == "jsarabia"
    assert "veredicto" in cuerpo and set(cuerpo["veredicto"]) == {"volumen", "calidad", "velocidad"}
    assert "recetas" in cuerpo["operadores"][0]
    assert "lotes" in cuerpo["operadores"][0]
    assert isinstance(cuerpo["recetas"]["comunes"], list)


def test_comparador_operador_inexistente(cliente):
    d = _login(cliente, "jsarabia")
    r = cliente.get("/api/estadisticas/comparar?a=jsarabia&b=nadie",
                    headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 404


def test_permisos_granulares(cliente):
    admin = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + admin["access"]}
    catalogo = cliente.get("/api/permisos", headers=cab).json()
    assert len(catalogo) >= 8
    usuario = next(u for u in cliente.get("/api/usuarios", headers=cab).json()
                   if u["username"] == "ldaza")
    # sin permiso: el operador no ve estadísticas
    op = _login(cliente, "ldaza")
    assert cliente.get("/api/estadisticas/operadores",
                       headers={"Authorization": "Bearer " + op["access"]}).status_code == 403
    # se lo concedemos
    r = cliente.put(f"/api/usuarios/{usuario['id']}/permisos", headers=cab,
                    json={"permisos": ["ver_estadisticas"]})
    assert r.status_code == 200
    op2 = _login(cliente, "ldaza")
    cab2 = {"Authorization": "Bearer " + op2["access"]}
    assert op2["usuario"]["permisos"] == ["ver_estadisticas"]
    assert cliente.get("/api/estadisticas/operadores", headers=cab2).status_code == 200
    # pero sigue sin poder gestionar respaldos
    assert cliente.get("/api/respaldos", headers=cab2).status_code == 403
    # se le quita
    cliente.put(f"/api/usuarios/{usuario['id']}/permisos", headers=cab, json={"permisos": []})
    op3 = _login(cliente, "ldaza")
    assert cliente.get("/api/estadisticas/operadores",
                       headers={"Authorization": "Bearer " + op3["access"]}).status_code == 403

# --------------------------------------------------------------------------- #
# informe de gestión por períodos
# --------------------------------------------------------------------------- #
def test_informe_por_semanas(cliente):
    d = _login(cliente, "jsarabia")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.get("/api/estadisticas/periodos?granularidad=semana", headers=cab)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["granularidad"] == "semana"
    assert "periodos" in cuerpo and "totales" in cuerpo and "variacion" in cuerpo
    assert set(cuerpo["variacion"]) == {"total", "aprobadas", "rechazadas"}
    if cuerpo["periodos"]:
        cubo = cuerpo["periodos"][0]
        for campo in ("etiqueta", "total", "aprobadas", "aprobacion_pct", "desde", "hasta"):
            assert campo in cubo


def test_informe_por_meses(cliente):
    d = _login(cliente, "dparedes")
    cab = {"Authorization": "Bearer " + d["access"]}
    r = cliente.get("/api/estadisticas/periodos?granularidad=mes", headers=cab)
    assert r.status_code == 200
    assert r.json()["granularidad"] == "mes"


def test_informe_granularidad_invalida(cliente):
    d = _login(cliente, "dparedes")
    r = cliente.get("/api/estadisticas/periodos?granularidad=dia",
                    headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 422


def test_informe_solo_supervisores(cliente):
    d = _login(cliente, "ldaza")
    r = cliente.get("/api/estadisticas/periodos",
                    headers={"Authorization": "Bearer " + d["access"]})
    assert r.status_code == 403
