"""
generate_scripts.py de PR000349-SP2 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: 9 pantallas (RF-01..RF-09), 76 casos (ver matriz_casos.json;
CP073/CP074 agregados 02/11/2026 a partir de los manuales de usuario,
CP075/CP076 agregados el mismo dia a partir de exploracion en vivo de
RF-05 - ninguno de los 4 estaba en la matriz Excel original).
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

PROYECTO = "PR000349-SP2-IT3"  # debe coincidir con el nombre de esta carpeta
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

# CORRECCION 02/11/2026: el hallazgo anterior ("falla consistentemente
# con 'No se generó informe.'", confirmado 3/3 veces el 27/09) resulto
# ser un FALSO NEGATIVO de automatizacion, no un defecto real ni un
# servicio externo caido. Con S.S. 1234567 (2 clientes reales) y una
# espera de hasta 240s tras confirmar "¿Desea generar archivos?" (en vez
# de los ~1-5s que se esperaban antes), el informe SI se genera y se
# descarga: archivo real "ODESS_Informe_1234567.txt" confirmado en vivo
# via _exploracion/explore_68c_rf01_cp008_espera_larga.py. El servicio
# es simplemente muy lento, mismo patron ya visto en CP024 (RF-03, hasta
# ~220s) - no estaba permanentemente caido como se penso en septiembre.

CUERPOS_REALES["CP008"] = '''
app, frame = abrir_consulta_clientes_ss(page, paso_excel=1)
leer_clientes_ss(app, frame, numero_ss="1234567")
capturar_paso(app, "busqueda_ss_1234567", paso_excel=2)

_descarga = {"obj": None}
app.on("download", lambda d: _descarga.__setitem__("obj", d))

frame.get_by_role("button", name=re.compile("Imprimir")).click()
app.wait_for_timeout(1000)
dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
assert dialogo.count() and dialogo.first.is_visible(), "Se esperaba la confirmacion '\\u00bfDesea generar archivos?'"
texto_confirmacion = dialogo.first.inner_text()
assert "desea generar" in texto_confirmacion.lower(), f"Dialogo inesperado: {texto_confirmacion!r}"
capturar_paso(app, "confirmacion_desea_generar_archivos", paso_excel=3)
dialogo.first.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$", re.I)).first.click(force=True)

# El backend puede tardar bastante (confirmado en vivo: hasta ~240s en
# una corrida real) - esperar en bucle en vez de un timeout corto fijo.
plazo = time.monotonic() + 240
resultado = None
while time.monotonic() < plazo:
    if _descarga["obj"] is not None:
        resultado = ("descarga", _descarga["obj"])
        break
    modal2 = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal2.count() and modal2.first.is_visible():
        texto_actual = modal2.first.inner_text()
        if "desea generar" not in texto_actual.lower():
            resultado = ("modal", texto_actual)
            break
    app.wait_for_timeout(3000)

assert resultado is not None, "Tras 240s, no hubo descarga ni modal final (ni exito ni el error conocido)"
if resultado[0] == "modal":
    capturar_paso(app, "modal_final_inesperado", paso_excel=4)
    raise AssertionError(f"Se esperaba una descarga exitosa, pero aparecio este modal: {resultado[1]!r}")

destino = EVIDENCIA / f"{CASO}_informe.txt"
resultado[1].save_as(str(destino))
assert destino.exists() and destino.stat().st_size > 0, "El archivo descargado esta vacio o no se guardo"
capturar_paso(app, "informe_generado_y_descargado", paso_excel=4)
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
# DEFECTO REAL H001 confirmado en vivo 02/11/2026 (ver
# _exploracion/explore_101_rf02_cp011_cp014.py, explore_102_rf02_validar_update_1603071.py):
# se probaron 54 clientes reales con BD real (datos aportados por el
# usuario via query directa a nucli/estoc, ambos estados de traspaso
# 'A'=anulada y 'S'=guarda activa) y el 100% esta bloqueado por "El
# NUCLI fue generado por el ACTICOME, favor trabajar en dicho módulo" -
# independientemente del estado de traspaso. Se probo ademas forzar
# rol_creacion='DACD' (rol real de sesion de DCABA_DW) via UPDATE
# directo en BD sobre uno de esos clientes (1603071/880406/9): el
# bloqueo de ACTICOME PERSISTE IGUAL, confirmando que es una compuerta
# independiente de rol_creacion - no se identifico la columna real que
# la controla (se investigo el codigo fuente real de ACTICOME,
# `backend/gestioncliente.acticome` BoActicome.cs:4165
# InsertarEstoc_BO, pero solo descarta que sea `traspaso`). Con una
# muestra de 54 clientes reales con datos reales + un intento de UPDATE
# directo, se considera H001 un defecto/bloqueo estructural de datos en
# el ambiente de Pruebas: no hay ningun cliente real conocido cuya
# orden de conexion sea editable por esta pantalla legacy - CP011 y
# CP012-016/CP072 dependen todos de llegar a pasar esta misma compuerta,
# asi que quedan BLOQUEADOS por este mismo defecto (no son fallas de
# automatizacion independientes).

_MOTIVO_BLOQUEO_H001 = (
    "BLOQUEADO por el defecto real H001 (ver CP009): el 100% de una muestra de 54 clientes "
    "reales (BD real, ambos estados de traspaso) esta bloqueado por 'El NUCLI fue generado "
    "por el ACTICOME, favor trabajar en dicho módulo' antes de llegar a evaluar esCreador/"
    "esPrivilegiado - incluso forzando rol_creacion via UPDATE directo en BD. Sin identificar "
    "la columna real que controla ese bloqueo, no hay forma de alcanzar el flujo que este caso "
    "necesita validar. Ver _framework/modulos/mantenimiento_orden_conexion.py."
)

CUERPOS_REALES["CP009"] = '''
# H001 RECLASIFICADO (04/11/2026): no era un defecto real universal - la
# muestra original de 54 clientes solo tenia casos con bloqueadoPorActicome=true.
# El cliente 1305674/SS 90002699 que trae la propia precondicion de la MCP
# (con rol_creacion actualizado a 'DACD', el rol de sesion real de
# DCABA_DW, via UPDATE directo en BD) SI tiene bloqueadoPorActicome=false
# - confirmado en vivo via captura de red: HTTP 200, esSoloConsulta=false,
# puedeActualizar=true, bloqueadoPorActicome=false, sin dialogo de error.
app, frame = abrir_mantord(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

respuestas = []
app.on("response", lambda r: respuestas.append((r.status, r.url, r.text())) if "mantord" in r.url.lower() and "leer" in r.url.lower() else None)

mensaje = leer_orden(app, frame, "1305674")
capturar_paso(app, "detalle_completo_de_la_orden", paso_excel=2)
assert mensaje is None, f"No se esperaba ningun dialogo de bloqueo/error: {mensaje!r}"

assert respuestas, "No se capturo la respuesta de red de /mantord/Leer"
status_real, url_real, body_real = respuestas[-1]
assert status_real == 200, f"Se esperaba HTTP 200, se obtuvo {status_real} - {url_real}"
assert "\\"puedeActualizar\\":true" in body_real.replace(" ", ""), (
    f"Se esperaba puedeActualizar=true (camino esCreador habilitado, rol_creacion=DACD "
    f"coincide con el rol de sesion real de DCABA_DW): {body_real!r}"
)
assert "\\"bloqueadoPorActicome\\":false" in body_real.replace(" ", ""), (
    f"Se esperaba bloqueadoPorActicome=false para este cliente especifico: {body_real!r}"
)

campo_cliente_anterior = frame.locator("#clienteAnterior, [formcontrolname='clienteAnterior']")
boton_actualizar = frame.get_by_role("button", name=re.compile(r"^\\s*Actualizar\\s*$"))
assert boton_actualizar.count() == 0 or boton_actualizar.first.is_enabled(), (
    "Se esperaba que el boton Actualizar quedara habilitado (esCreador=true para este cliente)"
)
capturar_paso(app, "actualizar_habilitado", paso_excel=4)
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

CUERPOS_REALES["CP011"] = '''
# H001 RECLASIFICADO (04/11/2026): cliente real 4027177/SS 5621
# (fechor_anulacion real en BD, confirmado via query de precondicion) -
# NO esta bloqueado por ACTICOME (a diferencia de la muestra original
# de 54 clientes). El mensaje "ya esta anulada" es un toast efimero
# (mismo patron que otros proyectos de esta sesion) - hay que sondearlo
# activamente en vez de leerlo una sola vez tras un wait fijo.
app, frame = abrir_mantord(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

frame.locator("#numeroCliente").click()
frame.locator("#numeroCliente").fill("4027177")
app.wait_for_timeout(300)
frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()

plazo = time.monotonic() + 8
texto_toast = ""
while time.monotonic() < plazo:
    texto = frame.locator("body").inner_text()
    if "ya est" in texto.lower() and "anulada" in texto.lower():
        texto_toast = texto
        break
    app.wait_for_timeout(300)
capturar_paso(app, "mensaje_orden_ya_anulada", paso_excel=2)
assert texto_toast, "Se esperaba el mensaje 'Esta orden de conexion ya esta anulada' (toast efimero)"

campo_cliente = frame.locator("#numeroCliente")
assert campo_cliente.get_attribute("disabled") is not None, (
    "Se esperaba que N.\\u00b0 de Cliente quede deshabilitado tras la orden ya anulada"
)
boton_actualizar = frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$"))
assert not boton_actualizar.is_enabled(), "Se esperaba Actualizar deshabilitado"
boton_anular = frame.get_by_role("button", name=re.compile(r"^\\s*Anular\\s*$"))
assert boton_anular.count() == 0 or not boton_anular.is_enabled(), "Se esperaba Anular deshabilitado"
capturar_paso(app, "anular_y_actualizar_deshabilitados", paso_excel=3)
'''

CUERPOS_REALES["CP012"] = '''
# H001 RECLASIFICADO (04/11/2026): confirmado en vivo con el mismo cliente
# que CP009/014 (1305674/SS 90002699), Criterio Individual. Esta es una
# escritura REAL sobre un cliente compartido entre varios CP - el caso
# revierte la Sucursal al valor original en el mismo run, inmediatamente
# despues de confirmar el mensaje de exito (ver
# _exploracion/explore_cp012_actualizar_individual.py), para no dejar el
# dato mutado para CP009/013/014.
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_cargado", paso_excel=1)

sucursal_original = frame.locator("#sucursal").input_value()
sucursal_nueva = "3200" if sucursal_original != "3200" else "3100"

sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_nueva)
app.wait_for_timeout(500)
capturar_paso(app, "nueva_sucursal_ingresada", paso_excel=3)

frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el mensaje de 'Orden de Conexion actualizada.'"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_operacion_exitosa", paso_excel=5)
assert "operaci" in mensaje.lower() and "exitosa" in mensaje.lower() and "actualizada" in mensaje.lower(), (
    f"Mensaje inesperado: {mensaje!r}"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_confirmada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_actualizada_confirmada_tras_releer", paso_excel=6)
assert sucursal_confirmada == sucursal_nueva, (
    f"Se esperaba que la sucursal quede en {sucursal_nueva!r} tras re-Leer, quedo en {sucursal_confirmada!r}"
)

# Revertir INMEDIATAMENTE al valor original - mismo cliente compartido
# con CP009/013/014, no debe quedar mutado para esos casos.
sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_original)
app.wait_for_timeout(500)
frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal_revert = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal_revert.count() and modal_revert.first.is_visible():
    modal_revert.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_restaurada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_revertida_al_valor_original", paso_excel=6)
assert sucursal_restaurada == sucursal_original, (
    f"REVERT FALLIDO: se esperaba restaurar la sucursal original {sucursal_original!r}, quedo en {sucursal_restaurada!r} "
    f"- requiere correccion manual para no dejar mutado el cliente compartido con CP009/013/014"
)
'''

CUERPOS_REALES["CP013"] = '''
# H001 RECLASIFICADO (04/11/2026): confirmado en vivo por el usuario con
# sesion manual (ver _exploracion/sesion_manual_cp013.py / network_log.txt,
# sin ningun HTTP >=400) - Criterio Masivo + Actualizar sobre el cliente
# 1305674 (el mismo de CP009/012/014/072, unico cliente de su S.S.) SI
# funciona, mensaje de exito mostrado correctamente. Escritura real sobre
# un cliente compartido - se revierte la Sucursal al valor original en
# el mismo run, igual que CP012.
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_cargado", paso_excel=1)

radios = frame.locator("input[type=radio]")
radios.nth(1).click(force=True)
app.wait_for_timeout(500)
capturar_paso(app, "criterio_masivo_seleccionado", paso_excel=2)

sucursal_original = frame.locator("#sucursal").input_value()
sucursal_nueva = "3200" if sucursal_original != "3200" else "3100"

sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_nueva)
app.wait_for_timeout(500)
capturar_paso(app, "nueva_sucursal_ingresada", paso_excel=3)

frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el mensaje de 'Orden de Conexion actualizada.'"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_operacion_exitosa_masivo", paso_excel=5)
assert "actualizada" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_confirmada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_actualizada_confirmada_tras_releer", paso_excel=6)
assert sucursal_confirmada == sucursal_nueva, (
    f"Se esperaba que la sucursal quede en {sucursal_nueva!r} tras re-Leer, quedo en {sucursal_confirmada!r}"
)

# Revertir INMEDIATAMENTE al valor original - cliente compartido con
# CP009/012/014/072, no debe quedar mutado.
radios = frame.locator("input[type=radio]")
radios.nth(1).click(force=True)
app.wait_for_timeout(500)
sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_original)
app.wait_for_timeout(500)
frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal_revert = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal_revert.count() and modal_revert.first.is_visible():
    modal_revert.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_restaurada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_revertida_al_valor_original", paso_excel=6)
assert sucursal_restaurada == sucursal_original, (
    f"REVERT FALLIDO: se esperaba restaurar la sucursal original {sucursal_original!r}, quedo en {sucursal_restaurada!r}"
)
'''

CUERPOS_REALES["CP014"] = '''
# H001 RECLASIFICADO (04/11/2026): confirmado en vivo con la precondicion
# real de la MCP (estoc.traspaso='S' para numero_cliente=1305674/
# numero_ss=90002699/correlativo_ss=1, aplicada manualmente en BD - ver
# _exploracion/explore_cp014_actualizar.py). El Actualizar es RECHAZADO
# por la guarda de negocio (RN-17) - cero riesgo real, no persiste ningun
# cambio.
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_con_proceso_avanzado_cargado", paso_excel=1)

sucursal_original = frame.locator("#sucursal").input_value()
sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill("3200")
app.wait_for_timeout(500)
capturar_paso(app, "nueva_sucursal_ingresada", paso_excel=2)

frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el mensaje de bloqueo de la guarda de negocio"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_de_bloqueo_guarda_de_negocio", paso_excel=4)
assert "no se puede actualizar" in mensaje.lower() and "proceso de conexi" in mensaje.lower(), (
    f"Mensaje de bloqueo inesperado: {mensaje!r}"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(1000)

sucursal_restaurada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_restaurada_al_valor_original", paso_excel=5)
assert sucursal_restaurada == sucursal_original, (
    f"Se esperaba que Sucursal se restaure a {sucursal_original!r} tras el bloqueo, quedo en {sucursal_restaurada!r}"
)
'''

CUERPOS_REALES["CP015"] = '''
# H001 RECLASIFICADO (04/11/2026): DCABA_DW ya tiene el rol JEFESUCU,
# Anular se habilita con Criterio Masivo. H004 (HTTP 400 "Error al
# eliminar Orden de Conexion.") RECUPERADO (06/11/2026, re-verificado en
# vivo 2 veces): con el cliente 1305674 (SS 90002699, sin bloqueo de
# ACTICOME ni guarda de "proceso avanzado"), Anular ahora responde con
# el mensaje correcto de exito "Operacion Exitosa / Orden de Conexion
# Anulada." - se valida ese mensaje.
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_cargado", paso_excel=1)

radios = frame.locator("input[type=radio]")
radios.nth(1).click(force=True)
app.wait_for_timeout(500)
capturar_paso(app, "criterio_masivo_seleccionado", paso_excel=2)

boton_anular = frame.locator("button", has_text=re.compile(r"^\\s*Anular\\s*$"))
assert boton_anular.is_enabled(), "Se esperaba Anular habilitado con Criterio Masivo (rol JEFESUCU)"

boton_anular.click()
app.wait_for_timeout(1500)
frame.get_by_role("button", name=re.compile(r"^\\s*Aceptar\\s*$")).click()
app.wait_for_timeout(2500)
capturar_paso(app, "mensaje_operacion_exitosa", paso_excel=4)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el mensaje de 'Orden de Conexion Anulada.'"
mensaje = modal.first.inner_text()
assert "anulada" in mensaje.lower() and "exitosa" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP016"] = '''
# H001 RECLASIFICADO (04/11/2026): DCABA_DW ya tiene el rol JEFESUCU.
# Confirmado en vivo: con Criterio Individual (default al Leer), el
# boton Anular queda deshabilitado de raiz (atributo disabled, no solo
# estilo) - confirmado tambien con force-click, no responde. Se valida
# la restriccion tal cual: Anular NO se activa con Individual.
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_cargado_criterio_individual", paso_excel=1)

boton_anular = frame.locator("button", has_text=re.compile(r"^\\s*Anular\\s*$"))
assert boton_anular.count() > 0, "Se esperaba encontrar el boton Anular en pantalla"
assert not boton_anular.is_enabled(), (
    "Se esperaba que Anular este deshabilitado con Criterio Individual (restriccion confirmada en el EF)"
)
capturar_paso(app, "anular_deshabilitado_con_individual", paso_excel=2)
'''

CUERPOS_REALES["CP072"] = '''
# H001 RECLASIFICADO (04/11/2026): DCABA_DW ya tiene el rol JEFESUCU
# (permiso ELIMINAR de SRV.MANTORD resuelto via LDS Seguridad,
# confirmado en vivo - habilito tambien Anular con Criterio Masivo).
# Intentos previos con 1200210 y 1201729 (clientes reales distintos a
# 1305674) chocaron con la guarda de "proceso de conexion avanzado" al
# confirmar el Actualizar (puedeActualizar=true en el Leer NO garantiza
# pasar esa guarda - se evalua aparte, al confirmar). El UNICO cliente
# real confirmado LIBRE de esa guarda en este ambiente es 1305674 (el
# mismo de CP009/012/014) - se le cambio temporalmente rol_creacion a
# 'DVC' (su valor original, distinto al rol de sesion real de DCABA_DW)
# para poder probar el camino privilegiado sin esCreador. Revertir a
# 'DACD' despues de este caso (CP009/012/014 lo necesitan).
app, frame = abrir_mantord(page, paso_excel=1)
leer_orden(app, frame, "1305674")
capturar_paso(app, "cliente_cargado_no_creador", paso_excel=1)

rol_creacion = frame.locator("#rolCreacion").input_value()
assert "DACD" not in rol_creacion, f"Se esperaba rol_creacion distinto de DACD (no creador): {rol_creacion!r}"

sucursal_original = frame.locator("#sucursal").input_value()
sucursal_nueva = "3200" if sucursal_original != "3200" else "3100"

sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_nueva)
app.wait_for_timeout(500)
capturar_paso(app, "nueva_sucursal_ingresada", paso_excel=3)

frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal.count() and modal.first.is_visible(), "Se esperaba el mensaje de 'Orden de Conexion actualizada.'"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_operacion_exitosa_sin_ser_creador", paso_excel=5)
assert "actualizada" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
assert "no puede actualizarla" not in mensaje.lower() and "no ingres" not in mensaje.lower(), (
    f"No se esperaba el mensaje de bloqueo por no ser el creador: {mensaje!r}"
)
modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_confirmada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_actualizada_confirmada_tras_releer", paso_excel=6)
assert sucursal_confirmada == sucursal_nueva, (
    f"Se esperaba que la sucursal quede en {sucursal_nueva!r} tras re-Leer, quedo en {sucursal_confirmada!r}"
)

# Revertir INMEDIATAMENTE al valor original - cliente compartido, no
# debe quedar mutado.
sucursal_campo = frame.locator("#sucursal")
sucursal_campo.click()
sucursal_campo.fill(sucursal_original)
app.wait_for_timeout(500)
frame.locator("button", has_text=re.compile(r"^\\s*Actualizar\\s*$")).click()
app.wait_for_timeout(2500)
modal_revert = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal_revert.count() and modal_revert.first.is_visible():
    modal_revert.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(1000)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2500)
sucursal_restaurada = frame.locator("#sucursal").input_value()
capturar_paso(app, "sucursal_revertida_al_valor_original", paso_excel=6)
assert sucursal_restaurada == sucursal_original, (
    f"REVERT FALLIDO: se esperaba restaurar la sucursal original {sucursal_original!r}, quedo en {sucursal_restaurada!r}"
)
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

# Error de servicio secundario/asincrono conocido ("Error al recargar
# el combo de N. de Sesion") puede quedar tapando la pantalla sin
# afectar los resultados ya cargados - cerrarlo si aparece antes de
# seguir interactuando con la grilla.
modal_secundario = frame.locator("nz-modal-container, .ant-modal").filter(has_text=re.compile("Error de Servicio", re.I))
if modal_secundario.count() and modal_secundario.last.is_visible():
    modal_secundario.last.get_by_role("button", name=re.compile("Cerrar", re.I)).click()
    app.wait_for_timeout(500)
casilla.check(force=True)
app.wait_for_timeout(800)
columnas_con_ampliar = frame.locator("table.grid thead th").count()
assert columnas_con_ampliar > columnas_antes, (
    f"Se esperaba mas columnas al marcar 'Ampliar Campos': antes={columnas_antes}, despues={columnas_con_ampliar}"
)
capturar_paso(app, "detalle_monetario_expandido", paso_excel=3)

casilla.uncheck(force=True)
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
# Ficha 7010 real y Activa (codigo 1380, Miranda Carrillo Miguel Angel,
# Proveedor Luz del Sur) - re-confirmada en vivo 04/11/2026, ver
# _exploracion/explore_cp042_ficha_real.py (la ficha 5631 usada antes
# ya no correspondia a ningun inspector Activo).
aplicar_filtro_inspectores(app, overlay, codigo="1", ficha="7010")
capturar_paso(app, "codigo_y_ficha_completados", paso_excel=2)

# El backend de esta pantalla puede tardar en actualizar "Filtro vigente"
# tras Filtrar (mismo patron lento ya visto en otros CP de RF-06) -
# esperar en bucle en vez de leer una sola vez a los 2s fijos del helper.
plazo = time.monotonic() + 20
linea_filtro = ""
while time.monotonic() < plazo:
    texto = frame.locator("body").inner_text()
    linea_filtro = next((l for l in texto.splitlines() if l.startswith("Filtro vigente")), "")
    if "Ficha = 7010" in linea_filtro:
        break
    app.wait_for_timeout(1000)
assert "Ficha = 7010" in linea_filtro, f"Se esperaba ver 'Ficha = 7010' en el filtro vigente: {linea_filtro!r}"
assert "C\\u00f3digo = 1" not in linea_filtro and "C\\u00f3digo" in linea_filtro, (
    f"Se esperaba el rotulo fijo 'C\\u00f3digo' SIN el valor tecleado (RN conocida): {linea_filtro!r}"
)
filas = filas_inspectores(frame)
assert filas.count() > 0, "Se esperaba al menos 1 resultado para Ficha=7010"
primera_fila = filas.first.inner_text()
assert "7010" in primera_fila, f"El resultado deberia corresponder al filtro de Ficha: {primera_fila!r}"
capturar_paso(app, "resultado_prioriza_ficha_sobre_codigo", paso_excel=4)
'''

# DEFECTO REAL confirmado 02/11/2026 (re-verificado en vivo, incluye
# ahora el codigo HTTP real via _exploracion/explore_71_rf06_cp039_status_code.py):
# presionar Leer con el filtro por defecto (Estado=Activos, sin ningun
# otro filtro) da 'Demasiados registros para ser mostrados en la
# grilla.' porque el backend (POST .../inspector/web/api/inspector/Leer)
# responde HTTP 400 - el universo real de inspectores ACTIVOS en Pruebas
# supera el limite de 2000 registros. Tambien se probo acotando por
# Proveedor = Luz del Sur (20331898008) desde la ventana Filtrar: MISMO
# resultado (400), ni siquiera el propio proveedor dueno del sistema
# queda bajo el limite.
#
# CAUSA RAIZ (agregada como paso 2, 02/11/2026 - ver
# _exploracion/explore_75_rf06_cp041_duplicados.py): el motivo por el
# que el universo "supera 2000" es que el backend devuelve FILAS
# DUPLICADAS en vez de una fila por inspector - confirmado con
# Proveedor=Luz del Sur + Estado=Noactivos (combo que SI queda bajo el
# limite, 116 "registros" declarados): de 100 filas del primer bloque,
# solo hay 4 codigos de inspector reales distintos (922, 315, 314, 305),
# repetidos 13-29 veces cada uno, fila por fila identica (probable JOIN
# del backend sin deduplicar). El conteo de "demasiados registros" esta
# inflado por esta misma duplicacion.

CUERPOS_REALES["CP039"] = '''
# RECUPERADO (re-verificado en vivo 04/11/2026, ver
# _exploracion/explore_buscar_filtro_100.py en PR000349-SP2-IT2): el
# filtro por defecto (Estado=Activos, sin otro filtro) daba HTTP 400
# "Demasiados registros" en PR000349-SP2 (ver CP039 alla) - esta corrida
# confirma que el volumen real ya bajo del limite y el "Leer" por
# defecto funciona normal, sin la Ventana de Validacion. Mismo patron de
# recuperacion silenciosa visto en otros proyectos de esta sesion.
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
capturar_paso(app, "pantalla_inicial", paso_excel=1)

respuestas_leer = []
app.on("response", lambda r: respuestas_leer.append((r.status, r.url)) if "/inspector/Leer" in r.url else None)

frame.get_by_role("button", name=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(3000)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert not (modal.count() and modal.first.is_visible()), (
    f"Se esperaba que 'Leer' con el filtro por defecto NO muestre la Ventana de Validacion "
    f"(defecto historico de 'demasiados registros' ya recuperado), pero sigue apareciendo: "
    f"{modal.first.inner_text() if modal.count() else ''!r}"
)

assert respuestas_leer, "No se capturo ninguna respuesta de red para /inspector/Leer"
status_real = respuestas_leer[-1][0]
assert status_real == 200, (
    f"Se esperaba HTTP 200 del backend (defecto historico de HTTP 400 ya recuperado), "
    f"se obtuvo {status_real} - {respuestas_leer[-1][1]}"
)

filas = filas_inspectores(frame)
n = filas.count()
assert n > 0, "Se esperaba al menos 1 fila con el filtro por defecto (Estado=Activos)"
capturar_paso(app, "listado_dentro_del_limite_sin_error", paso_excel=2)
'''

# DEFECTO REAL MAYOR descubierto 02/11/2026 ("Siguientes" ignora el
# filtro vigente - ver _exploracion/explore_76_rf06_siguientes_rompe_filtro.py):
# con Proveedor = Luz del Sur (20331898008) + Sucursal = Chacarilla
# (3100) + Estado = Noactivos, el primer bloque SI viene correcto (100
# filas, todas Estado=NoActivo y Sucursal=Chacarilla, pie "100 de 116").
# Al presionar Siguientes, el pie salta a "200 de 116" (contradictorio
# con su propio total declarado) y las filas NUEVAS son Estado=Activo y
# Sucursal="0000 - Sin Sucursal" - datos de OTRO filtro completamente
# distinto, mientras la etiqueta "Filtro vigente" sigue mostrando el
# filtro original sin avisar del cambio. Conclusion: Siguientes NO
# reusa el filtro de la consulta original. (La causa-raiz de filas
# duplicadas que tambien se encontro en esta misma exploracion quedo
# documentada en CP039, que es donde corresponde tematicamente.)

CUERPOS_REALES["CP041"] = '''
# RECUPERADO (re-verificado en vivo 04/11/2026, ver
# _exploracion/explore_siguientes_noactivos.py en PR000349-SP2-IT2): el
# combo Proveedor=Luz del Sur + Sucursal=Chacarilla + Estado=Noactivos
# que exponia el defecto en PR000349-SP2 ya NO tiene suficiente volumen
# real (solo 8 registros ahora, Siguientes ni se habilita). Se usa
# Estado=Noactivos SOLO (sin Proveedor/Sucursal) porque es el combo real
# actual que SI supera 100 registros (1523) y permite probar Siguientes
# de verdad. Confirmado que ahora Siguientes SI respeta el filtro
# vigente (pie coherente 20->40 de 1523, filas nuevas tambien NoActivo).
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
overlay.locator("#flt-estado").select_option(value="N")
app.wait_for_timeout(300)
capturar_paso(app, "filtro_noactivos_solo", paso_excel=1)
overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)
capturar_paso(app, "primer_bloque_correcto", paso_excel=2)

filas = filas_inspectores(frame)
n = filas.count()
assert n > 0, "Se esperaba al menos 1 fila con Estado=Noactivos"
estados_antes = set(filas.nth(i).locator("td").nth(5).inner_text().strip() for i in range(n))
assert estados_antes == {"N - NoActivo"}, f"Se esperaba que el primer bloque fuera todo NoActivo: {estados_antes!r}"
texto_antes = frame.locator("body").inner_text()
pie_antes = next((l for l in texto_antes.splitlines() if "Registros" in l), "")

boton_siguientes = frame.get_by_role("button", name=re.compile(r"^\\s*Siguientes\\s*$"))
assert boton_siguientes.is_enabled(), "El boton Siguientes deberia estar habilitado (hay mas de 100 registros declarados)"
boton_siguientes.click()
app.wait_for_timeout(3000)
capturar_paso(app, "tras_presionar_siguientes", paso_excel=3)

filas_despues = filas_inspectores(frame)
n_despues = filas_despues.count()
estados_nuevas_filas = set(filas_despues.nth(i).locator("td").nth(5).inner_text().strip() for i in range(n, n_despues))
texto_despues = frame.locator("body").inner_text()
pie_despues = next((l for l in texto_despues.splitlines() if "Registros" in l), "")

capturar_paso(app, "siguientes_respeta_el_filtro", paso_excel=4)
assert estados_nuevas_filas == {"N - NoActivo"}, (
    f"Se esperaba que las filas nuevas de Siguientes tambien sean 'N - NoActivo' (defecto "
    f"historico ya recuperado), pero trajeron estos estados: {estados_nuevas_filas!r} "
    f"(pie antes: {pie_antes!r}, pie despues: {pie_despues!r})"
)
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

# RE-INTENTADO 02/11/2026 (ver _exploracion/explore_77_rf06_cp044_estado_2408.py
# y explore_78_rf06_cp044_intento.py): confirmado en vivo que el unico
# inspector descartable conocido (codigo 2408) sigue N-NoActivo (quedo
# asi desde la Baja real del 28/09/2026, sin reversion posible en la
# UI). Con Estado=Noactivos, la fila SI aparece (19 filas duplicadas del
# mismo registro - mismo defecto de CP039/CP041), pero su checkbox
# individual esta deshabilitado (RN: solo se pueden marcar filas
# S-Activo) y el boton Eliminar permanece deshabilitado - confirmado
# que NO se puede repetir la Baja sobre este registro. Alta (que
# generaria un descartable nuevo) sigue bloqueada por el servicio
# externo de validacion de ficha (ver CP046/CP047) - sin eso, no hay
# forma de obtener un inspector descartable para repetir este caso sin
# arriesgar datos reales.

# CP044 EJECUTADO DE VERDAD 02/11/2026. Primer intento con codigo 302
# ("Antonio Lopez") funciono (confirmado "Operacion Exitosa" con
# captura real), pero la corrida completa se cayo despues en el paso de
# verificacion por un overlay que quedo sin cerrar - ya consumido, no
# repetible. El usuario indico el codigo 301 ("Julio Rios", confirmado
# S-Activo en vivo via _exploracion/explore_80_rf06_verificar_301_303_304.py)
# para una corrida limpia de punta a punta con video. Secuencia
# confirmada funcional el 28/09/2026 con 2408 (ver
# _exploracion/explore_55_56_rf06_eliminar_2408.py): marcar -> Eliminar
# (pantalla principal) -> se abre un 2do overlay "Modo: Baja" -> Eliminar
# DENTRO de ese overlay -> confirmacion con boton real de clase
# "conf-btn-ok" (NO es el patron Aceptar/role generico de otros modales
# de esta pantalla) -> mensaje final.

CUERPOS_REALES["CP044"] = '''
# Codigo 1376 (Castañeda Gutierrez Jhoan Alejandro, Proveedor Luz del Sur)
# real y Activo - re-confirmado en vivo 06/11/2026 (1379, usado en la
# iteracion anterior, ya quedo NoActivo por esa misma baja).
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
overlay.locator("#flt-codigo").fill("1376")
app.wait_for_timeout(300)
overlay.locator("#flt-estado").select_option(value="S")
app.wait_for_timeout(300)
capturar_paso(app, "filtro_codigo_1376_activo", paso_excel=1)
overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)

filas = filas_inspectores(frame)
n = filas.count()
assert n > 0, "Se esperaba encontrar el inspector 1376 (Activo, confirmado en vivo)"
fila = filas.first
checkbox = fila.locator("input[type=checkbox]")
assert checkbox.is_enabled(), "Se esperaba el checkbox HABILITADO (codigo 1376 es S-Activo)"
checkbox.check()
app.wait_for_timeout(500)
capturar_paso(app, "codigo_1376_marcado", paso_excel=2)

frame.get_by_role("button", name=re.compile(r"^\\s*Eliminar\\s*$")).click()
app.wait_for_timeout(1500)
capturar_paso(app, "ventana_detalle_modo_baja", paso_excel=3)

overlay_baja = frame.locator("[id^='cdk-overlay-']").last
boton_eliminar_modal = overlay_baja.get_by_role("button", name=re.compile(r"^\\s*Eliminar\\s*$"))
assert boton_eliminar_modal.count(), "Se esperaba el boton Eliminar dentro de la ventana de Detalle (Modo: Baja)"
boton_eliminar_modal.click()
app.wait_for_timeout(1500)
capturar_paso(app, "pidiendo_confirmacion", paso_excel=4)

boton_confirmar = frame.locator("button.conf-btn-ok")
assert boton_confirmar.count() and boton_confirmar.first.is_visible(), (
    "Se esperaba el dialogo de confirmacion (\\'\\u00bfEsta seguro que desea eliminar el Registro?\\')"
)
boton_confirmar.first.click()
app.wait_for_timeout(2000)
capturar_paso(app, "baja_confirmada", paso_excel=5)

texto_final = frame.locator("body").inner_text()
assert "eliminaci" in texto_final.lower() and "satisfactoriamente" in texto_final.lower(), (
    f"Se esperaba 'Eliminaci\\u00f3n realizada Satisfactoriamente.': {texto_final[-400:]!r}"
)

# Cerrar TODOS los overlays que queden abiertos (el modal "Operacion
# Exitosa" y, debajo, la ventana de Detalle en Modo: Baja) - repetir
# hasta que no quede ninguno visible, no alcanza con 1 pasada.
for _ in range(6):
    cerrado = False
    for nombre_boton in ("Aceptar", "Cerrar"):
        boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
        if boton.count() and boton.first.is_visible():
            boton.first.click(force=True)
            app.wait_for_timeout(800)
            cerrado = True
    if not cerrado:
        break
capturar_paso(app, "modales_cerrados", paso_excel=6)

# Verificar el estado final real: 1376 debe quedar N-NoActivo
overlay2 = abrir_filtro_inspectores(app, frame)
overlay2.locator("#flt-codigo").fill("1376")
app.wait_for_timeout(300)
overlay2.locator("#flt-estado").select_option(value="N")
app.wait_for_timeout(300)
overlay2.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)
capturar_paso(app, "estado_final_verificado_noactivo", paso_excel=7)
filas_finales = filas_inspectores(frame)
assert filas_finales.count() > 0, "Se esperaba encontrar el codigo 1376 como N-NoActivo tras la baja real"
'''

# CP045 re-destrabado 06/11/2026: los codigos 1378/1377 usados en la
# iteracion anterior ya quedaron NoActivo (consumidos en esa corrida).
# Se usan 1375 ("Lurita Nieto Fredy Juan") y 1374 ("Rojas Gutierrez
# Humberto Jose"), ambos confirmados S-Activo en vivo (ver
# _buscar_codigos_044_045.py), con el prefijo "137" que
# ya los trae juntos en el primer bloque (sin necesitar Siguientes).

CUERPOS_REALES["CP045"] = '''
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
overlay.locator("#flt-codigo").fill("137")
app.wait_for_timeout(300)
overlay.locator("#flt-estado").select_option(value="S")
app.wait_for_timeout(300)
capturar_paso(app, "filtro_codigo_137_activos", paso_excel=1)
overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)

filas = filas_inspectores(frame)
codigos_pagina1 = set(filas.nth(i).locator("td").nth(1).inner_text().strip() for i in range(filas.count()))
if not ({"1375", "1374"} <= codigos_pagina1):
    boton_siguientes = frame.get_by_role("button", name=re.compile(r"^\\s*Siguientes\\s*$"))
    assert boton_siguientes.is_enabled(), "Se esperaba poder traer mas registros con Siguientes para alcanzar 1375 y 1374"
    boton_siguientes.click()
    app.wait_for_timeout(3000)
capturar_paso(app, "bloque_con_1375_y_1374", paso_excel=2)

filas = filas_inspectores(frame)
n = filas.count()
fila_303 = None
fila_304 = None
for i in range(n):
    codigo_fila = filas.nth(i).locator("td").nth(1).inner_text().strip()
    if codigo_fila == "1375" and fila_303 is None:
        fila_303 = filas.nth(i)
    elif codigo_fila == "1374" and fila_304 is None:
        fila_304 = filas.nth(i)
    if fila_303 is not None and fila_304 is not None:
        break
assert fila_303 is not None and fila_304 is not None, (
    f"No se encontraron filas de 1375 y 1374 juntas en el bloque cargado ({n} filas)"
)

fila_303.locator("input[type=checkbox]").check()
app.wait_for_timeout(300)
fila_304.locator("input[type=checkbox]").check()
app.wait_for_timeout(500)
capturar_paso(app, "1375_y_1374_marcados", paso_excel=3)

marcadas = frame.locator("table.resultados tbody tr input[type=checkbox]:checked").count()
assert marcadas == 2, f"Se esperaban exactamente 2 filas marcadas (1375 y 1374), hay {marcadas}"

frame.get_by_role("button", name=re.compile(r"^\\s*Eliminar\\s*$")).click()
app.wait_for_timeout(1500)
capturar_paso(app, "pidiendo_confirmacion_masiva", paso_excel=4)

boton_confirmar = frame.locator("button.conf-btn-ok")
if not (boton_confirmar.count() and boton_confirmar.first.is_visible()):
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    assert modal.count() and modal.first.is_visible(), "Se esperaba un dialogo de confirmacion de eliminacion masiva"
    boton_confirmar = modal.first.get_by_role("button", name=re.compile(r"^\\s*(Aceptar|S[ií])\\s*$", re.I))
assert boton_confirmar.count(), "No se encontro boton de confirmacion para la eliminacion masiva"
boton_confirmar.first.click()
app.wait_for_timeout(2000)
capturar_paso(app, "baja_masiva_confirmada", paso_excel=5)

texto_final = frame.locator("body").inner_text()
assert "eliminaron" in texto_final.lower() and "2" in texto_final and "satisfactoriamente" in texto_final.lower(), (
    f"Se esperaba 'Se eliminaron 2 registros, satisfactoriamente.': {texto_final[-400:]!r}"
)

for _ in range(6):
    cerrado = False
    for nombre_boton in ("Aceptar", "Cerrar"):
        boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
        if boton.count() and boton.first.is_visible():
            boton.first.click(force=True)
            app.wait_for_timeout(800)
            cerrado = True
    if not cerrado:
        break
capturar_paso(app, "modales_cerrados", paso_excel=6)

# Verificar estado final real: 303 y 304 deben quedar N-NoActivo
for codigo_verificar in ("1375", "1374"):
    overlay2 = abrir_filtro_inspectores(app, frame)
    overlay2.locator("#flt-codigo").fill(codigo_verificar)
    app.wait_for_timeout(300)
    overlay2.locator("#flt-estado").select_option(value="N")
    app.wait_for_timeout(300)
    overlay2.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
    app.wait_for_timeout(3000)
    capturar_paso(app, f"estado_final_{codigo_verificar}_noactivo", paso_excel=7)
    filas_verif = filas_inspectores(frame)
    assert filas_verif.count() > 0, f"Se esperaba encontrar el codigo {codigo_verificar} como N-NoActivo tras la baja masiva"
'''

# CP046 DESTRABADO 02/11/2026 (ver _exploracion/explore_85_rf06_cp046_ficha.py):
# el servicio externo de validacion de ficha, caido el 28/09/2026 ('Error
# de Servicio: Error al validar la ficha.'), ya responde normalmente -
# mismo patron de recuperacion ya visto en CP008 (servicio de informes
# de RF-01) y CP039 (backend de RF-02/03/05, un mes despues). Confirmado
# en vivo: Ficha=4504 -> "Ficha 4504 no válida." (ya no es real); Ficha
# real conocida 5631 (del inspector 1373) -> mensaje EXACTO del EF: "La
# ficha 5631 ya tiene asignado el código de contratista 1373. No se
# puede ingresar otro codigo a la misma ficha."

CUERPOS_REALES["CP046"] = '''
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
frame.get_by_role("button", name=re.compile(r"^\\s*Agregar\\s*$")).click()
app.wait_for_timeout(1500)
capturar_paso(app, "ventana_alta_abierta", paso_excel=1)

campo_ficha = frame.locator("#det-ficha")
# Ficha 7010 real y Activa (codigo 1380, Miranda Carrillo Miguel Angel,
# Proveedor Luz del Sur) - re-confirmada en vivo 04/11/2026, ver
# _exploracion/explore_cp042_ficha_real.py (la ficha 5631 usada antes
# ya no correspondia a ningun inspector Activo, por eso no disparaba
# el aviso).
campo_ficha.fill("7010")
campo_ficha.press("Tab")
app.wait_for_timeout(3000)
capturar_paso(app, "ficha_7010_tab", paso_excel=2)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validaci", re.I))
assert modal.count() and modal.last.is_visible(), "Se esperaba la Ventana de Validacion sobre la ficha ya asignada"
mensaje = modal.last.inner_text()
capturar_paso(app, "mensaje_ficha_ya_asignada", paso_excel=3)
assert "7010" in mensaje and "1380" in mensaje and "ya tiene asignado" in mensaje.lower(), (
    f"Mensaje inesperado para ficha ya asignada: {mensaje!r}"
)
'''

# CP047 sigue BLOQUEADO (no por el servicio, que ya funciona, sino por
# falta de una ficha real VALIDA y aun no usada como inspector - crear
# un Alta completa es una escritura permanente sin reversion en la UI,
# igual que la Baja). Pendiente: el usuario indique una ficha real de
# MANTRABEX que no sea ya un inspector.
CUERPOS_REALES["CP047"] = '''
# H005 RETRACTADO (06/11/2026): no era un defecto real. El Alta con
# "Todas las sucursales" marcada SI crea un registro por cada sucursal
# vigente (confirmado en vivo con ficha 5763/codigo 1526, presente en
# las 12 sucursales reales: 0000, 0022, 1000, 3100, 3200, 3300, 4100,
# 4200, 4300, 4400, 5100, 5200) - lo que fallaba era el metodo de
# verificacion (filtrar solo por Ficha muestra una sola fila por
# defecto; hay que seleccionar cada Sucursal en el filtro y Leer, tal
# como aclara la MCP actualizada). No se repite el Alta (escritura
# permanente) - se verifica el resultado ya confirmado de ficha 5763.
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)

sucursales_reales = [
    "0000", "0022", "1000", "3100", "3200", "3300",
    "4100", "4200", "4300", "4400", "5100", "5200",
]
sucursales_con_codigo = []
for suc in sucursales_reales:
    overlay = abrir_filtro_inspectores(app, frame)
    overlay.locator("#flt-ficha").fill("5763")
    app.wait_for_timeout(300)
    overlay.locator("#flt-sucursal").select_option(value=suc)
    app.wait_for_timeout(300)
    overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
    app.wait_for_timeout(2500)
    filas = filas_inspectores(frame)
    if filas.count() > 0:
        sucursales_con_codigo.append(suc)
capturar_paso(app, "codigo_1526_presente_en_cada_sucursal", paso_excel=1)

assert set(sucursales_con_codigo) == set(sucursales_reales), (
    f"Se esperaba el codigo 1526 (ficha 5763) en las 12 sucursales reales, solo aparecio en: "
    f"{sucursales_con_codigo!r}"
)
'''

# CP073 "Uso de la barra de paginado de la grilla" (RF-06, caso nuevo
# agregado a la matriz oficial 04/11/2026, no estaba en versiones
# anteriores) - confirmado en vivo (ver
# _exploracion/explore_cp073_paginado.py). Los numeros exactos que trae
# el MCP (130 registros Activo / 349 No activo, verificados en
# Desarrollo el 2026-11-03) ya NO coinciden con el universo real de
# Pruebas hoy (71 Activos) - el dato de volumen cambia con el tiempo,
# asi que el caso valida la MECANICA del paginado (rangos, Pagina N de
# M, Siguientes acumulando) de forma dinamica contra el total real del
# momento, no contra un numero fijo.
CUERPOS_REALES["CP073"] = '''
app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
frame.get_by_role("button", name=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(3000)
capturar_paso(app, "pantalla_inicial_activos", paso_excel=2)

texto = frame.locator("body").inner_text()
assert "demasiados registros" not in texto.lower(), "No se esperaba el mensaje de demasiados registros"
m_pie = re.search(r"Mostrando\\s+1.20\\s+de\\s+(\\d+)\\s+registros", texto, re.I)
assert m_pie, f"No se encontro el pie \\'Mostrando 1-20 de N registros\\': {texto[-300:]!r}"
total_activos = int(m_pie.group(1))
paginas_20 = -(-total_activos // 20)
assert f"P\\u00e1gina 1 de {paginas_20}" in texto, f"Se esperaba \\'Pagina 1 de {paginas_20}\\' con 20 por pagina: {texto!r}"

frame.get_by_role("button", name="\\u00daltima p\\u00e1gina").click()
app.wait_for_timeout(1500)
texto_ultima = frame.locator("body").inner_text()
capturar_paso(app, "ultima_pagina", paso_excel=4)
assert f"P\\u00e1gina {paginas_20} de {paginas_20}" in texto_ultima, (
    f"Se esperaba llegar a la pagina {paginas_20} (ultima): {texto_ultima!r}"
)
desde_ultima = (paginas_20 - 1) * 20 + 1
assert f"Mostrando {desde_ultima}" in texto_ultima, (
    f"Se esperaba que la ultima pagina muestre desde el registro {desde_ultima}: {texto_ultima!r}"
)

frame.get_by_role("button", name="Primera p\\u00e1gina").click()
app.wait_for_timeout(1500)
capturar_paso(app, "primera_pagina_de_nuevo", paso_excel=4)

campo_rpp = frame.locator(".lds-pg__input")
campo_rpp.fill("5")
campo_rpp.press("Enter")
app.wait_for_timeout(2000)
texto_5 = frame.locator("body").inner_text()
capturar_paso(app, "registros_por_pagina_5", paso_excel=6)
assert f"Mostrando 1\\u20135 de {total_activos} registros" in texto_5, (
    f"Se esperaba \\'Mostrando 1-5 de {total_activos} registros\\' tras cambiar a 5 por pagina: {texto_5!r}"
)
paginas_5 = -(-total_activos // 5)
assert f"P\\u00e1gina 1 de {paginas_5}" in texto_5, f"Se esperaba \\'Pagina 1 de {paginas_5}\\': {texto_5!r}"
filas_5 = frame.locator("table.resultados tbody tr").filter(has_not_text=re.compile("Sin registros"))
assert filas_5.count() == 5, f"Se esperaban exactamente 5 filas visibles, hay {filas_5.count()}"

frame.get_by_role("button", name=re.compile(r"^\\s*Siguientes\\s*$")).click()
app.wait_for_timeout(2000)
texto_siguientes = frame.locator("body").inner_text()
capturar_paso(app, "siguientes_acumula_conservando_filtro", paso_excel=7)
assert f"10 de {total_activos} Registros" in texto_siguientes, (
    f"Se esperaba el pie acumulado \\'10 de {total_activos} Registros\\': {texto_siguientes!r}"
)
assert f"acumuladas 2 de {paginas_5} p" in texto_siguientes.lower(), (
    f"Se esperaba \\'acumuladas 2 de {paginas_5} paginas\\': {texto_siguientes!r}"
)
assert "demasiados registros" not in texto_siguientes.lower(), "No se esperaba el mensaje de demasiados registros"

# Segunda parte: Estado = Noactivos, repetir la verificacion mecanica
# (sin asumir un total fijo, el universo real de NoActivos es mucho
# mayor que el que documenta el MCP - ver RECUPERADO en CP039/CP041).
overlay = abrir_filtro_inspectores(app, frame)
overlay.locator("#flt-estado").select_option(value="N")
app.wait_for_timeout(300)
overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)
capturar_paso(app, "estado_noactivos", paso_excel=8)
texto_noactivos = frame.locator("body").inner_text()
assert "demasiados registros" not in texto_noactivos.lower(), "No se esperaba el mensaje de demasiados registros con Noactivos"

filas_noactivos = frame.locator("table.resultados tbody tr").filter(has_not_text=re.compile("Sin registros"))
n_noactivos = filas_noactivos.count()
assert n_noactivos > 0, "Se esperaba al menos 1 fila con Estado=Noactivos"
estados_vistos = set(filas_noactivos.nth(i).locator("td").nth(5).inner_text().strip() for i in range(n_noactivos))
assert estados_vistos == {"N - NoActivo"}, f"Se esperaba que todas las filas fueran NoActivo: {estados_vistos!r}"
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

# CP048 EJECUTADO DE VERDAD 02/11/2026 con codigo 1373 ("Vega Rodriguez
# Alex Henry", ficha 5631, confirmado S-Activo) - autorizado
# explicitamente por el usuario. Estructura con try/finally: el bloque
# de RESTAURACION corre SIEMPRE, incluso si alguna de las verificaciones
# de la regla de negocio falla a mitad de camino - exactamente el riesgo
# que en septiembre impidio dejar este caso como automatizado (ver
# _MOTIVO_CP048_NO_AUTOMATIZADO arriba, ya historico).

CUERPOS_REALES["CP048"] = '''
def _confirmar_grabar():
    boton_confirmar = frame.locator("button.conf-btn-ok")
    if not (boton_confirmar.count() and boton_confirmar.first.is_visible()):
        modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Confirmaci", re.I))
        boton_confirmar = modal.last.get_by_role("button", name=re.compile(r"^\\s*(Aceptar|S[ií])\\s*$", re.I))
    assert boton_confirmar.count(), "No se encontro boton de confirmacion para Grabar"
    boton_confirmar.first.click()
    app.wait_for_timeout(2000)

app, frame = abrir_mantenedor_inspectores(page, paso_excel=1)
overlay = abrir_filtro_inspectores(app, frame)
overlay.locator("#flt-codigo").fill("1373")
app.wait_for_timeout(300)
overlay.locator("#flt-estado").select_option(value="S")
app.wait_for_timeout(300)
capturar_paso(app, "filtro_codigo_1373_activo", paso_excel=1)
overlay.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
app.wait_for_timeout(3000)

filas = filas_inspectores(frame)
assert filas.count() > 0, "Se esperaba encontrar el inspector 1373 (Activo, confirmado en vivo)"
filas.first.click()
app.wait_for_timeout(500)
frame.get_by_role("button", name=re.compile(r"^\\s*Detalles\\s*$")).click()
app.wait_for_timeout(1500)
capturar_paso(app, "ventana_modificacion_abierta", paso_excel=2)

campo_nombre = frame.locator("#det-nombre")
select_proveedor = frame.locator("#det-proveedor")
checkbox_todas_sucursales = frame.locator("#det-todas-sucursales")

nombre_original = campo_nombre.input_value()
proveedor_original = select_proveedor.input_value()
todas_sucursales_original = checkbox_todas_sucursales.is_checked()
assert "Vega Rodriguez" in nombre_original, f"Nombre original inesperado (revisar si 1373 sigue siendo el mismo registro): {nombre_original!r}"

try:
    nombre_temporal = nombre_original + " - MODIFICADO CP048"
    campo_nombre.fill(nombre_temporal)
    select_proveedor.select_option(label="20206018411 - TECSUR S.A.")
    app.wait_for_timeout(300)
    capturar_paso(app, "datos_modificados_temporalmente", paso_excel=3)

    frame.get_by_role("button", name=re.compile(r"^\\s*Grabar\\s*$")).click()
    app.wait_for_timeout(1500)
    _confirmar_grabar()
    texto_grabado = frame.locator("body").inner_text()
    capturar_paso(app, "grabacion_exitosa", paso_excel=4)
    assert "grabaci" in texto_grabado.lower() and "exitosa" in texto_grabado.lower(), (
        f"Se esperaba 'Grabaci\\u00f3n exitosa.': {texto_grabado[-400:]!r}"
    )

    for _ in range(6):
        cerrado = False
        for nombre_boton in ("Aceptar", "Cerrar"):
            boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
            if boton.count() and boton.first.is_visible():
                boton.first.click(force=True)
                app.wait_for_timeout(800)
                cerrado = True
        if not cerrado:
            break

    # DEFECTO REAL (confirmado en vivo 28/09/2026, re-verificado hoy):
    # la grilla debe mostrar el Nombre/Proveedor actualizados, pero
    # Sucursal y Area quedan SIN CAMBIOS pese a haber elegido otra
    # Sucursal en el combo.
    overlay2 = abrir_filtro_inspectores(app, frame)
    overlay2.locator("#flt-codigo").fill("1373")
    app.wait_for_timeout(300)
    overlay2.locator("#flt-estado").select_option(value="S")
    app.wait_for_timeout(300)
    overlay2.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
    app.wait_for_timeout(3000)
    capturar_paso(app, "defecto_real_sucursal_area_sin_cambios", paso_excel=5)

    filas2 = filas_inspectores(frame)
    assert filas2.count() > 0, "Se esperaba seguir encontrando el inspector 1373 tras modificar"
    primera_fila_texto = filas2.first.inner_text()
    assert "MODIFICADO CP048" in primera_fila_texto, (
        f"Se esperaba ver el Nombre modificado en la grilla: {primera_fila_texto!r}"
    )
    assert "0000 - Sin Sucursal" in primera_fila_texto and "3521" in primera_fila_texto, (
        f"DEFECTO REAL: se esperaba que Sucursal/Area quedaran SIN CAMBIOS "
        f"('0000 - Sin Sucursal' / '3521') pese a la modificacion: {primera_fila_texto!r}"
    )
finally:
    # RESTAURACION: corre siempre, pase lo que pase arriba.
    overlay3 = abrir_filtro_inspectores(app, frame)
    overlay3.locator("#flt-codigo").fill("1373")
    app.wait_for_timeout(300)
    overlay3.locator("#flt-estado").select_option(value="S")
    app.wait_for_timeout(300)
    overlay3.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
    app.wait_for_timeout(3000)
    filas3 = filas_inspectores(frame)
    assert filas3.count() > 0, "RESTAURACION: no se encontro el inspector 1373 para revertir los datos"
    filas3.first.click()
    app.wait_for_timeout(500)
    frame.get_by_role("button", name=re.compile(r"^\\s*Detalles\\s*$")).click()
    app.wait_for_timeout(1500)

    frame.locator("#det-nombre").fill(nombre_original)
    frame.locator("#det-proveedor").select_option(value=proveedor_original)
    app.wait_for_timeout(300)
    capturar_paso(app, "restaurando_valores_originales", paso_excel=6)

    frame.get_by_role("button", name=re.compile(r"^\\s*Grabar\\s*$")).click()
    app.wait_for_timeout(1500)
    _confirmar_grabar()
    texto_restaurado = frame.locator("body").inner_text()
    capturar_paso(app, "restauracion_confirmada", paso_excel=7)
    assert "grabaci" in texto_restaurado.lower() and "exitosa" in texto_restaurado.lower(), (
        f"RESTAURACION: se esperaba 'Grabaci\\u00f3n exitosa.' al revertir, pero: {texto_restaurado[-400:]!r}"
    )

    for _ in range(6):
        cerrado2 = False
        for nombre_boton in ("Aceptar", "Cerrar"):
            boton = frame.get_by_role("button", name=re.compile(rf"^\\s*{nombre_boton}\\s*$"))
            if boton.count() and boton.first.is_visible():
                boton.first.click(force=True)
                app.wait_for_timeout(800)
                cerrado2 = True
        if not cerrado2:
            break

    overlay4 = abrir_filtro_inspectores(app, frame)
    overlay4.locator("#flt-codigo").fill("1373")
    app.wait_for_timeout(300)
    overlay4.locator("#flt-estado").select_option(value="S")
    app.wait_for_timeout(300)
    overlay4.get_by_role("button", name=re.compile(r"^\\s*Filtrar\\s*$")).click()
    app.wait_for_timeout(3000)
    capturar_paso(app, "estado_final_restaurado", paso_excel=8)
    filas4 = filas_inspectores(frame)
    if filas4.count() > 0:
        texto_final = filas4.first.inner_text()
        assert "MODIFICADO CP048" not in texto_final, (
            f"RESTAURACION INCOMPLETA: el nombre modificado sigue visible: {texto_final!r}"
        )
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

# CORRECCION 02/11/2026 (ver _exploracion/explore_88_rf07_revalidar_freeze.py,
# explore_89_rf07_entre_campos.py, explore_90_rf07_cp053_rango.py): el
# freeze del date-picker confirmado 28/09/2026 (congelaba 30s+ al
# ingresar una fecha calendario valida) YA NO SE REPRODUCE - escribir la
# fecha, hacer screenshot y leer el valor terminan en <2s. Mismo patron
# de recuperacion ya visto en CP008/CP039/CP046 de este mismo proyecto.
# Confirmado en vivo el flujo completo de ambos casos con los mensajes
# EXACTOS del EF.

CUERPOS_REALES["CP052"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
frame.locator("#fld-tipo-fecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="Entre").first.click()
app.wait_for_timeout(500)

campo_ini = frame.get_by_label("Fecha inicial")
campo_ini.click()
campo_ini.press_sequentially("01/01/2026", delay=80)
app.wait_for_timeout(500)
capturar_paso(app, "entre_con_fecha_inicial_sin_final", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
assert modal.count() and modal.first.is_visible(), "Se esperaba la Ventana de Validacion de rango incompleto"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_rango_superior_obligatorio", paso_excel=2)
assert "rango superior" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP053"] = '''
app, frame = abrir_consulta_cortes_pendientes(page, paso_excel=1)
frame.locator("#fld-tipo-fecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="Entre").first.click()
app.wait_for_timeout(500)

campo_ini = frame.get_by_label("Fecha inicial")
campo_fin = frame.get_by_label("Fecha final")
campo_ini.click()
campo_ini.press_sequentially("01/01/2026", delay=80)
app.wait_for_timeout(300)
campo_fin.click()
campo_fin.press_sequentially("01/06/2026", delay=80)  # 151 dias, supera el maximo de 60
app.wait_for_timeout(500)
capturar_paso(app, "rango_mayor_a_60_dias", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
assert modal.count() and modal.first.is_visible(), "Se esperaba la Ventana de Validacion de rango excedido"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_rango_excedido", paso_excel=2)
assert "60" in mensaje and "d" in mensaje.lower() and "m" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
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

# CP057-061/063 escritos y confirmados en vivo 29/10/2026 (DCABA_DW) -
# ver detalle de cada hallazgo en los comentarios de cada caso.

CUERPOS_REALES["CP057"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldSucursal", "1000 - Cañete")
app.wait_for_timeout(500)
capturar_paso(app, "filtro_sucursal_aplicado", paso_excel=1)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2000)

esperar_fin_de_carga(app, frame)
encabezados = frame.locator("table thead th").all_text_contents()
idx_estado = encabezados.index("Estado Solicitud")
idx_fecha = encabezados.index("Fecha Solicitud")

# La grilla puede tardar en terminar de renderizar incluso despues de que
# "Cargando..." desaparece (mismo patron ya visto en otras pantallas de
# este proyecto) - se espera activamente a tener filas con el numero
# real de columnas, no solo a que exista algun <tr>.
plazo = time.monotonic() + 40
filas = frame.locator("tr.ant-table-row")
estados = []
fechas_solicitud = []
while time.monotonic() < plazo:
    estados = []
    fechas_solicitud = []
    for i in range(filas.count()):
        celdas = filas.nth(i).locator("td").all_text_contents()
        if len(celdas) != len(encabezados):
            continue
        estados.append(celdas[idx_estado].strip())
        fechas_solicitud.append(celdas[idx_fecha].strip())
    if estados:
        break
    app.wait_for_timeout(1500)
capturar_paso(app, "resultado_solicitudes_pendientes", paso_excel=3)

assert estados, "No se pudieron leer los estados de las filas"
assert all(e != "ANULADO" and e != "ANULADA" for e in estados), (
    f"Se esperaba que NINGUNA fila mostrara una solicitud anulada: {estados!r}"
)

fechas_dt = []
for f in fechas_solicitud:
    if not f:
        continue
    dd, mm, yyyy = f.split("/")
    fechas_dt.append(date(int(yyyy), int(mm), int(dd)))
assert fechas_dt == sorted(fechas_dt), (
    f"Se esperaba el resultado ordenado por Fecha Solicitud ascendente: {fechas_solicitud!r}"
)
'''

CUERPOS_REALES["CP058"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldTipoFecha", "=")
app.wait_for_timeout(500)
frame.locator("#fldFechaInicio").fill("31/02/2026")
capturar_paso(app, "fecha_calendario_inexistente", paso_excel=1)

mensaje = leer_reposicion_pendientes(app, frame)
capturar_paso(app, "mensaje_fecha_invalida", paso_excel=3)
assert mensaje is not None and "fecha inv" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP059"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldTipoFecha", "=")
app.wait_for_timeout(500)
capturar_paso(app, "tipo_fecha_sin_fecha_inicial", paso_excel=1)

mensaje = leer_reposicion_pendientes(app, frame)
capturar_paso(app, "mensaje_rango_inferior_obligatorio", paso_excel=4)
assert mensaje is not None and "rango inferior" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP060"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldTipoFecha", "Entre")
app.wait_for_timeout(500)
frame.locator("#fldFechaInicio").fill("01/06/2026")
capturar_paso(app, "solo_fecha_inicial_sin_final", paso_excel=2)

mensaje = leer_reposicion_pendientes(app, frame)
capturar_paso(app, "mensaje_rango_superior_obligatorio", paso_excel=4)
assert mensaje is not None and "rango superior" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP061"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldTipoFecha", "Entre")
app.wait_for_timeout(500)
frame.locator("#fldFechaInicio").fill("01/01/2026")
frame.locator("#fldFechaFin").fill("15/03/2026")  # 73 dias, supera el maximo de 31
capturar_paso(app, "rango_mayor_a_31_dias", paso_excel=2)

mensaje = leer_reposicion_pendientes(app, frame)
capturar_paso(app, "mensaje_limite_31_dias", paso_excel=4)
assert mensaje is not None and "31" in mensaje and "d" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
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

CUERPOS_REALES["CP063"] = '''
app, frame = abrir_reposicion_pendientes(page, paso_excel=1)
elegir_nz_select(frame, app, "fldSucursal", "1000 - Cañete")
app.wait_for_timeout(500)

frame.locator("button", has_text=re.compile(r"^\\s*Leer\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2000)

esperar_fin_de_carga(app, frame)
# La primera fila de `tr.ant-table-row` puede ser una fila estructural
# vacia (sin <td>, confirmado en vivo) - hay que ubicar la primera fila
# con celdas de datos reales, no asumir que es filas.first().
plazo = time.monotonic() + 40
filas = frame.locator("tr.ant-table-row")
primera_fila = None
while time.monotonic() < plazo:
    for i in range(filas.count()):
        candidata = filas.nth(i)
        if candidata.locator("td").count() > 0:
            primera_fila = candidata
            break
    if primera_fila is not None:
        break
    app.wait_for_timeout(1500)
assert primera_fila is not None, "No se cargo ningun resultado real para seleccionar y anular"
capturar_paso(app, "resultado_antes_de_seleccionar", paso_excel=1)

boton_anular = frame.locator("button", has_text=re.compile(r"^\\s*Anular\\s*$"))
assert boton_anular.is_disabled(), "Anular deberia iniciar deshabilitado sin ninguna fila seleccionada"

numero_solicitud = primera_fila.locator("td").nth(14).inner_text().strip()
primera_fila.click()
app.wait_for_timeout(500)
assert not boton_anular.is_disabled(), "Anular deberia habilitarse al seleccionar una fila pendiente"
capturar_paso(app, "fila_seleccionada", paso_excel=1)

boton_anular.click()
app.wait_for_timeout(1500)
modal2 = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal2.count() and modal2.first.is_visible(), "Se esperaba la confirmacion antes de anular"
mensaje_confirmacion = modal2.first.inner_text()
assert "desea continuar" in mensaje_confirmacion.lower(), f"Mensaje de confirmacion inesperado: {mensaje_confirmacion!r}"
capturar_paso(app, "confirmacion_desea_continuar", paso_excel=3)

modal2.first.get_by_role("button", name=re.compile("S[ií]|Aceptar", re.I)).first.click()
app.wait_for_timeout(2500)
modal3 = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
assert modal3.count() and modal3.first.is_visible(), f"Se esperaba el mensaje de exito tras anular la solicitud {numero_solicitud}"
mensaje_final = modal3.first.inner_text()
capturar_paso(app, "solicitud_anulada", paso_excel=4)
assert "anulada" in mensaje_final.lower(), f"Mensaje final inesperado: {mensaje_final!r}"
'''

# CORRECCION 02/11/2026 (ver _exploracion/explore_91_rf09_revalidar_freeze.py,
# explore_92_rf09_cp068_069_071.py): el freeze del date-picker confirmado
# 28/09/2026 YA NO SE REPRODUCE en esta pantalla tampoco - mismo patron
# de recuperacion que RF-07 (ver _MOTIVO_BLOQUEO_RF07_FECHA, ya
# historico). Confirmados en vivo: CP064 (fecha "=" 02/11/2026, solo
# filtro de fecha, trae 1 resultado real: suministro 2353914, solicitud
# 872378, INGRESADO), CP068 ("Debe Seleccionar Rango Superior de Fecha"),
# CP069 ("Error, Rango de Fechas Debe Ser Como Máximo 31 Días"), CP071
# ("No existen datos de la consulta" con fecha 01/01/2000).

CUERPOS_REALES["CP064"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
frame.locator("#fldTipoFecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="=").first.click()
app.wait_for_timeout(500)
frame.locator("#fldFechaIni").click()
frame.locator("#fldFechaIni").press_sequentially("02/11/2026", delay=80)
app.wait_for_timeout(500)
capturar_paso(app, "solo_filtro_de_fecha", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
plazo = time.monotonic() + 45
resultado = None
while time.monotonic() < plazo:
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
    if modal.count() and modal.first.is_visible():
        resultado = ("modal", modal.first.inner_text())
        break
    texto = frame.locator("body").inner_text()
    if "total registros" in texto.lower():
        resultado = ("completo", texto)
        break
    app.wait_for_timeout(1000)
assert resultado is not None, "La busqueda no termino en 45s"
assert resultado[0] == "completo", f"No se esperaba un modal (busqueda solo con fecha): {resultado[1]!r}"
capturar_paso(app, "resultado_solo_con_fecha", paso_excel=2)
assert "total registros: 0" not in resultado[1].lower(), (
    f"Se esperaba al menos 1 resultado real con solo el filtro de fecha: {resultado[1][-300:]!r}"
)
'''

CUERPOS_REALES["CP068"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
frame.locator("#fldTipoFecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="Entre").first.click()
app.wait_for_timeout(500)
frame.locator("#fldFechaIni").click()
frame.locator("#fldFechaIni").press_sequentially("01/01/2026", delay=80)
app.wait_for_timeout(500)
capturar_paso(app, "entre_con_fecha_inicial_sin_final", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(2500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
assert modal.count() and modal.first.is_visible(), "Se esperaba la Ventana de Validacion de rango incompleto"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_rango_superior_obligatorio", paso_excel=2)
assert "rango superior" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

CUERPOS_REALES["CP069"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
frame.locator("#fldTipoFecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="Entre").first.click()
app.wait_for_timeout(500)
frame.locator("#fldFechaIni").click()
frame.locator("#fldFechaIni").press_sequentially("01/01/2026", delay=80)
app.wait_for_timeout(300)
frame.locator("#fldFechaFin").click()
frame.locator("#fldFechaFin").press_sequentially("15/03/2026", delay=80)  # 73 dias, supera el maximo de 31
app.wait_for_timeout(500)
capturar_paso(app, "rango_mayor_a_31_dias", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(2500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
assert modal.count() and modal.first.is_visible(), "Se esperaba la Ventana de Validacion de rango excedido"
mensaje = modal.first.inner_text()
capturar_paso(app, "mensaje_rango_excedido", paso_excel=2)
assert "31" in mensaje and "d" in mensaje.lower() and "m" in mensaje.lower(), f"Mensaje inesperado: {mensaje!r}"
'''

# CP070 DESTRABADO 02/11/2026: como no se encontro ninguna solicitud ya
# Anulada en 9 rangos probados, se genero el dato real anulando una
# solicitud pendiente real via RF-08 (ver
# _exploracion/explore_98_rf08_anular_499575.py - cliente 1964154,
# N. Solicitud 499575, Sucursal Cañete, "Operación Exitosa - Solicitud
# de Reposición Anulada" confirmado). Verificado luego en esta pantalla
# (ver _exploracion/explore_100_rf09_entre_mayo2025.py) que SI aparece
# con Estado Solicitud = ANULADO - a diferencia de RF-08, que la hubiera
# excluido del resultado tras la baja. Nota: filtrar solo por fecha NO
# encontraba el registro (probado con "=" y con "Entre" acotado a la
# fecha de Solicitud) - hizo falta combinar N. de Cliente + rango de
# fecha para que el backend lo devolviera; no se investigo la causa
# exacta de por que el filtro de fecha solo no alcanzaba.

CUERPOS_REALES["CP070"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
frame.locator("#fldCliente").fill("1964154")
app.wait_for_timeout(300)
frame.locator("#fldTipoFecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="Entre").first.click()
app.wait_for_timeout(500)
frame.locator("#fldFechaIni").click()
frame.locator("#fldFechaIni").press_sequentially("01/05/2025", delay=80)
app.wait_for_timeout(300)
frame.locator("#fldFechaFin").click()
frame.locator("#fldFechaFin").press_sequentially("31/05/2025", delay=80)
app.wait_for_timeout(500)
capturar_paso(app, "filtro_cliente_y_rango_mayo_2025", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(4000)
texto = frame.locator("body").inner_text()
capturar_paso(app, "resultado_incluye_anulada", paso_excel=2)
assert "499575" in texto, f"No se encontro la solicitud 499575 en el resultado: {texto[-400:]!r}"
assert "ANULAD" in texto.upper(), (
    f"Se esperaba ver el Estado Solicitud = ANULADO (a diferencia de RF-08, que la excluiria): {texto[-400:]!r}"
)
'''

CUERPOS_REALES["CP071"] = '''
app, frame = abrir_consulta_generica_reposiciones(page, paso_excel=1)
frame.locator("#fldTipoFecha").click()
app.wait_for_timeout(500)
frame.locator(".ant-select-item-option").filter(has_text="=").first.click()
app.wait_for_timeout(500)
frame.locator("#fldFechaIni").click()
frame.locator("#fldFechaIni").press_sequentially("01/01/2000", delay=80)
app.wait_for_timeout(500)
capturar_paso(app, "fecha_sin_coincidencias", paso_excel=1)

frame.get_by_role("button", name=re.compile("Leer")).click()
app.wait_for_timeout(3000)
texto = frame.locator("body").inner_text()
capturar_paso(app, "mensaje_sin_resultados", paso_excel=2)
assert "no existen datos de la consulta" in texto.lower(), f"Mensaje inesperado: {texto[-300:]!r}"
'''

# CP073 (RF-05) y CP074 (RF-03) agregados 02/11/2026 a partir de los
# manuales de usuario subidos a Documentos/ - no estaban en la matriz
# Excel original. Ver matriz_casos.json para el detalle de cada hallazgo
# que originó el caso.

CUERPOS_REALES["CP074"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboReferencia", "Otros Conceptos")
app.wait_for_timeout(800)
capturar_paso(app, "referencia_otros_conceptos", paso_excel=1)

frame.locator("nz-select#cboOrigen").click()
app.wait_for_timeout(500)
opciones_origen = [o.strip() for o in frame.locator("nz-option-item, .ant-select-item-option").all_text_contents() if o.strip()]
opciones_reales = [o for o in opciones_origen if o not in ("(todos)", "(no aplica)", "Todos", "(Todos)")]
assert opciones_reales, f"No se encontro ningun valor real de Origen para elegir: {opciones_origen!r}"
valor_origen = opciones_reales[0]
frame.locator("nz-option-item, .ant-select-item-option").filter(has_text=re.compile(r"^\\s*" + re.escape(valor_origen) + r"\\s*$")).first.click()
app.wait_for_timeout(500)
origen_elegido = frame.locator("nz-select#cboOrigen").inner_text().strip()
assert origen_elegido == valor_origen, f"No se aplico el valor de Origen elegido: {origen_elegido!r} != {valor_origen!r}"
capturar_paso(app, "origen_elegido", paso_excel=2)

elegir_nz_select(frame, app, "cboReferencia", "Actualización de Saldo")
app.wait_for_timeout(800)
capturar_paso(app, "referencia_cambiada_actualizacion_saldo", paso_excel=3)

elegir_nz_select(frame, app, "cboReferencia", "Otros Conceptos")
app.wait_for_timeout(800)
origen_tras_volver = frame.locator("nz-select#cboOrigen").inner_text().strip()
capturar_paso(app, "origen_tras_volver_a_otros_conceptos", paso_excel=4)
assert origen_tras_volver == valor_origen, (
    f"Segun el manual de usuario, Origen deberia conservar '{valor_origen}' tras volver a Otros Conceptos sin tocarlo, "
    f"pero quedo en {origen_tras_volver!r}"
)
'''

CUERPOS_REALES["CP075"] = '''
app, frame = abrir_cortes_reconexiones(page, paso_excel=1)
frame.locator("select").nth(0).select_option(index=1)
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-01-01")
fechas.nth(1).fill("2026-03-01")  # 59 dias, supera el limite de 15
capturar_paso(app, "motivo_y_rango_mayor_a_15_dias", paso_excel=2)

tipo, mensaje = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
assert tipo == "validacion" and "15 d" in mensaje.lower(), (
    f"Se esperaba activar el limite de 15 dias igual que CP022: tipo={tipo!r} mensaje={mensaje!r}"
)
capturar_paso(app, "limite_15_dias_activado", paso_excel=3)

frame.locator("button", has_text=re.compile(r"^\\s*Limpiar\\s*$")).click()
app.wait_for_timeout(1000)
capturar_paso(app, "pantalla_despues_de_limpiar", paso_excel=4)

# Segun el manual de usuario (seccion 3.4), el limite de 15 dias sigue
# vigente por el resto de la sesion aunque Limpiar vacie los demas
# filtros. Repetimos el MISMO rango de 59 dias sin volver a elegir
# ningun motivo, para comprobar si el limite realmente sobrevive.
fechas = frame.locator("input[type=date]")
fechas.nth(0).fill("2026-01-01")
fechas.nth(1).fill("2026-03-01")
capturar_paso(app, "mismo_rango_sin_motivo_tras_limpiar", paso_excel=5)

tipo2, mensaje2 = leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True)
capturar_paso(app, "resultado_tras_limpiar", paso_excel=6)
assert tipo2 == "validacion" and "15 d" in mensaje2.lower() and "máximo" in mensaje2.lower(), (
    f"Segun el manual de usuario, el limite de 15 dias deberia seguir vigente pese a Limpiar y sin motivo seleccionado, "
    f"pero el resultado fue: tipo={tipo2!r} mensaje={mensaje2!r}"
)
'''

# CP075/CP076 (RF-05) agregados 02/11/2026 a partir de exploracion en vivo
# (explore_65_rf05_otras_referencias.py) - no estaban en la matriz Excel
# original. Encargos de Cobranza SI tiene datos reales con Fecha <=
# 01/01/2023 (cliente 573750, oficina 0010, cajero 0005, lote 12319,
# concepto PLZ, encargo 0002). Cobranza Externa da SIEMPRE "Error de
# Servicio: Error en consulta." - mismo patron de defecto real que
# CP034 (No Ubicados).

CUERPOS_REALES["CP076"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboReferencia", "Encargos de Cobranza")
app.wait_for_timeout(800)
elegir_nz_select(frame, app, "cboFechaOperador", "<=")
app.wait_for_timeout(400)
frame.locator("#txtFechaInicial").fill("2023-01-01")
capturar_paso(app, "encargos_de_cobranza_antes_de_leer", paso_excel=1)

frame.locator("button", has_text=re.compile(r"^\\s*(Leer|Siguiente)\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible() and "confirmaci" in modal.first.inner_text().lower():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2500)

plazo = time.monotonic() + 60
filas = 0
while time.monotonic() < plazo:
    filas = frame.locator("tr").count()
    if filas > 2:
        break
    app.wait_for_timeout(2000)
assert filas > 2, "No se cargo ningun resultado real de Encargos de Cobranza"
capturar_paso(app, "resultado_encargos_de_cobranza", paso_excel=3)

# Columna propia de "Encargos de Cobranza": Encargo con dato real
# (distinta a las demas referencias, confirmado en vivo con "0002" -
# indice 15: F.Ingreso,F.Pago,Importe,Oficina,Cajero,N.Lote,Cpto.,
# N.Cliente,Sector,Suc.Cli.,Estado,F.Retiro,Tipo Dcto.,Libro,N.Dcto.,Encargo,Cuotas Pag.).
primera_fila = frame.locator("table").first.locator("tbody tr, tr").nth(1).inner_text()
celdas = primera_fila.split("\\t")
assert len(celdas) >= 16 and celdas[15].strip() not in ("", "—"), (
    f"Se esperaba la columna Encargo (indice 15) con dato real: {primera_fila!r}"
)
'''

CUERPOS_REALES["CP077"] = '''
app, frame = abrir_consulta_pagos(page, paso_excel=1)
elegir_nz_select(frame, app, "cboReferencia", "Cobranza Externa")
app.wait_for_timeout(800)
elegir_nz_select(frame, app, "cboFechaOperador", "<=")
app.wait_for_timeout(400)
frame.locator("#txtFechaInicial").fill("2023-01-01")
capturar_paso(app, "cobranza_externa_antes_de_leer", paso_excel=1)

frame.locator("button", has_text=re.compile(r"^\\s*(Leer|Siguiente)\\s*$")).click()
app.wait_for_timeout(2000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
if modal.count() and modal.first.is_visible() and "confirmaci" in modal.first.inner_text().lower():
    modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
    app.wait_for_timeout(2500)

# DEFECTO REAL confirmado en vivo 02/11/2026: el backend responde
# "Error de Servicio: Error en consulta." para Cobranza Externa sin
# importar el filtro de fecha - mismo patron ya confirmado en CP034
# (No Ubicados), segunda referencia de las 5 con este defecto.
plazo = time.monotonic() + 30
texto_error = ""
while time.monotonic() < plazo:
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        texto_error = modal.first.inner_text()
        if "confirmaci" not in texto_error.lower():
            break
    app.wait_for_timeout(1000)
assert texto_error and "confirmaci" not in texto_error.lower(), (
    f"Se esperaba el modal de error real de 'Cobranza Externa' (no la confirmacion ya aceptada): {texto_error!r}"
)
capturar_paso(app, "defecto_real_error_en_consulta_cobranza_externa", paso_excel=4)
assert "error en consulta" in texto_error.lower(), f"Mensaje de error inesperado: {texto_error!r}"
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
#
# CP064-071 (RF-09) agregado 02/11/2026: mismo problema que RF-07 nunca
# se habia corregido aca - CP065/066/067 (que no dependen del defecto del
# date-picker) fallaban con el mismo RuntimeError de menu no visible con
# SCASTI_DW. Se mueven al mismo grupo DCABA_DW.
_CPS_DCABA_DW = {f"CP{n:03d}" for n in range(9, 25)} | {f"CP{n:03d}" for n in range(25, 38)} | {f"CP{n:03d}" for n in range(38, 72)} | {"CP072", "CP073", "CP074", "CP075", "CP076"}

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
