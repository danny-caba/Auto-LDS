"use strict";

const FASES_TERMINALES = new Set([
  "bootstrap_ok",
  "bootstrap_error",
  "exploracion_manual_pendiente",
  "exploracion_terminada",
  "exploracion_error",
  "listo",
  "reporte_error",
]);

// ---------- Navegación de pestañas ----------

function mostrarVista(nombre) {
  document.querySelectorAll(".vista").forEach((v) => v.classList.add("oculto"));
  document.getElementById(`vista-${nombre}`).classList.remove("oculto");
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("activo", b.dataset.vista === nombre));
  if (nombre === "ejecutar") cargarProyectosEnSelect("ejecutar-proyecto", onCambioProyectoEjecutar);
  if (nombre === "reporte") cargarProyectosEnSelect("reporte-proyecto");
}

document.querySelectorAll(".tab-btn").forEach((b) => {
  b.addEventListener("click", () => mostrarVista(b.dataset.vista));
});

// ---------- Helpers ----------

async function apiGet(ruta) {
  const res = await fetch(ruta);
  const datos = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(datos.error || `Error ${res.status}`);
  return datos;
}

async function apiPost(ruta, body, esMultipart) {
  const opciones = esMultipart
    ? { method: "POST", body }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(ruta, opciones);
  const datos = await res.json().catch(() => ({}));
  if (!res.ok && res.status !== 202) throw new Error(datos.error || `Error ${res.status}`);
  return datos;
}

async function cargarProyectosEnSelect(idSelect, onChange) {
  const select = document.getElementById(idSelect);
  const actual = select.value;
  try {
    const { proyectos } = await apiGet("/api/proyectos");
    select.innerHTML = proyectos.map((p) => `<option value="${p}">${p}</option>`).join("");
    if (proyectos.includes(actual)) select.value = actual;
    if (onChange && select.value) onChange(select.value);
  } catch (e) {
    select.innerHTML = `<option value="">(error cargando proyectos)</option>`;
  }
  if (onChange && !select.dataset.listener) {
    select.addEventListener("change", () => onChange(select.value));
    select.dataset.listener = "1";
  }
}

// ---------- Vista: Nuevo proyecto ----------
// Carga (bootstrap) y exploracion con IA son 2 acciones SEPARADAS -
// subir documentos nunca dispara la exploracion sola, hace falta el
// boton "2. Explorar con IA" aparte, una vez que la carga termino OK.

let proyectoActual = "";

// Checkbox "Es una nueva iteracion" - SIEMPRE pregunta (nunca adivina
// por el nombre), con un desplegable manual de cual es el proyecto
// base. Al tildarlo, carga la lista de proyectos existentes recien en
// ese momento (no de entrada, para no pegarle a /api/proyectos sin
// necesidad).
const checkboxIteracion = document.getElementById("es-iteracion");
const boxProyectoBase = document.getElementById("proyecto-base-box");
const selectProyectoBase = document.getElementById("proyecto-base");
checkboxIteracion.addEventListener("change", async () => {
  if (!checkboxIteracion.checked) {
    boxProyectoBase.classList.add("oculto");
    return;
  }
  boxProyectoBase.classList.remove("oculto");
  selectProyectoBase.innerHTML = `<option value="">Cargando...</option>`;
  try {
    const { proyectos } = await apiGet("/api/proyectos");
    selectProyectoBase.innerHTML = proyectos.length
      ? proyectos.map((p) => `<option value="${p}">${p}</option>`).join("")
      : `<option value="">(no hay proyectos existentes todavía)</option>`;
  } catch (e) {
    selectProyectoBase.innerHTML = `<option value="">(error cargando proyectos: ${e.message})</option>`;
  }
});

