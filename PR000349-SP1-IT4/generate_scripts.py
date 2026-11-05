"""
generate_scripts.py de PR000349-SP1 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: migracion de 4 frentes de negocio comercial (Retiro y Castigo de
Clientes, Cuadratura de Saldos, Convenios de Pago, Aprobacion de Informes
del Datawarehouse), 12 pantallas / RF-01..RF-12, 74 casos (ver
matriz_casos.json). Ver documentos/EF_texto.txt y documentos/ET_texto.txt
para el detalle funcional/tecnico completo de cada RF.

Estado (25/09/2026): infraestructura de generacion COMPLETA (HEADER_TEMPLATE,
render(), un add() por cada uno de los 74 CP con rf/cu/name/desc/precond/
datos/esperado ya poblados desde matriz_casos.json) Y las 12 pantallas ya
CONFIRMADAS EN VIVO (login + navegacion + apertura de cada una, ver tabla
abajo). Los `body` de cada caso quedan en NotImplementedError a proposito:
el cuerpo real (selectores de CAMPOS/BOTONES puntuales, asserts, datos de
prueba reales) todavia NO es automatizable a ciegas - falta explorar cada
pantalla en detalle (Paso 2, segunda mitad) antes de escribirlos. Ver
PENDIENTES mas abajo.

**Navegacion CONFIRMADA en vivo el 25/09/2026** (usuario SCASTI_DW, rol
LUZGENACT ya asignado - mismo usuario reusado de PR000326-SP2, ver memoria
`feedback_cuenta_prueba_scasti_dw`): las 12 apps se abren TODAS desde el
MISMO portal Web LDS (`https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb`,
igual que PR000325/PR000335/PR000326), ruta de menu `Aplicaciones >
Comercial > <nombre exacto de la tabla de abajo>` (un solo nivel bajo
Comercial, sin sub-submenu) - NO se navega directo a las URIs propias del
ET (esas son internas del microservicio, ver `abrir_aplicacion()` en
`web_lds_core.py`). Las 12 abren su popup con iframe `#aplicacion` normal.
Confirmado tambien que el usuario/ambiente actual pega contra el backend de
**Pruebas** (`tk0s-web.luzdelsur.com.pe`, ver columna "backend confirmado"),
tal como se decidio usar para este proyecto (ver PENDIENTES).

| RF    | Texto EXACTO del menu (bajo "Comercial")              | Componente Angular raiz         | Backend confirmado (Pruebas) |
|-------|--------------------------------------------------------|----------------------------------|-------------------------------|
| RF-01 | Traslado De Clientes                                    | app-traslado-clientes            | .../gesclie/retirocastigo/trasladoclientes/web |
| RF-02 | Mantenimiento De Carteras                                | app-carteras                     | .../gesclie/retirocastigo/carteras/web |
| RF-03 | Asignacion De Clientes A Carteras                        | app-asignacion-carteras          | .../gesclie/retirocastigo/asignacioncarteras/web |
| RF-04 | Investigacion De Clientes                                | app-clientes-investigar          | .../gesclie/retirocastigo/clientesinvestigar/web |
| RF-05 | Emisión De Cartas Masivas                                | app-cartas-masivas (+ app-validacion-modal) | .../gesclie/retirocastigo/cartasmasivas/web |
| RF-06 | Anulacion De Facturas                                    | app-anulamiento-factura          | .../gesclie/retirocastigo/anulamientofactura/web |
| RF-07 | Consulta De Movimientos De Saldos                        | app-consulta-movimientos         | .../gessaldo/gessaldo/cuadrasaldo/web |
| RF-08 | Listados De Facilidades De Pago Por Deuda De Energía     | app-listado-convenios-deuda      | .../recauda/facilidadpago/listconvenergia/web |
| RF-09 | Listados De Ingresos De Cnr Por Deuda De Servicios       | app-listado-facilidades-no-deuda | .../recauda/facilidadpago/listconvservicio/web |
| RF-10 | Aprobación De Informes Dwh                               | app-aprobacion-informes          | .../Dwh/Dwh/Aprobacion/web |
| RF-11 | Mantenimiento De Informes Dwh                            | app-mantenimiento-informes       | .../Dwh/Dwh/Mantenimiento/web |
| RF-12 | Log De Carga De Datawarehouse                            | app-log-carga                    | .../Dwh/Dwh/LogCarga/web |

OJO: el texto de menu real NO siempre coincide con el nombre del RF en el
EF (gotcha ya documentado en NUEVO_PROYECTO_CHECKLIST.md: "no confiar en el
EF a ciegas") - ej. RF-04 "Clientes a Investigar" en el EF es
"Investigacion De Clientes" en el menu real, RF-06 "Anulamiento de
Facturas" es "Anulacion De Facturas". Usar SIEMPRE el texto de la tabla de
arriba (confirmado en vivo), no el nombre del EF.

Evidencia de esta exploracion: `_exploracion/explore_02_estructura_menu.py`
(rutas de menu) y `_exploracion/explore_03_abrir_las_12_apps.py` (apertura +
componente raiz + llamadas backend), con su salida en `_exploracion/dump/`.

PENDIENTES antes de poder escribir un solo body real:
  1. Exploracion en vivo EN DETALLE de cada una de las 12 pantallas
     (selectores de campos/botones puntuales para los 74 casos) - lo de
     arriba solo confirma que la pantalla ABRE, no el detalle interno.
  2. Datos de prueba reales por caso (ej. un cliente en estado "Retirado"
     sin cartera para CP001, una Orden de Trabajo nueva para CP008,
     convenios/facilidades vigentes para RF-08/RF-09, un informe permitido
     para el usuario en RF-10/11/12, etc.) - no se puede adivinar, hay que
     confirmarlos en el ambiente de Pruebas real.

Completar siguiendo NUEVO_PROYECTO_CHECKLIST.md (Paso 3) una vez resuelto lo
de arriba: reemplazar el NotImplementedError de cada add(...) por el body
real, mirando la matriz (columnas desc/precond/datos/esperado/pasos, ya
disponibles como variables en cada caso) + la exploracion en vivo detallada,
usando las funciones abrir_traslado_clientes..abrir_log_carga_datawarehouse ya definidas mas abajo.
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
import traslado_clientes as modulo_rf01  # noqa: E402
import mantenimiento_carteras as modulo_rf02  # noqa: E402
import asignacion_clientes_carteras as modulo_rf03  # noqa: E402
import investigacion_clientes as modulo_rf04  # noqa: E402
import emision_cartas_masivas as modulo_rf05  # noqa: E402
import anulacion_facturas as modulo_rf06  # noqa: E402
import consulta_movimientos_saldos as modulo_rf07  # noqa: E402
import listado_facilidades_deuda_energia as modulo_rf08  # noqa: E402
import listado_ingresos_cnr_deuda_servicios as modulo_rf09  # noqa: E402
import aprobacion_informes_dwh as modulo_rf10  # noqa: E402
import mantenimiento_informes_dwh as modulo_rf11  # noqa: E402
import log_carga_datawarehouse as modulo_rf12  # noqa: E402

PROYECTO = "PR000349-SP1-IT4"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


def fuente_modulo(modulo, saltar=("PWTimeoutError",)):
    """Extrae el codigo fuente de un modulo de _framework/modulos/ (su
    docstring + todas sus funciones, en el orden en que estan escritas)
    para volcarlo como texto en el CPxxx.py generado. Ver
    _sandbox_modulos/RF06_piloto/generate_scripts.py (referencia original
    de esta funcion) y NUEVO_PROYECTO_CHECKLIST.md Seccion 0c. `saltar`
    son nombres importados por el modulo que ya vienen de otro lado en el
    header del CPxxx.py (ej. PWTimeoutError, ya cubierto por
    %%HELPERS_ESPERA%%/el import estandar de playwright) y no hace falta
    re-emitir."""
    codigo_completo = inspect.getsource(modulo)
    lineas = codigo_completo.split("\n")
    dentro_docstring = False
    doc_lineas = []
    i = 0
    if lineas[0].strip().startswith('"""'):
        dentro_docstring = True
        doc_lineas.append(lineas[0].strip().lstrip('"'))
        i = 1
    while dentro_docstring and i < len(lineas):
        if lineas[i].strip().endswith('"""'):
            doc_lineas.append(lineas[i].rstrip().rstrip('"'))
            dentro_docstring = False
            i += 1
            break
        doc_lineas.append(lineas[i])
        i += 1
    resto = lineas[i:]
    salida = [l for l in resto if not (l.startswith("import ") or l.startswith("from "))]
    ficha_tecnica = "\n".join(f"# {l}" if l.strip() else "#" for l in doc_lineas)
    fuente = ficha_tecnica + "\n\n\n" + "\n".join(salida).strip("\n")
    # HEADER_TEMPLATE completo pasa por .format() en render() - cualquier
    # llave literal del modulo (f-strings, dict/set literals) tiene que
    # venir DOBLADA para sobrevivir ese .format() como llave literal en el
    # CPxxx.py final (mismo patron ya usado en el resto de HEADER_TEMPLATE,
    # ej. opciones_contexto = {{"viewport": ...}}).
    return fuente.replace("{", "{{").replace("}", "}}")


# Helper generico consolidado (antes duplicado 3 veces entre RF-02/03/04,
# byte-a-byte identico en los 3 casos) - buscar un <button> por texto
# exacto. Candidato a subir a web_lds_core.py si se repite en futuros
# proyectos (ver Seccion 0c del checklist, "helpers genuinamente genericos").
HELPERS_GENERICOS = '''
def boton_por_texto(frame, texto):
    return frame.locator("button", has_text=re.compile(r"^\\s*" + re.escape(texto) + r"\\s*$"))


MESES_ABREV_NZ = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]


def seleccionar_fecha_calendario(app, frame, input_locator, dia, mes, anio):
    """Selecciona una fecha en un nz-date-picker (ant-design) haciendo CLIC
    en el calendario (anio -> mes -> dia), NUNCA tipeando el texto.
    CONFIRMADO EN VIVO 16/10/2026 (RF-09 CP050): fill() deja el input
    visualmente con el valor correcto (ng-pristine, confirma que Angular
    nunca se enteró), pero el FormControl real queda vacío - "Generar"
    sigue mostrando "No existen registros" pese a que el dato SI existe en
    la base, exactamente el mismo sintoma/causa ya confirmado en
    PR000349-SP7 CP042 (otro proyecto, mismo componente). Clickear la
    celda real del calendario SI actualiza el control. Patron reusable
    para cualquier nz-date-picker con el sintoma "no encuentra nada pese a
    que el dato existe" o "se borra solo al perder el foco"."""
    input_locator.click()
    app.wait_for_timeout(400)
    frame.locator(".ant-picker-header-year-btn").last.click()
    app.wait_for_timeout(400)
    for _ in range(25):
        celda_anio = frame.locator(f'.ant-picker-cell[title="{{anio}}"]').last
        if celda_anio.count():
            celda_anio.click()
            break
        primero = int(frame.locator(".ant-picker-cell").first.get_attribute("title"))
        if primero > anio:
            frame.locator(".ant-picker-header-super-prev-btn").last.click()
        else:
            frame.locator(".ant-picker-header-super-next-btn").last.click()
        app.wait_for_timeout(300)
    app.wait_for_timeout(400)
    frame.locator(".ant-picker-header-month-btn").last.click()
    app.wait_for_timeout(400)
    frame.locator(f'.ant-picker-cell[title="{{MESES_ABREV_NZ[mes - 1]}}"]').last.click()
    app.wait_for_timeout(400)
    objetivo = f"{{dia:02d}}/{{mes:02d}}/{{anio}}"
    frame.locator(f'.ant-picker-cell[title="{{objetivo}}"]').last.click()
    app.wait_for_timeout(300)


def paginador(frame, indice=0):
    """Componente generico <lds-paginador> (confirmado en vivo 26/10/2026,
    PR000349-SP1-IT4 CP075, RF-12 Log de Carga DWH) - barra "Mostrando X-Y
    de Z registros" + "Pagina N de M" + botones Primera/Anterior/
    Siguiente/Ultima (title exacto, NO por texto del icono) + input de
    texto "Registros por pagina" (NO es un <select>). Puede haber varias
    instancias en la misma pantalla (ej. 1 por grilla) - usar `indice`
    para elegir cual."""
    return frame.locator("lds-paginador").nth(indice)


def texto_paginador(frame, indice=0):
    p = paginador(frame, indice)
    return p.locator(".lds-pg__posicion").inner_text(), p.locator(".lds-pg__texto").inner_text()


def click_paginador(app, frame, titulo_regex, indice=0, timeout_ms=8000):
    """Clickea un boton del paginador por `title` (pasar un patron regex
    SIN tildes, ej. 'P.gina siguiente' - el title real del DOM SI tiene
    tildes, pero se evita escribirlas literal en el codigo fuente por
    convencion de este proyecto; el wildcard '.' las cubre) y espera
    activamente a que la posicion cambie - CONFIRMADO EN VIVO: leer el
    texto justo despues del click (sin esperar el cambio real) agarra el
    valor VIEJO, la actualizacion es asincrona."""
    p = paginador(frame, indice)
    posicion = p.locator(".lds-pg__posicion")
    anterior = posicion.inner_text()
    p.get_by_title(re.compile(titulo_regex, re.I)).click()
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        app.wait_for_timeout(250)
        actual = posicion.inner_text()
        if actual != anterior:
            return actual
    return posicion.inner_text()


def fijar_registros_por_pagina(app, frame, cantidad, indice=0, timeout_ms=8000):
    p = paginador(frame, indice)
    rango = p.locator(".lds-pg__texto")
    anterior = rango.inner_text()
    campo = p.locator("input.lds-pg__input")
    campo.fill(str(cantidad))
    campo.press("Enter")
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        app.wait_for_timeout(250)
        actual = rango.inner_text()
        if actual != anterior:
            return actual
    return rango.inner_text()
'''

HELPERS_MODULOS = "\n\n\n".join(
    fuente_modulo(m) for m in (
        modulo_rf01, modulo_rf02, modulo_rf03, modulo_rf04, modulo_rf05, modulo_rf06,
        modulo_rf07, modulo_rf08, modulo_rf09, modulo_rf10, modulo_rf11, modulo_rf12,
    )
)

