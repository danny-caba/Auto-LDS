"""
generate_scripts.py de IP016521 - FUENTE DE VERDAD que genera los CPxxx.py.

Requerimiento: IP016521 (AV023854) - Validacion de periodo en la
Autorizacion Manual de Comprobantes/Planillas de Transporte. 1 RF, 2
casos (ver matriz_casos.json). Ver documentos/EF_texto.txt y
documentos/ET_texto.txt para el detalle funcional/tecnico completo.

Exploracion en vivo (27/10/2026, cuenta DCABA_DW) confirmo:
  Ruta de menu real: Administrativo > Transportes > Planillas De
  Transportes > Autorizador Comprobantes Transporte (NO bajo Comercial
  como el resto de proyectos de este framework hasta ahora).

  A diferencia de TODOS los proyectos anteriores (ant-design/ng-zorro,
  Angular), esta es una pantalla CLASICA (jQuery + DataTables + Select2
  + bootbox, ASP.NET MVC server-rendered) - "Comprobantes Contables
  Transporte". No hay componente Angular raiz; se usa #btnBuscarComprobantes
  como selector_pantalla para confirmar que cargo.

  Selectores reales confirmados:
  - Filtros: #codDocumento, #placa, #fecha (date), #Estado (select:
    S=Activo/A=Autorizado/R=Rechazado/L=Liquidado), #cr, #tipoVehiculo,
    #turno, #tipoServicio, #periodo (select - SOLO trae los periodos
    ABIERTOS reales, confirmado en vivo con una sola opcion "202607" el
    27/10/2026).
  - Botones (icon-only, sin texto visible - usar el atributo title):
    #btnBuscarComprobantes (title="Buscar"), #btnLimpiarComprobantes,
    #btnDescargarResultados, #aprobarComprobantes (title="Autorizar"),
    #rechazarComprobantes (title="Rechazar").
  - Grilla real: tabla #tblComprobantes (DataTables), checkbox por fila
    (primera celda), columnas [checkbox, Cod. Documento, Estado, Placa,
    Tipo Vehiculo, CR, Fecha, Turno, Km, ValKm, Duracion HN, Total HN,
    Duracion HE, Total HE, Peaje, Total Final, Codigo SAP, Imputacion].
    Info de paginado real: #tblComprobantes_info ("Mostrando del X al Y
    de Z registros").
  - Confirmacion real al Autorizar: modal bootbox (clase ".bootbox", NO
    ".ant-modal"/"nz-modal-container" como en proyectos anteriores) con
    botones ".bootbox-cancel" (Salir) y ".bootbox-accept" (Aceptar) -
    titulo "Autorizar Comprobantes", cuerpo "Se va a autorizar todos los
    comprobantes marcados / ¿Desea Continuar?". Tras Aceptar, un SEGUNDO
    modal bootbox (mismo titulo) muestra el resultado real.

  CP01 (bloqueo) CONFIRMADO EN VIVO con datos reales: el unico periodo
  abierto es "202607", pero los 4 comprobantes reales en estado ACTIVO
  (E304389/E304384/E304361/E304333) son todos del 06-10-2026 (periodo
  real 202610) - mensaje real obtenido, coincide EXACTO con el EF:
  "El período de autorización 202607 no corresponde a los códigos de
  documentos seleccionados: E304389. Revise su selección."

  CP02 (caso positivo) CONFIRMADO EN VIVO 27/10/2026: los 4 comprobantes
  "por defecto" (sin filtro de fecha) son todos de octubre, pero una
  busqueda con Fecha Desde=01/06/2026 (backend tarda 6s+ en responder,
  ver gotcha de timing en buscar_comprobantes()) trae 124 comprobantes
  reales ACTIVOS de junio/julio 2026 - encontrados via el export real
  "MigradorTrnsporteSAP.xlsx" en Documentos/ (busqueda hecha a mano por
  el usuario). E294667 (10/07/2026) se autorizo de verdad en la
  exploracion (quedo AUTORIZADO, Codigo SAP 3800022564 asignado,
  mensaje real: "Se ejecuto la accion de autorizar. Verificar en el
  Excel de resultados." - a pesar de sonar generico, ES el mensaje de
  EXITO). E294552 se consumio en un intento posterior fallido (bug de
  automatizacion, ya corregido - ver Limpiar en autorizar_marcados). El
  cuerpo final usa E294268 (07/07/2026, mismo vehiculo CNK542), sin
  consumir al cierre de esta sesion.
"""
import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = OUT_DIR.parent / "_framework"
sys.path.insert(0, str(FRAMEWORK_DIR))
import web_lds_core as core  # noqa: E402