const formAnalizar = document.getElementById("form-analizar");
formAnalizar.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const datosForm = new FormData(formAnalizar);
  const proyecto = datosForm.get("proyecto").trim();
  if (!proyecto) return;
  proyectoActual = proyecto;

  // Si la persona no tildo "Es una nueva iteracion", no mandar
  // proyecto_base aunque el <select> tenga algun valor cargado de un
  // tilde anterior (evita mandar un dato que la persona ya no quiere).
  if (!checkboxIteracion.checked) {
    datosForm.delete("proyecto_base");
  } else if (!datosForm.get("proyecto_base")) {
    alert("Tildaste 'nueva iteración' pero no elegiste un proyecto base.");
    return;
  }

  document.getElementById("analizar-estado").classList.remove("oculto");
  document.getElementById("analizar-fase").textContent = "enviando...";
  document.getElementById("analizar-mensaje").textContent = "";
  document.getElementById("analizar-log").textContent = "";
  document.getElementById("explorar-box").classList.add("oculto");

  try {
    await apiPost("/api/proyectos/analizar", datosForm, true);
    pollearEstadoCarga(proyecto);
  } catch (e) {
    document.getElementById("analizar-fase").textContent = "error";
    document.getElementById("analizar-mensaje").textContent = e.message;
  }
});

function pollearEstadoCarga(proyecto) {
  const tick = async () => {
    let datos;
    try {
      datos = await apiGet(`/api/estado/${encodeURIComponent(proyecto)}`);
    } catch (e) {
      document.getElementById("analizar-mensaje").textContent = `(no se pudo consultar el estado: ${e.message})`;
      setTimeout(tick, 12000);
      return;
    }

    document.getElementById("analizar-fase").textContent = datos.fase || "—";
    document.getElementById("analizar-mensaje").textContent = datos.mensaje || "";
    document.getElementById("analizar-log").textContent = (datos.log || []).join("\n");
    document.getElementById("analizar-log").scrollTop = 1e9;

    if (datos.fase === "bootstrap_ok") {
      document.getElementById("explorar-box").classList.remove("oculto");
      return; // carga lista - esperar al clic de "2. Explorar con IA", no seguir poleando sola
    }

    if (!FASES_TERMINALES.has(datos.fase)) {
      setTimeout(tick, 12000);
    }
  };
  tick();
}

document.getElementById("explorar-boton").addEventListener("click", async () => {
  if (!proyectoActual) return;

  document.getElementById("explorar-estado").classList.remove("oculto");
  document.getElementById("explorar-fase").textContent = "enviando...";
  document.getElementById("explorar-mensaje").textContent = "";
  document.getElementById("explorar-prompt-box").classList.add("oculto");
  document.getElementById("explorar-log").textContent = "";

  try {
    await apiPost(`/api/proyectos/${encodeURIComponent(proyectoActual)}/explorar`, {}, false);
    pollearEstadoExplorar(proyectoActual);
  } catch (e) {
    document.getElementById("explorar-fase").textContent = "error";
    document.getElementById("explorar-mensaje").textContent = e.message;
  }
});

function pollearEstadoExplorar(proyecto) {
  const tick = async () => {
    let datos;
    try {
      datos = await apiGet(`/api/estado/${encodeURIComponent(proyecto)}`);
    } catch (e) {
      document.getElementById("explorar-mensaje").textContent = `(no se pudo consultar el estado: ${e.message})`;
      setTimeout(tick, 12000);
      return;
    }

    document.getElementById("explorar-fase").textContent = datos.fase || "—";
    document.getElementById("explorar-mensaje").textContent = datos.mensaje || "";
    document.getElementById("explorar-log").textContent = (datos.log || []).join("\n");
    document.getElementById("explorar-log").scrollTop = 1e9;

    if (datos.fase === "exploracion_manual_pendiente" && datos.prompt_exploracion) {
      const box = document.getElementById("explorar-prompt-box");
      box.classList.remove("oculto");
      document.getElementById("explorar-prompt-texto").value = datos.prompt_exploracion;
    }

    if (!FASES_TERMINALES.has(datos.fase)) {
      setTimeout(tick, 12000);
    }
  };
  tick();
}

document.getElementById("explorar-copiar").addEventListener("click", () => {
  const texto = document.getElementById("explorar-prompt-texto");
  texto.select();
  navigator.clipboard?.writeText(texto.value).catch(() => document.execCommand("copy"));
});

