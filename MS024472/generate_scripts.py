"""
generate_scripts.py de MS024472 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: "Migración Consulta Clientes" - pantalla "Información General"
dentro de "Atención Integral" (app AtencionCliente.ConsClie.InfoGeneral.Web),
rol funcional CONSCLIE. 2 casos en la matriz (CP001 consulta, CP002 PDF).

Exploracion en vivo (31/10/2026, cuenta SCASTI_DW, cliente de prueba 15 =
"TOWER AND TOWER S.A.", test1_cv@luzdelsur.com.pe):

Ruta de menu real (NO coincide con el texto corto del EF "Atención
Integral" solo - son 4 niveles, confirmados uno por uno tras varios
intentos fallidos con rutas mas cortas):
    Comercial > Atención Integral Al Cliente > Consulta De Clientes > Atención Integral
El ultimo click abre un POPUP (Principal/NuevaPestana) con un iframe
#aplicacion adentro - mismo patron que el resto del proyecto.

HALLAZGO REAL (typo de la propia app, no de esta automatizacion): el
item de menu dice **"Informacíon General"** (acento en la í) en vez de
"Información General" (acento en la ó, la forma correcta) - confirmado
visualmente y en el DOM. Selector de texto adaptado a como esta
ESCRITO REALMENTE, no a como deberia estar.

La pantalla "Atención Integral" es LEGACY (jQuery/Bootstrap, sin
componentes Angular con tag propio) - selectores reales por id
(#cliente, #txtTotalDeuda, etc.), no hay nz-select/nz-table. Buscar un
cliente (#cliente + boton "Buscar") carga el resumen general; clickear
"Informacíon General" en el sidebar izquierdo cambia el contenido
PRINCIPAL del MISMO iframe a la pantalla de 5 pestañas (Deuda, General,
Reparto y Lectura, Cambios de Ruta y Tarifa, Indicador de Riesgo) -
dispara una llamada async real (el texto "Cargando..." aparece y
desaparece solo, no es instantaneo como en la pagina de prueba local de
la Etapa 4).

IDs reales confirmados de la pestaña Deuda (todos con el formato de 2
decimales que exige el EF): txtAntiguedad, txtMesCerrados, txtImporte,
txtConsPromMes, txtUltConsumo, txtConsPromDia, txtUltPago, txtOficina,
txtUltiRefac, txtTipoRefac, txtFechaCorteCliente, txtRolDeuda, txtDesde,
txtHasta, txtMotivo, txtTotalDeuda (el campo clave, "DEUDA TOTAL"),
txtDeudaConvenio. Los campos de la pestaña General (txtRuc,
txtEstadoCliente, etc.) YA estan poblados en el DOM aunque no se haya
clickeado esa pestaña - los datos de las 5 pestañas cargan juntos.

"Descargar PDF" dispara una descarga real (evento `download` de
Playwright, no un dialogo nativo) - confirmado con un PDF real valido
(magic bytes %PDF-1.5, 92KB) nombrado "InformacionGeneral_<cliente>.pdf".
"""
import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = OUT_DIR.parent / "_framework"
sys.path.insert(0, str(FRAMEWORK_DIR))
import web_lds_core as core  # noqa: E402

PROYECTO = "MS024472"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


NAV_HELPERS = '''
def abrir_atencion_integral(page, paso_excel=None):
    return abrir_aplicacion(
        page,
        ["Comercial", "Atención Integral Al Cliente", "Consulta De Clientes", "Atención Integral"],
        "#cliente",
        paso_excel=paso_excel,
    )


def entrar_informacion_general(frame, app, timeout_ms=20000):
    """Clickea el item del sidebar (OJO: la app tiene un typo real,
    dice 'Informacíon General' con acento en la i, no 'Información
    General') y espera a que el 'Cargando...' que dispara la llamada
    async real desaparezca del todo, en vez de una espera fija."""
    frame.get_by_text("Informacíon General", exact=False).first.click()
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        if "Cargando" not in frame.locator("body").inner_text():
            return
        app.wait_for_timeout(500)
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
        opciones_contexto = {{"viewport": {{"width": 1700, "height": 1100}}, "accept_downloads": True}}
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


# La matriz de este proyecto no trae columna "CU" (a diferencia de otros
# proyectos) - CU-01/CU-02 se toman del cruce con el EF (Etapa 2:
# CU-01 Consulta de Informacion General del Suministro, CU-02
# Generacion de Reporte PDF).
_CU_POR_CP = {"CP001": "CU-01", "CP002": "CU-02"}


def add(cp, body, usuario="SCASTI_DW", password="Melquisedec_01"):
    m = MATRIZ[cp]
    CASES.append(dict(
        cp=cp, rf=m["rf"], cu=m.get("cu", _CU_POR_CP.get(cp, "-")), name=m["name"], desc=m["desc"],
        precond=m["precond"], datos=m["datos"], esperado=m["esperado"],
        pasos=m["pasos"], body=body, usuario=usuario, password=password,
    ))


CUERPOS_REALES = {}

CUERPOS_REALES["CP001"] = '''
app, frame = abrir_atencion_integral(page, paso_excel=2)

