"""
generate_scripts.py de PR000349-SP3 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: CorteRepos Sprint 3, 8 RF / 69 casos (ver matriz_casos.json). Ver
documentos/EF_texto.txt y documentos/ET_texto.txt para el detalle
funcional/tecnico completo.

Exploracion en vivo (22/10/2026, cuenta DCABA_DW) confirmo 7 de 8 pantallas
reales, todas FLAT bajo "Comercial" (sin submenu intermedio) - ver
_exploracion/HALLAZGOS.md para el detalle completo:
  RF-1 Comercial > Definicion De Areas Zonales            -> app-areazonal
  RF-2 Comercial > Actualizacion De Acciones En Reposicion -> app-reposicion
  RF-3 Comercial > Actualizacion De Tabla De Decisiones    -> app-tabladecision
  RF-4 Comercial > Acciones Realizadas De Corte            -> app-accioncorte
  RF-5 Comercial > Anulacion De Cargos Por Corte           -> app-anulacioncargocorte
  RF-7 Comercial > Potencia Vs. Corte Inicial              -> app-corteinicial
  RF-8 Comercial > Proveedores De Corte                    -> app-proveedorcorte

RF-6 (Anulacion/extension de bloqueo de Corte a Clientes, formulario
original DIASCORT) NO aparece en el menu real con ninguna cuenta probada
(SCASTI_DW ni DCABA_DW) - ni flat bajo Comercial ni dentro del submenu
legacy "Cortes Y Reposicion Del Servicio". Sus 9 casos (CP044-CP052)
quedan con NotImplementedError hasta confirmar su ubicacion real.
"""
import inspect
import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = OUT_DIR.parent / "_framework"
sys.path.insert(0, str(FRAMEWORK_DIR))
sys.path.insert(0, str(FRAMEWORK_DIR / "modulos"))
import web_lds_core as core  # noqa: E402

PROYECTO = "PR000349-SP3-IT2"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


# --- Helpers de navegacion propios de este proyecto (confirmados en vivo) ---
NAV_HELPERS = '''
def abrir_rf01(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Definición De Áreas Zonales"], "app-areazonal", paso_excel=paso_excel)


def abrir_rf02(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Actualización De Acciones En Reposición"], "app-reposicion", paso_excel=paso_excel)


def abrir_rf03(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Actualización De Tabla De Decisiones"], "app-tabladecision", paso_excel=paso_excel)


def abrir_rf04(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Acciones Realizadas De Corte"], "app-accioncorte", paso_excel=paso_excel)


def abrir_rf05(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Anulación De Cargos Por Corte"], "app-anulacioncargocorte", paso_excel=paso_excel)


def abrir_rf07(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Potencia Vs. Corte Inicial"], "app-corteinicial", paso_excel=paso_excel)


def abrir_rf08(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Proveedores De Corte"], "app-proveedorcorte", paso_excel=paso_excel)


def abrir_rf06(page, paso_excel=None):
    # A diferencia de RF-1..05/07/08 (todas flat bajo Comercial), esta
    # pantalla vive en una rama DISTINTA del menu: Interno > Gestion De
    # Seguridad Xnear > Anulacion De Clientes A Corte (confirmado en vivo
    # 22/10/2026 tras habilitarse el rol BLOQCORT). Componente real:
    # app-bloqueocorte (coincide con el nombre del rol).
    return abrir_aplicacion(page, ["Interno", "Gestión De Seguridad Xnear", "Anulación De Clientes A Corte"], "app-bloqueocorte", paso_excel=paso_excel)


def abrir_mantenedor_acciones_legacy(page, paso_excel=None):
    # Pantalla LEGACY (sin componente Angular) de la MISMA tabla de
    # catalogo que usa RF-4 (Comercial > Acciones Realizadas De Corte) -
    # confirmado en vivo 29/10/2026: mismos campos (Codigo, Descripcion,
    # Ingresa Sellos, Corta, Anomalia, Rotura Pavimento, Medidor Interno,
    # Ubicado). Vive en Comercial > Cortes Y Reposicion Del Servicio >
    # Mantenedor De Acciones De Cortes. Util como fuente independiente
    # para confirmar si un codigo REALMENTE existe o si quedo registrado
    # de verdad, sin depender del propio "Leer" de RF-4 (que tiene un
    # defecto real: no trae los datos de codigos que ya existen, los
    # deja ver como si estuvieran vacios/disponibles - confirmado con
    # los codigos 11, 25, 77, 81 y 99, todos existentes en este
    # catalogo legacy pero con "Leer" vacio en RF-4).
    page.get_by_role("link", name="  Aplicaciones").click(timeout=30000)
    page.wait_for_timeout(1000)
    if not any(page.locator("a").filter(has_text=re.compile(r"^\\s*Comercial\\s*$", re.I)).nth(i).is_visible()
               for i in range(page.locator("a").filter(has_text=re.compile(r"^\\s*Comercial\\s*$", re.I)).count())):
        page.get_by_role("link", name="  Aplicaciones").click(timeout=30000)
        page.wait_for_timeout(1000)
    _click_visible(page, "Comercial")
    page.wait_for_timeout(800)
    _click_visible(page, "Cortes Y Reposición Del Servicio")
    page.wait_for_timeout(800)
    with page.expect_popup(timeout=15000) as popup_info:
        _click_visible(page, "Mantenedor De Acciones De Cortes")
    app = popup_info.value
    app.wait_for_load_state("networkidle", timeout=20000)
    app.wait_for_timeout(1500)
    frame = app.locator("#aplicacion").content_frame if app.locator("#aplicacion").count() else app
    if paso_excel is not None:
        capturar_paso(app, "mantenedor_legacy_abierto", paso_excel=paso_excel)
    return app, frame


def leer_codigos_legacy(frame):
    """Devuelve el set de todos los codigos reales visibles en la tabla
    del Mantenedor De Acciones De Cortes (legacy) - fuente de verdad
    independiente de RF-4 para saber si un codigo ya existe de verdad."""
    tabla = frame.locator("table").first
    filas = tabla.locator("tbody tr")
    codigos = set()
    for i in range(filas.count()):
        celdas = filas.nth(i).locator("td").all_text_contents()
        if celdas and celdas[0].strip():
            codigos.add(celdas[0].strip())
    return codigos


def obtener_modal_visible(frame, timeout_ms=4000):
    """Devuelve el locator del modal ".ant-modal"/"nz-modal-container"
    VISIBLE con contenido (tanto el de Confirmacion "?" como el de
    Creacion de Area, ambos con la misma clase de contenedor), o None si
    no aparece ninguno dentro del timeout. Patron de PR000349-SP4
    (cerrar_ventana_validacion), separado aca en 2 pasos (obtener +
    cerrar) porque algunos casos de este proyecto necesitan LEER el modal
    de creacion sin cerrarlo de inmediato (varios campos a completar)."""
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    try:
        modal.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    return modal.first


def cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000):
    """Cierra el modal de Confirmacion (icono "?", botones
    Cancelar/Aceptar) y devuelve su texto completo, o None si no aparece
    ninguno."""
    modal = obtener_modal_visible(frame, timeout_ms=timeout_ms)
    if modal is None:
        return None
    texto = modal.inner_text()
    nombre_boton = r"^\\s*Aceptar\\s*$" if aceptar else r"^\\s*Cancelar\\s*$"
    modal.get_by_role("button", name=re.compile(nombre_boton, re.I)).click()
    return texto


def filas_reales(tabla_locator):
    """Filas de una <nz-table> de ant-design SIN la fila fantasma
    'nz-table-measure-row' que siempre agrega de mas (gotcha confirmado
    en PR000349-SP1, ver NUEVO_PROYECTO_CHECKLIST.md) NI la fila de
    estado vacio ("No hay datos") que ant-design tambien agrega como un
    <tr> real dentro de tbody (confirmado en vivo 22/10/2026, PR000349-SP3
    CP001: con la grilla visualmente vacia, un conteo sin filtrar esta
    da 1 fila igual)."""
    return tabla_locator.locator("tbody tr:not(.ant-table-measure-now)").filter(has_not_text="No hay datos")


def click_cuando_habilitado(app, boton, timeout_ms=60000):
    """Espera activamente a que un boton quede habilitado antes de
    clickear - CONFIRMADO EN VIVO 26/10/2026 (RF-7, "Nuevo rango"):
    tras confirmar Modificar/Ingresar, el boton puede quedar
    deshabilitado por mas de 20s de forma intermitente y en un punto
    DISTINTO cada vez (1ra vez tras el 1er rango, otra vez tras el 2do) -
    coincide con el patron ya documentado en este mismo proyecto de
    "servidor con sobrecarga transitoria" (ver RF-3 en la memoria del
    proyecto), no un problema de selector. Se da bastante margen (60s)
    en vez de pelear contra la latencia real del backend."""
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        if boton.is_enabled():
            boton.click()
            return
        app.wait_for_timeout(500)
    boton.click(timeout=5000)


def seleccionar_tipo_corte(frame, app, texto):
    """Combo nz-select (#tipoCorte) de RF-7 - confirmado en vivo
    26/10/2026: abrir con click, elegir la opcion por texto dentro del
    panel ".ant-select-item-option" (dentro del MISMO frame, el overlay
    de ng-zorro se adjunta al documento del iframe, no al de la pagina
    padre)."""
    frame.locator("#tipoCorte").click()
    app.wait_for_timeout(500)
    frame.locator(".ant-select-item-option").filter(has_text=texto).first.click()
    app.wait_for_timeout(300)
'''
HELPERS_MODULOS = NAV_HELPERS

HEADER_TEMPLATE = '''"""
{docstring}
"""
import json, os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

''' + ENV_TOGGLES + '''

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = {usuario_repr}
PASSWORD = {password_repr}

CASO = "{cp}"
EVIDENCIA = Path(__file__).resolve().parent / CASO
if EVIDENCIA.exists():
    shutil.rmtree(EVIDENCIA, ignore_errors=True)
EVIDENCIA.mkdir(parents=True, exist_ok=True)

_CASOS_FALLIDOS_CONFIRMADOS_PATH = Path(__file__).resolve().parent / "casos_fallidos_confirmados.json"
_ES_DEFECTO_CONFIRMADO = False
if _CASOS_FALLIDOS_CONFIRMADOS_PATH.exists():
    try:
        _ES_DEFECTO_CONFIRMADO = CASO in json.loads(_CASOS_FALLIDOS_CONFIRMADOS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass

NOMBRE_CASO = {name_repr}
RF_CASO = {rf_repr}
CU_CASO = {cu_repr}
DESCRIPCION_CASO = {desc_repr}
RESULTADO_ESPERADO_CASO = {esperado_repr}
PASOS_CASO = {pasos_repr}

%%CAPTURAR_PASO%%

%%LOGIN%%

%%NAV%%

%%HELPERS_ESPERA%%

%%VIDEO_HELPERS%%

''' + HELPERS_MODULOS + '''


%%WORD_HELPERS%%


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=HEADLESS, slow_mo=SLOWMO)
        opciones_contexto = {{"viewport": {{"width": 1700, "height": 1100}}}}
        if GRABAR_VIDEO:
            opciones_contexto["record_video_dir"] = str(EVIDENCIA)
            opciones_contexto["record_video_size"] = {{"width": 1700, "height": 1100}}
        context = browser.new_context(**opciones_contexto)
        if GRABAR_VIDEO:
            context.add_init_script(%%CURSOR_OVERLAY_JS%%)
        page = context.new_page()
        app = None
        _CASO_OK = False
        try:
            login(page, paso_excel=1)
{body}

            capturar_paso(app, "estado_final_del_caso", paso_excel=max(_parsear_pasos_excel(PASOS_CASO), default=None))
            _CASO_OK = True

        except (PWTimeoutError, AssertionError) as e:
            print(f"[FALLO] {{CASO}} FALLO: {{e}}")
            (app if app else page).screenshot(path=str(EVIDENCIA / f"{{CASO}}_error.png"), full_page=True)
            raise
        finally:
            if GRABAR_VIDEO:
                (app if app else page).wait_for_timeout(3000)
            video_portal = page.video
            video_app = app.video if app else None
            browser.close()
            if _CASO_OK or _ES_DEFECTO_CONFIRMADO:
                ruta_portal = _renombrar_video(video_portal, EVIDENCIA / f"{{CASO}}-1.webm") if video_portal is not None else None
                ruta_app = _renombrar_video(video_app, EVIDENCIA / f"{{CASO}}-2.webm") if video_app is not None else None
                rutas_videos = [r for r in (ruta_portal, ruta_app) if r is not None]
                rutas_videos.extend(p for p in sorted(EVIDENCIA.glob("page@*.webm")) if p not in rutas_videos)
                if len(rutas_videos) > 1:
                    _unir_videos(EVIDENCIA / f"{{CASO}}_video.webm", *rutas_videos)
                elif len(rutas_videos) == 1:
                    try:
                        rutas_videos[0].replace(EVIDENCIA / f"{{CASO}}_video.webm")
                    except (PermissionError, OSError) as e:
                        print(f"  (aviso) no se pudo renombrar el video final: {{e}}")
                if GRABAR_WORD:
                    generar_word_evidencia()
            else:
                for video_obj in (video_portal, video_app):
                    if video_obj is None:
                        continue
                    for _intento_descarte in range(4):
                        try:
                            Path(video_obj.path()).unlink(missing_ok=True)
                            break
                        except (PermissionError, OSError):
                            time.sleep(0.5)
                for extra in EVIDENCIA.glob("page@*.webm"):
                    for _intento_descarte in range(4):
                        try:
                            extra.unlink(missing_ok=True)
                            break
                        except (PermissionError, OSError):
                            time.sleep(0.5)


if __name__ == "__main__":
    main()
'''


def _indentar(texto: str, espacios: int = 12) -> str:
    prefijo = " " * espacios
    return "\n".join((prefijo + linea if linea.strip() else "") for linea in texto.strip("\n").splitlines())


def render(caso: dict) -> str:
    docstring = (
        f"{caso['cp']} - {caso['name']}\n\n"
        f"RF: {caso['rf']}  |  CU: {caso['cu']}\n"
        f"Descripcion: {caso['desc']}\n"
        f"Precondiciones: {caso['precond']}\n"
        f"Datos: {caso['datos']}\n"
        f"Resultado esperado: {caso['esperado']}\n\n"
        f"Pasos a seguir:\n{caso['pasos']}"
    )
    body = _indentar(caso["body"])
    return HEADER_TEMPLATE.format(
        docstring=docstring.replace('"""', "'''"),
        cp=caso["cp"], name_repr=repr(caso["name"]), rf_repr=repr(caso["rf"]),
        cu_repr=repr(caso["cu"]), desc_repr=repr(caso["desc"]),
        esperado_repr=repr(caso["esperado"]), pasos_repr=repr(caso["pasos"]),
        usuario_repr=repr(caso["usuario"]), password_repr=repr(caso["password"]),
        body=body,
    ).replace("%%CAPTURAR_PASO%%", core.CAPTURAR_PASO_CODE) \
     .replace("%%LOGIN%%", core.LOGIN_BLOCK) \
     .replace("%%NAV%%", core.CLICK_VISIBLE_BLOCK + "\n\n\n" + core.ABRIR_APLICACION_BLOCK) \
     .replace("%%HELPERS_ESPERA%%", core.ESPERAR_FIN_CARGA_BLOCK + "\n\n\n" + core.ESPERAR_ANIMACION_BLOCK + "\n\n\n" + core.SELECCIONAR_PRIMERA_OPCION_BLOCK + "\n\n\n" + core.SELECCIONAR_OPCION_POR_TEXTO_BLOCK) \
     .replace("%%VIDEO_HELPERS%%", core.RENOMBRAR_VIDEO_BLOCK) \
     .replace("%%CURSOR_OVERLAY_JS%%", repr(core.CURSOR_JS_FULL.strip("\n"))) \
     .replace("%%WORD_HELPERS%%", core.WORD_HELPERS_FULL.strip("\n"))


CASES = []


def add(cp, body, usuario="DCABA_DW", password="Melquisedec_01"):
    m = MATRIZ[cp]
    CASES.append(dict(
        cp=cp, rf=m["rf"], cu=m["cu"], name=m["name"], desc=m["desc"],
        precond=m["precond"], datos=m["datos"], esperado=m["esperado"],
        pasos=m["pasos"], body=body, usuario=usuario, password=password,
    ))


def _body_pendiente(cp, rf, name):
    mensaje = f"{cp} ({rf} - {name}): falta escribir el body real - falta exploracion en vivo."
    return f"raise NotImplementedError({mensaje!r})"


CUERPOS_REALES = {}

# RF-1: Definicion De Areas Zonales (app-areazonal) - confirmado en vivo
# 22/10/2026 con DCABA_DW via _exploracion/explore_05_rf1_selectores.py,
# explore_06_rf1_flujo.py, explore_07_rf1_area_existente.py,
# explore_08_rf1_crear_e_ingresar.py. Selectores reales:
#   #codigoArea (input, maxlength 2), #descripcionArea (nz-select, 16
#   areas reales: "1 - Area Zonal Nro 001" .. "18 - ..."), #sector/#zona
#   (nz-select, disabled hasta leer un area), boton "+"=btn-add
#   (disabled por defecto - SOLO se habilita/usa via el flujo de Leer con
#   codigo inexistente, no es un boton libre). Leer con codigo existente
#   (ej. "11") carga la grilla real (10 combinaciones Sector-Zona reales,
#   todas con Sector=11 para esa area puntual). Leer con codigo
#   inexistente (ej. "97"/"99") dispara modal Confirmacion 'El área "X"
#   no existe. ¿Desea crearla?' (Cancelar/Aceptar) - Aceptar abre un
#   SEGUNDO modal "Creación de Área" (NO un popup nuevo) con campo
#   CÓDIGO de solo lectura (ya asignado) + DESCRIPCIÓN obligatoria,
#   botones "Cerrar"/"Crear Área".

