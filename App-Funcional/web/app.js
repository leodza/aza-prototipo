/* AZA Analyzer — prototipo funcional (cliente) */
"use strict";

const estado = {
  access: null,
  refresh: null,
  usuario: null,
  pagina: 1,
  ultima: null,
  seleccion: null,
  motor: "",
};

/* ------------------------------------------------------------------ utilidades */
const $ = (id) => document.getElementById(id);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toFixed(d).replace(".", ",");
const dos = (n) => String(n).padStart(2, "0");
const hoyLocal = () => {
  const d = new Date();                        // fecha local, no UTC
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
};
const fecha = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  // formato AAAA-MM-DD HH:MM:SS (año primero)
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ` +
         `${dos(d.getHours())}:${dos(d.getMinutes())}:${dos(d.getSeconds())}`;
};
const ORIGEN = { camara_simulada: "cámara simulada", historico_demo: "histórico demo", api: "API (visión)" };
const origen = (o) => ORIGEN[o] || o || "—";
const badge = (e) => {
  const mapa = { aprobado: ["aprobado", "Aprobada"], rechazado: ["rechazado", "Rechazada"], sin_receta: ["sin-receta", "Sin receta"] };
  const [clase, texto] = mapa[e] || ["sin-receta", e || "—"];
  return `<span class="estado ${clase}">${texto}</span>`;
};

async function api(ruta, opciones = {}, reintento = true) {
  const cab = { "Content-Type": "application/json", ...(opciones.headers || {}) };
  if (estado.access) cab.Authorization = "Bearer " + estado.access;
  const r = await fetch(ruta, { ...opciones, headers: cab });
  if (r.status === 401 && reintento && estado.refresh) {
    if (await renovar()) return api(ruta, opciones, false);
  }
  if (!r.ok) {
    let msg = `Error ${r.status}`;
    try { const j = await r.json(); msg = j.detail || msg; } catch (_) { }
    throw new Error(msg);
  }
  if (r.status === 204) return null;
  const tipo = r.headers.get("content-type") || "";
  return tipo.includes("application/json") ? r.json() : r;
}

async function renovar() {
  try {
    const r = await fetch("/api/auth/refresh", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: estado.refresh }),
    });
    if (!r.ok) return false;
    const j = await r.json();
    estado.access = j.access; estado.refresh = j.refresh;
    return true;
  } catch (_) { return false; }
}

/* ------------------------------------------------------------------ sesión */
async function entrar(ev) {
  ev.preventDefault();
  const btn = $("btn-login");
  btn.disabled = true; btn.textContent = "Verificando…";
  $("login-error").textContent = "";
  try {
    const j = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: $("login-usuario").value, pin: $("login-pin").value }),
    }, false);
    estado.access = j.access; estado.refresh = j.refresh; estado.usuario = j.usuario;
    $("pantalla-login").style.display = "none";
    $("app").style.display = "flex";
    $("nombre-usuario").textContent = j.usuario.nombre;
    $("rol-usuario").textContent = j.usuario.rol;
    $("avatar").textContent = j.usuario.nombre.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();
    $("chip-rol").textContent = "rol: " + j.usuario.rol;
    await arrancar();
  } catch (e) {
    $("login-error").textContent = e.message;
  } finally {
    btn.disabled = false; btn.textContent = "Ingresar";
  }
}

async function salir() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { }
  estado.access = estado.refresh = estado.usuario = null;
  $("app").style.display = "none";
  $("pantalla-login").style.display = "grid";
}

async function arrancar() {
  const h = await api("/api/health");
  estado.motor = h.motor;
  $("chip-motor").textContent = h.motor.includes("APP-AZA") ? "motor: pipeline APP-AZA" : "motor: interno";
  $("chip-motor").className = h.motor.includes("APP-AZA") ? "chip ok" : "chip info";
  $("estado-api").textContent = `${h.inspecciones} inspecciones · ${h.base || "base de datos"}` +
    (h.objetos ? ` · ${h.objetos} objetos` : "");
  const pie = $("pie-base");
  if (pie) pie.textContent = h.base || "base de datos";
  aplicarPermisos();
  await Promise.all([cargarDashboard(), cargarSelects()]);
  irA("dashboard");                 // siempre se vuelve al menú principal al entrar
  reloj(); setInterval(reloj, 30000);
}

/* ------------------------------------------------------------------ permisos */
function rolActual() {
  return (estado.usuario && estado.usuario.rol) || "";
}

function vistasPermitidas() {
  const rol = rolActual();
  return [...document.querySelectorAll("nav button")]
    .filter((b) => !b.dataset.roles || b.dataset.roles.split(",").includes(rol))
    .map((b) => b.dataset.vista);
}

function aplicarPermisos() {
  const rol = rolActual();
  document.querySelectorAll("nav button").forEach((b) => {
    const permitido = !b.dataset.roles || b.dataset.roles.split(",").includes(rol);
    b.classList.toggle("oculto", !permitido);
  });
  $("card-nuevo-usuario").classList.toggle("oculto", rol !== "administrador");
}

function reloj() {
  const d = new Date();
  $("reloj").textContent =
    `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
}