HEADER_TEMPLATE = '''"""
{docstring}
"""
import os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

''' + ENV_TOGGLES + '''

# Ambiente Pruebas confirmado (decision del usuario, ver docstring) - el
# portal es el mismo para cualquier ambiente, la diferencia de Pruebas vs
# Produccion la resuelve el backend segun la sesion/usuario, no la URL.
URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "SCASTI_DW"      # cuenta de prueba reutilizable, rol LUZGENACT ya asignado
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

''' + HELPERS_GENERICOS.strip("\n") + '''


''' + HELPERS_MODULOS + '''


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
        body=body,
    ).replace("%%CAPTURAR_PASO%%", core.CAPTURAR_PASO_CODE) \
     .replace("%%LOGIN%%", core.LOGIN_BLOCK) \
     .replace("%%NAV%%", core.CLICK_VISIBLE_BLOCK + "\n\n\n" + core.ABRIR_APLICACION_BLOCK) \
     .replace("%%HELPERS_ESPERA%%", core.ESPERAR_FIN_CARGA_BLOCK + "\n\n\n" + core.ESPERAR_ANIMACION_BLOCK + "\n\n\n" + core.SELECCIONAR_PRIMERA_OPCION_BLOCK + "\n\n\n" + core.SELECCIONAR_OPCION_POR_TEXTO_BLOCK) \
     .replace("%%VIDEO_HELPERS%%", core.RENOMBRAR_VIDEO_BLOCK) \
     .replace("%%CURSOR_OVERLAY_JS%%", repr(core.CURSOR_JS_FULL.strip("\n"))) \
     .replace("%%WORD_HELPERS%%", core.WORD_HELPERS_FULL.strip("\n"))


CASES = []


def add(cp, body):
    m = MATRIZ[cp]
    CASES.append(dict(
        cp=cp, rf=m["rf"], cu=m["cu"], name=m["name"], desc=m["desc"],
        precond=m["precond"], datos=m["datos"], esperado=m["esperado"],
        pasos=m["pasos"], body=body,
    ))


_BODY_PENDIENTE = '''raise NotImplementedError(
    "{cp} ({rf} - {name}): falta escribir el body real - ver PENDIENTES en "
    "el docstring de generate_scripts.py (exploracion en vivo + credenciales "
    "pendientes)."
)'''

# --- RF-01 "Traslado de Clientes" (CP001-CP006) - bodies reales, escritos y
# verificados en vivo el 25/09/2026 (ver _exploracion/explore_04..09.py y
# dump/*.png/*.json). Datos de prueba: numeros de cliente reales confirmados
# via la propia API ValidarCliente (no via SQL - la BD Informix de este
# sistema legacy quedo enredada en sinonimos entre las bases 'clientes' y
# 'web' del mismo servidor, ver historial de esta sesion): 264252 (Retirado,
# estado=2), 264279/1583373 (Cobranza Externa CON cartera, "91.00"/"19.21"),
# 1764523 (estado=0, "activo", no elegible), 781409/781410/1830410
# (cualquier estado, solo para probar carga por lote/duplicado).
CUERPOS_REALES = {}

CUERPOS_REALES["CP001"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
seleccionar_tipo_traslado(frame, "RACE")
capturar_paso(app, "tipo_traslado_race", paso_excel=2)
# IT2 15/10/2026: cualquier numero fijo se quema con la primera ejecucion
# real (confirmado una 3ra vez: 264252/781431/781435 de IT1, y 1583377
# quemado por esta misma sesion al confirmar el fix) - se busca un
# cliente Retirado FRESCO en vivo en cada corrida en vez de hardcodear.
SEMILLAS_CLIENTES_RF01 = [264252, 264279, 1583373, 1764523, 781409, 781410,
                          1830410, 781435, 781384, 781428, 781429, 264302,
                          264268, 781431]
numero_cliente = encontrar_cliente_en_estado(app, frame, SEMILLAS_CLIENTES_RF01, "2", radio=100)
agregar_cliente_traslado(app, frame, numero_cliente)
capturar_paso(app, "cliente_agregado", paso_excel=3)
trasladar_y_confirmar(app, frame)
mensaje = leer_mensaje_resultado_traslado(frame)
assert "se procesaron todos los clientes" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[:400]}"
capturar_paso(app, "resultado_exitoso", paso_excel=5)
cerrar_dialogos_resultado_traslado(app, frame)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
seleccionar_tipo_traslado(frame, "CEAR")
capturar_paso(app, "tipo_traslado_cear", paso_excel=2)
agregar_cliente_traslado(app, frame, "264279")  # confirmado con cartera "91.00" via Trasladar real (rechazado) el 25/09/2026
capturar_paso(app, "cliente_con_cartera_agregado", paso_excel=3)
capturar_paso(app, "forzar_sin_marcar", paso_excel=4)  # checkbox permanece sin marcar (estado por defecto)
trasladar_y_confirmar(app, frame)
mensaje = leer_mensaje_resultado_traslado(frame)
assert "cartera" in mensaje.lower(), f"No se vio el rechazo por cartera esperado: {mensaje[:400]}"
assert "no se procesaron" in mensaje.lower(), f"Se esperaba que el cliente NO se procese: {mensaje[:400]}"
capturar_paso(app, "resultado_rechazado", paso_excel=5)
cerrar_dialogos_resultado_traslado(app, frame)
'''

CUERPOS_REALES["CP003"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
seleccionar_tipo_traslado(frame, "CEAR")
capturar_paso(app, "tipo_traslado_cear", paso_excel=2)
agregar_cliente_traslado(app, frame, "1583373")  # confirmado con cartera "19.21" via Trasladar real (rechazado sin forzar) el 25/09/2026
capturar_paso(app, "cliente_con_cartera_agregado", paso_excel=3)
marcar_forzar_retiro_carteras(frame)
capturar_paso(app, "forzar_marcado", paso_excel=4)
trasladar_y_confirmar(app, frame)
mensaje = leer_mensaje_resultado_traslado(frame)
assert "se procesaron todos los clientes" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[:400]}"
capturar_paso(app, "resultado_forzado_exitoso", paso_excel=5)
cerrar_dialogos_resultado_traslado(app, frame)
'''

CUERPOS_REALES["CP004"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
# El EF llama al boton "Buscar"; en la pantalla real el control se llama
# "Cargar archivo" (label que envuelve un <input type=file> oculto) -
# confirmado en vivo el 25/09/2026, ver gotcha de nombres EF-vs-real en
# NUEVO_PROYECTO_CHECKLIST.md.
archivo_clientes = EVIDENCIA / "clientes_carga.txt"
archivo_clientes.write_text("781409\\n781410\\n1830410\\n", encoding="utf-8")
capturar_paso(app, "antes_de_cargar_archivo", paso_excel=2)
frame.locator('input[type="file"]').set_input_files(str(archivo_clientes))
app.wait_for_timeout(1500)
capturar_paso(app, "archivo_cargado", paso_excel=4)
filas = filas_clientes_traslado(frame)
assert filas.count() == 3, f"Se esperaban 3 clientes cargados desde archivo, se ven {filas.count()}"
'''

CUERPOS_REALES["CP005"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app, frame, "781409")
capturar_paso(app, "cliente_agregado_primera_vez", paso_excel=2)
agregar_cliente_traslado(app, frame, "781409")
capturar_paso(app, "intento_agregar_duplicado", paso_excel=3)
filas = filas_clientes_traslado(frame)
assert filas.count() == 1, f"Se esperaba que el cliente duplicado no se agregue de nuevo, hay {filas.count()} filas"
capturar_paso(app, "lista_con_una_sola_entrada", paso_excel=4)
'''

CUERPOS_REALES["CP006"] = '''
app, frame = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app, frame, "1764523")  # confirmado estado=0 ("activo", no Retirado) via API ValidarCliente el 25/09/2026
capturar_paso(app, "cliente_no_elegible_agregado", paso_excel=2)
trasladar_y_confirmar(app, frame)
mensaje = leer_mensaje_resultado_traslado(frame)
assert "no est" in mensaje.lower() and "retirado" in mensaje.lower(), f"No se vio el rechazo esperado: {mensaje[:400]}"
capturar_paso(app, "resultado_no_procesado", paso_excel=4)
cerrar_dialogos_resultado_traslado(app, frame)
'''

# --- RF-02 "Mantenimiento de Carteras" (CP007-CP012) - bodies reales,
# verificados en vivo el 25/09/2026 (ver _exploracion/explore_10..14.py).
# Datos de prueba: "01.03" (OT ya existente, confirmada real, para CP009);
# "91.00" (cartera real con cliente asociado - confirmada en explore_08 de
# RF-01 - para CP012, ubicada en la pagina 3 de la grilla via
# buscar_fila_en_paginas_carteras); CP008/CP010/CP011 crean su propia cartera
# fresca con generar_codigo_ot() (garantiza 0 clientes asociados, ideal para
# CP011 en particular).

CUERPOS_REALES["CP007"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
capturar_paso(app, "grilla_carteras", paso_excel=2)
filas = frame.locator("nz-table tbody tr:not(.ant-table-measure-now)")
assert filas.count() > 0, "Se esperaban carteras vigentes en la grilla al abrir la pantalla"
# El combo de Proveedor viene deshabilitado hasta pulsar "Ingresar" (no hay
# forma de inspeccionarlo desde el estado de solo lectura) - se entra a modo
# alta solo para verificar su contenido y se descarta con "Cancelar" sin
# guardar nada (confirmado en vivo: no dispara ningun registro).
click_ingresar_cartera(frame)
app.wait_for_timeout(500)
frame.locator("#proveedor").click()
app.wait_for_timeout(800)
opciones_proveedor = frame.locator("nz-option-item, .ant-select-item-option")
capturar_paso(app, "combo_proveedores", paso_excel=3)
assert opciones_proveedor.count() > 0, "Se esperaban proveedores de cobranza activos en el combo"
frame.locator("body").press("Escape")
app.wait_for_timeout(300)
boton_por_texto(frame, "Cancelar").click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP008"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
ot_nueva = generar_codigo_ot()
click_ingresar_cartera(frame)
capturar_paso(app, "antes_de_completar", paso_excel=1)
completar_ot_proveedor(app, frame, ot_nueva)
capturar_paso(app, "datos_completados", paso_excel=2)
boton_por_texto(frame, "Aceptar").click()
mensaje = confirmar_y_leer_resultado_cartera(app, frame)
assert "creada exitosamente" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-500:]}"
capturar_paso(app, "resultado_exitoso", paso_excel=4)
'''

CUERPOS_REALES["CP009"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
click_ingresar_cartera(frame)
capturar_paso(app, "antes_de_completar", paso_excel=2)
completar_ot_proveedor(app, frame, "01.03")  # OT confirmada existente en vivo el 25/09/2026 (explore_10)
capturar_paso(app, "ot_duplicada_completada", paso_excel=2)
boton_por_texto(frame, "Aceptar").click()
mensaje_error = confirmar_y_leer_resultado_cartera(app, frame)  # cierra la confirmacion y la "Ventana de Validacion" con el error real
assert "ya existe" in mensaje_error.lower(), f"No se vio el rechazo por OT duplicada esperado: {mensaje_error!r}"
capturar_paso(app, "resultado_rechazado", paso_excel=4)
'''

CUERPOS_REALES["CP010"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
ot_nueva = generar_codigo_ot()
click_ingresar_cartera(frame)
completar_ot_proveedor(app, frame, ot_nueva, indice_proveedor=0)
boton_por_texto(frame, "Aceptar").click()
confirmar_y_leer_resultado_cartera(app, frame)
recargar_carteras(app)
frame = app.locator("#aplicacion").content_frame
fila = buscar_fila_en_paginas_carteras(app, frame, ot_nueva)
assert fila is not None, f"No se encontro la cartera recien creada {ot_nueva} tras recargar (revisadas todas las paginas)"
fila.click()
capturar_paso(app, "cartera_seleccionada", paso_excel=1)
boton_por_texto(frame, "Modificar").click()
app.wait_for_timeout(600)
frame.locator("#proveedor").click()
app.wait_for_timeout(800)
frame.locator("nz-option-item, .ant-select-item-option").nth(1).click()  # proveedor DISTINTO al inicial (indice 0)
app.wait_for_timeout(400)
capturar_paso(app, "proveedor_cambiado", paso_excel=3)
boton_por_texto(frame, "Aceptar").click()
mensaje = confirmar_y_leer_resultado_cartera(app, frame)
assert "modificada exitosamente" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-500:]}"
capturar_paso(app, "resultado_exitoso", paso_excel=5)
'''

CUERPOS_REALES["CP011"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
# Cartera creada de cero en este mismo caso: garantiza 0 clientes asociados
# (condicion de RN-13, sin depender de datos reales que puedan cambiar).
ot_nueva = generar_codigo_ot()
click_ingresar_cartera(frame)
completar_ot_proveedor(app, frame, ot_nueva)
boton_por_texto(frame, "Aceptar").click()
confirmar_y_leer_resultado_cartera(app, frame)
recargar_carteras(app)
frame = app.locator("#aplicacion").content_frame
fila = buscar_fila_en_paginas_carteras(app, frame, ot_nueva)
assert fila is not None, f"No se encontro la cartera recien creada {ot_nueva} tras recargar (revisadas todas las paginas)"
fila.click()
capturar_paso(app, "cartera_sin_clientes_seleccionada", paso_excel=1)
boton_por_texto(frame, "Anular").click()
mensaje_final = confirmar_y_leer_resultado_cartera(app, frame)
assert "anulada exitosamente" in mensaje_final.lower(), f"No se vio el mensaje de exito esperado: {mensaje_final[-500:]}"
capturar_paso(app, "resultado_exitoso", paso_excel=3)
'''

CUERPOS_REALES["CP012"] = '''
app, frame = abrir_mantenimiento_carteras(page, paso_excel=1)
# "91.00" confirmada en vivo el 25/09/2026 con cliente asociado (264279,
# ver exploracion de RF-01) - no tiene buscador esta grilla, se pagina
# hasta encontrarla (confirmada en pagina 3 el 25/09/2026, puede variar).
fila = buscar_fila_en_paginas_carteras(app, frame, "91.00")
assert fila is not None, "No se encontro la cartera 91.00 (con clientes asociados) en ninguna pagina"
fila.click()
capturar_paso(app, "cartera_con_clientes_seleccionada", paso_excel=1)
boton_por_texto(frame, "Anular").click()
mensaje_error = confirmar_y_leer_resultado_cartera(app, frame)
assert "clientes asociados" in mensaje_error.lower(), f"No se vio el rechazo esperado: {mensaje_error!r}"
capturar_paso(app, "resultado_rechazado", paso_excel=3)
'''

# --- RF-03 "Asignacion de Clientes a Carteras" (CP013-CP018) - bodies
# reales, verificados en vivo el 26/09/2026 (ver
# _exploracion/explore_16..22_rf03_*.py). Cada caso que necesita un cliente
# "elegible" (Cobranza Externa sin cartera) lo crea DE CERO al inicio de su
# propio body (transicion via RF-01 con un cliente Retirado confirmado por
# API el 25/09/2026), en vez de depender de datos ambiente ya existentes -
# se descarto usar carteras "reales" de negocio (ej. "91.00") como dato de
# prueba porque su asociacion, vista desde ESTA pantalla especificamente,
# no coincidio con lo visto desde RF-01 (dato no confiable, ver memoria del
# proyecto). Cartera destino usada en las asignaciones: "005340" (creada en
# RF-02, confirmada real). La grilla de esta pantalla tampoco se refresca
# sola tras Agregar/Asignar/Quitar - siempre se reselecciona la cartera
# para verificar el estado real.

CUERPOS_REALES["CP013"] = '''
app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)
frame.locator(".cartera-select").click(timeout=20000)
app.wait_for_timeout(1000)
opciones = frame.locator("nz-option-item, .ant-select-item-option")
capturar_paso(app, "combo_carteras_abierto", paso_excel=2)
assert opciones.count() > 0, "Se esperaban carteras activas en el combo"
frame.locator("body").press("Escape")
app.wait_for_timeout(300)
'''

CUERPOS_REALES["CP014"] = '''
app1, frame1 = abrir_traslado_clientes(page, paso_excel=1)
# IT2 15/10/2026: "264302" (hardcodeado en IT1) ya esta quemado - buscar
# un cliente Retirado fresco en vivo, mismo metodo que CP001.
SEMILLAS_CLIENTES_RF01_CP014 = [264252, 264279, 1583373, 1764523, 781409,
                                781410, 1830410, 781435, 781384, 781428,
                                781429, 264302, 264268, 781431]
cliente_cp014 = encontrar_cliente_en_estado(app1, frame1, SEMILLAS_CLIENTES_RF01_CP014, "2", radio=100)
agregar_cliente_traslado(app1, frame1, cliente_cp014)
trasladar_y_confirmar(app1, frame1)
app1.close()
# Recargar el portal antes de abrir la 2da app: reutilizar `page` para 2
# navegaciones seguidas via el menu Aplicaciones deja el arbol de menu en
# un estado impredecible (confirmado en vivo el 26/09/2026, mismo bug que
# explore_03 de las 12 apps) - un goto simple (la sesion sigue logueada)
# alcanza para resetear el menu sin repetir login().
page.goto(URL)
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(800)

app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
seleccionar_cartera_asignacion(app, frame, "005340")
agregar_cliente_asignacion(frame, cliente_cp014)
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
boton_por_texto(frame, "Asignar").click()
confirmar_dialogo_asignacion(app, frame)
capturar_paso(app, "cliente_asignado", paso_excel=1)

# La grilla no se refresca sola (confirmado en vivo el 26/09/2026) -
# reseleccionar la cartera dispara un fetch nuevo con el estado real.
seleccionar_cartera_asignacion(app, frame, "005340")
capturar_paso(app, "cartera_reseleccionada", paso_excel=2)
filas_asociados = filas_panel_asignacion(frame, "Clientes Asociados a la Cartera")
assert filas_asociados.filter(has_text=cliente_cp014).count() > 0, "Se esperaba ver el cliente asociado en la grilla de la cartera"
'''

CUERPOS_REALES["CP015"] = '''
app1, frame1 = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app1, frame1, "264268")  # confirmado Retirado (estado=2) via API el 25/09/2026
trasladar_y_confirmar(app1, frame1)
app1.close()
# Recargar el portal antes de abrir la 2da app: reutilizar `page` para 2
# navegaciones seguidas via el menu Aplicaciones deja el arbol de menu en
# un estado impredecible (confirmado en vivo el 26/09/2026, mismo bug que
# explore_03 de las 12 apps) - un goto simple (la sesion sigue logueada)
# alcanza para resetear el menu sin repetir login().
page.goto(URL)
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(800)