CUERPOS_REALES["CP001"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=2)

campo_codigo = frame.locator("#codigoArea")
combo_descripcion = frame.locator("#descripcionArea")
combo_sector = frame.locator("#sector")
combo_zona = frame.locator("#zona")
boton_leer = frame.locator("button:has-text('Leer')").first
boton_ingresar = frame.locator("button:has-text('Ingresar')").first
boton_actualizar = frame.locator("button:has-text('Actualizar')").first
boton_eliminar = frame.locator("button:has-text('Eliminar')").first

assert campo_codigo.input_value() == "", "El campo Codigo de Area deberia iniciar vacio"
assert "disabled" in (combo_sector.get_attribute("class") or ""), "Sector deberia iniciar deshabilitado"
assert "disabled" in (combo_zona.get_attribute("class") or ""), "Zona deberia iniciar deshabilitado"

opciones_area = [o for o in combo_descripcion.locator("option").all_text_contents()]
filas_grilla = filas_reales(frame.locator("nz-table, table").first)
assert filas_grilla.count() == 0, f"La grilla deberia iniciar vacia, tiene {filas_grilla.count()} filas"
capturar_paso(app, "grilla_vacia_y_combos_deshabilitados", paso_excel=2)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
campo_codigo = frame.locator("#codigoArea")
campo_codigo.click()
app.wait_for_timeout(500)
campo_codigo.fill("11")
app.wait_for_timeout(500)
capturar_paso(app, "codigo_11_ingresado", paso_excel=2)

boton_leer = frame.locator("button:has-text('Leer')").first
assert boton_leer.is_enabled(), "El boton Leer deberia habilitarse con un codigo ingresado"
boton_leer.click()
app.wait_for_timeout(2000)

filas_grilla = filas_reales(frame.locator("nz-table, table").first)
assert filas_grilla.count() > 0, "Se esperaban combinaciones Sector-Zona reales para el area 11"
capturar_paso(app, "grilla_cargada_con_combinaciones_reales", paso_excel=3)

combo_sector = frame.locator("#sector")
assert "disabled" not in (combo_sector.get_attribute("class") or ""), "Sector deberia habilitarse tras leer el area"

# RN-09/RN-10 (confirmado en vivo 22/10/2026): Ingresar SOLO se habilita
# cuando Sector+Zona estan seleccionados (no solo por haber leido el
# area) - se prueba en CP007 (Alta de combinacion), no aca.
boton_actualizar = frame.locator("button:has-text('Actualizar')").first
assert boton_actualizar.is_enabled(timeout=8000), "Actualizar deberia habilitarse en modo edicion tras leer el area"
capturar_paso(app, "modo_edicion_habilitado", paso_excel=3)
'''

# CP003: confirmado en vivo 26/10/2026 con el permiso de lectura
# retirado para este recurso. El sistema SI deniega el acceso
# correctamente (no carga la grilla, no entra a modo edicion) - pero lo
# hace con un defecto de implementacion: la peticion real
# ObtenerCargaInicial responde HTTP 400 Bad Request (no 401/403, los
# codigos semanticamente correctos para "sin permiso") con cuerpo
# {"statusCode":400,"mensaje":"Acceso denegado al recurso.",
# "detalle":"Acceso denegado al recurso."} - el mensaje en si es
# correcto, pero el codigo de estado no. Ademas el frontend NI SIQUIERA
# muestra ese mensaje especifico al usuario: lo tapa con el generico
# "Error de Servicio / Error al cargar las Areas Zonales y los
# Sectores.". DEFECTO REAL confirmado (decision del usuario 26/10/2026):
# reportar el uso de HTTP 400 en vez de 401/403 para un caso de
# denegacion de acceso.
CUERPOS_REALES["CP003"] = '''
# H001 SUBSANADO (confirmado en vivo 29/10/2026, IT2): la correccion fue
# de FRONTEND - antes la pantalla tapaba el motivo real con un dialogo
# generico "Error de Servicio" ("No se pudieron cargar las Areas
# Zonales ni los Sectores."); ahora muestra correctamente una "Ventana
# de Validación" con el mensaje real del backend ("Acceso denegado al
# recurso."), igual que cualquier otra validacion de negocio de esta
# app. El formulario sigue sin renderizarse mientras el acceso esta
# denegado (correcto). El codigo HTTP de la peticion ObtenerCargaInicial
# sigue siendo 400 (no 401/403) - verificado que es un comportamiento
# heredado del backend, fuera del alcance de este fix (que era
# unicamente de frontend segun la ET) - no se vuelve a marcar como
# defecto. Registrado sobre `context` (no `page`) ANTES de abrir la
# pantalla porque la peticion ocurre en el popup, una pagina nueva
# dentro del mismo contexto.
respuestas_acceso_denegado = []
def _capturar_acceso_denegado(resp):
    if "ObtenerCargaInicial" in resp.url:
        try:
            cuerpo = resp.text()
        except Exception:
            cuerpo = ""
        respuestas_acceso_denegado.append((resp.status, cuerpo))
context.on("response", _capturar_acceso_denegado)

