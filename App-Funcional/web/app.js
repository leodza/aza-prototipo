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
    estado.inactividadMin = j.inactividad_min || 20;
    $("pantalla-login").style.display = "none";
    $("app").style.display = "flex";
    $("nombre-usuario").textContent = j.usuario.nombre;
    $("rol-usuario").textContent = j.usuario.rol;
    $("avatar").textContent = j.usuario.nombre.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();
    $("chip-rol").textContent = "rol: " + j.usuario.rol;
    await arrancar();
  } catch (e) {
    $("login-error").textContent = e.message;
    if (/bloqueada/i.test(e.message)) $("login-error").textContent += " Puedes pedir el desbloqueo al administrador.";
  } finally {
    btn.disabled = false; btn.textContent = "Entrar";
  }
}

async function salir(motivo) {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { }
  estado.access = estado.refresh = estado.usuario = null;
  detenerInactividad();
  $("app").style.display = "none";
  $("pantalla-login").style.display = "grid";
  $("login-error").textContent = motivo || "";
  $("login-pin").value = "";
  $("login-usuario").value = "";
  $("login-usuario").focus();
}

async function arrancar() {
  const h = await api("/api/health");
  estado.motor = h.motor;
  $("chip-motor").textContent = h.motor.includes("APP-AZA") ? "motor: pipeline APP-AZA" : "motor: interno";
  $("chip-motor").className = h.motor.includes("APP-AZA") ? "chip ok" : "chip info";
  // La información técnica (motor de base de datos, cantidad de objetos) no se
  // muestra en la barra: es detalle de operación, no del trabajo diario.
  $("estado-api").textContent = "conectado";
  const pie = $("pie-base");
  if (pie) pie.textContent = h.base || "base de datos";
  aplicarPermisos();
  ocultarTecnico();
  iniciarInactividad();
  if ($("est-desde")) { $("est-desde").value = hoyLocal(); $("est-hasta").value = hoyLocal(); }
  if ($("inf-desde")) {
    $("inf-hasta").value = hoyLocal();
    const d0 = new Date(); d0.setDate(d0.getDate() - 83);
    $("inf-desde").value = d0.toISOString().slice(0, 10);
  }
  await Promise.all([cargarDashboard(), cargarSelects()]);
  if (rolActual() === "administrador") cargarConfiguracion();
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

const PERMISO_POR_VISTA = {
  simulador: "simular",
  historico: "ver_historico",
  auditoria: "ver_auditoria",
  estadisticas: "ver_estadisticas",
  recetas: "gestionar_recetas",
  usuarios: "gestionar_usuarios",
  respaldos: "gestionar_respaldos",
  configuracion: "gestionar_configuracion",
};

function aplicarPermisos() {
  const rol = rolActual();
  const permisos = (estado.usuario && estado.usuario.permisos) || [];
  document.querySelectorAll("nav button").forEach((b) => {
    const porRol = !b.dataset.roles || b.dataset.roles.split(",").includes(rol);
    const clave = PERMISO_POR_VISTA[b.dataset.vista];
    const porPermiso = !!clave && permisos.includes(clave);
    b.classList.toggle("oculto", !(porRol || porPermiso));
  });
  $("card-nuevo-usuario").classList.toggle("oculto", rol !== "administrador");
  const acciones = $("acciones-recetas");
  if (acciones) acciones.classList.toggle("oculto", rol !== "administrador");
}

/* El operador solo ve lo que necesita para operar: se ocultan los datos
   técnicos del motor y del almacenamiento. */
function ocultarTecnico() {
  if (rolActual() === "operador") {
    ["chip-motor", "pie-base"].forEach((id) => { const el = $(id); if (el) el.classList.add("oculto"); });
  }
}

function reloj() {
  const d = new Date();
  $("reloj").textContent =
    `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
}

/* ------------------------------------------------------------------ navegación */
const TITULOS = {
  dashboard: "Dashboard", historico: "Histórico de inspecciones",
  alarmas: "Alarmas de tolerancia", configuracion: "Configuración",
  estadisticas: "Estadísticas por operador", informe: "Informe de gestión",
  respaldos: "Respaldos de la base", detalle: "Detalle de la inspección",
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
  if (vista === "alarmas") cargarAlarmas();
  if (vista === "configuracion") { cargarConfiguracion(); cargarSolicitudes(); }
  if (vista === "estadisticas") { cargarEstadisticas(); cargarSelectsOperadores(); }
  if (vista === "informe") cargarInforme();
  if (vista === "respaldos") cargarRespaldos();
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
    const selOper = $("f-operador");
    if (selOper) {
      try {
        const usuarios = await api("/api/usuarios");
        selOper.innerHTML = `<option value="">Todos</option>` +
          usuarios.map((u) => `<option value="${esc(u.username)}">${esc(u.nombre)}</option>`).join("");
      } catch (_) { selOper.innerHTML = `<option value="">Todos</option>`; }
    }
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
  if ($("f-operador") && $("f-operador").value) q.set("operador", $("f-operador").value);
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
  if (!confirm("¿Limpiar todos los filtros de la consulta?\n\nNo se borra ningún registro: " +
               "solo se restablecen los filtros al día de hoy.")) return;
  ["f-receta", "f-lote", "f-estado", "f-operador"].forEach((id) => {
    const el = $(id); if (el) el.value = "";
  });
  const hoy = hoyLocal();
  $("f-desde").value = hoy; $("f-hasta").value = hoy;
  cargarHistorico(1);
}

function exportarCSV() {
  const d = estado.ultimoHist;
  if (!d || !d.items.length) { alert("No hay resultados para exportar."); return; }
  const cab = ["id", "fecha_hora", "receta", "receta_id", "lote", "batch", "batch_id",
    "material", "operador", "angulo", "limite_min", "limite_max", "estado", "origen",
    "velocidad_m_min", "desviacion_deg", "objeto"];
  const filas = d.items.map((i) => [i.id, i.fecha_hora, i.receta, i.receta_id, i.lote,
    i.batch, i.batch_id, i.materialidad, i.operador, i.angulo, i.limite_min, i.limite_max,
    i.estado, i.origen, i.velocidad_m_min, i.desviacion_deg, i.imagen_clave]
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

function velocidadManual(valor) {
  const v = Math.max(4, Math.min(30, Number(valor) || 12));
  const slider = sim-velocidad;
  if (slider) slider.value = v;
  actualizarVelocidad('numero');
}

function actualizarVelocidad(origen) {
  const v = Number($("sim-velocidad").value);
  const campo = $("sim-velocidad-num");
  if (campo && origen !== "numero") campo.value = v;
  if ($("sim-velocidad-valor")) $("sim-velocidad-valor").textContent = num(v);
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
            <button class="btn sec" onclick="abrirPermisos(${u.id})">Permisos</button>
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
      <td class="detalle-largo">${esc(a.detalle_texto || a.detalle || "")}</td></tr>`).join("")
      || `<tr><td colspan="5" class="muted">Sin eventos.</td></tr>`;
  } catch (e) {
    $("tabla-auditoria").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`;
  }
}

/* ------------------------------------------------------------------ arranque */
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && $("pantalla-login").style.display !== "none") entrar(e);
});


/* ==================================================================== */
/*  Modales                                                            */
/* ==================================================================== */
function abrirModal(id) {
  const m = $(id);
  if (m) m.hidden = false;
}

function cerrarModal(id) {
  const m = $(id);
  if (m) m.hidden = true;
}

function cerrarModalFondo(ev, id) {
  if (ev.target.id === id) cerrarModal(id);
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.querySelectorAll(".modal-fondo:not([hidden])")
    .forEach((m) => { m.hidden = true; });
});

/* ==================================================================== */
/*  Olvidé mi contraseña                                               */
/* ==================================================================== */
function olvidarClave() {
  $("olvido-ident").value = $("login-usuario").value.trim();
  $("olvido-msg").textContent = "";
  abrirModal("modal-olvido");
  $("olvido-ident").focus();
}

async function enviarOlvido() {
  const ident = $("olvido-ident").value.trim();
  const msg = $("olvido-msg");
  if (ident.length < 3) { msg.textContent = "Escribe tu usuario, correo o nombre."; return; }
  try {
    const r = await api("/api/auth/olvido", {
      method: "POST", body: JSON.stringify({ identificador: ident }),
    }, false);
    msg.textContent = r.mensaje;
    setTimeout(() => cerrarModal("modal-olvido"), 2200);
  } catch (e) {
    msg.textContent = "No se pudo enviar: " + e.message;
  }
}

/* ==================================================================== */
/*  Configuración (administrador)                                      */
/* ==================================================================== */
async function cargarConfiguracion() {
  try {
    const d = await api("/api/configuracion");
    $("cfg-intentos").value = d.max_intentos.valor;
    $("cfg-bloqueo").value = d.bloqueo_min.valor;
    $("cfg-inactividad").value = d.inactividad_min.valor;
    $("cfg-sesion").value = String(d.sesion_unica.valor);
    const u = estado.usuario || {};
    if (u.rol === "administrador") estado.inactividadMin = d.inactividad_min.valor;
  } catch (e) {
    $("cfg-msg").textContent = "No se pudo leer la configuración: " + e.message;
  }
}

async function guardarConfiguracion() {
  const msg = $("cfg-msg");
  msg.textContent = "Guardando…";
  try {
    await api("/api/configuracion", {
      method: "PUT",
      body: JSON.stringify({
        max_intentos: Number($("cfg-intentos").value),
        bloqueo_min: Number($("cfg-bloqueo").value),
        inactividad_min: Number($("cfg-inactividad").value),
        sesion_unica: Number($("cfg-sesion").value),
      }),
    });
    msg.textContent = "Cambios guardados ✓";
    estado.inactividadMin = Number($("cfg-inactividad").value);
    reiniciarInactividad();
  } catch (e) {
    msg.textContent = "✗ " + e.message;
  }
}

async function cargarSolicitudes() {
  const cuerpo = $("tabla-solicitudes");
  try {
    const d = await api("/api/solicitudes");
    const pend = d.filter((x) => x.estado === "pendiente").length;
    cuerpo.innerHTML = d.map((x) => `
      <tr>
        <td class="mono">#${x.id}</td>
        <td class="mono">${esc(x.identificador)}</td>
        <td>${esc(x.usuario || "—")}</td>
        <td class="mono">${fecha(x.creada_en)}</td>
        <td>${x.estado === "pendiente"
              ? '<span class="chip warn">pendiente</span>'
              : '<span class="chip ok">atendida</span>'}</td>
        <td>${x.estado === "pendiente"
              ? `<button class="btn sec" onclick="resolverSolicitud(${x.id})">Restablecer</button>`
              : "—"}</td>
      </tr>`).join("") || `<tr><td colspan="6" class="muted">Sin solicitudes registradas.</td></tr>`;
    const sub = $("tabla-solicitudes").closest(".card").querySelector(".sub");
    if (sub) sub.textContent = `${pend} pendiente(s) de atender`;
  } catch (e) {
    cuerpo.innerHTML = `<tr><td colspan="6" class="muted">${esc(e.message)}</td></tr>`;
  }
}

async function resolverSolicitud(id) {
  const clave = prompt("Nueva contraseña para el usuario (mínimo 8 caracteres,\ncon mayúscula, minúscula y número):");
  if (!clave) return;
  const nota = prompt("Nota para la bitácora (opcional):") || null;
  try {
    await api(`/api/solicitudes/${id}/resolver`, {
      method: "POST", body: JSON.stringify({ nueva_clave: clave, nota }),
    });
    await cargarSolicitudes();
    alert("Contraseña restablecida. La cuenta quedó activa y desbloqueada.");
  } catch (e) {
    alert("No se pudo restablecer: " + e.message);
  }
}

/* ==================================================================== */
/*  Alarmas                                                            */
/* ==================================================================== */
const ALARMA_ETIQUETA = {
  pendiente: "Pendiente", en_revision: "En revisión", solucionada: "Solucionada",
};
let alarmaAbierta = null;

async function cargarAlarmas() {
  const cuerpo = $("tabla-alarmas");
  if (!cuerpo) return;
  const filtro = $("f-estado-alarma") ? $("f-estado-alarma").value : "";
  try {
    let d = await api("/api/alarmas");
    if (filtro) d = d.filter((a) => a.estado === filtro);
    const pend = d.filter((a) => a.estado !== "solucionada").length;
    $("alarmas-sub").textContent =
      `${d.length} alarmas · ${pend} sin cerrar`;
    cuerpo.innerHTML = d.map((a) => `
      <tr>
        <td class="mono">${String(a.id).padStart(3, "0")}</td>
        <td class="mono">${fecha(a.creada_en)}</td>
        <td>${a.severidad === "alta"
              ? '<span class="estado rechazado">alta</span>'
              : '<span class="estado sin_receta">media</span>'}</td>
        <td>${esc(a.receta || "—")} <span class="muted mono">${esc(a.lote || "")}</span></td>
        <td class="num mono">${a.angulo === null ? "—" : num(a.angulo) + "°"}</td>
        <td><span class="alarma-estado ${a.estado}">${ALARMA_ETIQUETA[a.estado] || a.estado}</span></td>
        <td class="detalle-largo">${esc(a.solucion || "—")}</td>
        <td>${a.estado === "solucionada" ? "—"
              : `<button class="btn sec" onclick="abrirAlarma(${a.id})">Revisar</button>`}</td>
      </tr>`).join("") || `<tr><td colspan="8" class="muted">No hay alarmas con ese filtro.</td></tr>`;
    estado.alarmas = d;
  } catch (e) {
    cuerpo.innerHTML = `<tr><td colspan="8" class="muted">${esc(e.message)}</td></tr>`;
  }
}

function abrirAlarma(id) {
  const a = (estado.alarmas || []).find((x) => x.id === id);
  if (!a) return;
  alarmaAbierta = id;
  $("alarma-titulo").textContent = `Alarma #${a.id} · ${ALARMA_ETIQUETA[a.estado] || a.estado}`;
  $("alarma-sub").textContent =
    `${a.mensaje || ""} · receta ${a.receta || "—"} ${a.lote ? "· lote " + a.lote : ""}`;
  $("alarma-solucion").value = a.solucion || "";
  $("alarma-msg").textContent = "";
  abrirModal("modal-alarma");
}