app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
seleccionar_cartera_asignacion(app, frame, "005340")
capturar_paso(app, "cartera_seleccionada", paso_excel=1)
agregar_cliente_asignacion(frame, "264268")
capturar_paso(app, "cliente_ingresado", paso_excel=2)
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
capturar_paso(app, "cliente_agregado_a_lista", paso_excel=3)
filas_por_asociar = filas_panel_asignacion(frame, "Clientes por Asociar")
assert filas_por_asociar.filter(has_text="264268").count() > 0, "Se esperaba ver el cliente en la grilla de Clientes por Asociar"
'''

CUERPOS_REALES["CP016"] = '''
app1, frame1 = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app1, frame1, "781384")  # confirmado Retirado (estado=2) via API el 25/09/2026
trasladar_y_confirmar(app1, frame1)
app1.close()
# Recargar el portal antes de abrir la 2da app: reutilizar `page` para 2
# navegaciones seguidas via el menu Aplicaciones deja el arbol de menu en
# un estado impredecible (confirmado en vivo el 26/09/2026, mismo bug que
# explore_03 de las 12 apps) - un goto simple (la sesion sigue logueada)
# alcanza para resetear el menu sin repetir login().
page.goto(URL)
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(800)

app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
seleccionar_cartera_asignacion(app, frame, "005340")
agregar_cliente_asignacion(frame, "781384")
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
boton_por_texto(frame, "Asignar").click()
confirmar_dialogo_asignacion(app, frame)

# Cliente 264290 ya tiene cartera "005340" asignada - intentar agregarlo a
# OTRA cartera distinta debe rechazarlo. Confirmado en vivo el 26/09/2026:
# el rechazo es SILENCIOSO (sin dialogo ni toast visible, a diferencia de
# RF-01) - se verifica por el estado real de la grilla, no por mensaje.
seleccionar_cartera_asignacion(app, frame, "005456")
capturar_paso(app, "cartera_distinta_seleccionada", paso_excel=1)
agregar_cliente_asignacion(frame, "781384")
capturar_paso(app, "cliente_no_elegible_ingresado", paso_excel=2)
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
capturar_paso(app, "resultado_rechazado", paso_excel=3)
filas_por_asociar = filas_panel_asignacion(frame, "Clientes por Asociar")
assert filas_por_asociar.filter(has_text="781384").count() == 0, "El cliente ya asignado a otra cartera NO deberia poder agregarse aqui"
'''

CUERPOS_REALES["CP017"] = '''
app1, frame1 = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app1, frame1, "781428")  # confirmado Retirado (estado=2) via API el 25/09/2026
trasladar_y_confirmar(app1, frame1)
app1.close()
# Recargar el portal antes de abrir la 2da app: reutilizar `page` para 2
# navegaciones seguidas via el menu Aplicaciones deja el arbol de menu en
# un estado impredecible (confirmado en vivo el 26/09/2026, mismo bug que
# explore_03 de las 12 apps) - un goto simple (la sesion sigue logueada)
# alcanza para resetear el menu sin repetir login().
page.goto(URL)
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(800)

app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
seleccionar_cartera_asignacion(app, frame, "005340")
agregar_cliente_asignacion(frame, "781428")
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
capturar_paso(app, "grilla_por_asociar_conformada", paso_excel=1)
boton_por_texto(frame, "Asignar").click()
confirmar_dialogo_asignacion(app, frame)
capturar_paso(app, "tras_asignar", paso_excel=2)

# Reseleccionar la cartera para verificar el estado real (la grilla no se
# refresca sola, confirmado en vivo el 26/09/2026).
seleccionar_cartera_asignacion(app, frame, "005340")
capturar_paso(app, "cartera_reseleccionada", paso_excel=3)
filas_asociados = filas_panel_asignacion(frame, "Clientes Asociados a la Cartera")
assert filas_asociados.filter(has_text="781428").count() > 0, "Se esperaba que el cliente quede asociado a la cartera tras Asignar"
'''

CUERPOS_REALES["CP018"] = '''
app1, frame1 = abrir_traslado_clientes(page, paso_excel=1)
agregar_cliente_traslado(app1, frame1, "781429")  # confirmado Retirado (estado=2) via API el 25/09/2026
trasladar_y_confirmar(app1, frame1)
app1.close()
# Recargar el portal antes de abrir la 2da app: reutilizar `page` para 2
# navegaciones seguidas via el menu Aplicaciones deja el arbol de menu en
# un estado impredecible (confirmado en vivo el 26/09/2026, mismo bug que
# explore_03 de las 12 apps) - un goto simple (la sesion sigue logueada)
# alcanza para resetear el menu sin repetir login().
page.goto(URL)
page.wait_for_load_state("networkidle", timeout=20000)
page.wait_for_timeout(800)

app, frame = abrir_asignacion_clientes_carteras(page, paso_excel=1)
seleccionar_cartera_asignacion(app, frame, "005340")
agregar_cliente_asignacion(frame, "781429")
boton_por_texto(frame, "Agregar").click()
app.wait_for_timeout(1500)
boton_por_texto(frame, "Asignar").click()
confirmar_dialogo_asignacion(app, frame)
seleccionar_cartera_asignacion(app, frame, "005340")  # ver el estado real ya asignado

filas_asociados = filas_panel_asignacion(frame, "Clientes Asociados a la Cartera")
assert filas_asociados.filter(has_text="781429").count() > 0, "El cliente deberia estar asociado antes de poder Quitarlo"
filas_asociados.filter(has_text="781429").first.click()
capturar_paso(app, "cliente_asociado_seleccionado", paso_excel=1)
boton_por_texto(frame, "Quitar").click()
confirmar_dialogo_asignacion(app, frame)
capturar_paso(app, "tras_quitar", paso_excel=2)

seleccionar_cartera_asignacion(app, frame, "005340")  # verificar estado real tras Quitar
capturar_paso(app, "cartera_reseleccionada", paso_excel=3)
filas_asociados = filas_panel_asignacion(frame, "Clientes Asociados a la Cartera")
assert filas_asociados.filter(has_text="781429").count() == 0, "El cliente NO deberia seguir asociado tras Quitar"
'''

# --- RF-04 "Clientes a Investigar" (CP019-CP024) - bodies reales,
# verificados en vivo el 26/09/2026 (ver _exploracion/explore_24..25.py).
# Cartera "005340" (creada en RF-02, poblada con clientes reales en RF-03)
# tiene 8 clientes en estado "Activo" - se reusan esos mismos numeros para
# marcar/normalizar. "000000" es la "cartera de espera" mencionada en el
# CP019 (aparece primera en el combo real).

CUERPOS_REALES["CP019"] = '''
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)
frame.locator(".sel-cartera").click(timeout=20000)
app.wait_for_timeout(1000)
opciones = frame.locator("nz-option-item, .ant-select-item-option")
capturar_paso(app, "combo_carteras_abierto", paso_excel=2)
assert opciones.count() > 0, "Se esperaban carteras en el combo"
assert opciones.filter(has_text="000000").count() > 0, "Se esperaba ver la cartera de espera (000000) en el combo"
frame.locator("body").press("Escape")
app.wait_for_timeout(300)
'''

CUERPOS_REALES["CP020"] = '''
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
seleccionar_cartera_investigacion(app, frame, "005340")
capturar_paso(app, "cartera_seleccionada", paso_excel=1)
leer_clientes_investigacion(app, frame)
capturar_paso(app, "grilla_leida", paso_excel=3)
filas = frame.locator("nz-table tbody tr:not(.ant-table-measure-now)")
assert filas.count() > 0, "Se esperaban clientes en la grilla de la cartera"
assert "Activo" in filas.first.inner_text() or "Investigado" in filas.first.inner_text(), "Se esperaba ver el Estado del cliente en la grilla"
'''

CUERPOS_REALES["CP021"] = '''
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
seleccionar_cartera_investigacion(app, frame, "005340")
leer_clientes_investigacion(app, frame)
marcar_cliente_investigacion(frame, "264241")
marcar_cliente_investigacion(frame, "264264")
capturar_paso(app, "dos_clientes_marcados", paso_excel=1)
boton_por_texto(frame, "A Investigar").click()
confirmar_dialogo_asignacion(app, frame)
capturar_paso(app, "tras_a_investigar", paso_excel=2)
leer_clientes_investigacion(app, frame)  # releer para confirmar el estado persistido
capturar_paso(app, "grilla_releida", paso_excel=3)
assert "Investigado" in fila_cliente_investigacion(frame, "264241").inner_text(), "Se esperaba que 264241 quede Investigado"
assert "Investigado" in fila_cliente_investigacion(frame, "264264").inner_text(), "Se esperaba que 264264 quede Investigado"
'''

CUERPOS_REALES["CP022"] = '''
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
seleccionar_cartera_investigacion(app, frame, "005340")
leer_clientes_investigacion(app, frame)
# Setup propio: marcar 2 clientes distintos como Investigado primero (RN
# de este RF exige estado Investigado para poder Normalizar).
marcar_cliente_investigacion(frame, "264290")
marcar_cliente_investigacion(frame, "264295")
boton_por_texto(frame, "A Investigar").click()
confirmar_dialogo_asignacion(app, frame)
leer_clientes_investigacion(app, frame)

marcar_cliente_investigacion(frame, "264290")
marcar_cliente_investigacion(frame, "264295")
capturar_paso(app, "dos_clientes_investigados_marcados", paso_excel=1)
boton_por_texto(frame, "Normalizar").click()
confirmar_dialogo_asignacion(app, frame)
capturar_paso(app, "tras_normalizar", paso_excel=2)
leer_clientes_investigacion(app, frame)
capturar_paso(app, "grilla_releida", paso_excel=3)
assert "Activo" in fila_cliente_investigacion(frame, "264290").inner_text(), "Se esperaba que 264290 vuelva a Activo"
assert "Activo" in fila_cliente_investigacion(frame, "264295").inner_text(), "Se esperaba que 264295 vuelva a Activo"
'''

CUERPOS_REALES["CP023"] = '''
# La matriz describe "pulsar A Investigar/Normalizar sin seleccion y ver
# un mensaje de advertencia" - confirmado en vivo el 26/09/2026 que ESTO
# NO ES POSIBLE en la pantalla real: ambos botones quedan DESHABILITADOS
# (atributo disabled, no solo estilo) mientras no haya ninguna fila
# marcada - un click real no dispara nada, no hay forma de generar el
# mensaje de texto. Se verifico ademas que no es un bug de reactividad
# (marcar y desmarcar SI vuelve a deshabilitar los botones correctamente).
# Se adapta el caso a lo que SI es verificable: el sistema impide la
# accion sin seleccion mediante los botones deshabilitados - garantia
# equivalente o mas fuerte que un mensaje de error en tiempo de ejecucion.
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
seleccionar_cartera_investigacion(app, frame, "005340")
leer_clientes_investigacion(app, frame)
capturar_paso(app, "sin_seleccion", paso_excel=1)
boton_investigar = boton_por_texto(frame, "A Investigar")
boton_normalizar = boton_por_texto(frame, "Normalizar")
capturar_paso(app, "botones_deshabilitados", paso_excel=3)
assert boton_investigar.get_attribute("disabled") is not None, "Se esperaba 'A Investigar' deshabilitado sin seleccion"
assert boton_normalizar.get_attribute("disabled") is not None, "Se esperaba 'Normalizar' deshabilitado sin seleccion"
'''

CUERPOS_REALES["CP024"] = '''
app, frame = abrir_investigacion_clientes(page, paso_excel=1)
seleccionar_cartera_investigacion(app, frame, "005340")
leer_clientes_investigacion(app, frame)
marcar_cliente_investigacion(frame, "264296")
capturar_paso(app, "cliente_marcado", paso_excel=1)
boton_por_texto(frame, "A Investigar").click()
confirmar_dialogo_asignacion(app, frame)
# Sin volver a pulsar "Leer / Consultar": la fila deberia reflejar el
# cambio de estado de inmediato en la MISMA grilla ya cargada.
capturar_paso(app, "estado_actualizado_sin_recargar", paso_excel=2)
assert "Investigado" in fila_cliente_investigacion(frame, "264296").inner_text(), "Se esperaba ver el estado actualizado sin recargar la grilla"
'''

# --- RF-05 "Emision de Cartas Masivas" (CP025-CP030) - bodies reales,
# verificados en vivo el 26/09/2026 (ver _exploracion/explore_27..32.py).
# Clientes reales confirmados con direccion/distrito completos (204241,
# 264268, 264295 - ya usados en RFs anteriores). CP027 no es literalmente
# reproducible (el campo Fecha se defiende de cualquier valor invalido,
# revierte solo a la fecha de hoy) - se adapta a verificar esa defensa,
# mismo criterio que CP023 de RF-04.

CUERPOS_REALES["CP025"] = '''
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
agregar_cliente_carta(app, frame, "264241")
capturar_paso(app, "cliente_agregado", paso_excel=2)
# Fecha ya viene con la fecha de hoy por defecto (valida); Art. 90 y Art.
# 178 ya vienen marcados por defecto - solo hace falta completar Responsable.
completar_responsable_carta(frame)
capturar_paso(app, "datos_completados", paso_excel=3)
cerrar_dialogo_cartas_masivas(app, frame)
frame.locator("button", has_text=re.compile(r"^\\s*Generar\\s*$")).click()
mensaje = esperar_mensaje_exito_impresion(app, frame)
assert "impresion finalizada con exito" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-400:]}"
capturar_paso(app, "resultado_exitoso", paso_excel=5)
'''

CUERPOS_REALES["CP026"] = '''
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
archivo_clientes = EVIDENCIA / "clientes_cartas.txt"
archivo_clientes.write_text("264264\\n264268\\n264290\\n", encoding="utf-8")
capturar_paso(app, "antes_de_cargar_archivo", paso_excel=1)
frame.locator('input[type="file"]').set_input_files(str(archivo_clientes))
app.wait_for_timeout(1500)
cerrar_dialogo_cartas_masivas(app, frame)
capturar_paso(app, "archivo_cargado", paso_excel=3)
filas = frame.locator("nz-table tbody tr:not(.ant-table-measure-now)")
assert filas.count() == 3, f"Se esperaban 3 clientes cargados desde archivo, se ven {filas.count()}"
'''

CUERPOS_REALES["CP027"] = '''
# La matriz describe "ingresar una fecha invalida y ver Fecha no es
# valida." - confirmado en vivo el 26/09/2026 que el campo Fecha se
# defiende de esto: escribir texto invalido o dejarlo vacio SIEMPRE
# revierte a la fecha de hoy (valida) al perder foco - no hay forma real
# de dejarlo en un estado invalido para que "Generar" lo rechace. Se
# adapta el caso a verificar esa defensa (mismo criterio que CP023 de RF-04).
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
valor_inicial = campo_fecha.input_value()
capturar_paso(app, "fecha_inicial", paso_excel=1)
campo_fecha.click()
app.wait_for_timeout(300)
campo_fecha.fill("")
app.wait_for_timeout(300)
frame.locator("h3", has_text="Selección de Clientes").click()
app.wait_for_timeout(500)
capturar_paso(app, "fecha_tras_intentar_vaciar", paso_excel=2)
valor_final = campo_fecha.input_value()
assert valor_final, "Se esperaba que el campo Fecha nunca quede vacio (revierte a la fecha de hoy)"
capturar_paso(app, "fecha_se_mantiene_valida", paso_excel=3)
'''

CUERPOS_REALES["CP028"] = '''
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
agregar_cliente_carta(app, frame, "264268")
capturar_paso(app, "cliente_agregado", paso_excel=1)
checks = frame.locator('.check-group input[type="checkbox"]')
for i in range(checks.count()):
    if checks.nth(i).is_checked():
        checks.nth(i).click()
        app.wait_for_timeout(300)