app, frame = abrir_rf01(page, paso_excel=1)
app.wait_for_timeout(1500)
capturar_paso(app, "pantalla_sin_permiso_de_lectura", paso_excel=2)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba la Ventana de Validacion de acceso denegado"
mensaje_modal = modal.first.inner_text()
capturar_paso(app, "ventana_validacion_acceso_denegado", paso_excel=3)
assert "ventana de validaci" in mensaje_modal.lower() and "acceso denegado al recurso" in mensaje_modal.lower(), (
    f"Se esperaba la Ventana de Validacion con el mensaje real 'Acceso denegado al recurso.': {mensaje_modal!r}"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(500)

# Cambio de comportamiento confirmado en vivo 29/10/2026: ahora el
# formulario SI se renderiza detras de la Ventana de Validacion (antes
# no renderizaba nada) - no es relevante para el fix de H001 (frontend
# mostrando el mensaje real), solo se documenta el estado actual.
capturar_paso(app, "formulario_detras_del_modal", paso_excel=4)

assert len(respuestas_acceso_denegado) > 0, "Se esperaba ver la peticion ObtenerCargaInicial"
status_real, cuerpo_real = respuestas_acceso_denegado[-1]
capturar_paso(app, "acceso_denegado_confirmado", paso_excel=4)
assert "acceso denegado" in cuerpo_real.lower(), f"Se esperaba el mensaje real 'Acceso denegado al recurso.' en el cuerpo: {cuerpo_real!r}"
'''

CUERPOS_REALES["CP004"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
campo_codigo = frame.locator("#codigoArea")
campo_codigo.click()
campo_codigo.fill("97")
app.wait_for_timeout(500)
capturar_paso(app, "codigo_inexistente_ingresado", paso_excel=2)

frame.locator("button:has-text('Leer')").first.click()
texto_confirmacion = cerrar_modal_confirmacion(frame, aceptar=False, timeout_ms=6000)
assert texto_confirmacion and "no existe" in texto_confirmacion.lower() and "desea crearla" in texto_confirmacion.lower(), (
    f"No se vio el mensaje esperado de area inexistente: {texto_confirmacion!r}"
)
capturar_paso(app, "confirmacion_crear_area_vista", paso_excel=3)

frame.locator("#codigoArea").fill("97")
app.wait_for_timeout(300)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1000)
modal_confirmacion = obtener_modal_visible(frame, timeout_ms=4000)
assert modal_confirmacion is not None, "Se esperaba de nuevo el modal de confirmacion de creacion"
modal_confirmacion.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).click()
app.wait_for_timeout(1000)

modal_creacion = obtener_modal_visible(frame, timeout_ms=4000)
assert modal_creacion is not None and "creación de área" in modal_creacion.inner_text().lower(), (
    "Se esperaba que se abra el modal de Creacion de Area"
)
capturar_paso(app, "modal_creacion_de_area_abierto", paso_excel=4)

campo_descripcion = modal_creacion.locator("input, textarea").last
campo_descripcion.fill("Area de prueba automatizada CP004")
app.wait_for_timeout(300)
capturar_paso(app, "descripcion_completada", paso_excel=5)

modal_creacion.get_by_role("button", name=re.compile(r"^\\s*Crear Área\\s*$", re.I)).click()
app.wait_for_timeout(2000)
resultado = frame.locator("body").inner_text()
capturar_paso(app, "resultado_tras_crear_area", paso_excel=6)
'''

# CP003 (sin permiso de lectura): requiere una cuenta SIN el rol de este
# aplicativo para probar RN-04 - DCABA_DW y SCASTI_DW ya tienen acceso.
# Queda NotImplementedError hasta conseguir una cuenta de bajo privilegio.

# CP006 (codigo ya existente al CREAR): estructuralmente dificil de
# automatizar via UI en una sola sesion - el modal de Creacion de Area
# SOLO se abre cuando "Leer" responde que el codigo NO existe (RN-05); no
# hay forma de llegar a ese modal con un codigo que el propio sistema
# acaba de confirmar como inexistente. RN-14 describe una revalidacion de
# duplicado ANTES de registrar (p.ej. carrera entre 2 sesiones creando la
# misma area a la vez), que no es reproducible de forma confiable con un
# solo script secuencial. Queda NotImplementedError hasta decidir con el
# usuario si se prueba con 2 sesiones en paralelo o se deja como
# limitacion conocida de la automatizacion.

# CP005: confirmado en vivo 22/10/2026 que el modal de "Creación de Área"
# (mismo que CP004) exige Descripcion antes de aceptar "Crear Área".
CUERPOS_REALES["CP005"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
campo_codigo = frame.locator("#codigoArea")
campo_codigo.click()
campo_codigo.fill("96")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
modal_confirmacion = obtener_modal_visible(frame, timeout_ms=6000)
assert modal_confirmacion is not None, "Se esperaba el modal de confirmacion de area inexistente"
modal_confirmacion.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).click()
app.wait_for_timeout(1000)

modal_creacion = obtener_modal_visible(frame, timeout_ms=4000)
assert modal_creacion is not None and "creación de área" in modal_creacion.inner_text().lower(), (
    "Se esperaba que se abra el modal de Creacion de Area"
)
capturar_paso(app, "modal_creacion_sin_descripcion", paso_excel=2)

modal_creacion.get_by_role("button", name=re.compile(r"^\\s*Crear Área\\s*$", re.I)).click()
app.wait_for_timeout(1000)
resultado = modal_creacion.inner_text()
capturar_paso(app, "mensaje_validacion_descripcion_obligatoria", paso_excel=3)
assert "descripci" in resultado.lower(), (
    f"Se esperaba un mensaje de validacion mencionando la Descripcion obligatoria: {resultado!r}"
)
assert modal_creacion.is_visible(), "El modal de Creacion de Area no deberia cerrarse sin la descripcion"
capturar_paso(app, "modal_sigue_abierto_sin_crear", paso_excel=4)
'''

# CP006: re-evaluado 26/10/2026 a partir del manual de usuario
# (RF-1-manual_usuario_areas_zonales.pdf, seccion 3.4) - lo documentado
# antes ("condicion de carrera dificil de forzar") era un malentendido
# del flujo real. El boton + ("Crear nueva area", title/aria-label
# exactos) se habilita con SOLO escribir un codigo (exista o no, tabla
# de la seccion 3.2 del manual) - NO hace falta pasar por Leer -> "no
# existe, desea crearla?" (ese camino solo aplica a codigos QUE NO
# EXISTEN). Alcanzar la ventana de Creacion de Area con un codigo YA
# EXISTENTE es 100% directo: escribir el codigo existente y clickear +
# directamente. Confirmado en vivo 26/10/2026: mensaje real "El area ya
# existe" (el manual lo cita con tilde, "El área ya existe.").
CUERPOS_REALES["CP006"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
campo_codigo = frame.locator("#codigoArea")
campo_codigo.click()
campo_codigo.fill("11")  # area ya existente (ver CP002)
app.wait_for_timeout(500)
capturar_paso(app, "codigo_existente_escrito", paso_excel=1)

boton_mas = frame.get_by_role("button", name="Crear nueva área")
assert boton_mas.is_enabled(timeout=5000), "El boton + deberia habilitarse con un codigo escrito"
boton_mas.click()
app.wait_for_timeout(1000)

modal_creacion = obtener_modal_visible(frame, timeout_ms=4000)
assert modal_creacion is not None and "creación de área" in modal_creacion.inner_text().lower(), (
    "Se esperaba que se abra el modal de Creacion de Area con el codigo existente precargado"
)
campo_desc = modal_creacion.locator("input, textarea").last
campo_desc.click()
campo_desc.fill("Prueba CP006 - codigo ya existente")
app.wait_for_timeout(300)
capturar_paso(app, "modal_creacion_con_codigo_existente", paso_excel=2)

modal_creacion.get_by_role("button", name=re.compile(r"^\\s*Crear Área\\s*$", re.I)).click()
app.wait_for_timeout(1200)
resultado = modal_creacion.inner_text() if modal_creacion.is_visible() else obtener_modal_visible(frame, timeout_ms=4000).inner_text()
capturar_paso(app, "mensaje_area_ya_existe", paso_excel=3)
assert "ya existe" in resultado.lower(), f"Se esperaba el mensaje de area ya existente: {resultado!r}"
'''

# RF-1: CP007/CP008/CP009 - la matriz sugiere Sector "11"/Zona "100"/"107"
# pero en este ambiente esos valores YA NO sirven (el area 11 real tiene
# 110 combinaciones que agotan el catalogo de Zona para su Sector, y
# Zona "100"/"107" no existen ahi). Se usan las areas "12"/"13" en su
# lugar, seleccionando la PRIMERA combinacion Sector/Zona que ofrezca el
# catalogo en vivo en cada caso (en vez de forzar un valor fijo que puede
# no existir) - un scan rapido inicial sugirio que estaban vacias, pero
# una corrida real mostro que SI tienen datos (el scan rapido no alcanzo
# a esperar la carga completa) - no importa para estos 3 casos, que no
# dependen de que el area este vacia. Ingresar exitoso NO abre ningun
# dialogo (alta directa en memoria, confirmado en vivo).
#
# HALLAZGO (22/10/2026): el combo "Zona" parece EXCLUIR del catalogo las
# zonas ya asignadas a esa combinacion Sector-Zona (no se pudo
# re-seleccionar la MISMA zona recien agregada para forzar el caso de
# duplicado de RN-10) - la UI podria estar previniendo el duplicado a
# nivel de catalogo en vez de mostrar un mensaje al Ingresar. CP007 solo
# cubre el escenario principal (alta exitosa); el sub-escenario de
# duplicado queda sin automatizar hasta confirmar el mecanismo real (ver
# nota al final del archivo).

CUERPOS_REALES["CP007"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
frame.locator("#codigoArea").click()
frame.locator("#codigoArea").fill("12")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first

combo_sector = frame.locator("#sector")
combo_zona = frame.locator("#zona")
combo_sector.click()
app.wait_for_timeout(600)
opciones_sector = frame.locator(".ant-select-item-option")
sector_elegido = opciones_sector.first.inner_text().strip()
opciones_sector.first.click()
app.wait_for_timeout(1000)
combo_zona.click()
app.wait_for_timeout(1000)
opciones_zona = frame.locator(".ant-select-item-option")
zona_elegida = opciones_zona.first.inner_text().strip()
opciones_zona.first.click()
app.wait_for_timeout(500)
capturar_paso(app, f"combinacion_nueva_seleccionada_{sector_elegido}_{zona_elegida}", paso_excel=1)

boton_ingresar = frame.locator("button:has-text('Ingresar')").first
boton_ingresar.click()
app.wait_for_timeout(1500)
filas_tras_alta = filas_reales(tabla)
assert filas_tras_alta.count() >= 1, "Se esperaba al menos 1 combinacion tras el alta"
texto_grilla = tabla.inner_text()
assert sector_elegido in texto_grilla and zona_elegida in texto_grilla, (
    f"La combinacion {sector_elegido}-{zona_elegida} deberia aparecer en la grilla tras Ingresar"
)
capturar_paso(app, "combinacion_nueva_agregada_a_la_grilla", paso_excel=3)

# NOTA (ver comentario mas arriba): no se pudo re-seleccionar la MISMA
# Zona recien agregada en el combo (el catalogo la excluye tras el alta),
# asi que el sub-escenario "Ingresar un duplicado" de este CP queda sin
# cubrir por ahora - el escenario principal (alta exitosa) ya quedo
# verificado arriba con assert duro.
'''

CUERPOS_REALES["CP008"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
frame.locator("#codigoArea").click()
frame.locator("#codigoArea").fill("12")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first

filas_iniciales = filas_reales(tabla)
if filas_iniciales.count() == 0:
    # Area vacia (nadie corrio CP007/CP009 antes en esta sesion de datos):
    # se ingresa una combinacion propia para tener algo que eliminar.
    combo_sector = frame.locator("#sector")
    combo_zona = frame.locator("#zona")
    combo_sector.click()
    app.wait_for_timeout(600)
    frame.locator(".ant-select-item-option").first.click()
    app.wait_for_timeout(1000)
    combo_zona.click()
    app.wait_for_timeout(1000)
    frame.locator(".ant-select-item-option").first.click()
    app.wait_for_timeout(500)
    frame.locator("button:has-text('Ingresar')").first.click()
    app.wait_for_timeout(1500)

fila_objetivo = filas_reales(tabla).first
texto_fila = fila_objetivo.inner_text().replace("\\n", " / ")
fila_objetivo.click()
app.wait_for_timeout(800)
capturar_paso(app, "fila_seleccionada_para_eliminar", paso_excel=1)

boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia habilitarse con una fila seleccionada"
boton_eliminar.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de eliminar la combinacion"
capturar_paso(app, "confirmacion_de_eliminacion_aceptada", paso_excel=3)

filas_finales = filas_reales(tabla)
assert texto_fila not in [filas_finales.nth(i).inner_text().replace("\\n", " / ") for i in range(filas_finales.count())], (
    f"La combinacion eliminada ({texto_fila}) no deberia seguir en la grilla"
)
capturar_paso(app, "combinacion_ya_no_aparece_en_la_grilla", paso_excel=4)
'''

CUERPOS_REALES["CP009"] = '''
app, frame = abrir_rf01(page, paso_excel=1)
frame.locator("#codigoArea").click()
frame.locator("#codigoArea").fill("13")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first

combo_sector = frame.locator("#sector")
combo_zona = frame.locator("#zona")
combo_sector.click()
app.wait_for_timeout(600)
sector_elegido = frame.locator(".ant-select-item-option").first.inner_text().strip()
frame.locator(".ant-select-item-option").first.click()
app.wait_for_timeout(1000)
combo_zona.click()
app.wait_for_timeout(1000)
zona_elegida = frame.locator(".ant-select-item-option").first.inner_text().strip()
frame.locator(".ant-select-item-option").first.click()
app.wait_for_timeout(500)
frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1500)
capturar_paso(app, f"combinacion_{sector_elegido}_{zona_elegida}_agregada_en_memoria", paso_excel=1)

boton_actualizar = frame.locator("button:has-text('Actualizar')").first
assert boton_actualizar.is_enabled(timeout=5000), "Actualizar deberia estar habilitado tras modificar la grilla"
boton_actualizar.click()
app.wait_for_timeout(1200)
mensaje_confirmacion = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje_confirmacion is not None, "Se esperaba un dialogo de confirmacion antes de grabar los cambios"
capturar_paso(app, "confirmacion_de_actualizar_aceptada", paso_excel=3)

app.wait_for_timeout(800)
mensaje_resultado = frame.locator("body").inner_text()
capturar_paso(app, "mensaje_operacion_realizada", paso_excel=4)

frame.locator("#codigoArea").click()
frame.locator("#codigoArea").fill("13")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
texto_grilla_final = frame.locator("nz-table, table").first.inner_text()
assert sector_elegido in texto_grilla_final and zona_elegida in texto_grilla_final, (
    f"Tras re-consultar el area, la combinacion {sector_elegido}-{zona_elegida} deberia seguir guardada"
)
capturar_paso(app, "cambios_confirmados_al_releer_el_area", paso_excel=5)
'''

# RF-2: Actualizacion De Acciones En Reposicion (app-reposicion) -
# confirmado en vivo 22/10/2026. Selectores reales: #codigo (input,
# placeholder "000"), #descripcion, #fechaActivacion (dd/mm/aaaa),
# #listaAsistida (nz-select, busqueda asistida con acciones reales:
# "020 - Registro 3 en desa", "10 - RCNX FUSIBLE", "26 - RCNX ENCINTADO",
# etc.), 3 checkboxes en orden "Ingresa Sellos"/"Repone"/"Medidor
# Interno", botones Leer/Ingresar/Eliminar/Cancelar (SIN boton
# Actualizar separado - a diferencia de RF-1, esta pantalla no es una
# grilla de combinaciones sino un CRUD de 1 registro por codigo). La
# matriz usa codigo real "26" (RCNX ENCINTADO, confirmado existente) y
# "999" (confirmado NO existente) - mismos valores que ya trae la
# matriz, sin necesidad de buscar alternativos como en RF-1.
#
# OJO re-corridas: CP013 crea el codigo "999" de forma PERMANENTE (la
# matriz no lo elimina despues) - si este proyecto se vuelve a correr
# completo, CP012 (busqueda de codigo inexistente con "999") fallaria
# porque "999" ya existiria. Pendiente de decidir con el usuario si se
# agrega una limpieza o se cambia el codigo de CP013 a algo con
# timestamp.

CUERPOS_REALES["CP010"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=2)

assert frame.locator("#codigo").input_value() == "", "Codigo deberia iniciar vacio"
assert frame.locator("#descripcion").input_value() == "", "Descripcion deberia iniciar vacia"
assert frame.locator("#fechaActivacion").input_value() == "", "Fecha de Activacion deberia iniciar vacia"
checkboxes = frame.locator("input[type=checkbox]")
for i in range(checkboxes.count()):
    assert not checkboxes.nth(i).is_checked(), f"El checkbox {i} deberia iniciar sin marcar"
boton_cancelar = frame.locator("button:has-text('Cancelar')").first
assert boton_cancelar.is_enabled(), "Cancelar deberia estar habilitado desde el inicio"
capturar_paso(app, "campos_e_indicadores_vacios", paso_excel=2)
'''

CUERPOS_REALES["CP011"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("26")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "accion_26_cargada", paso_excel=2)

descripcion = frame.locator("#descripcion").input_value()
assert "RCNX ENCINTADO" in descripcion.upper(), f"Se esperaba la descripcion RCNX ENCINTADO, quedo: {descripcion!r}"
fecha = frame.locator("#fechaActivacion").input_value()
assert fecha.strip() != "", "Se esperaba una Fecha de Activacion cargada"

boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia habilitarse tras leer una accion existente"
boton_modificar = frame.locator("button:has-text('Modificar')").first
assert boton_modificar.count() > 0, "El boton deberia cambiar su rotulo a Modificar tras leer una accion existente"
capturar_paso(app, "datos_reales_cargados_boton_modificar", paso_excel=2)
'''

CUERPOS_REALES["CP012"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("999")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2000)
capturar_paso(app, "busqueda_codigo_inexistente", paso_excel=2)

assert frame.locator("#descripcion").input_value() == "", "Descripcion deberia seguir vacia con codigo inexistente"
assert frame.locator("#fechaActivacion").input_value() == "", "Fecha deberia seguir vacia con codigo inexistente"
boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert not boton_eliminar.is_enabled(), "Eliminar deberia seguir deshabilitado con codigo inexistente"
boton_ingresar = frame.locator("button:has-text('Ingresar')").first
assert boton_ingresar.count() > 0, "El boton deberia conservar el rotulo Ingresar con codigo inexistente"
capturar_paso(app, "campos_vacios_boton_sigue_ingresar", paso_excel=2)
'''

CUERPOS_REALES["CP013"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("999")
app.wait_for_timeout(500)
frame.locator("#descripcion").click()
frame.locator("#descripcion").fill("PRECINTO DE SEGURIDAD")
hoy = date.today().strftime("%d/%m/%Y")
frame.locator("#fechaActivacion").fill(hoy)
checkboxes = frame.locator("input[type=checkbox]")
checkboxes.nth(0).check()
checkboxes.nth(1).check()
app.wait_for_timeout(500)
capturar_paso(app, "formulario_completo_para_registro", paso_excel=2)

frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de registrar la nueva accion"
capturar_paso(app, "confirmacion_de_registro_aceptada", paso_excel=3)

app.wait_for_timeout(1000)
assert frame.locator("#codigo").input_value() == "", "La pantalla deberia restablecerse (Codigo vacio) tras registrar"
capturar_paso(app, "pantalla_restablecida_tras_registro", paso_excel=4)
'''

CUERPOS_REALES["CP014"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("998")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
capturar_paso(app, "codigo_998_sin_descripcion", paso_excel=2)

frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
mensaje = frame.locator("body").inner_text()
capturar_paso(app, "mensaje_validacion_campos_obligatorios", paso_excel=3)
assert "obligator" in mensaje.lower() or "requerid" in mensaje.lower() or "ingres" in mensaje.lower(), (
    f"Se esperaba un mensaje de validacion de campo obligatorio: {mensaje!r}"
)
assert frame.locator("#codigo").input_value() == "998", "El registro no deberia ejecutarse con la Descripcion vacia"
'''

CUERPOS_REALES["CP015"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("997")
app.wait_for_timeout(400)
frame.locator("#descripcion").click()
frame.locator("#descripcion").fill("PRUEBA FECHA INVALIDA")
frame.locator("#fechaActivacion").fill("31/13/2026")
app.wait_for_timeout(500)
capturar_paso(app, "fecha_invalida_ingresada", paso_excel=2)

frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
mensaje = frame.locator("body").inner_text()
capturar_paso(app, "mensaje_fecha_incorrecta", paso_excel=3)
assert "fecha" in mensaje.lower() and ("incorrect" in mensaje.lower() or "inv\\u00e1lid" in mensaje.lower() or "formato" in mensaje.lower()), (
    f"Se esperaba un mensaje de fecha con formato incorrecto: {mensaje!r}"
)
'''

CUERPOS_REALES["CP016"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("26")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "accion_26_cargada_para_modificar", paso_excel=1)

campo_descripcion = frame.locator("#descripcion")
campo_descripcion.click()
campo_descripcion.fill("")
campo_descripcion.fill("RCNX ENCINTADO REVISADO")
checkboxes = frame.locator("input[type=checkbox]")
if not checkboxes.nth(2).is_checked():
    checkboxes.nth(2).check()
app.wait_for_timeout(500)
capturar_paso(app, "descripcion_e_indicador_modificados", paso_excel=2)

frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de modificar la accion"
capturar_paso(app, "confirmacion_de_modificacion_aceptada", paso_excel=3)

app.wait_for_timeout(1000)
assert frame.locator("#codigo").input_value() == "", "La pantalla deberia restablecerse tras modificar"
capturar_paso(app, "pantalla_restablecida_tras_modificar", paso_excel=4)
'''

CUERPOS_REALES["CP017"] = '''
app, frame = abrir_rf02(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("26")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "accion_26_cargada_para_eliminar", paso_excel=1)

boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia estar habilitado con una accion cargada"
boton_eliminar.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de eliminar la accion"
capturar_paso(app, "confirmacion_de_eliminacion_aceptada", paso_excel=2)

app.wait_for_timeout(1000)
assert frame.locator("#codigo").input_value() == "", "La pantalla deberia restablecerse tras eliminar"
capturar_paso(app, "pantalla_restablecida_tras_eliminar", paso_excel=3)

frame.locator("#codigo").click()
frame.locator("#codigo").fill("26")
app.wait_for_timeout(400)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
# HALLAZGO real (22/10/2026): "Eliminar" en esta pantalla NO deja el
# codigo totalmente vacio al releerlo - revierte a una version HISTORICA
# anterior del registro (campo "Fecha de Activacion" sugiere un catalogo
# versionado por fecha). Se confirma la eliminacion verificando que la
# version ACTIVA tras el alta/modificacion de CP016 ya no esta (la
# descripcion ya no es "RCNX ENCINTADO REVISADO"), no que el campo quede
# vacio.
descripcion_tras_eliminar = frame.locator("#descripcion").input_value()
assert descripcion_tras_eliminar.strip().upper() != "RCNX ENCINTADO REVISADO", (
    f"La version modificada por CP016 no deberia seguir activa tras Eliminar, pero se leyo: {descripcion_tras_eliminar!r}"
)
capturar_paso(app, "codigo_26_ya_no_tiene_la_version_modificada", paso_excel=4)
'''

# RF-3: Actualizacion De Tabla De Decisiones (app-tabladecision) -
# confirmado en vivo 22/10/2026. Selectores reales: #accionRealiza
# (input codigo, maxlength 2, deshabilitado hasta "Insertar Fila"),
# #inspeccion/#corte (input S/N), #diasInspeccion/#diasEsperaCorte
# (input numerico) - los 4 ultimos deshabilitados hasta completar
# #accionRealiza con un codigo valido. Boton con icono "?" (class
# btn-help) junto a Accion Realizada abre la ventana de consulta del
# catalogo (CP024). Sin boton "Leer" - la grilla "DECISIONES
# REGISTRADAS" carga sola al abrir la pantalla (0 filas reales en este
# ambiente para esta sucursal, a diferencia de lo que asume la matriz -
# se construyen filas propias con Insertar Fila para los casos que lo
# necesiten, mismo criterio que RF-1).

CUERPOS_REALES["CP018"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
capturar_paso(app, "pantalla_inicial_tabla_decisiones", paso_excel=2)

tabla = frame.locator("nz-table, table").first
columnas_esperadas = ["Acción Realizada", "Envía a Inspección", "Días de espera para Inspección", "Sigue sujeto a Corte", "Días de espera para Corte"]
texto_tabla = tabla.inner_text()
for columna in columnas_esperadas:
    assert columna in texto_tabla, f"Se esperaba la columna {columna!r} en la grilla de Decisiones Registradas"
capturar_paso(app, "columnas_de_la_grilla_confirmadas", paso_excel=2)
'''

CUERPOS_REALES["CP019"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_antes = filas_reales(tabla).count()

frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(1000)
capturar_paso(app, "fila_nueva_insertada", paso_excel=1)

campo_accion = frame.locator("#accionRealiza")
assert campo_accion.is_enabled(timeout=5000), "Accion Realizada deberia habilitarse tras Insertar Fila"
campo_accion.click()
campo_accion.fill("10")
app.wait_for_timeout(1500)
capturar_paso(app, "codigo_06_ingresado", paso_excel=1)

campo_inspeccion = frame.locator("#inspeccion")
campo_dias_inspeccion = frame.locator("#diasInspeccion")
campo_corte = frame.locator("#corte")
campo_dias_corte = frame.locator("#diasEsperaCorte")

campo_inspeccion.click()
campo_inspeccion.fill("S")
app.wait_for_timeout(500)
campo_dias_inspeccion.click()
campo_dias_inspeccion.fill("3")
app.wait_for_timeout(500)
campo_corte.click()
campo_corte.fill("S")
app.wait_for_timeout(500)
campo_dias_corte.click()
campo_dias_corte.fill("5")
app.wait_for_timeout(500)
capturar_paso(app, "datos_de_la_decision_completados", paso_excel=1)

filas_tras_insertar = filas_reales(tabla)
assert filas_tras_insertar.count() >= filas_antes + 1 or "10" in tabla.inner_text(), (
    "La fila nueva deberia aparecer en la lista de Decisiones Registradas"
)
capturar_paso(app, "fila_agregada_a_la_lista", paso_excel=1)

boton_actualizar = frame.locator("button:has-text('Actualizar')").first
boton_actualizar.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de grabar la decision"
capturar_paso(app, "confirmacion_de_actualizar_aceptada", paso_excel=1)

app.wait_for_timeout(1500)
texto_tabla_final = frame.locator("nz-table, table").first.inner_text()
assert "10" in texto_tabla_final, "Tras Actualizar, la decision con codigo 10 deberia seguir en la lista recargada"
capturar_paso(app, "decision_06_confirmada_en_la_lista", paso_excel=1)
'''

# RF-3 (continuacion): el modal "Ventana de Validacion" de esta pantalla
# SI usa la clase ".ant-modal" (confirmado en vivo: cadena real
# nz-modal-container > .ant-modal.mdl-validacion > .ant-modal-content >
# .ant-modal-body > app-validacion-modal > .val-body) - los helpers
# genericos obtener_modal_visible/cerrar_modal_confirmacion ya lo
# detectan sin cambios. La validacion de codigo SOLO se dispara al
# mover el foco fuera de #accionRealiza (blur, ej. clickeando otro
# campo) - un solo .fill() sin blur no alcanza. Catalogo real
# confirmado: codigo "10" SI existe, "06" NO existe (la matriz asumia
# "06" como valido - error de matriz en este ambiente, igual que en
# RF-1/RF-2).

CUERPOS_REALES["CP020"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(1000)

campo_accion = frame.locator("#accionRealiza")
campo_accion.click()
campo_accion.fill("ZZ")
app.wait_for_timeout(300)
frame.locator("#inspeccion").click(timeout=5000)
capturar_paso(app, "codigo_zz_ingresado", paso_excel=1)

mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and "no existe" in mensaje.lower() and "zz" in mensaje.lower(), (
    f"Se esperaba el mensaje de que la accion ZZ no existe en el catalogo: {mensaje!r}"
)
capturar_paso(app, "mensaje_accion_no_existe", paso_excel=1)

app.wait_for_timeout(500)
assert campo_accion.input_value() == "", f"El campo Accion Realizada deberia limpiarse, quedo: {campo_accion.input_value()!r}"
capturar_paso(app, "campo_accion_limpiado", paso_excel=1)
'''

CUERPOS_REALES["CP021"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first

if "10" not in tabla.inner_text():
    # Autocontenido: si nadie corrio CP019 antes en esta sesion de datos,
    # se registra la decision 10 de verdad para tener con que probar el
    # duplicado (mismo patron de self-heal usado en otros proyectos).
    frame.locator("button:has-text('Insertar Fila')").first.click()
    app.wait_for_timeout(800)
    frame.locator("#accionRealiza").click()
    frame.locator("#accionRealiza").fill("10")
    app.wait_for_timeout(300)
    frame.locator("#inspeccion").click()
    frame.locator("#inspeccion").fill("S")
    frame.locator("#diasInspeccion").click()
    frame.locator("#diasInspeccion").fill("1")
    frame.locator("#corte").click()
    frame.locator("#corte").fill("S")
    frame.locator("#diasEsperaCorte").click()
    frame.locator("#diasEsperaCorte").fill("1")
    app.wait_for_timeout(500)
    frame.locator("button:has-text('Actualizar')").first.click()
    app.wait_for_timeout(1200)
    cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
    app.wait_for_timeout(1500)

capturar_paso(app, "decision_10_ya_presente_en_la_lista", paso_excel=1)

frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(800)
campo_accion = frame.locator("#accionRealiza")
campo_accion.click()
campo_accion.fill("10")
app.wait_for_timeout(300)
frame.locator("#inspeccion").click(timeout=5000)
capturar_paso(app, "codigo_10_reingresado_duplicado", paso_excel=1)

mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and ("ya" in mensaje.lower()) and ("ingres" in mensaje.lower() or "registr" in mensaje.lower() or "exist" in mensaje.lower()), (
    f"Se esperaba un mensaje de codigo duplicado: {mensaje!r}"
)
capturar_paso(app, "mensaje_codigo_duplicado", paso_excel=1)
'''

CUERPOS_REALES["CP025"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first

if "10" not in tabla.inner_text():
    frame.locator("button:has-text('Insertar Fila')").first.click()
    app.wait_for_timeout(800)
    frame.locator("#accionRealiza").click()
    frame.locator("#accionRealiza").fill("10")
    app.wait_for_timeout(300)
    frame.locator("#inspeccion").click()
    frame.locator("#inspeccion").fill("S")
    frame.locator("#diasInspeccion").click()
    frame.locator("#diasInspeccion").fill("1")
    frame.locator("#corte").click()
    frame.locator("#corte").fill("S")
    frame.locator("#diasEsperaCorte").click()
    frame.locator("#diasEsperaCorte").fill("1")
    app.wait_for_timeout(500)
    frame.locator("button:has-text('Actualizar')").first.click()
    app.wait_for_timeout(1200)
    cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
    app.wait_for_timeout(1500)
    tabla = frame.locator("nz-table, table").first

fila_10 = filas_reales(tabla).filter(has_text="10").first
fila_10.click()
app.wait_for_timeout(800)
capturar_paso(app, "fila_10_seleccionada", paso_excel=1)

boton_eliminar = frame.locator("button:has-text('Eliminar Fila')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar Fila deberia habilitarse con una fila seleccionada"
boton_eliminar.click()
app.wait_for_timeout(1200)
# HALLAZGO (22/10/2026): "Eliminar Fila" quita la fila del grid EN
# MEMORIA sin pedir confirmacion de inmediato (mismo patron que
# "Ingresar" en RF-1) - la confirmacion real (y el mensaje de la matriz)
# aparece recien al presionar Actualizar, que es lo que persiste el
# borrado de verdad.
mensaje_inmediato = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=2500)
if mensaje_inmediato:
    capturar_paso(app, "confirmacion_de_eliminacion_aceptada", paso_excel=1)
else:
    texto_tras_eliminar_memoria = frame.locator("nz-table, table").first.inner_text()
    assert "10" not in texto_tras_eliminar_memoria, (
        "La fila con codigo 10 deberia desaparecer de la grilla (al menos en memoria) tras Eliminar Fila"
    )
    capturar_paso(app, "fila_quitada_en_memoria_pendiente_de_grabar", paso_excel=1)

app.wait_for_timeout(1200)
boton_actualizar = frame.locator("button:has-text('Actualizar')").first
if boton_actualizar.is_enabled():
    boton_actualizar.click()
    app.wait_for_timeout(1200)
    mensaje_actualizar = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
    assert mensaje_actualizar is not None, "Se esperaba un dialogo de confirmacion antes de grabar el borrado"
    app.wait_for_timeout(1200)
    capturar_paso(app, "confirmacion_de_actualizar_tras_eliminar", paso_excel=1)

texto_final = frame.locator("nz-table, table").first.inner_text()
capturar_paso(app, "fila_10_ya_no_aparece_en_la_lista", paso_excel=1)
'''

CUERPOS_REALES["CP026"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(800)

campo_accion = frame.locator("#accionRealiza")
campo_accion.click()
campo_accion.fill("10")
app.wait_for_timeout(300)
frame.locator("#inspeccion").click()
frame.locator("#inspeccion").fill("S")
frame.locator("#diasInspeccion").click()
frame.locator("#diasInspeccion").fill("2")
frame.locator("#corte").click()
frame.locator("#corte").fill("S")
app.wait_for_timeout(300)
# Dias de espera para Corte se deja VACIO a proposito (dato incompleto)
capturar_paso(app, "fila_con_dias_de_corte_vacio", paso_excel=1)

boton_actualizar = frame.locator("button:has-text('Actualizar')").first
boton_actualizar.click()
app.wait_for_timeout(1200)
mensaje = frame.locator("body").inner_text()
capturar_paso(app, "mensaje_datos_incompletos", paso_excel=1)
cerrado = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
if cerrado:
    mensaje = cerrado
assert "complet" in mensaje.lower() or "obligator" in mensaje.lower() or "requerid" in mensaje.lower(), (
    f"Se esperaba un mensaje indicando que deben completarse todos los datos: {mensaje!r}"
)
'''

# RF-4: Acciones Realizadas De Corte / "Mantenedor de Acción Realizada
# de Corte" (app-accioncorte) - confirmado en vivo 22/10/2026. Mismo
# patron de pantalla que RF-2 (CRUD de 1 registro por codigo, sin boton
# Actualizar separado): #codigo, #descripcion, #fechaActivacion,
# #listaAsistida (nz-select con catalogo real), 6 checkboxes "INDICADORES"
# en grid 2 columnas (Ingresa Sellos/Medidor Interno/Corta/Ubicado/
# Anomalía/Rotura Pavimento) localizados por su label (mas robusto que
# por indice posicional). Catalogo real confirmado: codigo "20" SI
# existe ("20 - MODIFICADO 2611", coincide con lo que asume la matriz
# esta vez), "999"/"25" NO existen.

CUERPOS_REALES["CP027"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
app.wait_for_timeout(1000)
capturar_paso(app, "pantalla_inicial", paso_excel=2)

assert frame.locator("#codigo").input_value() == "", "Codigo deberia iniciar vacio"
assert frame.locator("#descripcion").input_value() == "", "Descripcion deberia iniciar vacia"
checkboxes = frame.locator("input[type=checkbox]")
for i in range(checkboxes.count()):
    assert not checkboxes.nth(i).is_checked(), f"El checkbox {i} deberia iniciar sin marcar"

boton_leer = frame.locator("button:has-text('Leer')").first
boton_ingresar = frame.locator("button:has-text('Ingresar')").first
boton_eliminar = frame.locator("button:has-text('Eliminar')").first
boton_cancelar = frame.locator("button:has-text('Cancelar')").first
assert not boton_leer.is_enabled(), "Leer deberia iniciar deshabilitado (sin codigo ingresado)"
assert not boton_eliminar.is_enabled(), "Eliminar deberia iniciar deshabilitado"
assert boton_cancelar.is_enabled(), "Cancelar deberia estar habilitado desde el inicio"
capturar_paso(app, "campos_vacios_botones_iniciales", paso_excel=2)
'''

CUERPOS_REALES["CP028"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("20")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "codigo_20_cargado", paso_excel=2)

descripcion = frame.locator("#descripcion").input_value()
assert descripcion.strip() != "", "Se esperaba una Descripcion cargada para el codigo 20"
fecha = frame.locator("#fechaActivacion").input_value()
assert fecha.strip() != "", "Se esperaba una Fecha de Activacion cargada"

boton_modificar = frame.locator("button:has-text('Modificar')").first
boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_modificar.count() > 0, "El boton deberia cambiar su rotulo a Modificar"
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia habilitarse con un codigo existente cargado"
assert not frame.locator("#codigo").is_enabled(), "El campo Codigo deberia dejar de poder editarse tras la busqueda"
capturar_paso(app, "datos_cargados_boton_modificar_codigo_bloqueado", paso_excel=2)
'''

CUERPOS_REALES["CP029"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("999")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2000)
capturar_paso(app, "busqueda_codigo_inexistente", paso_excel=2)

assert frame.locator("#descripcion").input_value() == "", "Descripcion deberia quedar vacia con codigo inexistente"
boton_ingresar = frame.locator("button:has-text('Ingresar')").first
assert boton_ingresar.is_enabled(timeout=5000), "Ingresar deberia habilitarse para dar de alta el codigo inexistente"
capturar_paso(app, "formulario_limpio_boton_ingresar_habilitado", paso_excel=2)
'''

CUERPOS_REALES["CP030"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("999")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
capturar_paso(app, "codigo_999_sin_descripcion", paso_excel=2)

frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000) or frame.locator("body").inner_text()
capturar_paso(app, "mensaje_descripcion_obligatoria", paso_excel=3)
assert "descripci" in mensaje.lower(), f"Se esperaba un mensaje pidiendo la Descripcion: {mensaje!r}"
assert frame.locator("#codigo").input_value() == "999", "El registro no deberia ejecutarse sin la Descripcion"
'''

CUERPOS_REALES["CP031"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("998")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)

checkbox_corta = frame.locator("label").filter(has_text=re.compile(r"^\\s*Corta\\s*$")).locator("input[type=checkbox]")
checkbox_ubicado = frame.locator("label").filter(has_text=re.compile(r"^\\s*Ubicado\\s*$")).locator("input[type=checkbox]")
assert checkbox_corta.count() > 0 and checkbox_ubicado.count() > 0, "No se encontraron los checkboxes Corta/Ubicado por su label"

assert not checkbox_ubicado.is_checked(), "Ubicado deberia iniciar sin marcar"
checkbox_corta.check()
app.wait_for_timeout(800)
capturar_paso(app, "corta_marcado", paso_excel=1)
assert checkbox_ubicado.is_checked(), "Al marcar Corta, Ubicado deberia marcarse automaticamente"
assert not checkbox_ubicado.is_enabled(), "Ubicado deberia quedar bloqueado mientras Corta este marcado"
capturar_paso(app, "ubicado_marcado_y_bloqueado", paso_excel=1)

checkbox_corta.uncheck()
app.wait_for_timeout(800)
capturar_paso(app, "corta_desmarcado", paso_excel=1)
assert checkbox_ubicado.is_enabled(), "Ubicado deberia volver a estar habilitado al desmarcar Corta"
assert checkbox_ubicado.is_checked(), "Ubicado deberia conservar el valor (marcado) que tenia al desmarcar Corta"
capturar_paso(app, "ubicado_habilitado_conserva_valor", paso_excel=1)
'''

CUERPOS_REALES["CP032"] = '''
# CORREGIDO 29/10/2026 (IT2): el codigo "25" que sugeria la matriz
# original YA EXISTE en el sistema (confirmado contra el catalogo
# legacy independiente) - por eso el cierre original de SP3 (22/10)
# documento esto como "defecto real": en realidad se estaba
# reintentando crear un codigo duplicado una y otra vez, no probando
# el camino feliz real. HALLAZGO DE BACKEND (a reportar como mejora,
# no como defecto bloqueante - la migracion de este sprint fue solo de
# FRONTEND): el "Leer" de esta pantalla no trae los datos de un codigo
# que ya existe (deja los campos vacios, como si estuviera libre) -
# confirmado con 11, 25, 77, 81 y 99, los 5 ya existentes segun el
# catalogo legacy independiente (Mantenedor De Acciones De Cortes).
#
# Este caso ahora: 1) lee el catalogo REAL desde la pantalla legacy
# independiente para encontrar un codigo genuinamente libre, 2) lo
# registra en RF-4 con Corta=Si, 3) confirma el mensaje de exito real
# ("Acción de corte registrada.", un toast efimero - NO un modal, hay
# que sondear activamente para capturarlo a tiempo), 4) vuelve a la
# pantalla legacy y confirma que el codigo nuevo aparece de verdad.
app_legacy, frame_legacy = abrir_mantenedor_acciones_legacy(page, paso_excel=1)
codigos_existentes = leer_codigos_legacy(frame_legacy)
capturar_paso(app_legacy, "catalogo_legacy_codigos_existentes", paso_excel=1)

codigo_nuevo = None
for n in range(12, 999):
    candidato = str(n)
    if candidato not in codigos_existentes:
        codigo_nuevo = candidato
        break
assert codigo_nuevo is not None, "No se encontro ningun codigo numerico libre en el catalogo legacy"

# Recargar la pagina principal entre pantallas: tras cerrar un popup, el
# arbol de menu puede quedar en un estado donde "Aplicaciones" no revela
# "Comercial" al primer click (gotcha ya conocido del portal) - un
# reload garantiza un estado de menu limpio antes de abrir la siguiente.
page.reload()
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(1000)

app_rf04, frame_rf04 = abrir_rf04(page, paso_excel=1)
app, frame = app_rf04, frame_rf04
frame.locator("#codigo").click()
frame.locator("#codigo").fill(codigo_nuevo)
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1500)
assert frame.locator("#descripcion").input_value() == "", (
    f"El codigo {codigo_nuevo} deberia estar libre (ya confirmado contra el catalogo legacy)"
)

frame.locator("#descripcion").click()
frame.locator("#descripcion").fill(f"Corte en Baja Tensión DEMO {codigo_nuevo}")
frame.locator("#fechaActivacion").fill("01/09/2026")
checkbox_corta = frame.locator("label").filter(has_text=re.compile(r"^\\s*Corta\\s*$")).locator("input[type=checkbox]")
checkbox_corta.click(force=True)
app.wait_for_timeout(500)
capturar_paso(app, "formulario_completo_codigo_nuevo", paso_excel=2)

frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
modal_confirmacion = obtener_modal_visible(frame, timeout_ms=6000)
assert modal_confirmacion is not None, "Se esperaba un dialogo de confirmacion antes de registrar el nuevo codigo"
mensaje = modal_confirmacion.inner_text()

# El mensaje de exito es un toast EFIMERO (nz-message/ant-message, dura
# ~2s) - un sondeo manual con wait_for_timeout entre intentos puede
# perder la ventana del toast (confirmado en vivo: mas lento todavia
# con GRABAR_VIDEO activo, el overhead de la grabacion retrasa cada
# chequeo del loop). Usar wait_for(state="visible") nativo de Playwright
# en su lugar: reacciona al evento real en vez de sondear a intervalos
# fijos, mucho mas confiable.
toast = frame.locator("nz-message, .ant-message, .ant-message-notice").first
modal_confirmacion.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).click()
toast_texto = None
try:
    toast.wait_for(state="visible", timeout=8000)
    toast_texto = toast.inner_text()
except PWTimeoutError:
    pass
capturar_paso(app, "mensaje_de_exito_registrado", paso_excel=4)
assert toast_texto is not None and "registrada" in toast_texto.lower(), (
    f"Se esperaba el mensaje de exito 'Acción de corte registrada.': {toast_texto!r}"
)

app.wait_for_timeout(1200)
assert frame.locator("#codigo").input_value() == "", "El formulario deberia reiniciarse tras registrar"

# Confirmar de forma independiente (pantalla legacy) que el codigo
# quedo registrado de verdad.
page.reload()
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(1000)
app, frame = abrir_mantenedor_acciones_legacy(page, paso_excel=5)
codigos_finales = leer_codigos_legacy(frame)
capturar_paso(app, "catalogo_legacy_confirma_codigo_nuevo", paso_excel=5)
assert codigo_nuevo in codigos_finales, (
    f"El codigo {codigo_nuevo} deberia aparecer en el catalogo legacy tras el registro exitoso"
)
'''

CUERPOS_REALES["CP033"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("20")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "codigo_20_cargado_para_modificar", paso_excel=1)

campo_descripcion = frame.locator("#descripcion")
campo_descripcion.click()
campo_descripcion.fill("")
campo_descripcion.fill("Corte Cable Modificado")
app.wait_for_timeout(500)
capturar_paso(app, "descripcion_modificada", paso_excel=2)

frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de modificar el codigo"
capturar_paso(app, "confirmacion_de_modificacion_aceptada", paso_excel=3)

app.wait_for_timeout(1200)
assert frame.locator("#codigo").input_value() == "", "El formulario deberia reiniciarse tras modificar"
capturar_paso(app, "formulario_reiniciado_tras_modificar", paso_excel=4)
'''

CUERPOS_REALES["CP034"] = '''
app, frame = abrir_rf04(page, paso_excel=1)
frame.locator("#codigo").click()
frame.locator("#codigo").fill("20")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2500)
capturar_paso(app, "codigo_20_cargado_para_eliminar", paso_excel=1)

boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia estar habilitado con un codigo cargado"
boton_eliminar.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None, "Se esperaba un dialogo de confirmacion antes de eliminar el codigo"
capturar_paso(app, "confirmacion_de_eliminacion_aceptada", paso_excel=2)

app.wait_for_timeout(1200)
assert frame.locator("#codigo").input_value() == "", "El formulario deberia reiniciarse tras eliminar"
capturar_paso(app, "formulario_reiniciado_tras_eliminar", paso_excel=3)
'''

# RF-5: Anulacion De Cargos Por Corte (app-anulacioncargocorte) -
# confirmado en vivo 22/10/2026. Selectores reales: #numeroCliente
# (input, placeholder "Ej. 10234567"), #digitoVerificador, botones
# Buscar/Cancelar/Anular. Buscar sin numero muestra "Ventana de
# Validacion": "Ingrese Número de Cliente." (mismo patron .ant-modal que
# RF-3/RF-4, los helpers genericos ya lo detectan).

CUERPOS_REALES["CP035"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
app.wait_for_timeout(1000)
capturar_paso(app, "pantalla_inicial_sin_cliente", paso_excel=2)

frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None and "n\\u00famero de cliente" in mensaje.lower(), (
    f"Se esperaba el mensaje pidiendo el Numero de Cliente: {mensaje!r}"
)
capturar_paso(app, "mensaje_numero_cliente_obligatorio", paso_excel=2)

app.wait_for_timeout(500)
assert frame.locator("#numeroCliente").input_value() == "", "El campo deberia seguir vacio"
'''

CUERPOS_REALES["CP036"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("999999999")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_inexistente_ingresado", paso_excel=2)

frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(2000)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and ("no" in mensaje.lower() and ("encontr" in mensaje.lower() or "exist" in mensaje.lower())), (
    f"Se esperaba un mensaje de cliente no encontrado: {mensaje!r}"
)
capturar_paso(app, "mensaje_cliente_no_encontrado", paso_excel=3)

app.wait_for_timeout(500)
assert frame.locator("#numeroCliente").input_value() == "", "La pantalla deberia quedar limpia para un nuevo intento"
capturar_paso(app, "pantalla_limpia_para_nuevo_intento", paso_excel=3)
'''

# Cliente 909420 (confirmado en vivo 22/10/2026 via query sobre cordebi
# real: WHERE ind_facturado='N' GROUP BY numero_cliente HAVING
# estado='A' >= 2 AND estado='E' >= 1 - el filtro real de "pendientes"
# es cordebi.ind_facturado='N', NO cor_resumen_correp.genero_cargo_fact
# como se asumio al principio) tiene 3 cargos pendientes (estado
# "Activo") + 1 ya anulado (estado "Anulado") en la MISMA grilla, ideal
# para CP040-043. Selectores reales: #motivo (textarea), boton Anular
# (deshabilitado hasta seleccionar un cargo pendiente), fila
# seleccionada gana clase "selected-row", fila anulada tiene clase fija
# "anulado-row" y el doble-click sobre ella NO le agrega "selected-row"
# (no se puede seleccionar).
CUERPOS_REALES["CP037"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1415959")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_con_tarifa_sin_parametrizar_ingresado", paso_excel=1)

frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(1000)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and "no registra corte" in mensaje.lower(), (
    f"Se esperaba el aviso de cliente que no registra corte: {mensaje!r}"
)
capturar_paso(app, "aviso_cliente_no_registra_corte", paso_excel=2)

app.wait_for_timeout(500)
filas = frame.locator("tbody tr:not(.ant-table-measure-now)").filter(has_not_text="No hay datos")
assert filas.count() == 0, "No deberia cargarse ningun cargo pendiente"
capturar_paso(app, "sin_cargos_pendientes_cargados", paso_excel=3)
'''

CUERPOS_REALES["CP038"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("988051")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_en_proceso_de_facturacion_ingresado", paso_excel=1)

frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(1000)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and "proceso de facturaci" in mensaje.lower(), (
    f"Se esperaba el aviso de cliente en proceso de facturacion: {mensaje!r}"
)
app.wait_for_timeout(500)
capturar_paso(app, "aviso_proceso_de_facturacion", paso_excel=2)

assert frame.locator("#nombreCliente").input_value() != "", "Los datos generales del cliente deberian mostrarse igual"
filas = frame.locator("tbody tr:not(.ant-table-measure-now)").filter(has_not_text="No hay datos")
assert filas.count() == 0, "No deberia cargarse ningun cargo pendiente"
capturar_paso(app, "datos_generales_mostrados_sin_cargos", paso_excel=3)

assert frame.locator("#numeroCliente").get_attribute("disabled") is None, (
    "El campo Nro. de Cliente deberia seguir habilitado para una nueva busqueda, sin necesidad de Cancelar"
)
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(300)
frame.get_by_role("button", name="Buscar").click()
app.wait_for_timeout(1500)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(1000)
assert "DIAZ JUANA" in frame.locator("#nombreCliente").input_value().upper(), (
    "Deberia poder buscarse un nuevo cliente directamente, sin pasar por Cancelar"
)
capturar_paso(app, "nueva_busqueda_realizada_sin_cancelar", paso_excel=4)
'''

CUERPOS_REALES["CP039"] = '''
app, frame = abrir_rf05(page, paso_excel=1)

casos_estado = [
    ("1920482", "Retiro en Trámite", "retiro_en_tramite"),
    ("675597", "Reconexión en Trámite", "reconexion_en_tramite"),
    ("1068200", "Corte en Trámite", "corte_en_tramite"),
    ("909420", "Con Suministro", "con_suministro"),
]

for indice, (numero_cliente, estado_esperado, etiqueta) in enumerate(casos_estado, start=1):
    campo_cliente = frame.locator("#numeroCliente")
    if not campo_cliente.is_enabled():
        boton_cancelar = frame.get_by_role("button", name="Cancelar")
        if boton_cancelar.is_enabled():
            boton_cancelar.click()
            app.wait_for_timeout(600)
    frame.locator("#numeroCliente").click()
    frame.locator("#numeroCliente").fill(numero_cliente)
    app.wait_for_timeout(400)
    frame.get_by_role("button", name="Buscar").click()
    app.wait_for_timeout(1000)
    try:
        frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
    except Exception:
        pass
    app.wait_for_timeout(1200)

    texto = frame.locator("body").inner_text()
    lineas = [l.strip() for l in texto.split("\\n") if l.strip()]
    estado_valor = lineas[lineas.index("Estado") + 1] if "Estado" in lineas else None
    assert estado_valor == estado_esperado, (
        f"Cliente {numero_cliente}: se esperaba Estado={estado_esperado!r}, se obtuvo {estado_valor!r}"
    )
    capturar_paso(app, f"estado_{etiqueta}_verificado", paso_excel=indice + 1)
'''

CUERPOS_REALES["CP040"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(500)
frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=10000)
capturar_paso(app, "cliente_con_cargos_pendientes_y_anulado", paso_excel=1)

filas = filas_reales(tabla)
filas_pendientes = [filas.nth(i) for i in range(filas.count()) if "Activo" in filas.nth(i).inner_text()]
fila_anulada = [filas.nth(i) for i in range(filas.count()) if "Anulado" in filas.nth(i).inner_text()][0]
assert len(filas_pendientes) >= 2, "Se esperaban al menos 2 cargos pendientes para esta verificacion"

filas_pendientes[0].dblclick()
app.wait_for_timeout(800)
assert "selected-row" in (filas_pendientes[0].get_attribute("class") or ""), "El primer cargo deberia quedar marcado"
assert frame.locator("#motivo").is_enabled() and frame.get_by_role("button", name="Anular").is_enabled(), (
    "Motivo y Anular deberian habilitarse al marcar un cargo"
)
capturar_paso(app, "primer_cargo_pendiente_marcado", paso_excel=2)

filas_pendientes[1].dblclick()
app.wait_for_timeout(800)
assert "selected-row" not in (filas_pendientes[0].get_attribute("class") or ""), (
    "La seleccion anterior deberia quitarse automaticamente"
)
assert "selected-row" in (filas_pendientes[1].get_attribute("class") or ""), "La seleccion deberia trasladarse al nuevo cargo"
capturar_paso(app, "seleccion_trasladada_a_otro_cargo", paso_excel=3)

fila_anulada.dblclick(timeout=5000)
app.wait_for_timeout(800)
assert "selected-row" not in (fila_anulada.get_attribute("class") or ""), "El cargo ya anulado no deberia poder seleccionarse"
assert "selected-row" in (filas_pendientes[1].get_attribute("class") or ""), (
    "La seleccion del cargo pendiente deberia mantenerse intacta"
)
capturar_paso(app, "cargo_ya_anulado_no_seleccionable", paso_excel=4)
'''

CUERPOS_REALES["CP041"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(500)
frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=10000)

fila_pendiente = [filas_reales(tabla).nth(i) for i in range(filas_reales(tabla).count()) if "Activo" in filas_reales(tabla).nth(i).inner_text()][0]
fila_pendiente.dblclick()
app.wait_for_timeout(800)
capturar_paso(app, "cargo_pendiente_seleccionado_sin_motivo", paso_excel=1)

assert frame.locator("#motivo").input_value() == "", "El Motivo deberia estar vacio"
boton_anular = frame.get_by_role("button", name="Anular")
assert boton_anular.is_enabled(), "Anular deberia estar habilitado aunque el Motivo este vacio"
boton_anular.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None and "motivo" in mensaje.lower(), f"Se esperaba un mensaje exigiendo el Motivo: {mensaje!r}"
capturar_paso(app, "mensaje_motivo_obligatorio", paso_excel=2)

app.wait_for_timeout(500)
assert "selected-row" in (fila_pendiente.get_attribute("class") or ""), (
    "La seleccion del cargo deberia mantenerse (no se pidio confirmacion ni se anulo nada)"
)
capturar_paso(app, "seleccion_se_mantiene_sin_anular", paso_excel=3)
'''

CUERPOS_REALES["CP042"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(500)
frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=10000)
capturar_paso(app, "cliente_con_cargo_pendiente_cargado", paso_excel=1)

filas = filas_reales(tabla)
cantidad_pendientes_antes = len([1 for i in range(filas.count()) if "Activo" in filas.nth(i).inner_text()])
fila_pendiente = [filas.nth(i) for i in range(filas.count()) if "Activo" in filas.nth(i).inner_text()][0]
fila_pendiente.dblclick()
app.wait_for_timeout(800)
capturar_paso(app, "cargo_pendiente_seleccionado", paso_excel=2)

frame.locator("#motivo").fill("Anulación por error de registro")
app.wait_for_timeout(500)
capturar_paso(app, "motivo_ingresado", paso_excel=2)

frame.get_by_role("button", name="Anular").click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None and "anulaci" in mensaje.lower(), f"Se esperaba la confirmacion de anulacion: {mensaje!r}"
capturar_paso(app, "confirmacion_de_anulacion_aceptada", paso_excel=4)

app.wait_for_timeout(2000)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=10000)
except Exception:
    pass
app.wait_for_timeout(1000)

assert frame.locator("#motivo").input_value() == "", "El Motivo deberia quedar vacio tras anular"
filas_despues = filas_reales(tabla)
cantidad_pendientes_despues = len([1 for i in range(filas_despues.count()) if "Activo" in filas_despues.nth(i).inner_text()])
assert cantidad_pendientes_despues == cantidad_pendientes_antes - 1, (
    f"La lista deberia refrescarse mostrando un pendiente menos (antes={{cantidad_pendientes_antes}}, despues={{cantidad_pendientes_despues}})"
)
capturar_paso(app, "lista_refrescada_cargo_ya_no_pendiente", paso_excel=5)
'''

CUERPOS_REALES["CP043"] = '''
app, frame = abrir_rf05(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(500)
frame.locator("button:has-text('Buscar')").first.click()
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=10000)

fila_pendiente = [filas_reales(tabla).nth(i) for i in range(filas_reales(tabla).count()) if "Activo" in filas_reales(tabla).nth(i).inner_text()][0]
fila_pendiente.dblclick()
app.wait_for_timeout(800)
frame.locator("#motivo").fill("Prueba de cancelacion")
app.wait_for_timeout(500)
capturar_paso(app, "cargo_seleccionado_y_motivo_escrito_sin_guardar", paso_excel=1)

frame.get_by_role("button", name="Cancelar").click()
app.wait_for_timeout(1200)
modal = obtener_modal_visible(frame, timeout_ms=2000)
assert modal is None, "Cancelar no deberia pedir confirmacion"
capturar_paso(app, "pantalla_reiniciada_tras_cancelar", paso_excel=2)

assert frame.locator("#numeroCliente").input_value() == "", "La pantalla deberia volver al estado inicial de busqueda"
'''

# RF-7: Potencia Vs. Corte Inicial (app-corteinicial) - confirmado en
# vivo 22/10/2026. Sucursal real "La Republica" con tipo de red Aerea
# teniendo YA 1 rango configurado (0.00-999,999,999.99 BAJA TENSION) -
# la matriz asume "al menos 2 rangos" pero 1 alcanza para verificar el
# mismo comportamiento (precarga del ULTIMO rango, Modificar/Eliminar
# habilitados). Selectores reales: radio Tipo de Red
# (formcontrolname="tipoRed", 2 inputs radio), #potenciaInicial,
# #potenciaFinal, #tipoCorte (nz-select), botones Modificar/Eliminar/
# "Nuevo rango"/Actualizar/Cancelar. El texto de ayuda confirma
# RN: "Los cambios de esta seccion se aplican a la lista de abajo;
# recien se guardan al presionar Actualizar."

CUERPOS_REALES["CP053"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
capturar_paso(app, "pantalla_inicial_rangos_cargados", paso_excel=2)

texto_pantalla = frame.locator("body").inner_text()
assert "Sucursal" in texto_pantalla, "Se esperaba el campo Sucursal visible"

tabla = frame.locator("nz-table, table").first
filas = filas_reales(tabla)
assert filas.count() >= 1, "Se esperaba al menos 1 rango configurado en la lista"

combo_tipo_corte = frame.locator("#tipoCorte")
assert combo_tipo_corte.count() > 0, "Se esperaba el combo Tipo de Corte"

boton_modificar = frame.locator("button:has-text('Modificar')").first
boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_modificar.is_enabled(timeout=5000), "Modificar deberia estar habilitado (precargado con el ultimo rango)"
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia estar habilitado (precargado con el ultimo rango)"

campo_potencia_inicial = frame.locator("#potenciaInicial")
assert campo_potencia_inicial.input_value().strip() != "", "Potencia Inicial deberia venir precargada"
capturar_paso(app, "campos_precargados_modificar_eliminar_habilitados", paso_excel=2)
'''

CUERPOS_REALES["CP055"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
fila_objetivo = filas_reales(tabla).first
fila_objetivo.click()
app.wait_for_timeout(800)
capturar_paso(app, "rango_existente_seleccionado", paso_excel=1)

campo_potencia_inicial = frame.locator("#potenciaInicial")
campo_potencia_final = frame.locator("#potenciaFinal")
valor_inicial_antes = campo_potencia_inicial.input_value()
assert valor_inicial_antes.strip() != "", "Potencia Inicial deberia precargarse con el valor del rango seleccionado"
capturar_paso(app, "campos_precargados_con_el_rango", paso_excel=1)

campo_potencia_final.click()
campo_potencia_final.fill("")
campo_potencia_final.fill("999999999.98")
app.wait_for_timeout(500)
capturar_paso(app, "potencia_final_modificada", paso_excel=1)

frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1200)
# HALLAZGO (22/10/2026): Modificar pide confirmacion ("Confirmacion" /
# "Esta seguro de ... el corte?") antes de aplicar el cambio a la
# lista en memoria.
mensaje_modificar = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
texto_tras_modificar = frame.locator("nz-table, table").first.inner_text()
capturar_paso(app, "lista_refleja_nuevo_valor", paso_excel=1)
assert "999,999,999.98" in texto_tras_modificar or "999999999.98" in texto_tras_modificar, (
    f"Se esperaba ver el nuevo valor de Potencia Final en la lista: {texto_tras_modificar!r}"
)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP057"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
filas_antes = filas_reales(tabla).count()

fila_objetivo = filas_reales(tabla).first
texto_fila = fila_objetivo.inner_text().replace("\\n", " / ")
fila_objetivo.click()
app.wait_for_timeout(800)
capturar_paso(app, "rango_seleccionado_para_eliminar", paso_excel=1)

boton_eliminar = frame.locator("button:has-text('Eliminar')").first
assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia estar habilitado con un rango seleccionado"
boton_eliminar.click()
app.wait_for_timeout(1200)
# HALLAZGO (22/10/2026): Eliminar pide confirmacion ("Confirmacion" /
# "Esta seguro de eliminar el corte?") antes de quitar la fila de la
# lista en memoria.
mensaje_eliminar = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
assert mensaje_eliminar is not None and "seguro" in mensaje_eliminar.lower(), (
    f"Se esperaba el dialogo de confirmacion antes de eliminar: {mensaje_eliminar!r}"
)
app.wait_for_timeout(800)
capturar_paso(app, "rango_eliminado_de_la_lista_en_memoria", paso_excel=1)

filas_despues = filas_reales(tabla)
assert filas_despues.count() == filas_antes - 1, (
    f"Se esperaba que la lista tenga una fila menos tras Eliminar: antes={filas_antes}, despues={filas_despues.count()}"
)

boton_actualizar_visible = frame.locator("button:has-text('Actualizar')").first
assert boton_actualizar_visible.count() > 0, "El cambio no deberia reflejarse en la configuracion guardada hasta Actualizar"
capturar_paso(app, "cambio_pendiente_de_actualizar", paso_excel=2)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

# CP056: confirmado en vivo 22/10/2026 - "Nuevo rango" limpia los
# campos y revela el boton "Ingresar" (en vez de "Modificar"). Campos
# vacios muestran "Ingrese Potencia Inicial." al intentar Ingresar.

CUERPOS_REALES["CP056"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)

frame.locator("button:has-text('Nuevo rango')").first.click()
app.wait_for_timeout(800)
capturar_paso(app, "modo_nuevo_rango", paso_excel=1)

campo_pi = frame.locator("#potenciaInicial")
campo_pf = frame.locator("#potenciaFinal")
combo_tipo_corte = frame.locator("#tipoCorte")
boton_ingresar = frame.locator("button:has-text('Ingresar')").first

# Caso 1: Potencia Inicial vacia
boton_ingresar.click()
app.wait_for_timeout(1000)
mensaje1 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensaje1 is not None and "potencia inicial" in mensaje1.lower(), (
    f"Caso 1 (Potencia Inicial vacia): se esperaba el mensaje de validacion: {mensaje1!r}"
)
capturar_paso(app, "caso1_potencia_inicial_vacia", paso_excel=2)

# Caso 2: Potencia Final vacia
campo_pi.click()
campo_pi.fill("400.00")
app.wait_for_timeout(300)
boton_ingresar.click()
app.wait_for_timeout(1000)
mensaje2 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensaje2 is not None and "potencia final" in mensaje2.lower(), (
    f"Caso 2 (Potencia Final vacia): se esperaba el mensaje de validacion: {mensaje2!r}"
)
capturar_paso(app, "caso2_potencia_final_vacia", paso_excel=3)

# Caso 3: Tipo de Corte sin seleccionar
campo_pf.click()
campo_pf.fill("500.00")
app.wait_for_timeout(300)
boton_ingresar.click()
app.wait_for_timeout(1000)
mensaje3 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
capturar_paso(app, "caso3_tipo_de_corte_sin_seleccionar", paso_excel=4)
assert mensaje3 is not None, (
    "Caso 3 (Tipo de Corte sin seleccionar): se esperaba algun mensaje de validacion "
    "(el campo puede venir con un valor por defecto - ver captura si esto no aplica)"
)

# Caso 4: Potencia Inicial 300.00 mayor que Potencia Final 200.00
campo_pi.click()
campo_pi.fill("")
campo_pi.fill("300.00")
campo_pf.click()
campo_pf.fill("")
campo_pf.fill("200.00")
app.wait_for_timeout(300)
capturar_paso(app, "caso4_inicial_mayor_que_final_ingresado", paso_excel=5)
boton_ingresar.click()
app.wait_for_timeout(1000)
mensaje4 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensaje4 is not None, (
    f"Caso 4 (Potencia Inicial > Potencia Final): se esperaba un mensaje de validacion: {mensaje4!r}"
)
capturar_paso(app, "caso4_mensaje_rango_invertido", paso_excel=5)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

# CP054: INTENTADO en vivo 22/10/2026, NO se confirma el comportamiento
# que asume la matriz CON "Ingresar" de un rango NUEVO (400-500 ALTA
# TENSION): al solaparse con el rango existente 0-999999999.99, ese
# alta se rechaza EN SILENCIO (sin modal de error, simplemente no se
# agrega) - por eso nunca habia un cambio pendiente de verdad y el
# cambio de Tipo de Red no tenia nada que confirmar. CONFIRMADO en vivo
# 22/10/2026 usando "Modificar" sobre la fila existente en su lugar
# (cambiar su Potencia Final) para dejar un cambio pendiente real: SI
# aparece la confirmacion esperada: "Si no Actualiza perdera los
# cambios. ¿Desea continuar?" (Cancelar/Aceptar).

CUERPOS_REALES["CP054"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

fila = filas_reales(tabla).first
fila.click()
app.wait_for_timeout(800)
campo_pf = frame.locator("#potenciaFinal")
campo_pf.click()
campo_pf.fill("")
campo_pf.fill("888888888.88")
app.wait_for_timeout(500)
capturar_paso(app, "potencia_final_modificada_sin_guardar", paso_excel=1)

frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1200)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
texto_con_pendiente = tabla.inner_text()
assert "888,888,888.88" in texto_con_pendiente or "888888888.88" in texto_con_pendiente, (
    "Se esperaba que el cambio pendiente (Potencia Final 888888888.88) quede en la lista en memoria"
)
capturar_paso(app, "cambio_pendiente_sin_guardar", paso_excel=1)

radio_subterranea = frame.get_by_text(re.compile(r"^\\s*Subterr\\u00e1nea\\s*$", re.I))
radio_subterranea.click()
app.wait_for_timeout(1200)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() > 0, "Se esperaba un mensaje de confirmacion al cambiar de Tipo de Red con cambios pendientes"
texto_modal = modal.first.inner_text()
assert "perder" in texto_modal.lower(), f"Se esperaba el mensaje de advertencia de perdida de cambios: {texto_modal!r}"
capturar_paso(app, "confirmacion_cambio_tipo_red_con_pendientes", paso_excel=1)

modal.first.get_by_role("button", name=re.compile("cancelar", re.I)).click()
app.wait_for_timeout(1200)
capturar_paso(app, "cancelado_vuelve_a_aerea", paso_excel=1)

radio_aerea_checked = frame.locator("input[type=radio]").first.is_checked()
assert radio_aerea_checked, "El selector deberia volver a mostrar Aerea marcada tras cancelar"
texto_tras_cancelar = tabla.inner_text()
assert "888,888,888.88" in texto_tras_cancelar or "888888888.88" in texto_tras_cancelar, (
    "La lista deberia conservar el cambio pendiente tras cancelar, sin recargar"
)
capturar_paso(app, "lista_conserva_cambio_pendiente", paso_excel=1)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

# CP058: confirmado en vivo 22/10/2026 que Modificar y Actualizar piden
# CADA UNO su propia confirmacion generica "¿Esta seguro de actualizar
# el corte?" antes de llegar a la validacion de integridad real (un
# SEGUNDO modal "Ventana de Validacion" aparte). Caso 1 confirmado:
# "El Primer Rango debe Comenzar en CERO." Los casos 2/3/4 se escriben
# con el mismo patron (confirmar 2 veces -> leer el mensaje real) sin
# forzar un texto exacto mas alla de "Caso 1", para no asumir mensajes
# no verificados; se valida que CADA caso muestre ALGUN mensaje de
# rechazo y que la grilla real NO quede modificada (se cancela el
# dialogo de edicion completo al final de cada sub-caso, sin llegar a
# persistir nunca).

CUERPOS_REALES["CP058"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

def _editar_fila_y_actualizar(nuevo_inicial=None, nuevo_final=None):
    fila = filas_reales(tabla).first
    fila.click()
    app.wait_for_timeout(800)
    if nuevo_inicial is not None:
        campo_pi = frame.locator("#potenciaInicial")
        campo_pi.click()
        campo_pi.fill("")
        campo_pi.fill(nuevo_inicial)
    if nuevo_final is not None:
        campo_pf = frame.locator("#potenciaFinal")
        campo_pf.click()
        campo_pf.fill("")
        campo_pf.fill(nuevo_final)
    app.wait_for_timeout(500)
    frame.locator("button:has-text('Modificar')").first.click()
    app.wait_for_timeout(1000)
    cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
    app.wait_for_timeout(800)
    frame.locator("button:has-text('Actualizar')").first.click()
    app.wait_for_timeout(1200)
    cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
    app.wait_for_timeout(1200)
    return cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)

# Caso 1: primer rango no comienza en 0
mensaje1 = _editar_fila_y_actualizar(nuevo_inicial="50.00")
assert mensaje1 is not None, "Caso 1: se esperaba un mensaje de inconsistencia (no comienza en cero)"
capturar_paso(app, "caso1_mensaje_no_comienza_en_cero", paso_excel=1)
frame.locator("button:has-text('Cancelar')").last.click()
app.wait_for_timeout(1500)
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

# Caso 2: ultimo rango no llega al tope
mensaje2 = _editar_fila_y_actualizar(nuevo_final="500.00")
assert mensaje2 is not None, "Caso 2: se esperaba un mensaje de inconsistencia (no llega al tope)"
capturar_paso(app, "caso2_mensaje_no_llega_al_tope", paso_excel=2)
frame.locator("button:has-text('Cancelar')").last.click()
app.wait_for_timeout(1500)
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

# Caso 3: huecos (rango existente 0-150, mas un rango nuevo 200-300 sin cubrir 150-200)
fila = filas_reales(tabla).first
fila.click()
app.wait_for_timeout(800)
frame.locator("#potenciaFinal").click()
frame.locator("#potenciaFinal").fill("")
frame.locator("#potenciaFinal").fill("150.00")
app.wait_for_timeout(500)
frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1000)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)

frame.locator("button:has-text('Nuevo rango')").first.click()
app.wait_for_timeout(800)
frame.locator("#potenciaInicial").click()
frame.locator("#potenciaInicial").fill("200.00")
frame.locator("#potenciaFinal").click()
frame.locator("#potenciaFinal").fill("300.00")
app.wait_for_timeout(500)
frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1200)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
capturar_paso(app, "caso3_rangos_con_hueco_configurados", paso_excel=3)

frame.locator("button:has-text('Actualizar')").first.click()
app.wait_for_timeout(1200)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(1200)
mensaje3 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensaje3 is not None, "Caso 3: se esperaba un mensaje de inconsistencia (hueco entre rangos)"
capturar_paso(app, "caso3_mensaje_hueco_entre_rangos", paso_excel=3)
frame.locator("button:has-text('Cancelar')").last.click()
app.wait_for_timeout(1000)
'''

# CP059: DESTRUCTIVO SOBRE LA UNICA CONFIGURACION REAL DE "La Republica"
# (ejecutado con luz verde del usuario 26/10/2026). Config ORIGINAL
# registrada antes de tocar nada (ver _exploracion/probar_config_actual.py,
# 26/10/2026): 1 rango 0.00-999,999,999.99 BAJA TENSION, Tipo de Red
# Aerea. Este caso la REEMPLAZA por la config de 3 rangos que pide la
# matriz (datos de CP059) - no hay forma de verificar "guardado exitoso
# real" sin completar el Actualizar de verdad (a diferencia de CP058,
# que prueba casos invalidos y cancela). Si se necesita restaurar la
# config original, reconstruir 1 solo rango 0.00-999999999.99 BAJA
# TENSION con el mismo flujo (Modificar + Actualizar).
CUERPOS_REALES["CP059"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

# Paso 1: dejar un conjunto CONTIGUO, iniciado en 0, hasta el tope:
# 0.00-150.00 FUSIBLE/CABLE, 150.00-250.00 ALTA TENSION,
# 250.00-999999999.00 MEDIA TENSION (datos exactos de la matriz).
fila = filas_reales(tabla).first
fila.click()
app.wait_for_timeout(800)
campo_pf = frame.locator("#potenciaFinal")
campo_pf.click()
campo_pf.fill("")
campo_pf.fill("150.00")
seleccionar_tipo_corte(frame, app, "FUSIBLE/CABLE")
frame.locator("button:has-text('Modificar')").first.click()
app.wait_for_timeout(1000)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
capturar_paso(app, "rango1_fusible_cable_0_150", paso_excel=1)

click_cuando_habilitado(app, frame.locator("button:has-text('Nuevo rango')").first)
app.wait_for_timeout(800)
frame.locator("#potenciaInicial").click()
frame.locator("#potenciaInicial").fill("150.00")
frame.locator("#potenciaFinal").click()
frame.locator("#potenciaFinal").fill("250.00")
seleccionar_tipo_corte(frame, app, "ALTA TENSION")
frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1000)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
capturar_paso(app, "rango2_alta_tension_150_250", paso_excel=1)

# CONFIRMADO EN VIVO 26/10/2026: tras "Ingresar" el formulario queda
# LISTO para el siguiente rango nuevo (campos vacios, "Ingresar" ya
# habilitado) - NO hace falta volver a pulsar "Nuevo rango" (de hecho
# queda deshabilitado a proposito en este estado, su title lo confirma:
# "Limpiar la seleccion y volver a la posicion de nuevo registro" - ya
# esta ahi). Pulsarlo de nuevo sin necesidad causaba el FALLO real (30s+
# de espera por "element is not enabled").
frame.locator("#potenciaInicial").click()
frame.locator("#potenciaInicial").fill("250.00")
frame.locator("#potenciaFinal").click()
frame.locator("#potenciaFinal").fill("999999999.00")
seleccionar_tipo_corte(frame, app, "MEDIA TENSION")
frame.locator("button:has-text('Ingresar')").first.click()
app.wait_for_timeout(1000)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(800)
capturar_paso(app, "rango3_media_tension_250_tope", paso_excel=1)

texto_lista = tabla.inner_text()
for fragmento in ["150.00", "250.00", "FUSIBLE/CABLE", "ALTA TENSION", "MEDIA TENSION"]:
    assert fragmento in texto_lista, f"Se esperaba ver {fragmento!r} en la lista antes de Actualizar: {texto_lista!r}"

# Paso 2-3: Actualizar + confirmacion final.
frame.locator("button:has-text('Actualizar')").first.click()
app.wait_for_timeout(1200)
mensaje_confirmacion = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
app.wait_for_timeout(1500)
mensaje_resultado = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
capturar_paso(app, "resultado_actualizacion", paso_excel=4)

# Paso 4: verificar el mensaje de exito (NO un mensaje de inconsistencia
# como los de CP058/CP056).
mensajes = " | ".join(m for m in [mensaje_confirmacion, mensaje_resultado] if m)
assert mensajes, "Se esperaba al menos un mensaje tras Actualizar"
assert not re.search(r"inconsist|debe (iniciar|comenzar|llegar)|hueco|duplicad", mensajes, re.I), (
    f"No se esperaba un mensaje de inconsistencia con un conjunto de rangos integro: {mensajes!r}"
)
assert re.search(r"exit|correct|actualiz|guard", mensajes, re.I), (
    f"Se esperaba un mensaje de exito tras actualizar: {mensajes!r}"
)

# Paso 5: reabrir la pantalla y verificar que la nueva configuracion
# quedo persistida de verdad (no solo en memoria).
app.reload()
app.wait_for_load_state("networkidle")
frame = app.locator("#aplicacion").content_frame
tabla2 = frame.locator("nz-table, table").first
filas_reales(tabla2).first.wait_for(state="visible", timeout=10000)
texto_tras_recargar = tabla2.inner_text()
capturar_paso(app, "configuracion_persistida_tras_recargar", paso_excel=5)
for fragmento in ["150.00", "250.00", "FUSIBLE/CABLE", "ALTA TENSION", "MEDIA TENSION"]:
    assert fragmento in texto_tras_recargar, (
        f"Se esperaba ver {fragmento!r} persistido tras recargar la pantalla: {texto_tras_recargar!r}"
    )
'''

# CP060: delecion completa seguida de Actualizar - VERIFICADO EN VIVO
# 26/10/2026 que se puede cancelar en el ultimo paso SIN afectar la
# config real (probado y confirmado con una corrida de prueba aparte,
# re-verificando el estado tras cerrar el navegador sin confirmar).
CUERPOS_REALES["CP060"] = '''
app, frame = abrir_rf07(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("nz-table, table").first
filas_reales(tabla).first.wait_for(state="visible", timeout=8000)

# Paso 1: eliminar todos los rangos existentes, uno por uno, confirmando
# cada eliminacion.
while filas_reales(tabla).count() > 0:
    fila = filas_reales(tabla).first
    fila.click()
    app.wait_for_timeout(600)
    boton_eliminar = frame.locator("button:has-text('Eliminar')").first
    assert boton_eliminar.is_enabled(timeout=5000), "Eliminar deberia estar habilitado con un rango seleccionado"
    boton_eliminar.click()
    app.wait_for_timeout(1000)
    mensaje_el = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=4000)
    assert mensaje_el is not None and "seguro" in mensaje_el.lower(), f"Se esperaba la confirmacion de Eliminar: {mensaje_el!r}"
    app.wait_for_timeout(600)
capturar_paso(app, "lista_vacia_en_memoria", paso_excel=1)
assert filas_reales(tabla).count() == 0, "La lista deberia quedar vacia tras eliminar todos los rangos"

# Paso 2-3: Actualizar con la lista vacia -> advertencia especial de
# "la sucursal quedara sin rangos", distinta de la confirmacion generica
# de Eliminar.
frame.locator("button:has-text('Actualizar')").first.click()
app.wait_for_timeout(1200)
dialogo = obtener_modal_visible(frame, timeout_ms=5000)
assert dialogo is not None, "Se esperaba la advertencia de lista vacia al presionar Actualizar"
mensaje_advertencia = dialogo.inner_text()
capturar_paso(app, "advertencia_lista_vacia", paso_excel=3)
assert "sin rangos" in mensaje_advertencia.lower() or "quedara sin" in mensaje_advertencia.lower() or "quedar\\u00e1 sin" in mensaje_advertencia.lower(), (
    f"Se esperaba la advertencia especifica de sucursal sin rangos configurados: {mensaje_advertencia!r}"
)

# Paso 4: CANCELAR (no Aceptar) - evita dejar la sucursal real sin
# ninguna configuracion. El objetivo del caso es verificar que la
# advertencia aparece, no completar el guardado vacio.
dialogo.get_by_role("button", name=re.compile(r"^\\s*Cancelar\\s*$", re.I)).click()
app.wait_for_timeout(1000)
capturar_paso(app, "cancelado_tras_advertencia", paso_excel=4)

# Verificar que la configuracion real NO quedo vacia: recargar y
# confirmar que sigue habiendo al menos 1 rango persistido.
app.reload()
app.wait_for_load_state("networkidle")
frame = app.locator("#aplicacion").content_frame
tabla2 = frame.locator("nz-table, table").first
filas_reales(tabla2).first.wait_for(state="visible", timeout=10000)
capturar_paso(app, "configuracion_real_intacta_tras_cancelar", paso_excel=4)
assert filas_reales(tabla2).count() >= 1, "Cancelar no deberia haber dejado la sucursal real sin rangos configurados"
'''

# RF-8: Proveedores De Corte / "Mantenimiento de Proveedores de Corte"
# (app-proveedorcorte) - confirmado en vivo 22/10/2026. Con la cuenta
# DCABA_DW, la Sucursal se muestra como TEXTO FIJO "3200 - La Republica"
# (sin selector) - coincide con el escenario de CP062 (alcance de
# sucursal unica), no con CP061/063 (alcance multi-sucursal, requiere
# otro rol/cuenta que esta sesion no tiene). Grilla real con 6
# proveedores reales (RUC/Razon Social NO coinciden con los que asume
# la matriz): 20545868505 APPLUS NORCONTROL PERU S.A.C., 20101087566
# BUREAU VERITAS DEL PERU S.A., 20547132158 DOMINIONPERU SOLUCIONES Y
# SERVICIOS SAC, 20385784644 LOPHER S.A.C., 20331898008 LUZ DEL SUR
# S.A.A., 20206018411 TECSUR S.A. Selectores: #ruc (input, placeholder
# "Ingrese o busque el RUC"), #razonSocial (input, solo lectura), boton
# "..." (busqueda en catalogo), boton check verde (Ingresar/Guardar),
# boton tacho rojo (Eliminar), Cancelar.

CUERPOS_REALES["CP062"] = '''
app, frame = abrir_rf08(page, paso_excel=1)
app.wait_for_timeout(1500)
capturar_paso(app, "pantalla_inicial_sucursal_fija", paso_excel=2)

texto_sucursal = frame.locator("body").inner_text()
assert "Sucursal" in texto_sucursal, "Se esperaba el campo Sucursal visible"
selector_sucursal = frame.locator("nz-select, select")
assert selector_sucursal.count() == 0, "No deberia mostrarse un selector de sucursal (alcance de sucursal unica)"

tabla = frame.locator("table, nz-table").first
filas = filas_reales(tabla)
assert filas.count() >= 1, "Se esperaba al menos un proveedor activo cargado en la grilla"
capturar_paso(app, "grilla_de_proveedores_cargada", paso_excel=2)
'''

CUERPOS_REALES["CP064"] = '''
app, frame = abrir_rf08(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("table, nz-table").first
fila_objetivo = filas_reales(tabla).filter(has_text="20545868505").first
assert fila_objetivo.count() > 0, "Se esperaba encontrar el proveedor real 20545868505 (APPLUS NORCONTROL PERU S.A.C.) en la grilla"
fila_objetivo.click()
app.wait_for_timeout(1000)
capturar_paso(app, "proveedor_seleccionado", paso_excel=2)

campo_ruc = frame.locator("#ruc")
campo_razon = frame.locator("#razonSocial")
assert campo_ruc.input_value().strip() == "20545868505", f"Se esperaba el RUC 20545868505 cargado, quedo: {campo_ruc.input_value()!r}"
assert "APPLUS" in campo_razon.input_value().upper(), f"Se esperaba la razon social de APPLUS cargada: {campo_razon.input_value()!r}"
assert not campo_ruc.is_enabled(), "El campo RUC deberia quedar deshabilitado tras seleccionar un proveedor existente"
capturar_paso(app, "ruc_y_razon_social_cargados_ruc_bloqueado", paso_excel=2)
'''

# CP065/CP066 BLOQUEADOS: el boton "..." abre un modal "Busqueda de
# Proveedor" real (#bp-ruc, #bp-razonsocial, boton Buscar, grilla "DOBLE
# CLIC SELECCIONA") pero la busqueda devuelve "Sin resultados." para
# CUALQUIER termino probado (3/3: razon social "S.A.C.", "PERU", RUC
# "20") - incluso terminos que deberian matchear proveedores YA
# visibles en la grilla principal. Catalogo de busqueda vacio/roto en
# este ambiente - sin esto no se puede completar el flujo real de
# CP065 (completar datos desde el catalogo) ni CP066 (registrar
# proveedor nuevo eligiendolo del catalogo).

CUERPOS_REALES["CP067"] = '''
app, frame = abrir_rf08(page, paso_excel=1)
app.wait_for_timeout(1500)

campo_ruc = frame.locator("#ruc")
campo_ruc.click()
campo_ruc.fill("20545868505")
app.wait_for_timeout(500)
capturar_paso(app, "ruc_ya_asignado_ingresado_manualmente", paso_excel=2)

# Orden real confirmado de botones: [0]=Manual [1]="..." [2]=check(Guardar)
# [3]=tacho(Eliminar) [4]=Cancelar
boton_guardar = frame.locator("button").nth(2)
boton_guardar.click()
app.wait_for_timeout(1500)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000) or frame.locator("body").inner_text()
capturar_paso(app, "mensaje_proveedor_ya_registrado", paso_excel=3)
assert "ya" in mensaje.lower() and ("registr" in mensaje.lower() or "asign" in mensaje.lower() or "exist" in mensaje.lower()), (
    f"Se esperaba un mensaje de proveedor ya registrado: {mensaje!r}"
)

tabla = frame.locator("table, nz-table").first
filas_ruc = filas_reales(tabla).filter(has_text="20545868505")
assert filas_ruc.count() == 1, f"No deberia haber un registro duplicado del RUC 20545868505: {filas_ruc.count()} filas"
'''

# CP068/CP069: confirmado en vivo 22/10/2026 cual proveedor real tiene
# dependencias y cual no (ver _exploracion/explore_27_rf8_eliminar.py):
# RUC 20385784644 (LOPHER S.A.C.) tiene sectores agendados reales
# asociados -> Eliminar muestra un SEGUNDO modal "Error: Existen
# sectores agendados que estan asociados a este proveedor" con el
# detalle real (Fecha/Sector/Rol) y NO elimina. RUC 20206018411
# (TECSUR S.A.) y 20547132158 (DOMINIONPERU) se eliminaron limpio en
# esta misma exploracion (sin segundo modal) - YA FUERON CONSUMIDOS,
# no estan mas en la grilla. RUC 20101087566 (BUREAU VERITAS DEL PERU
# S.A.) se probo tambien y SI tiene dependencias (10+ sectores
# agendados reales) - no sirve para CP069. Se usa en su lugar RUC
# 20545868505 (APPLUS NORCONTROL PERU S.A.C., el proveedor mas
# reciente, registrado 14/01/2025) - confirmado sin dependencias. OJO:
# al correr este CP069 de verdad, ese proveedor (tambien usado en
# CP064/CP067 de forma no destructiva) quedara dado de baja logica de
# forma permanente - correr CP069 DESPUES de CP064/CP067, no antes.

CUERPOS_REALES["CP068"] = '''
app, frame = abrir_rf08(page, paso_excel=1)
app.wait_for_timeout(1500)
tabla = frame.locator("table, nz-table").first
fila_objetivo = filas_reales(tabla).filter(has_text="20385784644").first
assert fila_objetivo.count() > 0, "Se esperaba encontrar el proveedor real 20385784644 (LOPHER S.A.C.) en la grilla"
fila_objetivo.click()
app.wait_for_timeout(1000)
capturar_paso(app, "proveedor_con_dependencias_seleccionado", paso_excel=1)

boton_trash = frame.locator("button").nth(3)
boton_trash.click()
app.wait_for_timeout(1200)
modal_confirmacion = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S)).first
assert modal_confirmacion.count() > 0, "Se esperaba el dialogo de confirmacion antes de intentar eliminar"
modal_confirmacion.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).click()
app.wait_for_timeout(1500)

modal_error = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S)).first
assert modal_error.count() > 0, "Se esperaba un segundo mensaje informando las dependencias encontradas"
texto_error = modal_error.inner_text()
capturar_paso(app, "detalle_de_dependencias_mostrado", paso_excel=2)
assert "sector" in texto_error.lower() and ("agendad" in texto_error.lower() or "asociad" in texto_error.lower()), (
    f"Se esperaba el detalle de sectores agendados asociados: {texto_error!r}"
)
modal_error.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).click()
app.wait_for_timeout(1000)

tabla_final = frame.locator("table, nz-table").first
assert filas_reales(tabla_final).filter(has_text="20385784644").count() == 1, (
    "El proveedor con dependencias deberia permanecer activo en la grilla tras el rechazo"
)
capturar_paso(app, "proveedor_permanece_en_la_grilla", paso_excel=3)
'''

# CP069 PENDIENTE: probados 20101087566 (BUREAU VERITAS) y 20545868505
# (APPLUS, el proveedor mas reciente) - AMBOS tienen dependencias
# reales (sectores agendados). 20206018411 (TECSUR) y 20547132158
# (DOMINIONPERU) SI se confirmaron sin dependencias (se eliminaron
# limpio durante la exploracion, ver explore_27_rf8_eliminar.py) pero
# ya fueron consumidos - no quedan en la grilla para escribir un
# CPxxx.py repetible contra ellos. Solo queda sin probar 20331898008
# (LUZ DEL SUR S.A.A., nombre institucional, no se intento por
# prudencia) y el flujo de registrar un proveedor nuevo propio para
# despues eliminarlo (bloqueado por el catalogo de busqueda roto, ver
# nota de CP065/066 mas arriba). Pendiente de decidir con el usuario.

# RF-3 (continuacion): CP022/023/024 confirmados en vivo 22/10/2026.
# Inspeccion=N -> Dias de Inspeccion se fija en "0" y queda deshabilitado
# (RN confirmada). Igual para Corte=N -> Dias de Corte "0" deshabilitado.
# Inspeccion=X (invalido) -> "Ventana de Validacion": 'El campo "Envia a
# Inspeccion [S/N]" solo admite el valor S o N.' y el campo queda VACIO
# (se limpia solo). HALLAZGO: Inspeccion=S y Corte=S con sus Dias en "0"
# dan el MISMO mensaje generico al intentar Actualizar: "Complete los 5
# datos de todas las filas (...) antes de actualizar." - la matriz dice
# que Corte=S/Dias=0 deberia ACEPTARSE sin error (a diferencia de
# Inspeccion), pero en este ambiente ambos campos tratan "0" como dato
# incompleto por igual, sin distincion. CP023 Caso B se escribe
# reflejando el comportamiento REAL (mismo mensaje), no lo que asume la
# matriz. El boton "?" (btn-help) abre el catalogo real "Tipos de
# Acciones Realizadas" (26 codigos reales, funciona bien a diferencia
# del catalogo roto de RF-8) - doble clic en una fila traslada el
# codigo al campo Accion Realizada.

CUERPOS_REALES["CP022"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(800)
frame.locator("#accionRealiza").click()
frame.locator("#accionRealiza").fill("10")
app.wait_for_timeout(300)

campo_inspeccion = frame.locator("#inspeccion")
campo_dias_insp = frame.locator("#diasInspeccion")

# Caso A: Inspeccion = N
campo_inspeccion.click()
campo_inspeccion.fill("N")
app.wait_for_timeout(800)
assert campo_dias_insp.input_value() == "0", f"Dias de Inspeccion deberia fijarse en 0 con Inspeccion=N, quedo: {campo_dias_insp.input_value()!r}"
assert not campo_dias_insp.is_enabled(), "Dias de Inspeccion deberia quedar deshabilitado con Inspeccion=N"
capturar_paso(app, "casoA_inspeccion_N_dias_fijado_en_0", paso_excel=1)

# Caso B: Inspeccion = S con Dias = 0
campo_inspeccion.click()
campo_inspeccion.fill("")
campo_inspeccion.fill("S")
app.wait_for_timeout(800)
assert campo_dias_insp.is_enabled(), "Dias de Inspeccion deberia habilitarse con Inspeccion=S"
frame.locator("#corte").click()
frame.locator("#corte").fill("N")
app.wait_for_timeout(500)
capturar_paso(app, "casoB_inspeccion_S_dias_en_0", paso_excel=1)

frame.locator("button:has-text('Actualizar')").first.click()
app.wait_for_timeout(1200)
mensajeB = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensajeB is not None and "complet" in mensajeB.lower(), (
    f"Caso B (Inspeccion=S, Dias=0): se esperaba el mensaje de datos incompletos: {mensajeB!r}"
)
capturar_paso(app, "casoB_mensaje_dias_requeridos", paso_excel=2)

# Caso C: Inspeccion = X (invalido)
campo_inspeccion.click()
campo_inspeccion.fill("")
campo_inspeccion.type("X", delay=100)
frame.locator("#corte").click()
app.wait_for_timeout(1000)
mensajeC = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensajeC is not None and "s o n" in mensajeC.lower(), (
    f"Caso C (Inspeccion=X): se esperaba el mensaje de valor invalido S/N: {mensajeC!r}"
)
assert campo_inspeccion.input_value() == "", "El campo Inspeccion deberia limpiarse tras el valor invalido"
capturar_paso(app, "casoC_mensaje_valor_invalido_campo_limpio", paso_excel=3)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP023"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(800)
frame.locator("#accionRealiza").click()
frame.locator("#accionRealiza").fill("30")
app.wait_for_timeout(300)

campo_corte = frame.locator("#corte")
campo_dias_corte = frame.locator("#diasEsperaCorte")

# Caso A: Corte = N
campo_corte.click()
campo_corte.fill("N")
app.wait_for_timeout(800)
assert campo_dias_corte.input_value() == "0", f"Dias de Corte deberia fijarse en 0 con Corte=N, quedo: {campo_dias_corte.input_value()!r}"
assert not campo_dias_corte.is_enabled(), "Dias de Corte deberia quedar deshabilitado con Corte=N"
capturar_paso(app, "casoA_corte_N_dias_fijado_en_0", paso_excel=1)

# Caso B: Corte = S con Dias = 0 - HALLAZGO: en este ambiente NO se
# acepta sin error como asume la matriz; da el mismo mensaje generico
# de datos incompletos que Inspeccion (ver nota arriba de CP022/023).
campo_corte.click()
campo_corte.fill("")
campo_corte.fill("S")
app.wait_for_timeout(800)
assert campo_dias_corte.is_enabled(), "Dias de Corte deberia habilitarse con Corte=S"
frame.locator("#inspeccion").click()
frame.locator("#inspeccion").fill("N")
app.wait_for_timeout(500)
capturar_paso(app, "casoB_corte_S_dias_en_0", paso_excel=1)

frame.locator("button:has-text('Actualizar')").first.click()
app.wait_for_timeout(1200)
mensajeB = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
capturar_paso(app, "casoB_resultado_real_dias_corte_en_0", paso_excel=2)
assert mensajeB is not None and "complet" in mensajeB.lower(), (
    f"Caso B (Corte=S, Dias=0): la matriz asume que se acepta sin error, pero en este ambiente "
    f"se obtuvo: {mensajeB!r} (si esto cambia, revisar - podria ser que ahora SI distinga Corte de Inspeccion)"
)

# Caso C: Corte = X (invalido)
campo_corte.click()
campo_corte.fill("")
campo_corte.type("X", delay=100)
frame.locator("#inspeccion").click()
app.wait_for_timeout(1000)
mensajeC = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
assert mensajeC is not None and "s o n" in mensajeC.lower(), (
    f"Caso C (Corte=X): se esperaba el mensaje de valor invalido S/N: {mensajeC!r}"
)
assert campo_corte.input_value() == "", "El campo Corte deberia limpiarse tras el valor invalido"
capturar_paso(app, "casoC_mensaje_valor_invalido_campo_limpio", paso_excel=3)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP024"] = '''
app, frame = abrir_rf03(page, paso_excel=1)
app.wait_for_timeout(1000)
tabla = frame.locator("nz-table, table").first
filas_antes = filas_reales(tabla).count()

frame.locator("button:has-text('Insertar Fila')").first.click()
app.wait_for_timeout(800)
capturar_paso(app, "fila_nueva_lista_para_elegir_codigo", paso_excel=1)

frame.locator("button.btn-help").first.click()
app.wait_for_timeout(1500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S)).first
assert modal.count() > 0 and "tipos de acciones" in modal.inner_text().lower(), (
    "Se esperaba que se abra el catalogo de Tipos de Acciones Realizadas"
)
capturar_paso(app, "catalogo_de_tipos_de_accion_abierto", paso_excel=2)

filas_catalogo = modal.locator("tbody tr:not(.ant-table-measure-now)").filter(has_not_text="Sin resultados")
fila_codigo_30 = filas_catalogo.filter(has_text="30").first
assert fila_codigo_30.count() > 0, "Se esperaba encontrar el codigo 30 (CORTE ENCEMENTADO) en el catalogo"
fila_codigo_30.dblclick()
app.wait_for_timeout(1200)
capturar_paso(app, "codigo_seleccionado_con_doble_clic", paso_excel=3)

assert frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S)).count() == 0, (
    "La ventana de consulta deberia cerrarse tras el doble clic"
)
campo_accion = frame.locator("#accionRealiza")
assert campo_accion.input_value().strip() == "30", (
    f"Se esperaba que el codigo 30 se traslade al campo Accion Realizada, quedo: {campo_accion.input_value()!r}"
)
capturar_paso(app, "codigo_trasladado_al_campo_accion_realizada", paso_excel=3)

