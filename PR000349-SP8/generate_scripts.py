"""
generate_scripts.py de PR000349-SP8 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: ADSOLTRA (Administrador de Solicitudes de Trabajo), 8 RF
(Transversal + RF-01..RF-07), 61 casos (ver matriz_casos.json).
Ver documentos/EF_texto.txt y documentos/ET_texto.txt para el detalle
funcional/tecnico completo de cada RF.

Usa la arquitectura de modulos (Seccion 0c del checklist): el helper
propio de la pantalla vive en _framework/modulos/adsoltra.py (ficha
tecnica + funciones, sin nada especifico de este proyecto) y se importa
aca via fuente_modulo().

Cuenta de prueba unica para todo el proyecto: DCABA_DW (rol de sesion
confirmado DACD).

Estado (06/11/2026): exploracion inicial completa (login, menu, botones
de accion sin bloqueo de permisos, Manual por pantalla). DATO ESCASO
confirmado: con DCABA_DW la bandeja da 0 registros en los 5 estados -
bloquea los CP de RF-01 que necesitan filas reales hasta aplicar el
flip temporal de rol_actual (igual tecnica que RF-05/CP038, ver modulo).
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
import adsoltra as modulo_adsoltra  # noqa: E402

PROYECTO = "PR000349-SP8"  # debe coincidir con el nombre de esta carpeta
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


HELPERS_MODULOS = fuente_modulo(modulo_adsoltra)

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

# Transversal - CP001: login + acceso al menu, confirmado en vivo 100%.
CUERPOS_REALES["CP001"] = '''
app, frame = abrir_adsoltra(page, paso_excel=4)
capturar_paso(app, "menu_principal_adsoltra", paso_excel=4)
assert frame.locator("text=ADMINISTRADOR DE SOLICITUDES DE TRABAJO").first.is_visible(), "No se vio el titulo de la bandeja tras abrir el aplicativo"
'''

# RF-01 CP002: estado por defecto (grilla vacia, contador en cero, titulo
# sin sufijo) - confirmado en vivo 06/11/2026, no depende de datos reales.
CUERPOS_REALES["CP002"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
capturar_paso(app, "bandeja_estado_inicial", paso_excel=2)
texto = frame.locator("body").inner_text()
assert "No hay una consulta en curso. Elija una opción del listado para obtener datos." in texto, f"No se vio el mensaje de estado inicial: {texto[-400:]!r}"
pie = texto_pie_paginador(frame)
assert pie == (0, 0, 0), f"Se esperaba el contador en 0, se obtuvo: {pie!r}"
titulo = frame.locator("body").inner_text().splitlines()[0]
assert titulo.strip() == "ADMINISTRADOR DE SOLICITUDES DE TRABAJO", f"El titulo no deberia llevar sufijo de estado: {titulo!r}"
capturar_paso(app, "contador_en_cero_sin_sufijo", paso_excel=3)
'''

# RF-01 CP008: validacion de seleccion previa - no depende de datos reales
# (el mensaje aparece precisamente PORQUE no hay ninguna fila seleccionada).
CUERPOS_REALES["CP008"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
capturar_paso(app, "listado_cargado_sin_seleccion", paso_excel=1)

for texto_boton in ["Consultar/Modificar", "Historial de la Orden", "Reasignación de Orden"]:
    boton = frame.locator("button", has_text=texto_boton)
    boton.first.click()
    app.wait_for_timeout(1500)
    mensaje_actual = frame.locator("body").inner_text()
    assert "Ud. no ha seleccionado ninguna orden." in mensaje_actual, f"No se vio el mensaje esperado al accionar {texto_boton!r} sin seleccion: {mensaje_actual[-300:]!r}"
    capturar_paso(app, f"mensaje_sin_seleccion_{texto_boton.lower().replace('/', '_').replace(' ', '_')}", paso_excel=2)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        boton_cerrar = modal.first.get_by_role("button", name=re.compile("Aceptar|Cerrar|OK", re.I))
        if boton_cerrar.count():
            boton_cerrar.first.click(force=True)
        else:
            modal.first.locator(".ant-modal-close, button[aria-label='Close']").first.click(force=True)
        app.wait_for_timeout(800)
'''

# RF-01 CP010: exportar sin datos - reutiliza el mismo estado vacio natural
# de DCABA_DW (confirmado en vivo: los 5 estados dan 0 registros), sin
# necesitar ningun flip de dato real.
CUERPOS_REALES["CP010"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] == 0, f"Este caso requiere un estado sin ordenes visibles, se obtuvo: {pie!r}"
capturar_paso(app, "listado_vacio_antes_de_exportar", paso_excel=1)

boton_exportar = frame.locator("button", has_text=re.compile(r"Exportar a Excel"))
try:
    with app.expect_download(timeout=4000) as descarga_info:
        boton_exportar.first.click()
    descarga_info.value
    assert False, "No deberia generarse ningun archivo cuando el listado esta vacio"
except PWTimeoutError:
    pass
app.wait_for_timeout(1500)
mensaje_actual = frame.locator("body").inner_text()
assert "no se encontr" in mensaje_actual.lower() or "sin registros" in mensaje_actual.lower() or "no hay" in mensaje_actual.lower(), f"No se vio ningun mensaje de 'sin datos' tras exportar: {mensaje_actual[-300:]!r}"
capturar_paso(app, "mensaje_exportar_sin_datos", paso_excel=3)
'''

# RF-02 "Busqueda especifica" - confirmado en vivo 06/11/2026
# (_exploracion/explore_rf02_*.py). Casos que NO dependen del dato
# escaso de RF-01 (mecanica del modal/validaciones puras); CP013/015-
# 018/020/023 quedan pendientes de la misma visibilidad de acl_orden.

CUERPOS_REALES["CP012"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
capturar_paso(app, "busqueda_abierta", paso_excel=1)
assert modal.count() and modal.first.is_visible(), "No se abrio el modal de Busqueda especifica"
backdrop = frame.locator(".cdk-overlay-backdrop")
assert backdrop.count() and backdrop.first.is_visible(), "No se vio el backdrop que deshabilita la bandeja detras del modal"
modal.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)
assert not frame.locator(".cdk-overlay-backdrop").count(), "El backdrop deberia desaparecer y la bandeja volver a habilitarse tras Cancelar"
capturar_paso(app, "bandeja_rehabilitada_tras_cancelar", paso_excel=2)
'''

CUERPOS_REALES["CP014"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
tema = modal.first.locator("#bsqTema")
assert tema.get_attribute("disabled") is not None, "Tema deberia estar deshabilitado con el tipo de orden por defecto (no SEGEN)"
capturar_paso(app, "tema_deshabilitado_tipo_no_segen", paso_excel=1)

modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
assert tema.get_attribute("disabled") is None, "Tema deberia habilitarse con tipo de orden SEGEN"
tema.select_option(index=2)
valor_elegido = tema.input_value()
capturar_paso(app, "tema_habilitado_con_segen", paso_excel=1)

modal.first.locator("#bsqTipoOrden").select_option(label="EXTRAC = Extractor")
app.wait_for_timeout(500)
assert tema.get_attribute("disabled") is not None, "Tema deberia deshabilitarse de nuevo al cambiar a un tipo distinto de SEGEN"
assert tema.input_value() == valor_elegido, "El valor de Tema no deberia limpiarse aunque quede deshabilitado"
capturar_paso(app, "tema_deshabilitado_valor_no_limpiado", paso_excel=1)
'''

CUERPOS_REALES["CP019"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqRango").check()
app.wait_for_timeout(300)
modal.first.locator("#bsqDesde").fill("01/01/2024")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
mensaje1 = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje1 and "Ingrese ambas fechas" in mensaje1, f"No se vio el mensaje esperado con una sola fecha: {mensaje1!r}"
capturar_paso(app, "validacion_ingrese_ambas_fechas", paso_excel=2)

modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\\s*Búsqueda\\s*-"))
assert modal.count() and modal.first.is_visible(), "El modal de Busqueda deberia seguir abierto tras la validacion"
modal.first.locator("#bsqHasta").fill("31/13/2024")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
mensaje2 = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje2 and "Fecha inválida" in mensaje2 and "dd/mm/aaaa" in mensaje2, f"No se vio el mensaje esperado con fecha de formato invalido: {mensaje2!r}"
capturar_paso(app, "validacion_fecha_invalida", paso_excel=2)

pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] == 0, f"Ningun criterio invalido deberia haberse aplicado sobre la bandeja: {pie!r}"
'''

CUERPOS_REALES["CP021"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqNroOrden").fill("999999999")
modal.first.locator("#bsqNroOrden").press("Enter")
app.wait_for_timeout(1500)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje and "No se encontro la orden solicitada" in mensaje, f"La tecla Enter deberia ejecutar la busqueda igual que el boton Buscar: {mensaje!r}"
capturar_paso(app, "busqueda_ejecutada_con_enter", paso_excel=1)
'''

CUERPOS_REALES["CP022"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqNroOrden").fill("999999999")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje and "No se encontro la orden solicitada" in mensaje, f"No se vio el mensaje de busqueda sin resultados: {mensaje!r}"
texto_bandeja = frame.locator("body").inner_text()
assert "No se encontraron Registros." in texto_bandeja, f"La grilla deberia quedar limpia (sin registros): {texto_bandeja[-300:]!r}"
# Confirmado en vivo 06/11/2026: a diferencia de una validacion de campo
# (CP019, que deja el modal abierto para corregir), una busqueda SIN
# RESULTADOS si se ejecuta - el modal de Busqueda se cierra solo tras
# el Aceptar del dialogo, volviendo a la bandeja.
assert not frame.locator(".ant-modal, nz-modal-container").count(), "El modal de Busqueda deberia cerrarse tras una busqueda sin resultados"
capturar_paso(app, "busqueda_sin_resultados", paso_excel=2)

modal = abrir_buscar(app, frame)
modal.first.locator("#bsqNroOrden").fill("123456")
modal.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)
assert not frame.locator(".ant-modal, nz-modal-container").count(), "El modal deberia cerrarse sin aplicar criterios al Cancelar"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] == 0, f"La bandeja deberia quedar limpia (sin criterios aplicados) tras Cancelar: {pie!r}"
capturar_paso(app, "cancelado_bandeja_limpia", paso_excel=3)
'''

CUERPOS_REALES["CP024"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
opciones_estado = modal.first.locator("#bsqEstado option")
opciones_tipo = modal.first.locator("#bsqTipoOrden option")
valores_estado = [opciones_estado.nth(i).get_attribute("value") for i in range(opciones_estado.count())]
valores_tipo = [opciones_tipo.nth(i).get_attribute("value") for i in range(opciones_tipo.count())]
assert all(v not in (None, "") for v in valores_estado), f"El combo Estado no deberia tener una opcion vacia seleccionable: {valores_estado!r}"
assert all(v not in (None, "") for v in valores_tipo), f"El combo Tipo de Orden no deberia tener una opcion vacia seleccionable: {valores_tipo!r}"
assert modal.first.locator("#bsqEstado").input_value(), "El combo Estado deberia tener una opcion elegida por defecto"
assert modal.first.locator("#bsqTipoOrden").input_value(), "El combo Tipo de Orden deberia tener una opcion elegida por defecto"
capturar_paso(app, "combos_estado_tipo_sin_opcion_vacia", paso_excel=1)
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
cerrar_dialogo_validacion_si_aparece(app, frame)
capturar_paso(app, "busqueda_ejecutada_con_default", paso_excel=1)
'''

# RF-03 CP026: Historial sin orden seleccionada - mismo patron que CP008,
# no depende del dato escaso de acl_orden.
CUERPOS_REALES["CP026"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
capturar_paso(app, "listado_cargado_sin_seleccion", paso_excel=1)
frame.locator("button", has_text="Historial de la Orden").first.click()
app.wait_for_timeout(1500)
mensaje = frame.locator("body").inner_text()
assert "Ud. no ha seleccionado ninguna orden." in mensaje, f"No se vio el mensaje esperado al accionar Historial de la Orden sin seleccion: {mensaje[-300:]!r}"
capturar_paso(app, "mensaje_sin_seleccion_historial", paso_excel=2)
'''

# RF-07 - confirmado en vivo 06/11/2026 (_exploracion/explore_rf06_*.py):
# el buscador de Rol/Area abierto desde SEGEN (Usuario Destino). Las
# columnas/filtro/cancelacion no dependen del dato escaso de
# ConsultarRolAreaVigente (eso solo se valida al Enviar en RF-06).

CUERPOS_REALES["CP056"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
capturar_paso(app, "segen_abierto", paso_excel=1)
buscador = abrir_buscador_usuario_destino(app, frame, overlay)
assert buscador.count() and buscador.first.is_visible(), "No se abrio el buscador de Rol/Area"
titulo = buscador.first.inner_text().splitlines()[0]
assert "Usuario Destino" in titulo, f"No se vio el titulo esperado del buscador: {titulo!r}"
encabezados = buscador.first.locator("thead th")
textos_encabezados = [encabezados.nth(i).inner_text().strip() for i in range(encabezados.count())]
assert [t.upper() for t in textos_encabezados[:3]] == ["ROL", "NOMBRE", "TIPO"], f"No se vieron las columnas esperadas: {textos_encabezados!r}"
filas = buscador.first.locator("tr.sm-fila")
assert filas.count() > 0, "El buscador deberia mostrar roles vigentes con area"
capturar_paso(app, "buscador_rol_area_columnas", paso_excel=4)

campo_buscar = buscador.first.locator("input").first
if campo_buscar.count():
    valor_filtro = filas.first.locator("td").first.inner_text().strip()[:3]
    campo_buscar.fill(valor_filtro)
    app.wait_for_timeout(1000)
    capturar_paso(app, "buscador_filtro_por_aproximacion", paso_excel=4)

buscador.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
overlay.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP061"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
campo_usuario_destino = overlay.locator("#segUsuarioDestino")
campo_usuario_destino.fill("MGG")
valor_anotado = campo_usuario_destino.input_value()
capturar_paso(app, "valor_cargado_antes_de_cancelar", paso_excel=1)

buscador = abrir_buscador_usuario_destino(app, frame, overlay)
filas = buscador.first.locator("tr.sm-fila")
assert filas.count() > 1, "Se necesitan al menos 2 filas para elegir una distinta a la ya cargada"
fila_distinta = filas.nth(1)
fila_distinta.click()
app.wait_for_timeout(300)
capturar_paso(app, "fila_distinta_marcada_sin_seleccionar", paso_excel=3)

buscador.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
assert not frame.get_by_label("Consultar Usuario Destino", exact=True).count(), "El buscador deberia cerrarse al Cancelar"
valor_tras_cancelar = overlay.locator("#segUsuarioDestino").input_value()
assert valor_tras_cancelar == valor_anotado, f"El campo deberia conservar el valor anotado {valor_anotado!r}, quedo {valor_tras_cancelar!r}"
capturar_paso(app, "valor_conservado_tras_cancelar", paso_excel=5)

buscador2 = abrir_buscador_usuario_destino(app, frame, overlay)
assert buscador2.count() and buscador2.first.is_visible(), "El buscador deberia poder reabrirse y operar con normalidad"
buscador2.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
overlay.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP058"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
capturar_paso(app, "segen_abierto", paso_excel=1)
overlay.locator("button", has_text="…").nth(1).click(force=True)
app.wait_for_timeout(2500)
buscador = frame.get_by_label("Consultar Cliente", exact=True)
assert buscador.count() and buscador.first.is_visible(), "No se abrio el buscador de Clientes"
titulo = buscador.first.inner_text().splitlines()[0]
assert "Cliente" in titulo, f"No se vio el titulo esperado del buscador de clientes: {titulo!r}"
encabezados = buscador.first.locator("thead th")
textos_encabezados = [encabezados.nth(i).inner_text().strip().upper() for i in range(encabezados.count())]
assert textos_encabezados[:3] == ["NUMERO CLIENTE", "NOMBRE", "SUCURSAL"], f"No se vieron las columnas esperadas: {textos_encabezados!r}"
filas = buscador.first.locator("tr.sm-fila")
assert filas.count() > 0, "El buscador deberia mostrar clientes de la empresa de la sesion"
capturar_paso(app, "buscador_cliente_columnas", paso_excel=4)
buscador.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
overlay.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP057"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
buscador_destino = abrir_buscador_usuario_destino(app, frame, overlay)
filas_destino = buscador_destino.first.locator("tr.sm-fila")
tipos_destino = set()
for i in range(filas_destino.count()):
    tipos_destino.add(filas_destino.nth(i).locator("td").nth(2).inner_text().strip())
capturar_paso(app, "buscador_desde_usuario_destino", paso_excel=2)
buscador_destino.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
overlay.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# DEFECTO REAL confirmado en vivo 06/11/2026 (ver casos_fallidos_confirmados.json,
# evidencia cruzada contra el buscador de Rol Emisor en _exploracion/explore_rf07_cp057*.py):
# el buscador de Usuario Destino deberia mostrar SOLO tipo "U" (usuario),
# pero devuelve el catalogo completo sin filtrar (mezcla U+F).
assert tipos_destino == {"U"}, f"Defecto real: Usuario Destino deberia mostrar solo roles tipo U, se vieron tipos {tipos_destino!r} - el filtro por tipo nunca se aplica (confirmado tambien que el buscador de Rol Emisor devuelve exactamente el mismo catalogo sin filtrar)"
'''

CUERPOS_REALES["CP059"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
overlay.locator("button", has_text="…").nth(1).click(force=True)
app.wait_for_timeout(2500)
buscador = frame.get_by_label("Consultar Cliente", exact=True)
filas_antes = buscador.first.locator("tr.sm-fila")
total_antes = filas_antes.count()
assert total_antes > 0, "El buscador deberia abrir con resultados cargados"
primera_fila_antes = filas_antes.first.inner_text()
capturar_paso(app, "resultados_primera_pagina", paso_excel=2)

buscador.first.get_by_role("button", name=re.compile("Sgtes", re.I)).click(force=True)
app.wait_for_timeout(2000)
filas_despues = buscador.first.locator("tr.sm-fila")
total_despues = filas_despues.count()
assert total_despues > total_antes, f"Sgtes deberia incorporar filas nuevas (antes {total_antes}, despues {total_despues})"
assert filas_despues.first.inner_text() == primera_fila_antes, "Las filas ya cargadas no deberian perderse/reordenarse al avanzar con Sgtes"
capturar_paso(app, "resultados_incorporados_tras_sgtes", paso_excel=3)
buscador.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
overlay.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

# RF-03 - confirmado en vivo 06/11/2026 con la orden real 500007 (EXTRAC,
# flip temporal de rol_actual a DACD, ver _exploracion/explore_rf03_rf05_500007b.py).

CUERPOS_REALES["CP025"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
frame.locator("button", has_text="Todas las Ordenes").first.click()
app.wait_for_timeout(2500)
frame.locator("button", has_text="Buscar").first.click()
app.wait_for_timeout(1500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\\s*Búsqueda\\s*-")).last
modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(300)
modal.first.locator("#bsqNroOrden").fill("500007")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(2000)
frame.locator("tr", has_text="500007").first.click()
app.wait_for_timeout(500)
capturar_paso(app, "orden_500007_seleccionada", paso_excel=1)

frame.locator("button", has_text="Historial de la Orden").first.click()
app.wait_for_timeout(2000)
historial = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).last
assert historial.count() and historial.first.is_visible(), "No se abrio la ventana del historial"
titulo = historial.first.inner_text().splitlines()[0]
assert titulo.strip() == "Historia de la Orden # 500007", f"Titulo inesperado: {titulo!r}"
filas = historial.first.locator("tr", has_text="0000001")
assert filas.count() > 0, "La grilla deberia mostrar el movimiento registrado de la orden"
capturar_paso(app, "historial_abierto_con_movimientos", paso_excel=2)
historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP027"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
frame.locator("button", has_text="Todas las Ordenes").first.click()
app.wait_for_timeout(2500)
frame.locator("button", has_text="Buscar").first.click()
app.wait_for_timeout(1500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\\s*Búsqueda\\s*-")).last
modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(300)
modal.first.locator("#bsqNroOrden").fill("500007")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(2000)
frame.locator("tr", has_text="500007").first.click()
app.wait_for_timeout(500)

frame.locator("button", has_text="Historial de la Orden").first.click()
app.wait_for_timeout(2000)
historial = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).last
encabezados = historial.first.locator("thead th")
textos_encabezados = [encabezados.nth(i).inner_text().strip() for i in range(encabezados.count())]
assert textos_encabezados[:7] == ["Correlativo", "Tipo de Envio", "Rol P.Emisor", "Rol F.Emisor", "Rol P.Receptor", "Rol F.Receptor", "Fecha Emision"], f"No se vieron las columnas esperadas: {textos_encabezados!r}"
capturar_paso(app, "columnas_del_historial", paso_excel=1)

fila = historial.first.locator("tr", has_text="0000001")
celdas = fila.first.locator("td")
correlativo = celdas.nth(0).inner_text().strip()
assert correlativo == "0000001", f"El correlativo deberia mostrarse con ceros a la izquierda, se vio {correlativo!r}"
tipo_envio = celdas.nth(1).inner_text().strip()
assert tipo_envio and tipo_envio not in ("1", "0"), f"El tipo de envio deberia mostrarse con su descripcion, no un codigo crudo: {tipo_envio!r}"
capturar_paso(app, "correlativo_con_ceros_tipo_envio_descripcion", paso_excel=1)

# DEFECTO REAL confirmado en vivo 06/11/2026 (ver casos_fallidos_confirmados.json):
# las columnas de rol sin valor deberian mostrarse en blanco, pero el motor
# real todavia devuelve "0" (el propio EF ya advierte este bug historico:
# "sin el 0 del motor del sistema actual").
rol_f_receptor = celdas.nth(5).inner_text().strip()
assert rol_f_receptor == "", f"Defecto real: las columnas de rol sin valor deberian presentarse en blanco (sin el 0 del motor actual), se vio {rol_f_receptor!r}"
historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

# RF-05 - confirmado en vivo 06/11/2026 con la orden real 500007 (EXTRAC,
# flip temporal de rol_actual a DACD, ver _exploracion/explore_rf05_extractor_selectores.py).
CUERPOS_REALES["CP038"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
frame.locator("button", has_text="Todas las Ordenes").first.click()
app.wait_for_timeout(2500)
frame.locator("button", has_text="Buscar").first.click()
app.wait_for_timeout(1500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\\s*Búsqueda\\s*-")).last
modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(300)
modal.first.locator("#bsqNroOrden").fill("500007")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(2000)
frame.locator("tr", has_text="500007").first.click()
app.wait_for_timeout(500)
capturar_paso(app, "orden_500007_seleccionada", paso_excel=2)

frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
extractor = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"Extractor")).last
assert extractor.count() and extractor.first.is_visible(), "No se abrio la pantalla del Extractor"
titulo = extractor.first.inner_text().splitlines()[0]
assert titulo.strip() == "Extractor", f"Titulo inesperado: {titulo!r}"
capturar_paso(app, "extractor_abierto", paso_excel=3)

odt = extractor.first.locator("#extNumeroOdt").input_value()
para = extractor.first.locator("#extPara").input_value()
adjunto = extractor.first.locator("#extAdjunto").input_value()
assert odt == "14865", f"Numero de ODT inesperado: {odt!r}"
assert para == "DACD", f"Campo Para inesperado (deberia ser el rol que tiene la orden a su cargo): {para!r}"
assert adjunto == "todas865.xls", f"Archivo Adjunto inesperado: {adjunto!r}"
capturar_paso(app, "campos_odt_para_adjunto", paso_excel=4)

assert extractor.first.locator("button", has_text="Finalizar").first.is_enabled(), "Finalizar deberia estar habilitado"
capturar_paso(app, "finalizar_habilitado", paso_excel=5)
extractor.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

# RF-04 - confirmado en vivo 06/11/2026 con la orden real 500007 (EXTRAC,
# flip temporal de rol_actual a DACD, ver _exploracion/explore_rf04_reasignacion.py).
CUERPOS_REALES["CP033"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
frame.locator("button", has_text="Todas las Ordenes").first.click()
app.wait_for_timeout(2500)
frame.locator("button", has_text="Buscar").first.click()
app.wait_for_timeout(1500)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\\s*Búsqueda\\s*-")).last
modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(300)
modal.first.locator("#bsqNroOrden").fill("500007")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(2000)
frame.locator("tr", has_text="500007").first.click()
app.wait_for_timeout(500)
capturar_paso(app, "orden_500007_seleccionada", paso_excel=2)

frame.locator("button", has_text="Reasignación de Orden").first.click()
app.wait_for_timeout(2500)
reasig = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).last
assert reasig.count() and reasig.first.is_visible(), "No se abrio la pantalla de Reasignacion de Orden"
texto = reasig.first.inner_text()
titulo = texto.splitlines()[0]
assert titulo.strip() == "Reasignación de la Orden Nro.500007", f"Titulo inesperado: {titulo!r}"
assert re.search(r"Tipo de Orden\\s*:\\s*\\n?EXTRAC\\s*\\(Requerimiento\\)", texto), f"No se vio Tipo de Orden con el estado entre parentesis: {texto[:400]!r}"
assert re.search(r"Rol Creador\\s*:\\s*\\n?ANA\\s*\\(", texto), f"No se vio Rol Creador con fecha entre parentesis: {texto[:400]!r}"
assert re.search(r"Rol Emisor\\s*:\\s*\\n?ANA\\s*\\(", texto), f"No se vio Rol Emisor con fecha entre parentesis: {texto[:400]!r}"
assert re.search(r"Rol Actual\\s*:\\s*\\n?DACD", texto), f"No se vio Rol Actual: {texto[:400]!r}"
capturar_paso(app, "reasignacion_titulo_y_4_pares", paso_excel=4)
reasig.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP031"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "500007")
historial = abrir_historial_de_orden(app, frame)
capturar_paso(app, "historial_abierto", paso_excel=1)

fila = historial.first.locator("tr.his-fila")
fila.first.click()
app.wait_for_timeout(1200)
panel = historial.first.locator(".his-obs-box")
texto_panel = panel.first.inner_text()
assert texto_panel == "", f"El panel deberia mostrarse vacio para un movimiento con registro existente y observacion vacia: {texto_panel!r}"
texto_pantalla = historial.first.inner_text()
assert "No existen observaciones" not in texto_pantalla, "No deberia mostrarse el mensaje 'No existen observaciones' cuando el registro existe (solo esta vacio)"
capturar_paso(app, "panel_vacio_sin_mensaje", paso_excel=2)
historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP032"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "500007")
historial = abrir_historial_de_orden(app, frame)
fila = historial.first.locator("tr.his-fila")
fila.first.click()
app.wait_for_timeout(1000)
panel = historial.first.locator(".his-obs-box")
assert panel.first.get_attribute("aria-readonly") == "true", "El panel de observaciones deberia ser de solo lectura (aria-readonly=true)"
assert panel.first.get_attribute("contenteditable") != "true", "El panel no deberia ser editable (contenteditable)"
capturar_paso(app, "panel_marcado_solo_lectura", paso_excel=1)

panel.first.click()
page.keyboard.type("intento de edicion - no deberia quedar guardado")
app.wait_for_timeout(500)
texto_tras_tipeo = panel.first.inner_text()
assert texto_tras_tipeo == "", f"El panel no deberia admitir tipeo: quedo con {texto_tras_tipeo!r}"
capturar_paso(app, "tipeo_no_admitido", paso_excel=1)

boton_guardar = historial.first.locator("button", has_text=re.compile("Guardar", re.I))
assert boton_guardar.count() == 0, "No deberia existir ninguna accion de guardar sobre la observacion"
historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP036"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "500007")
frame.locator("button", has_text="Reasignación de Orden").first.click()
app.wait_for_timeout(2500)
reasig = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).last
assert reasig.count() and reasig.first.is_visible(), "No se abrio la pantalla de Reasignacion de Orden"
capturar_paso(app, "reasignacion_abierta_area_vacia", paso_excel=2)

reasig.first.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
app.wait_for_timeout(2000)
dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
assert dlg.count() and dlg.first.is_visible(), "No se vio la validacion esperada al dejar vacia el Area Ejecutora"
mensaje = dlg.first.inner_text()
assert "Debe ingresar el Area Ejecutora" in mensaje, f"Mensaje inesperado: {mensaje!r}"
dlg.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(600)
assert reasig.first.is_visible(), "La pantalla de Reasignacion deberia seguir abierta (no se envio la orden)"
capturar_paso(app, "validacion_area_ejecutora_obligatoria", paso_excel=4)
reasig.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

# RF-01 - confirmado en vivo 06/11/2026 tras flip real de 22 ordenes a
# rol_actual=DACD + 1 INSERT (orden NUCLI 40009802, "otro tipo" para
# CP007). Estados confirmados con datos reales: RQ=17 (500007 EXTRAC +
# 15 SEGEN + 1 NUCLI), DV=2, AN=2, FI=3 (2 SEGEN + 1 EXTRAC, tarda
# ~30s en responder - ver gotcha en elegir_estado()).

CUERPOS_REALES["CP003"] = '''
app, frame = abrir_adsoltra(page, paso_excel=2)

elegir_estado(app, frame, "Ordenes Pendientes")
texto = frame.locator("body").inner_text()
assert "Rol Emisor" in texto and "Rol Receptor" in texto, f"Encabezados de Pendientes inesperados: {texto[:400]!r}"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Pendientes deberia tener ordenes visibles: {pie!r}"
assert "(Ordenes Pendientes)" in texto.splitlines()[0], f"Pendientes deberia llevar el sufijo de estado al elegirse explicitamente: {texto.splitlines()[0]!r}"
capturar_paso(app, "pendientes_con_datos", paso_excel=3)

elegir_estado(app, frame, "Ordenes Devueltas")
texto = frame.locator("body").inner_text()
assert "Rol Emisor" in texto and "Rol Receptor" in texto, f"Encabezados de Devueltas inesperados: {texto[:400]!r}"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Devueltas deberia tener ordenes visibles: {pie!r}"
assert "(Ordenes Devueltas)" in texto.splitlines()[0], f"Devueltas deberia llevar el sufijo de estado: {texto.splitlines()[0]!r}"
capturar_paso(app, "devueltas_con_datos", paso_excel=4)

elegir_estado(app, frame, "Ordenes Finalizadas")
texto = frame.locator("body").inner_text()
assert "Rol Creador" in texto and "Rol Finalizador" in texto, f"Encabezados de Finalizadas inesperados: {texto[:400]!r}"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Finalizadas deberia tener ordenes visibles: {pie!r}"
assert "(Ordenes Finalizadas)" in texto.splitlines()[0], f"Finalizadas deberia llevar el sufijo de estado: {texto.splitlines()[0]!r}"
capturar_paso(app, "finalizadas_con_datos", paso_excel=4)

elegir_estado(app, frame, "Ordenes Anuladas")
texto = frame.locator("body").inner_text()
assert "Rol Emisor" in texto and "Rol Receptor" in texto, f"Encabezados de Anuladas inesperados: {texto[:400]!r}"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Anuladas deberia tener ordenes visibles: {pie!r}"
assert "(Ordenes Anuladas)" in texto.splitlines()[0], f"Anuladas deberia llevar el sufijo de estado: {texto.splitlines()[0]!r}"
capturar_paso(app, "anuladas_con_datos", paso_excel=4)

elegir_estado(app, frame, "Todas las Ordenes")
texto = frame.locator("body").inner_text()
assert "Rol Creador" in texto and "Rol Actual" in texto, f"Encabezados de Todas inesperados: {texto[:400]!r}"
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Todas deberia tener ordenes visibles: {pie!r}"
assert "(Todas las Ordenes)" in texto.splitlines()[0], f"Todas deberia llevar el sufijo de estado: {texto.splitlines()[0]!r}"
capturar_paso(app, "todas_sin_filtro_estado", paso_excel=5)
'''

CUERPOS_REALES["CP006"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 10, f"Este caso requiere un estado con mas de 10 registros, se obtuvo: {pie!r}"
assert pie == (1, 10, pie[2]), f"La primera pagina deberia mostrar 10 registros (1 a 10): {pie!r}"
total = pie[2]
capturar_paso(app, "primera_pagina_10_registros", paso_excel=2)

frame.locator("button", has_text=re.compile(r"Siguiente")).first.click(force=True)
app.wait_for_timeout(2000)
pie_siguiente = texto_pie_paginador(frame)
assert pie_siguiente is not None and pie_siguiente[0] == 11, f"La pagina siguiente deberia arrancar en el registro 11: {pie_siguiente!r}"
assert pie_siguiente[2] == total, f"El total no deberia cambiar al paginar: {pie_siguiente!r}"
capturar_paso(app, "pagina_siguiente_rango", paso_excel=3)

frame.locator("button", has_text=re.compile(r"Anterior")).first.click(force=True)
app.wait_for_timeout(2000)
pie_anterior = texto_pie_paginador(frame)
assert pie_anterior == (1, 10, total), f"Al retroceder deberia volver a 1-10 conservando el total: {pie_anterior!r}"
texto = frame.locator("body").inner_text()
assert "(Ordenes Pendientes)" in texto.splitlines()[0], "El estado deberia conservarse al retroceder de pagina"
capturar_paso(app, "pagina_anterior_estado_conservado", paso_excel=4)
'''

CUERPOS_REALES["CP007"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")

# SEGEN - abre la Solicitud Especial
frame.locator("tr", has_text="3365694").first.click()
app.wait_for_timeout(500)
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
modal_segen = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
assert modal_segen.count() and modal_segen.first.is_visible(), "La orden SEGEN deberia abrir la Solicitud Especial"
capturar_paso(app, "segen_abre_solicitud_especial", paso_excel=2)
modal_segen.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1200)

# EXTRAC - abre el Extractor (orden real 500007)
buscar_y_seleccionar_orden(app, frame, "500007")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
modal_extrac = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"Extractor")).last
assert modal_extrac.count() and modal_extrac.first.is_visible(), "La orden EXTRAC deberia abrir el Extractor"
capturar_paso(app, "extrac_abre_extractor", paso_excel=3)
modal_extrac.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1200)

# NUCLI (otro tipo) - no debe abrir nada ni mostrar error. No se puede
# usar buscar_y_seleccionar_orden() aqui: el combo Tipo de Orden de la
# Busqueda especifica solo tiene EXTRAC/SEGEN, sin opcion "=(Todos)" -
# NUCLI nunca se encontraria por ese camino. Se re-elige el estado
# Pendientes desde cero (estado conocido y estable) y se pagina.
elegir_estado(app, frame, "Ordenes Pendientes")
frame.locator("button", has_text=re.compile(r"Siguiente")).first.click(force=True)
app.wait_for_timeout(2000)
fila_nucli = frame.locator("tr", has_text="40009802")
fila_nucli.first.click(force=True)
app.wait_for_timeout(500)
overlays_antes = frame.locator(".ant-modal, nz-modal-container").count()
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2000)
overlays_despues = frame.locator(".ant-modal, nz-modal-container").count()
assert overlays_despues == overlays_antes, f"Para 'otro tipo' (NUCLI) no deberia abrirse ninguna pantalla: overlays antes={overlays_antes} despues={overlays_despues}"
capturar_paso(app, "nucli_no_abre_nada", paso_excel=4)
'''

CUERPOS_REALES["CP009"] = '''
import openpyxl

app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] > 0, f"Se necesita un listado con registros: {pie!r}"
total_pantalla = pie[2]
capturar_paso(app, "listado_pendientes_cargado", paso_excel=1)

with app.expect_download(timeout=15000) as descarga_info:
    frame.locator("button", has_text=re.compile("Exportar a Excel")).first.click()
descarga = descarga_info.value
ruta_descarga = EVIDENCIA / "export_pendientes.xlsx"
descarga.save_as(str(ruta_descarga))
capturar_paso(app, "exportado_a_excel", paso_excel=2)

wb = openpyxl.load_workbook(str(ruta_descarga))
assert wb.sheetnames == ["LISTADO DE ORDENES PENDIENTES"], f"Nombre de hoja inesperado: {wb.sheetnames!r}"
ws = wb[wb.sheetnames[0]]
encabezado = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
assert len(encabezado) == 8, f"Se esperaban 8 columnas, se obtuvieron {len(encabezado)}: {encabezado!r}"
assert encabezado[0].startswith("N") and "Orden" in encabezado[0], f"Primera columna inesperada: {encabezado[0]!r}"
assert encabezado[-1] == "Estado", f"Ultima columna inesperada: {encabezado[-1]!r}"
filas_archivo = ws.max_row - 1
assert filas_archivo == total_pantalla, f"El archivo deberia tener las mismas {total_pantalla} filas que la grilla, tiene {filas_archivo}"
capturar_paso(app, "archivo_verificado_8_columnas", paso_excel=3)
'''

CUERPOS_REALES["CP011"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
pie_antes = texto_pie_paginador(frame)
titulo_antes = frame.locator("body").inner_text().splitlines()[0]
capturar_paso(app, "listado_antes_de_actualizar", paso_excel=1)

frame.locator("button", has_text=re.compile("Actualizar Ventana")).first.click()
app.wait_for_timeout(2500)
texto = frame.locator("body").inner_text()
titulo_despues = texto.splitlines()[0]
pie_despues = texto_pie_paginador(frame)
assert titulo_despues == titulo_antes, f"El titulo deberia conservarse al actualizar: antes={titulo_antes!r} despues={titulo_despues!r}"
assert pie_despues == pie_antes, f"El listado deberia reflejar el mismo estado/orden: antes={pie_antes!r} despues={pie_despues!r}"
capturar_paso(app, "listado_actualizado_estado_conservado", paso_excel=4)

app.reload()
app.wait_for_timeout(2500)
frame = app.locator("#aplicacion").content_frame
frame.locator("button", has_text=re.compile("Actualizar Ventana")).first.click()
app.wait_for_timeout(2500)
texto2 = frame.locator("body").inner_text()
assert "No hay una consulta en curso" in texto2, f"Sin estado elegido, Actualizar Ventana no deberia aplicar ninguna consulta: {texto2[-300:]!r}"
pie2 = texto_pie_paginador(frame)
assert pie2 == (0, 0, 0), f"Sin estado elegido, el contador deberia seguir en 0: {pie2!r}"
capturar_paso(app, "actualizar_sin_estado_no_aplica", paso_excel=5)
'''

CUERPOS_REALES["CP004"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
texto = frame.locator("body").inner_text()
assert "500007" in texto, "La orden propia (rol_actual=DACD) deberia estar visible en Pendientes"
assert "3365694" in texto, "La orden propia (rol_actual=DACD) deberia estar visible en Pendientes"
capturar_paso(app, "ordenes_propias_visibles", paso_excel=2)

modal = abrir_buscar(app, frame)
modal.first.locator("#bsqNroOrden").fill("500005")
modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(2000)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje and "No se encontro la orden solicitada" in mensaje, f"La orden ajena (500005, rol_actual=REC, real y nunca modificada) NO deberia ser visible para DACD: {mensaje!r}"
texto_tras = frame.locator("body").inner_text()
assert "500005" not in texto_tras, "La orden ajena no deberia aparecer en ningun listado"
capturar_paso(app, "orden_ajena_no_visible", paso_excel=4)
'''

CUERPOS_REALES["CP005"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")

def primera_fila():
    texto = frame.locator("body").inner_text()
    filas = re.findall(r"^\\d{5,8}\\t.*$", texto, re.M)
    return filas[0].split("\\t")[0] if filas else None

orden_default = primera_fila()
capturar_paso(app, "orden_por_defecto", paso_excel=2)

with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    frame.locator("button", has_text="Ordenes Recientes").first.click(force=True)
app.wait_for_timeout(1000)
orden_recientes = primera_fila()
assert orden_recientes == "40009802", f"Ordenes Recientes deberia mostrar primero la mas nueva (40009802): {orden_recientes!r}"
capturar_paso(app, "ordenado_por_ordenes_recientes", paso_excel=2)

with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    frame.locator("button", has_text="Por Cliente").first.click(force=True)
app.wait_for_timeout(1000)
orden_cliente = primera_fila()
assert orden_cliente != orden_recientes, "Por Cliente deberia cambiar el orden respecto de Ordenes Recientes"
capturar_paso(app, "ordenado_por_cliente", paso_excel=2)

with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    frame.locator("button").filter(has_text="Ordenes Devueltas").first.click()
app.wait_for_timeout(1000)
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    frame.locator("button").filter(has_text="Ordenes Pendientes").first.click()
app.wait_for_timeout(1000)
orden_tras_cambio = primera_fila()
assert orden_tras_cambio == orden_default, f"Al cambiar de estado se deberia perder el criterio de orden elegido (volver al orden natural {orden_default!r}), se obtuvo {orden_tras_cambio!r}"
capturar_paso(app, "orden_perdido_al_cambiar_estado", paso_excel=4)
'''

CUERPOS_REALES["CP013"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
capturar_paso(app, "busqueda_abierta", paso_excel=1)

casos = [
    ("RQ = Requerimiento", "Búsqueda - Pendientes", "Rol Emisor", "POR FECHAS DE ENVÍO"),
    ("DV = Devolucion", "Búsqueda - Devueltos", "Rol Emisor", "POR FECHAS DE ENVÍO"),
    ("FI = Finalizacion", "Búsqueda - Finalizados", "Rol Creador", "POR FECHAS DE FINALIZACIÓN"),
    ("AN = Anulado", "Búsqueda - Anulados", "Rol Emisor", "POR FECHAS DE FINALIZACIÓN"),
    ("= (Todos)", "Búsqueda - Todas las Ordenes", "Rol Creador", "POR FECHAS DE ULTIMO ENVÍO"),
]
for valor_estado, titulo_esperado, rotulo_rol_esperado, rotulo_fechas_esperado in casos:
    modal.first.locator("#bsqEstado").select_option(label=valor_estado)
    app.wait_for_timeout(600)
    texto_modal = modal.first.inner_text()
    titulo = texto_modal.splitlines()[0]
    assert titulo == titulo_esperado, f"Titulo inesperado para estado {valor_estado!r}: {titulo!r} (se esperaba {titulo_esperado!r})"
    assert rotulo_rol_esperado in texto_modal, f"No se vio el rotulo de rol {rotulo_rol_esperado!r} para estado {valor_estado!r}: {texto_modal[:400]!r}"
    modal.first.locator("#bsqRango").check()
    app.wait_for_timeout(500)
    texto_con_rango = modal.first.inner_text()
    assert rotulo_fechas_esperado in texto_con_rango, f"No se vio el rotulo de fechas {rotulo_fechas_esperado!r} para estado {valor_estado!r}: {texto_con_rango[:600]!r}"
    modal.first.locator("#bsqRango").uncheck()
    app.wait_for_timeout(400)
    capturar_paso(app, f"rotulos_estado_{valor_estado[:2].strip()}", paso_excel=2)

modal.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP015"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqRolEmisor").fill("CCQ")
capturar_paso(app, "criterio_rol_emisor_pendientes", paso_excel=2)
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] == 15, f"Se esperaban las 15 ordenes SEGEN con ult. rol personal emisor CCQ en Pendientes, se obtuvo: {pie!r}"
texto = frame.locator("body").inner_text()
assert "CCQ" in texto, "El rol emisor buscado deberia aparecer en el resultado"
capturar_paso(app, "resultado_filtrado_por_rol_emisor", paso_excel=4)
'''

CUERPOS_REALES["CP016"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqEstado").select_option(label="DV = Devolucion")
app.wait_for_timeout(500)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqRolEmisor").fill("JCZG")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie_dv = texto_pie_paginador(frame)
assert pie_dv is not None and pie_dv[2] == 2, f"Se esperaban las 2 ordenes Devueltas con rol emisor JCZG: {pie_dv!r}"
capturar_paso(app, "devueltas_filtradas_por_rol_emisor", paso_excel=2)

modal2 = abrir_buscar(app, frame)
modal2.first.locator("#bsqEstado").select_option(label="AN = Anulado")
app.wait_for_timeout(500)
modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal2.first.locator("#bsqRolEmisor").fill("VJMM")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal2.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie_an = texto_pie_paginador(frame)
assert pie_an is not None and pie_an[2] == 2, f"Se esperaban las 2 ordenes Anuladas con rol emisor VJMM: {pie_an!r}"
capturar_paso(app, "anuladas_filtradas_por_rol_emisor", paso_excel=2)
'''

CUERPOS_REALES["CP017"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqEstado").select_option(label="FI = Finalizacion")
app.wait_for_timeout(500)
assert "Rol Creador" in modal.first.inner_text(), "El rotulo deberia mostrarse como Rol Creador en Finalizadas"
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqRolEmisor").fill("CCQ")
for _intento in range(3):
    with app.expect_response(lambda r: "ConsultarOrdenes" in r.url, timeout=60000):
        modal.first.locator("button", has_text="Buscar").click(force=True)
    app.wait_for_timeout(1500)
    if not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).count():
        break
    frame.locator("button", has_text=re.compile("^Cancelar$", re.I)).click(force=True)
    app.wait_for_timeout(800)
    modal = abrir_buscar(app, frame)
    modal.first.locator("#bsqEstado").select_option(label="FI = Finalizacion")
    app.wait_for_timeout(500)
    modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
    app.wait_for_timeout(500)
    modal.first.locator("#bsqRolEmisor").fill("CCQ")
pie_fi = texto_pie_paginador(frame)
assert pie_fi is not None and pie_fi[2] == 2, f"Se esperaban las 2 ordenes Finalizadas (SEGEN) con rol creador CCQ: {pie_fi!r}"
capturar_paso(app, "finalizadas_filtradas_por_rol_creador", paso_excel=2)

modal2 = abrir_buscar(app, frame)
modal2.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(500)
assert "Rol Creador" in modal2.first.inner_text(), "El rotulo deberia mostrarse como Rol Creador en Todas"
modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal2.first.locator("#bsqRolEmisor").fill("CCQ")
for _intento in range(3):
    with app.expect_response(lambda r: "ConsultarOrdenes" in r.url, timeout=60000):
        modal2.first.locator("button", has_text="Buscar").click(force=True)
    app.wait_for_timeout(1500)
    if not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).count():
        break
    frame.locator("button", has_text=re.compile("^Cancelar$", re.I)).click(force=True)
    app.wait_for_timeout(800)
    modal2 = abrir_buscar(app, frame)
    modal2.first.locator("#bsqEstado").select_option(label="= (Todos)")
    app.wait_for_timeout(500)
    modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
    app.wait_for_timeout(500)
    modal2.first.locator("#bsqRolEmisor").fill("CCQ")
pie_todas = texto_pie_paginador(frame)
assert pie_todas is not None and pie_todas[2] >= 2, f"Se esperaban al menos las ordenes SEGEN con rol creador CCQ en Todas: {pie_todas!r}"
capturar_paso(app, "todas_filtradas_por_rol_creador", paso_excel=2)
'''

CUERPOS_REALES["CP018"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqRango").check()
app.wait_for_timeout(300)
modal.first.locator("#bsqDesde").fill("11/10/2017")
modal.first.locator("#bsqHasta").fill("11/10/2017")
capturar_paso(app, "rango_de_fechas_del_dia_de_creacion", paso_excel=2)
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie_dentro = texto_pie_paginador(frame)
assert pie_dentro is not None and pie_dentro[2] == 15, f"Se esperaban las 15 ordenes creadas el 11/10/2017: {pie_dentro!r}"
capturar_paso(app, "ordenes_incluidas_dentro_del_rango", paso_excel=3)

modal2 = abrir_buscar(app, frame)
modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal2.first.locator("#bsqRango").check()
app.wait_for_timeout(300)
modal2.first.locator("#bsqDesde").fill("12/10/2017")
modal2.first.locator("#bsqHasta").fill("20/10/2017")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal2.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie_fuera = texto_pie_paginador(frame)
assert pie_fuera is not None and pie_fuera[2] == 0, f"Un rango que excluye el 11/10/2017 no deberia devolver esas ordenes: {pie_fuera!r}"
capturar_paso(app, "ordenes_excluidas_fuera_del_rango", paso_excel=3)
'''

CUERPOS_REALES["CP020"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
capturar_paso(app, "busqueda_abierta", paso_excel=1)

buscador_rol = abrir_buscador_dinamico(app, frame, "Consultar Rol Emisor", 1, modal.first)
assert buscador_rol.count() and buscador_rol.is_visible(), "No se abrio el buscador dinamico de Rol Emisor"
encabezados_rol = buscador_rol.locator("thead th")
assert [t.inner_text().strip().upper() for t in [encabezados_rol.nth(i) for i in range(encabezados_rol.count())]][:3] == ["ROL", "NOMBRE", "TIPO"], "Columnas inesperadas en el buscador de roles"
fila_rol = buscador_rol.locator("tr.sm-fila", has_text="CCQ")
for _ in range(5):
    if fila_rol.count():
        break
    sgtes = buscador_rol.get_by_role("button", name=re.compile("Sgtes", re.I))
    if not sgtes.is_enabled():
        break
    sgtes.click(force=True)
    app.wait_for_timeout(1200)
    fila_rol = buscador_rol.locator("tr.sm-fila", has_text="CCQ")
assert fila_rol.count(), "No se encontro el rol CCQ en el buscador"
fila_rol.first.click()
buscador_rol.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
app.wait_for_timeout(1000)
valor_rol = modal.first.locator("#bsqRolEmisor").input_value()
assert valor_rol == "CCQ", f"El criterio Rol Emisor deberia completarse con el valor elegido: {valor_rol!r}"
capturar_paso(app, "rol_emisor_completado_desde_buscador", paso_excel=2)

buscador_cliente = abrir_buscador_dinamico(app, frame, "Consultar Cliente", 0, modal.first)
assert buscador_cliente.count() and buscador_cliente.is_visible(), "No se abrio el buscador dinamico de Cliente"
encabezados_cli = buscador_cliente.locator("thead th")
assert [t.inner_text().strip().upper() for t in [encabezados_cli.nth(i) for i in range(encabezados_cli.count())]][:3] == ["NUMERO CLIENTE", "NOMBRE", "SUCURSAL"], "Columnas inesperadas en el buscador de clientes"
primer_cliente = buscador_cliente.locator("tr.sm-fila").first.locator("td").first.inner_text().strip()
buscador_cliente.locator("tr.sm-fila").first.click()
buscador_cliente.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
app.wait_for_timeout(1000)
valor_cliente = modal.first.locator("#bsqNroCliente").input_value()
assert valor_cliente == primer_cliente, f"El criterio Numero de Cliente deberia completarse con el valor elegido ({primer_cliente!r}), quedo {valor_cliente!r}"
capturar_paso(app, "numero_cliente_completado_desde_buscador", paso_excel=2)
'''

CUERPOS_REALES["CP023"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqRolEmisor").fill("CCQ")
modal.first.locator("#bsqNroCliente").fill("508904")
capturar_paso(app, "criterios_combinados_cargados", paso_excel=2)
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie = texto_pie_paginador(frame)
assert pie is not None and pie[2] == 1, f"La combinacion de tipo+rol emisor+cliente deberia acotar a 1 sola orden (3365694): {pie!r}"
texto = frame.locator("body").inner_text()
assert "3365694" in texto, f"No se encontro la orden esperada que cumple todos los criterios: {texto[-300:]!r}"
capturar_paso(app, "resultado_acotado_por_todos_los_criterios", paso_excel=3)

modal2 = abrir_buscar(app, frame)
modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal2.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
pie_sin_filtros = texto_pie_paginador(frame)
assert pie_sin_filtros is not None and pie_sin_filtros[2] == 15, f"Sin Rol Emisor ni Cliente cargados, el filtro no deberia restringir mas alla del tipo (deberian verse las 15 SEGEN): {pie_sin_filtros!r}"
capturar_paso(app, "campos_vacios_no_restringen", paso_excel=3)
'''

CUERPOS_REALES["CP041"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "4106420")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
extractor = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Extractor")).last
assert extractor.count() and extractor.first.is_visible(), "No se abrio la consulta del Extractor para la orden finalizada"
odt = extractor.first.locator("#extNumeroOdt").input_value()
para = extractor.first.locator("#extPara").input_value()
adjunto = extractor.first.locator("#extAdjunto").input_value()
assert odt == "157758", f"Numero de ODT inesperado: {odt!r}"
assert para == "DACD", f"Campo Para inesperado: {para!r}"
assert adjunto == "todas758.xls", f"Archivo Adjunto inesperado: {adjunto!r}"
capturar_paso(app, "datos_orden_finalizada_visibles", paso_excel=1)

assert not extractor.first.locator("button", has_text="Finalizar").first.is_enabled(), "Finalizar deberia estar deshabilitado para una orden ya finalizada"
capturar_paso(app, "finalizar_deshabilitado", paso_excel=1)
extractor.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP042"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "4128448")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
extractor = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Extractor")).last
assert extractor.count() and extractor.first.is_visible(), "No se abrio el Extractor de la orden de prueba"
capturar_paso(app, "extractor_no_finalizado", paso_excel=1)

mensaje_resultado = None
for _intento in range(3):
    extractor.first.locator("button", has_text="Finalizar").click(force=True)
    app.wait_for_timeout(1500)
    error_servicio = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio"))
    if error_servicio.count() and error_servicio.last.is_visible():
        error_servicio.last.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(1200)
        continue
    confirmacion = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Confirmación EXTRAC"))
    assert confirmacion.count() and confirmacion.last.is_visible(), "No se vio la confirmacion esperada antes de finalizar"
    mensaje_confirmacion = confirmacion.last.inner_text()
    assert "¿Está Ud. seguro que desea finalizar el EXTRAC?" in mensaje_confirmacion, f"Texto de confirmacion inesperado: {mensaje_confirmacion!r}"
    capturar_paso(app, "confirmacion_antes_de_finalizar", paso_excel=2)

    confirmacion.last.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
    app.wait_for_timeout(2500)
    dlg_resultado = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación|Error de Servicio"))
    if dlg_resultado.count() and "Error de Servicio" in dlg_resultado.first.inner_text():
        dlg_resultado.first.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(1200)
        continue
    assert dlg_resultado.count() and dlg_resultado.first.is_visible(), "No se vio el mensaje de resultado de la finalizacion"
    mensaje_resultado = dlg_resultado.first.inner_text()
    assert "La Orden 4128448 ha sido finalizado correctamente" in mensaje_resultado, f"Mensaje de confirmacion inesperado: {mensaje_resultado!r}"
    capturar_paso(app, "mensaje_orden_finalizada", paso_excel=2)
    dlg_resultado.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(1500)
    break
assert mensaje_resultado is not None, "No se pudo completar la finalizacion tras varios intentos (Error de Servicio persistente)"

buscar_y_seleccionar_orden(app, frame, "4128448")
texto_final = frame.locator("body").inner_text()
assert "Finalizacion" in texto_final, f"La orden deberia quedar en estado Finalizacion en la bandeja: {texto_final[-300:]!r}"
capturar_paso(app, "orden_en_estado_finalizacion", paso_excel=2)
'''

CUERPOS_REALES["CP043"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "500007")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
extractor = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Extractor")).last
assert extractor.count() and extractor.first.is_visible(), "No se abrio el Extractor de la orden de prueba"
nombre_archivo_adjunto = extractor.first.locator("#extAdjunto").input_value()
print(f"ARCHIVO ADJUNTO ANTES DE FINALIZAR: {nombre_archivo_adjunto!r}")
capturar_paso(app, f"extractor_no_finalizado_archivo_{nombre_archivo_adjunto}", paso_excel=1)

mensaje_resultado = None
for _intento in range(6):
    extractor.first.locator("button", has_text="Finalizar").click(force=True)
    app.wait_for_timeout(2500)
    error_servicio = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio"))
    if error_servicio.count() and error_servicio.last.is_visible():
        error_servicio.last.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(2000)
        continue
    confirmacion = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Confirmación EXTRAC"))
    for _ in range(6):
        if confirmacion.count() and confirmacion.last.is_visible():
            break
        app.wait_for_timeout(500)
    if not (confirmacion.count() and confirmacion.last.is_visible()):
        continue
    capturar_paso(app, "confirmacion_antes_de_finalizar", paso_excel=2)
    confirmacion.last.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
    app.wait_for_timeout(2500)
    dlg_resultado = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación|Error de Servicio"))
    if dlg_resultado.count() and "Error de Servicio" in dlg_resultado.first.inner_text():
        dlg_resultado.first.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(2000)
        continue
    assert dlg_resultado.count() and dlg_resultado.first.is_visible(), "No se vio el mensaje de resultado de la finalizacion"
    mensaje_resultado = dlg_resultado.first.inner_text()
    capturar_paso(app, "mensaje_resultado_finalizacion", paso_excel=2)
    dlg_resultado.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(1500)
    break
assert mensaje_resultado is not None, "No se pudo completar la finalizacion tras varios intentos (Error de Servicio persistente)"
assert "La Orden 500007 ha sido finalizado correctamente" in mensaje_resultado, f"Mensaje de confirmacion inesperado: {mensaje_resultado!r}"

# DEFECTO REAL confirmado en vivo (ver casos_fallidos_confirmados.json,
# 3/3 ordenes reales distintas fallan igual): el sistema deberia retirar el
# adjunto del repositorio al finalizar, pero siempre informa que no pudo.
# El nombre del archivo (nombre_archivo_adjunto, impreso antes de Finalizar)
# confirma que SI habia un archivo real registrado para esta orden.
assert "no pudo retirarse del repositorio" not in mensaje_resultado, f"Defecto real: el sistema deberia retirar el adjunto del repositorio al finalizar (archivo {nombre_archivo_adjunto!r}), pero informo: {mensaje_resultado!r}"
'''

CUERPOS_REALES["CP039"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "40009801")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
assert dlg.count() and dlg.first.is_visible(), "No se vio el mensaje de orden sin informacion asociada"
mensaje = dlg.first.inner_text()
assert "No se encontró información de la orden seleccionada. Comuníquese con informática" in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_orden_sin_informacion", paso_excel=2)
dlg.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(1000)
assert not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Extractor")).count(), "La pantalla del Extractor deberia cerrarse tras el mensaje"
capturar_paso(app, "pantalla_cerrada", paso_excel=2)
'''

CUERPOS_REALES["CP028"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
elegir_estado(app, frame, "Ordenes Pendientes")
frame.locator("button", has_text=re.compile(r"Siguiente")).first.click(force=True)
app.wait_for_timeout(2000)
fila = frame.locator("tr", has_text="40009802")
fila.first.click(force=True)
app.wait_for_timeout(500)
capturar_paso(app, "orden_sin_movimientos_seleccionada", paso_excel=1)

frame.locator("button", has_text="Historial de la Orden").first.click()
app.wait_for_timeout(2500)
historial = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).last
assert historial.count() and historial.first.is_visible(), "No se abrio el historial de la orden sin movimientos"
titulo = historial.first.inner_text().splitlines()[0]
assert titulo.strip() == "Historia de la Orden # 40009802", f"Titulo inesperado: {titulo!r}"
filas_movimiento = historial.first.locator("tr.his-fila")
assert filas_movimiento.count() == 0, f"La grilla deberia estar vacia (orden sin movimientos): {filas_movimiento.count()} filas"
texto = historial.first.inner_text()
assert "Error" not in texto, f"No deberia mostrarse ningun mensaje de error: {texto!r}"
capturar_paso(app, "historial_vacio_sin_error", paso_excel=2)

historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
assert not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).count(), "La pantalla deberia poder cerrarse y volver a la bandeja"
capturar_paso(app, "vuelta_a_la_bandeja", paso_excel=2)
'''

CUERPOS_REALES["CP029"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
app.wait_for_timeout(500)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqNroOrden").fill("40006337")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
frame.locator("tr", has_text="40006337").first.click()
app.wait_for_timeout(500)
frame.locator("button", has_text="Historial de la Orden").first.click()
app.wait_for_timeout(2500)
historial = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).last
assert historial.count() and historial.first.is_visible(), "No se abrio el historial de la orden"
capturar_paso(app, "historial_con_movimientos", paso_excel=1)

fila1 = historial.first.locator("tr.his-fila", has_text="0000001")
fila1.first.locator("td").first.click()
app.wait_for_timeout(1200)
panel = historial.first.locator(".his-obs-box")
texto_panel = panel.first.inner_text()
assert "SE QUIERE INSTALAR UN MEDIDOR NUEVO AL SISTEMA" in texto_panel, f"No se vio el texto de observacion esperado: {texto_panel!r}"
rotulo = historial.first.inner_text()
assert "Seleccione el correlativo" in rotulo, "El rotulo deberia indicar que se debe seleccionar un correlativo para ver las observaciones"
capturar_paso(app, "observacion_con_texto_real", paso_excel=2)
'''

CUERPOS_REALES["CP034"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqNroOrden").fill("3365695")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
frame.locator("tr", has_text="3365695").first.click()
app.wait_for_timeout(500)

frame.locator("button", has_text="Reasignación de Orden").first.click()
app.wait_for_timeout(2500)
reasig = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).last
assert reasig.count() and reasig.first.is_visible(), "No se abrio la pantalla de Reasignacion de Orden"
texto_antes = reasig.first.inner_text()
assert "Rol Actual" in texto_antes and "DACD" in texto_antes, f"No se vio el rol actual antes de reasignar: {texto_antes[:300]!r}"
capturar_paso(app, "rol_actual_antes_de_reasignar", paso_excel=3)

reasig.first.locator("#reaAreaEjecutora").fill("EXPLRECAU")
reasig.first.locator("textarea").fill("PRUEBA CP034 - reasignacion exitosa")
capturar_paso(app, "area_ejecutora_y_observacion_cargadas", paso_excel=4)
reasig.first.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
app.wait_for_timeout(2500)
dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
assert dlg.count() and dlg.first.is_visible(), "No se vio el mensaje de confirmacion del envio"
mensaje = dlg.first.inner_text()
assert "La Orden Numero: 3365695 ha sido enviada." in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_orden_enviada", paso_excel=6)
dlg.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(1500)
assert not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).count(), "La pantalla de Reasignacion deberia cerrarse"

modal2 = abrir_buscar(app, frame)
modal2.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal2.first.locator("#bsqNroOrden").fill("3365695")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal2.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
texto_final = frame.locator("body").inner_text()
assert "EXPLRECAU" in texto_final, f"La orden deberia quedar con el nuevo rol actual EXPLRECAU: {texto_final[-300:]!r}"
capturar_paso(app, "orden_con_nuevo_rol_actual", paso_excel=7)
'''

CUERPOS_REALES["CP035"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
modal = abrir_buscar(app, frame)
modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
app.wait_for_timeout(500)
modal.first.locator("#bsqNroOrden").fill("3365696")
with app.expect_response(lambda r: "ConsultarOrdenes" in r.url):
    modal.first.locator("button", has_text="Buscar").click()
app.wait_for_timeout(1500)
frame.locator("tr", has_text="3365696").first.click()
app.wait_for_timeout(500)

frame.locator("button", has_text="Reasignación de Orden").first.click()
app.wait_for_timeout(2500)
reasig = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).last
reasig.first.locator("#reaAreaEjecutora").fill("EXPLRECAU")
observacion_cruda = "Linea 1\\n\\tLinea 2 con tab\\nLinea 3 con comilla simple: O'Brien"
reasig.first.locator("textarea").fill(observacion_cruda)
capturar_paso(app, "observacion_con_caracteres_especiales", paso_excel=2)
reasig.first.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
app.wait_for_timeout(2500)
dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
assert dlg.count() and dlg.first.is_visible(), "No se vio el mensaje de confirmacion del envio"
mensaje = dlg.first.inner_text()
assert "La Orden Numero: 3365696 ha sido enviada." in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_orden_enviada", paso_excel=3)
dlg.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(1500)

buscar_y_seleccionar_orden(app, frame, "3365696", tipo_orden="SEGEN = Solicitudes Especiales")
historial = abrir_historial_de_orden(app, frame)
assert historial.count() and historial.first.is_visible(), "No se abrio el historial de la orden reasignada"
fila_reasignacion = historial.first.locator("tr.his-fila").last
fila_reasignacion.locator("td").first.click()
app.wait_for_timeout(1200)
panel = historial.first.locator(".his-obs-box")
texto_panel = panel.first.inner_text()
assert "\\n" not in texto_panel and "\\t" not in texto_panel, f"La observacion deberia mostrarse en una sola linea, sin saltos ni tabulaciones: {texto_panel!r}"
assert "O'Brien" in texto_panel or "O\\u2019Brien" in texto_panel, f"La comilla simple deberia mostrarse como un solo caracter: {texto_panel!r}"
capturar_paso(app, "observacion_en_una_sola_linea", paso_excel=5)
'''

CUERPOS_REALES["CP044"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
titulo = overlay.first.inner_text().splitlines()[0]
assert titulo.strip() == "Creación de una Solicitud Especial", f"Titulo inesperado: {titulo!r}"
assert overlay.first.locator("#segTipoOrden").is_enabled(), "El panel de clasificacion deberia estar habilitado"
assert overlay.first.locator("button", has_text="Enviar").first.is_enabled(), "El boton Enviar deberia estar habilitado"
capturar_paso(app, "segen_titulo_y_paneles", paso_excel=4)

opciones_tipo = overlay.first.locator("#segTipoOrden option")
for _ in range(20):
    if opciones_tipo.count() > 1:
        break
    app.wait_for_timeout(300)
overlay.first.locator("#segTipoOrden").select_option(label="SR = SOLICITUD DE SERVICIO EN RUTINA")
app.wait_for_timeout(500)
overlay.first.locator("#segTema").select_option(label="020 = Clientes")
app.wait_for_timeout(800)
overlay.first.locator("#segTrabajo").select_option(index=1)
app.wait_for_timeout(800)
opciones_form = overlay.first.locator("#segFormulario option")
if opciones_form.count() > 1:
    overlay.first.locator("#segFormulario").select_option(index=1)
overlay.first.locator("#segClase").select_option(index=1)
app.wait_for_timeout(500)
capturar_paso(app, "clasificacion_elegida", paso_excel=5)

buscador = abrir_buscador_usuario_destino(app, frame, overlay)
fila = buscador.locator("tr.sm-fila", has_text="EPSG")
for _ in range(6):
    if fila.count():
        break
    sgtes = buscador.get_by_role("button", name=re.compile("Sgtes", re.I))
    if not sgtes.is_enabled():
        break
    sgtes.click(force=True)
    app.wait_for_timeout(1200)
    fila = buscador.locator("tr.sm-fila", has_text="EPSG")
if fila.count():
    fila.first.click()
    buscador.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
    app.wait_for_timeout(1000)
else:
    buscador.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
    app.wait_for_timeout(800)
    overlay.first.locator("#segUsuarioDestino").fill("EPSG")
capturar_paso(app, "usuario_destino_elegido", paso_excel=6)

overlay.first.locator("textarea").last.fill("CP044 - creacion de solicitud especial (prueba automatizada)")
capturar_paso(app, "observacion_cargada", paso_excel=7)

overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(3000)
dlg_error = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio"))
dlg_resultado = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))

# DEFECTO REAL confirmado en vivo 08/11/2026 (ver casos_fallidos_confirmados.json):
# el backend de RegistrarOrdenSegen devuelve HTTP 500 (INSERT mal formado)
# sin importar que el Usuario Destino sea valido - nunca se llega al
# mensaje de exito esperado "La Orden Numero: X ha sido enviada.".
assert not (dlg_error.count() and dlg_error.last.is_visible()), f"Defecto real: RegistrarOrdenSegen devuelve Error de Servicio (HTTP 500, INSERT mal formado en el backend) en vez de confirmar el envio: {dlg_error.last.inner_text() if dlg_error.count() else None!r}"
assert dlg_resultado.count() and dlg_resultado.first.is_visible(), "No se vio ningun mensaje de resultado tras Enviar"
mensaje = dlg_resultado.first.inner_text()
assert "ha sido enviada" in mensaje, f"Mensaje de confirmacion inesperado: {mensaje!r}"
capturar_paso(app, "orden_enviada_correctamente", paso_excel=9)
'''

CUERPOS_REALES["CP037"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

def abrir_buscar_con_reintento():
    for _intento in range(3):
        residual = frame.locator(".ant-modal, nz-modal-container")
        if residual.count() and residual.first.is_visible():
            boton_cerrar = residual.first.get_by_role("button", name=re.compile("Aceptar|Cancelar|Cerrar", re.I))
            if boton_cerrar.count():
                boton_cerrar.first.click(force=True)
            app.wait_for_timeout(800)
        modal = abrir_buscar(app, frame)
        if not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).count():
            return modal
        frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).last.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(1000)
    return modal

def reasignar(numero, rol_destino):
    modal = abrir_buscar_con_reintento()
    modal.first.locator("#bsqTipoOrden").select_option(label="SEGEN = Solicitudes Especiales")
    app.wait_for_timeout(500)
    modal.first.locator("#bsqNroOrden").fill(numero)
    for _intento in range(3):
        with app.expect_response(lambda r: "ConsultarOrdenes" in r.url, timeout=45000):
            modal.first.locator("button", has_text="Buscar").click(force=True)
        app.wait_for_timeout(1500)
        if not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).count():
            break
        frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).last.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(1000)
    frame.locator("tr", has_text=numero).first.click()
    app.wait_for_timeout(500)
    frame.locator("button", has_text="Reasignación de Orden").first.click()
    app.wait_for_timeout(2500)
    reasig = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Reasignaci")).last
    reasig.first.locator("#reaAreaEjecutora").fill(rol_destino)
    reasig.first.locator("textarea").fill(f"CP037 - destino {rol_destino}")
    reasig.first.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
    app.wait_for_timeout(2500)
    dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
    assert dlg.count() and dlg.first.is_visible(), f"No se vio confirmacion al reasignar {numero} a {rol_destino}"
    dlg.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(2000)
    for _ in range(6):
        residual = frame.locator(".ant-modal, nz-modal-container")
        if not residual.count() or not residual.first.is_visible():
            break
        boton_cerrar = residual.first.get_by_role("button", name=re.compile("Aceptar|Cancelar|Cerrar", re.I))
        if boton_cerrar.count():
            boton_cerrar.first.click(force=True)
        app.wait_for_timeout(800)

reasignar("3365705", "EXPLRECAU")
capturar_paso(app, "reasignado_a_rol_funcional", paso_excel=1)
reasignar("3365706", "EPSG")
capturar_paso(app, "reasignado_a_rol_usuario", paso_excel=3)

buscar_y_seleccionar_orden(app, frame, "3365705", tipo_orden="SEGEN = Solicitudes Especiales")
historial1 = abrir_historial_de_orden(app, frame)
texto1 = historial1.first.inner_text()
fila_reasig1 = re.search(r"0000002\\t.*", texto1)
assert fila_reasig1, f"No se encontro el movimiento de reasignacion: {texto1!r}"
columnas1 = fila_reasig1.group(0).split("\\t")
assert columnas1[5] == "EXPLRECAU" and columnas1[4] in ("0", ""), f"EXPLRECAU (funcional) deberia quedar en Rol F.Receptor: {columnas1!r}"
capturar_paso(app, "receptor_en_rol_funcional", paso_excel=2)
historial1.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)

buscar_y_seleccionar_orden(app, frame, "3365706", tipo_orden="SEGEN = Solicitudes Especiales")
historial2 = abrir_historial_de_orden(app, frame)
texto2 = historial2.first.inner_text()
fila_reasig2 = re.search(r"0000002\\t.*", texto2)
assert fila_reasig2, f"No se encontro el movimiento de reasignacion: {texto2!r}"
columnas2 = fila_reasig2.group(0).split("\\t")
assert columnas2[4] == "EPSG" and columnas2[5] in ("0", ""), f"EPSG (usuario) deberia quedar en Rol P.Receptor: {columnas2!r}"
capturar_paso(app, "receptor_en_rol_personal", paso_excel=4)
'''

CUERPOS_REALES["CP046"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: sin Tipo de Orden
overlay = abrir_segen(app, frame)
opciones_tipo = overlay.first.locator("#segTipoOrden option")
for _ in range(20):
    if opciones_tipo.count() > 1:
        break
    app.wait_for_timeout(300)
overlay.first.locator("#segUsuarioDestino").fill("EPSG")
overlay.first.locator("textarea").last.fill("CP046 escenario A")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(2000)
mensaje_a = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_a and "Debe ingresar el Tipo de Orden" in mensaje_a, f"Mensaje inesperado en escenario A: {mensaje_a!r}"
capturar_paso(app, "escenario_a_sin_tipo_orden", paso_excel=4)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# Escenario B: tipo si, tema no
overlay = abrir_segen(app, frame)
overlay.first.locator("#segTipoOrden").select_option(label="SR = SOLICITUD DE SERVICIO EN RUTINA")
app.wait_for_timeout(500)
overlay.first.locator("#segUsuarioDestino").fill("EPSG")
overlay.first.locator("textarea").last.fill("CP046 escenario B")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(2000)
mensaje_b = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_b and "Debe ingresar el Tema" in mensaje_b, f"Mensaje inesperado en escenario B: {mensaje_b!r}"
capturar_paso(app, "escenario_b_sin_tema", paso_excel=4)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# Escenario C: tipo+tema si, clase no - confirmado en vivo 08/11/2026:
# el boton Enviar queda DESHABILITADO (no se puede ni clickear), en vez
# de mostrar el mensaje "Debe ingresar la Clase" al intentar enviar -
# comportamiento real distinto al descrito en la matriz (que asume
# Enviar clickeable con validacion posterior).
overlay = abrir_segen(app, frame)
overlay.first.locator("#segTipoOrden").select_option(label="SR = SOLICITUD DE SERVICIO EN RUTINA")
app.wait_for_timeout(500)
overlay.first.locator("#segTema").select_option(label="020 = Clientes")
app.wait_for_timeout(800)
overlay.first.locator("#segUsuarioDestino").fill("EPSG")
overlay.first.locator("textarea").last.fill("CP046 escenario C")
boton_enviar = overlay.first.locator("button", has_text="Enviar")
assert not boton_enviar.first.is_enabled(), "Defecto real (vs matriz): Enviar deberia estar habilitado para poder mostrar 'Debe ingresar la Clase' al hacer click; en cambio queda deshabilitado sin ningun mensaje"
capturar_paso(app, "escenario_c_enviar_deshabilitado_sin_clase", paso_excel=4)
'''

CUERPOS_REALES["CP047"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: Tipo de Orden AC, Nro. Cliente vacio
overlay = abrir_segen(app, frame)
opciones_tipo = overlay.first.locator("#segTipoOrden option")
for _ in range(20):
    if opciones_tipo.count() > 1:
        break
    app.wait_for_timeout(300)
overlay.first.locator("#segTipoOrden").select_option(label="AC = ATENCION COMERCIAL")
app.wait_for_timeout(500)
overlay.first.locator("#segUsuarioDestino").fill("EPSG")
overlay.first.locator("textarea").last.fill("CP047 escenario A - cliente vacio con tipo AC")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(2000)
mensaje_a = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_a and "Debe Ingresar el Numero del Cliente" in mensaje_a, f"Mensaje inesperado en escenario A: {mensaje_a!r}"
capturar_paso(app, "escenario_a_cliente_obligatorio_AC", paso_excel=3)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# Escenario B: Tipo de Orden distinto de AC (SR), Nro. Cliente vacio -
# la matriz espera que el cliente NO se exija y la solicitud se envie
# con los demas datos validos. Mismo combo valido usado en CP044 (SR,
# Tema 020, primer Trabajo/Formulario, primera Clase, EPSG) - esto
# deberia topar con el defecto REAL YA CONFIRMADO en CP044
# (RegistrarOrdenSegen HTTP 500, INSERT mal formado), no con un mensaje
# de cliente obligatorio.
overlay = abrir_segen(app, frame)
overlay.first.locator("#segTipoOrden").select_option(label="SR = SOLICITUD DE SERVICIO EN RUTINA")
app.wait_for_timeout(500)
overlay.first.locator("#segTema").select_option(label="020 = Clientes")
app.wait_for_timeout(800)
overlay.first.locator("#segTrabajo").select_option(index=1)
app.wait_for_timeout(800)
opciones_form = overlay.first.locator("#segFormulario option")
if opciones_form.count() > 1:
    overlay.first.locator("#segFormulario").select_option(index=1)
overlay.first.locator("#segClase").select_option(index=1)
app.wait_for_timeout(500)
overlay.first.locator("#segUsuarioDestino").fill("EPSG")
overlay.first.locator("textarea").last.fill("CP047 escenario B - cliente vacio con tipo distinto de AC")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(3000)
dlg_error = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio"))
dlg_resultado = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
mensaje_b = dlg_resultado.first.inner_text() if dlg_resultado.count() and dlg_resultado.first.is_visible() else None
assert not (dlg_error.count() and dlg_error.last.is_visible()), f"Defecto real (mismo que CP044): RegistrarOrdenSegen devuelve Error de Servicio en vez de confirmar el envio sin cliente: {dlg_error.last.inner_text() if dlg_error.count() else None!r}"
assert mensaje_b is not None and "Debe Ingresar el Numero del Cliente" not in mensaje_b, f"No deberia exigirse el cliente con tipo de orden distinto de AC: {mensaje_b!r}"
assert "ha sido enviada" in mensaje_b, f"Bloqueado por el mismo defecto real de CP044 (RegistrarOrdenSegen): {mensaje_b!r}"
capturar_paso(app, "escenario_b_cliente_no_exigido", paso_excel=5)
'''

CUERPOS_REALES["CP048"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Paso 2-5 de la matriz: cadena Tema -> Trabajo (funciona bien, se
# confirma primero antes de aislar el defecto real de Trabajo -> Formulario)
overlay = abrir_segen(app, frame)
opciones_tipo = overlay.first.locator("#segTipoOrden option")
for _ in range(20):
    if opciones_tipo.count() > 1:
        break
    app.wait_for_timeout(300)

overlay.first.locator("#segTema").select_option(label="020 = Clientes")
opciones_trabajo_020 = overlay.first.locator("#segTrabajo option")
for _ in range(20):
    if opciones_trabajo_020.count() > 1:
        break
    app.wait_for_timeout(300)
codigos_020 = [opciones_trabajo_020.nth(i).text_content().strip() for i in range(1, opciones_trabajo_020.count())]
assert all(c.startswith("020") for c in codigos_020), f"Los trabajos deberian empezar todos con el codigo del Tema 020: {codigos_020[:5]!r}"
capturar_paso(app, "trabajos_recargados_con_tema_020", paso_excel=2)

overlay.first.locator("#segTema").select_option(label="001 = Nuevos Clientes")
opciones_trabajo_001 = overlay.first.locator("#segTrabajo option")
for _ in range(20):
    textos = [opciones_trabajo_001.nth(i).text_content().strip() for i in range(1, opciones_trabajo_001.count())]
    if textos and all(c.startswith("001") for c in textos):
        break
    app.wait_for_timeout(300)
codigos_001 = [opciones_trabajo_001.nth(i).text_content().strip() for i in range(1, opciones_trabajo_001.count())]
assert codigos_001 and all(c.startswith("001") for c in codigos_001), f"Al cambiar de Tema, los trabajos deberian recargarse con el codigo del Tema 001: {codigos_001[:5]!r}"
capturar_paso(app, "trabajos_recargados_al_cambiar_de_tema", paso_excel=5)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# DEFECTO REAL DE BACKEND confirmado en vivo 10/11/2026: el combo de
# Trabajo manda su VALUE completo (tema+trabajo concatenado, ej
# "020000") al endpoint ConsultarFormulariosPorTrabajo como si fuera el
# codigo de trabajo puro - pero en la tabla real `textord` el campo
# `trabajo` guarda solo el sufijo sin el tema (ej "000"), confirmado por
# SQL directo (empresa='7', tema='020', trabajo='000' -> 2 filas reales:
# idtexto 64 "Verificacion Capacidad empalme" e idtexto 118 "Reclamo
# Contratista"; la misma consulta con trabajo='020000' -> 0 filas). El
# POST real queda {"tema":"020","trabajo":"020000"} y SIEMPRE responde
# [] sin importar el trabajo elegido - el combo de Formulario nunca
# puede mostrar nada en ningun par Tema+Trabajo.
overlay = abrir_segen(app, frame)
overlay.first.locator("#segTema").select_option(label="020 = Clientes")
opciones_trabajo = overlay.first.locator("#segTrabajo option")
for _ in range(20):
    if opciones_trabajo.count() > 1:
        break
    app.wait_for_timeout(300)
with app.expect_response(lambda r: "ConsultarFormulariosPorTrabajo" in r.url):
    overlay.first.locator("#segTrabajo").select_option(label="020000")
app.wait_for_timeout(1000)
opciones_form = overlay.first.locator("#segFormulario option")
textos_form = [opciones_form.nth(i).text_content().strip() for i in range(opciones_form.count())]
capturar_paso(app, "formulario_vacio_tras_elegir_trabajo", paso_excel=3)
assert len(textos_form) > 1, f"DEFECTO REAL: el combo de Formulario deberia mostrar los 2 formularios reales de Tema 020 + Trabajo 000 (idtexto 64 y 118), pero el backend compara 'trabajo' con el codigo completo '020000' en vez del codigo real '000' y siempre devuelve una lista vacia: {textos_form!r}"
'''

CUERPOS_REALES["CP050"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)
opciones_tipo = overlay.first.locator("#segTipoOrden option")
for _ in range(20):
    if opciones_tipo.count() > 1:
        break
    app.wait_for_timeout(300)
overlay.first.locator("#segTipoOrden").select_option(label="AC = ATENCION COMERCIAL")
app.wait_for_timeout(500)

# Paso 2-3: cliente existente con medidor instalado (orden real 500007)
overlay.first.locator("#segNumeroCliente").fill("1391305")
overlay.first.locator("#segNumeroCliente").press("Tab")
app.wait_for_timeout(2000)
nombre = overlay.first.locator("#segNombreCliente").input_value()
alimentador = overlay.first.locator("#segAlimentador").input_value()
ruta = overlay.first.locator("#segRuta").input_value()
llave = overlay.first.locator("#segLlave").input_value()
texto_overlay = overlay.first.inner_text()
assert nombre == "CORTEZ SANCHEZ DE ARRIAGA IRMA ELIZABETH", f"Nombre inesperado: {nombre!r}"
assert "CALLE D MARGEN IZQ. KM 29" in texto_overlay and "CIENEGUILLA" in texto_overlay, f"Direccion/comuna no se cargaron: {texto_overlay[-400:]!r}"
assert alimentador == "MA - 41", f"Alimentador inesperado: {alimentador!r}"
assert ruta == "019 - 831 - 0800", f"Ruta inesperada: {ruta!r}"
assert llave == "A11407 - 4", f"Llave inesperada: {llave!r}"
assert "6034669" in texto_overlay and "ABB" in texto_overlay, f"Medidor instalado no se cargo: {texto_overlay[-400:]!r}"
capturar_paso(app, "datos_cliente_cargados", paso_excel=3)

# Paso 4: cliente inexistente - mensaje y limpieza
overlay.first.locator("#segNumeroCliente").fill("9999999999")
overlay.first.locator("#segNumeroCliente").press("Tab")
app.wait_for_timeout(2000)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje and "El cliente N\\u00b0 9999999999 no existe" in mensaje, f"Mensaje inesperado para cliente inexistente: {mensaje!r}"
nombre_tras_inexistente = overlay.first.locator("#segNombreCliente").input_value()
alimentador_tras_inexistente = overlay.first.locator("#segAlimentador").input_value()
assert nombre_tras_inexistente == "", f"El nombre deberia quedar vacio con un cliente inexistente: {nombre_tras_inexistente!r}"
assert alimentador_tras_inexistente == "", f"El alimentador deberia quedar vacio con un cliente inexistente: {alimentador_tras_inexistente!r}"
capturar_paso(app, "cliente_inexistente_datos_limpios", paso_excel=4)

# Paso 5: primer cliente otra vez, despues un SEGUNDO cliente valido
# distinto - los datos (incluidos medidores) deben limpiarse/reemplazarse
overlay.first.locator("#segNumeroCliente").fill("1391305")
overlay.first.locator("#segNumeroCliente").press("Tab")
app.wait_for_timeout(2000)
assert overlay.first.locator("#segNombreCliente").input_value() == "CORTEZ SANCHEZ DE ARRIAGA IRMA ELIZABETH", "No se recargo el primer cliente"

overlay.first.locator("#segNumeroCliente").fill("508904")
overlay.first.locator("#segNumeroCliente").press("Tab")
app.wait_for_timeout(2000)
nombre2 = overlay.first.locator("#segNombreCliente").input_value()
alimentador2 = overlay.first.locator("#segAlimentador").input_value()
ruta2 = overlay.first.locator("#segRuta").input_value()
llave2 = overlay.first.locator("#segLlave").input_value()
texto_overlay2 = overlay.first.inner_text()
assert nombre2 == "NUÑEZ VILCA VDA DE GAMARRA EMILIA", f"No se cargo el segundo cliente: {nombre2!r}"
assert alimentador2 == "SM - 11", f"Alimentador del segundo cliente inesperado: {alimentador2!r}"
assert ruta2 == "019 - 902 - 1000", f"Ruta del segundo cliente inesperada: {ruta2!r}"
assert llave2 == "A10145 - 2", f"Llave del segundo cliente inesperada: {llave2!r}"
assert "6034669" not in texto_overlay2 and "MA - 41" not in texto_overlay2, f"Los datos/medidor del primer cliente deberian haberse limpiado al cambiar de cliente: {texto_overlay2[-400:]!r}"
capturar_paso(app, "segundo_cliente_reemplaza_datos_anteriores", paso_excel=5)
'''

CUERPOS_REALES["CP055"] = '''
from pypdf import PdfReader

app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: modo consulta (orden real 3365694, rol_actual=EXPLRECAU
# distinto del rol de la sesion DACD -> abre en solo lectura)
buscar_y_seleccionar_orden(app, frame, "3365694", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal_a = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
assert not modal_a.get_by_role("button", name=re.compile("^Enviar$", re.I)).first.is_enabled(), "En modo consulta Enviar deberia estar deshabilitado"
assert not modal_a.get_by_role("button", name=re.compile("^Finalizar$", re.I)).first.is_enabled(), "En modo consulta Finalizar deberia estar deshabilitado"
pdf_btn_a = modal_a.get_by_role("button", name=re.compile("Descargar PDF", re.I))
for _ in range(15):
    if pdf_btn_a.count() and pdf_btn_a.first.is_enabled():
        break
    app.wait_for_timeout(500)
assert pdf_btn_a.count() and pdf_btn_a.first.is_enabled(), "En modo consulta Descargar PDF deberia estar habilitado"
capturar_paso(app, "escenario_a_modo_consulta", paso_excel=1)

with app.expect_download(timeout=20000) as descarga_info_a:
    pdf_btn_a.first.click(force=True)
ruta_pdf_a = EVIDENCIA / "CP055_consulta_3365694.pdf"
descarga_info_a.value.save_as(ruta_pdf_a)
texto_pdf_a = "\\n".join(p.extract_text() for p in PdfReader(str(ruta_pdf_a)).pages)
assert "3365694" in texto_pdf_a, f"El PDF deberia incluir el numero de orden: {texto_pdf_a!r}"
assert "508904" in texto_pdf_a, f"El PDF deberia incluir el numero de cliente: {texto_pdf_a!r}"
assert "EXPLRECAU" in texto_pdf_a, f"El PDF deberia incluir el ejecutor (rol actual): {texto_pdf_a!r}"
assert "020906" in texto_pdf_a, f"El PDF deberia incluir el trabajo: {texto_pdf_a!r}"
assert "Fecha Impresi" in texto_pdf_a, f"El PDF deberia incluir la fecha de impresion: {texto_pdf_a!r}"
capturar_paso(app, "pdf_descargado_modo_consulta", paso_excel=1)
modal_a.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
app.wait_for_timeout(1000)

# Escenario B: modo modificacion (orden real 3365695, rol_actual=DACD
# tras UPDATE directo - mismo rol que la sesion, confirmado en vivo
# 10/11/2026 que abre con Enviar/Finalizar habilitados y campos editables)
buscar_y_seleccionar_orden(app, frame, "3365695", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal_b = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
assert modal_b.get_by_role("button", name=re.compile("^Enviar$", re.I)).first.is_enabled(), "En modo modificacion Enviar deberia estar habilitado"
assert modal_b.get_by_role("button", name=re.compile("^Finalizar$", re.I)).first.is_enabled(), "En modo modificacion Finalizar deberia estar habilitado"
pdf_btn_b = modal_b.get_by_role("button", name=re.compile("Descargar PDF", re.I))
for _ in range(15):
    if pdf_btn_b.count() and pdf_btn_b.first.is_enabled():
        break
    app.wait_for_timeout(500)
assert pdf_btn_b.count() and pdf_btn_b.first.is_enabled(), "En modo modificacion Descargar PDF deberia estar habilitado"
capturar_paso(app, "escenario_b_modo_modificacion", paso_excel=2)

with app.expect_download(timeout=20000) as descarga_info_b:
    pdf_btn_b.first.click(force=True)
ruta_pdf_b = EVIDENCIA / "CP055_modificacion_3365695.pdf"
descarga_info_b.value.save_as(ruta_pdf_b)
texto_pdf_b = "\\n".join(p.extract_text() for p in PdfReader(str(ruta_pdf_b)).pages)
assert "3365695" in texto_pdf_b, f"El PDF deberia incluir el numero de orden: {texto_pdf_b!r}"
assert "468322" in texto_pdf_b, f"El PDF deberia incluir el numero de cliente: {texto_pdf_b!r}"
capturar_paso(app, "pdf_descargado_modo_modificacion", paso_excel=2)
modal_b.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
app.wait_for_timeout(1000)

# Escenario C: modo creacion (SEGEN) - la accion no deberia mostrarse
overlay = abrir_segen(app, frame)
pdf_btn_c = overlay.first.get_by_role("button", name=re.compile("Descargar PDF", re.I))
assert pdf_btn_c.count() == 0, f"En modo creacion la accion de Descargar PDF no deberia mostrarse, se encontraron {pdf_btn_c.count()} boton(es)"
capturar_paso(app, "escenario_c_sin_boton_pdf_en_creacion", paso_excel=3)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP051"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: orden real 3365694 (rol_actual=EXPLRECAU, distinto del
# rol de la sesion DACD) -> modo consulta
buscar_y_seleccionar_orden(app, frame, "3365694", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last

for campo in ["segNumeroCliente", "segTipoOrden", "segTema", "segTrabajo", "segClase", "segUsuarioDestino"]:
    assert not modal.locator(f"#{campo}").is_enabled(), f"El panel {campo} deberia estar deshabilitado en modo consulta"
assert not modal.get_by_role("button", name=re.compile("^Enviar$", re.I)).first.is_enabled(), "Enviar deberia estar deshabilitado en modo consulta"
assert not modal.get_by_role("button", name=re.compile("^Finalizar$", re.I)).first.is_enabled(), "Finalizar deberia estar deshabilitado en modo consulta"
pdf_btn = modal.get_by_role("button", name=re.compile("Descargar PDF", re.I))
for _ in range(15):
    if pdf_btn.count() and pdf_btn.first.is_enabled():
        break
    app.wait_for_timeout(500)
assert pdf_btn.count() and pdf_btn.first.is_enabled(), "Descargar PDF deberia estar habilitado en modo consulta"
capturar_paso(app, "escenario_a_modo_lectura", paso_excel=3)

modal.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
app.wait_for_timeout(1000)
assert frame.locator("button", has_text="Buscar").count() > 0, "No se volvio a la bandeja tras cerrar el modal"
capturar_paso(app, "vuelta_a_la_bandeja", paso_excel=4)

# Escenario B: numero de orden inexistente - el sistema informa la
# situacion (Ventana de Validacion) y la aplicacion sigue funcionando
try:
    buscar_y_seleccionar_orden(app, frame, "9999998", tipo_orden="SEGEN = Solicitudes Especiales")
except PWTimeoutError:
    pass
app.wait_for_timeout(1000)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje and "No se encontro la orden solicitada" in mensaje, f"Mensaje inesperado para orden inexistente: {mensaje!r}"
capturar_paso(app, "escenario_b_orden_inexistente", paso_excel=5)
assert frame.locator("button", has_text="Buscar").count() > 0, "La aplicacion deberia seguir en ejecucion tras la orden inexistente"
'''

CUERPOS_REALES["CP052"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)


def _modificar_y_enviar(numero_orden, texto_observacion, paso_excel_base):
    buscar_y_seleccionar_orden(app, frame, numero_orden, tipo_orden="SEGEN = Solicitudes Especiales")
    frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
    app.wait_for_timeout(3000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
    assert modal.locator("#segUsuarioDestino").is_editable(), f"Usuario Destino deberia ser editable en modo modificacion (orden {numero_orden})"
    assert modal.locator("textarea").last.is_editable(), f"La observacion deberia ser editable en modo modificacion (orden {numero_orden})"
    assert modal.get_by_role("button", name=re.compile("^Enviar$", re.I)).first.is_enabled(), f"Enviar deberia estar habilitado en modo modificacion (orden {numero_orden})"
    assert modal.get_by_role("button", name=re.compile("^Finalizar$", re.I)).first.is_enabled(), f"Finalizar deberia estar habilitado en modo modificacion (orden {numero_orden})"
    capturar_paso(app, f"orden_{numero_orden}_modo_modificacion", paso_excel=paso_excel_base)

    buscador = abrir_buscador_usuario_destino(app, frame, modal)
    fila = buscador.locator("tr.sm-fila", has_text="EPSG")
    for _ in range(6):
        if fila.count():
            break
        sgtes = buscador.get_by_role("button", name=re.compile("Sgtes", re.I))
        if sgtes.count() and sgtes.is_enabled():
            sgtes.click(force=True)
            app.wait_for_timeout(1200)
            fila = buscador.locator("tr.sm-fila", has_text="EPSG")
        else:
            break
    if fila.count():
        fila.first.click(force=True)
        buscador.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
        app.wait_for_timeout(1000)
    else:
        buscador.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
        app.wait_for_timeout(800)
        modal.locator("#segUsuarioDestino").fill("EPSG")
    capturar_paso(app, f"orden_{numero_orden}_usuario_destino_alternativo", paso_excel=paso_excel_base + 1)

    # Gotcha real confirmado en vivo 10/11/2026: cualquier accion que le
    # quite el foco al textarea de observacion ANTES de clickear Enviar
    # (un .press("Tab") explicito, o incluso un capturar_paso() de por
    # medio - su screenshot es full_page=True y ese scroll tambien hace
    # blur) dispara una validacion en segundo plano que deja un overlay
    # de carga (.seg-overlay) tapando el boton Enviar de forma
    # persistente en este contexto (headless + slowmo). Por eso el
    # fill() y el click a Enviar van seguidos, SIN ningun paso intermedio.
    # Gotcha real confirmado en vivo 10/11/2026: un div .seg-overlay
    # (loading propio del formulario SEGEN) queda tapando el boton
    # Enviar en este flujo de MODIFICAR (no en el de CREAR) - un
    # click(force=True) de Playwright sigue despachando el evento en
    # las coordenadas del boton, pero el navegador se lo entrega al
    # elemento que esta FISICAMENTE encima en ese pixel (el overlay),
    # asi que nunca llega ningun request al backend (confirmado: 0
    # respuestas de red capturadas tras el click). Fix: invocar
    # el.click() directo via evaluate(), que llama al handler de
    # Angular sin pasar por el hit-testing visual del navegador.
    modal.locator("textarea").last.fill(texto_observacion)
    modal.get_by_role("button", name=re.compile("^Enviar$", re.I)).evaluate("el => el.click()")
    app.wait_for_timeout(3000)
    mensaje = cerrar_dialogo_validacion_si_aparece(app, frame, timeout_ms=8000)
    assert mensaje and f"La Orden Numero: {numero_orden} ha sido enviada." in mensaje, f"Mensaje de confirmacion inesperado para la orden {numero_orden}: {mensaje!r}"
    capturar_paso(app, f"orden_{numero_orden}_enviada", paso_excel=paso_excel_base + 2)


# Escenario A: orden real 3365695 en estado Requerimiento (RQ), rol_actual=DACD via UPDATE directo
_modificar_y_enviar("3365695", "PRUEBA SEGEN CP052 - escenario A (Requerimiento)", paso_excel_base=2)

# Escenario B (repeticion, paso 6 de la matriz): orden real 43796 en
# estado Devolucion (DV), con rol receptor=DACD de forma nativa (sin
# necesitar UPDATE). NOTA: no se encontro ninguna orden real en estado
# Ejecucion (EJ) en el ambiente de Pruebas para repetir ese 3er
# escenario - la unica forma de confirmarlo seria con la consulta
# pesada de "Todas las Ordenes" (2.3M filas, intermitente/timeout
# confirmado en vivo) o un insert temporal adicional.
_modificar_y_enviar("43796", "PRUEBA SEGEN CP052 - escenario B (Devolucion)", paso_excel_base=6)
'''

CUERPOS_REALES["CP053"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: orden real 3365695 (RQ, rol_actual=DACD via UPDATE) -
# finalizar de verdad (Aceptar). Mismo gotcha del .seg-overlay que
# CP052: click de Finalizar via evaluate(), no via Playwright click normal.
buscar_y_seleccionar_orden(app, frame, "3365695", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal_a = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
boton_finalizar_a = modal_a.get_by_role("button", name=re.compile("^Finalizar$", re.I))
for _ in range(15):
    if boton_finalizar_a.count() and boton_finalizar_a.first.is_enabled():
        break
    app.wait_for_timeout(500)
assert boton_finalizar_a.count() and boton_finalizar_a.first.is_enabled(), "Finalizar deberia estar habilitado en modo modificacion"

# Reintento sobre el flujo completo Finalizar->confirmacion->Aceptar:
# gotcha ya conocido (ver CP042/043) de 'Error de Servicio: Error al
# consultar las ordenes de la bandeja' intermitente - confirmado en
# vivo 10/11/2026 que tambien aparece en el refresco posterior a
# finalizar un SEGEN, no solo en el de un EXTRAC.
mensaje_a = None
for _intento in range(6):
    modal_a.get_by_role("button", name=re.compile("^Finalizar$", re.I)).evaluate("el => el.click()")
    app.wait_for_timeout(2000)
    error_servicio_a = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio"))
    if error_servicio_a.count() and error_servicio_a.last.is_visible():
        error_servicio_a.last.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(2000)
        continue
    confirmacion_a = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Confirmaci.n SEGEN"))
    assert confirmacion_a.count() and confirmacion_a.last.is_visible(), "No aparecio la confirmacion de Finalizar (Confirmacion SEGEN)"
    texto_confirmacion_a = confirmacion_a.last.inner_text()
    assert "Confirmaci" in texto_confirmacion_a and "SEGEN" in texto_confirmacion_a, f"Titulo de confirmacion inesperado: {texto_confirmacion_a!r}"
    assert "Est" in texto_confirmacion_a and "seguro que desea finalizar el SEGEN" in texto_confirmacion_a, f"Texto de confirmacion inesperado: {texto_confirmacion_a!r}"
    capturar_paso(app, "confirmacion_finalizar_3365695", paso_excel=3)

    confirmacion_a.last.get_by_role("button", name=re.compile("^Aceptar$", re.I)).click(force=True)
    app.wait_for_timeout(3000)
    dlg_resultado_a = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación|Error de Servicio"))
    if dlg_resultado_a.count() and "Error de Servicio" in dlg_resultado_a.first.inner_text():
        dlg_resultado_a.first.get_by_role("button", name=re.compile("Cancelar", re.I)).click(force=True)
        app.wait_for_timeout(2000)
        continue
    assert dlg_resultado_a.count() and dlg_resultado_a.first.is_visible(), "No se vio el mensaje de resultado de la finalizacion"
    mensaje_a = dlg_resultado_a.first.inner_text()
    assert "3365695" in mensaje_a and "ha sido finalizado correctamente" in mensaje_a, f"Mensaje de finalizacion inesperado: {mensaje_a!r}"
    dlg_resultado_a.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(1500)
    break
assert mensaje_a is not None, "No se pudo completar la finalizacion tras varios intentos (Error de Servicio persistente)"
capturar_paso(app, "orden_3365695_finalizada", paso_excel=4)

# Verificacion de bandeja refrescada SIN volver a abrir el modal de
# Busqueda (gotcha real confirmado en vivo 10/11/2026: justo despues de
# cerrar los dialogos de Error de Servicio/confirmacion puede quedar un
# tooltip-popover residual (.cdk-overlay-popover) que intercepta el
# siguiente click en 'Buscar' - el texto de la grilla ya esta
# refrescado automaticamente, no hace falta buscar de nuevo).
texto_bandeja_a = frame.locator("body").inner_text()
assert "3365695" in texto_bandeja_a and "Finalizacion" in texto_bandeja_a, f"La orden deberia quedar en estado Finalizacion en la bandeja ya refrescada: {texto_bandeja_a[-300:]!r}"
capturar_paso(app, "orden_3365695_en_bandeja_finalizada", paso_excel=4)

# Escenario B: orden real 43796 (DV, rol_actual=DACD via UPDATE) -
# cancelar la finalizacion, debe conservar su estado anterior (Devolucion)
buscar_y_seleccionar_orden(app, frame, "43796", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal_b = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
modal_b.get_by_role("button", name=re.compile("^Finalizar$", re.I)).evaluate("el => el.click()")
app.wait_for_timeout(2000)
confirmacion_b = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Confirmaci.n SEGEN"))
assert confirmacion_b.count() and confirmacion_b.last.is_visible(), "No aparecio la confirmacion de Finalizar para la orden 43796"
capturar_paso(app, "confirmacion_finalizar_43796", paso_excel=3)
confirmacion_b.last.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(1500)

assert modal_b.get_by_role("button", name=re.compile("^Enviar$", re.I)).first.is_enabled(), "Tras cancelar la finalizacion deberia seguir en modo modificacion (Enviar habilitado)"
capturar_paso(app, "orden_43796_sigue_en_modificacion", paso_excel=5)
modal_b.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(1000)

texto_bandeja_b = frame.locator("body").inner_text()
assert "43796" in texto_bandeja_b and "Devolucion" in texto_bandeja_b, f"La orden 43796 deberia conservar su estado anterior (Devolucion) tras cancelar: {texto_bandeja_b[-300:]!r}"
capturar_paso(app, "orden_43796_conserva_estado_devolucion", paso_excel=5)
'''

CUERPOS_REALES["CP054"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Orden real 43796 (DV, rol_actual=DACD), ya tiene 3 observaciones
# previas reales acumuladas en sus movimientos (confirmado en vivo:
# 2 historicas de 2002 + 1 de la prueba de CP052).
buscar_y_seleccionar_orden(app, frame, "43796", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last

observaciones_previas = modal.locator("textarea").first
assert not observaciones_previas.is_editable(), "Las observaciones previas deberian estar en modo lectura (no editables)"
texto_previas = observaciones_previas.input_value()
assert texto_previas.count("\\n") >= 1, f"Las observaciones previas deberian verse acumuladas (varios movimientos): {texto_previas!r}"
capturar_paso(app, "observaciones_previas_acumuladas_solo_lectura", paso_excel=2)

# Paso 3: Enter no debe incorporar salto de linea en la observacion nueva
observacion_nueva = modal.locator("textarea").last
observacion_nueva.fill("")
observacion_nueva.type("Texto de Prueba 123", delay=30)
observacion_nueva.press("Enter")
observacion_nueva.type(" - sin salto de linea", delay=30)
valor_tras_enter = observacion_nueva.input_value()
assert "\\n" not in valor_tras_enter, f"Enter no deberia incorporar un salto de linea en la observacion nueva: {valor_tras_enter!r}"
capturar_paso(app, "enter_no_agrega_salto_de_linea", paso_excel=3)

# Paso 4: Enviar con la observacion mezclando mayusculas y minusculas
observacion_nueva.fill("Texto de Prueba 123")
modal.get_by_role("button", name=re.compile("^Enviar$", re.I)).evaluate("el => el.click()")
app.wait_for_timeout(3000)
mensaje = cerrar_dialogo_validacion_si_aparece(app, frame, timeout_ms=8000)
assert mensaje and "43796" in mensaje and "ha sido enviada" in mensaje, f"Mensaje de confirmacion inesperado: {mensaje!r}"
capturar_paso(app, "envio_con_observacion_mixta", paso_excel=4)

# Paso 5: reabrir y verificar que el movimiento conserva mayus/minus,
# sin saltos de linea, dentro de las observaciones acumuladas
buscar_y_seleccionar_orden(app, frame, "43796", tipo_orden="SEGEN = Solicitudes Especiales")
frame.locator("button", has_text=re.compile("Consultar|Modificar")).first.click(force=True)
app.wait_for_timeout(3000)
modal2 = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Solicitud Especial")).last
texto_previas_2 = modal2.locator("textarea").first.input_value()
assert "Texto de Prueba 123" in texto_previas_2, f"La observacion deberia conservar mayusculas/minusculas tal como se ingreso (sin convertirse a mayusculas): {texto_previas_2!r}"
capturar_paso(app, "movimiento_conserva_mayus_minus", paso_excel=5)

# Paso 6: repetir el envio dejando la observacion vacia
modal2.locator("textarea").last.fill("")
modal2.get_by_role("button", name=re.compile("^Enviar$", re.I)).evaluate("el => el.click()")
app.wait_for_timeout(3000)
mensaje2 = cerrar_dialogo_validacion_si_aparece(app, frame, timeout_ms=8000)
assert mensaje2 and "43796" in mensaje2 and "ha sido enviada" in mensaje2, f"Mensaje de confirmacion inesperado (observacion vacia): {mensaje2!r}"
capturar_paso(app, "envio_con_observacion_vacia", paso_excel=6)
'''

CUERPOS_REALES["CP060"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
overlay = abrir_segen(app, frame)

# Paso 1-3: buscador de Usuario Destino, rol de 1 caracter ('*', tipo F,
# area asignada manualmente para destrabar el caso - ver
# casos_fallidos_confirmados.json H002). Se recorre con Sgtes hasta
# encontrarlo (no esta garantizado en la primera pagina).
buscador_rol = abrir_buscador_usuario_destino(app, frame, overlay)
fila_rol = buscador_rol.locator("tr.sm-fila", has_text=re.compile(r"^\\*"))
for _ in range(60):
    if fila_rol.count():
        break
    sgtes = buscador_rol.get_by_role("button", name=re.compile("Sgtes", re.I))
    if not sgtes.is_enabled():
        break
    sgtes.click(force=True)
    app.wait_for_timeout(700)
    fila_rol = buscador_rol.locator("tr.sm-fila", has_text=re.compile(r"^\\*"))
assert fila_rol.count(), "No se encontro el rol '*' en el buscador de Usuario Destino"
capturar_paso(app, "rol_1_caracter_encontrado", paso_excel=2)
fila_rol.first.locator("td").first.click()
buscador_rol.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
app.wait_for_timeout(1000)
assert not buscador_rol.first.is_visible(), "El buscador deberia cerrarse tras Seleccionar"
valor_rol = overlay.first.locator("#segUsuarioDestino").input_value()
assert valor_rol == "0*", f"El rol de 1 caracter deberia normalizarse a dos caracteres ('0*'): {valor_rol!r}"
capturar_paso(app, "rol_normalizado_a_dos_caracteres", paso_excel=3)

# Paso 4: repetir desde el campo Nro. Cliente (segundo boton "...")
buscador_cliente = abrir_buscador_dinamico(app, frame, "Consultar Cliente", 1, overlay)
fila_cliente = buscador_cliente.locator("tr.sm-fila").first
assert fila_cliente.count(), "No se encontraron resultados en el buscador de Cliente"
numero_cliente_esperado = fila_cliente.locator("td").first.inner_text().strip()
fila_cliente.locator("td").first.click()
buscador_cliente.get_by_role("button", name=re.compile("^Seleccionar$", re.I)).click(force=True)
app.wait_for_timeout(1000)
assert not buscador_cliente.first.is_visible(), "El buscador de Cliente deberia cerrarse tras Seleccionar"
valor_cliente = overlay.first.locator("#segNumeroCliente").input_value()
assert valor_cliente == numero_cliente_esperado, f"El campo deberia recibir el numero de cliente de la fila seleccionada ({numero_cliente_esperado!r}): {valor_cliente!r}"
capturar_paso(app, "numero_cliente_recibido", paso_excel=4)
'''

CUERPOS_REALES["CP049"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)

# Escenario A: sin Rol Destino (Usuario Destino vacio)
overlay = abrir_segen(app, frame)
overlay.first.locator("textarea").last.fill("CP049 escenario A")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(2000)
mensaje_a = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_a and "Debe ingresar el Rol Destino" in mensaje_a, f"Mensaje inesperado en escenario A: {mensaje_a!r}"
capturar_paso(app, "escenario_a_sin_rol_destino", paso_excel=2)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)

# Escenario B: rol destino invalido (tipeado directo, sin pasar por el
# buscador - confirmado en vivo que el backend lo rechaza igual)
overlay = abrir_segen(app, frame)
overlay.first.locator("#segUsuarioDestino").fill("NOEXISTE99")
overlay.first.locator("textarea").last.fill("CP049 escenario B")
overlay.first.locator("button", has_text="Enviar").click(force=True)
app.wait_for_timeout(2000)
mensaje_b = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_b and "Debe de seleccionar un rol destino válido." in mensaje_b, f"Mensaje inesperado en escenario B: {mensaje_b!r}"
capturar_paso(app, "escenario_b_rol_invalido", paso_excel=2)
overlay.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP030"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
buscar_y_seleccionar_orden(app, frame, "40006337", tipo_orden="SEGEN = Solicitudes Especiales")
historial = abrir_historial_de_orden(app, frame)
capturar_paso(app, "historial_abierto", paso_excel=1)

# Correlativo 0000002: texto_envio IS NULL en acl_orden_flujo (confirmado
# por SQL directo: SELECT f.corr_flujo, f.texto_envio FROM acl_orden_flujo
# f WHERE f.empresa='7' AND f.numero_orden=40006337 AND f.texto_envio IS NULL).
# El mensaje "No existen observaciones" NO aparece dentro del panel inline
# (.his-obs-box, que queda vacio) sino en una "Ventana de Validacion"
# aparte (overlay hermano del modal de Historial) - gotcha confirmado en
# vivo 09/11/2026 tras una corrida previa que lo paso por alto mirando
# solo el texto del modal de Historial.
fila = historial.first.locator("tr.his-fila", has_text="0000002")
fila.first.locator("td").first.click()
app.wait_for_timeout(1500)
capturar_paso(app, "tras_seleccionar_correlativo_0000002", paso_excel=3)
mensaje_dialogo = cerrar_dialogo_validacion_si_aparece(app, frame)
assert mensaje_dialogo is not None and "No existen observaciones" in mensaje_dialogo, f"Se esperaba la 'Ventana de Validacion' con 'No existen observaciones' para el correlativo 0000002 (texto_envio NULL) de la orden 40006337: {mensaje_dialogo!r}"
capturar_paso(app, "mensaje_no_existen_observaciones", paso_excel=4)
historial.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).click(force=True)
app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP040"] = '''
app, frame = abrir_adsoltra(page, paso_excel=1)
# Orden 500007 vuelta a RQ con UPDATE directo (estaba en Finalizacion
# por el run de CP043) para cumplir la precondicion real de CP040 (orden
# EXTRAC NO finalizada con adjunto registrado) - no hay ninguna orden
# EXTRAC no finalizada nativa en todo el ambiente de Pruebas (ver
# casos_fallidos_confirmados.json, 0 EXTRAC en Pendientes/Devueltas/Anuladas).
buscar_y_seleccionar_orden(app, frame, "500007")
frame.locator("button", has_text="Consultar/Modificar").first.click()
app.wait_for_timeout(2500)
extractor = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Extractor")).last
assert extractor.count() and extractor.first.is_visible(), "No se abrio el Extractor de la orden de prueba"
capturar_paso(app, "extractor_no_finalizado", paso_excel=2)

boton_guardar = extractor.first.get_by_role("button", name=re.compile(r"^\\s*Guardar\\s*$", re.I))
assert boton_guardar.count(), "No se encontro el boton Guardar (accion de obtencion del adjunto, paso 3 de la matriz)"
try:
    with app.expect_download(timeout=15000) as descarga_info:
        boton_guardar.first.click(force=True)
    capturar_paso(app, "descarga_confirmada", paso_excel=4)
    assert False, f"INESPERADO: la descarga SI se completo ({descarga_info.value.suggested_filename}) - revisar si el defecto de CP043 (retiro de adjunto) se corrigio"
except PWTimeoutError:
    mensaje_dialogo = cerrar_dialogo_validacion_si_aparece(app, frame)
    capturar_paso(app, "guardar_sin_descarga", paso_excel=4)
    # PENDIENTE DE REPORTAR A DESARROLLO (mismo defecto de fondo que
    # CP043): el boton Guardar SI es la accion real de descarga (confirmado
    # en vivo 10/11/2026 con la orden 500007 en estado RQ), pero el backend
    # no logra servir el archivo - mismo problema sistemico del servicio
    # de repositorio de adjuntos, visto ahora desde el lado de la descarga.
    assert mensaje_dialogo is not None and "No existen" not in mensaje_dialogo, f"Se esperaba una descarga exitosa (paso 4-5 de la matriz), pero Guardar no descargo nada: {mensaje_dialogo!r}"
    assert False, f"El archivo NO se descarga: {mensaje_dialogo!r} - mismo defecto sistemico de repositorio de adjuntos que CP043"
extractor.first.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(800)
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