capturar_paso(app, "tipos_de_carta_desmarcados", paso_excel=2)
frame.locator("button", has_text=re.compile(r"^\\s*Generar\\s*$")).click()
app.wait_for_timeout(1500)
mensaje = cerrar_dialogo_cartas_masivas(app, frame)
assert mensaje is not None and "error al generar" in mensaje.lower(), f"No se vio el mensaje de rechazo esperado: {mensaje!r}"
capturar_paso(app, "resultado_rechazado", paso_excel=4)
'''

CUERPOS_REALES["CP029"] = '''
# No se encontro un cliente real "sin medidor activo" (el propio ambiente
# de Pruebas no distingue esto de forma sencilla) - se usa un numero de
# cliente INEXISTENTE junto a uno valido, mismo efecto de "datos
# incompletos que deben excluirse sin bloquear el resto del lote"
# (confirmado en vivo: ambos se agregan a la lista sin error inmediato,
# pero Generar sigue dando OK igual - el invalido se excluye en
# silencio sin frenar la generacion de los validos).
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
agregar_cliente_carta(app, frame, "9999999")
cerrar_dialogo_cartas_masivas(app, frame)
agregar_cliente_carta(app, frame, "264295")
cerrar_dialogo_cartas_masivas(app, frame)
capturar_paso(app, "clientes_agregados", paso_excel=1)
completar_responsable_carta(frame)
frame.locator("button", has_text=re.compile(r"^\\s*Generar\\s*$")).click()
mensaje = esperar_mensaje_exito_impresion(app, frame)
assert "impresion finalizada con exito" in mensaje.lower(), f"Se esperaba que el cliente invalido no bloquee la generacion del resto: {mensaje[-400:]}"
capturar_paso(app, "resultado_cliente_excluido", paso_excel=3)
'''

CUERPOS_REALES["CP030"] = '''
app, frame = abrir_emision_cartas_masivas(page, paso_excel=1)
cerrar_dialogo_cartas_masivas(app, frame)
agregar_cliente_carta(app, frame, "264296")
capturar_paso(app, "cliente_agregado_primera_vez", paso_excel=1)
agregar_cliente_carta(app, frame, "264296")
mensaje = cerrar_dialogo_cartas_masivas(app, frame)
assert mensaje is not None and "ya est" in mensaje.lower() and "lista" in mensaje.lower(), f"No se vio el rechazo por duplicado esperado: {mensaje!r}"
capturar_paso(app, "intento_agregar_duplicado", paso_excel=2)
filas = frame.locator("nz-table tbody tr:not(.ant-table-measure-now)").filter(has_text="264296")
assert filas.count() == 1, f"Se esperaba una sola entrada de 264296, hay {filas.count()}"
capturar_paso(app, "lista_con_una_sola_entrada", paso_excel=3)
'''

# --- RF-06 "Anulamiento de Facturas" (CP031, CP034 unicamente) - bodies
# reales, verificados en vivo el 26/09/2026 (ver
# _exploracion/explore_33_rf06_detalle.py).
#
# BLOQUEADO (decision del usuario 26/09/2026): CP032/033/035/036 necesitan
# un cliente con FACTURAS REALES ANULABLES en este ambiente de Pruebas -
# ninguno de los clientes de prueba disponibles (ni los sinteticos propios
# de este proyecto, ni los reales conocidos de suministros.txt, ej.
# 1764523 "HUAMAN TEJO PAOLA FERNANDA") tiene facturas anulables cargadas
# ("Sin facturas anulables" en los 8 numeros probados). CP035/036 ademas
# necesitan condiciones muy especificas (tasa de IGV historica distinta a
# la actual, consumos de mas de 12 meses - el propio aviso de la pantalla
# confirma el corte real: "Los consumos fisicos anteriores a 01/10/2025 no
# seran ingresados en la refacturacion"). El usuario decidio dejarlos
# pendientes hasta conseguir un numero de cliente real con facturas
# anulables, en vez de seguir buscando a ciegas. Quedan con
# NotImplementedError explicito (ver PENDIENTE en la memoria del
# proyecto), NO con el placeholder generico _BODY_PENDIENTE.

CUERPOS_REALES["CP031"] = '''
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "264241")  # confirmado Cobranza Externa (estado=6), sin rechazo
capturar_paso(app, "cliente_consultado", paso_excel=2)
mensaje_error = cerrar_dialogo_anulacion_facturas(app, frame)
assert mensaje_error is None, f"No se esperaba rechazo para un cliente en Cobranza Externa: {mensaje_error!r}"
# El cliente no tiene facturas anulables reales en este ambiente, pero la
# grilla SI carga (vacia) junto con los totales en S/ 0.00 - confirma que
# el sistema completo el flujo de carga sin error, que es lo que valida
# este caso segun CU-18.
texto = frame.locator("body").inner_text()
assert "total saldo" in texto.lower(), "Se esperaba ver la seccion de Totales cargada"
capturar_paso(app, "facturas_y_totales_cargados", paso_excel=3)
'''

_MOTIVO_BLOQUEO_RF06 = (
    "necesita un cliente con facturas anulables REALES en este ambiente de "
    "Pruebas - ninguno de los clientes de prueba disponibles tiene facturas "
    "cargadas ('Sin facturas anulables' en los 8 numeros probados el "
    "26/09/2026, incluidos clientes reales conocidos como 1764523). "
    "Bloqueado por decision del usuario hasta conseguir un numero de "
    "cliente real con facturas anulables - ver memoria del proyecto "
    "PR000349-SP1 (seccion RF-06)."
)

CUERPOS_REALES["CP032"] = '''
# Cliente 4016725 (no 126331: ese quedo con menos de 4 facturas libres
# tras las pruebas individuales de CP033/CP035 de esta misma sesion -
# confirmado en vivo 21/10/2026, 7 facturas anulables disponibles).
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "4016725")
capturar_paso(app, "cliente_con_facturas", paso_excel=1)
checks = frame.locator(\'tbody input[type="checkbox"]\')
assert checks.count() >= 4, f"Se esperaban al menos 4 facturas anulables para el cliente 4016725: {checks.count()}"
# OJO: la pantalla tiene 3 <table> (Datos del Cliente + Facturas +
# Refacturaciones oculta) - frame.locator("tbody tr") sin acotar agarra
# la fila de "Datos del Cliente" primero (confirmado en vivo 21/10/2026
# con CP033). Usar el checkbox como ancla (su fila ANCESTRA real) evita
# el desalineamiento.
fechas_marcadas = []
for i in range(4):
    fila_i = checks.nth(i).locator("xpath=ancestor::tr")
    fecha_fila = fila_i.locator("td").nth(1).inner_text().strip()
    assert "/" in fecha_fila, f"La fila marcada {i} no parece tener una fecha real: {fecha_fila!r}"
    fechas_marcadas.append(fecha_fila)
    checks.nth(i).check()
    app.wait_for_timeout(200)
capturar_paso(app, "4_facturas_marcadas", paso_excel=2)
frame.locator("button").filter(has_text=re.compile(r"Anular facturas", re.I)).click()
app.wait_for_timeout(1000)
mensaje_confirmacion = cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(1500)
mensaje_resultado = cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
capturar_paso(app, "resultado_anulacion", paso_excel=3)
frame.get_by_text("Refacturaciones", exact=True).click()
app.wait_for_timeout(1500)
capturar_paso(app, "refacturaciones_generadas", paso_excel=4)
texto_refac = frame.locator("body").inner_text()
for fecha in fechas_marcadas:
    assert fecha in texto_refac, (
        f"Se esperaba una refacturacion para la factura con fecha {fecha} "
        f"(mensajes vistos: confirmacion={mensaje_confirmacion!r}, resultado={mensaje_resultado!r}): {texto_refac!r}"
    )
'''

CUERPOS_REALES["CP033"] = '''
# Autocontenido: anula UNA factura antigua propia (distinta a las que usa
# CP032/CP035) y revierte esa misma refacturacion recien creada, en vez
# de depender de una refacturacion REAL de 1996-97 ya existente (esas
# resultaron no revertibles al probarlo en vivo - confirmado 21/10/2026,
# el boton "Revertir refacturaciones" queda deshabilitado para una
# refacturacion vieja/ya procesada).
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "126331")
app.wait_for_timeout(1000)
checks = frame.locator(\'tbody input[type="checkbox"]\')
assert checks.count() >= 1, f"Se esperaba al menos 1 factura anulable libre: {checks.count()}"
# OJO: la pantalla tiene 3 <table> (Datos del Cliente + Facturas +
# Refacturaciones oculta) - frame.locator("tbody tr") sin acotar agarra
# la fila de "Datos del Cliente" primero. Usar el checkbox como ancla
# (su fila ANCESTRA real) evita el desalineamiento.
fila_propia = checks.nth(0).locator("xpath=ancestor::tr")
fecha_propia = fila_propia.locator("td").nth(1).inner_text().strip()
assert "/" in fecha_propia, f"La fila de la factura marcada no parece tener una fecha real: {fecha_propia!r}"
checks.nth(0).check()
app.wait_for_timeout(200)
capturar_paso(app, "factura_propia_marcada", paso_excel=1)
frame.locator("button").filter(has_text=re.compile(r"Anular facturas", re.I)).click()
app.wait_for_timeout(1000)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(1500)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(500)
frame.get_by_text("Refacturaciones", exact=True).click()
app.wait_for_timeout(1500)
capturar_paso(app, "refacturacion_propia_creada", paso_excel=2)
fila_refac = frame.locator("tbody tr").filter(has_text=fecha_propia)
assert fila_refac.count() >= 1, f"Se esperaba ver la refacturacion recien creada para la fecha {fecha_propia}"
check_refac = fila_refac.first.locator(\'input[type="checkbox"]\')
check_refac.check()
app.wait_for_timeout(300)
capturar_paso(app, "refacturacion_marcada", paso_excel=2)
boton_revertir = frame.locator("button").filter(has_text=re.compile(r"Revertir refacturaciones", re.I))
assert not boton_revertir.is_disabled(), "El boton Revertir refacturaciones deberia habilitarse con la refacturacion recien creada marcada"
boton_revertir.click()
app.wait_for_timeout(1000)
mensaje_confirmacion = cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(1500)
mensaje_resultado = cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
capturar_paso(app, "resultado_reversion", paso_excel=4)
frame.get_by_text("Facturas", exact=True).click()
app.wait_for_timeout(1500)
capturar_paso(app, "factura_revertida_en_tab_facturas", paso_excel=4)
texto_facturas = frame.locator("body").inner_text()
assert fecha_propia in texto_facturas, (
    f"Se esperaba ver la factura {fecha_propia} de vuelta en el tab Facturas tras revertir "
    f"(mensajes vistos: confirmacion={mensaje_confirmacion!r}, resultado={mensaje_resultado!r}): {texto_facturas!r}"
)
'''

CUERPOS_REALES["CP034"] = '''
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "781409")  # confirmado real, estado=0 (activo, ni Retirado ni Cobranza Externa)
capturar_paso(app, "cliente_estado_invalido_consultado", paso_excel=2)
mensaje = cerrar_dialogo_anulacion_facturas(app, frame)
assert mensaje is not None and "no est" in mensaje.lower() and "retirado" in mensaje.lower() and "cobranza externa" in mensaje.lower(), f"No se vio el rechazo esperado: {mensaje!r}"
capturar_paso(app, "resultado_rechazado", paso_excel=3)
'''

CUERPOS_REALES["CP035"] = '''
# Cliente 4016811 (VICENTE Q. HECTOR): facturas de 2006, dentro de la
# ventana real 2003-08-01/2011-03-01 donde la tasa de IGV vigente fue
# 19% (confirmado por SQL contra tabla/IMPTOS, codigo 070) - distinta a
# la tasa actual/2011-presente (18%), que es la misma que ya cubren los
# periodos usados en CP032/033 (cliente 126331, facturas 1996-97,
# tambien 18%). Se compara el IGV de la factura original (ya calculado
# con la tasa vigente en 2006) contra el IGV de la refacturacion recien
# generada: si coinciden EXACTO, confirma que el sistema preservo la
# tasa historica (19%) en vez de recalcular con la tasa actual (18%).
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "4016811")
app.wait_for_timeout(1000)
checks = frame.locator(\'tbody input[type="checkbox"]\')
assert checks.count() >= 1, f"Se esperaba al menos 1 factura anulable para el cliente 4016811: {checks.count()}"
fila_propia = checks.nth(0).locator("xpath=ancestor::tr")
celdas = fila_propia.locator("td")
fecha_propia = celdas.nth(1).inner_text().strip()
igv_original = celdas.nth(4).inner_text().strip()
assert "/" in fecha_propia, f"La fila marcada no parece tener una fecha real: {fecha_propia!r}"
capturar_paso(app, "factura_antigua_antes_de_anular", paso_excel=2)
checks.nth(0).check()
app.wait_for_timeout(200)
capturar_paso(app, "factura_antigua_marcada", paso_excel=2)
frame.locator("button").filter(has_text=re.compile(r"Anular facturas", re.I)).click()
app.wait_for_timeout(1000)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(1500)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(500)
frame.get_by_text("Refacturaciones", exact=True).click()
app.wait_for_timeout(1500)
capturar_paso(app, "refacturacion_con_igv_historico", paso_excel=4)
fila_refac = frame.locator("tbody tr").filter(has_text=fecha_propia)
assert fila_refac.count() >= 1, f"Se esperaba ver la refacturacion para la fecha {fecha_propia}"
igv_refac = fila_refac.first.locator("td").nth(4).inner_text().strip()
assert igv_refac == igv_original, (
    f"El IGV de la refacturacion ({igv_refac}) deberia coincidir con el IGV original "
    f"({igv_original}), calculado con la tasa vigente en {fecha_propia} (19%, distinta "
    f"a la tasa actual 18%) - si no coincide, el sistema esta recalculando con la tasa actual."
)
'''

CUERPOS_REALES["CP036"] = '''
# Cliente 4017449, factura corr=191 (30/06/2013, consumo_activo=310
# sembrado por INSERT directo en hisfac/hisco - ver matriz). Es muy
# anterior al corte real que la propia pantalla anuncia ("Los consumos
# fisicos anteriores a 01/11/2025 no seran ingresados en la
# refacturacion"), asi que el consumo (Kwh FP) deberia EXCLUIRSE
# (quedar en 0.00) en la refacturacion generada.
app, frame = abrir_anulacion_facturas(page, paso_excel=1)
consultar_cliente_facturas(app, frame, "4017449")
app.wait_for_timeout(1000)
checks = frame.locator(\'tbody input[type="checkbox"]\')
assert checks.count() >= 1, f"Se esperaba al menos 1 factura anulable para el cliente 4017449 (verificar el INSERT en hisfac/hisco): {checks.count()}"
fila_propia = checks.nth(0).locator("xpath=ancestor::tr")
celdas = fila_propia.locator("td")
fecha_propia = celdas.nth(1).inner_text().strip()
kwh_original = celdas.nth(6).inner_text().strip()
assert "/" in fecha_propia, f"La fila marcada no parece tener una fecha real: {fecha_propia!r}"
capturar_paso(app, "factura_con_consumo_antiguo", paso_excel=2)
assert kwh_original not in ("0.00", "0"), f"Se esperaba ver el consumo fisico sembrado (Kwh FP) en la factura original antes de anular, se vio: {kwh_original!r}"
checks.nth(0).check()
app.wait_for_timeout(200)
capturar_paso(app, "factura_marcada", paso_excel=2)
frame.locator("button").filter(has_text=re.compile(r"Anular facturas", re.I)).click()
app.wait_for_timeout(1000)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(1500)
cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=5000)
app.wait_for_timeout(500)
frame.get_by_text("Refacturaciones", exact=True).click()
app.wait_for_timeout(1500)
capturar_paso(app, "refacturacion_sin_consumo_antiguo", paso_excel=4)
fila_refac = frame.locator("tbody tr").filter(has_text=fecha_propia)
assert fila_refac.count() >= 1, f"Se esperaba ver la refacturacion para la fecha {fecha_propia}"
kwh_refac = fila_refac.first.locator("td").nth(6).inner_text().strip()
assert kwh_refac in ("0.00", "0"), (
    f"El consumo fisico de mas de 12 meses de antiguedad ({kwh_original}) NO deberia "
    f"incluirse en la refacturacion (Kwh FP deberia ser 0.00), se vio: {kwh_refac!r}"
)
'''

# --- RF-07 "Consulta de Movimientos de Saldos" (CP037-CP041; CP042/043
# bloqueados) - bodies reales, verificados en vivo el 26/09/2026 (ver
# _exploracion/explore_34..35_rf07_*.py). Primer RF de un sistema DISTINTO
# ("Cuadratura de Saldos") - confirma que el gotcha "boton/campo REAL mas
# permisivo de lo que describe la matriz" no es exclusivo de la familia
# "Retiro y Castigo de Clientes": CP039/040 (fecha Desde/Hasta vacia) NO
# disparan ningun mensaje, la consulta simplemente corre con "Sin
# registros" - se adaptan igual que CP023/RF-04 y CP027/RF-05. CP041 (rango
# invertido) SI dio el mensaje exacto de la matriz.

CUERPOS_REALES["CP037"] = '''
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
llenar_fecha_movimientos(app, frame, 0, "01/01/2020")
llenar_fecha_movimientos(app, frame, 1, "26/09/2026")
capturar_paso(app, "fechas_completadas", paso_excel=2)
# Estado "Activo" (nzvalue="A") ya viene marcado por defecto.
consultar_movimientos(app, frame)
mensaje_error = cerrar_dialogo_movimientos(app, frame)
assert mensaje_error is None, f"No se esperaba rechazo para un rango de fechas valido: {mensaje_error!r}"
texto = frame.locator("body").inner_text()
assert "resumen de movimientos" in texto.lower(), "Se esperaba ver la seccion Resumen de Movimientos cargada"
capturar_paso(app, "resumen_cargado", paso_excel=4)
'''

CUERPOS_REALES["CP038"] = '''
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
llenar_fecha_movimientos(app, frame, 0, "01/01/2020")
llenar_fecha_movimientos(app, frame, 1, "26/09/2026")
frame.locator('label[nzvalue="R"]').click()  # Estado Retirado
capturar_paso(app, "estado_retirado_seleccionado", paso_excel=1)
consultar_movimientos(app, frame)
mensaje_error = cerrar_dialogo_movimientos(app, frame)
assert mensaje_error is None, f"No se esperaba rechazo para un rango de fechas valido: {mensaje_error!r}"
texto = frame.locator("body").inner_text()
assert "resumen de movimientos" in texto.lower(), "Se esperaba ver la seccion Resumen de Movimientos cargada"
capturar_paso(app, "resumen_cargado", paso_excel=3)
'''

CUERPOS_REALES["CP039"] = '''
# La matriz describe "Debe ingresar fecha de inicio." al dejar Desde vacio
# - confirmado en vivo el 26/09/2026 que la pantalla real NO valida esto:
# la consulta corre igual y devuelve "Sin registros" sin ningun mensaje.
# Se adapta a verificar ese comportamiento real (mismo criterio que
# CP023/RF-04 y CP027/RF-05: la app es mas permisiva que lo descrito).
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
llenar_fecha_movimientos(app, frame, 1, "26/09/2026")  # solo Hasta, Desde queda vacio
capturar_paso(app, "solo_hasta_completado", paso_excel=1)
consultar_movimientos(app, frame)
mensaje_error = cerrar_dialogo_movimientos(app, frame)
capturar_paso(app, "resultado_sin_validacion_de_desde", paso_excel=3)
assert mensaje_error is None, f"La pantalla real no valida Desde vacio (confirmado en vivo) - no se esperaba dialogo: {mensaje_error!r}"
'''

CUERPOS_REALES["CP040"] = '''
# Mismo hallazgo que CP039 pero con Hasta vacio - la matriz describe "Debe
# ingresar fecha de termino." pero la pantalla real tampoco lo valida.
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
llenar_fecha_movimientos(app, frame, 0, "01/01/2020")  # solo Desde, Hasta queda vacio
capturar_paso(app, "solo_desde_completado", paso_excel=1)
consultar_movimientos(app, frame)
mensaje_error = cerrar_dialogo_movimientos(app, frame)
capturar_paso(app, "resultado_sin_validacion_de_hasta", paso_excel=2)
assert mensaje_error is None, f"La pantalla real no valida Hasta vacio (confirmado en vivo) - no se esperaba dialogo: {mensaje_error!r}"
'''

CUERPOS_REALES["CP041"] = '''
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
llenar_fecha_movimientos(app, frame, 0, "01/01/2021")
llenar_fecha_movimientos(app, frame, 1, "01/01/2020")  # Hasta ANTERIOR a Desde
capturar_paso(app, "rango_invertido_completado", paso_excel=1)
consultar_movimientos(app, frame)
mensaje_error = cerrar_dialogo_movimientos(app, frame)
assert mensaje_error is not None and "no debe ser mayor" in mensaje_error.lower(), f"No se vio el rechazo esperado: {mensaje_error!r}"
capturar_paso(app, "resultado_rechazado", paso_excel=3)
'''

# RF-07 CP042/CP043: el usuario corrio el INSERT de la matriz en
# cuadra_saldo el 26/09/2026 (sucursal '0001', sector 1, zona 1, saldo
# 1000, intereses 10, moras 5, tipo 'CP', fecha_movimiento=hoy) -
# confirmado en vivo que la fila aparece en "Resumen de Movimientos" con
# esos valores exactos (`_exploracion/explore_54..55_rf07_*.py`). Al
# hacer click en la fila del resumen, "Detalle" carga una fila con
# sucursal/sector/zona = 0001/1/1 (coincide con el INSERT). El boton
# "Copiar" (hay 2: uno para Resumen, otro para Detalle) copia al
# portapapeles un TSV con headers - confirmado leyendo
# navigator.clipboard.readText() tras concederle permisos al contexto.

CUERPOS_REALES["CP042"] = '''
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
consultar_movimientos(app, frame)
capturar_paso(app, "resumen_cargado_con_dato_insertado", paso_excel=1)

filas_resumen = frame.locator("table.g").first.locator("tbody tr")
assert filas_resumen.count() >= 1, "Se esperaba al menos 1 fila en el Resumen (dato insertado en cuadra_saldo)"
filas_resumen.first.click()
app.wait_for_timeout(1500)
capturar_paso(app, "detalle_de_la_fila_seleccionada", paso_excel=2)

filas_detalle = frame.locator("table.g").nth(1).locator("tbody tr")
assert filas_detalle.count() >= 1, "Se esperaba que el Detalle cargue al menos 1 fila para el resumen seleccionado"
texto_detalle = filas_detalle.first.inner_text()
assert "0001" in texto_detalle, f"Se esperaba ver la sucursal '0001' insertada en el Detalle: {texto_detalle!r}"
capturar_paso(app, "detalle_con_sucursal_insertada", paso_excel=4)
'''

CUERPOS_REALES["CP043"] = '''
app, frame = abrir_consulta_movimientos_saldos(page, paso_excel=1)
consultar_movimientos(app, frame)
capturar_paso(app, "resumen_cargado_con_dato_insertado", paso_excel=1)

filas_resumen = frame.locator("table.g").first.locator("tbody tr")
assert filas_resumen.count() >= 1, "Se esperaba al menos 1 fila en el Resumen (dato insertado en cuadra_saldo)"
filas_resumen.first.click()
app.wait_for_timeout(1500)

context.grant_permissions(["clipboard-read", "clipboard-write"])
botones_copiar = frame.get_by_role("button", name=re.compile(r"Copiar"))
assert botones_copiar.count() >= 2, f"Se esperaban 2 botones 'Copiar' (Resumen y Detalle), se encontraron {botones_copiar.count()}"

botones_copiar.first.click()
app.wait_for_timeout(500)
portapapeles_resumen = app.evaluate("navigator.clipboard.readText()")
capturar_paso(app, "resumen_copiado", paso_excel=2)
assert "1000.00" in portapapeles_resumen and "CP" in portapapeles_resumen, (
    f"El portapapeles deberia contener los datos del Resumen copiado: {portapapeles_resumen!r}"
)

botones_copiar.nth(1).click()
app.wait_for_timeout(500)
portapapeles_detalle = app.evaluate("navigator.clipboard.readText()")
capturar_paso(app, "detalle_copiado", paso_excel=2)
assert "0001" in portapapeles_detalle and "1000.00" in portapapeles_detalle, (
    f"El portapapeles deberia contener los datos del Detalle copiado: {portapapeles_detalle!r}"
)
'''

# --- RF-08 "Listados de Facilidad de Pago por Deuda de Energia" (CP046,
# CP047, CP048; CP044/045/049 bloqueados) - bodies reales, verificados en
# vivo el 26/09/2026 (ver _exploracion/explore_36..37_rf08_*.py).

CUERPOS_REALES["CP046"] = '''
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
assert campo_fecha.input_value() == "", "Se esperaba el campo Fecha vacio al abrir la pantalla"
capturar_paso(app, "fecha_en_blanco", paso_excel=1)
generar_informe_facilidades(app, frame)
capturar_paso(app, "tras_generar", paso_excel=2)
valor_fecha = campo_fecha.input_value()
assert valor_fecha, "Se esperaba que el campo Fecha se complete solo con la fecha actual"
capturar_paso(app, "fecha_actual_usada", paso_excel=3)
'''

CUERPOS_REALES["CP047"] = '''
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
# "Vigentes" ya viene marcado por defecto; sin convenios reales cargados en
# este ambiente, cualquier filtro da "sin registros" - exactamente el
# escenario que pide este caso.
capturar_paso(app, "filtro_sin_resultados", paso_excel=1)
generar_informe_facilidades(app, frame)
app.wait_for_timeout(500)
mensaje = frame.locator("body").inner_text()
assert "no existen registros para el requerimiento" in mensaje.lower(), f"No se vio el mensaje esperado: {mensaje[-400:]}"
capturar_paso(app, "mensaje_sin_registros", paso_excel=3)
'''

CUERPOS_REALES["CP048"] = '''
# La matriz describe "ingresar fecha futura y ver que el sistema la
# rechaza" - confirmado en vivo el 26/09/2026 que el campo Fecha se
# defiende de esto: revierte SOLO a la fecha de hoy al perder foco, igual
# que con un valor vacio (mismo patron que CP023/RF-04, CP027/RF-05,
# CP039-040/RF-07). Se adapta a verificar esa defensa.
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
campo_fecha.click()
app.wait_for_timeout(300)
campo_fecha.fill("31/12/2030")
frame.locator("body").press("Enter")
app.wait_for_timeout(300)
frame.locator("body").press("Escape")
app.wait_for_timeout(500)
capturar_paso(app, "fecha_futura_ingresada", paso_excel=1)
valor_final = campo_fecha.input_value()
assert "2030" not in valor_final, f"Se esperaba que el campo Fecha revierta la fecha futura, quedo en {valor_final!r}"
capturar_paso(app, "fecha_futura_revertida", paso_excel=2)
'''

# RF-08 CP045/CP049: el usuario corrio el INSERT de la matriz en `conve`
# el 26/09/2026 (cliente 1259207, corr_convenio 2, estado 'C', fecha_termino
# 03/03/2026 - con 2 columnas de la matriz corregidas por no existir en el
# esquema real: tasa_fija/id_tasa_convenio no existen, se omitieron; y las
# fechas literales via MDY() en vez de string, por error de conversion de
# formato). Confirmado en vivo (`_exploracion/explore_56_rf08_datos_insertados.py`)
# que "Cancelados y Revocados" con fecha de corte 03/03/2026 SI encuentra el
# convenio: mensaje "Listado generado." + descarga real
# "InformeConveniosDeuda_20260303.xlsx".

CUERPOS_REALES["CP044"] = '''
# RESUELTO 16/10/2026: NO era falta de dato ni regla de negocio - era el
# mismo bug de nz-date-picker que CP050/051 de RF-09 (fill() no actualiza
# el FormControl real). Con fecha de corte 10/07/2026 (en vez de la fecha
# de insercion 26/09/2026 que se probo originalmente en IT1) via clic real
# en el calendario, el convenio Vigente del cliente 1259207 SI aparece.
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
# "Vigentes" ya viene marcado por defecto (no hace falta click).
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
seleccionar_fecha_calendario(app, frame, campo_fecha, 10, 7, 2026)
frame.locator("body").click()
app.wait_for_timeout(500)
capturar_paso(app, "vigentes_fecha_corte_completada", paso_excel=3)

with app.expect_download(timeout=15000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
app.wait_for_timeout(800)
mensaje = frame.locator("body").inner_text()
assert "listado generado" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-300:]!r}"
capturar_paso(app, "listado_generado", paso_excel=4)
'''

CUERPOS_REALES["CP045"] = '''
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
frame.get_by_text(re.compile("Cancelados", re.I)).click()
app.wait_for_timeout(400)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
campo_fecha.click()
app.wait_for_timeout(300)
campo_fecha.fill("03/03/2026")  # coincide con fecha_termino del convenio insertado (corr_convenio=2, cliente 1259207)
frame.locator("body").press("Enter")
app.wait_for_timeout(300)
frame.locator("body").press("Escape")
app.wait_for_timeout(500)
capturar_paso(app, "cancelados_revocados_fecha_corte_completada", paso_excel=1)