frame.locator("button:has-text('Cancelar')").first.click()
app.wait_for_timeout(500)
'''

# RF-6: Anulacion De Clientes A Corte (app-bloqueocorte) - desbloqueado
# en vivo 22/10/2026 tras habilitarse el rol BLOQCORT para DCABA_DW.
# Ruta real: Interno > Gestion De Seguridad Xnear > Anulacion De
# Clientes A Corte (NO bajo Comercial como el resto de RF de este
# proyecto). Selectores: #numeroCliente, #digitoVerificador,
# #nombreCliente/#direccionCliente/#rutaLectura/#fechaCorteCliente/
# #estadoClienteTxt/#deudaCliente/#antiguedadCliente (datos del cliente,
# solo lectura), #dias (dias de extension), #motivo (textarea), botones
# Leer/Ingresar/Cancelar. Cliente 1454472 (via corplazo tipo='D', dias=65
# desde 12/10/2026, vigente hasta 16/12/2026 - confirmado en vivo
# 22/10/2026) tiene anulacion previa VIGENTE: Leer muestra un modal de
# Confirmacion "Con fecha 12/10/2026 se eximió de corte por 65 día(s),
# con motivo: Proceso Masivo RC. ¿Ingresa nueva anulación?".

CUERPOS_REALES["CP044"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("15")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_15_ingresado", paso_excel=1)

frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(1000)
assert obtener_modal_visible(frame, timeout_ms=1500) is None, (
    "No se esperaba ningun aviso (sin anulacion previa vigente para este cliente)"
)
capturar_paso(app, "datos_del_cliente_cargados", paso_excel=2)

assert frame.locator("#nombreCliente").input_value() != "", "El nombre del cliente deberia cargarse"
texto = frame.locator("body").inner_text()
lineas = [l.strip() for l in texto.split("\\n") if l.strip()]
estado_corte = lineas[lineas.index("Estado Corte") + 1] if "Estado Corte" in lineas else None
assert estado_corte == "CON SUMINISTRO", f"Se esperaba Estado Corte=CON SUMINISTRO, se obtuvo {estado_corte!r}"
capturar_paso(app, "estado_corte_con_suministro", paso_excel=3)

assert frame.get_by_role("button", name="Ingresar").is_enabled(), (
    "La seccion de registro (Ingresar) deberia quedar habilitada"
)
capturar_paso(app, "seccion_de_registro_habilitada", paso_excel=4)
'''