frame.locator("#cliente").click()
frame.locator("#cliente").fill("15")
capturar_paso(app, "cliente_ingresado", paso_excel=3)

frame.get_by_role("button", name="Buscar").click()
app.wait_for_timeout(3000)
nombre_cliente = frame.locator("#nombreCliente").input_value()
assert "TOWER" in nombre_cliente.upper(), f"Se esperaba el cliente TOWER AND TOWER S.A.: {nombre_cliente!r}"
capturar_paso(app, "atencion_integral_cargada", paso_excel=3)

entrar_informacion_general(frame, app)
capturar_paso(app, "informacion_general_cargada", paso_excel=4)

texto_pantalla = frame.locator("body").inner_text()
for pestana in ("Deuda", "General", "Reparto y Lectura", "Cambios de Ruta y Tarifa", "Indicador de Riesgo"):
    assert pestana in texto_pantalla, f"Se esperaba ver la pestana {pestana!r} en Informacion General: {texto_pantalla[:200]!r}"

# Regla del EF (12.1 RF-1): los campos numericos deben respetar el
# formato de 2 decimales y punto decimal.
patron_decimal = re.compile(r"^\\d+\\.\\d{2}$")
campos_numericos = ["txtImporte", "txtConsPromMes", "txtUltConsumo", "txtConsPromDia", "txtUltPago", "txtUltiRefac", "txtTotalDeuda", "txtDeudaConvenio"]
for campo_id in campos_numericos:
    valor = frame.locator(f"#{campo_id}").input_value()
    assert patron_decimal.match(valor), f"Campo #{campo_id} no tiene formato de 2 decimales: {valor!r}"

valor_deuda_total = frame.locator("#txtTotalDeuda").input_value()
assert valor_deuda_total, "Se esperaba un valor en DEUDA TOTAL"
capturar_paso(app, "datos_de_informacion_general_verificados", paso_excel=5)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_atencion_integral(page, paso_excel=2)

frame.locator("#cliente").click()
frame.locator("#cliente").fill("15")
frame.get_by_role("button", name="Buscar").click()
app.wait_for_timeout(3000)
capturar_paso(app, "cliente_consultado", paso_excel=3)

entrar_informacion_general(frame, app)
capturar_paso(app, "informacion_general_antes_de_descargar", paso_excel=5)

with app.expect_download(timeout=30000) as download_info:
    frame.get_by_role("button", name="Descargar PDF").click()
download = download_info.value
destino_pdf = EVIDENCIA / f"{CASO}_reporte.pdf"
download.save_as(str(destino_pdf))
capturar_paso(app, "pdf_descargado", paso_excel=6)

assert destino_pdf.is_file(), "El PDF no se genero/descargo"
contenido_pdf = destino_pdf.read_bytes()
assert contenido_pdf[:4] == b"%PDF", f"El archivo descargado no es un PDF valido (primeros bytes: {contenido_pdf[:8]!r})"
assert len(contenido_pdf) > 1000, f"El PDF parece sospechosamente chico ({len(contenido_pdf)} bytes) para contener info real"
'''

for _cp in sorted(MATRIZ.keys(), key=lambda c: int(c[2:])):
    _datos = MATRIZ[_cp]
    if _cp in CUERPOS_REALES:
        add(_cp, CUERPOS_REALES[_cp])

if __name__ == "__main__":
    if not CASES:
        raise SystemExit("CASES vacio - no hay nada que generar.")
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