/* ------------------------------------------------------------------ navegación */
const TITULOS = {
  dashboard: "Dashboard", historico: "Histórico de inspecciones", detalle: "Detalle de la inspección",
  simulador: "Simulador de cámara", recetas: "Recetas y tolerancias",
  usuarios: "Usuarios y roles", auditoria: "Auditoría del sistema",
};

function irA(vista) {
  if (!vistasPermitidas().includes(vista)) vista = "dashboard";   // el rol manda
  document.querySelectorAll(".vista").forEach((v) => v.classList.toggle("activa", v.id === "v-" + vista));
  document.querySelectorAll("nav button").forEach((b) => {
    if (b.dataset.vista === vista) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  $("titulo-vista").textContent = TITULOS[vista] || vista;
  if (vista === "historico") cargarHistorico(1);
  if (vista === "recetas") { cargarRecetas(); cargarMateriales(); }
  if (vista === "usuarios") cargarUsuarios();
  if (vista === "auditoria") cargarAuditoria();
  window.scrollTo({ top: 0, behavior: "instant" });
}

document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => irA(b.dataset.vista)));

/* ------------------------------------------------------------------ dashboard */
function aguja(angulo) {
  const a = (Number(angulo) || 0) * Math.PI / 180;
  return { x: 60 + 46 * Math.sin(a), y: 60 - 46 * Math.cos(a) };
}

function pintarMedidor(angulo) {
  const p = aguja(angulo);
  $("gauge-aguja").setAttribute("x2", p.x.toFixed(1));
  $("gauge-aguja").setAttribute("y2", p.y.toFixed(1));
  const grande = Number(angulo) > 180 ? 1 : 0;
  $("gauge-arco").setAttribute("d", `M60 60 L60 14 A46 46 0 ${grande} 1 ${p.x.toFixed(1)} ${p.y.toFixed(1)} Z`);
  $("gauge-texto").textContent = angulo === null || angulo === undefined ? "—" : num(angulo) + "°";
}