async function cambiarAlarma(nuevoEstado) {
  if (!alarmaAbierta) return;
  const solucion = $("alarma-solucion").value.trim();
  const msg = $("alarma-msg");
  msg.textContent = "Guardando…";
  try {
    await api(`/api/alarmas/${alarmaAbierta}`, {
      method: "PATCH", body: JSON.stringify({ estado: nuevoEstado, solucion }),
    });
    cerrarModal("modal-alarma");
    await cargarAlarmas();
    await cargarDashboard();
  } catch (e) {
    msg.textContent = "✗ " + e.message;
  }
}

/* ==================================================================== */
/*  Cierre por inactividad                                             */
/* ==================================================================== */
let temporizadorInactividad = null;
let ultimaActividad = Date.now();

function reiniciarInactividad() {
  ultimaActividad = Date.now();
}

function detenerInactividad() {
  if (temporizadorInactividad) clearInterval(temporizadorInactividad);
  temporizadorInactividad = null;
}

function iniciarInactividad() {
  detenerInactividad();
  ultimaActividad = Date.now();
  ["click", "keydown", "mousemove", "scroll"].forEach((ev) =>
    document.addEventListener(ev, reiniciarInactividad, { passive: true }));
  temporizadorInactividad = setInterval(() => {
    if (!estado.usuario) return;
    const minutos = (Date.now() - ultimaActividad) / 60000;
    if (minutos >= (estado.inactividadMin || 20)) {
      salir("La sesión se cerró por inactividad. Vuelve a entrar.");
    }
  }, 15000);
}