document.getElementById("ejecutar-copiar").addEventListener("click", () => {
  const texto = document.getElementById("ejecutar-prompt-texto");
  texto.select();
  navigator.clipboard?.writeText(texto.value).catch(() => document.execCommand("copy"));
});

// ---------- Vista: Ejecutar pruebas ----------

async function onCambioProyectoEjecutar(proyecto) {
  const cont = document.getElementById("ejecutar-rf-lista");
  cont.innerHTML = "Cargando RF...";
  if (!proyecto) { cont.innerHTML = ""; return; }
  try {
    const { rf } = await apiGet(`/api/rf/${encodeURIComponent(proyecto)}`);
    cont.innerHTML = rf.map((r) => {
      const sinCasos = r.cp_generados === 0;
      return `<label class="rf-item ${sinCasos ? "sin-casos" : ""}">
        <input type="checkbox" value="${r.rf}" ${sinCasos ? "disabled" : ""}>
        ${r.rf} (${r.cp_generados}/${r.cp_total} generados)
      </label>`;
    }).join("");
  } catch (e) {
    cont.innerHTML = `(error cargando RF: ${e.message})`;
  }
}

document.getElementById("ejecutar-boton").addEventListener("click", async () => {
  const proyecto = document.getElementById("ejecutar-proyecto").value;
  if (!proyecto) return;
  const rfSeleccionados = Array.from(document.querySelectorAll("#ejecutar-rf-lista input:checked")).map((c) => c.value);
  if (rfSeleccionados.length === 0) {
    alert("Selecciona al menos un RF con casos generados.");
    return;
  }
  const video = document.getElementById("ejecutar-video").checked;

  document.getElementById("ejecutar-estado").classList.remove("oculto");
  document.getElementById("ejecutar-fase").textContent = "enviando...";
  document.getElementById("ejecutar-mensaje").textContent = "";
  document.getElementById("ejecutar-log").textContent = "";
  document.getElementById("ejecutar-progreso-box").classList.add("oculto");
  document.getElementById("ejecutar-prompt-box").classList.add("oculto");

  try {
    await apiPost(`/api/ejecutar/${encodeURIComponent(proyecto)}`, { rf: rfSeleccionados, video });
    pollearEstadoEjecutar(proyecto);
  } catch (e) {
    document.getElementById("ejecutar-fase").textContent = "error";
    document.getElementById("ejecutar-mensaje").textContent = e.message;
  }
});

function pollearEstadoEjecutar(proyecto) {
  const tick = async () => {
    let datos;
    try {
      datos = await apiGet(`/api/estado/${encodeURIComponent(proyecto)}`);
    } catch (e) {
      document.getElementById("ejecutar-mensaje").textContent = `(no se pudo consultar el estado: ${e.message})`;
      setTimeout(tick, 12000);
      return;
    }

    document.getElementById("ejecutar-fase").textContent = datos.fase || "—";
    document.getElementById("ejecutar-mensaje").textContent = datos.mensaje || "";
    document.getElementById("ejecutar-log").textContent = (datos.log || []).join("\n");
    document.getElementById("ejecutar-log").scrollTop = 1e9;

    const prog = datos.progreso;
    const progBox = document.getElementById("ejecutar-progreso-box");
    if (prog && prog.total) {
      progBox.classList.remove("oculto");
      document.getElementById("ejecutar-progreso").max = prog.total;
      document.getElementById("ejecutar-progreso").value = prog.actual;
      document.getElementById("ejecutar-progreso-texto").textContent = `${prog.actual}/${prog.total} — ${prog.cp_actual || ""}`;
    }

    if (datos.prompt_ejecucion) {
      const box = document.getElementById("ejecutar-prompt-box");
      box.classList.remove("oculto");
      document.getElementById("ejecutar-prompt-texto").value = datos.prompt_ejecucion;
    }

    if (datos.fase === "listo") {
      // Si hubo fallos (prompt_ejecucion presente), nos quedamos en esta
      // vista para que el prompt sea visible - no saltar solos al
      // reporte, que tapa el cuadro de ayuda.
      if (!datos.prompt_ejecucion) {
        mostrarVista("reporte");
        document.getElementById("reporte-proyecto").value = proyecto;
        cargarReporte(proyecto);
      }
      return;
    }
    if (!FASES_TERMINALES.has(datos.fase)) {
      setTimeout(tick, 12000);
    }
  };
  tick();
}