with app.expect_download(timeout=10000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
app.wait_for_timeout(800)
mensaje = frame.locator("body").inner_text()
assert "listado generado" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-300:]!r}"
capturar_paso(app, "listado_generado", paso_excel=3)
assert descarga.suggested_filename.lower().endswith(".xlsx"), (
    f"Se esperaba una descarga XLSX, se obtuvo: {descarga.suggested_filename!r}"
)
'''

CUERPOS_REALES["CP049"] = '''
# Reutiliza el mismo dato insertado para CP045 (cliente 1259207,
# corr_convenio=2, estado Cancelado, fecha_termino 03/03/2026).
app, frame = abrir_listado_facilidades_deuda_energia(page, paso_excel=1)
frame.get_by_text(re.compile("Cancelados", re.I)).click()
app.wait_for_timeout(400)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
campo_fecha.click()
app.wait_for_timeout(300)
campo_fecha.fill("03/03/2026")
frame.locator("body").press("Enter")
app.wait_for_timeout(300)
frame.locator("body").press("Escape")
app.wait_for_timeout(500)
capturar_paso(app, "filtro_valido_con_resultados", paso_excel=1)

with app.expect_download(timeout=10000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
capturar_paso(app, "archivo_descargado", paso_excel=2)

nombre = descarga.suggested_filename
assert nombre.lower().endswith(".xlsx"), f"Se esperaba extension .xlsx, se obtuvo: {nombre!r}"
ruta_local = EVIDENCIA / nombre
descarga.save_as(str(ruta_local))
assert ruta_local.stat().st_size > 0, "El archivo XLSX descargado no deberia estar vacio"
capturar_paso(app, "archivo_xlsx_valido_y_no_vacio", paso_excel=2)
'''

# --- RF-09 "Listados de Ingresos de CNR por Deuda de Servicios" ---
# CORREGIDO 26/09/2026 (tarde): originalmente se documento como
# BLOQUEADO COMPLETO por un supuesto "defecto real de infraestructura"
# (error CORS en el endpoint interno LanzarAplicativoDebug, confirmado
# 2 veces seguidas en la misma sesion). Esa conclusion fue INCORRECTA -
# el usuario reabrio la app horas despues y funcionaba bien; re-verificado
# en vivo 6/6 veces sin ningun error CORS
# (`_exploracion/explore_57..58_*.py`). Era un fallo TRANSITORIO del
# backend, no un defecto permanente. La pantalla real es identica a RF-08
# (radio Vigentes/Cancelados y Revocados + Fecha + "Generar", descarga
# XLSX). CP052/053/054 (sin datos) ya dan OK real; CP050/051/055 siguen
# bloqueados por falta de datos en `fac_cli` (ver mas abajo), NO por el
# CORS.

# CORRECCION 26/09/2026 (tarde): lo de arriba resulto ser un fallo
# TRANSITORIO del backend, NO un defecto permanente de infraestructura -
# el usuario reabrio esta app horas despues y abrio bien; re-verificado
# en vivo 6/6 veces sin ningun error CORS
# (`_exploracion/explore_58_reverificar_rf09_rf10.py`). Pantalla real:
# identica a RF-08 (radio Vigentes/Cancelados y Revocados + Fecha +
# "Generar", descarga XLSX directa, banner inline "No existen registros
# para el requerimiento."). Mismo patron defensivo de Fecha que RF-05/
# 07/08 confirmado en vivo (`explore_59_60_rf09_*.py`): fecha en blanco o
# futura terminan usando la fecha de hoy al pulsar "Generar".

CUERPOS_REALES["CP052"] = '''
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
assert campo_fecha.input_value() == "", "Se esperaba el campo Fecha vacio al abrir la pantalla"
capturar_paso(app, "fecha_en_blanco", paso_excel=1)
generar_informe_cnr(app, frame)
capturar_paso(app, "tras_generar", paso_excel=2)
valor_fecha = campo_fecha.input_value()
assert valor_fecha, "Se esperaba que el campo Fecha se complete solo con la fecha actual"
capturar_paso(app, "fecha_actual_usada", paso_excel=3)
'''

CUERPOS_REALES["CP053"] = '''
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
# "Vigentes" ya viene marcado por defecto; sin facilidades reales cargadas
# en este ambiente, cualquier filtro da "sin registros" - exactamente el
# escenario que pide este caso.
capturar_paso(app, "filtro_sin_resultados", paso_excel=1)
generar_informe_cnr(app, frame)
app.wait_for_timeout(500)
mensaje = frame.locator("body").inner_text()
assert "no existen registros para el requerimiento" in mensaje.lower(), f"No se vio el mensaje esperado: {mensaje[-400:]}"
capturar_paso(app, "mensaje_sin_registros", paso_excel=3)
'''

CUERPOS_REALES["CP054"] = '''
# La matriz describe "ingresar fecha futura y ver que el sistema la
# rechaza" - confirmado en vivo el 26/09/2026 que el campo Fecha se
# defiende de esto: revierte a la fecha de hoy al pulsar "Generar" (mismo
# patron que CP023/RF-04, CP027/RF-05, CP039-040/RF-07, CP046-048/RF-08).
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
campo_fecha.click()
app.wait_for_timeout(300)
campo_fecha.fill("31/12/2030")
frame.locator("body").press("Enter")
app.wait_for_timeout(300)
frame.locator("body").press("Escape")
app.wait_for_timeout(500)
capturar_paso(app, "fecha_futura_ingresada", paso_excel=1)
generar_informe_cnr(app, frame)
valor_final = campo_fecha.input_value()
assert "2030" not in valor_final, f"Se esperaba que el campo Fecha revierta la fecha futura, quedo en {valor_final!r}"
capturar_paso(app, "fecha_futura_revertida", paso_excel=2)
'''

_MOTIVO_BLOQUEO_RF09 = (
    "necesita una facilidad real en la tabla fac_cli para el cliente "
    "1259207 (Vigente) o clientes 4/2292893 (Cancelado/Revocado) - sin "
    "datos seeded, 'Generar' siempre da 'No existen registros para el "
    "requerimiento.' La propia matriz trae el INSERT (validado en "
    "Desarrollo 17/09/2026, ver columna precond de CP050/CP051 en "
    "matriz_casos.json) pero OJO: el INSERT analogo de RF-08 (tabla "
    "conve) tenia 2 columnas que no existen en el esquema real de este "
    "ambiente (tasa_fija/id_tasa_convenio) y fechas literales que dieron "
    "error de conversion - verificar el esquema REAL de fac_cli primero "
    "(SELECT * FROM fac_cli WHERE 1=0) antes de correr el INSERT tal "
    "cual. Bloqueado 26/09/2026, ver memoria del proyecto PR000349-SP1 "
    "(seccion RF-09)."
)

CUERPOS_REALES["CP050"] = '''
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
# "Vigentes" ya viene marcado por defecto (no hace falta click).
# OJO: este campo es un nz-date-picker (ant-design) - fill() deja el
# input visualmente bien pero el FormControl real queda vacio, dando
# "No existen registros" pese a que el dato SI existe (confirmado en
# vivo 16/10/2026, mismo sintoma que CP042 de PR000349-SP7). Usar
# seleccionar_fecha_calendario (clic real en el calendario), nunca fill().
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
seleccionar_fecha_calendario(app, frame, campo_fecha, 10, 7, 2026)  # coincide con fecha_creacion/fecha_prim_factura de la facilidad insertada (cliente 1259207, codigo CNR, estado V)
frame.locator("body").click()
app.wait_for_timeout(500)
capturar_paso(app, "vigentes_fecha_corte_completada", paso_excel=3)

with app.expect_download(timeout=10000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
app.wait_for_timeout(800)
mensaje = frame.locator("body").inner_text()
assert "listado generado" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-300:]!r}"
capturar_paso(app, "listado_generado", paso_excel=4)
'''

CUERPOS_REALES["CP051"] = '''
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
frame.get_by_text(re.compile("Cancelados", re.I)).click()
app.wait_for_timeout(400)
# nz-date-picker: usar seleccionar_fecha_calendario (clic real), fill()
# deja el FormControl vacio aunque el input se vea bien (ver CP050).
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
seleccionar_fecha_calendario(app, frame, campo_fecha, 30, 4, 2025)  # coincide con fecha_termino de la facilidad Cancelada insertada (cliente 4)
frame.locator("body").click()
app.wait_for_timeout(500)
capturar_paso(app, "cancelados_revocados_fecha_corte_completada", paso_excel=2)