/* ==================================================================== */
/*  Estadísticas por operador                                          */
/* ==================================================================== */
async function cargarEstadisticas() {
  const cuerpo = $("tabla-estadisticas");
  if (!cuerpo) return;
  const q = new URLSearchParams();
  if ($("est-desde").value) q.set("desde", $("est-desde").value);
  if ($("est-hasta").value) q.set("hasta", $("est-hasta").value);
  try {
    const d = await api("/api/estadisticas/operadores?" + q);
    const total = d.reduce((a, x) => a + x.total, 0);
    const aprob = d.reduce((a, x) => a + x.aprobadas, 0);
    $("est-sub").textContent = d.length
      ? `${total} inspecciones · ${aprob} aprobadas (${total ? Math.round(100 * aprob / total) : 0} % del total)`
      : "Sin datos en el período";

    dibujarGraficoOperadores(d);

    cuerpo.innerHTML = d.map((o) => {
      const nivel = o.aprobacion_pct >= 90 ? ["Alto", "aprobado"]
        : o.aprobacion_pct >= 75 ? ["Medio", "sin_receta"] : ["A revisar", "rechazado"];
      return `
      <tr>
        <td><strong>${esc(o.nombre)}</strong><div class="muted mono">${esc(o.username)}</div></td>
        <td class="num mono">${o.total}</td>
        <td class="num mono">${o.aprobadas}</td>
        <td class="num mono">${o.rechazadas}</td>
        <td class="num mono"><strong>${num(o.aprobacion_pct)} %</strong></td>
        <td class="num mono">${o.angulo_medio === null ? "—" : num(o.angulo_medio) + "°"}</td>
        <td class="num mono">${o.duracion_media_ms ? (o.duracion_media_ms / 1000).toFixed(1) + " s" : "—"}</td>
        <td><span class="estado ${nivel[1]}">${nivel[0]}</span></td>
      </tr>`;
    }).join("") || `<tr><td colspan="8" class="muted">Sin inspecciones en el período.</td></tr>`;
  } catch (e) {
    cuerpo.innerHTML = `<tr><td colspan="8" class="muted">${esc(e.message)}</td></tr>`;
  }
}