// ---------- Vista: Reporte ----------

document.getElementById("reporte-boton").addEventListener("click", () => {
  const proyecto = document.getElementById("reporte-proyecto").value;
  if (proyecto) cargarReporte(proyecto);
});

const CLASE_ESTADO = { "OK": "estado-OK", "FALLIDO": "estado-FALLIDO", "NO OK": "estado-NOOK", "SIN CORRER": "estado-SINCORRER" };

async function cargarReporte(proyecto) {
  const cont = document.getElementById("reporte-contenido");
  cont.innerHTML = "Cargando...";
  try {
    const datos = await apiGet(`/api/reporte/${encodeURIComponent(proyecto)}`);
    cont.innerHTML = renderizarReporte(datos);
  } catch (e) {
    cont.innerHTML = `<p>${e.message}</p>`;
  }
}

function renderizarReporte(datos) {
  const filasResumen = datos.resumen.map((r) => `
    <tr>
      <td>${r.rf}</td>
      <td class="estado-OK">${r.ok}</td>
      <td class="estado-NOOK">${r.no_ok}</td>
      <td class="estado-FALLIDO">${r.fallido}</td>
      <td class="estado-SINCORRER">${r.sin_correr}</td>
      <td>${r.total}</td>
      <td>${r.pct_ok !== null ? r.pct_ok + "%" : "-"}</td>
    </tr>`).join("");

  const t = datos.total;
  const filaTotal = `
    <tr style="font-weight:bold">
      <td>TOTAL</td>
      <td class="estado-OK">${t.ok}</td>
      <td class="estado-NOOK">${t.no_ok}</td>
      <td class="estado-FALLIDO">${t.fallido}</td>
      <td class="estado-SINCORRER">${t.sin_correr}</td>
      <td>${t.total}</td>
      <td>${t.pct_ok !== null ? t.pct_ok + "%" : "-"}</td>
    </tr>`;

  let rfActual = null;
  const filasDetalle = datos.detalle.map((d) => {
    let encabezado = "";
    if (d.rf !== rfActual) {
      rfActual = d.rf;
      encabezado = `<tr class="rf-header"><td colspan="7">${rfActual}</td></tr>`;
    }
    const clase = CLASE_ESTADO[d.resultado] || "estado-NOOK";
    return `${encabezado}<tr>
      <td>${d.cp}</td>
      <td>${d.cu}</td>
      <td>${d.nombre}</td>
      <td class="${clase}">${d.resultado}</td>
      <td>${d.ultima_corrida || ""}</td>
      <td>${d.detalle || ""}</td>
      <td>${d.motivo_confirmado || ""}</td>
    </tr>`;
  }).join("");

  return `
    <p><em>Generado: ${new Date(datos.generado).toLocaleString()}</em></p>
    <h3>Resumen por RF</h3>
    <table class="reporte">
      <thead><tr><th>RF</th><th>OK</th><th>NO OK</th><th>Fallido</th><th>Sin correr</th><th>Total</th><th>% OK</th></tr></thead>
      <tbody>${filasResumen}${filaTotal}</tbody>
    </table>
    <h3>Detalle por caso</h3>
    <table class="reporte">
      <thead><tr><th>CP</th><th>CU</th><th>Nombre</th><th>Resultado</th><th>Última corrida</th><th>Detalle</th><th>Motivo confirmado</th></tr></thead>
      <tbody>${filasDetalle}</tbody>
    </table>
  `;
}

// ---------- Arranque ----------

mostrarVista("nuevo");