with app.expect_download(timeout=15000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
app.wait_for_timeout(800)
mensaje = frame.locator("body").inner_text()
assert "listado generado" in mensaje.lower(), f"No se vio el mensaje de exito esperado: {mensaje[-300:]!r}"
capturar_paso(app, "listado_generado", paso_excel=4)
'''

CUERPOS_REALES["CP055"] = '''
# Reutiliza el dato de CP050 (cliente 1259207, facilidad CNR Vigente,
# fecha_creacion/fecha_prim_factura 10/07/2026).
app, frame = abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=1)
campo_fecha = frame.locator('input[placeholder="Seleccionar fecha"]')
seleccionar_fecha_calendario(app, frame, campo_fecha, 10, 7, 2026)
frame.locator("body").click()
app.wait_for_timeout(500)
capturar_paso(app, "filtro_valido_con_resultados", paso_excel=1)

with app.expect_download(timeout=15000) as info_descarga:
    frame.locator("button", has_text=re.compile(r"Generar")).click()
descarga = info_descarga.value
capturar_paso(app, "archivo_descargado", paso_excel=2)

nombre = descarga.suggested_filename
assert nombre.lower().endswith(".xlsx"), f"Se esperaba extension .xlsx, se obtuvo: {nombre!r}"
ruta_local = EVIDENCIA / nombre
descarga.save_as(str(ruta_local))
assert ruta_local.stat().st_size > 0, "El archivo XLSX descargado no deberia estar vacio"
assert zipfile.is_zipfile(ruta_local), "El archivo XLSX descargado deberia ser un ZIP valido (no corrupto)"
with zipfile.ZipFile(ruta_local) as z:
    assert z.testzip() is None, "El archivo XLSX descargado tiene contenido corrupto"
capturar_paso(app, "archivo_xlsx_valido_y_no_vacio", paso_excel=2)
'''

# RF-10 "Aprobacion de Informes Dwh" (CP056-CP061): el fallo CORS
# documentado antes result0 ser TRANSITORIO (ver correccion mas arriba,
# seccion RF-09) - re-verificado en vivo 26/09/2026 (tarde), la app abre
# perfecto de forma consistente. Bodies reales confirmados con
# _exploracion/explore_61..64_rf10_*.py, usando el informe "Liquidacion
# de IGV" (LIQUID, 171 aprobaciones historicas reales 2000-2014) para no
# tocar el informe "Ventas" (el mas usado). Periodo Junio/2026 usado para
# CP058/059/061 (lejos de cualquier dato historico existente, sin riesgo
# de choque); se aprueba en CP058 y se revoca de vuelta en CP061, dejando
# el ambiente igual a como estaba.

CUERPOS_REALES["CP056"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

selects = frame.locator("select")
opciones_informe = selects.nth(0).locator("option").all_inner_texts()
assert len([o for o in opciones_informe if o.strip() and "Seleccione" not in o]) >= 1, (
    f"El combo de informes deberia mostrar al menos 1 informe asignado, opciones: {opciones_informe}"
)
capturar_paso(app, "combo_informes_visible", paso_excel=2)

selects.nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
badge_periodo = frame.locator(".badge-periodo")
assert badge_periodo.count() == 1 and badge_periodo.inner_text().strip() == "Mensual", (
    f"Se esperaba ver el control de periodo 'Mensual' al elegir un informe: {badge_periodo.inner_text() if badge_periodo.count() else None!r}"
)
capturar_paso(app, "periodicidad_mostrada_al_elegir_informe", paso_excel=4)
'''