async function cargarDashboard() {
  try {
    const d = await api("/api/dashboard");
    estado.ultima = d.ultima;
    const k = d.kpis;
    $("kpi-total").textContent = k.total;
    $("kpi-total-d").textContent = k.tasa + " % de aprobación";
    $("kpi-aprob").textContent = k.aprobadas;
    $("kpi-aprob-d").textContent = k.total ? Math.round(k.aprobadas * 100 / k.total) + " % del total" : "sin registros";
    $("kpi-rech").textContent = k.rechazadas;
    $("kpi-rech-d").textContent = k.total ? Math.round(k.rechazadas * 100 / k.total) + " % del total" : "sin registros";
    $("kpi-sin").textContent = k.sin_receta;
    $("kpi-sin-d").textContent = k.alarmas + " alarmas pendientes";

    if (d.ultima) {
      const u = d.ultima;
      $("banner-ultima").innerHTML = `<strong>Última inspección:</strong> ${fecha(u.fecha_hora)} ·
        lote <span class="mono">${esc(u.lote || "—")}</span> · receta <span class="mono">${esc(u.receta || "—")}</span> ·
        ${badge(u.estado)}`;
      $("banner-ultima").className = "banner " + (u.estado === "aprobado" ? "verde" : "ambar");
      $("ultima-sub").textContent = `#${u.id} · ${fecha(u.fecha_hora)} · operador ${u.operador || "—"}`;
      $("ultima-estado").innerHTML = badge(u.estado);
      $("ultima-tol").textContent = `${num(u.limite_min)}° – ${num(u.limite_max)}°`;
      $("ultima-origen").textContent = origen(u.origen);
      $("ultima-min").textContent = "mín " + num(u.limite_min) + "°";
      $("ultima-max").textContent = "máx " + num(u.limite_max) + "°";
      pintarMedidor(u.angulo);
      const pct = u.angulo == null ? 50 : Math.max(0, Math.min(100, (Number(u.angulo) / 180) * 100));
      $("ultima-pin").style.left = pct + "%";
    }

    const t = d.tendencia.filter((x) => x.angulo !== null);
    if (t.length > 1) {
      const pts = t.map((x, i) => `${(i / (t.length - 1)) * 320},${110 - (Number(x.angulo) / 180) * 100}`);
      $("spark-linea").setAttribute("points", pts.join(" "));
      const ult = t[t.length - 1];
      $("spark-punto").setAttribute("cx", 320);
      $("spark-punto").setAttribute("cy", (110 - (Number(ult.angulo) / 180) * 100).toFixed(1));
      $("spark-punto").setAttribute("fill", ult.estado === "aprobado" ? "#1b5e20" : "#c62828");
    }

    $("recientes-sub").textContent = `${k.total} inspecciones registradas hoy`;
    $("tabla-recientes").innerHTML = d.recientes.map((i) => `
      <tr style="cursor:pointer" onclick="verDetalle(${i.id})">
        <td class="mono">${String(i.id).padStart(4, "0")}</td>
        <td class="mono">${fecha(i.fecha_hora)}</td>
        <td>${esc(i.receta || "—")} <span class="muted mono">#${i.receta_id ?? "—"}</span></td>
        <td class="mono">${esc(i.lote || "—")} · B${i.batch ?? "—"} <span class="muted">#${i.batch_id ?? "—"}</span></td>
        <td class="num">${num(i.angulo)}°</td>
        <td>${badge(i.estado)}</td>
        <td class="muted" style="font-size:.8rem">${esc(origen(i.origen))}</td>
      </tr>`).join("") || `<tr><td colspan="7" class="muted">Sin registros todavía.</td></tr>`;
  } catch (e) {
    $("banner-ultima").textContent = "No se pudo cargar el dashboard: " + e.message;
  }
}

/* ------------------------------------------------------------------ histórico */
async function cargarSelects() {
  try {
    const [recetas, lotes, materiales] = await Promise.all(
      [api("/api/recetas"), api("/api/lotes"), api("/api/materiales")]);
    $("f-receta").innerHTML = `<option value="">Todas</option>` +
      recetas.map((r) => `<option>${esc(r.nombre)}</option>`).join("");
    $("sim-receta").innerHTML = recetas.filter((r) => r.activa)
      .map((r) => `<option value="${r.id}">${esc(r.nombre)} · ${esc(r.materialidad || "sin material")} ` +
                  `(${num(r.min_tol)}° – ${num(r.max_tol)}°)</option>`).join("");
    $("f-lote").innerHTML = `<option value="">Todos</option>` +
      lotes.map((l) => `<option>${esc(l.codigo)}</option>`).join("");
    $("r-mat").innerHTML = materiales.map((m) =>
      `<option value="${m.id}">${esc(m.familia)} ${esc(m.tipo)}</option>`).join("");
    const hoy = hoyLocal();
    if (!$("f-desde").value) { $("f-desde").value = hoy; $("f-hasta").value = hoy; }
    actualizarVelocidad();
  } catch (_) { }
}