function dibujarGraficoOperadores(datos) {
  const caja = $("est-grafico");
  if (!caja) return;
  if (!datos.length) { caja.innerHTML = `<div class="muted">Sin datos para graficar.</div>`; return; }
  const altoFila = 44;
  const alto = datos.length * altoFila + 26;
  const ancho = 760;
  const margenEtiqueta = 150;
  const maxTotal = Math.max(...datos.map((d) => d.total), 1);
  const escala = (ancho - margenEtiqueta - 90) / maxTotal;

  const filas = datos.map((o, i) => {
    const y = 14 + i * altoFila;
    const anchoAprob = o.aprobadas * escala;
    const anchoRech = o.rechazadas * escala;
    const anchoSin = o.sin_receta * escala;
    return `
      <g>
        <text x="0" y="${y + 18}" class="g-etq">${esc(o.nombre.split(" ")[0])}</text>
        <rect x="${margenEtiqueta}" y="${y}" width="${anchoAprob}" height="20" rx="4" class="g-aprob"></rect>
        <rect x="${margenEtiqueta + anchoAprob}" y="${y}" width="${anchoRech}" height="20" rx="4" class="g-rech"></rect>
        <rect x="${margenEtiqueta + anchoAprob + anchoRech}" y="${y}" width="${anchoSin}" height="20" rx="4" class="g-sin"></rect>
        <text x="${margenEtiqueta + anchoAprob + anchoRech + anchoSin + 10}" y="${y + 15}"
              class="g-val">${num(o.aprobacion_pct)} % · ${o.total}</text>
      </g>`;
  }).join("");

  caja.innerHTML = `
    <svg viewBox="0 0 ${ancho} ${alto}" class="grafico-operadores" role="img"
         aria-label="Comparación de operadores">
      ${filas}
    </svg>
    <div class="leyenda-graf">
      <span><i class="lg-aprob"></i>aprobadas</span>
      <span><i class="lg-rech"></i>rechazadas</span>
      <span><i class="lg-sin"></i>sin receta</span>
    </div>`;
}

/* ==================================================================== */
/*  Respaldos                                                          */
/* ==================================================================== */
async function cargarRespaldos() {
  const cuerpo = $("tabla-respaldos");
  if (!cuerpo) return;
  try {
    const d = await api("/api/respaldos");
    const lista = d.respaldos || [];
    const cfg = d.configuracion || {};
    $("resp-sub").textContent =
      `${lista.length} copias · automático cada ${cfg.horas} h · se conservan ${cfg.maximo}`;

    cuerpo.innerHTML = lista.map((r) => {
      const origen = /automatico/.test(r.archivo) ? "automático" : "manual";
      return `
      <tr>
        <td class="mono">${esc(r.archivo.replace("respaldo-", ""))}</td>
        <td class="mono">${fecha(r.generado)}</td>
        <td class="num mono">${r.total}</td>
        <td class="num mono">${(r.bytes / 1024).toFixed(0)} KB</td>
        <td>${origen === "automático"
              ? '<span class="chip info">automático</span>'
              : '<span class="chip">manual</span>'}</td>
        <td style="white-space:nowrap">
          <button class="btn sec" onclick="descargarRespaldo('${esc(r.archivo)}')">Descargar</button>
          <button class="btn peligro-suave" onclick="restaurarRespaldo('${esc(r.archivo)}')">Restaurar</button>
        </td>
      </tr>`;
    }).join("") || `<tr><td colspan="6" class="muted">Todavía no hay respaldos.</td></tr>`;

    const opciones = lista.map((r) =>
      `<option value="${esc(r.archivo)}">${fecha(r.generado)} · ${r.total} reg.</option>`).join("");
    if ($("cmp-a")) $("cmp-a").innerHTML = opciones;
    if ($("cmp-b")) $("cmp-b").innerHTML = opciones;
    if (lista.length > 1 && $("cmp-a")) $("cmp-a").selectedIndex = 1;
  } catch (e) {
    cuerpo.innerHTML = `<tr><td colspan="6" class="muted">${esc(e.message)}</td></tr>`;
  }
}