PROYECTO = "IP016521"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


# --- Helpers de navegacion y de la pantalla, propios de este proyecto ---
NAV_HELPERS = '''
def abrir_autorizador(page, paso_excel=None):
    return abrir_aplicacion(
        page,
        ["Administrativo", "Transportes", "Planillas De Transportes", "Autorizador Comprobantes Transporte"],
        "#btnBuscarComprobantes",
        paso_excel=paso_excel,
    )


def buscar_comprobantes(app, frame, fecha_desde=None, timeout_s=20):
    """Click en Buscar y espera a que el DataTable termine de cargar -
    CONFIRMADO EN VIVO 27/10/2026: con un filtro de Fecha Desde amplio
    (ej. 2026-06-01, trae 120+ registros) el backend tarda 6s o mas en
    responder - el patron "Se encontraron 0 registros" aparece como
    estado INTERMEDIO mientras carga, no como resultado real; hay que
    sondear #tblComprobantes_info hasta que cambie, no leerlo una sola
    vez con una pausa fija corta."""
    if fecha_desde is not None:
        frame.locator("#fecha").fill(fecha_desde)
        app.wait_for_timeout(300)
    frame.locator("#btnBuscarComprobantes").click()
    info = frame.locator("#tblComprobantes_info")
    for _ in range(timeout_s // 2):
        app.wait_for_timeout(2000)
        texto = info.inner_text()
        if "registros" in texto and not texto.startswith("Se encontraron 0") and "0 al 0" not in texto:
            return texto
    return info.inner_text()


def marcar_comprobante(frame, codigo):
    """Marca el checkbox de la fila cuyo Cod. Documento coincide EXACTO
    (no substring - varios codigos comparten prefijo, ej. E304389 vs
    E3043890)."""
    filas = frame.locator("#tblComprobantes tbody tr")
    for i in range(filas.count()):
        fila = filas.nth(i)
        if fila.locator("td").nth(1).inner_text().strip() == codigo:
            fila.locator("input[type=checkbox]").check()
            return fila
    raise AssertionError(f"No se encontro el comprobante {{codigo!r}} en la grilla")


def autorizar_marcados(app, frame):
    """Click en Autorizar + confirmar el primer dialogo bootbox
    ("¿Desea Continuar?") y devuelve el texto del dialogo de RESULTADO
    (exito o el mensaje de bloqueo de periodo). CONFIRMADO EN VIVO
    27/10/2026: bootbox.js reusa el MISMO contenedor ".bootbox" para la
    confirmacion Y el resultado (reemplaza el contenido en vez de abrir
    un segundo modal) - el boton de cerrar en AMBOS casos comparte la
    MISMA clase ".bootbox-accept" (solo cambia el texto: "Aceptar" vs
    "Cerrar"). Hay que esperar a que el modal realmente desaparezca del
    DOM tras cerrarlo, o el siguiente click en la pantalla de fondo
    queda bloqueado ("intercepts pointer events")."""
    frame.locator("#aprobarComprobantes").click()
    app.wait_for_timeout(1200)
    modal = frame.locator(".bootbox")
    modal.first.wait_for(state="visible", timeout=8000)
    modal.locator(".bootbox-accept").click()
    app.wait_for_timeout(2000)
    modal.first.wait_for(state="visible", timeout=8000)
    texto = modal.first.inner_text()
    modal.locator(".bootbox-accept").click()
    modal.first.wait_for(state="hidden", timeout=8000)
    app.wait_for_timeout(500)
    return texto
'''