async function cargarHistorico(pagina = 1) {
  estado.pagina = pagina;
  const q = new URLSearchParams({ pagina, tamano: 20, orden: $("f-orden").value || "lote" });
  if ($("f-desde").value) q.set("desde", $("f-desde").value);
  if ($("f-hasta").value) q.set("hasta", $("f-hasta").value);
  if ($("f-receta").value) q.set("receta", $("f-receta").value);
  if ($("f-lote").value) q.set("lote", $("f-lote").value);
  if ($("f-estado").value) q.set("estado", $("f-estado").value);
  try {
    const d = await api("/api/inspecciones?" + q);
    const criterio = d.orden === "fecha" ? "más recientes primero" : "lote → batch → fecha";
    $("hist-contador").textContent =
      `${d.total} registros · orden: ${criterio} · página ${d.pagina} de ${Math.max(1, Math.ceil(d.total / d.tamano))}`;
    $("tabla-historico").innerHTML = d.items.map((i) => `
      <tr style="cursor:pointer" onclick="verDetalle(${i.id})">
        <td class="mono">${String(i.id).padStart(4, "0")}</td>
        <td class="mono">${fecha(i.fecha_hora)}</td>
        <td>${esc(i.receta || "—")} <span class="muted mono">#${i.receta_id ?? "—"}</span></td>
        <td class="mono">${esc(i.lote || "—")} · B${i.batch ?? "—"} <span class="muted">#${i.batch_id ?? "—"}</span></td>
        <td>${esc(i.operador || "—")}</td>
        <td class="num">${num(i.angulo)}°</td>
        <td class="num">${num(i.limite_min, 0)}–${num(i.limite_max, 0)}</td>
        <td>${badge(i.estado)}</td>
      </tr>`).join("") || `<tr><td colspan="8" class="muted">Sin resultados para los filtros aplicados.</td></tr>`;
    estado.ultimoHist = d;
  } catch (e) {
    $("hist-contador").textContent = "Error: " + e.message;
  }
}

function paginaHist(delta) {
  const total = estado.ultimoHist ? Math.ceil(estado.ultimoHist.total / estado.ultimoHist.tamano) : 1;
  const nueva = Math.min(Math.max(1, estado.pagina + delta), Math.max(1, total));
  cargarHistorico(nueva);
}

function limpiarFiltros() {
  ["f-receta", "f-lote", "f-estado"].forEach((id) => $(id).value = "");
  const hoy = hoyLocal();
  $("f-desde").value = hoy; $("f-hasta").value = hoy;
  cargarHistorico(1);
}