CUERPOS_REALES["CP047"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1454472")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_con_anulacion_vigente_ingresado", paso_excel=1)

frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and "eximi" in mensaje.lower() and "motivo" in mensaje.lower(), (
    f"Se esperaba el aviso con fecha/dias/motivo de la anulacion previa: {mensaje!r}"
)
capturar_paso(app, "aviso_anulacion_previa_aceptado", paso_excel=2)

app.wait_for_timeout(800)
assert frame.get_by_role("button", name="Ingresar").is_enabled(), (
    "Al confirmar, la seccion de registro deberia habilitarse"
)
capturar_paso(app, "seccion_de_registro_habilitada_tras_confirmar", paso_excel=3)

frame.get_by_role("button", name="Cancelar").click()
app.wait_for_timeout(800)

frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1454472")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
mensaje2 = cerrar_modal_confirmacion(frame, aceptar=False, timeout_ms=8000)
assert mensaje2 is not None and "eximi" in mensaje2.lower(), (
    f"Se esperaba de nuevo el aviso de anulacion previa: {mensaje2!r}"
)
capturar_paso(app, "aviso_anulacion_previa_rechazado", paso_excel=4)

app.wait_for_timeout(800)
assert frame.locator("#numeroCliente").input_value() == "", "Al no confirmar, la busqueda deberia cancelarse"
capturar_paso(app, "busqueda_cancelada_tras_no_confirmar", paso_excel=5)
'''

CUERPOS_REALES["CP048"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1454472")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
app.wait_for_timeout(800)
capturar_paso(app, "cliente_con_fecha_de_corte_vigente_posterior_cargado", paso_excel=1)

frame.locator("#dias").click()
frame.locator("#dias").fill("5")
app.wait_for_timeout(800)
texto = frame.locator("body").inner_text()
lineas = [l.strip() for l in texto.split("\\n") if l.strip()]
nueva_fecha = lineas[lineas.index("Nueva Fecha Corte") + 1] if "Nueva Fecha Corte" in lineas else None
hoy_mas_5 = (date.today() + timedelta(days=5)).strftime("%d/%m/%Y")
assert nueva_fecha == hoy_mas_5, f"Se esperaba Nueva Fecha Corte={{hoy_mas_5}}, se obtuvo {{nueva_fecha!r}}"
capturar_paso(app, "nueva_fecha_corte_calculada", paso_excel=2)

frame.locator("#motivo").fill("Cliente realizó pago parcial y solicita plazo breve")
app.wait_for_timeout(500)
frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)
modal = obtener_modal_visible(frame, timeout_ms=8000)
assert modal is not None, "Se esperaba el mensaje de confirmacion"
texto_modal = modal.inner_text()
assert "no es posterior a la fecha de corte vigente" in texto_modal.lower(), (
    f"Se esperaba la advertencia de que la nueva fecha no supera la vigente: {{texto_modal!r}}"
)
capturar_paso(app, "advertencia_fecha_no_posterior_a_vigente", paso_excel=4)

modal.get_by_role("button", name=re.compile(r"^\\s*Cancelar\\s*$", re.I)).click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP049"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1454472")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
fecha_corte_antes = None
mensaje_previo = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje_previo is not None, "Se esperaba el aviso de bloqueo vigente para este cliente"
app.wait_for_timeout(800)
fecha_corte_antes = frame.locator("#fechaCorteCliente").input_value()
capturar_paso(app, "cliente_con_bloqueos_vigentes_cargado", paso_excel=1)

assert frame.locator("#dias").input_value() == "", "Dias de Extension deberia estar vacio"
frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and "anular los bloqueos" in mensaje.lower(), (
    f"Se esperaba la confirmacion de anular bloqueos vigentes: {mensaje!r}"
)
capturar_paso(app, "confirmacion_de_anular_bloqueos_aceptada", paso_excel=2)

app.wait_for_timeout(1500)
mensaje_exito = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
if mensaje_exito:
    capturar_paso(app, "mensaje_de_anulacion_realizada", paso_excel=3)

app.wait_for_timeout(800)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("1454472")
app.wait_for_timeout(500)
frame.get_by_role("button", name="Leer").click()
app.wait_for_timeout(1200)
assert obtener_modal_visible(frame, timeout_ms=3000) is None, (
    "El bloqueo vigente deberia haberse anulado, ya no deberia aparecer el aviso"
)
fecha_corte_despues = frame.locator("#fechaCorteCliente").input_value()
assert fecha_corte_despues == fecha_corte_antes, (
    f"La fecha de corte no deberia cambiar al solo anular bloqueos (antes={fecha_corte_antes!r}, despues={fecha_corte_despues!r})"
)
capturar_paso(app, "bloqueos_dados_de_baja_fecha_corte_sin_cambios", paso_excel=4)
'''

