"""
generate_scripts.py de PR000349-SP10 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: Migracion Modulo Gestion de Cliente - Modificacion (Sprint 10), 9 RF,
186 casos (ver matriz_casos.json). Dominio: Modificacion de datos de Cliente.
Ver Documentos/EF_texto.txt y Documentos/ET_texto.txt para el detalle completo.

Usa la arquitectura de modulos (Seccion 0c del checklist): el helper propio de
cada pantalla vive en _framework/modulos/ y se importa aca via fuente_modulo().

Cuenta de prueba unica para todo el proyecto: DCABA_DW.

Estado (13/11/2026): RF-01 (Antiguedad de Saldo) explorado en vivo con el
cliente real 15 (TOWER AND TOWER S.A.) - 13 de sus 18 casos escritos y
confirmados (CP001,002,003,008,009,010,011,012,013,014,017,018). Pendientes de
RF-01: CP004/005/006/007/016 (necesitan un segundo cliente y estados
especiales: facturacion, estado invalido, sin area de trabajo) y CP015
(necesita verificacion en BD, sin panel de historico visible en la UI). RF-02
a RF-09 (los otros 8 modulos ya tienen su ficha tecnica en _framework/modulos/
desde la exploracion de accesos, pero sus casos no se han escrito todavia).
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
import modificacion_antiguedad_saldo as modulo_antiguedad_saldo  # noqa: E402

PROYECTO = "PR000349-SP10"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)


def fuente_modulo(modulo, saltar=("PWTimeoutError",)):
    """Extrae el codigo fuente de un modulo de _framework/modulos/ (su
    docstring + todas sus funciones) para volcarlo como texto en el
    CPxxx.py generado. Ver NUEVO_PROYECTO_CHECKLIST.md Seccion 0c."""
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
    # el CPxxx.py final (bug real evitado, ver memoria: project_modulos_por_aplicativo).
    return fuente.replace("{", "{{").replace("}", "}}")


HELPERS_MODULOS = fuente_modulo(modulo_antiguedad_saldo)

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
    mensaje = f"{cp} ({rf} - {name}): falta escribir el body real - falta exploracion en vivo o dato real."
    return f"raise NotImplementedError({mensaje!r})"


CUERPOS_REALES = {}

CUERPOS_REALES["CP001"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
nombre = frame.locator("#nombre").input_value()
direccion = frame.locator("#direccion").input_value()
antiguedad = frame.locator("#antiguedadSaldo").input_value()
assert nombre == "TOWER AND TOWER S.A.", f"Nombre inesperado: {nombre!r}"
assert direccion == "CARLOS VILLARAN 1087", f"Direccion inesperada: {direccion!r}"
assert antiguedad == "1,00", f"Antiguedad de Saldo inesperada: {antiguedad!r}"
capturar_paso(app, "cliente_consultado_con_antiguedad_saldo", paso_excel=4)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
boton_leer = frame.get_by_role("button", name=re.compile(r"^\\s*Leer\\s*$"))
assert boton_leer.is_enabled(), "Leer no deberia estar deshabilitado con el campo vacio (la validacion ocurre al clickear, no antes)"
capturar_paso(app, "pantalla_sin_cliente_ingresado", paso_excel=1)

mensaje = leer_cliente_antiguedad_saldo(app, frame, "")
assert mensaje == "Debe ingresar el Número de Cliente.", f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_cliente_obligatorio", paso_excel=3)
'''

CUERPOS_REALES["CP003"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "1")
assert mensaje == "Cliente no existe.", f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_cliente_no_existe", paso_excel=3)

nombre = frame.locator("#nombre").input_value()
assert nombre == "", f"No deberian cargarse datos para un cliente inexistente: {nombre!r}"
capturar_paso(app, "pantalla_sin_datos_cargados", paso_excel=3)
'''

CUERPOS_REALES["CP008"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
numero_cliente = frame.locator("#numeroCliente")
boton_leer = frame.get_by_role("button", name=re.compile(r"^\\s*Leer\\s*$"))
assert numero_cliente.is_disabled(), "N.de Cliente deberia quedar bloqueado tras una consulta exitosa"
assert not boton_leer.is_enabled(), "Leer deberia deshabilitarse tras una consulta exitosa"
capturar_paso(app, "campo_y_boton_bloqueados_tras_leer", paso_excel=3)

# La matriz llama "Cancelar" a este paso, pero el boton real de esta
# pantalla se llama "Cerrar" (no existe un boton "Cancelar" fuera del
# dialogo de confirmacion de Modificar) - confirmado en vivo 13/11/2026.
cerrar_antiguedad_saldo(app, frame)
assert not numero_cliente.is_disabled(), "N.de Cliente deberia re-habilitarse tras Cerrar"
assert boton_leer.is_enabled(), "Leer deberia re-habilitarse tras Cerrar"
assert numero_cliente.input_value() == "", "N.de Cliente deberia quedar vacio tras Cerrar"
capturar_paso(app, "campo_y_boton_rehabilitados_tras_cerrar", paso_excel=5)
'''

CUERPOS_REALES["CP009"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
boton_manual = frame.locator("button", has_text=re.compile(r"^\\s*Manual\\s*$"))
with app.expect_download(timeout=15000) as descarga_info:
    boton_manual.first.click(force=True)
descarga = descarga_info.value
assert descarga.suggested_filename == "manual_usuario_antiguedad_saldo.pdf", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
ruta_descarga = EVIDENCIA / descarga.suggested_filename
descarga.save_as(ruta_descarga)
assert ruta_descarga.stat().st_size > 0, "El PDF descargado esta vacio"
capturar_paso(app, "manual_descargado", paso_excel=3)
'''

CUERPOS_REALES["CP010"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
valor_original = frame.locator("#antiguedadSaldo").input_value()
capturar_paso(app, "cliente_consultado_antes_de_modificar", paso_excel=1)

estado = iniciar_modificacion_antiguedad_saldo(app, frame, "5,00")
assert estado == "confirmacion", f"Se esperaba el dialogo de confirmacion (valor numerico valido y distinto del actual): {estado!r}"
capturar_paso(app, "dialogo_confirmacion_modificar", paso_excel=4)

mensaje_final = confirmar_modificacion_antiguedad_saldo(app, frame, aceptar=True)
assert mensaje_final == "Operación realizada.", f"Mensaje inesperado tras confirmar: {mensaje_final!r}"
capturar_paso(app, "modificacion_confirmada", paso_excel=6)

cerrar_antiguedad_saldo(app, frame)
mensaje2 = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje2 is None, f"No se esperaba ningun mensaje al releer: {mensaje2!r}"
valor_tras_modificar = frame.locator("#antiguedadSaldo").input_value()
assert valor_tras_modificar == "5,00", f"La Antiguedad de Saldo deberia haberse actualizado a 5,00: {valor_tras_modificar!r}"
capturar_paso(app, "cambio_persistido_verificado", paso_excel=6)

# Restaurar el valor original - cliente real (15), no un dato descartable;
# fixture debe quedar idempotente entre corridas (ver memoria: gotchas_playwright).
estado_restaurar = iniciar_modificacion_antiguedad_saldo(app, frame, valor_original)
assert estado_restaurar == "confirmacion", f"Se esperaba poder restaurar el valor original: {estado_restaurar!r}"
confirmar_modificacion_antiguedad_saldo(app, frame, aceptar=True)
'''

CUERPOS_REALES["CP011"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
valor_actual = frame.locator("#antiguedadSaldo").input_value()
capturar_paso(app, "cliente_consultado_antes_de_intentar_mismo_valor", paso_excel=1)

resultado = iniciar_modificacion_antiguedad_saldo(app, frame, valor_actual)
assert resultado == "No hubieron modificaciones.", f"Mensaje inesperado: {resultado!r}"
capturar_paso(app, "aviso_sin_modificaciones", paso_excel=4)
'''

CUERPOS_REALES["CP012"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
capturar_paso(app, "cliente_consultado_antes_de_vaciar_el_campo", paso_excel=1)

resultado = iniciar_modificacion_antiguedad_saldo(app, frame, "")
assert resultado == "Debe ingresar una Antigüedad de Saldo válida.", f"Mensaje inesperado: {resultado!r}"
capturar_paso(app, "aviso_valor_obligatorio", paso_excel=4)
'''

CUERPOS_REALES["CP013"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
boton_modificar = frame.get_by_role("button", name=re.compile(r"^\\s*Modificar\\s*$"))
assert not boton_modificar.is_enabled(), "Modificar deberia estar deshabilitado antes de cualquier Leer"
capturar_paso(app, "modificar_deshabilitado_sin_leer", paso_excel=2)
'''

CUERPOS_REALES["CP014"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
valor_original = frame.locator("#antiguedadSaldo").input_value()
capturar_paso(app, "cliente_consultado_antes_de_cancelar", paso_excel=1)

estado = iniciar_modificacion_antiguedad_saldo(app, frame, "7,00")
assert estado == "confirmacion", f"Se esperaba el dialogo de confirmacion: {estado!r}"
capturar_paso(app, "dialogo_confirmacion_antes_de_cancelar", paso_excel=4)

mensaje_cancelar = confirmar_modificacion_antiguedad_saldo(app, frame, aceptar=False)
assert mensaje_cancelar is None, f"Cancelar no deberia disparar ningun mensaje de resultado: {mensaje_cancelar!r}"
capturar_paso(app, "dialogo_cerrado_sin_confirmar", paso_excel=5)

cerrar_antiguedad_saldo(app, frame)
mensaje2 = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje2 is None, f"No se esperaba ningun mensaje al releer: {mensaje2!r}"
valor_tras_cancelar = frame.locator("#antiguedadSaldo").input_value()
assert valor_tras_cancelar == valor_original, f"Cancelar no deberia haber persistido ningun cambio: {valor_tras_cancelar!r} (original: {valor_original!r})"
capturar_paso(app, "valor_original_conservado_tras_cancelar", paso_excel=6)
'''

CUERPOS_REALES["CP017"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
valor_actual = frame.locator("#antiguedadSaldo").input_value()
capturar_paso(app, "cliente_consultado_antes_del_rechazo", paso_excel=1)

resultado = iniciar_modificacion_antiguedad_saldo(app, frame, valor_actual)
assert resultado == "No hubieron modificaciones.", f"Mensaje inesperado: {resultado!r}"
capturar_paso(app, "modificacion_rechazada", paso_excel=5)

cerrar_antiguedad_saldo(app, frame)
mensaje2 = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje2 is None, f"No se esperaba ningun mensaje al releer: {mensaje2!r}"
valor_tras_rechazo = frame.locator("#antiguedadSaldo").input_value()
assert valor_tras_rechazo == valor_actual, f"La Antiguedad de Saldo no deberia haber cambiado tras el rechazo: {valor_tras_rechazo!r} (antes: {valor_actual!r})"
capturar_paso(app, "valor_sin_cambios_verificado", paso_excel=6)
'''

CUERPOS_REALES["CP018"] = '''
app, frame = abrir_antiguedad_saldo(page, paso_excel=1)
mensaje = leer_cliente_antiguedad_saldo(app, frame, "15")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
capturar_paso(app, "cliente_consultado_antes_de_formatos_invalidos", paso_excel=1)

# #antiguedadSaldo tiene maxlength=6 - los valores son cortos a proposito
# para que no se trunquen antes de llegar a la validacion real (confirmado
# en vivo: "-100.00"/"100.555" se truncan a "100.0"/"100.55", que SI son
# validos, por eso se usan "-10,00" y "1,555" en su lugar).
casos_invalidos = [("-10,00", "negativo"), ("abc", "letras"), ("1,555", "tres_decimales")]
for valor_invalido, etiqueta in casos_invalidos:
    resultado = iniciar_modificacion_antiguedad_saldo(app, frame, valor_invalido)
    assert resultado == "Debe ingresar una Antigüedad de Saldo válida.", f"Mensaje inesperado para {etiqueta} ({valor_invalido!r}): {resultado!r}"
    capturar_paso(app, f"formato_invalido_rechazado_{etiqueta}", paso_excel=3)

cerrar_antiguedad_saldo(app, frame)
'''

_CPS_TODOS = sorted(MATRIZ, key=lambda x: int(x[2:]))
for _cp in _CPS_TODOS:
    _m = MATRIZ[_cp]
    _body = CUERPOS_REALES.get(_cp) or _body_pendiente(_cp, _m["rf"], _m["name"])
    add(_cp, _body)


if __name__ == "__main__":
    for c in CASES:
        (OUT_DIR / f"{c['cp']}.py").write_text(render(c), encoding="utf-8")
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