function exportarCSV() {
  const d = estado.ultimoHist;
  if (!d || !d.items.length) { alert("No hay resultados para exportar."); return; }
  const cab = ["id", "fecha_hora", "receta", "lote", "operador", "angulo", "estado"];
  const filas = d.items.map((i) => [i.id, i.fecha_hora, i.receta, i.lote, i.operador, i.angulo, i.estado]
    .map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","));
  const blob = new Blob(["\uFEFF" + [cab.join(","), ...filas].join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `aza_historicos_${hoyLocal()}.csv`;
  a.click();
}

/* ------------------------------------------------------------------ detalle */
async function verDetalle(id) {
  irA("detalle");
  try {
    const d = await api("/api/inspecciones/" + id);
    const i = d.inspeccion;
    estado.seleccion = i;
    $("detalle-aviso").style.display = "none";
    $("detalle-grid").style.display = "grid";
    $("det-titulo").innerHTML = `Inspección ${String(i.id).padStart(4, "0")} ${badge(i.estado)}`;
    $("det-sub").textContent = `${fecha(i.fecha_hora)} · lote ${i.lote || "—"} · operador ${i.operador || "—"}`;
    $("det-datos").innerHTML = `
      <div><dt>Ángulo medido</dt><dd class="mono" style="font-size:1.15rem"><b>${num(i.angulo)}°</b></dd></div>
      <div><dt>Estado</dt><dd>${badge(i.estado)}</dd></div>
      <div><dt>Receta aplicada</dt><dd>${esc(i.receta || "—")} <span class="muted mono">#${i.receta_id ?? "—"}</span>
        (${num(i.limite_min)}° – ${num(i.limite_max)}°)</dd></div>
      <div><dt>Material</dt><dd>${esc(i.materialidad || "—")}</dd></div>
      <div><dt>Lote · batch · turno</dt><dd class="mono">${esc(i.lote || "—")} · B${i.batch ?? "—"} <span class="muted">#${i.batch_id ?? "—"}</span> · ${esc(i.turno || "—")}</dd></div>
      <div><dt>Operador</dt><dd>${esc(i.operador || "—")}</dd></div>
      <div><dt>Origen del dato</dt><dd>${esc(origen(i.origen))}</dd></div>
      <div><dt>Velocidad del tren</dt><dd class="mono">${i.velocidad_m_min ? num(i.velocidad_m_min) + " m/min" : "—"}</dd></div>
      <div><dt>Desviación vs. centro</dt><dd class="mono">${i.desviacion_deg === null || i.desviacion_deg === undefined
        ? "—" : (i.desviacion_deg >= 0 ? "+" : "−") + num(Math.abs(i.desviacion_deg)) + "°"}</dd></div>`;

    $("det-tecnico-card").hidden = false;
    $("det-tecnico").innerHTML = `
      <div><dt>Confianza del análisis</dt><dd>${esc(i.confianza || "—")}</dd></div>
      <div><dt>Tiempo de proceso</dt><dd>${i.duracion_ms ? i.duracion_ms + " ms" : "—"}</dd></div>
      <div><dt>Frame de salida</dt><dd class="mono">${i.frame_salida ? i.frame_salida + " de 16" : "—"}</dd></div>
      <div><dt>Círculo detectado</dt><dd class="mono">${i.centro_x !== null && i.centro_x !== undefined ? `(${num(i.centro_x)}, ${num(i.centro_y)}) r=${num(i.radio)}` : "—"}</dd></div>
      <div><dt>Espesor de receta</dt><dd>${i.espesor_mm ? num(i.espesor_mm) + " mm" : "—"}</dd></div>
      <div><dt>Materialidad</dt><dd>${esc(i.materialidad || "—")}</dd></div>
      <div><dt>Motor de análisis</dt><dd style="font-size:.78rem">${esc(i.motor || "—")}</dd></div>
      <div><dt>Ráfaga en disco</dt><dd style="font-size:.74rem;word-break:break-all">${esc(i.carpeta || "—")}</dd></div>`;

    $("det-auditoria").innerHTML = (d.auditoria || []).map((e, n) => `
      <div class="paso"><span class="n">${n + 1}</span>
        <div><strong>${fecha(e.fecha)}</strong> · ${esc(e.accion)} sobre <span class="mono">${esc(e.entidad)}</span></div></div>`
    ).join("") || `<div class="muted" style="font-size:.84rem">Sin eventos asociados.</div>`;
    const cont = $("det-imagen");
    if (i.tiene_imagen) {
      cont.innerHTML = `<img src="/api/inspecciones/${i.id}/imagen?t=${Date.now()}" alt="Diagnóstico de la inspección"
        style="width:100%;display:block">`;
      $("det-img-sub").textContent = "resultado_analisis.png generado por el pipeline";
    } else {
      cont.innerHTML = `<span class="muted" style="font-size:.8rem;padding:24px;text-align:center">
        Esta inspección no tiene imagen asociada<br>(registros del histórico de demostración)</span>`;
      $("det-img-sub").textContent = "sin imagen";
    }
  } catch (e) {
    alert("No se pudo cargar el detalle: " + e.message);
  }
}

/* ------------------------------------------------------------------ simulador */
const VELOCIDAD_NOMINAL = 12.0;
const GRADOS_POR_M_MIN = 2.8;

function actualizarVelocidad() {
  const v = Number($("sim-velocidad").value);
  $("sim-velocidad-valor").textContent = num(v);
  const efecto = (v - VELOCIDAD_NOMINAL) * GRADOS_POR_M_MIN;
  const signo = efecto >= 0 ? "+" : "−";
  $("sim-velocidad-ayuda").innerHTML =
    `Velocidad nominal ${num(VELOCIDAD_NOMINAL)} m/min · efecto esperado sobre el ángulo: ` +
    `<b>${signo}${num(Math.abs(efecto))}°</b> respecto del centro de la receta`;
}

async function simular() {
  const btn = $("btn-simular");
  btn.disabled = true;
  const t0 = performance.now();
  let paso = 0;
  const mensajes = ["Capturando ráfaga de la cámara…", "Guardando imágenes BMP…",
    "Ejecutando el pipeline de visión…", "Detectando círculo y ángulo…", "Registrando en la base…"];
  const tick = setInterval(() => {
    paso = Math.min(paso + 1, mensajes.length - 1);
    $("sim-estado").textContent = mensajes[paso] + " (" + ((performance.now() - t0) / 1000).toFixed(1) + " s)";
  }, 450);
  $("sim-estado").textContent = mensajes[0];
  try {
    const q = new URLSearchParams();
    if ($("sim-receta").value) q.set("receta_id", $("sim-receta").value);
    q.set("modo", $("sim-modo").value);
    q.set("velocidad", $("sim-velocidad").value);
    const d = await api("/api/simular?" + q, { method: "POST" });
    const i = d.inspeccion, m = d.medicion, p = d.proceso || {};
    window.__ultimaSim = i.id;
    $("sim-sub").textContent = `Ráfaga ${d.rafaga.frames} frames · ${d.duracion_ms} ms · motor: ${m.motor}`;
    const desv = p.desviacion_medida;
    const signo = desv >= 0 ? "+" : "−";
    $("sim-resultado").innerHTML = `
      <dl class="lista-def" style="display:grid;grid-template-columns:1fr 1fr;gap:0 18px;margin:0">
        <div><dt>Ángulo medido</dt><dd class="mono" style="font-size:1.3rem"><b>${num(m.angulo)}°</b></dd></div>
        <div><dt>Estado</dt><dd>${badge(i.estado)}</dd></div>
        <div><dt>Velocidad del tren</dt><dd class="mono">${num(p.velocidad_m_min)} m/min</dd></div>
        <div><dt>Desviación vs. centro</dt><dd class="mono">${desv === null || desv === undefined ? "—" : signo + num(Math.abs(desv)) + "°"}</dd></div>
        <div><dt>Confianza</dt><dd>${esc(m.confianza || "—")}</dd></div>
        <div><dt>Frame de salida</dt><dd class="mono">${m.frame_salida ?? "—"} / ${m.total_frames ?? "—"}</dd></div>
        <div><dt>Círculo detectado</dt><dd class="mono">(${m.centro ? num(m.centro[0]) + ", " + num(m.centro[1]) : "—"}) r=${num(m.radio)}</dd></div>
        <div><dt>Tolerancia aplicada</dt><dd class="mono">${num(i.limite_min)}° – ${num(i.limite_max)}°</dd></div>
        <div><dt>Receta · material</dt><dd>${esc(i.receta)} <span class="muted mono">#${i.receta_id}</span> · ${esc(i.materialidad || "—")}</dd></div>
        <div><dt>Lote · batch</dt><dd class="mono">${esc(i.lote || "—")} · B${i.batch ?? "—"}</dd></div>
        <div><dt>Insp. registrada</dt><dd class="mono">#${i.id}</dd></div>
        <div><dt>Modo</dt><dd>${esc(p.modo)}</dd></div>
      </dl>
      <div class="banner ${i.estado === "aprobado" ? "verde" : "ambar"}" style="margin-top:14px">
        ${i.estado === "aprobado"
          ? "Resultado dentro de tolerancia: la pieza se clasifica como <strong>aprobada</strong>."
          : "Resultado fuera de tolerancia: se registró la inspección y se generó una <strong>alarma</strong>."}
        ${i.estado !== "aprobado" && p.modo !== "fuera" && p.velocidad_m_min
          ? ` Prueba ${p.velocidad_m_min > VELOCIDAD_NOMINAL ? "bajando" : "subiendo"} la velocidad ` +
            `hacia ~${num(VELOCIDAD_NOMINAL)} m/min para corregir la diferencia de grados.`
          : ""}
      </div>`;
    if (i.tiene_imagen) {
      $("sim-imagen-card").hidden = false;
      $("sim-imagen").src = `/api/inspecciones/${i.id}/imagen?t=${Date.now()}`;
    } else {
      $("sim-imagen-card").hidden = true;
    }
    $("sim-estado").textContent = `Listo en ${d.duracion_ms} ms ✓`;
    await cargarDashboard();
  } catch (e) {
    $("sim-estado").textContent = "Error: " + e.message;
  } finally {
    clearInterval(tick);
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------------ recetas y materiales */
async function cargarRecetas() {
  try {
    const d = await api("/api/recetas");
    const admin = estado.usuario && estado.usuario.rol === "administrador";
    $("form-receta").hidden = !admin;
    $("tabla-recetas").innerHTML = d.map((r) => `
      <tr>
        <td class="mono">#${r.id}</td>
        <td><strong>${esc(r.nombre)}</strong></td>
        <td class="num">${num(r.min_tol)}°</td>
        <td class="num">${num(r.max_tol)}°</td>
        <td>${r.espesor_mm ? num(r.espesor_mm) + " mm" : "—"}</td>
        <td>${esc(r.materialidad || "—")}</td>
        <td class="num">${r.registros}</td>
        <td>${r.activa ? '<span class="estado aprobado">Activa</span>' : '<span class="estado rechazado">Inactiva</span>'}</td>
      </tr>`).join("");
  } catch (e) {
    $("tabla-recetas").innerHTML = `<tr><td colspan="8" class="muted">Error: ${esc(e.message)}</td></tr>`;
  }
}

async function cargarMateriales() {
  try {
    const d = await api("/api/materiales");
    const admin = estado.usuario && estado.usuario.rol === "administrador";
    $("form-material").hidden = !admin;
    $("tabla-materiales").innerHTML = d.map((m) => `
      <tr>
        <td class="mono">#${m.id}</td>
        <td><strong>${esc(m.familia)}</strong></td>
        <td>${esc(m.tipo)}</td>
        <td class="muted">${esc(m.descripcion || "—")}</td>
        <td class="num">${m.recetas}</td>
      </tr>`).join("");
  } catch (e) {
    $("tabla-materiales").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`;
  }
}

async function crearMaterial() {
  const msg = $("material-msg");
  msg.textContent = "";
  const tipo = $("m-tipo").value.trim();
  if (!tipo) { msg.textContent = "Indique el tipo de material."; return; }
  try {
    const r = await api("/api/materiales", {
      method: "POST",
      body: JSON.stringify({ familia: $("m-familia").value, tipo,
                             descripcion: $("m-desc").value.trim() || null }),
    });
    msg.textContent = `Material «${r.nombre}» agregado ✓`;
    $("m-tipo").value = ""; $("m-desc").value = "";
    await Promise.all([cargarMateriales(), cargarSelects()]);
  } catch (e) {
    msg.textContent = "✗ " + e.message;
  }
}

async function crearReceta() {
  $("receta-msg").textContent = "";
  try {
    await api("/api/recetas", {
      method: "POST",
      body: JSON.stringify({
        nombre: $("r-nombre").value.trim(),
        min_tol: Number($("r-min").value),
        max_tol: Number($("r-max").value),
        espesor_mm: $("r-esp").value ? Number($("r-esp").value) : null,
        material_id: $("r-mat").value ? Number($("r-mat").value) : null,
      }),
    });
    $("receta-msg").textContent = "Receta creada ✓";
    $("r-nombre").value = "";
    await Promise.all([cargarRecetas(), cargarSelects()]);
  } catch (e) {
    $("receta-msg").textContent = "✗ " + e.message;
  }
}

/* ------------------------------------------------------------------ usuarios y auditoría */
async function cargarUsuarios() {
  try {
    const d = await api("/api/usuarios");
    estado.usuarios = d;
    $("usuarios-sub").textContent = `${d.length} cuentas registradas · ${d.filter((u) => u.activo).length} activas`;
    $("tabla-usuarios").innerHTML = d.map((u) => `
      <tr>
        <td class="mono">${esc(u.username)}</td>
        <td>${esc(u.nombre)}</td>
        <td><span class="chip info">${esc(u.rol)}</span></td>
        <td>${u.activo ? '<span class="estado aprobado">Activo</span>' : '<span class="estado rechazado">Inactivo</span>'}</td>
        <td>
          <div class="acciones">
            <button class="btn sec" onclick="cambiarEstadoUsuario(${u.id}, ${!u.activo})">
              ${u.activo ? "Desactivar" : "Activar"}</button>
            ${u.activo ? `<button class="btn peligro-suave" onclick="borrarUsuario(${u.id}, '${esc(u.username)}')">Borrar</button>` : ""}
          </div>
        </td>
      </tr>`).join("");
  } catch (e) {
    $("tabla-usuarios").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`;
  }
}

async function crearUsuario() {
  const msg = $("usuario-msg");
  msg.textContent = "";
  const username = $("u-username").value.trim();
  const nombre = $("u-nombre").value.trim();
  const pin = $("u-pin").value;
  if (!username || !nombre || !pin) { msg.textContent = "Complete usuario, nombre y PIN."; return; }
  try {
    await api("/api/usuarios", {
      method: "POST",
      body: JSON.stringify({ username, nombre, rol: $("u-rol").value, pin }),
    });
    msg.textContent = `Usuario «${username}» creado ✓`;
    $("u-username").value = ""; $("u-nombre").value = ""; $("u-pin").value = "";
    await cargarUsuarios();
  } catch (e) {
    msg.textContent = "✗ " + e.message;
  }
}

async function cambiarEstadoUsuario(id, activo) {
  try {
    await api("/api/usuarios/" + id, {
      method: "PATCH", body: JSON.stringify({ activo }),
    });
    await cargarUsuarios();
  } catch (e) {
    alert("No se pudo cambiar el estado: " + e.message);
  }
}

async function borrarUsuario(id, username) {
  if (!confirm(`¿Dar de baja la cuenta «${username}»?\n\nLa cuenta deja de poder ingresar, pero sus inspecciones y registros de auditoría se conservan.`)) return;
  try {
    const r = await api("/api/usuarios/" + id, { method: "DELETE" });
    await cargarUsuarios();
    $("usuario-msg").textContent = r.mensaje || "Cuenta desactivada";
  } catch (e) {
    alert("No se pudo borrar: " + e.message);
  }
}

async function cargarAuditoria() {
  try {
    const d = await api("/api/auditoria");
    $("tabla-auditoria").innerHTML = d.map((a) => `
      <tr><td>${fecha(a.fecha)}</td><td><span class="chip info">${esc(a.accion)}</span></td>
      <td>${esc(a.entidad)}</td><td class="mono">${a.entidad_id ?? "—"}</td>
      <td class="muted" style="font-size:.82rem">${esc(a.detalle || "")}</td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">Sin eventos.</td></tr>`;
  } catch (e) {
    $("tabla-auditoria").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`;
  }
}

/* ------------------------------------------------------------------ arranque */
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && $("pantalla-login").style.display !== "none") entrar(e);
});