CUERPOS_REALES["CP057"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
frame.locator("select").nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
capturar_paso(app, "informe_seleccionado", paso_excel=1)

leer_aprobaciones(app, frame)
capturar_paso(app, "grilla_de_aprobaciones", paso_excel=2)
filas = frame.locator("table.g").first.locator("tbody tr")
n = filas.count()
assert n > 0, "Se esperaba al menos 1 aprobacion registrada en el historial real de Liquidacion de IGV"

anios = []
for i in range(min(10, n)):
    celdas = filas.nth(i).locator("td")
    anios.append(int(celdas.nth(1).inner_text().strip()))
assert anios == sorted(anios, reverse=True), (
    f"La grilla deberia estar ordenada por fecha descendente (anios de las primeras filas): {anios}"
)
capturar_paso(app, "orden_descendente_confirmado", paso_excel=3)
'''

CUERPOS_REALES["CP058"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
frame.locator("select").nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
leer_aprobaciones(app, frame)
filas_antes = frame.locator("table.g").first.locator("tbody tr").count()

frame.locator("select").nth(1).select_option("6")  # Junio
frame.locator('input[maxlength="4"]').fill("2026")
capturar_paso(app, "periodo_junio_2026_seleccionado", paso_excel=1)

frame.get_by_role("button", name=re.compile("Aprobar")).click()
app.wait_for_timeout(800)
texto_confirmacion = confirmar_dialogo_aprobacion(app, frame)
assert texto_confirmacion and "aprobar" in texto_confirmacion.lower(), (
    f"Se esperaba dialogo de confirmacion al aprobar, se obtuvo: {texto_confirmacion!r}"
)
app.wait_for_timeout(1000)
capturar_paso(app, "informe_aprobado", paso_excel=2)

leer_aprobaciones(app, frame)
filas_despues = frame.locator("table.g").first.locator("tbody tr")
assert filas_despues.count() == filas_antes + 1, (
    f"Se esperaba una aprobacion mas tras aprobar ({filas_antes} -> {filas_despues.count()})"
)
primera_fila = filas_despues.first.inner_text()
assert "Junio" in primera_fila and "2026" in primera_fila, (
    f"La nueva aprobacion (Junio/2026) deberia aparecer primero (orden descendente): {primera_fila!r}"
)
capturar_paso(app, "nueva_aprobacion_en_la_grilla", paso_excel=3)

# limpieza: revocar la aprobacion de prueba para dejar el ambiente igual
filas_despues.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile("Revocar")).click()
app.wait_for_timeout(600)
confirmar_dialogo_aprobacion(app, frame)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP059"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
frame.locator("select").nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
leer_aprobaciones(app, frame)
filas_antes = frame.locator("table.g").first.locator("tbody tr").count()

frame.locator("select").nth(1).select_option("6")  # Junio
frame.locator('input[maxlength="4"]').fill("2027")  # anio distinto a CP058, para no chocar
capturar_paso(app, "periodo_seleccionado", paso_excel=1)

frame.get_by_role("button", name=re.compile("Aprobar")).click()
app.wait_for_timeout(800)
dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
assert dialogo.count() > 0 and dialogo.first.is_visible(), "Se esperaba el dialogo de confirmacion antes de cancelar"
capturar_paso(app, "dialogo_confirmacion_visible", paso_excel=2)
dialogo.first.get_by_role("button", name=re.compile("Cancelar", re.I)).first.click()
app.wait_for_timeout(800)
capturar_paso(app, "confirmacion_cancelada", paso_excel=3)

leer_aprobaciones(app, frame)
filas_despues = frame.locator("table.g").first.locator("tbody tr").count()
assert filas_despues == filas_antes, (
    f"No deberia haberse registrado ninguna aprobacion nueva al cancelar ({filas_antes} -> {filas_despues})"
)
capturar_paso(app, "grilla_sin_cambios", paso_excel=4)
'''

CUERPOS_REALES["CP060"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
frame.locator("select").nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
leer_aprobaciones(app, frame)
capturar_paso(app, "grilla_cargada_sin_seleccion", paso_excel=1)

frame.get_by_role("button", name=re.compile("Revocar")).click(force=True)
app.wait_for_timeout(800)
dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
assert dialogo.count() > 0 and dialogo.first.is_visible(), "Se esperaba un dialogo de aviso al revocar sin seleccion"
texto_dialogo = dialogo.first.inner_text()
assert "debe seleccionar el informe" in texto_dialogo.lower(), (
    f"No se vio el mensaje esperado: {texto_dialogo!r}"
)
capturar_paso(app, "mensaje_debe_seleccionar", paso_excel=3)
dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP061"] = '''
app, frame = abrir_aprobacion_informes_dwh(page, paso_excel=1)
frame.locator("select").nth(0).select_option("LIQUID")
app.wait_for_timeout(600)
leer_aprobaciones(app, frame)

# se registra una aprobacion de prueba propia para poder revocarla (no se
# toca ninguna aprobacion real historica)
frame.locator("select").nth(1).select_option("7")  # Julio
frame.locator('input[maxlength="4"]').fill("2026")
frame.get_by_role("button", name=re.compile("Aprobar")).click()
app.wait_for_timeout(800)
confirmar_dialogo_aprobacion(app, frame)
app.wait_for_timeout(1000)
leer_aprobaciones(app, frame)
capturar_paso(app, "aprobacion_de_prueba_creada", paso_excel=1)

filas = frame.locator("table.g").first.locator("tbody tr")
fila_prueba = filas.first
assert "Julio" in fila_prueba.inner_text() and "2026" in fila_prueba.inner_text(), (
    "La aprobacion de prueba (Julio/2026) deberia estar primera en la grilla"
)
fila_prueba.click()
app.wait_for_timeout(400)
capturar_paso(app, "fila_seleccionada", paso_excel=1)

frame.get_by_role("button", name=re.compile("Revocar")).click()
app.wait_for_timeout(800)
dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
assert dialogo.count() > 0 and dialogo.first.is_visible(), "Se esperaba el dialogo de confirmacion antes de revocar"
texto_confirmacion = dialogo.first.inner_text()
capturar_paso(app, "dialogo_confirmacion_revocar", paso_excel=3)
dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
app.wait_for_timeout(1000)

leer_aprobaciones(app, frame)
primera_fila_final = frame.locator("table.g").first.locator("tbody tr").first.inner_text()
assert not ("Julio" in primera_fila_final and "2026" in primera_fila_final), (
    f"La fila revocada no deberia seguir apareciendo primera: {primera_fila_final!r}"
)
capturar_paso(app, "fila_eliminada_de_la_grilla", paso_excel=4)
'''

# RF-11 "Mantenimiento de Informes Dwh" (CP062-CP068): pantalla propia,
# CONFIRMADA en vivo el 26/09/2026 (explore_42..49). A diferencia de RF-09/
# RF-10, aqui la app abre perfecto (sin CORS). Se uso el informe
# "Liquidacion de IGV" / agrupacion "Cargos" para las pruebas de
# escritura (Crear/Modificar/Eliminar/Reordenar/Asignar elemento) porque
# tiene pocos grupos (25) y no es el informe mas usado en produccion
# ("Informe de Ventas"); todo grupo de prueba creado se elimino al final
# de cada caso para dejar el ambiente limpio (confirmado con un Leer
# posterior mostrando la grilla original de 25 filas).

CUERPOS_REALES["CP062"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

# Informe de Ventas tiene 6 agrupaciones activas configuradas. El boton
# "Leer" exige AMBOS combos (Informe y Agrupacion) elegidos - aqui solo
# interesa el recalculo del combo Agrupacion al elegir el Informe, no
# llegar a pulsar Leer.
frame.locator("select").nth(0).select_option("VENTAS")
app.wait_for_timeout(500)
capturar_paso(app, "informe_ventas_seleccionado", paso_excel=2)
opciones_ventas = frame.locator("select").nth(1).locator("option").all_inner_texts()
assert len([o for o in opciones_ventas if o.strip() and "Seleccione" not in o]) >= 1, (
    f"El combo de agrupaciones deberia mostrar solo las activas del informe, opciones: {opciones_ventas}"
)

# Contraprueba: Morosidad Semanal no tiene NINGUNA agrupacion configurada,
# lo que confirma que el combo refleja agrupaciones reales por informe
# (no una lista fija) - confirmado en vivo (explore_44_rf11_combos_dinamicos.py)
frame.locator("select").nth(0).select_option("MOROSI")
app.wait_for_timeout(500)
opciones_morosi = frame.locator("select").nth(1).locator("option").all_inner_texts()
capturar_paso(app, "informe_morosidad_sin_agrupaciones", paso_excel=3)
assert len([o for o in opciones_morosi if o.strip() and "Seleccione" not in o]) == 0, (
    f"Morosidad Semanal no deberia tener agrupaciones activas, opciones: {opciones_morosi}"
)
'''

CUERPOS_REALES["CP063"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "VENTAS", "CARGO")
capturar_paso(app, "grupos_de_cargos_para_tarifas", paso_excel=2)
filas = frame.locator("table.g").first.locator("tbody tr")
n = filas.count()
assert n > 0, "La grilla deberia mostrar los grupos configurados de la agrupacion"
primera_fila = filas.first.inner_text()
capturar_paso(app, "primer_grupo_de_la_lista", paso_excel=3)
print(f"Primer grupo mostrado: {primera_fila!r}")
'''

CUERPOS_REALES["CP064"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
filas_antes = frame.locator("table.g").first.locator("tbody tr").count()
capturar_paso(app, "grilla_antes_de_crear", paso_excel=1)

frame.get_by_role("button", name=re.compile(r"Nuevo")).click()
app.wait_for_timeout(600)
frame.locator("input[placeholder='Descripción del grupo']").fill("ZZ_AUTOMATION_TEST")
frame.locator("input[type=radio][name=tipoGrupo]").nth(0).check()  # Blanco
capturar_paso(app, "formulario_nuevo_grupo_completado", paso_excel=2)

frame.get_by_role("button", name=re.compile(r"Guardar")).click()
app.wait_for_timeout(800)
texto_confirmacion = confirmar_dialogo_mantenimiento_informes(app, frame)
assert texto_confirmacion and "guardar" in texto_confirmacion.lower(), (
    f"Se esperaba dialogo de confirmacion al guardar, se obtuvo: {texto_confirmacion!r}"
)
app.wait_for_timeout(1000)
capturar_paso(app, "grupo_creado_y_guardado", paso_excel=3)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
filas_despues = frame.locator("table.g").first.locator("tbody tr").count()
assert filas_despues == filas_antes + 1, (
    f"Se esperaba un grupo mas tras crear ({filas_antes} -> {filas_despues})"
)
fila_creada = fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST")
assert fila_creada.count() == 1, "El grupo creado deberia aparecer en la grilla"
capturar_paso(app, "grupo_visible_en_grilla_final", paso_excel=4)

# limpieza: eliminar el grupo de prueba para no dejar datos residuales
fila_creada.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Eliminar")).click()
app.wait_for_timeout(600)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP065"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")

# se crea un grupo de prueba propio (no se toca un grupo real de produccion)
frame.get_by_role("button", name=re.compile(r"Nuevo")).click()
app.wait_for_timeout(600)
frame.locator("input[placeholder='Descripción del grupo']").fill("ZZ_AUTOMATION_TEST")
frame.locator("input[type=radio][name=tipoGrupo]").nth(0).check()
frame.get_by_role("button", name=re.compile(r"Guardar")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
leer_grupos_informe(app, frame, "LIQUID", "CARGO")
capturar_paso(app, "grupo_de_prueba_creado", paso_excel=1)

fila = fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST")
fila.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Modificar")).click()
app.wait_for_timeout(500)
frame.locator("input[placeholder='Descripción del grupo']").fill("ZZ_AUTOMATION_TEST_MOD")
capturar_paso(app, "descripcion_modificada", paso_excel=3)

frame.get_by_role("button", name=re.compile(r"Guardar")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
capturar_paso(app, "tras_guardar", paso_excel=4)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
assert fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST_MOD").count() == 1, (
    "La nueva descripcion deberia reflejarse en la grilla"
)
assert fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST").count() == 0 or \\
       "ZZ_AUTOMATION_TEST_MOD" in frame.locator("table.g").first.locator("tbody").inner_text(), (
    "La descripcion antigua no deberia seguir apareciendo tal cual"
)
capturar_paso(app, "grilla_con_descripcion_actualizada", paso_excel=5)

fila_mod = fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST_MOD")
fila_mod.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Eliminar")).click()
app.wait_for_timeout(600)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP066"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")

frame.get_by_role("button", name=re.compile(r"Nuevo")).click()
app.wait_for_timeout(600)
frame.locator("input[placeholder='Descripción del grupo']").fill("ZZ_AUTOMATION_ELEM")
frame.locator("input[type=radio][name=tipoGrupo]").nth(1).check()  # Elemento
app.wait_for_timeout(400)
capturar_paso(app, "grupo_tipo_elemento_en_edicion", paso_excel=1)

no_seleccionados = frame.locator(".dual-col", has_text="No seleccionados").locator("tbody tr").first
texto_elemento = no_seleccionados.inner_text()
no_seleccionados.click()
app.wait_for_timeout(300)
frame.locator("button[title='Agregar']").click()
app.wait_for_timeout(500)
capturar_paso(app, "elemento_movido_a_seleccionados", paso_excel=2)

seleccionados_texto = frame.locator(".dual-col", has_text="Seleccionados (").first.inner_text()
assert texto_elemento.split("\\t")[0] in seleccionados_texto, (
    "El elemento movido deberia aparecer en la columna de Seleccionados"
)

frame.get_by_role("button", name=re.compile(r"Guardar")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
capturar_paso(app, "grupo_elemento_guardado", paso_excel=3)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
fila = fila_grupo_informe(frame, "ZZ_AUTOMATION_ELEM")
assert fila.count() == 1, "El grupo tipo Elemento deberia quedar registrado en la grilla"
capturar_paso(app, "grupo_visible_en_grilla_final", paso_excel=4)

fila.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Eliminar")).click()
app.wait_for_timeout(600)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP067"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
frame.get_by_role("button", name=re.compile(r"Nuevo")).click()
app.wait_for_timeout(600)
frame.locator("input[placeholder='Descripción del grupo']").fill("ZZ_AUTOMATION_TEST")
frame.locator("input[type=radio][name=tipoGrupo]").nth(0).check()
frame.get_by_role("button", name=re.compile(r"Guardar")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
leer_grupos_informe(app, frame, "LIQUID", "CARGO")
capturar_paso(app, "grupo_de_prueba_creado", paso_excel=1)

fila = fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST")
assert fila.count() == 1
fila.first.click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Eliminar")).click()
app.wait_for_timeout(600)
texto_confirmacion = confirmar_dialogo_mantenimiento_informes(app, frame)
assert texto_confirmacion and "eliminar" in texto_confirmacion.lower(), (
    f"Se esperaba dialogo de confirmacion de eliminacion, se obtuvo: {texto_confirmacion!r}"
)
app.wait_for_timeout(1000)
capturar_paso(app, "tras_confirmar_eliminacion", paso_excel=2)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
assert fila_grupo_informe(frame, "ZZ_AUTOMATION_TEST").count() == 0, (
    "El grupo eliminado no deberia seguir apareciendo en la grilla"
)
capturar_paso(app, "grupo_ya_no_aparece_en_consulta", paso_excel=3)
'''

CUERPOS_REALES["CP068"] = '''
app, frame = abrir_mantenimiento_informes_dwh(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
capturar_paso(app, "orden_original", paso_excel=1)

frame.get_by_role("button", name=re.compile(r"Ordenar")).click()
app.wait_for_timeout(600)
fila_intereses = fila_grupo_informe(frame, "Intereses")
fila_intereses.first.click()
app.wait_for_timeout(300)
frame.get_by_role("button", name=re.compile(r"Subir")).click()
app.wait_for_timeout(400)
capturar_paso(app, "orden_modificado_en_pantalla", paso_excel=2)

frame.get_by_role("button", name=re.compile(r"Guardar Orden")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
capturar_paso(app, "tras_guardar_orden", paso_excel=3)

leer_grupos_informe(app, frame, "LIQUID", "CARGO")
grid_tras_guardar = frame.locator("table.g").first.locator("tbody").inner_text()
posicion_intereses = [l for l in grid_tras_guardar.splitlines() if "Intereses" in l]
posicion_alumbrado = [l for l in grid_tras_guardar.splitlines() if "Alum. Publico" in l]
assert grid_tras_guardar.index(posicion_intereses[0]) < grid_tras_guardar.index(posicion_alumbrado[0]), (
    "Intereses deberia quedar antes que Alum. Publico tras subirlo y guardar el orden"
)
capturar_paso(app, "orden_persistido_al_reconsultar", paso_excel=4)

# se revierte el orden para dejar el ambiente igual a como estaba
frame.get_by_role("button", name=re.compile(r"Ordenar")).click()
app.wait_for_timeout(600)
fila_grupo_informe(frame, "Intereses").first.click()
app.wait_for_timeout(300)
frame.get_by_role("button", name=re.compile(r"Bajar")).click()
app.wait_for_timeout(400)
frame.get_by_role("button", name=re.compile(r"Guardar Orden")).click()
app.wait_for_timeout(800)
confirmar_dialogo_mantenimiento_informes(app, frame)
app.wait_for_timeout(1000)
'''

# RF-12 "Log de Carga de Datawarehouse" (CP069-CP074): el bloqueo de IT1/IT2
# ("la tabla de logs esta vacia" / "el servicio real devuelve [] siempre,
# desalineacion de conexion/base") QUEDO DESCARTADO en IT3 (21/10/2026):
# confirmado en vivo con captura de red que el endpoint real
# POST .../api/log-carga/ConsultarLogCarga SI devuelve datos reales -
# tanto los 176 registros historicos reales (2026, rolInicio='ACTPLA') como
# los 4 nuevos sembrados por el usuario (numero_log 990001-990004,
# rolInicio='QA-AUTO', ver INSERT de la matriz IT3 para CP069 en
# matriz_casos.json). La causa real del "siempre devuelve []" de IT1/IT2
# NO era infraestructura: la pantalla simplemente NO llama al backend si
# se busca con TODOS los filtros vacios (incluidas las fechas) - un
# guard del lado del cliente, confirmado con captura de red (0 llamadas
# a ConsultarLogCarga con filtros vacios vs. 1 llamada real con un rango
# de fechas, aunque sea amplio). Por eso ningun intento anterior (ni con
# datos reales de 2000-2003, ni con un registro nuevo insertado en 2026)
# encontraba nada: SIEMPRE se buscaba sin fechas.
#
# Datos sembrados (numero_log 990001-990004, Proceso=DIFERENCIASDECAJERO,
# ver INSERT completo en matriz_casos.json / CP069):
#   990001 - 20/09/2026, fuente cli, SIN etapas (EnProceso)      -> CP074
#   990002 - 21/09/2026, fuente cli, CON 2 etapas (Finalizada)   -> CP071
#   990003 - 22/09/2026, fuente cli, SIN etapas (mas reciente)   -> CP073
#   990004 - 21/09/2026, fuente sif, SIN etapas (EnProceso)      -> CP069 (fuente SIF)

CUERPOS_REALES["CP069"] = '''
# RE-VERIFICADO EN VIVO 26/10/2026 (PR000349-SP1-IT4): el defecto
# confirmado en IT3 (21/10/2026 - "Buscar" con Proceso/Etapa=(Todos) y
# fechas vacias no disparaba NINGUNA peticion de red, la pantalla
# quedaba colgada) ya NO se reproduce - Desarrollo lo corrigio entre el
# 21 y el 22/10. Confirmado con sonda de red: ahora SI dispara
# ConsultarLogCarga (HTTP 200) y devuelve la grilla paginada real
# (decenas de miles de registros acumulados). Se vuelve al escenario
# LITERAL de la matriz en vez del rodeo que uso IT3.
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
peticiones = []
app.on("response", lambda r: peticiones.append(r.status) if "ConsultarLogCarga" in r.url else None)
capturar_paso(app, "filtros_por_defecto_todos_vacios", paso_excel=2)
buscar_log_carga(app, frame)
app.wait_for_timeout(2000)
assert peticiones and peticiones[-1] == 200, f"Se esperaba que 'Buscar' sin filtros dispare ConsultarLogCarga con HTTP 200: {peticiones!r}"
dialogo_error = frame.locator(".ant-modal, nz-modal-container")
assert dialogo_error.count() == 0 or not dialogo_error.first.is_visible(), "No se esperaba una Ventana de Error al buscar sin filtros"
_, rango = texto_paginador(frame, indice=0)
capturar_paso(app, "resultado_sin_filtros", paso_excel=4)
assert "registros" in rango.lower(), f"Se esperaba ver la barra de paginado con el total de registros: {rango!r}"
# Verificacion adicional (reusa el metodo ya probado en IT3): acotar a
# Proceso=DIFERENCIASDECAJERO + rango de fechas de los sembrados
# QA-AUTO confirma especificamente que la lista integra AMBAS fuentes
# (990004 es de etl_log_carga_sif, el resto de etl_log_carga_cli) - el
# total de 115 mil+ filas sin filtro hace impractico buscar un registro
# puntual ahi dentro.
frame.locator("select").nth(0).select_option(label="DIFERENCIASDECAJERO")
frame.locator("select").nth(1).select_option(label="(Todos)")
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-09-19")
fechas.nth(1).fill("2026-09-23")
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
capturar_paso(app, "ambas_fuentes_integradas_acotado", paso_excel=4)
texto_grilla = frame.locator("table.g").first.inner_text()
for numero in ["990001", "990002", "990003", "990004"]:
    assert numero in texto_grilla, f"Se esperaba ver el registro {numero} (sembrado QA-AUTO) en la grilla integrada: {texto_grilla!r}"
'''

CUERPOS_REALES["CP070"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
frame.locator("select").nth(0).select_option(label="DIFERENCIASDECAJERO")
frame.locator("select").nth(1).select_option(label="Solicitado")
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-09-19")
fechas.nth(1).fill("2026-09-23")
capturar_paso(app, "filtros_especificos", paso_excel=1)
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
capturar_paso(app, "resultado_filtrado", paso_excel=4)
filas = frame.locator("table.g").first.locator("tbody tr")
assert filas.count() == 4, f"Se esperaban exactamente los 4 registros sembrados (990001-990004) con estos filtros, se obtuvieron {filas.count()}"
texto_grilla = frame.locator("table.g").first.inner_text()
for numero in ["990001", "990002", "990003", "990004"]:
    assert numero in texto_grilla, f"Se esperaba ver el registro {numero}: {texto_grilla!r}"
'''

CUERPOS_REALES["CP071"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
frame.locator("select").nth(0).select_option(label="DIFERENCIASDECAJERO")
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-09-19")
fechas.nth(1).fill("2026-09-23")
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
tabla_log = frame.locator("table.g").first
fila_990002 = tabla_log.locator("tbody tr").filter(has_text="990002")
assert fila_990002.count() == 1, f"Se esperaba encontrar el registro 990002 (tiene etapas reales): count={fila_990002.count()}"
fila_990002.first.click()
app.wait_for_timeout(1000)
capturar_paso(app, "detalle_de_etapas", paso_excel=3)
tabla_etapas = frame.locator("table.g").nth(1)
filas_etapas = tabla_etapas.locator("tbody tr")
assert filas_etapas.count() == 2, f"Se esperaban las 2 etapas reales sembradas para 990002: {filas_etapas.count()}"
texto_etapas = tabla_etapas.inner_text()
assert "QA-AUTO" in texto_etapas, f"Se esperaba ver el rol QA-AUTO en las etapas: {texto_etapas!r}"
'''

CUERPOS_REALES["CP072"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

# El input Desde es <input type="date"> NATIVO del navegador - confirmado
# en vivo que rechaza cualquier texto no valido y queda vacio, sin ningun
# dialogo/mensaje (mismo patron defensivo que CP023/CP027/CP046/CP048).
# La matriz espera "Fecha inicial no valida." pero eso no es alcanzable
# via UI real - se adapta a verificar la reversion/rechazo del propio campo.
campo_desde = frame.locator("input[type=date]").nth(0)
campo_desde.click()
page.keyboard.type("13452026")  # dia=13 (invalido para mes), mes=45 (invalido)
app.wait_for_timeout(400)
valor_desde = campo_desde.input_value()
capturar_paso(app, "fecha_invalida_tecleada", paso_excel=1)
assert valor_desde == "", (
    f"El campo Desde deberia rechazar una fecha invalida y quedar vacio, quedo: {valor_desde!r}"
)

peticiones = []
app.on("response", lambda r: peticiones.append(r.status) if "ConsultarLogCarga" in r.url else None)
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
dialogo = frame.locator(".ant-modal, nz-modal-container")
assert dialogo.count() == 0 or not dialogo.first.is_visible(), (
    "No se esperaba ningun dialogo de error: el campo ya rechazo la fecha invalida antes de buscar"
)
# RE-VERIFICADO EN VIVO 26/10/2026 (IT4): desde que se corrigio el bug
# de "Buscar sin filtros" (ver CP069), la busqueda con el campo Desde
# vacio YA NO muestra "Sin registros" - trae la grilla real paginada
# (igual que un "(Todos)" sin restriccion). Se verifica eso en vez del
# texto viejo "sin registros"/"presione", que ya no aplica.
assert peticiones and peticiones[-1] == 200, f"La busqueda deberia correr igual (sin bloquear la pantalla) con el campo Desde vacio: {peticiones!r}"
_, rango = texto_paginador(frame, indice=0)
assert "registros" in rango.lower(), f"Se esperaba ver la grilla con su barra de paginado tras la busqueda: {rango!r}"
capturar_paso(app, "busqueda_corre_sin_bloquear_pantalla", paso_excel=3)
'''

CUERPOS_REALES["CP073"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
frame.locator("select").nth(0).select_option(label="DIFERENCIASDECAJERO")
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-09-19")
fechas.nth(1).fill("2026-09-23")
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
capturar_paso(app, "resultados_ordenados", paso_excel=2)
filas = frame.locator("table.g").first.locator("tbody tr")
assert filas.count() >= 2, f"Se esperaban al menos 2 registros con fechas distintas para verificar el orden: {filas.count()}"
primera_fila = filas.nth(0).inner_text()
assert primera_fila.startswith("990003"), f"El registro mas reciente (990003, 22/09/2026 10:00) deberia aparecer primero: {primera_fila!r}"
'''

CUERPOS_REALES["CP074"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
frame.locator("select").nth(0).select_option(label="DIFERENCIASDECAJERO")
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-09-19")
fechas.nth(1).fill("2026-09-23")
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
tabla_log = frame.locator("table.g").first
fila_990001 = tabla_log.locator("tbody tr").filter(has_text="990001")
assert fila_990001.count() == 1, f"Se esperaba encontrar el registro 990001 (sin etapas, sembrado a proposito): count={fila_990001.count()}"
fila_990001.first.click()
app.wait_for_timeout(1000)
capturar_paso(app, "etapas_vacias", paso_excel=2)
tabla_etapas = frame.locator("table.g").nth(1)
texto_etapas = tabla_etapas.inner_text()
assert "sin etapas" in texto_etapas.lower(), f"La grilla de etapas deberia quedar vacia para un registro sin etapas: {texto_etapas!r}"
'''

# --- RF-12 "Log de Carga de Datawarehouse" (CP075, nuevo en IT4) -
# verificado en vivo 26/10/2026. Confirmado que el componente de
# paginado (<lds-paginador>) NO EXISTIA cuando se cerro CP069-074 en
# IT3 (21/10/2026) - aparecio junto con el fix del bug de "Buscar sin
# filtros" (ver CP069 arriba). El numero real de registros (115000+)
# no coincide con los 849 que la matriz dice haber verificado el
# 22/10/2026 (crece con el tiempo) - se verifica el PATRON (barra con
# rango/total/paginas, navegacion, cambio de tamano de pagina), no el
# numero literal.

CUERPOS_REALES["CP075"] = '''
app, frame = abrir_log_carga_datawarehouse(page, paso_excel=1)
buscar_log_carga(app, frame)
app.wait_for_timeout(1500)
posicion_inicial, rango_inicial = texto_paginador(frame, indice=0)
capturar_paso(app, "pagina_1_rango_inicial", paso_excel=3)
assert re.match(r"P.gina 1 de \\d+", posicion_inicial), f"Se esperaba 'Pagina 1 de N': {posicion_inicial!r}"
assert re.match(r"Mostrando 1.20 de \\d+ registros", rango_inicial), f"Se esperaba 'Mostrando 1-20 de N registros': {rango_inicial!r}"
total_paginas = int(re.search(r"de (\\d+)", posicion_inicial).group(1))
assert total_paginas > 1, f"Se esperaba mas de 1 pagina para probar la navegacion: {posicion_inicial!r}"

posicion_siguiente = click_paginador(app, frame, "P.gina siguiente", indice=0)
assert "gina 2 " in posicion_siguiente, f"Se esperaba pasar a la pagina 2: {posicion_siguiente!r}"
capturar_paso(app, "tras_siguiente", paso_excel=4)

posicion_ultima = click_paginador(app, frame, ".ltima p.gina", indice=0)
assert f"gina {total_paginas} " in posicion_ultima, f"Se esperaba llegar a la ultima pagina ({total_paginas}): {posicion_ultima!r}"
capturar_paso(app, "tras_ultima", paso_excel=4)

posicion_anterior = click_paginador(app, frame, "P.gina anterior", indice=0)
assert f"gina {total_paginas - 1} " in posicion_anterior, f"Se esperaba retroceder 1 pagina desde la ultima: {posicion_anterior!r}"

posicion_primera = click_paginador(app, frame, "Primera p.gina", indice=0)
assert "gina 1 " in posicion_primera, f"Se esperaba volver a la pagina 1: {posicion_primera!r}"
capturar_paso(app, "tras_primera", paso_excel=4)

rango_5 = fijar_registros_por_pagina(app, frame, 5, indice=0)
assert re.match(r"Mostrando 1.5 de \\d+ registros", rango_5), f"Se esperaba 'Mostrando 1-5 de N registros' tras fijar 5 por pagina: {rango_5!r}"
filas_visibles = frame.locator("table.g").first.locator("tbody tr").count()
assert filas_visibles == 5, f"Se esperaban exactamente 5 filas visibles tras fijar 5 registros por pagina: {filas_visibles}"
capturar_paso(app, "5_registros_por_pagina", paso_excel=6)

# Paso 7 de la matriz: repetir la verificacion de la barra en la grilla
# de etapas (indice=1). Sin seleccionar ninguna fila queda vacia
# ("Sin etapas registradas" - CONFIRMADO EN VIVO: en ese estado el
# componente NO renderiza ".lds-pg__texto", solo ".lds-pg__vacio", por
# eso se verifica con una fila real seleccionada). Se usa la fila con
# mas filas visibles (los 5 registros por pagina fijados arriba).
frame.locator("table.g").first.locator("tbody tr").first.click()
app.wait_for_timeout(1200)
paginador_etapas = frame.locator("lds-paginador").nth(1)
assert paginador_etapas.locator(".lds-pg__posicion").count() > 0, "Se esperaba ver tambien el paginador en la grilla de Etapas del Proceso"
posicion_etapas = paginador_etapas.locator(".lds-pg__posicion").inner_text()
assert re.search(r"[Pp].gina", posicion_etapas), f"Se esperaba el formato 'Pagina N de M' tambien en Etapas del Proceso: {posicion_etapas!r}"
capturar_paso(app, "paginador_en_grilla_etapas", paso_excel=7)
'''

# --- Un add() por cada uno de los 75 casos de matriz_casos.json, en orden ---
# TODO: reemplazar cada _BODY_PENDIENTE por el body real (ver PENDIENTES).
for _cp in sorted(MATRIZ, key=lambda x: int(x[2:])):
    _m = MATRIZ[_cp]
    _body = CUERPOS_REALES.get(_cp) or _BODY_PENDIENTE.format(cp=_cp, rf=_m["rf"], name=_m["name"])
    add(_cp, _body)


if __name__ == "__main__":
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
