"""
generate_scripts.py de PR000349-SP9 - FUENTE DE VERDAD que genera los CPxxx.py.

Proyecto: Migracion Modulo Encargos LuzDelSur (Sprint 9), 6 RF (RF-01..RF-06),
46 casos (ver matriz_casos.json). Dos dominios independientes que comparten
sprint pero no tablas ni logica: Cobranza (RF-01 Informacion FONAVI, RF-02
Mantenedor de Orden de Pagos, RF-03 Consulta de Cobranza Externa, RF-04
Mantenimiento de Proyectos de Encargos) y Medidores (RF-05 Base Semestral de
Medidores, RF-06 Consulta y Extraccion de la Base Semestral).
Ver documentos/EF_texto.txt y documentos/ET_texto.txt para el detalle
funcional/tecnico completo de cada RF.

Usa la arquitectura de modulos (Seccion 0c del checklist): el helper propio
de cada pantalla vive en _framework/modulos/ (uno por aplicativo, ej.
encargos_fonavi.py para RF-01) y se importa aca via fuente_modulo().

Cuenta de prueba unica para todo el proyecto: DCABA_DW.

Estado (10/11/2026): exploracion inicial de RF-01 (Informacion FONAVI)
completa en vivo - ruta de menu, componente Angular, campos reales,
endpoints reales y los 7 casos de RF-01 ya escritos. RF-02 a RF-06
pendientes de exploracion.
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
import encargos_fonavi as modulo_encargos_fonavi  # noqa: E402
import encargos_proyectos as modulo_encargos_proyectos  # noqa: E402
import encargos_ordenpago as modulo_encargos_ordenpago  # noqa: E402
import encargos_cobranzaexterna as modulo_encargos_cobranzaexterna  # noqa: E402
import encargos_basesemestral as modulo_encargos_basesemestral  # noqa: E402

PROYECTO = "PR000349-SP9"  # debe coincidir con el nombre de esta carpeta
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


HELPERS_MODULOS = fuente_modulo(modulo_encargos_fonavi) + "\n\n\n" + fuente_modulo(modulo_encargos_proyectos) + "\n\n\n" + fuente_modulo(modulo_encargos_ordenpago) + "\n\n\n" + fuente_modulo(modulo_encargos_cobranzaexterna) + "\n\n\n" + fuente_modulo(modulo_encargos_basesemestral)

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
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "1006406", "6")
assert mensaje is None, f"No se esperaba ningun mensaje de error: {mensaje!r}"
assert datos is not None, "Se esperaba la informacion FONAVI del cliente real"
assert datos["nombre"] == "ALVAREZ LANCHIPA NOLBERTO FERNANDO", f"Nombre inesperado: {datos['nombre']!r}"
assert datos["sucursal"] == "Pedro  Miotta", f"Sucursal inesperada: {datos['sucursal']!r}"
assert datos["numeroProyecto"] == "880333", f"Numero de proyecto inesperado: {datos['numeroProyecto']!r}"
assert datos["cuotas"] == 40, f"Cuotas inesperadas: {datos['cuotas']!r}"
assert datos["importe"] == 334.3, f"Importe inesperado: {datos['importe']!r}"
assert datos["mora"] == 15.22, f"Mora inesperada: {datos['mora']!r}"
capturar_paso(app, "cliente_con_registro_fonavi_consultado", paso_excel=4)
'''

CUERPOS_REALES["CP002"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "1", "9")
assert datos is None, f"No deberia haber datos para un cliente sin registro FONAVI: {datos!r}"
assert mensaje and "No existe datos del FONAVI para el cliente." in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_sin_registro_fonavi", paso_excel=3)
valor_cliente_tras_error = frame.locator("#numeroCliente").input_value()
assert valor_cliente_tras_error == "", f"La pantalla deberia limpiarse tras el error: numeroCliente={valor_cliente_tras_error!r}"
capturar_paso(app, "pantalla_limpia_tras_error", paso_excel=3)
'''

CUERPOS_REALES["CP003"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "1006406", "5")
assert datos is None, "No deberia dispararse la consulta con un DV incorrecto"
assert mensaje and "El dígito verificador no corresponde al N.° de Cliente ingresado." in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_dv_incorrecto", paso_excel=3)
valor_cliente_tras_dv_malo = frame.locator("#numeroCliente").input_value()
assert valor_cliente_tras_dv_malo == "1006406", f"El campo N.de Cliente NO deberia limpiarse con un DV incorrecto (se mantiene el foco/dato): {valor_cliente_tras_dv_malo!r}"
capturar_paso(app, "campo_cliente_se_mantiene", paso_excel=3)
'''

CUERPOS_REALES["CP004"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
boton_leer = frame.locator("button", has_text="Leer")
assert not boton_leer.is_enabled(), "El boton Leer deberia estar deshabilitado con el campo N.de Cliente vacio"
capturar_paso(app, "boton_leer_deshabilitado", paso_excel=3)
'''

CUERPOS_REALES["CP005"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "1006406", "6")
assert datos is not None, f"Se esperaba poder consultar al cliente antes de emitir: {mensaje!r}"
capturar_paso(app, "cliente_consultado_antes_de_emitir", paso_excel=1)

descarga = emitir_constancia_fonavi(app, frame, "08945612", "JUAN PEREZ")
assert descarga.suggested_filename == "ConstanciaFonavi_1006406.txt", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
ruta_descarga = EVIDENCIA / descarga.suggested_filename
descarga.save_as(ruta_descarga)
texto_constancia = ruta_descarga.read_text(encoding="utf-8", errors="replace")
assert "ALVAREZ LANCHIPA NOLBERTO FERNANDO" in texto_constancia, f"La constancia deberia incluir el nombre del cliente: {texto_constancia[:300]!r}"
assert "880333" in texto_constancia, f"La constancia deberia incluir el numero de proyecto: {texto_constancia[:300]!r}"
capturar_paso(app, "constancia_descargada", paso_excel=3)
'''

CUERPOS_REALES["CP006"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "47521", "1")
assert datos is not None, f"Se esperaba poder consultar al cliente: {mensaje!r}"
assert datos["historial"] == [], f"Se esperaba un cliente con historial vacio (sin constancias previas): {datos!r}"
boton_imprimir = frame.locator("button", has_text="Imprimir")
capturar_paso(app, "antes_de_imprimir_sin_representante", paso_excel=2)
# El boton Imprimir queda HABILITADO con el representante vacio (no se
# deshabilita de antemano) - la restriccion real ocurre al clickearlo:
# muestra una Ventana de Validacion y NO dispara ninguna descarga.
# Confirmado en vivo 13/11/2026 (corrige el assert anterior, que solo
# miraba is_enabled() sin clickear de verdad y por eso daba un falso
# FALLO).
boton_imprimir.click(force=True)
app.wait_for_timeout(1000)
dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validaci.n"))
assert dialogo.count() and dialogo.first.is_visible(), "Se esperaba la Ventana de Validacion al presionar Imprimir sin los datos del representante"
texto_dialogo = dialogo.first.inner_text()
assert "representante" in texto_dialogo.lower(), f"Mensaje de validacion inesperado: {texto_dialogo!r}"
capturar_paso(app, "mensaje_representante_obligatorio", paso_excel=3)
dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
app.wait_for_timeout(500)
'''

CUERPOS_REALES["CP007"] = '''
app, frame = abrir_fonavi(page, paso_excel=1)
datos, mensaje = consultar_cliente_fonavi(app, frame, "1006406", "6")
assert datos is not None, f"Se esperaba poder consultar al cliente antes de cancelar: {mensaje!r}"
capturar_paso(app, "consulta_en_curso_antes_de_cancelar", paso_excel=1)

frame.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)
assert frame.locator("#numeroCliente").input_value() == "", "N.de Cliente deberia quedar vacio tras Cancelar"
assert frame.locator("#digitoVerificador").input_value() == "", "Digito Verificador deberia quedar vacio tras Cancelar"
assert not frame.locator("button", has_text="Leer").is_enabled(), "Leer deberia quedar deshabilitado tras Cancelar"
assert not frame.locator("button", has_text="Imprimir").is_enabled(), "Imprimir deberia quedar deshabilitado tras Cancelar"
capturar_paso(app, "formulario_limpio_tras_cancelar", paso_excel=2)
'''

CUERPOS_REALES["CP023"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
datos = consultar_proyecto(app, frame, "0001", "880390")
assert datos["descripcion"].strip() == "A.H.PAMPL. ALTA  ST.VILLA AMP.F,G,H,I,K,", f"Descripcion inesperada: {datos['descripcion']!r}"
assert datos["direccionAdicional"] == "SAN JUAN MIRAFLORES", f"Direccion adicional inesperada: {datos['direccionAdicional']!r}"
assert datos["estado"] == "Activo", f"Estado inesperado: {datos['estado']!r}"
capturar_paso(app, "proyecto_existente_consultado", paso_excel=3)
'''

CUERPOS_REALES["CP024"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
boton_leer = frame.locator("button", has_text="Leer")
assert not boton_leer.is_enabled(), "El boton Leer deberia estar deshabilitado sin codigo de encargo"
capturar_paso(app, "boton_leer_deshabilitado_sin_encargo", paso_excel=2)
'''

CUERPOS_REALES["CP030"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
seleccionar_proyecto(frame, app, "0001", "880390")
capturar_paso(app, "proyecto_seleccionado_antes", paso_excel=1)

frame.locator("#codigoEncargo").fill("9999")
frame.locator("#codigoEncargo").press("Tab")
app.wait_for_timeout(1500)
valor_encargo = frame.locator(".ant-select-selection-item").count()
texto_pantalla = frame.locator("body").inner_text()
assert "Seleccione un encargo" in texto_pantalla, f"El encargo deberia limpiarse con un codigo invalido: {texto_pantalla[:300]!r}"
assert "Seleccione un proyecto" in texto_pantalla, f"El proyecto deberia limpiarse junto con el encargo invalido: {texto_pantalla[:300]!r}"
capturar_paso(app, "combos_limpiados_tras_encargo_invalido", paso_excel=3)
'''

CUERPOS_REALES["CP008"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
fecha_hoy = date.today().isoformat()
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Procesada", "Mayor o igual", fecha_hoy)
assert not datos.get("requiereConfirmacionTipoCambio"), "No se esperaba pedido de confirmacion de tipo de cambio (el tipo de cambio del dia ya esta registrado)"
ordenes = datos.get("ordenes") or []
assert len(ordenes) == 1, f"Se esperaba 1 fila de entrega Procesada: {ordenes!r}"
orden = ordenes[0]
assert orden["montoRecaudado"] == 250, f"Recaudado inesperado: {orden['montoRecaudado']!r}"
assert orden["montoComision"] == 80.0, f"Comision inesperada: {orden['montoComision']!r}"
assert orden["montoEntrega"] == 170.0, f"Entrega inesperada: {orden['montoEntrega']!r}"
assert orden["cantidad"] == 10, f"Cantidad inesperada: {orden['cantidad']!r}"
capturar_paso(app, "grilla_con_totales_procesada", paso_excel=4)
assert frame.locator("#totalRecaudado").input_value() == "250,00", "Total Recaudado de la grilla deberia mostrar 250,00"
assert frame.locator("#totalComision").input_value() == "80,00", "Total Comision de la grilla deberia mostrar 80,00"
assert frame.locator("#totalEntrega").input_value() == "170,00", "Total Entrega de la grilla deberia mostrar 170,00"
assert frame.locator("#totalCantidad").input_value() == "10", "Total Cantidad de la grilla deberia mostrar 10"
'''

CUERPOS_REALES["CP010"] = '''
app, frame = abrir_orden_pagos(page, paso_excel=1)
seleccionar_encargo(app, frame, "SEGURO SALUD")
boton_leer = frame.locator("button", has_text="Leer")
assert not boton_leer.is_enabled(), "Leer deberia quedar deshabilitado con un encargo sin comision configurada (ASS)"
texto_sin_comision = frame.locator("body").inner_text()
assert "no tiene comisión configurada" in texto_sin_comision, f"Deberia avisar que el encargo no tiene comision: {texto_sin_comision[:300]!r}"
capturar_paso(app, "leer_deshabilitado_sin_comision", paso_excel=2)

seleccionar_encargo(app, frame, "TELEFONICA DEL PERU MOVILES")
assert boton_leer.is_enabled(), "Leer deberia habilitarse con un encargo con comision vigente (TMO, control positivo)"
with app.expect_response(lambda r: "/api/" in r.url, timeout=15000) as resp_info:
    boton_leer.click(force=True)
assert resp_info.value.status == 200, f"Se esperaba 200 al consultar con el encargo de control (TMO): {resp_info.value.status}"
capturar_paso(app, "leer_habilitado_con_comision", paso_excel=2)
'''

CUERPOS_REALES["CP011"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Procesada", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) == 1, f"Se esperaba 1 fila de entrega Procesada antes de generar: {ordenes!r}"
capturar_paso(app, "consulta_procesada_antes_de_generar", paso_excel=1)

cuerpo, mensaje = marcar_entregas_y_generar(app, frame)
assert cuerpo.get("bloqueado") is True, f"Se esperaba que la generacion quedara bloqueada por el automatismo pendiente: {cuerpo!r}"
assert cuerpo.get("cantidadEntregas") == 0, f"No deberia haberse consumido ninguna entrega: {cuerpo!r}"
assert mensaje and "No se puede Generar orden" in mensaje, f"Mensaje de bloqueo inesperado: {mensaje!r}"
capturar_paso(app, "generacion_bloqueada_por_automatismo", paso_excel=3)
'''

CUERPOS_REALES["CP012"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Procesada", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) == 1, f"Se esperaba 1 fila de entrega Procesada antes de generar: {ordenes!r}"
assert ordenes[0]["codigoEntrega"] == 82698, f"Entrega inesperada: {ordenes[0]!r}"
capturar_paso(app, "consulta_procesada_antes_de_generar", paso_excel=1)

cuerpo, mensaje = marcar_entregas_y_generar(app, frame)
assert cuerpo.get("bloqueado") is False, f"No se esperaba bloqueo (sin automatismo pendiente): {cuerpo!r}"
assert cuerpo.get("cantidadEntregas") == 1, f"Se esperaba 1 entrega emitida: {cuerpo!r}"
assert cuerpo.get("montoTotal") == 170.0, f"Monto total neto inesperado (250.00 - 80.00 comision): {cuerpo!r}"
folio = cuerpo.get("folio")
assert folio, f"Se esperaba un folio asignado: {cuerpo!r}"
print(f"  FOLIO GENERADO (para la reversa manual en BD): {folio!r}")
capturar_paso(app, "orden_generada_con_folio", paso_excel=3)
'''

CUERPOS_REALES["CP015"] = '''
from datetime import date
import zipfile
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Procesada", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) == 1, f"Se esperaba 1 fila antes de exportar: {ordenes!r}"
capturar_paso(app, "consulta_antes_de_exportar", paso_excel=1)

descarga = exportar_a_excel(app, frame)
assert descarga.suggested_filename == "OrdenPagos.xlsx", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
ruta_descarga = EVIDENCIA / descarga.suggested_filename
descarga.save_as(ruta_descarga)
with zipfile.ZipFile(ruta_descarga) as z:
    assert z.testzip() is None, "El .xlsx exportado esta corrupto (testzip no devolvio None)"
    contenido_hoja = z.read("xl/worksheets/sheet1.xml").decode("utf-8", errors="replace")
    contenido_strings = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
assert "82698" in contenido_hoja, f"La fila exportada deberia incluir la entrega real 82698: {contenido_hoja[:500]!r}"
assert "<x:v>250</x:v>" in contenido_hoja, "El Recaudado (250) deberia venir como celda numerica, no texto"
assert "Chacarilla" in contenido_strings, "La oficina real (Chacarilla) deberia estar en el contenido exportado"
capturar_paso(app, "excel_exportado_y_validado", paso_excel=2)
'''

CUERPOS_REALES["CP016"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Procesada", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) == 1, f"Se esperaba 1 fila antes de cancelar: {ordenes!r}"
assert frame.locator("#totalRecaudado").input_value() == "250,00", "Total Recaudado deberia mostrar 250,00 antes de Cancelar"
capturar_paso(app, "consulta_antes_de_cancelar", paso_excel=1)

frame.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1500)
texto_tras_cancelar = frame.locator("body").inner_text()
assert "Realice una consulta" in texto_tras_cancelar, f"La grilla deberia limpiarse tras Cancelar: {texto_tras_cancelar[:300]!r}"
assert frame.locator("#totalRecaudado").input_value() == "0,00", "Total Recaudado deberia limpiarse a 0,00 tras Cancelar"
valor_combo_encargo = frame.locator(".ant-select-selection-item").first
assert valor_combo_encargo.count() and "TELEFONICA DEL PERU MOVILES" in valor_combo_encargo.inner_text(), "El combo Encargo de Cobranza deberia conservar la seleccion previa tras Cancelar"
capturar_paso(app, "grilla_limpia_combo_conservado", paso_excel=3)
'''

CUERPOS_REALES["CP013"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Liquidar", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) >= 1, f"Se esperaba al menos 1 orden en estado Liquidar: {ordenes!r}"
assert ordenes[0]["montoComision"] > 0, f"Se esperaba una orden con comision > 0 para esta prueba: {ordenes[0]!r}"
capturar_paso(app, "orden_en_liquidar_antes_de_emidoc", paso_excel=1)

monto_precargado, mensaje = liquidar_con_emidoc(app, frame, "Factura", "2026-01-14", "001", "4500")
assert monto_precargado != "0,00", f"El Monto de Pago deberia precargarse desde la comision real de la orden: {monto_precargado!r}"
assert mensaje and "el contrato de emisión no está especificado" in mensaje, f"Se esperaba el mensaje de corte por EMIDOC (B-01): {mensaje!r}"
capturar_paso(app, "liquidacion_bloqueada_por_emidoc", paso_excel=5)
'''

CUERPOS_REALES["CP014"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU MOVILES", "Liquidar", "Mayor o igual", date.today().isoformat())
ordenes = datos.get("ordenes") or []
assert len(ordenes) >= 1, f"Se esperaba al menos 1 orden en estado Liquidar: {ordenes!r}"
capturar_paso(app, "orden_en_liquidar_antes_de_periodo_cerrado", paso_excel=1)

monto_precargado, mensaje = liquidar_con_emidoc(app, frame, "Factura", "2025-12-15", "001", "4500")
assert mensaje and "se encuentra Cerrado" in mensaje, f"Se esperaba el mensaje de periodo contable cerrado: {mensaje!r}"
capturar_paso(app, "liquidacion_bloqueada_por_periodo_cerrado", paso_excel=4)
'''

CUERPOS_REALES["CP009"] = '''
from datetime import date
app, frame = abrir_orden_pagos(page, paso_excel=1)
datos = consultar_ordenes_pago(app, frame, "TELEFONICA DEL PERU FIJO", "Procesada", "Mayor o igual", date.today().isoformat())
assert datos.get("requiereConfirmacionTipoCambio") is True, f"Se esperaba que pida confirmacion de tipo de cambio: {datos!r}"
assert datos.get("tipoCambio"), f"Se esperaba el ultimo tipo de cambio disponible: {datos!r}"
capturar_paso(app, "respuesta_pide_confirmacion_tipo_cambio", paso_excel=3)

texto_pantalla = frame.locator("body").inner_text()
assert "No existe tipo de cambio del día" in texto_pantalla, f"Se esperaba el dialogo de confirmacion: {texto_pantalla[-400:]!r}"
assert "último tipo de cambio disponible" in texto_pantalla, f"Se esperaba la pregunta por el ultimo tipo de cambio: {texto_pantalla[-400:]!r}"
capturar_paso(app, "dialogo_confirmacion_tipo_cambio", paso_excel=3)
frame.get_by_role("button", name=re.compile("Cancelar", re.I)).last.click(force=True)
'''

CUERPOS_REALES["CP017"] = '''
app, frame = abrir_cobranza_externa(page, paso_excel=1)
cuerpo = consultar_cobranza_externa(app, frame, "0006", "Todas", "Entre", "2000-01-01", "2026-11-11")
resumen = cuerpo.get("resumen") or []
detalle = cuerpo.get("detalle") or []
assert len(resumen) == 8, f"Se esperaban 8 oficinas en el resumen (dato real estable, historico): {resumen!r}"
assert len(detalle) == 2, f"Se esperaban 2 productos en el detalle (dato real estable, historico): {detalle!r}"
assert cuerpo.get("totalTransacciones") == 12433, f"Total de transacciones inesperado: {cuerpo!r}"
assert cuerpo.get("totalMonto") == 210858, f"Total de monto inesperado: {cuerpo!r}"
capturar_paso(app, "resumen_y_detalle_con_totales", paso_excel=4)
'''

CUERPOS_REALES["CP018"] = '''
app, frame = abrir_cobranza_externa(page, paso_excel=1)
frame.locator("#encargo").click(force=True)
app.wait_for_timeout(1000)
frame.locator("nz-option-item", has_text="0006").first.click(force=True)
app.wait_for_timeout(1500)
frame.locator("#oficina").click(force=True)
app.wait_for_timeout(800)
frame.locator("nz-option-item", has_text=re.compile(r"^\\s*Todas\\s*$")).first.click(force=True)
app.wait_for_timeout(500)
frame.locator("#operadorFecha").click(force=True)
app.wait_for_timeout(800)
frame.locator("nz-option-item", has_text="Entre").first.click(force=True)
app.wait_for_timeout(500)
frame.locator("#fechaInicio").fill("2000-01-01")
app.wait_for_timeout(500)
capturar_paso(app, "fecha_fin_vacia_antes_de_buscar", paso_excel=2)

frame.locator("button", has_text="Buscar").click(force=True)
app.wait_for_timeout(1500)
texto_pantalla = frame.locator("body").inner_text()
assert "Ingrese la Fecha de Proceso Hasta" in texto_pantalla, f"Se esperaba el mensaje de validacion de fecha fin: {texto_pantalla[-400:]!r}"
capturar_paso(app, "consulta_bloqueada_sin_fecha_fin", paso_excel=3)
'''

CUERPOS_REALES["CP019"] = '''
app, frame = abrir_cobranza_externa(page, paso_excel=1)
capturar_paso(app, "pantalla_sin_encargo_seleccionado", paso_excel=1)
frame.locator("button", has_text="Buscar").click(force=True)
app.wait_for_timeout(1500)
texto_pantalla = frame.locator("body").inner_text()
assert "Seleccione el Encargo de Cobranza" in texto_pantalla, f"Se esperaba el mensaje de validacion de encargo: {texto_pantalla[-400:]!r}"
capturar_paso(app, "consulta_bloqueada_sin_encargo", paso_excel=2)
'''

CUERPOS_REALES["CP020"] = '''
import zipfile
app, frame = abrir_cobranza_externa(page, paso_excel=1)
consultar_cobranza_externa(app, frame, "0006", "Todas", "Entre", "2000-01-01", "2026-11-11")
capturar_paso(app, "consulta_antes_de_exportar", paso_excel=1)

frame.locator("button", has_text="Exportar a Excel").click(force=True)
app.wait_for_timeout(1000)
with app.expect_download(timeout=20000) as descarga_info:
    frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
descarga = descarga_info.value
assert descarga.suggested_filename == "CobranzaExterna.xlsx", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
ruta_descarga = EVIDENCIA / descarga.suggested_filename
descarga.save_as(ruta_descarga)
with zipfile.ZipFile(ruta_descarga) as z:
    assert z.testzip() is None, "El .xlsx exportado esta corrupto"
    workbook_xml = z.read("xl/workbook.xml").decode("utf-8", errors="replace")
nombres_hoja = re.findall(r\'name="([^"]+)"\', workbook_xml)
assert "Resumen" in nombres_hoja and "Detalle" in nombres_hoja, f"Se esperaban las hojas Resumen y Detalle: {nombres_hoja!r}"
capturar_paso(app, "excel_exportado_y_validado", paso_excel=2)
'''

CUERPOS_REALES["CP021"] = '''
app, frame = abrir_cobranza_externa(page, paso_excel=1)
consultar_cobranza_externa(app, frame, "0006", "Todas", "Entre", "2000-01-01", "2026-11-11")
capturar_paso(app, "consulta_con_resumen_y_detalle", paso_excel=1)

tabla_detalle = frame.locator("table").nth(1)
filas_detalle = tabla_detalle.locator("tbody tr")
cantidad_total = 0
monto_total = 0.0
for i in range(filas_detalle.count()):
    celdas = filas_detalle.nth(i).locator("td").all_inner_texts()
    cantidad_total += int(celdas[1].replace(".", "").replace(",", ""))
    monto_total += float(celdas[2].replace(".", "").replace(",", "."))
fila_totales = tabla_detalle.locator("tfoot tr").inner_text()
assert f"{cantidad_total:,}".replace(",", ".") in fila_totales, f"El total de Cantidad del detalle no coincide con la suma de sus filas: {fila_totales!r} vs suma={cantidad_total}"
capturar_paso(app, "totales_detalle_recalculados_ok", paso_excel=3)
'''

CUERPOS_REALES["CP022"] = '''
app, frame = abrir_cobranza_externa(page, paso_excel=1)
consultar_cobranza_externa(app, frame, "0006", "Todas", "Entre", "2000-01-01", "2026-11-11")
capturar_paso(app, "consulta_antes_de_cancelar", paso_excel=1)

frame.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1500)
texto_pantalla = frame.locator("body").inner_text()
assert texto_pantalla.count("Realice una consulta") >= 1, f"Las grillas deberian limpiarse tras Cancelar: {texto_pantalla[:600]!r}"
valores_combo = frame.locator(".ant-select-selection-item").all_inner_texts()
assert any("0006" in v for v in valores_combo), f"El combo Encargo deberia conservar la seleccion previa: {valores_combo!r}"
assert any("Entre" in v for v in valores_combo), f"El combo Operador deberia conservar la seleccion previa: {valores_combo!r}"
capturar_paso(app, "grillas_limpias_combos_conservados", paso_excel=3)
'''

CUERPOS_REALES["CP025"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
texto_confirma, cuerpo, mensaje = registrar_proyecto_nuevo(app, frame, "0001", "000456", "PROYECTO NUEVO SECTOR NORTE", "AV. LOS ANGELES 452")
assert "Se registrará el proyecto 000456 del encargo 0001" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
assert mensaje is None, f"No se esperaba ningun rechazo al registrar un codigo libre: {mensaje!r}"
capturar_paso(app, "proyecto_registrado", paso_excel=4)

datos_verificados = consultar_proyecto(app, frame, "0001", "000456")
assert datos_verificados["descripcion"].strip() == "PROYECTO NUEVO SECTOR NORTE", f"Descripcion no persistida: {datos_verificados!r}"
assert datos_verificados["direccionAdicional"] == "AV. LOS ANGELES 452", f"Direccion no persistida: {datos_verificados!r}"
assert datos_verificados["estado"] == "Activo", f"El proyecto nuevo deberia quedar Activo: {datos_verificados!r}"
capturar_paso(app, "proyecto_nuevo_disponible_en_combo", paso_excel=4)
'''

CUERPOS_REALES["CP027"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
datos_antes = consultar_proyecto(app, frame, "0001", "880390")
assert datos_antes["estado"] == "Activo", f"Se esperaba el proyecto activo antes de modificar: {datos_antes!r}"
capturar_paso(app, "proyecto_activo_antes_de_modificar", paso_excel=1)

texto_confirma, cuerpo, mensaje = modificar_proyecto(app, frame, "PROYECTO SECTOR NORTE ACTUALIZADO", "AV. LOS ANGELES 452 DPTO 302")
assert "Se modificará el proyecto 880390 del encargo 0001" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
assert mensaje is None, f"No se esperaba ningun rechazo al modificar un proyecto activo propio: {mensaje!r}"
capturar_paso(app, "proyecto_modificado", paso_excel=4)

datos_verificados = consultar_proyecto(app, frame, "0001", "880390")
assert datos_verificados["descripcion"].strip() == "PROYECTO SECTOR NORTE ACTUALIZADO", f"Descripcion no actualizada: {datos_verificados!r}"
assert datos_verificados["direccionAdicional"] == "AV. LOS ANGELES 452 DPTO 302", f"Direccion no actualizada: {datos_verificados!r}"
capturar_paso(app, "proyecto_actualizado_verificado", paso_excel=4)
'''

CUERPOS_REALES["CP029"] = '''
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
datos_antes = consultar_proyecto(app, frame, "0001", "880390")
assert datos_antes["estado"] == "Activo", f"Se esperaba el proyecto activo antes de eliminar: {datos_antes!r}"
capturar_paso(app, "proyecto_activo_antes_de_eliminar", paso_excel=1)

texto_confirma, cuerpo = eliminar_proyecto(app, frame)
assert "será eliminado lógicamente" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
texto_pantalla = frame.locator("body").inner_text()
assert "Proyecto eliminado exitosamente" in texto_pantalla, f"Se esperaba el mensaje real de exito: {texto_pantalla[:300]!r}"
capturar_paso(app, "proyecto_eliminado", paso_excel=3)

# El formulario se resetea por completo tras la baja (gotcha real confirmado
# en vivo 11/11/2026: el combo "Proyecto" excluye los Eliminados, asi que
# NO se puede re-consultar 880390 desde aqui - la pantalla ya lo confirma
# via el toast + el reseteo total, que deja Modificar/Eliminar deshabilitados
# por no haber nada seleccionado).
boton_modificar = frame.locator("button", has_text=re.compile("Ingresar|Modificar"))
boton_eliminar = frame.locator("button", has_text="Eliminar")
assert not boton_modificar.is_enabled(), "Modificar deberia quedar deshabilitado tras la baja (formulario reseteado)"
assert not boton_eliminar.is_enabled(), "Eliminar deberia quedar deshabilitado tras la baja (formulario reseteado)"
capturar_paso(app, "formulario_reseteado_tras_eliminar", paso_excel=3)
'''

CUERPOS_REALES["CP026"] = '''
import time
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
frame.locator("#codigoEncargo").fill("0001")
app.wait_for_timeout(500)
campo_codigo_proyecto = frame.locator("#codigoProyecto")
boton_accion = frame.locator("button", has_text=re.compile("Ingresar|Modificar")).first
for _ in range(6):
    if campo_codigo_proyecto.is_visible() and not campo_codigo_proyecto.is_disabled():
        break
    boton_accion.click(force=True)
    app.wait_for_timeout(1200)
campo_codigo_proyecto.fill("000456")
app.wait_for_timeout(500)
frame.locator("button", has_text="Leer").click(force=True)
app.wait_for_timeout(1500)
texto_tras_leer = frame.locator("body").inner_text()
assert "El proyecto no existe todavía" in texto_tras_leer, f"Se esperaba el codigo libre (modo Nuevo) antes del duplicado concurrente: {texto_tras_leer[-300:]!r}"
capturar_paso(app, "codigo_libre_antes_del_duplicado_concurrente", paso_excel=1)

print("  >>> AHORA: ejecutar el INSERT de precondicion de CP026 en BD (ventana de 35s) <<<")
time.sleep(35)
print("  >>> continuando (se asume que el INSERT ya se ejecuto) <<<")

frame.locator("#descripcion").fill("PROYECTO DUPLICADO QA - INTENTO NO DEBE GRABARSE")
frame.locator("#direccionAdicional").fill("CALLE QUE NO DEBE GRABARSE")
app.wait_for_timeout(500)

texto_confirma = _click_hasta_confirmacion(app, frame, boton_accion)
assert "Se registrará el proyecto 000456 del encargo 0001" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"

with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
    frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
app.wait_for_timeout(1500)
assert resp_info.value.status == 400, f"Se esperaba 400 al intentar registrar un duplicado concurrente: {resp_info.value.status}"
capturar_paso(app, "intento_de_alta_rechazado", paso_excel=4)

texto_pantalla = frame.locator("body").inner_text()
assert "Ventana de Validación" in texto_pantalla, f"Se esperaba la ventana de validacion de rechazo: {texto_pantalla[-400:]!r}"
assert "ya existe" in texto_pantalla, f"Mensaje de rechazo inesperado: {texto_pantalla[-400:]!r}"
capturar_paso(app, "mensaje_codigo_duplicado", paso_excel=5)
frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
app.wait_for_timeout(500)

frame.locator("button", has_text="Cancelar").click(force=True)
app.wait_for_timeout(1000)
datos_verificados = consultar_proyecto(app, frame, "0001", "000456")
assert datos_verificados["descripcion"].strip() == "PROYECTO DUPLICADO QA", f"La fila del otro usuario no deberia haberse modificado: {datos_verificados!r}"
assert datos_verificados["direccionAdicional"] == "CALLE DUPLICADA 123", f"La fila del otro usuario no deberia haberse modificado: {datos_verificados!r}"
capturar_paso(app, "fila_del_otro_usuario_intacta", paso_excel=5)
'''

CUERPOS_REALES["CP028"] = '''
import time
app, frame = abrir_proyectos_encargo(page, paso_excel=1)
datos_antes = consultar_proyecto(app, frame, "0001", "930001")
assert datos_antes["estado"] == "Activo", f"Se esperaba el proyecto activo antes de la eliminacion concurrente: {datos_antes!r}"
capturar_paso(app, "proyecto_activo_antes_de_eliminacion_concurrente", paso_excel=1)

print("  >>> AHORA: marcar 930001 como Eliminado en BD (ventana de 35s) <<<")
time.sleep(35)
print("  >>> continuando (se asume que el UPDATE ya se ejecuto) <<<")

texto_confirma, cuerpo, mensaje = modificar_proyecto(app, frame, "INTENTO DE MODIFICACION - NO DEBE GRABARSE", "CALLE QUE NO DEBE GRABARSE")
assert "Se modificará el proyecto 930001 del encargo 0001" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
capturar_paso(app, "modificacion_rechazada", paso_excel=3)

assert mensaje is not None, "Se esperaba un rechazo (el proyecto fue eliminado por otro usuario)"
assert "eliminado por otro usuario" in mensaje, f"Mensaje de rechazo inesperado: {mensaje!r}"
capturar_paso(app, "mensaje_eliminado_por_otro_usuario", paso_excel=3)
'''

CUERPOS_REALES["CP038"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S1")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(3).click(force=True)
app2.wait_for_timeout(500)
frame2.locator("#consultaRuta").fill("C:\\\\temp")
app2.wait_for_timeout(300)
capturar_paso(app2, "modo_excel_sin_nombre", paso_excel=1)

frame2.locator("button", has_text="Extraer").click(force=True)
app2.wait_for_timeout(1500)
texto_pantalla = frame2.locator("body").inner_text()
assert "Debe indicar el nombre del archivo a generar" in texto_pantalla, f"Se esperaba el mensaje de validacion: {texto_pantalla[-300:]!r}"
capturar_paso(app2, "extraccion_rechazada_sin_nombre", paso_excel=2)
'''

CUERPOS_REALES["CP039"] = '''
app, frame = abrir_consulta_base_semestral_directo(page, paso_excel=1)
texto_pantalla = frame.locator("body").inner_text()
assert "fijado" not in texto_pantalla.lower(), f"No deberia aparecer el aviso de semestre fijado al entrar por el recurso de menu: {texto_pantalla[:300]!r}"
combo_semestre = frame.locator("#consultaSemestre")
assert not combo_semestre.evaluate("el => el.classList.contains(\\'ant-select-disabled\\')"), "El combo de Semestre no deberia llegar bloqueado al entrar por el recurso de menu"
valor_semestre = combo_semestre.inner_text().strip()
assert valor_semestre, "El combo de Semestre deberia quedar posicionado en un semestre del catalogo al ingresar"
capturar_paso(app, "combo_semestre_posicionado", paso_excel=2)

combo_semestre.click(force=True)
app.wait_for_timeout(1000)
opciones_catalogo = frame.locator("nz-option-item").count()
assert opciones_catalogo > 1, f"Se esperaba el catalogo completo de semestres en el combo, se vieron {opciones_catalogo} opciones"
frame.locator("body").press("Escape")
app.wait_for_timeout(300)
descripcion = frame.locator("#consultaDescripcion").input_value()
assert descripcion.strip(), "La Descripcion deberia mostrar la del semestre elegido"
capturar_paso(app, "catalogo_cargado_y_descripcion", paso_excel=3)

boton_extraer = frame.get_by_role("button", name=re.compile("Extraer", re.I))
assert boton_extraer.is_enabled(), "El boton Extraer... deberia quedar habilitado"
capturar_paso(app, "extraer_habilitado", paso_excel=4)
'''

CUERPOS_REALES["CP040"] = '''
app, frame = abrir_consulta_base_semestral_directo(page, paso_excel=1)
texto_pantalla = frame.locator("body").inner_text()
assert "fijado" not in texto_pantalla.lower(), f"No deberia aparecer el aviso de semestre fijado al entrar por el recurso de menu: {texto_pantalla[:300]!r}"
combo_semestre = frame.locator("#consultaSemestre")
assert not combo_semestre.evaluate("el => el.classList.contains(\\'ant-select-disabled\\')"), "El combo de Semestre deberia estar habilitado (no bloqueado) al entrar por el recurso de menu"
capturar_paso(app, "combo_habilitado_sin_aviso_fijado", paso_excel=2)

seleccionar_semestre_consulta(app, frame, "2008- S1")
capturar_paso(app, "antes_de_verificar_cambio", paso_excel=3)
valor_combo = combo_semestre.inner_text().strip()
assert "2008" in valor_combo and "S1" in valor_combo.replace(" ", ""), f"El combo deberia reflejar el semestre elegido: {valor_combo!r}"
descripcion = frame.locator("#consultaDescripcion").input_value()
assert descripcion.strip(), "La Descripcion deberia reflejar el semestre elegido"
capturar_paso(app, "combo_y_descripcion_reflejan_el_cambio", paso_excel=4)
'''

CUERPOS_REALES["CP041"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2009- S2")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
texto_pantalla = frame2.locator("body").inner_text()
assert "Semestre fijado al abrir esta consulta desde" in texto_pantalla, f"Se esperaba el aviso de semestre fijado: {texto_pantalla[:500]!r}"
capturar_paso(app2, "consulta_abierta_con_semestre_fijado", paso_excel=1)
'''

CUERPOS_REALES["CP042"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S1")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(3).click(force=True)
app2.wait_for_timeout(500)
frame2.locator("#consultaNombreArchivo").fill("QA_CP042_s9")
app2.wait_for_timeout(500)
capturar_paso(app2, "modo_excel_con_nombre", paso_excel=2)

frame2.locator("button", has_text="Extraer").click(force=True)
app2.wait_for_timeout(1000)
texto_confirma = frame2.locator("*", has_text="¿Desea continuar?").last.inner_text()
assert "Se extraerá la base semestral a Excel" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
with app2.expect_download(timeout=15000) as descarga_info:
    frame2.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
descarga = descarga_info.value
assert descarga.suggested_filename == "QA_CP042_s9.xlsx", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
descarga.save_as(EVIDENCIA / descarga.suggested_filename)
capturar_paso(app2, "excel_extraido", paso_excel=3)
'''

CUERPOS_REALES["CP043"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S2")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(4).click(force=True)
app2.wait_for_timeout(500)
capturar_paso(app2, "modo_archivo_texto_sin_nombre", paso_excel=1)

frame2.locator("button", has_text="Extraer").click(force=True)
app2.wait_for_timeout(1000)
texto_confirma = frame2.locator("*", has_text="¿Desea continuar?").last.inner_text()
assert "archivo de texto" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"
with app2.expect_download(timeout=15000) as descarga_info:
    frame2.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
descarga = descarga_info.value
assert descarga.suggested_filename == "BaseSemestral.txt", f"Nombre de archivo inesperado: {descarga.suggested_filename!r}"
descarga.save_as(EVIDENCIA / descarga.suggested_filename)
capturar_paso(app2, "archivo_texto_extraido_sin_nombre", paso_excel=2)
'''

CUERPOS_REALES["CP044"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S1")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(4).click(force=True)
app2.wait_for_timeout(500)

capturas = []
app2.on("response", lambda r: capturas.append(r.url) if "/api/" in r.url else None)
with app2.expect_download(timeout=15000) as descarga_info:
    frame2.locator("button", has_text="Extraer").click(force=True)
    app2.wait_for_timeout(1000)
    frame2.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
descarga_control = descarga_info.value
descarga_control.save_as(EVIDENCIA / "control_fase_todas_tipo_todos.txt")
capturar_paso(app2, "extraccion_control_sin_filtros", paso_excel=1)

frame2.locator("#consultaFase").click(force=True)
app2.wait_for_timeout(800)
frame2.locator("nz-option-item", has_text=re.compile("Monof", re.I)).first.click(force=True)
app2.wait_for_timeout(500)
frame2.locator("#consultaTipoContraste").click(force=True)
app2.wait_for_timeout(800)
frame2.locator("nz-option-item", has_text=re.compile("Programado", re.I)).first.click(force=True)
app2.wait_for_timeout(500)
capturar_paso(app2, "filtros_fase_y_tipo_aplicados", paso_excel=2)

with app2.expect_download(timeout=15000) as descarga_info2:
    frame2.locator("button", has_text="Extraer").click(force=True)
    app2.wait_for_timeout(1000)
    frame2.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
descarga_filtrada = descarga_info2.value
ruta_filtrada = EVIDENCIA / "filtrado_monofasico_programado.txt"
descarga_filtrada.save_as(ruta_filtrada)
assert ruta_filtrada.stat().st_size > 0, "El archivo filtrado deberia tener contenido"
capturar_paso(app2, "extraccion_filtrada_generada", paso_excel=3)
'''

CUERPOS_REALES["CP045"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S1")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(4).click(force=True)
app2.wait_for_timeout(500)

opciones_filtro = ["Todos", "Solo los Contrastados", "Solo los Pendientes de Contrastación"]
for i, etiqueta in enumerate(opciones_filtro):
    frame2.locator("label", has_text=etiqueta).first.click(force=True)
    app2.wait_for_timeout(500)
    with app2.expect_download(timeout=15000) as descarga_info:
        frame2.locator("button", has_text="Extraer").click(force=True)
        app2.wait_for_timeout(1000)
        frame2.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
    descarga = descarga_info.value
    etiqueta_archivo = etiqueta[:10].replace(" ", "_")
    ruta_descarga = EVIDENCIA / f"filtro_estado_{i}_{etiqueta_archivo}.txt"
    descarga.save_as(ruta_descarga)
    assert ruta_descarga.stat().st_size > 0, f"El archivo con filtro {etiqueta!r} deberia tener contenido"
    capturar_paso(app2, f"extraccion_filtro_estado_{i}", paso_excel=1)
'''

CUERPOS_REALES["CP046"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2008- S1")
app2, frame2 = abrir_consulta_desde_detalles(app, frame)
frame2.locator("input[type='radio']").nth(3).click(force=True)
app2.wait_for_timeout(500)
frame2.locator("#consultaNombreArchivo").fill("QA_CP046_s9")
app2.wait_for_timeout(500)
capturar_paso(app2, "listo_para_extraer_antes_de_cancelar", paso_excel=1)

frame2.locator("button", has_text="Extraer").click(force=True)
app2.wait_for_timeout(1000)
texto_confirma = frame2.locator("*", has_text="¿Desea continuar?").last.inner_text()
assert "Se extraerá la base semestral a Excel" in texto_confirma, f"Dialogo de confirmacion inesperado: {texto_confirma!r}"

capturas = []
app2.on("response", lambda r: capturas.append(r.url) if "/api/" in r.url else None)
frame2.get_by_role("button", name=re.compile("Cancelar", re.I)).last.click(force=True)
app2.wait_for_timeout(2000)
assert len(capturas) == 0, f"No se esperaba ninguna llamada al backend tras Cancelar: {capturas!r}"
capturar_paso(app2, "extraccion_cancelada_sin_llamadas", paso_excel=2)
'''

CUERPOS_REALES["CP031"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2003- S2")
app.wait_for_timeout(2000)
texto_pantalla = frame.locator("body").inner_text()
assert "ya tiene medidores asociados" not in texto_pantalla, f"No se esperaba el aviso de medidores ya asignados: {texto_pantalla[:400]!r}"
radios = frame.locator("input[type='radio']")
assert not radios.nth(0).is_disabled(), "La opcion 'Cargar nueva base' deberia estar habilitada (semestre sin medidores previos)"
assert not radios.nth(1).is_disabled(), "La opcion 'Eliminar...' tambien deberia estar habilitada"
capturar_paso(app, "semestre_sin_medidores_previos", paso_excel=2)
'''

CUERPOS_REALES["CP033"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2003- S2")
app.wait_for_timeout(1500)

ruta_fixture = Path(__file__).resolve().parent / "documentos" / "input_rf05_cp033_incompletas.xlsx"
frame.locator("#archivoImportar").set_input_files(str(ruta_fixture))
app.wait_for_timeout(1500)
capturar_paso(app, "archivo_con_filas_incompletas_cargado", paso_excel=2)

boton_validar = frame.locator("button", has_text="Validar")
assert boton_validar.first.is_enabled(), "Validar deberia habilitarse tras cargar el archivo"
boton_validar.first.click(force=True)
app.wait_for_timeout(2500)

dlg = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("filas incompletas"))
assert dlg.count() and dlg.first.is_visible(), "No se vio el aviso de filas incompletas"
mensaje = dlg.first.inner_text()
assert "Se detectaron filas incompletas en el archivo" in mensaje and "Desea eliminarlas y obtener el archivo corregido" in mensaje, f"Mensaje inesperado: {mensaje!r}"
capturar_paso(app, "aviso_filas_incompletas", paso_excel=3)
dlg.first.get_by_role("button", name=re.compile("^Cancelar$", re.I)).evaluate("el => el.click()")
app.wait_for_timeout(1000)
'''

CUERPOS_REALES["CP034"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2003- S2")
app.wait_for_timeout(1500)

ruta_fixture = Path(__file__).resolve().parent / "documentos" / "input_rf05_cp034_equivalente.xlsx"
frame.locator("#archivoImportar").set_input_files(str(ruta_fixture))
app.wait_for_timeout(1500)
capturar_paso(app, "archivo_con_marca_equivalente_cargado", paso_excel=2)

boton_validar = frame.locator("button", has_text="Validar")
assert boton_validar.first.is_enabled(), "Validar deberia habilitarse tras cargar el archivo"
boton_validar.first.click(force=True)
app.wait_for_timeout(2500)

texto_resultado = frame.locator("body").inner_text()
assert "Detalle de Mensajes de Validaci" in texto_resultado, f"No se vio el panel de resultados de validacion: {texto_resultado[-600:]!r}"
assert re.search(r"MED\\[222057\\].*MAR OSI\\[FRT\\] OK", texto_resultado), f"El medidor con marca no exacta FRT->FRT deberia validar OK: {texto_resultado[-600:]!r}"
assert re.search(r"MED\\[1274566\\].*MAR OSI\\[OTR\\] OK", texto_resultado), f"El medidor con comodin OTR deberia validar OK: {texto_resultado[-600:]!r}"
capturar_paso(app, "medidores_marca_equivalente_validados_ok", paso_excel=3)
boton_cerrar = frame.get_by_role("button", name=re.compile("^Cancelar$", re.I)).last
if boton_cerrar.count():
    boton_cerrar.evaluate("el => el.click()")
    app.wait_for_timeout(800)
'''

CUERPOS_REALES["CP032"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2016- S1")
app.wait_for_timeout(2000)
texto_pantalla = frame.locator("body").inner_text()
assert "ya tiene medidores asociados" in texto_pantalla, f"Se esperaba el aviso de medidores ya asignados: {texto_pantalla[:400]!r}"
radios = frame.locator("input[type='radio']")
assert radios.nth(0).is_disabled(), "La opcion 'Cargar nueva base' deberia quedar deshabilitada (semestre con medidores ya asignados)"
assert radios.nth(1).is_checked(), "La opcion 'Eliminar...' deberia quedar fijada/marcada"
capturar_paso(app, "semestre_con_medidores_asignados_opcion_fijada", paso_excel=2)
'''

CUERPOS_REALES["CP035"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2025- S1")
app.wait_for_timeout(2000)
texto_pantalla = frame.locator("body").inner_text()
assert "ya tiene medidores asociados" in texto_pantalla, f"Se esperaba el aviso de medidores ya asignados (ruta optima previa): {texto_pantalla[:400]!r}"
radios = frame.locator("input[type='radio']")
assert radios.nth(0).is_disabled(), "La opcion 'Cargar nueva base' deberia quedar deshabilitada (ruta optima previa existente)"
assert radios.nth(1).is_checked(), "La opcion 'Eliminar...' deberia quedar fijada/marcada"
capturar_paso(app, "semestre_con_ruta_optima_previa", paso_excel=2)

# No hace falta cargar ningun archivo - "Procesar" reprocesa los medidores
# YA asociados al semestre (confirmado en vivo 13/11/2026 comparando con
# un video de referencia del desarrollador en Desarrollo).
boton_procesar = frame.locator("button", has_text="Procesar").first
assert boton_procesar.is_enabled(), "Procesar deberia estar habilitado sin necesidad de cargar un archivo"
boton_procesar.click()
app.wait_for_timeout(2000)
texto_confirmacion = frame.locator("body").inner_text()
assert "¿Desea continuar?" in texto_confirmacion, f"Se esperaba el dialogo de confirmacion de Procesar: {texto_confirmacion[-400:]!r}"
capturar_paso(app, "dialogo_confirmacion_procesar", paso_excel=3)

frame.get_by_role("button", name=re.compile("^Aceptar$", re.I)).last.click()
app.wait_for_timeout(2000)
texto_lanzado = frame.locator("body").inner_text()
assert "El proceso fue lanzado exitosamente" in texto_lanzado, f"Se esperaba el aviso de lanzamiento exitoso: {texto_lanzado[-400:]!r}"
capturar_paso(app, "proceso_lanzado_exitosamente", paso_excel=3)

# Confirmado con el desarrollador (13/11/2026, video CP005-validar.webm
# vs su propio video de Desarrollo): en Pruebas este proceso queda
# asincrono ("Proceso de seleccion lanzado en el servidor.") y no
# completa de inmediato como en Desarrollo (que termina sincronico con
# "Base semestral procesada") - el lanzamiento exitoso ES el resultado
# esperado para este caso en este ambiente, aceptado por el desarrollador.
frame.get_by_role("button", name=re.compile("^Aceptar$", re.I)).last.click()
app.wait_for_timeout(1000)
capturar_paso(app, "aviso_cerrado", paso_excel=4)
'''

CUERPOS_REALES["CP036"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2004- S1")
app.wait_for_timeout(1000)
capturar_paso(app, "semestre_sin_ruta_optima_antes_de_enviar", paso_excel=1)

frame.locator("button", has_text="Enviar a Osinerg").click(force=True)
app.wait_for_timeout(1000)
with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
    frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
assert resp_info.value.status == 400, f"Se esperaba 400 al enviar sin ruta optima ejecutada: {resp_info.value.status}"
app.wait_for_timeout(1000)
texto_pantalla = frame.locator("body").inner_text()
assert "Aún no ha ejecutado la ruta óptima" in texto_pantalla, f"Mensaje de rechazo inesperado: {texto_pantalla[-400:]!r}"
capturar_paso(app, "envio_rechazado_sin_ruta_optima", paso_excel=2)
'''

CUERPOS_REALES["CP037"] = '''
app, frame = abrir_base_semestral(page, paso_excel=1)
seleccionar_semestre(app, frame, "2007- S1")
app.wait_for_timeout(1000)
capturar_paso(app, "semestre_ya_enviado_antes_de_reenviar", paso_excel=1)

frame.locator("button", has_text="Enviar a Osinerg").click(force=True)
app.wait_for_timeout(1000)
with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
    frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
assert resp_info.value.status == 400, f"Se esperaba 400 al reenviar informacion ya enviada: {resp_info.value.status}"
app.wait_for_timeout(1000)
texto_pantalla = frame.locator("body").inner_text()
assert "Ya fue enviada la información a Osinerg" in texto_pantalla, f"Mensaje de rechazo inesperado: {texto_pantalla[-400:]!r}"
capturar_paso(app, "reenvio_rechazado", paso_excel=2)
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