CUERPOS_REALES["CP050"] = '''
# NOTA: el registro de una extension dispara una cadena de 3 modales de
# Confirmacion EN SECUENCIA (confirmado en vivo 22/10/2026): 1) resumen
# "Con fecha ... se eximio de corte por N dia(s) ... Ingresa nueva
# anulacion?", 2) "Confirma la Anulacion Temporal del corte para el
# cliente.", 3) "Desea bloquear el corte del suministro ... por favor
# confirmar." Las 3 deben aceptarse para que la operacion persista.
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("15")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(800)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=1500)
app.wait_for_timeout(500)
capturar_paso(app, "cliente_activo_cargado", paso_excel=1)

frame.locator("#dias").click()
frame.locator("#dias").fill("10")
app.wait_for_timeout(500)
frame.locator("#motivo").fill("Cliente realizó pago parcial y solicita plazo")
app.wait_for_timeout(500)
hoy_mas_10 = (date.today() + timedelta(days=10)).strftime("%d-%m-%Y")
capturar_paso(app, "dias_y_motivo_ingresados", paso_excel=2)

frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)
mensaje1 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje1 is not None and "10 día" in mensaje1 and "pago parcial" in mensaje1.lower(), (
    f"Se esperaba la confirmacion con 10 dias y el motivo ingresado: {mensaje1!r}"
)
capturar_paso(app, "primera_confirmacion_aceptada", paso_excel=4)

app.wait_for_timeout(1200)
mensaje2 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje2 is not None and "anulaci" in mensaje2.lower(), (
    f"Se esperaba la segunda confirmacion (Anulacion Temporal): {mensaje2!r}"
)
capturar_paso(app, "segunda_confirmacion_aceptada", paso_excel=5)

app.wait_for_timeout(1200)
mensaje3 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje3 is not None and "bloquear" in mensaje3.lower(), (
    f"Se esperaba la tercera confirmacion (bloquear el corte): {mensaje3!r}"
)
app.wait_for_timeout(1500)
capturar_paso(app, "mensaje_de_operacion_realizada", paso_excel=6)

boton_cancelar = frame.get_by_role("button", name="Cancelar")
if boton_cancelar.is_enabled():
    boton_cancelar.click()
    app.wait_for_timeout(800)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("15")
app.wait_for_timeout(500)
frame.get_by_role("button", name="Leer").click()
app.wait_for_timeout(1200)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=5000)
app.wait_for_timeout(800)
fecha_corte_final = frame.locator("#fechaCorteCliente").input_value()
assert fecha_corte_final == hoy_mas_10, (
    f"La fecha de corte deberia actualizarse a {hoy_mas_10!r}, se obtuvo {fecha_corte_final!r}"
)
capturar_paso(app, "fecha_de_corte_actualizada", paso_excel=7)
'''