HEADER_TEMPLATE = '''"""
{docstring}
"""
import os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

''' + ENV_TOGGLES + '''

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "DCABA_DW"
PASSWORD = "Melquisedec_01"

CASO = "{cp}"
EVIDENCIA = Path(__file__).resolve().parent / CASO
if EVIDENCIA.exists():
    shutil.rmtree(EVIDENCIA, ignore_errors=True)
EVIDENCIA.mkdir(parents=True, exist_ok=True)

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

''' + NAV_HELPERS.strip("\n") + '''

%%WORD_HELPERS%%


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=HEADLESS, slow_mo=SLOWMO)
        opciones_contexto = {{"viewport": {{"width": 1600, "height": 900}}}}
        if GRABAR_VIDEO:
            opciones_contexto["record_video_dir"] = str(EVIDENCIA)
            opciones_contexto["record_video_size"] = {{"width": 1600, "height": 900}}
        context = browser.new_context(**opciones_contexto)
        if GRABAR_VIDEO:
            context.add_init_script(%%CURSOR_OVERLAY_JS%%)
        page = context.new_page()
        app = None
        _CASO_OK = False
        try:
            login(page, paso_excel=1)
            app, frame = abrir_autorizador(page, paso_excel=2)

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
            if _CASO_OK:
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


def _indentar(body: str, espacios: int = 12) -> str:
    prefijo = " " * espacios
    return "\n".join((prefijo + linea if linea.strip() else "") for linea in body.strip("\n").split("\n"))


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
        body=body,
    ).replace("%%CAPTURAR_PASO%%", core.CAPTURAR_PASO_CODE) \
     .replace("%%LOGIN%%", core.LOGIN_BLOCK) \
     .replace("%%NAV%%", core.CLICK_VISIBLE_BLOCK + "\n\n\n" + core.ABRIR_APLICACION_BLOCK) \
     .replace("%%HELPERS_ESPERA%%", core.ESPERAR_FIN_CARGA_BLOCK + "\n\n\n" + core.ESPERAR_ANIMACION_BLOCK + "\n\n\n" + core.SELECCIONAR_PRIMERA_OPCION_BLOCK + "\n\n\n" + core.SELECCIONAR_OPCION_POR_TEXTO_BLOCK) \
     .replace("%%VIDEO_HELPERS%%", core.RENOMBRAR_VIDEO_BLOCK) \
     .replace("%%CURSOR_OVERLAY_JS%%", repr(core.CURSOR_JS_FULL.strip("\n"))) \
     .replace("%%WORD_HELPERS%%", core.WORD_HELPERS_FULL.strip("\n"))


CUERPOS_REALES = {}

# CP01: CONFIRMADO EN VIVO 27/10/2026. Comprobante real E304389 (06/10/2026,
# periodo real 202610) marcado con el unico periodo abierto (202607) ->
# bloqueo real, mensaje EXACTO del EF.
CUERPOS_REALES["CP01"] = '''
buscar_comprobantes(app, frame)
capturar_paso(app, "grilla_cargada", paso_excel=3)

periodo_actual = frame.locator("#periodo").input_value()
capturar_paso(app, "periodo_de_autorizacion", paso_excel=4)

fila = marcar_comprobante(frame, "E304389")
capturar_paso(app, "comprobante_marcado", paso_excel=4)

mensaje = autorizar_marcados(app, frame)
capturar_paso(app, "mensaje_bloqueo_periodo", paso_excel=6)
assert "no corresponde a los c" in mensaje.lower() and "E304389" in mensaje, (
    f"Se esperaba el mensaje de bloqueo por periodo no correspondiente: {mensaje!r}"
)
assert periodo_actual in mensaje, f"Se esperaba ver el periodo {periodo_actual!r} citado en el mensaje: {mensaje!r}"