async function crearRespaldo() {
  try {
    const r = await api("/api/respaldos", { method: "POST" });
    await cargarRespaldos();
    alert(`Respaldo creado: ${r.total} registros, huella ${r.huella}`);
  } catch (e) {
    alert("No se pudo crear el respaldo: " + e.message);
  }
}

async function descargarRespaldo(archivo) {
  try {
    const r = await fetch(`/api/respaldos/${encodeURIComponent(archivo)}`, {
      headers: { Authorization: "Bearer " + estado.access },
    });
    if (!r.ok) throw new Error("No se pudo descargar");
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = archivo;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert(e.message);
  }
}

async function restaurarRespaldo(archivo) {
  if (!confirm(`¿Restaurar «${archivo}»?\n\nSe reemplaza el contenido actual de la base por el de esa copia.`)) return;
  if (!confirm("Esta acción no se puede deshacer. ¿Confirmas la restauración?")) return;
  try {
    const r = await api("/api/respaldos/restaurar", {
      method: "POST", body: JSON.stringify({ archivo }),
    });
    alert(`Restaurado. Registros recuperados: ${r.insertados.inspecciones} inspecciones, ` +
          `${r.insertados.usuarios} usuarios.`);
    await cargarRespaldos();
    await cargarDashboard();
  } catch (e) {
    alert("No se pudo restaurar: " + e.message);
  }
}

async function compararRespaldos() {
  const caja = $("cmp-resultado");
  const a = $("cmp-a").value, b = $("cmp-b").value;
  if (!a || !b) { caja.innerHTML = `<div class="muted">Selecciona dos respaldos.</div>`; return; }
  try {
    const d = await api("/api/respaldos/comparar", {
      method: "POST", body: JSON.stringify({ a, b }),
    });
    const filas = d.tablas.map((f) => `
      <tr><td>${esc(f.tabla)}</td><td class="num mono">${f.a}</td><td class="num mono">${f.b}</td>
      <td class="num mono" style="color:${f.diferencia > 0 ? "var(--verde)" : f.diferencia < 0 ? "var(--rojo)" : "var(--texto-3)"}">
        ${f.diferencia > 0 ? "+" : ""}${f.diferencia}</td></tr>`).join("");
    caja.innerHTML = `
      <div class="banner ${d.iguales ? "verde" : "ambar"}" style="margin-top:14px">
        ${d.iguales ? "Los dos respaldos tienen el mismo contenido (huella idéntica)."
                    : `Contenido distinto: ${d.a.total} registros en A frente a ${d.b.total} en B.`}
      </div>
      <table><thead><tr><th>Tabla</th><th class="num">A</th><th class="num">B</th><th class="num">Diferencia</th></tr></thead>
      <tbody>${filas}</tbody></table>`;
  } catch (e) {
    caja.innerHTML = `<div class="muted">${esc(e.message)}</div>`;
  }
}

/* ==================================================================== */
/*  Comparador por pares de operadores                                 */
/* ==================================================================== */
let comparacionActual = null;

async function cargarSelectsOperadores() {
  try {
    const d = await api("/api/estadisticas/operadores");
    const opciones = d.map((o) => `<option value="${esc(o.username)}">${esc(o.nombre)}</option>`).join("");
    ["cmp-operador-a", "cmp-operador-b"].forEach((id) => {
      const sel = $(id);
      if (sel) { sel.innerHTML = opciones; }
    });
    if ($("cmp-operador-b") && $("cmp-operador-b").options.length > 1) $("cmp-operador-b").selectedIndex = 1;
  } catch (_) { }
}