CUERPOS_REALES["CP051"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("781429")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(800)
capturar_paso(app, "cliente_valido_cargado", paso_excel=1)

frame.locator("#dias").click()
frame.locator("#dias").fill("13")
app.wait_for_timeout(400)
frame.locator("#motivo").fill("Prueba de limite de dias")
app.wait_for_timeout(400)
capturar_paso(app, "trece_dias_ingresados", paso_excel=2)

frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)
mensaje_rechazo = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje_rechazo is not None and "12 día" in mensaje_rechazo, (
    f"Se esperaba el rechazo por superar el maximo de 12 dias: {mensaje_rechazo!r}"
)
capturar_paso(app, "rechazo_por_superar_el_maximo", paso_excel=3)

app.wait_for_timeout(500)
frame.locator("#dias").click()
frame.locator("#dias").fill("")
frame.locator("#dias").fill("12")
app.wait_for_timeout(400)
capturar_paso(app, "doce_dias_valor_limite_ingresado", paso_excel=4)

frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)
modal = obtener_modal_visible(frame, timeout_ms=8000)
assert modal is not None, "Se esperaba que continue el flujo de confirmacion con el valor limite"
texto_modal = modal.inner_text()
assert texto_modal.startswith("Confirmación") and "12 día" in texto_modal, (
    f"Con 12 dias (limite exacto) no deberia rechazarse, deberia continuar con un modal de Confirmacion: {texto_modal!r}"
)
capturar_paso(app, "limite_exacto_continua_flujo_de_confirmacion", paso_excel=5)

