"""
generate_scripts.py de PR000349-SP2 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: 9 pantallas (RF-01..RF-09), 72 casos (ver matriz_casos.json).
Ver documentos/EF_texto.txt y documentos/ET_texto.txt para el detalle
funcional/tecnico completo de cada RF.

A diferencia de PR000349-SP1 (donde los 12 modulos se escribieron inline
y se migraron a _framework/modulos/ recien al final), ESTE proyecto usa
la arquitectura de modulos (Seccion 0c del checklist) DESDE EL ARRANQUE:
cada pantalla que se explora en vivo se escribe directo como
_framework/modulos/<nombre>.py (ficha tecnica + helpers, sin nada
especifico de este proyecto) y se importa aca.

Estado (27/09/2026): RF-01 "Consulta de Clientes Asociados a una S.S."
explorado en vivo y con bodies reales (CP001-CP008). El resto (RF-02
hasta RF-09) sigue en NotImplementedError - RF-02/03/04/06 ademas estan
BLOQUEADOS por falta de rol funcional en la cuenta de prueba SCASTI_DW
(RELNUCLI, ANDESE, ANDESE1 respectivamente - esas pantallas ni siquiera
aparecen en el menu sin esos roles).
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
import consulta_clientes_ss as modulo_rf01  # noqa: E402
import mantenimiento_orden_conexion as modulo_rf02  # noqa: E402
import consulta_cortes_reconexiones as modulo_rf03  # noqa: E402
import consulta_pagos as modulo_rf05  # noqa: E402
import consulta_solicitudes_reposicion_pendientes as modulo_rf08  # noqa: E402
import consulta_cuadratura_sesion as modulo_rf04  # noqa: E402
import mantenedor_inspectores_corte as modulo_rf06  # noqa: E402
import consulta_cortes_pendientes as modulo_rf07  # noqa: E402
import consulta_generica_reposiciones as modulo_rf09  # noqa: E402

PROYECTO = "PR000349-SP2"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


def fuente_modulo(modulo, saltar=("PWTimeoutError",)):
    """Extrae el codigo fuente de un modulo de _framework/modulos/ (su
    docstring + todas sus funciones) para volcarlo como texto en el
    CPxxx.py generado. Ver PR000349-SP1/generate_scripts.py (misma
    funcion, ya usada y corregida ahi) y NUEVO_PROYECTO_CHECKLIST.md
    Seccion 0c. `saltar` son nombres importados por el modulo que ya
    vienen de otro lado en el header del CPxxx.py."""
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
    # venir DOBLADA para sobrevivir ese .format() como llave literal en
    # el CPxxx.py final. Ver el bug real que esto evita en PR000349-SP1
    # (memoria: project_modulos_por_aplicativo).
    return fuente.replace("{", "{{").replace("}", "}}")


HELPERS_MODULOS = "\n\n\n".join(
    fuente_modulo(m) for m in (
        modulo_rf01, modulo_rf02, modulo_rf03, modulo_rf04, modulo_rf05, modulo_rf06, modulo_rf07, modulo_rf08, modulo_rf09,
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

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = {usuario_repr}
PASSWORD = {password_repr}

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
            login(page)
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
                rutas_videos.extend(sorted(EVIDENCIA.glob("page@*.webm")))
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


def add(cp, body, usuario="SCASTI_DW", password="Melquisedec_01"):
    m = MATRIZ[cp]
    CASES.append(dict(
        cp=cp, rf=m["rf"], cu=m["cu"], name=m["name"], desc=m["desc"],
        precond=m["precond"], datos=m["datos"], esperado=m["esperado"],
        pasos=m["pasos"], body=body, usuario=usuario, password=password,
    ))


def _body_pendiente(cp, rf, name):
    # Algunos nombres de caso traen comillas dobles literales (ej. 'Cambio
    # a Tipo de Corte "Verificaciones"') - usar repr() en vez de interpolar
    # el texto crudo dentro de un string ya entrecomillado, para que el
    # .py generado siga siendo sintacticamente valido sin importar el
    # contenido exacto del nombre.
    mensaje = f"{cp} ({rf} - {name}): falta escribir el body real - falta exploracion en vivo."
    return f"raise NotImplementedError({mensaje!r})"

# RF-01 "Consulta de Clientes Asociados a una S.S." (CP001-CP008) - bodies
# reales, confirmados en vivo el 27/09/2026 (ver
# _exploracion/explore_04..07_rf01_*.py). Cliente/S.S. reales dados por el
# usuario: S.S. 541, correlativo 1 -> cliente 1201729 (unico asociado).

CUERPOS_REALES = {}

CUERPOS_REALES["CP001"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)
boton_imprimir = frame.get_by_role("button", name=re.compile("Imprimir"))
assert boton_imprimir.get_attribute("disabled") is not None, "Imprimir deberia estar deshabilitado al abrir la pantalla"
filas = filas_clientes_ss(frame)
assert filas.count() == 0, "La grilla deberia estar vacia al abrir la pantalla, sin busqueda automatica"
capturar_paso(app, "imprimir_deshabilitado_grilla_vacia", paso_excel=1)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
leer_clientes_ss(app, frame, numero_ss="541")
capturar_paso(app, "resultado_ss_541", paso_excel=3)
filas = filas_clientes_ss(frame)
assert filas.count() == 1, f"Se esperaba 1 cliente asociado a la S.S. 541, se obtuvieron {filas.count()}"
texto = frame.locator("body").inner_text()
assert "1201729" in texto, f"Se esperaba ver el cliente 1201729 en el resultado: {texto[-300:]!r}"
assert "Clientes asociados a la SS. 541:" in texto, f"No se vio el total esperado: {texto[-300:]!r}"
capturar_paso(app, "total_mostrado", paso_excel=4)
'''

CUERPOS_REALES["CP003"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(800)
capturar_paso(app, "leer_sin_ss", paso_excel=1)
texto_dialogo = cerrar_ventana_validacion(app, frame)
assert texto_dialogo and "ingrese n" in texto_dialogo.lower() and "s.s." in texto_dialogo.lower(), (
    f"No se vio el mensaje esperado 'Ingrese N.° de S.S.': {texto_dialogo!r}"
)
capturar_paso(app, "mensaje_ss_obligatorio", paso_excel=1)
'''

CUERPOS_REALES["CP004"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
leer_clientes_ss(app, frame, numero_ss="541", correlativo="99")
capturar_paso(app, "busqueda_con_correlativo_inexistente", paso_excel=1)
texto_dialogo = cerrar_ventana_validacion(app, frame)
assert texto_dialogo and "no encontrados" in texto_dialogo.lower(), (
    f"No se vio el mensaje esperado 'N.° de SS y Correlativo no encontrados.': {texto_dialogo!r}"
)
capturar_paso(app, "mensaje_sin_resultados_con_correlativo", paso_excel=1)
'''

CUERPOS_REALES["CP005"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
leer_clientes_ss(app, frame, numero_ss="999999")
capturar_paso(app, "busqueda_ss_inexistente", paso_excel=1)
texto_dialogo = cerrar_ventana_validacion(app, frame)
assert texto_dialogo and "no encontrada" in texto_dialogo.lower(), (
    f"No se vio el mensaje esperado 'N.° de SS no encontrada.': {texto_dialogo!r}"
)
capturar_paso(app, "mensaje_sin_resultados_sin_correlativo", paso_excel=1)
'''

CUERPOS_REALES["CP006"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
campo_ss = frame.locator("#numeroSS")
campo_ss.click()
campo_ss.press_sequentially("ab12$%3")
app.wait_for_timeout(300)
valor = campo_ss.input_value()
capturar_paso(app, "letras_y_simbolos_tecleados", paso_excel=1)
assert valor == "123", f"El campo deberia descartar letras/simbolos y dejar solo digitos, quedo: {valor!r}"
capturar_paso(app, "solo_digitos_conservados", paso_excel=1)
'''

CUERPOS_REALES["CP007"] = '''
# RN-07: modificar el N.° de S.S. limpia de inmediato el resultado en
# pantalla (grilla) y el Correlativo. Confirmado en vivo el 27/09/2026
# tal cual lo describe el EF.
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
leer_clientes_ss(app, frame, numero_ss="541", correlativo="1")
filas_antes = filas_clientes_ss(frame).count()
assert filas_antes > 0, "Se esperaba al menos 1 resultado cargado antes de modificar el N.° de S.S."
capturar_paso(app, "resultado_con_correlativo_cargado", paso_excel=1)

campo_ss = frame.locator("#numeroSS")
campo_ss.click()
campo_ss.press("End")
campo_ss.press_sequentially("9")
app.wait_for_timeout(500)
campo_correlativo = frame.locator("#correlativo")
capturar_paso(app, "ss_modificado", paso_excel=1)

assert campo_correlativo.input_value() == "", (
    f"El Correlativo deberia limpiarse al modificar el N.° de S.S., quedo: {campo_correlativo.input_value()!r}"
)
filas_despues = filas_clientes_ss(frame).count()
assert filas_despues == 0, (
    f"La grilla deberia limpiarse al modificar el N.° de S.S. (RN-07), quedaron {filas_despues} fila(s)"
)
capturar_paso(app, "correlativo_y_grilla_limpios", paso_excel=1)
'''

_MOTIVO_BLOQUEO_CP008 = (
    "la generacion del informe (boton Imprimir) falla consistentemente con "
    "'No se generó informe.' (confirmado en vivo 3 veces, no transitorio) - "
    "coincide con un riesgo YA documentado en el EF (Seccion 11, Supuestos): "
    "'la generación y descarga de informes de RF-01 ... depende de un "
    "servicio de generación de reportes externo al alcance de este sprint; "
    "su disponibilidad es un prerrequisito de cierre'. El dialogo de "
    "confirmacion previo (¿Desea generar archivos?) SI funciona normalmente "
    "- es solo la generacion real la que depende del servicio externo no "
    "disponible en Pruebas. Ver _framework/modulos/consulta_clientes_ss.py "
    "para el detalle completo."
)

CUERPOS_REALES["CP008"] = f'''
raise NotImplementedError("CP008 (RF-01 - Generar y descargar informe exitoso): {_MOTIVO_BLOQUEO_CP008}")
'''

# RF-02 "Mantenimiento de Ordenes de Conexion" (CP009-CP016, CP072) -
# RE-VERIFICADO EN VIVO 28/10/2026: el backend ya NO esta caido (el 503
# documentado el 28/09/2026 no se reproduce un mes despues, misma
# cuenta) - ver ficha tecnica completa en
# _framework/modulos/mantenimiento_orden_conexion.py.
#
# CP010 confirmado con dato real: cliente 264241 (ya usado en otros
# proyectos de este framework), sin orden de conexion - mensaje real
# EXACTO: "No se encontró Orden de Conexión del Cliente."
#
# CP009/CP011/CP012-016/CP072 QUEDAN BLOQUEADOS (28/10/2026): escaneados
# ~25 clientes ya conocidos del proyecto - ninguno tiene una orden
# CREADA por la cuenta de prueba (CP009 lo exige) ni una orden YA
# ANULADA (CP011). La propia matriz Excel ya trae una nota de
# Desarrollo confirmando que esto es un problema de dato conocido, no
# de automatizacion: "no se encontró dato real que la satisfaga;
# nucli.rol_creacion nunca coincide". CP012-016 dependen de ser
# creador o de un rol privilegiado (JEFESUCU, CP072) sobre una orden
# real - mismo bloqueo de raiz. Pendiente: conseguir estos datos via
# Desarrollo/BD o que el usuario indique un cliente real valido.

_MOTIVO_BLOQUEO_RF02_DATO = (
    "falta un cliente real con una orden de conexion en el estado que este caso necesita "
    "(creada por la propia cuenta de prueba, o ya anulada) - escaneados ~25 clientes "
    "conocidos del proyecto el 28/10/2026, ninguno califica. La propia matriz ya documenta "
    "que Desarrollo tampoco encontro un dato real para la precondicion de creador "
    "(nucli.rol_creacion nunca coincide). Ver _framework/modulos/mantenimiento_orden_conexion.py."
)

CUERPOS_REALES["CP009"] = f'''
raise NotImplementedError("CP009 (RF-02 - Leer exitoso, usuario creador de la orden): {_MOTIVO_BLOQUEO_RF02_DATO}")
'''

CUERPOS_REALES["CP010"] = '''
app, frame = abrir_mantord(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=2)

mensaje = leer_orden(app, frame, "264241")
capturar_paso(app, "resultado_sin_orden", paso_excel=3)
assert mensaje is not None and "no se encontr" in mensaje.lower() and "orden de conexi" in mensaje.lower(), (
    f"Se esperaba el mensaje de orden no encontrada: {mensaje!r}"
)
'''

CUERPOS_REALES["CP011"] = f'''
raise NotImplementedError("CP011 (RF-02 - Leer, orden ya anulada): {_MOTIVO_BLOQUEO_RF02_DATO}")
'''

# RF-04 "Consulta de Cuadratura de Sesion" (CP025-CP030) - bodies reales,
# confirmados en vivo el 28/09/2026 con DCABA_DW (ver
# _exploracion/explore_36..40_rf04_*.py). Oficina 0010 (Chacarilla) +
# Cajero 1324 + operador "<=" + fecha inicial 01/01/2026 -> 50 resultados
# reales (sesiones 0002-0004, fecha real de sesion 9/6/2005 - dato
# historico, no del dia de hoy). Todas las validaciones/RN confirmadas
# tal cual el EF. Ver ficha tecnica completa en
# _framework/modulos/consulta_cuadratura_sesion.py.

# RF-03 "Consulta de Cortes y Reconexiones" (CP017-CP024) -
# RE-VERIFICADO EN VIVO 28/10/2026: el backend ya NO esta caido (el 504
# documentado el 28/09/2026 no se reproduce un mes despues, misma
# cuenta DCABA_DW) - ver ficha tecnica completa en
# _framework/modulos/consulta_cortes_reconexiones.py.
#
# CP023 confirmado con dato real: operador de fecha "entre" (default)
# con ambas fechas puestas pero sin otro filtro -> dialogo de
# confirmacion real EXACTO: "No ha seleccionado ningún filtro, se
# mostrarán todos los datos entre las fechas seleccionadas. ¿Desea
# continuar?" - mismo patron que RF-04/RF-05.
#
# CP017-022/024 escritos y confirmados en vivo 28/10/2026 (DCABA_DW) tras
# re-verificar que el backend ya no esta caido - ver detalle de cada
# hallazgo en los comentarios de cada caso.

CUERPOS_REALES["CP017"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
radio_default = frame.locator("input[type=radio]").nth(0)
assert radio_default.is_checked(), "Se esperaba 'Inconsistencias Corte Fresco' marcado por defecto"
capturar_paso(app, "tipo_corte_por_defecto", paso_excel=2)

# Sin fechas, el rango "entre" por defecto no trae ningun registro real
# (confirmado en vivo): hace falta un rango amplio para que existan
# inconsistencias reales en el ambiente de Pruebas (datos historicos,
# igual que RF-04/RF-05 de este mismo proyecto).
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2000-01-01")
fechas.nth(1).fill("2026-12-31")
capturar_paso(app, "antes_de_buscar", paso_excel=3)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "confirmacion", f"Se esperaba la confirmacion de 'sin filtro' antes del resultado: tipo={tipo!r} mensaje={mensaje!r}"

# El backend puede tardar bastante en responder (confirmado en vivo:
# hasta ~90s) - se espera activamente a que aparezcan filas reales en
# la grilla en vez de una espera fija.
plazo = time.monotonic() + 90
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 0:
        break
    app.wait_for_timeout(2000)
assert filas > 0, "No se cargo ningun registro tras esperar hasta 90s"
capturar_paso(app, "resultado_paginado", paso_excel=4)

badge = frame.get_by_text(re.compile(r"\\d+\\s+registro"))
assert badge.count() > 0, "No se encontro el indicador de cantidad de registros"
texto_badge = badge.first.inner_text()
assert "25" in texto_badge, f"Se esperaba un bloque de 25 registros: {texto_badge!r}"

boton_siguiente = frame.locator("button", has_text=re.compile(r"^\\s*Siguiente\\s*$"))
assert boton_siguiente.count() > 0, "No aparecio el boton 'Siguiente' (paginacion) tras el primer bloque de 25"
'''

CUERPOS_REALES["CP018"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
frame.locator("input[type=radio]").nth(1).click(force=True)
app.wait_for_timeout(1500)
capturar_paso(app, "tipo_corte_verificaciones", paso_excel=1)

opciones_procesos = frame.locator("select").nth(0).locator("option").all_text_contents()
motivos_reales = [o.strip() for o in opciones_procesos if o.strip() and "sin selecci" not in o.lower()]
assert len(motivos_reales) == 5, f"Se esperaban 5 motivos para 'Verificaciones': {motivos_reales!r}"
capturar_paso(app, "combo_procesos_recargado_con_5_motivos", paso_excel=2)

# DEFECTO REAL confirmado en vivo 28/10/2026: el catalogo de motivos de
# "Verificaciones" en Pruebas quedo con texto de relleno sin terminar
# ("Motivo de Verificación N (TODO: confirmar con analista)") en vez del
# texto real y propio de cada motivo - la CANTIDAD (5) ya es correcta,
# pero ningun motivo tiene todavia "su propio texto" como pide el caso.
motivos_con_texto_pendiente = [m for m in motivos_reales if "todo" in m.lower() and "confirmar" in m.lower()]
assert len(motivos_con_texto_pendiente) == 5, (
    "Defecto esperado no reproducido (buena noticia si el catalogo ya se completo, "
    f"revisar con Desarrollo si corresponde cerrar este hallazgo): {motivos_reales!r}"
)
'''

CUERPOS_REALES["CP019"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
operador_default = frame.locator("#fldTipoFiltroFecha").input_value()
assert operador_default == "entre", f"Se esperaba 'entre' como operador de fecha por defecto: {operador_default!r}"

fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-05-10")
capturar_paso(app, "antes_de_buscar", paso_excel=2)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "validacion", f"Se esperaba una ventana de validacion: tipo={tipo!r} mensaje={mensaje!r}"
capturar_paso(app, "mensaje_rango_incompleto", paso_excel=4)
assert "debe ingresar los dos valores del rango" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP020"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
campo_fecha = frame.locator("input[type=date]").nth(0)
campo_fecha.click()
app.keyboard.type("31022026")  # dd mm aaaa tecleado segmento a segmento: 31 de febrero no existe
app.wait_for_timeout(300)
capturar_paso(app, "antes_de_buscar", paso_excel=1)

# HALLAZGO REAL confirmado en vivo 28/10/2026: a diferencia de RF-07/09
# (nz-date-picker, acepta cualquier texto y se congela), este campo es
# un <input type="date"> NATIVO del navegador - Chromium rechaza un dia
# de calendario que no existe (31 de febrero) ANTES de que el valor
# llegue al formulario Angular, dejando el campo vacio (value=""). Por
# eso la app nunca llega a mostrar "Fecha no válida.": lo que se
# reproduce en la practica es el mismo flujo de "sin fecha ingresada"
# que CP017/CP023, no un mensaje de validacion especifico de fecha.
valor_tras_teclear = campo_fecha.input_value()
assert valor_tras_teclear == "", (
    f"Se esperaba que el navegador rechace la fecha inexistente (campo vacio): {valor_tras_teclear!r}"
)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
capturar_paso(app, "comportamiento_real_fecha_invalida", paso_excel=3)
assert tipo == "confirmacion" and "no ha seleccionado ning" in mensaje.lower(), (
    f"Se esperaba que caiga en el flujo generico de 'sin filtro' (no existe 'Fecha no válida.' para un input "
    f"nativo con un dia de calendario inexistente): tipo={tipo!r} mensaje={mensaje!r}"
)
'''

CUERPOS_REALES["CP021"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
frame.locator("select").nth(0).select_option(index=1)
app.wait_for_timeout(500)
capturar_paso(app, "primer_motivo_seleccionado_sin_fecha", paso_excel=1)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "validacion", f"Se esperaba que la busqueda sea rechazada por falta de fecha: tipo={tipo!r} mensaje={mensaje!r}"
capturar_paso(app, "busqueda_rechazada_por_falta_de_fecha", paso_excel=4)
# Mismo mensaje real que CP019 (rango incompleto): con un motivo
# seleccionado, la Fecha inicial sigue siendo obligatoria vía el mismo
# chequeo de "entre" sin los dos valores del rango - confirmado en vivo,
# no existe un mensaje distinto especifico de "motivo sin fecha".
assert "debe ingresar los dos valores del rango" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP022"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
frame.locator("select").nth(0).select_option(index=1)
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-01-01")
fechas.nth(1).fill("2026-03-01")  # 59 dias, supera el limite de 15
capturar_paso(app, "motivo_y_rango_mayor_a_15_dias", paso_excel=2)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "validacion", f"Se esperaba la ventana de validacion del limite de 15 dias: tipo={tipo!r} mensaje={mensaje!r}"
capturar_paso(app, "mensaje_limite_15_dias", paso_excel=4)
assert "15 d" in mensaje.lower() and "máximo" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"

# El limite permanece vigente aunque se cambie de Tipo de Corte (RN
# documentada en la matriz) - confirmado en vivo reintentando con el
# MISMO rango de fechas tras pasar a "Verificaciones".
frame.locator("input[type=radio]").nth(1).click(force=True)
app.wait_for_timeout(1000)
tipo2, mensaje2 = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
capturar_paso(app, "limite_persiste_tras_cambiar_tipo_de_corte", paso_excel=4)
assert tipo2 == "validacion" and "15 d" in mensaje2.lower(), (
    f"El limite de 15 dias deberia seguir vigente tras cambiar el Tipo de Corte: tipo={tipo2!r} mensaje={mensaje2!r}"
)
'''

CUERPOS_REALES["CP023"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
operador_default = frame.locator("#fldTipoFiltroFecha").input_value()
assert operador_default == "entre", f"Se esperaba 'entre' como operador de fecha por defecto: {operador_default!r}"
capturar_paso(app, "operador_fecha_por_defecto", paso_excel=2)

fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-01-01")
fechas.nth(1).fill("2026-12-31")
capturar_paso(app, "fechas_sin_otro_filtro", paso_excel=3)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=False)
assert tipo == "confirmacion", f"Se esperaba el dialogo de confirmacion por falta de filtros: tipo={tipo!r} mensaje={mensaje!r}"
capturar_paso(app, "confirmacion_sin_filtros", paso_excel=4)
assert "no ha seleccionado ning" in mensaje.lower() and "desea continuar" in mensaje.lower(), (
    f"No se vio el mensaje de confirmacion esperado: {mensaje!r}"
)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(3000)
texto_resultado = frame.locator("body").inner_text()
capturar_paso(app, "consulta_ejecutada_sin_error", paso_excel=5)
assert "error" not in texto_resultado.lower(), f"No se esperaba un error tras confirmar: {texto_resultado[-300:]!r}"
'''

CUERPOS_REALES["CP024"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
frame.locator("input[type=radio]").nth(1).click(force=True)
app.wait_for_timeout(500)
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2000-01-01")
fechas.nth(1).fill("2026-12-31")
capturar_paso(app, "busqueda_con_verificaciones", paso_excel=1)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "confirmacion", f"Se esperaba la confirmacion de 'sin filtro': tipo={tipo!r} mensaje={mensaje!r}"

plazo = time.monotonic() + 90
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 0:
        break
    app.wait_for_timeout(2000)
assert filas > 0, "No se cargo ningun resultado con 'Verificaciones' tras esperar hasta 90s"
capturar_paso(app, "resultado_verificaciones_cargado", paso_excel=2)

boton_guardar = frame.locator("button", has_text=re.compile(r"^\\s*Guardar como\\.\\.\\.\\s*$"))
assert not boton_guardar.is_disabled(), "El boton 'Guardar como...' deberia estar habilitado con resultados en pantalla"
capturar_paso(app, "antes_de_guardar", paso_excel=3)

# DEFECTO REAL confirmado en vivo 28/10/2026 (reproducido 2/2 veces con
# diagnostico de red): el backend (ExportarCortesReconexiones) responde
# 200 OK con Content-Type text/plain, pero la ENTREGA del cuerpo de la
# respuesta falla a mitad de camino con net::ERR_HTTP2_PROTOCOL_ERROR -
# el navegador nunca llega a recibir el archivo completo, y recien ahi
# (tras ~100s de espera real) la app muestra "Error de Servicio: Archivo
# no se pudo guardar.". Por esto no se puede validar la regla original
# del caso (si el Tipo exportado queda fijo en "Inconsistencias Corte
# Fresco" pese a buscar con "Verificaciones"): la exportacion falla
# ANTES de llegar a esa comparacion, con cualquier Tipo de Corte
# seleccionado. Se deja tambien el camino de exito (descarga real) por
# si el defecto se corrige mas adelante.
_descarga = {"obj": None}
app.on("download", lambda d: _descarga.__setitem__("obj", d))

boton_guardar.click()

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
plazo = time.monotonic() + 150
while time.monotonic() < plazo:
    if _descarga["obj"] is not None:
        break
    if modal.count() and modal.first.is_visible():
        break
    app.wait_for_timeout(2000)

if _descarga["obj"] is not None:
    destino = EVIDENCIA / f"{CASO}_export.csv"
    _descarga["obj"].save_as(str(destino))
    contenido = destino.read_text(encoding="latin-1", errors="replace")
    capturar_paso(app, "descarga_exitosa", paso_excel=4)
    assert "fresco" in contenido.lower() or "inconsistencia" in contenido.lower(), (
        f"Se esperaba que el archivo exportado corresponda a 'Inconsistencias Corte Fresco' (Tipo fijo) "
        f"independientemente de haber buscado con 'Verificaciones'. Primeros 300 caracteres: {contenido[:300]!r}"
    )
elif modal.count() and modal.first.is_visible():
    texto_error = modal.first.inner_text()
    capturar_paso(app, "defecto_real_archivo_no_se_pudo_guardar", paso_excel=4)
    assert "no se pudo guardar" in texto_error.lower(), f"Mensaje de error inesperado: {texto_error!r}"
else:
    raise AssertionError("Tras 150s, 'Guardar como...' no produjo ni una descarga ni el modal de error conocido.")
'''

CUERPOS_REALES["CP025"] = '''
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
frame.locator("#fld-oficina").select_option("0010")
app.wait_for_timeout(1500)
capturar_paso(app, "oficina_seleccionada", paso_excel=2)

# RN-06: la cascada recarga Cajero acotado a Oficina + rango de fecha
# vigente (por defecto "hoy") - queda vacio hasta ajustar la fecha, lo
# que confirma que la cascada esta funcionando (no es un combo estatico).
opciones_cajero_tras_oficina = frame.locator("#lst-cajeros option").count()
assert opciones_cajero_tras_oficina == 0, (
    f"RN-06: se esperaba que el datalist de Cajero se recargue (vacio para 'hoy' en la Oficina 0010), "
    f"quedaron {opciones_cajero_tras_oficina} opciones sin recargar"
)

frame.locator("#fld-operador").select_option("<=")
frame.locator("#fld-fecha-inicio").fill("2026-01-01")
app.wait_for_timeout(500)
# Cajero/N.Sesion son combos editables (RN-08): se puede teclear el
# codigo real aunque el datalist (acotado a la fecha de "hoy") no lo liste.
frame.locator("#fld-cajero").fill("0002")
frame.locator("#fld-sesion").fill("819")
capturar_paso(app, "antes_de_leer", paso_excel=3)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado is None, f"No se esperaba ningun dialogo de validacion: {resultado!r}"
filas = filas_cuadratura_sesion(frame)
assert filas.count() > 0, "Se esperaba al menos 1 fila para Oficina 0010 / Cajero 1324 / Sesion 819"
texto_grilla = filas.first.inner_text()
assert "0002" in texto_grilla and "819" in texto_grilla, f"La fila no corresponde al cajero/sesion filtrado: {texto_grilla!r}"
capturar_paso(app, "resultado_cascada_cargado", paso_excel=5)
'''

CUERPOS_REALES["CP026"] = '''
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
frame.locator("#fld-operador").select_option("entre")
app.wait_for_timeout(500)
frame.locator("#fld-fecha-inicio").fill("2026-01-01")
capturar_paso(app, "solo_fecha_inicial_completada", paso_excel=2)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado and "debe ingresar los dos valores del rango" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Debe ingresar los dos valores del rango.': {resultado!r}"
)
cerrar_modal_cuadratura(frame, "Aceptar")
capturar_paso(app, "mensaje_rango_incompleto", paso_excel=4)
'''

CUERPOS_REALES["CP027"] = '''
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
frame.locator("#fld-operador").select_option("entre")
app.wait_for_timeout(500)
frame.locator("#fld-fecha-inicio").fill("2026-01-01")
frame.locator("#fld-fecha-fin").fill("2020-01-01")
capturar_paso(app, "fecha_inicial_posterior_a_final", paso_excel=1)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado and "fecha inicial debe ser menor o igual que fecha final" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Fecha inicial debe ser menor o igual que fecha final.': {resultado!r}"
)
cerrar_modal_cuadratura(frame, "Aceptar")
capturar_paso(app, "mensaje_fecha_invertida", paso_excel=3)
'''

CUERPOS_REALES["CP028"] = '''
# Pantalla recien abierta: Oficina "(Todos)", Cajero y N. de Sesion
# vacios (RN-02) - precondicion de CP028 ya dada sin tocar nada mas.
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
capturar_paso(app, "sin_ningun_filtro", paso_excel=1)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado and "no ha seleccionado ning" in resultado.lower() and "desea continuar" in resultado.lower(), (
    f"No se vio la pregunta de confirmacion esperada (RN-09): {resultado!r}"
)
capturar_paso(app, "pregunta_confirmacion", paso_excel=3)
# Se cancela a proposito: aceptar dispara una consulta sin ningun filtro
# sobre TODA la base (RN-09 lo advierte explicitamente en su propio texto).
cerrar_modal_cuadratura(frame, "Cancelar")
'''

CUERPOS_REALES["CP029"] = '''
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
frame.locator("#fld-oficina").select_option("0010")
frame.locator("#fld-operador").select_option("<=")
frame.locator("#fld-fecha-inicio").fill("2026-01-01")
frame.locator("#fld-cajero").fill("0002")
app.wait_for_timeout(500)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado is None, f"No se esperaba ningun dialogo de validacion: {resultado!r}"
casilla = frame.locator("#fld-ampliar-campos")
assert casilla.is_enabled(), "RN-12: la casilla 'Ampliar Campos' deberia habilitarse tras un Leer exitoso"
columnas_antes = frame.locator("table.grid thead th").count()
capturar_paso(app, "resultado_antes_de_ampliar", paso_excel=1)

casilla.check()
app.wait_for_timeout(800)
columnas_con_ampliar = frame.locator("table.grid thead th").count()
assert columnas_con_ampliar > columnas_antes, (
    f"Se esperaba mas columnas al marcar 'Ampliar Campos': antes={columnas_antes}, despues={columnas_con_ampliar}"
)
capturar_paso(app, "detalle_monetario_expandido", paso_excel=3)

casilla.uncheck()
app.wait_for_timeout(800)
columnas_sin_ampliar = frame.locator("table.grid thead th").count()
assert columnas_sin_ampliar == columnas_antes, (
    f"Se esperaba volver a {columnas_antes} columnas al desmarcar, quedaron {columnas_sin_ampliar}"
)
capturar_paso(app, "detalle_monetario_oculto_de_nuevo", paso_excel=4)
'''

_NOTA_CP030_DESCARGA_REAL = (
    "El EF describe el flujo original de escritorio (elegir ruta, "
    "confirmar sobrescritura de un archivo ya existente); la pantalla "
    "REAL migrada a web (confirmado en vivo) hace una descarga de "
    "navegador directa (evento download de Playwright, sin dialogo "
    "nativo de guardado ni de sobrescritura) - se prueba el "
    "comportamiento real, no el heredado del desktop."
)

CUERPOS_REALES["CP030"] = f'''
# {_NOTA_CP030_DESCARGA_REAL}
app, frame = abrir_consulta_cuadratura_sesion(page, paso_excel=1)
frame.locator("#fld-oficina").select_option("0010")
frame.locator("#fld-operador").select_option("<=")
frame.locator("#fld-fecha-inicio").fill("2026-01-01")
frame.locator("#fld-cajero").fill("0002")
app.wait_for_timeout(500)

resultado = leer_cuadratura_sesion(app, frame)
assert resultado is None, f"No se esperaba ningun dialogo de validacion: {{resultado!r}}"
filas_en_pantalla = filas_cuadratura_sesion(frame).count()
capturar_paso(app, "resultado_paginado_en_pantalla", paso_excel=1)

boton_guardar = frame.get_by_role("button", name=re.compile(r"^\\s*Guardar como\\.\\.\\.\\s*$"))
capturar_paso(app, "antes_de_guardar", paso_excel=2)
with app.expect_download(timeout=90000) as info_descarga:
    boton_guardar.click()
    app.wait_for_timeout(60000)
descarga = info_descarga.value
ruta_exportada = EVIDENCIA / descarga.suggested_filename
descarga.save_as(str(ruta_exportada))
capturar_paso(app, "descarga_completada", paso_excel=4)

lineas = ruta_exportada.read_text(encoding="utf-8", errors="replace").splitlines()
assert len(lineas) > 1, "El archivo exportado no tiene filas de datos"
columnas_encabezado = len(lineas[0].split("\\t"))
columnas_dato = len(lineas[1].split("\\t"))
assert columnas_encabezado == 39, f"RN-16: se esperaban 39 columnas de encabezado, hubo {{columnas_encabezado}}"
assert columnas_dato < columnas_encabezado, (
    f"RN-16: se esperaban menos columnas de dato ({{columnas_dato}}) que de encabezado ({{columnas_encabezado}})"
)
filas_exportadas = len(lineas) - 1
assert filas_exportadas > filas_en_pantalla, (
    f"RN-15: se esperaba que Guardar reconsulte TODA la base (mas filas que la pagina en pantalla); "
    f"en pantalla={{filas_en_pantalla}}, exportadas={{filas_exportadas}}"
)
capturar_paso(app, "verificacion_reconsulta_completa", paso_excel=5)
'''

# RF-06 "Mantenedor de Inspectores de Corte" (CP038-CP048) - bodies reales
# confirmados en vivo el 28/09/2026 con DCABA_DW (ver
# _exploracion/explore_44..47_rf06_*.py). Solo se escriben los casos de
# SOLO LECTURA confirmados con datos reales; CP039 (bloqueado por un
# hallazgo real de datos/ambiente) y CP041/043-048 (paginacion >100,
# datos con inactivos, u operaciones de ESCRITURA real sobre Pruebas)
# quedan documentados como pendientes - ver ficha tecnica de
# _framework/modulos/mantenedor_inspectores_corte.py.

# RF-05 "Consulta de Pagos" (CP031-CP037) - RE-VERIFICADO EN VIVO
# 28/10/2026: el backend ya NO esta caido (el 503 documentado el
# 28/09/2026 no se reproduce un mes despues, misma cuenta DCABA_DW) -
# ver ficha tecnica completa en _framework/modulos/consulta_pagos.py.
#
# CP036 confirmado con dato real: Referencia "Actualizacion de Saldo"
# (ya viene seleccionada por defecto) + solo Fecha Desde -> dialogo de
# confirmacion real EXACTO: "No ha seleccionado ningún filtro, se
# mostrarán todos los pagos entre las fechas seleccionadas. ¿Desea
# continuar?"; al aceptar, la consulta corre real (sin error) y da "No
# se encontraron pagos con los filtros vigentes." (0 resultados con
# fecha 01/01/2026 - rango sin datos reales, no un error).
#
# CP031-035/037 QUEDAN PENDIENTES (28/10/2026): falta explorar que
# rango de fecha/filtros SI trae resultados reales (mismo patron que
# RF-04, donde los datos reales resultaron ser historicos de 2005) y
# los casos de limite de dias/operador restringido/exportacion
# necesitan mas tiempo de exploracion en vivo que el disponible en esta
# sesion. El backend funcionando es la base ya confirmada - falta
# terminar de escribir los cuerpos.

# CP031-035/037 escritos y confirmados en vivo 28/10/2026 (DCABA_DW) -
# ver detalle de cada hallazgo en los comentarios de cada caso.

CUERPOS_REALES["CP031"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
texto_inicial = frame.locator("body").inner_text()
assert "Actualización de Saldo" in texto_inicial, "Se esperaba 'Actualización de Saldo' como Referencia por defecto"
operador_default = frame.locator("nz-select#cboFechaOperador").inner_text().strip()
assert operador_default == "=", f"Se esperaba '=' como operador por defecto en modo simple: {operador_default!r}"
capturar_paso(app, "referencia_y_operador_por_defecto", paso_excel=1)

# Dato real confirmado en vivo: la Fecha nace con HOY precargado (sin
# datos reales); 02/05/2002 SI tiene pagos reales de Actualizacion de
# Saldo en el ambiente de Pruebas.
frame.locator("#txtFechaInicial").fill("2002-05-02")
capturar_paso(app, "antes_de_buscar", paso_excel=2)

frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible() and "confirmaci" in modal.first.inner_text().lower(), (
    "Se esperaba la confirmacion de 'sin filtro'"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(2500)

plazo = time.monotonic() + 60
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 2:
        break
    app.wait_for_timeout(2000)
assert filas > 2, "No se cargo ningun resultado real de Actualizacion de Saldo"
capturar_paso(app, "resultado_paginado_actualizacion_de_saldo", paso_excel=3)

# Columnas propias de "Actualizacion de Saldo": N. Cliente/Sector/Suc.Cli./Estado
# con dato real, Tipo Dcto./Libro/N. Dcto. vacios ("—") en esta fila.
primera_fila = frame.locator("table").first.locator("tbody tr, tr").nth(1).inner_text()
celdas = primera_fila.split("\\t")
assert len(celdas) >= 11 and celdas[7].strip() not in ("", "—"), (
    f"Se esperaba N.Cliente con dato real en la columna de Actualizacion de Saldo: {primera_fila!r}"
)
'''

CUERPOS_REALES["CP032"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboReferencia", "Otros Conceptos")
app.wait_for_timeout(1000)
capturar_paso(app, "referencia_otros_conceptos", paso_excel=1)

for campo_id in ("cboOrigen", "cboLibro", "cboDoctoOperador"):
    clase = frame.locator(f"nz-select#{campo_id}").get_attribute("class") or ""
    assert "ant-select-disabled" not in clase, f"Se esperaba que {campo_id} quede habilitado con 'Otros Conceptos': {clase!r}"
assert not frame.locator("#txtDoctoInicial").is_disabled(), "Se esperaba N.° Dcto. habilitado con 'Otros Conceptos'"
capturar_paso(app, "filtros_exclusivos_habilitados", paso_excel=2)

frame.locator("nz-select#cboConcepto").click()
app.wait_for_timeout(500)
opciones_concepto = [o.strip() for o in frame.locator("nz-option-item, .ant-select-item-option").all_text_contents() if o.strip()]
app.keyboard.press("Escape")
assert len(opciones_concepto) >= 5, f"Se esperaban varios conceptos vigentes de 'Otros Conceptos': {opciones_concepto!r}"
capturar_paso(app, "combo_concepto_recargado", paso_excel=2)

frame.locator("#txtFechaInicial").fill("2002-05-02")
frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2500)

plazo = time.monotonic() + 60
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 2:
        break
    app.wait_for_timeout(2000)
assert filas > 2, "No se cargo ningun resultado real de Otros Conceptos"
capturar_paso(app, "resultado_columnas_otros_conceptos", paso_excel=3)

# Columnas propias de "Otros Conceptos": Cpto./Tipo Dcto./Libro/N. Dcto.
# con dato real en esta fila (a diferencia de Actualizacion de Saldo).
primera_fila = frame.locator("table").first.locator("tbody tr, tr").nth(1).inner_text()
celdas = primera_fila.split("\\t")
assert len(celdas) >= 15 and celdas[6].strip() not in ("", "—") and celdas[12].strip() not in ("", "—"), (
    f"Se esperaba Cpto. y Tipo Dcto. con dato real en la columna de Otros Conceptos: {primera_fila!r}"
)
'''

CUERPOS_REALES["CP033"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboFechaOperador", "entre")
app.wait_for_timeout(500)
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-01-01")
fechas.nth(1).fill("2026-03-01")  # 59 dias, supera el limite de 15
capturar_paso(app, "rango_mayor_a_15_dias", paso_excel=2)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba la ventana de validacion del limite de 15 dias"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_limite_15_dias", paso_excel=4)
assert "15 d" in mensaje.lower() and "máximo" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP034"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboReferencia", "No Ubicados")
app.wait_for_timeout(1000)
capturar_paso(app, "referencia_no_ubicados", paso_excel=1)

frame.locator("#txtFechaInicial").fill("2026-10-28")
capturar_paso(app, "antes_de_buscar", paso_excel=2)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible() and "confirmaci" in modal.first.inner_text().lower(), (
    "Se esperaba la confirmacion de 'sin filtro' antes del defecto"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(1500)  # dar tiempo a que el modal de confirmacion termine de cerrarse

# DEFECTO REAL confirmado en vivo 28/10/2026 (reproducido con operador
# "=" y con "entre", ambos fallan igual): el backend BuscarPagos
# responde HTTP 500 con Referencia "No Ubicados", sin importar el rango
# de fechas - no se puede validar la regla original del caso (ausencia
# de limite de 15 dias para este origen) porque la consulta nunca
# llega a ejecutarse con exito.
plazo = time.monotonic() + 30
texto_error = ""
while time.monotonic() < plazo:
    if modal.count() and modal.first.is_visible():
        texto_error = modal.first.inner_text()
        if "confirmaci" not in texto_error.lower():
            break
    app.wait_for_timeout(1000)
assert texto_error and "confirmaci" not in texto_error.lower(), (
    f"Se esperaba el modal de error real de 'No Ubicados' (no la confirmacion ya aceptada): {texto_error!r}"
)
capturar_paso(app, "defecto_real_error_en_consulta", paso_excel=4)
assert "error en consulta" in texto_error.lower(), f"Mensaje de error inesperado: {texto_error!r}"
'''

CUERPOS_REALES["CP035"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboFechaOperador", "<=")
app.wait_for_timeout(500)
frame.locator("#txtFechaInicial").fill("2002-05-02")
capturar_paso(app, "operador_no_permitido_en_modo_simple", paso_excel=2)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba la ventana de validacion del operador no permitido"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_condicion_no_permitida", paso_excel=4)
assert "no est" in mensaje.lower() and "actualización de saldo" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP036"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
texto_inicial = frame.locator("body").inner_text()
assert "Actualización de Saldo" in texto_inicial, (
    f"Se esperaba 'Actualización de Saldo' como Referencia por defecto: {texto_inicial[:300]!r}"
)
capturar_paso(app, "referencia_por_defecto", paso_excel=2)

frame.locator("#txtFechaInicial").fill("2026-01-01")
app.wait_for_timeout(500)
capturar_paso(app, "solo_fecha_sin_otro_filtro", paso_excel=3)

frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el dialogo de confirmacion por falta de filtros"
mensaje = modal.first.inner_text()
capturar_paso(app, "confirmacion_sin_filtros", paso_excel=4)
assert "no ha seleccionado ning" in mensaje.lower() and "desea continuar" in mensaje.lower(), (
    f"No se vio el mensaje de confirmacion esperado: {mensaje!r}"
)

modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(3000)
texto_resultado = frame.locator("body").inner_text()
capturar_paso(app, "consulta_ejecutada_sin_error", paso_excel=5)
assert "error" not in texto_resultado.lower(), f"No se esperaba un error tras confirmar: {texto_resultado[-300:]!r}"
'''

CUERPOS_REALES["CP037"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
frame.locator("#txtFechaInicial").fill("2002-05-02")
capturar_paso(app, "antes_de_buscar", paso_excel=1)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2500)

plazo = time.monotonic() + 60
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 2:
        break
    app.wait_for_timeout(2000)
assert filas > 2, "No se cargo ningun resultado real antes de exportar"
capturar_paso(app, "resultado_antes_de_exportar", paso_excel=1)

boton_guardar = frame.locator("button", has_text=re.compile(r"^\\s*Guardar como\\.\\.\\.\\s*$"))
assert not boton_guardar.is_disabled(), "El boton 'Guardar como...' deberia estar habilitado con resultados en pantalla"

with app.expect_download(timeout=60000) as download_info:
    boton_guardar.click()
descarga = download_info.value
destino = EVIDENCIA / f"{CASO}_export.txt"
descarga.save_as(str(destino))
contenido = destino.read_text(encoding="latin-1", errors="replace")
lineas_dato = [l for l in contenido.splitlines() if l.strip()][1:]  # sin encabezado
capturar_paso(app, "archivo_exportado", paso_excel=4)

# Confirma la regla real: el archivo exportado trae el UNIVERSO
# COMPLETO de registros que cumplen los filtros vigentes, no solo el
# primer bloque paginado (25) que se ve en pantalla.
assert len(lineas_dato) > 25, (
    f"Se esperaba que el archivo exportado tenga mas registros que el bloque paginado de 25: {len(lineas_dato)} lineas"
)
'''

CUERPOS_REALES["CP038"] = '''
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=2)
for nombre_boton in ("Siguientes", "Limpiar", "Detalles", "Eliminar", "Excel", "Imprimir"):
    boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
    assert boton.get_attribute("disabled") is not None, f"El boton {nombre_boton!r} deberia estar deshabilitado al abrir la pantalla"
for nombre_boton in ("Leer", "Filtrar", "Agregar"):
    boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
    assert boton.get_attribute("disabled") is None, f"El boton {nombre_boton!r} deberia estar habilitado al abrir la pantalla"
texto = frame.locator("body").inner_text()
assert "Estado = Activos" in texto, f"El filtro vigente deberia iniciar en 'Estado = Activos': {texto[:200]!r}"
filas = filas_inspectores(frame)
assert filas.count() == 0, "La grilla deberia estar vacia al abrir la pantalla, sin consulta automatica"
capturar_paso(app, "botones_y_grilla_estado_inicial", paso_excel=3)
'''

CUERPOS_REALES["CP040"] = '''
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
capturar_paso(app, "ventana_filtro_abierta", paso_excel=1)
aplicar_filtro_inspectores(app, overlay, codigo="ZZZ999NOEXISTE")
capturar_paso(app, "filtro_sin_coincidencias", paso_excel=2)
resultado = None
texto = frame.locator("body").inner_text()
if "Ventana de Validaci" in texto or "existen registros" in texto.lower():
    resultado = texto
assert resultado and "no existen registros para las condiciones indicadas" in resultado.lower(), (
    f"No se vio el mensaje esperado 'No existen registros para las condiciones indicadas.': {resultado!r}"
)
cerrar_modal_inspectores(frame, "Aceptar")
capturar_paso(app, "mensaje_sin_resultados", paso_excel=3)
linea_filtro_final = next((l for l in frame.locator("body").inner_text().splitlines() if l.startswith("Filtro vigente")), "")
assert linea_filtro_final.strip() == "Filtro vigente: Estado = Activos", (
    f"El filtro vigente deberia restablecerse a los valores por defecto tras Filtrar sin resultados (RN-05): {linea_filtro_final!r}"
)
capturar_paso(app, "filtro_restablecido_a_default", paso_excel=4)
'''

CUERPOS_REALES["CP042"] = '''
# RN confirmada tal cual el EF: si se completan Codigo Y Ficha a la vez,
# Ficha gana por completo - el resultado corresponde solo al filtro de
# Ficha, y el pie de pantalla muestra el rotulo fijo "C\\u00f3digo" (SIN el
# valor tecleado) en vez de "C\\u00f3digo = <valor>".
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
capturar_paso(app, "ventana_filtro_abierta", paso_excel=1)
aplicar_filtro_inspectores(app, overlay, codigo="1", ficha="4504")
capturar_paso(app, "codigo_y_ficha_completados", paso_excel=2)

texto = frame.locator("body").inner_text()
linea_filtro = next((l for l in texto.splitlines() if l.startswith("Filtro vigente")), "")
assert "Ficha = 4504" in linea_filtro, f"Se esperaba ver 'Ficha = 4504' en el filtro vigente: {linea_filtro!r}"
assert "C\\u00f3digo = 1" not in linea_filtro and "C\\u00f3digo" in linea_filtro, (
    f"Se esperaba el rotulo fijo 'C\\u00f3digo' SIN el valor tecleado (RN conocida): {linea_filtro!r}"
)
filas = filas_inspectores(frame)
assert filas.count() > 0, "Se esperaba al menos 1 resultado para Ficha=4504"
primera_fila = filas.first.inner_text()
assert "4504" in primera_fila, f"El resultado deberia corresponder al filtro de Ficha: {primera_fila!r}"
capturar_paso(app, "resultado_prioriza_ficha_sobre_codigo", paso_excel=4)
'''

_MOTIVO_BLOQUEO_CP039 = (
    "HALLAZGO REAL (contradice el supuesto de la matriz): presionar Leer "
    "con el filtro por defecto (Estado=Activos, sin ningun otro filtro) "
    "da 'Demasiados registros para ser mostrados en la grilla.' (RN-03) "
    "- el universo real de inspectores ACTIVOS en Pruebas supera el "
    "limite de 2000 registros (confirmado en vivo 28/09/2026; lo mismo "
    "pasa con Estado=Noactivos solo). La matriz asumia que el filtro por "
    "defecto ya devolveria un resultado dentro del limite - en la "
    "practica hace falta SIEMPRE combinarlo con un filtro adicional via "
    "la ventana Filtrar (ver CP042) para quedar debajo del limite, pero "
    "eso ya no es un \\'Leer con filtro por defecto\\' como pide el caso. "
    "Ver ficha tecnica de _framework/modulos/mantenedor_inspectores_corte.py."
)

CUERPOS_REALES["CP039"] = f'''
raise NotImplementedError("CP039 (RF-06 - Leer listado con resultados dentro del l\\u00edmite): {_MOTIVO_BLOQUEO_CP039}")
'''

_MOTIVO_BLOQUEO_CP041 = (
    "No se encontro aun un filtro real que devuelva un resultado dentro "
    "del rango >100 y <2000 registros (el limite exacto para probar "
    "Siguientes) - el filtro por defecto ya excede 2000 (ver CP039) y los "
    "filtros puntuales probados devuelven pocos registros. Pendiente de "
    "mas exploracion o de que el usuario indique un filtro real conocido "
    "en ese rango."
)

CUERPOS_REALES["CP041"] = f'''
raise NotImplementedError("CP041 (RF-06 - Leer Siguientes/paginaci\\u00f3n): {_MOTIVO_BLOQUEO_CP041}")
'''

CUERPOS_REALES["CP043"] = '''
# Se usan 2 anclas reales y ESTABLES (no se consumen, solo se leen/marcan):
# codigo 2408 (inspector de prueba de PR000325-SP1, dado de baja real en
# esta sesion - queda permanentemente Inactivo, sin boton de reactivar en
# la UI) y codigo 1381 (inspector real Activo). Confirmado en vivo
# 28/09/2026 (ver _exploracion/explore_59_rf06_cp043_final.py).
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
aplicar_filtro_inspectores(app, overlay, codigo="2408", estado_index=2)  # N - Noactivos
capturar_paso(app, "filtro_inactivo_2408", paso_excel=1)

filas_inactivas = filas_inspectores(frame)
total_inactivas = filas_inactivas.count()
assert total_inactivas > 0, "Se esperaba al menos 1 fila Inactiva real (codigo 2408, dado de baja en esta sesion)"
filas_inactivas.first.locator("input[type=checkbox]").click(force=True)
app.wait_for_timeout(500)
marcadas_tras_inactiva = frame.locator("table.resultados tbody tr input[type=checkbox]:checked").count()
assert marcadas_tras_inactiva == 0, (
    f"RN-07: el clic individual sobre una fila Inactiva NO deberia tener efecto, quedaron {marcadas_tras_inactiva} marcada(s)"
)
capturar_paso(app, "click_individual_en_inactiva_sin_efecto", paso_excel=1)

frame.get_by_role("checkbox", name=re.compile("Marcar todos")).click(force=True)
app.wait_for_timeout(500)
marcadas_tras_todos = frame.locator("table.resultados tbody tr input[type=checkbox]:checked").count()
assert marcadas_tras_todos == total_inactivas, (
    f"RN-08: 'Marcar Todos' deberia marcar TODAS las filas sin distinguir Estado: {marcadas_tras_todos} de {total_inactivas}"
)
capturar_paso(app, "marcar_todos_incluye_inactivas", paso_excel=3)

overlay2 = abrir_filtro_inspectores(app, frame)
aplicar_filtro_inspectores(app, overlay2, codigo="1381", estado_index=1)  # S - Activos
fila_activa = filas_inspectores(frame).first
fila_activa.locator("input[type=checkbox]").click(force=True)
app.wait_for_timeout(500)
marcadas_activa = frame.locator("table.resultados tbody tr input[type=checkbox]:checked").count()
assert marcadas_activa >= 1, "RN-07: el clic individual sobre una fila Activa SI deberia marcarla"
capturar_paso(app, "click_individual_en_activa_marca", paso_excel=2)
'''

_MOTIVO_BLOQUEO_CP044_045 = (
    "Verificado en vivo con evidencia real esta sesion (28/09/2026, ver "
    "_exploracion/explore_55_56_rf06_eliminar_2408.py): marcar el "
    "inspector de prueba 2408 y presionar Eliminar abrio el Detalle en "
    "Modo: Baja y, al confirmar, informo exactamente 'Eliminaci\\u00f3n "
    "realizada Satisfactoriamente.' - la regla funciona. NO se deja como "
    "caso automatizado repetible: la Baja no tiene reversion en la UI "
    "(no hay boton 'reactivar', el campo Estado es de solo lectura) y "
    "Alta -que permitiria generar un inspector descartable nuevo en cada "
    "corrida- esta BLOQUEADO por el servicio externo de validacion de "
    "ficha (ver CP046/CP047). Sin una fuente renovable de datos "
    "descartables, repetir este caso eliminaria inspectores REALES."
)

CUERPOS_REALES["CP044"] = f'''
raise NotImplementedError("CP044 (RF-06 - Eliminar con una sola fila marcada): {_MOTIVO_BLOQUEO_CP044_045}")
'''

CUERPOS_REALES["CP045"] = f'''
raise NotImplementedError("CP045 (RF-06 - Eliminaci\\u00f3n masiva de varias filas marcadas): {_MOTIVO_BLOQUEO_CP044_045} Ademas, tras usar el unico registro descartable conocido (2408) para CP044, no queda un 2do registro descartable disponible para una eliminacion masiva.")
'''

_MOTIVO_BLOQUEO_CP046_047 = (
    "DEFECTO/BLOQUEO REAL confirmado en vivo 28/09/2026 (ver "
    "_exploracion/explore_51_rf06_alta_todas_sucursales.py y "
    "explore_58_rf06_cp046_solo.py): CUALQUIER intento de Grabar un Alta "
    "-sea con una Ficha inventada (999001) O CON UNA FICHA REAL YA "
    "ASIGNADA (4504, la del inspector 1381)- falla igual con 'Error de "
    "Servicio: Error al validar la ficha.' ANTES de llegar a evaluar la "
    "regla de negocio especifica de este caso. Coincide exactamente con "
    "el riesgo YA documentado en el EF (Seccion 11): 'el alta de un nuevo "
    "inspector depende de un mecanismo de generacion de codigo "
    "correlativo y de resolucion del area asociada a la sucursal, "
    "provistos por un servicio de catalogos compartido; su disponibilidad "
    "... es un prerrequisito de cierre'. No hay nada que hacer desde la "
    "automatizacion hasta que ese servicio este disponible en Pruebas."
)

CUERPOS_REALES["CP046"] = f'''
raise NotImplementedError("CP046 (RF-06 - Alta de inspector con Ficha ya asignada): {_MOTIVO_BLOQUEO_CP046_047}")
'''

CUERPOS_REALES["CP047"] = f'''
raise NotImplementedError("CP047 (RF-06 - Alta exitosa con Todas las sucursales marcada): {_MOTIVO_BLOQUEO_CP046_047}")
'''

_MOTIVO_CP048_NO_AUTOMATIZADO = (
    "Verificado en vivo con evidencia real esta sesion (28/09/2026, ver "
    "_exploracion/explore_53_rf06_modificar_2408.py y "
    "explore_59..61_rf06_*.py): la regla se cumple exactamente - al "
    "modificar Nombre/Proveedor/Sucursal del inspector real 1381 y "
    "grabar ('Grabaci\\u00f3n exitosa.' confirmado), la grilla mostro "
    "Sucursal y \\u00c1rea SIN CAMBIOS (Sin Sucursal / 3521) pese a haber "
    "elegido una Sucursal distinta en el combo, tal cual describe la "
    "regla. HALLAZGO REAL ADICIONAL: 'Detalles' sobre un inspector "
    "INACTIVO muestra los campos deshabilitados (solo lectura) - "
    "Modificar de verdad requiere un inspector ACTIVO real, ya que el "
    "unico registro 100% descartable (2408) quedo Inactivo tras CP044 y "
    "Alta (que generaria uno nuevo) esta bloqueado (ver CP046/047). NO "
    "se deja como caso automatizado repetible: probarlo con datos reales "
    "obliga a modificar temporalmente un inspector real (1381) y "
    "restaurarlo despues - un flujo de escritura+restauracion en 2 pasos "
    "que, si el 2do paso (restaurar) llega a fallar a mitad de camino "
    "(confirmado inestable: el cierre de los modales anidados de esta "
    "pantalla fallo de forma intermitente durante esta misma "
    "verificacion), deja datos REALES modificados sin revertir. Ya se "
    "restauro manualmente 1381 a sus valores originales "
    "(Nombre='Rodriguez Medina Abel', Proveedor='LUZ DEL SUR S.A.A.', "
    "confirmado en explore_61) tras esta verificacion."
)

CUERPOS_REALES["CP048"] = f'''
raise NotImplementedError("CP048 (RF-06 - Modificaci\\u00f3n: Sucursal y \\u00c1rea no se actualizan): {_MOTIVO_CP048_NO_AUTOMATIZADO}")
'''

# RF-07 "Consulta de Cortes Pendientes" (CP049-CP056) - bodies reales,
# confirmados en vivo el 28/09/2026 (ver
# _exploracion/explore_13..19_rf07_*.py). Filtrar por CUALQUIER Sucursal
# real (Cañete/Chacarilla/Chorrillos/Chosica/La República/Miraflores/
# Pedro Miotta/San Bartolo/San Juan/Santa Anita/Sin Sucursal) ya trae
# resultados reales combinados - no requiere un cliente puntual.

CUERPOS_REALES["CP049"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
elegir_select_cortes(app, frame, "fld-sucursal", "Miraflores")
capturar_paso(app, "sucursal_seleccionada", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado is None, f"No se esperaba ningun dialogo de validacion: {resultado!r}"
filas = filas_cortes_pendientes(frame)
assert filas.count() > 0, "Se esperaba al menos 1 corte pendiente combinado para la Sucursal Miraflores"
capturar_paso(app, "resultado_combinado_cargado", paso_excel=1)
'''

CUERPOS_REALES["CP050"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
elegir_select_cortes(app, frame, "fld-tipo-fecha", "=")
campo_fecha_ini = frame.locator('input[aria-label="Fecha inicial"]')
campo_fecha_ini.click()
campo_fecha_ini.press_sequentially("31/02/2026")
app.wait_for_timeout(400)
capturar_paso(app, "fecha_invalida_ingresada", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado and "fecha inv" in resultado.lower(), f"No se vio el mensaje esperado 'Fecha Inválida': {resultado!r}"
capturar_paso(app, "mensaje_fecha_invalida", paso_excel=1)
'''

CUERPOS_REALES["CP051"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
elegir_select_cortes(app, frame, "fld-tipo-fecha", "=")
capturar_paso(app, "tipo_fecha_sin_fecha_inicial", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado and "rango inferior" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Debe Seleccionar Rango Inferior de Fecha': {resultado!r}"
)
capturar_paso(app, "mensaje_rango_inferior_obligatorio", paso_excel=1)
'''

CUERPOS_REALES["CP054"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
capturar_paso(app, "sin_ningun_filtro", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado and "alg" in resultado.lower() and "filtro" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Debe Seleccionar algún filtro para la consulta': {resultado!r}"
)
capturar_paso(app, "mensaje_filtro_obligatorio", paso_excel=1)
'''

_MOTIVO_BLOQUEO_RF07_FECHA = (
    "DEFECTO REAL confirmado en vivo el 28/09/2026: ingresar una fecha "
    "calendario VALIDA en el filtro F. Corte congela la pantalla por "
    "completo (reproducido 5 veces, con press_sequentially, .fill(), "
    "click en el calendario visual y click en el boton 'Hoy', tanto en "
    "modo '=' como 'Entre' - ningun metodo de interaccion lo evita). No "
    "hay excepcion de JS, error de consola, ni dialogo nativo bloqueante "
    "- el popup simplemente deja de responder a cualquier operacion "
    "(screenshot, input_value, nuevos clicks) por 30s+. Una fecha "
    "INVALIDA (CP050) o el campo vacio (CP051) NO producen el freeze - "
    "es especifico de un valor de fecha calendario real. Ver ficha "
    "tecnica de _framework/modulos/consulta_cortes_pendientes.py para el "
    "detalle completo - reportar como defecto real, no reintentar sin un "
    "cambio en el ambiente."
)

CUERPOS_REALES["CP052"] = f'''
raise NotImplementedError("CP052 (RF-07 - Rango superior obligatorio en filtro Entre): {_MOTIVO_BLOQUEO_RF07_FECHA}")
'''

CUERPOS_REALES["CP053"] = f'''
raise NotImplementedError("CP053 (RF-07 - Rango de fechas amplio): {_MOTIVO_BLOQUEO_RF07_FECHA}")
'''

CUERPOS_REALES["CP055"] = '''
# RN-14 (comportamiento conocido, NO corregido segun el EF): seleccionar
# UNICAMENTE Estado Libro deberia ser un filtro valido para el universo
# de cortes de libro, pero la pantalla real igual rechaza la busqueda
# con el mismo mensaje que "sin ningun filtro". Confirmado en vivo tal
# cual lo documenta el EF - se prueba el comportamiento REAL (rechazo),
# no el ideal.
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
elegir_select_cortes(app, frame, "fld-estado-libro", "ACTUALIZADO")
capturar_paso(app, "solo_estado_libro_seleccionado", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado and "alg" in resultado.lower() and "filtro" in resultado.lower(), (
    f"Comportamiento conocido (RN-14): se esperaba el mismo mensaje de 'falta filtro' pese a tener Estado Libro seleccionado: {resultado!r}"
)
capturar_paso(app, "mensaje_filtro_pese_a_estado_libro", paso_excel=1)
'''

CUERPOS_REALES["CP056"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
frame.locator("#fld-cliente").fill("99999999")
capturar_paso(app, "cliente_inexistente_ingresado", paso_excel=1)
resultado = leer_cortes_pendientes(app, frame)
assert resultado and "no existen datos" in resultado.lower(), (
    f"No se vio el mensaje esperado 'No existen datos de la consulta': {resultado!r}"
)
capturar_paso(app, "mensaje_sin_resultados", paso_excel=1)
'''

# RF-09 "Consulta Generica de Solicitudes de Reposicion" (CP064-CP071) -
# bodies reales confirmados en vivo el 28/09/2026 (ver
# _exploracion/explore_28..31_rf09_*.py). CP065/066/067 no requieren
# fecha valida - OK real. CP064/068/069/070/071 SI requieren ingresar una
# fecha valida - BLOQUEADOS por el mismo defecto real de freeze ya
# encontrado en RF-07 (ver ficha tecnica de
# _framework/modulos/consulta_generica_reposiciones.py).

CUERPOS_REALES["CP065"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
capturar_paso(app, "sin_tipo_de_fecha_elegido", paso_excel=1)
frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(800)
resultado = cerrar_ventana_validacion_reposiciones(app, frame)
assert resultado and "filtro de fechas" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Debe Seleccionar Filtro de Fechas': {resultado!r}"
)
capturar_paso(app, "mensaje_filtro_fecha_obligatorio", paso_excel=1)
'''

CUERPOS_REALES["CP066"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
elegir_select_reposiciones(app, frame, "fldTipoFecha")
campo_fecha_ini = frame.locator("#fldFechaIni")
campo_fecha_ini.click()
campo_fecha_ini.press_sequentially("31/02/2026")
app.wait_for_timeout(500)
capturar_paso(app, "fecha_invalida_ingresada", paso_excel=1)
frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(800)
resultado = cerrar_ventana_validacion_reposiciones(app, frame)
assert resultado and "fecha inv" in resultado.lower(), f"No se vio el mensaje esperado 'Fecha Inválida': {resultado!r}"
capturar_paso(app, "mensaje_fecha_invalida", paso_excel=1)
'''

CUERPOS_REALES["CP067"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
elegir_select_reposiciones(app, frame, "fldTipoFecha")
capturar_paso(app, "tipo_fecha_sin_fecha_inicial", paso_excel=1)
frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(800)
resultado = cerrar_ventana_validacion_reposiciones(app, frame)
assert resultado and "rango inferior" in resultado.lower(), (
    f"No se vio el mensaje esperado 'Debe Seleccionar Rango Inferior de Fecha': {resultado!r}"
)
capturar_paso(app, "mensaje_rango_inferior_obligatorio", paso_excel=1)
'''

_MOTIVO_BLOQUEO_RF09_FECHA = (
    "DEFECTO REAL confirmado en vivo el 28/09/2026: ingresar una fecha "
    "calendario VALIDA en el filtro de Fecha de Solicitud congela la "
    "pantalla por completo - mismo defecto ya confirmado en RF-07 "
    "'Consulta de Cortes Pendientes' (2 pantallas Angular distintas, "
    "mismo sintoma). Reproducido con escritura normal Y con delay de "
    "300ms/caracter (descarta que sea la velocidad de automatizacion). "
    "Una fecha invalida o el campo vacio NO producen el freeze. Ver "
    "ficha tecnica de _framework/modulos/consulta_generica_reposiciones.py "
    "para el detalle completo - reportar como defecto real, probablemente "
    "compartido entre varias pantallas de este sprint que usan el mismo "
    "componente de fecha."
)

# RF-08 "Consulta de Solicitudes de Reposicion Pendientes" (CP057-CP063)
# - RE-VERIFICADO EN VIVO 28/10/2026: el "combo roto" documentado el
# 28/09/2026 NO se reproduce un mes despues (misma cuenta DCABA_DW) -
# ambos nz-select cargan con datos reales. Ver ficha tecnica completa
# en _framework/modulos/consulta_solicitudes_reposicion_pendientes.py.
#
# CP062 confirmado con dato real: Leer sin ningun filtro puesto ->
# modal de Ventana de Validacion real EXACTO: "Debe Seleccionar algún
# filtro para la consulta".
#
# CP057-061/063 QUEDAN PENDIENTES (28/10/2026): backend/combos
# confirmados operativos, falta terminar la exploracion en vivo de cada
# validacion puntual (busqueda con resultados reales, limites de rango,
# Anular) - no alcanzo el tiempo en esta sesion.

_MOTIVO_PENDIENTE_RF08 = (
    "combos y backend confirmados operativos el 28/10/2026 (el 'combo roto' documentado el "
    "28/09/2026 no se reproduce) - falta terminar la exploracion en vivo de esta validacion "
    "puntual. Ver _framework/modulos/consulta_solicitudes_reposicion_pendientes.py."
)

CUERPOS_REALES["CP057"] = f'''
raise NotImplementedError("CP057 (RF-08 - Busqueda exitosa de solicitudes pendientes): {_MOTIVO_PENDIENTE_RF08}")
'''
CUERPOS_REALES["CP058"] = f'''
raise NotImplementedError("CP058 (RF-08 - Validacion de fecha invalida): {_MOTIVO_PENDIENTE_RF08}")
'''
CUERPOS_REALES["CP059"] = f'''
raise NotImplementedError("CP059 (RF-08 - Rango inferior obligatorio no ingresado): {_MOTIVO_PENDIENTE_RF08}")
'''
CUERPOS_REALES["CP060"] = f'''
raise NotImplementedError("CP060 (RF-08 - Rango superior obligatorio en filtro Entre): {_MOTIVO_PENDIENTE_RF08}")
'''
CUERPOS_REALES["CP061"] = f'''
raise NotImplementedError("CP061 (RF-08 - Rango de fechas, comportamiento configurable): {_MOTIVO_PENDIENTE_RF08}")
'''

CUERPOS_REALES["CP062"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial_sin_filtros", paso_excel=2)

mensaje = leer_reposicion_pendientes(app, frame)
capturar_paso(app, "mensaje_al_menos_un_filtro", paso_excel=3)
assert mensaje is not None and "filtro" in mensaje.lower() and "seleccionar" in mensaje.lower(), (
    f"Se esperaba el mensaje de 'debe seleccionar algun filtro': {mensaje!r}"
)
'''

CUERPOS_REALES["CP063"] = f'''
raise NotImplementedError("CP063 (RF-08 - Anular exitoso): {_MOTIVO_PENDIENTE_RF08}")
'''

CUERPOS_REALES["CP064"] = f'''
raise NotImplementedError("CP064 (RF-09 - Búsqueda exitosa usando únicamente el filtro de fecha): {_MOTIVO_BLOQUEO_RF09_FECHA}")
'''

CUERPOS_REALES["CP068"] = f'''
raise NotImplementedError("CP068 (RF-09 - Rango superior obligatorio en filtro Entre): {_MOTIVO_BLOQUEO_RF09_FECHA}")
'''

CUERPOS_REALES["CP069"] = f'''
raise NotImplementedError("CP069 (RF-09 - Rango de fechas amplio): {_MOTIVO_BLOQUEO_RF09_FECHA}")
'''

CUERPOS_REALES["CP070"] = f'''
raise NotImplementedError("CP070 (RF-09 - Consulta genérica incluye solicitudes anuladas): {_MOTIVO_BLOQUEO_RF09_FECHA}")
'''

CUERPOS_REALES["CP071"] = f'''
raise NotImplementedError("CP071 (RF-09 - Búsqueda sin resultados): {_MOTIVO_BLOQUEO_RF09_FECHA}")
'''

# RF-02/03/04/06 requieren la cuenta DCABA_DW (le faltan roles funcionales
# a SCASTI_DW - ver memoria project_pr000349_sp2_status y ficha tecnica de
# cada modulo). CP009-030, CP038-048, CP049-056, CP072 usan DCABA_DW; el
# resto sigue con SCASTI_DW (default de add()).
#
# CP049-056 (RF-07) agregado 28/10/2026: confirmado en vivo que el menu
# "Comercial > Consulta De Cortes Pendientes" NO aparece con SCASTI_DW
# (RuntimeError "No se encontro un enlace de menu visible" en los 72
# casos de esa corrida) pero SI aparece y abre bien con DCABA_DW -
# mismo patron ya visto en otras RF de este proyecto (rol/acceso
# presente en una cuenta y no en la otra).
_CPS_DCABA_DW = {f"CP{n:03d}" for n in range(9, 25)} | {f"CP{n:03d}" for n in range(25, 38)} | {f"CP{n:03d}" for n in range(38, 64)} | {"CP072"}

# --- Un add() por cada uno de los 72 casos de matriz_casos.json, en orden ---
for _cp in sorted(MATRIZ, key=lambda x: int(x[2:])):
    _m = MATRIZ[_cp]
    _body = CUERPOS_REALES.get(_cp) or _body_pendiente(_cp, _m["rf"], _m["name"])
    if _cp in _CPS_DCABA_DW:
        add(_cp, _body, usuario="DCABA_DW", password="Melquisedec_01")
    else:
        add(_cp, _body)


if __name__ == "__main__":
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