async function compararOperadores() {
  const caja = $("cmp-operadores-resultado");
  const a = $("cmp-operador-a").value;
  const b = $("cmp-operador-b").value;
  if (!a || !b) { caja.innerHTML = `<div class="muted">Elige dos operadores.</div>`; return; }
  if (a === b) { caja.innerHTML = `<div class="muted">Elige dos operadores distintos.</div>`; return; }
  const q = new URLSearchParams({ a, b });
  if ($("est-desde").value) q.set("desde", $("est-desde").value);
  if ($("est-hasta").value) q.set("hasta", $("est-hasta").value);
  try {
    const d = await api("/api/estadisticas/comparar?" + q);
    comparacionActual = d;
    const [x, y] = d.operadores;
    const fila = (etq, va, vb, mejor) => `
      <tr><td>${etq}</td>
        <td class="num mono ${mejor === "a" ? "gana" : ""}">${va}</td>
        <td class="num mono ${mejor === "b" ? "gana" : ""}">${vb}</td></tr>`;
    const recetasA = x.recetas.map((r) => `<li><b>${esc(r.receta)}</b> · ${r.total} (${num(r.pct)} %)</li>`).join("") || "<li class='muted'>—</li>";
    const recetasB = y.recetas.map((r) => `<li><b>${esc(r.receta)}</b> · ${r.total} (${num(r.pct)} %)</li>`).join("") || "<li class='muted'>—</li>";

    caja.innerHTML = `
      <div class="dos-col" style="margin-top:16px">
        <div class="card" style="margin:0">
          <h3>${esc(x.nombre)}</h3>
          <div class="sub mono">${esc(x.username)} · ${esc(x.rol)}</div>
          <ul class="lista-simple">${recetasA}</ul>
        </div>
        <div class="card" style="margin:0">
          <h3>${esc(y.nombre)}</h3>
          <div class="sub mono">${esc(y.username)} · ${esc(y.rol)}</div>
          <ul class="lista-simple">${recetasB}</ul>
        </div>
      </div>
      <table style="margin-top:14px">
        <thead><tr><th>Métrica</th><th class="num">${esc(x.nombre)}</th>
          <th class="num">${esc(y.nombre)}</th></tr></thead>
        <tbody>
          ${fila("Inspecciones", x.total, y.total, d.veredicto.volumen === a ? "a" : d.veredicto.volumen === b ? "b" : "")}
          ${fila("Aprobadas", x.aprobadas, y.aprobadas, "")}
          ${fila("Rechazadas", x.rechazadas, y.rechazadas, "")}
          ${fila("% aprobación", num(x.aprobacion_pct) + " %", num(y.aprobacion_pct) + " %",
                 d.veredicto.calidad === a ? "a" : d.veredicto.calidad === b ? "b" : "")}
          ${fila("Ángulo medio", x.angulo_medio === null ? "—" : num(x.angulo_medio) + "°",
                 y.angulo_medio === null ? "—" : num(y.angulo_medio) + "°", "")}
          ${fila("Rango de ángulo",
                 x.angulo_min === null ? "—" : num(x.angulo_min) + "° – " + num(x.angulo_max) + "°",
                 y.angulo_min === null ? "—" : num(y.angulo_min) + "° – " + num(y.angulo_max) + "°", "")}
          ${fila("Tiempo medio", x.duracion_media_ms ? (x.duracion_media_ms / 1000).toFixed(1) + " s" : "—",
                 y.duracion_media_ms ? (y.duracion_media_ms / 1000).toFixed(1) + " s" : "—",
                 d.veredicto.velocidad === a ? "a" : d.veredicto.velocidad === b ? "b" : "")}
        </tbody>
      </table>
      <div class="banner" style="margin-top:14px">
        <strong>Veredicto:</strong>
        volumen → <b>${esc(nombreDe(d.veredicto.volumen))}</b> ·
        calidad → <b>${esc(nombreDe(d.veredicto.calidad))}</b> ·
        velocidad → <b>${esc(nombreDe(d.veredicto.velocidad))}</b>
      </div>
      <div class="sub" style="margin-top:6px">
        Recetas en común: ${d.recetas.comunes.length ? d.recetas.comunes.map(esc).join(", ") : "ninguna"} ·
        solo ${esc(x.nombre)}: ${d.recetas.solo_a.length ? d.recetas.solo_a.map(esc).join(", ") : "—"} ·
        solo ${esc(y.nombre)}: ${d.recetas.solo_b.length ? d.recetas.solo_b.map(esc).join(", ") : "—"}
      </div>`;
  } catch (e) {
    caja.innerHTML = `<div class="muted">${esc(e.message)}</div>`;
  }
}

function nombreDe(username) {
  if (!comparacionActual) return "empate";
  const o = comparacionActual.operadores.find((x) => x.username === username);
  return o ? o.nombre : "empate";
}