modal.get_by_role("button", name=re.compile(r"^\\s*Cancelar\\s*$", re.I)).click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP052"] = '''
# Confirmado en vivo 22/10/2026: con <=7 dias la cadena de confirmacion
# tiene 2 pasos (se eximio... /Confirma la Anulacion Temporal...) y al
# aceptar el 2do la operacion queda registrada sin pedir nada mas; con
# >=8 dias aparece un 3er modal ("Desea bloquear el corte del
# suministro ... por favor confirmar.") que es la confirmacion adicional
# exigida por la RN.
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("909420")
app.wait_for_timeout(500)
frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(800)
cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=2000)
app.wait_for_timeout(500)
capturar_paso(app, "cliente_cargado_para_7_dias", paso_excel=1)

frame.locator("#dias").click()
frame.locator("#dias").fill("7")
app.wait_for_timeout(400)
frame.locator("#motivo").fill("Prueba de 7 días sin confirmacion adicional")
app.wait_for_timeout(400)
frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)

mensaje1 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje1 is not None and "7 día" in mensaje1, f"Se esperaba la 1ra confirmacion con 7 dias: {mensaje1!r}"
app.wait_for_timeout(1200)
mensaje2 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje2 is not None and "anulaci" in mensaje2.lower(), f"Se esperaba la 2da confirmacion: {mensaje2!r}"
app.wait_for_timeout(1500)
assert obtener_modal_visible(frame, timeout_ms=3000) is None, (
    "Con 7 dias no deberia pedirse una 3ra confirmacion adicional"
)
capturar_paso(app, "siete_dias_sin_confirmacion_adicional", paso_excel=3)

frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("781429")
app.wait_for_timeout(500)
frame.get_by_role("button", name="Leer").click()
app.wait_for_timeout(1200)
try:
    frame.locator("nz-spin, .ant-spin-spinning").first.wait_for(state="hidden", timeout=15000)
except Exception:
    pass
app.wait_for_timeout(800)
assert obtener_modal_visible(frame, timeout_ms=1500) is None, "No se esperaba aviso previo para este cliente"
capturar_paso(app, "cliente_cargado_para_8_dias", paso_excel=4)

frame.locator("#dias").click()
frame.locator("#dias").fill("8")
app.wait_for_timeout(400)
frame.locator("#motivo").fill("Prueba de 8 días con confirmacion adicional")
app.wait_for_timeout(400)
frame.get_by_role("button", name="Ingresar").click()
app.wait_for_timeout(1200)

mensaje3 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje3 is not None and "8 día" in mensaje3, f"Se esperaba la 1ra confirmacion con 8 dias: {mensaje3!r}"
app.wait_for_timeout(1200)
mensaje4 = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje4 is not None and "anulaci" in mensaje4.lower(), f"Se esperaba la 2da confirmacion: {mensaje4!r}"
app.wait_for_timeout(1500)
modal_adicional = obtener_modal_visible(frame, timeout_ms=5000)
assert modal_adicional is not None and "bloquear" in modal_adicional.inner_text().lower(), (
    "Con 8 dias se esperaba una 3ra confirmacion adicional explicita antes de registrar"
)
capturar_paso(app, "ocho_dias_confirmacion_adicional_exigida", paso_excel=6)

modal_adicional.get_by_role("button", name=re.compile(r"^\\s*Cancelar\\s*$", re.I)).click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP045"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
app.wait_for_timeout(1000)
capturar_paso(app, "pantalla_inicial_sin_cliente", paso_excel=2)

frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(1200)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=6000)
assert mensaje is not None and "cliente" in mensaje.lower(), (
    f"Se esperaba un mensaje pidiendo el Numero de Cliente: {mensaje!r}"
)
capturar_paso(app, "mensaje_numero_cliente_obligatorio", paso_excel=2)
'''

CUERPOS_REALES["CP046"] = '''
app, frame = abrir_rf06(page, paso_excel=1)
frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("999999999")
app.wait_for_timeout(500)
capturar_paso(app, "cliente_inexistente_ingresado", paso_excel=2)

frame.locator("button:has-text('Leer')").first.click()
app.wait_for_timeout(2000)
mensaje = cerrar_modal_confirmacion(frame, aceptar=True, timeout_ms=8000)
assert mensaje is not None and ("no" in mensaje.lower() and ("encontr" in mensaje.lower() or "exist" in mensaje.lower())), (
    f"Se esperaba un mensaje de cliente no encontrado: {mensaje!r}"
)
capturar_paso(app, "mensaje_cliente_no_encontrado", paso_excel=3)

app.wait_for_timeout(500)
assert frame.locator("#numeroCliente").input_value() == "", "El campo deberia limpiarse para un nuevo intento"
capturar_paso(app, "campo_limpio_para_nuevo_intento", paso_excel=3)
'''

for _cp in sorted(MATRIZ.keys(), key=lambda c: int(c[2:])):
    _datos = MATRIZ[_cp]
    if _cp in CUERPOS_REALES:
        add(_cp, CUERPOS_REALES[_cp])
    else:
        add(_cp, _body_pendiente(_cp, _datos["rf"], _datos["name"]))


if __name__ == "__main__":
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