# Confirmar que NO se autorizo: la fila sigue ACTIVO tras recargar.
buscar_comprobantes(app, frame)
fila_tras = frame.locator("#tblComprobantes tbody tr").filter(has_text="E304389")
assert fila_tras.count() == 1 and "ACTIVO" in fila_tras.first.inner_text(), (
    "El comprobante no deberia haberse autorizado (deberia seguir ACTIVO)"
)
'''

# CP02: CONFIRMADO EN VIVO 27/10/2026. El comprobante real E294667
# (10/07/2026, periodo 202607, directo - no necesito la regla de "mes
# siguiente") se autorizo de verdad: paso a estado AUTORIZADO con Codigo
# SAP asignado (3800022564) - "Se ejecuto la accion de autorizar.
# Verificar en el Excel de resultados." es el mensaje real de EXITO
# (no es un error, pese a sonar generico). Para el caso automatizado
# (repetible) se usa E294268 (07/07/2026, mismo vehiculo CNK542),
# todavia sin consumir a esa fecha - encontrado en el export
# "MigradorTrnsporteSAP.xlsx" (busqueda real con Fecha Desde=01/06/2026,
# 124 comprobantes activos reales, julio/junio 2026).
CUERPOS_REALES["CP02"] = '''
info = buscar_comprobantes(app, frame, fecha_desde="2026-06-01")
capturar_paso(app, "grilla_cargada_desde_junio", paso_excel=3)
assert "registros" in info and not info.lower().startswith("se encontraron 0"), (
    f"Se esperaba encontrar comprobantes activos desde 01/06/2026: {info!r}"
)

periodo_actual = frame.locator("#periodo").input_value()
capturar_paso(app, "periodo_de_autorizacion", paso_excel=4)

fila = marcar_comprobante(frame, "E294268")
capturar_paso(app, "comprobante_marcado", paso_excel=4)

mensaje = autorizar_marcados(app, frame)
capturar_paso(app, "mensaje_resultado", paso_excel=6)
assert "no corresponde" not in mensaje.lower() and "no se pudieron" not in mensaje.lower(), (
    f"No se esperaba un mensaje de bloqueo/error para un periodo valido: {mensaje!r}"
)
assert "autoriz" in mensaje.lower(), f"Se esperaba un mensaje confirmando la autorizacion: {mensaje!r}"

# Confirmar que SI quedo autorizado: buscar de nuevo con Estado=AUTORIZADO.
# CONFIRMADO EN VIVO 27/10/2026: los campos de filtro quedan
# deshabilitados tras la operacion de Autorizar - hay que pulsar
# Limpiar primero para poder volver a filtrar en la misma sesion.
frame.locator("#btnLimpiarComprobantes").click()
app.wait_for_timeout(1000)
frame.locator("#codDocumento").fill("E294268")
frame.locator("#Estado").select_option(value="A")
info2 = buscar_comprobantes(app, frame, fecha_desde="2026-06-01")
capturar_paso(app, "comprobante_queda_autorizado", paso_excel=6)
assert "1 al 1" in info2 or "registros" in info2, f"Se esperaba encontrar el comprobante ya autorizado: {info2!r}"
fila_final = frame.locator("#tblComprobantes tbody tr").first
assert "AUTORIZADO" in fila_final.inner_text(), (
    f"El comprobante deberia figurar como AUTORIZADO tras la operacion: {fila_final.inner_text()!r}"
)
'''


CASES = []


def add(cp, body):
    m = MATRIZ[cp]
    CASES.append(dict(
        cp=cp, rf=m["rf"], cu=m["cu"], name=m["name"], desc=m["desc"],
        precond=m["precond"], datos=m["datos"], esperado=m["esperado"],
        pasos=m["pasos"], body=body,
    ))


_BODY_PENDIENTE = '''
raise NotImplementedError({msg!r})
'''

for _cp in sorted(MATRIZ, key=lambda x: int(x[2:])):
    _m = MATRIZ[_cp]
    _cuerpo = CUERPOS_REALES.get(_cp)
    if _cuerpo is None:
        _cuerpo = _BODY_PENDIENTE.format(
            msg=f"{_cp} ({_m['rf']} - {_m['name']}): falta un comprobante real con periodo que coincida "
                f"con el unico periodo abierto actual - ningun comprobante ACTIVO existente califica "
                f"(los 4 disponibles al 27/10/2026 son todos de octubre/202610, el unico periodo abierto "
                f"es 202607). Pedir al usuario un comprobante valido o esperar a que se abra un periodo "
                f"que coincida con datos reales existentes."
        )
    add(_cp, _cuerpo)


if __name__ == "__main__":
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