function descargarInformeComparacion() {
  if (!comparacionActual) { alert("Primero compara dos operadores."); return; }
  const d = comparacionActual;
  const [x, y] = d.operadores;
  const filas = (etq, va, vb) => `<tr><td>${etq}</td><td>${va}</td><td>${vb}</td></tr>`;
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
    <title>Comparación de operadores · AZA Analyzer</title>
    <style>
      body{font-family:Segoe UI,system-ui,sans-serif;color:#111;margin:38px;font-size:13px}
      h1{font-size:20px;margin:0 0 4px} .sub{color:#555;margin-bottom:18px}
      table{width:100%;border-collapse:collapse;margin:12px 0}
      th,td{border:1px solid #ccc;padding:7px 9px;text-align:left}
      th{background:#eee} td:nth-child(2),td:nth-child(3){text-align:right}
      .box{border:1px solid #ccc;padding:10px 12px;border-radius:6px;margin-top:10px}
    </style></head><body>
    <h1>Comparación de operadores</h1>
    <div class="sub">AZA Analyzer · ${new Date().toLocaleString("es-CL")}
      ${d.periodo.desde || d.periodo.hasta
        ? " · período " + (d.periodo.desde || "inicio") + " a " + (d.periodo.hasta || "hoy") : ""}</div>
    <table>
      <tr><th>Métrica</th><th>${esc(x.nombre)}</th><th>${esc(y.nombre)}</th></tr>
      ${filas("Inspecciones", x.total, y.total)}
      ${filas("Aprobadas", x.aprobadas, y.aprobadas)}
      ${filas("Rechazadas", x.rechazadas, y.rechazadas)}
      ${filas("% aprobación", x.aprobacion_pct + " %", y.aprobacion_pct + " %")}
      ${filas("Ángulo medio", (x.angulo_medio ?? "—") + "°", (y.angulo_medio ?? "—") + "°")}
      ${filas("Tiempo medio", x.duracion_media_ms ? (x.duracion_media_ms / 1000).toFixed(1) + " s" : "—",
              y.duracion_media_ms ? (y.duracion_media_ms / 1000).toFixed(1) + " s" : "—")}
    </table>
    <div class="box"><b>Recetas usadas por ${esc(x.nombre)}:</b>
      ${x.recetas.map((r) => `${esc(r.receta)} (${r.total})`).join(", ") || "—"}</div>
    <div class="box"><b>Recetas usadas por ${esc(y.nombre)}:</b>
      ${y.recetas.map((r) => `${esc(r.receta)} (${r.total})`).join(", ") || "—"}</div>
    <div class="box"><b>Veredicto:</b> volumen → ${esc(nombreDe(d.veredicto.volumen))} ·
      calidad → ${esc(nombreDe(d.veredicto.calidad))} ·
      velocidad → ${esc(nombreDe(d.veredicto.velocidad))}</div>
    </body></html>`;
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `comparacion-${x.username}-vs-${y.username}.html`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ==================================================================== */
/*  Permisos por usuario                                               */
/* ==================================================================== */
let usuarioPermisos = null;

async function abrirPermisos(id) {
  const u = (estado.usuarios || []).find((x) => x.id === id);
  if (!u) return;
  usuarioPermisos = id;
  $("perm-titulo").textContent = "Permisos de " + u.nombre;
  $("perm-msg").textContent = "";
  try {
    const catalogo = await api("/api/permisos");
    $("perm-lista").innerHTML = catalogo.map((p) => `
      <label class="perm-item">
        <input type="checkbox" value="${p.clave}" ${(u.permisos || []).includes(p.clave) ? "checked" : ""}>
        <span><b>${esc(p.clave)}</b><br><small class="muted">${esc(p.descripcion)}</small></span>
      </label>`).join("");
    abrirModal("modal-permisos");
  } catch (e) {
    $("perm-msg").textContent = e.message;
  }
}

async function guardarPermisos() {
  if (!usuarioPermisos) return;
  const marcados = [...document.querySelectorAll("#perm-lista input:checked")].map((i) => i.value);
  try {
    await api(`/api/usuarios/${usuarioPermisos}/permisos`, {
      method: "PUT", body: JSON.stringify({ permisos: marcados }),
    });
    cerrarModal("modal-permisos");
    await cargarUsuarios();
    alert("Permisos actualizados. El usuario los verá al volver a iniciar sesión.");
  } catch (e) {
    $("perm-msg").textContent = "✗ " + e.message;
  }
}

/* ==================================================================== */
/*  Informe de gestión por períodos                                    */
/* ==================================================================== */
let informeActual = null;

async function cargarInforme() {
  const q = new URLSearchParams({ granularidad: $("inf-gran").value || "semana" });
  if ($("inf-desde").value) q.set("desde", $("inf-desde").value);
  if ($("inf-hasta").value) q.set("hasta", $("inf-hasta").value);
  try {
    const d = await api("/api/estadisticas/periodos?" + q);
    informeActual = d;

    const varTotal = d.variacion.total === null ? "—"
      : (d.variacion.total > 0 ? "+" : "") + num(d.variacion.total) + " %";
    const varClase = d.variacion.total === null ? "" : d.variacion.total >= 0 ? "pos" : "neg";
    $("inf-kpis").innerHTML = `
      <div class="card kpi"><div class="etq">Inspecciones</div>
        <div class="valor">${d.totales.total}</div>
        <div class="delta ${varClase}">${varTotal} vs período anterior</div></div>
      <div class="card kpi"><div class="etq">Aprobadas</div>
        <div class="valor" style="color:var(--verde)">${d.totales.aprobadas}</div>
        <div class="delta">${d.aprobacion_pct} % del total</div></div>
      <div class="card kpi"><div class="etq">Rechazadas</div>
        <div class="valor" style="color:var(--rojo)">${d.totales.rechazadas}</div>
        <div class="delta">${d.anterior.aprobacion_pct} % aprobación previa</div></div>
      <div class="card kpi"><div class="etq">Períodos</div>
        <div class="valor">${d.periodos.length}</div>
        <div class="delta">${d.granularidad === "semana" ? "semanas" : "meses"} analizados</div></div>`;

    $("inf-sub").textContent =
      `${d.rango.desde} a ${d.rango.hasta} · comparado con ${d.anterior.rango.desde} a ${d.anterior.rango.hasta}`;

    dibujarGraficoPeriodos(d.periodos);

    $("tabla-informe").innerHTML = d.periodos.map((p) => `
      <tr>
        <td><strong>${esc(p.etiqueta)}</strong></td>
        <td class="mono">${p.desde}</td>
        <td class="mono">${p.hasta}</td>
        <td class="num mono">${p.total}</td>
        <td class="num mono">${p.aprobadas}</td>
        <td class="num mono">${p.rechazadas}</td>
        <td class="num mono">${num(p.aprobacion_pct)} %</td>
        <td class="num mono">${p.angulo_medio === null ? "—" : num(p.angulo_medio) + "°"}</td>
      </tr>`).join("") || `<tr><td colspan="8" class="muted">Sin datos en el rango elegido.</td></tr>`;
  } catch (e) {
    $("inf-sub").textContent = "Error: " + e.message;
  }
}

function dibujarGraficoPeriodos(periodos) {
  const caja = $("inf-grafico");
  if (!caja) return;
  if (!periodos.length) { caja.innerHTML = `<div class="muted">Sin datos para graficar.</div>`; return; }
  const ancho = 820, alto = 220, base = 180, techo = 20;
  const max = Math.max(...periodos.map((p) => p.total), 1);
  const paso = (ancho - 60) / periodos.length;
  const barras = periodos.map((p, i) => {
    const x = 40 + i * paso + paso * 0.15;
    const anchoB = paso * 0.7;
    const altoTotal = (base - techo) * (p.total / max);
    const altoAprob = altoTotal * (p.aprobadas / (p.total || 1));
    return `
      <rect x="${x}" y="${base - altoTotal}" width="${anchoB}" height="${altoTotal}"
            rx="4" class="g-rech" opacity=".85"></rect>
      <rect x="${x}" y="${base - altoAprob}" width="${anchoB}" height="${altoAprob}"
            rx="4" class="g-aprob"></rect>
      <text x="${x + anchoB / 2}" y="${base - altoTotal - 6}" class="g-val"
            text-anchor="middle">${p.total}</text>
      <text x="${x + anchoB / 2}" y="${base + 16}" class="g-etq" text-anchor="middle"
            font-size="10">${esc(p.etiqueta.replace("Semana ", "S").replace(" · ", "/"))}</text>`;
  }).join("");
  caja.innerHTML = `
    <svg viewBox="0 0 ${ancho} ${alto}" class="grafico-operadores" role="img"
         aria-label="Producción por período">
      <line x1="30" y1="${base}" x2="${ancho - 10}" y2="${base}" class="g-eje"></line>
      ${barras}
    </svg>
    <div class="leyenda-graf">
      <span><i class="lg-aprob"></i>aprobadas</span>
      <span><i class="lg-rech"></i>rechazadas o sin receta</span>
    </div>`;
}

function descargarInformePeriodos() {
  if (!informeActual) { alert("Primero genera el informe."); return; }
  const d = informeActual;
  const filas = d.periodos.map((p) => `
    <tr><td>${esc(p.etiqueta)}</td><td>${p.desde}</td><td>${p.hasta}</td>
    <td>${p.total}</td><td>${p.aprobadas}</td><td>${p.rechazadas}</td>
    <td>${p.aprobacion_pct} %</td><td>${p.angulo_medio ?? "—"}°</td></tr>`).join("");
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
    <title>Informe de gestión · AZA Analyzer</title>
    <style>
      body{font-family:Segoe UI,system-ui,sans-serif;color:#111;margin:38px;font-size:13px}
      h1{font-size:20px;margin:0 0 4px} h2{font-size:15px;margin:22px 0 8px}
      .sub{color:#555;margin-bottom:16px}
      table{width:100%;border-collapse:collapse;margin:10px 0}
      th,td{border:1px solid #ccc;padding:7px 9px}
      th{background:#eee;text-align:left} td:nth-child(n+4){text-align:right}
      .kpi{display:inline-block;border:1px solid #ccc;border-radius:6px;padding:10px 14px;margin-right:10px}
      .kpi b{display:block;font-size:20px}
    </style></head><body>
    <h1>Informe de gestión · ${d.granularidad === "semana" ? "semanal" : "mensual"}</h1>
    <div class="sub">AZA Analyzer · ${d.rango.desde} a ${d.rango.hasta} ·
      comparado con ${d.anterior.rango.desde} a ${d.anterior.rango.hasta}</div>
    <div>
      <span class="kpi">Inspecciones <b>${d.totales.total}</b></span>
      <span class="kpi">Aprobadas <b>${d.totales.aprobadas}</b></span>
      <span class="kpi">Rechazadas <b>${d.totales.rechazadas}</b></span>
      <span class="kpi">% aprobación <b>${d.aprobacion_pct} %</b></span>
    </div>
    <h2>Detalle por período</h2>
    <table><tr><th>Período</th><th>Desde</th><th>Hasta</th><th>Total</th><th>Aprobadas</th>
      <th>Rechazadas</th><th>% aprobación</th><th>Ángulo medio</th></tr>${filas}</table>
    <h2>Variación frente al período anterior</h2>
    <table><tr><th>Métrica</th><th>Variación</th></tr>
      <tr><td>Inspecciones</td><td>${d.variacion.total ?? "—"} %</td></tr>
      <tr><td>Aprobadas</td><td>${d.variacion.aprobadas ?? "—"} %</td></tr>
      <tr><td>Rechazadas</td><td>${d.variacion.rechazadas ?? "—"} %</td></tr>
    </table>
    </body></html>`;
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `informe-${d.granularidad}-${d.rango.desde}.html`;
  a.click();
  URL.revokeObjectURL(a.href);
}
