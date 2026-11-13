"""
encargos_proyectos.py - helpers y ficha tecnica para la pantalla
"Mantenimiento de Proyectos de Encargos" (RF-04 de PR000349-SP9, modulo
Encargos - submodulo Cobranza).

Componente Angular raiz: <app-proyecto>
Ruta de menu real: Aplicaciones > Comercial > "Mantenimiento De Proyectos
De Encargos" (directo bajo Comercial, sin categoria intermedia -
confirmado en vivo 10/11/2026).

Campos reales:
  #codigoEncargo    input de texto simple (NO es combo), hasta 4 digitos.
  (combo "Proyecto")   nz-select con scroll virtual - ver nota de abajo.
  #descripcion      input, habilitado para Ingresar/Modificar.
  #direccionAdicional input, habilitado para Ingresar/Modificar.
  Estado: texto de solo lectura (Activo/Eliminado/etc, sin id propio).

Gotcha real confirmado en vivo 10-11/11/2026: la pagina tiene DOS
elementos `input.ant-select-selection-search-input` (no uno solo) -
`.first` NO es el combo de "Proyecto" (es otro, probablemente oculto o
de otro control). Usar siempre `.nth(1)` para el combo real de
Proyecto. Las opciones vienen de `nz-option-item` una vez que
#codigoEncargo tiene un valor valido (dispara la carga de la lista de
proyectos de ese encargo) - no hace falta tipear para filtrar, basta
con abrir el combo y clickear la opcion visible (lista corta, 8
elementos para el encargo 0001 en la primera carga).

Boton "Leer": deshabilitado mientras #codigoEncargo este vacio - NO
depende de tener un Proyecto seleccionado para habilitarse (confirmado
en vivo: con solo el encargo lleno ya se habilita, igual al patron de
"Leer" de encargos_fonavi.py).

Gotcha real confirmado en vivo 10/11/2026 (CP030): tipear directamente
un codigo de encargo invalido en #codigoEncargo (reemplazando el valor,
con un Proyecto ya seleccionado antes) limpia AMBOS combos (Encargo Y
Proyecto vuelven a "Seleccione...") al perder el foco - no hace falta
ninguna accion adicional para que se dispare la limpieza.

Endpoint real confirmado: la consulta (boton "Leer") dispara un POST
a .../api/... (ver on('response') en consultar_proyecto) con body real:
{"codigoEncargo":"0001","codigoProyecto":"880390","descripcion":"A.H.PAMPL. ALTA  ST.VILLA AMP.F,G,H,I,K,",
"direccionAdicional":"SAN JUAN MIRAFLORES","estado":"Activo","modo":""}

Datos de prueba reutilizables (confirmados en vivo 10-11/11/2026,
visibles en el combo real de Proyecto bajo el encargo 0001 - NO se usa
el proyecto 880333 que trae la matriz original porque esta verificado
contra Desarrollo, no Pruebas, y no aparece en el combo real de
Pruebas; 880390 SI esta confirmado real y visible):
- Encargo 0001, Proyecto 880390: "A.H.PAMPL. ALTA ST.VILLA AMP.F,G,H,I,K,",
  direccion "SAN JUAN MIRAFLORES", estado Activo.
- Otros proyectos reales visibles bajo el mismo encargo 0001: 930001
  (C.P. SAN ANTONIO DE JICARMARCA), 930093, 930200, 930216, 930250,
  930271, 930292 (los primeros 8 que trae el combo sin filtrar).

Gotcha real confirmado en vivo 11/11/2026 (CP025/alta de proyecto
NUEVO): el combo "Proyecto" (`input.ant-select-selection-search-input`
.nth(1)) SOLO lista proyectos que YA EXISTEN - no permite tipear un
codigo libre para crear uno. El campo real para un codigo NUEVO es
`#codigoProyecto` (`<input type="text">` simple, DISTINTO del combo,
oculto/deshabilitado hasta clickear 'Ingresar / Modificar' la PRIMERA
vez sin nada seleccionado). Flujo real: llenar #codigoEncargo -> click
'Ingresar / Modificar' (revela #codigoProyecto) -> llenar
#codigoProyecto -> click 'Leer' (si no existe, estado pasa a "Nuevo" y
habilita Descripcion/Direccion Adicional) -> llenar esos 2 campos ->
click 'Ingresar / Modificar' de nuevo -> dialogo real de confirmacion.

Boton 'Ingresar / Modificar' (un SOLO boton con ese texto fijo, no
cambia segun el modo) puede reportar `is_enabled() == False` via
Playwright en varios momentos del flujo (ej. sin proyecto
seleccionado) pero el click con `force=True` SIEMPRE dispara su
handler igual (mismo patron ya visto en la pantalla de Comision de
Encargo de encargos_ordenpago.py) - no hace falta esperar a que
is_enabled() de True antes de clickear.

Dialogos de confirmacion reales (antes del POST, requieren Aceptar):
- Alta: "Se registrará el proyecto {proyecto} del encargo {encargo}.
  ¿Desea continuar?"
- Modificacion: "Se modificará el proyecto {proyecto} del encargo
  {encargo}. ¿Desea continuar?"
- Eliminacion (baja logica): "El proyecto {proyecto} del encargo
  {encargo} será eliminado lógicamente. ¿Desea continuar?"
Los 3 tienen Cancelar/Aceptar; solo Aceptar dispara el POST real.

Mensaje real confirmado en vivo 11/11/2026 (CP028, modificar un
proyecto eliminado por otro usuario DESPUES de haberlo leido activo):
HTTP 400, "El proyecto fue eliminado por otro usuario. Vuelva a
consultarlo." (distinto al texto de la matriz original, "El proyecto
está Eliminado...", pero la misma validacion real).
"""
import re


def abrir_proyectos_encargo(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Mantenimiento De Proyectos De
    Encargos' y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Proyectos De Encargos"], "app-proyecto", paso_excel=paso_excel)


def seleccionar_proyecto(frame, app, codigo_encargo, codigo_proyecto):
    """Llena #codigoEncargo y selecciona codigo_proyecto del combo real
    de Proyecto (el SEGUNDO buscador ant-select de la pagina - ver
    gotcha en la ficha tecnica del modulo). No clickea Leer.

    Gotcha real confirmado en vivo 11/11/2026 (CP028, proyecto 930001):
    el combo sin filtrar NO siempre lista los mismos ~8 proyectos (esta
    virtualizado, `cdk-virtual-scroll-viewport`) - un codigo real y
    vigente puede no estar en esa ventana inicial. Si la opcion no
    aparece sin filtrar, se tipea el codigo en el buscador para forzar
    el filtrado server-side/client-side antes de clickear."""
    frame.locator("#codigoEncargo").fill(str(codigo_encargo))
    buscador = frame.locator("input.ant-select-selection-search-input").nth(1)
    buscador.click(force=True)
    app.wait_for_timeout(1000)
    opcion = frame.locator("nz-option-item", has_text=str(codigo_proyecto))
    if not opcion.count():
        buscador.fill(str(codigo_proyecto))
        app.wait_for_timeout(1200)
    opcion.first.click(force=True)
    app.wait_for_timeout(1000)


def _click_hasta_confirmacion(app, frame, boton, intentos=6):
    """Clickea `boton` (force=True) hasta que aparezca el dialogo real
    de confirmacion ("...¿Desea continuar?") o se agoten los intentos.
    Gotcha real confirmado en vivo 11/11/2026 (CP025): el click que
    dispara el dialogo de 'Ingresar / Modificar' / 'Eliminar' a veces
    no registra su handler en el primer intento bajo slow_mo+video (el
    screenshot de error muestra el formulario completo y listo, pero
    sin ningun dialogo abierto) - a diferencia de otros botones de este
    proyecto, un solo click force=True no alcanza siempre."""
    dialogo = frame.locator("*", has_text="¿Desea continuar?").last
    for _ in range(intentos):
        if dialogo.count() and dialogo.is_visible():
            break
        boton.click(force=True)
        app.wait_for_timeout(1500)
    return dialogo.inner_text() if dialogo.count() and dialogo.is_visible() else ""


def consultar_proyecto(app, frame, codigo_encargo, codigo_proyecto):
    """Selecciona el encargo/proyecto y clickea 'Leer'. Devuelve el
    cuerpo real (dict) de la respuesta de la consulta."""
    seleccionar_proyecto(frame, app, codigo_encargo, codigo_proyecto)
    with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
        frame.locator("button", has_text="Leer").click(force=True)
    app.wait_for_timeout(1000)
    return resp_info.value.json()


def registrar_proyecto_nuevo(app, frame, codigo_encargo, codigo_proyecto, descripcion, direccion_adicional):
    """Da de alta un proyecto NUEVO (codigo_proyecto que todavia no
    existe en el encargo). Flujo real confirmado en vivo 11/11/2026:
    1) #codigoEncargo + click 'Ingresar / Modificar' (revela el campo
    de texto LIBRE #codigoProyecto, oculto detras del combo "Proyecto"
    que solo lista proyectos EXISTENTES). 2) llenar #codigoProyecto y
    clickear 'Leer' (confirma 'Nuevo' y habilita Descripcion/Direccion
    Adicional). 3) llenar esos 2 campos y clickear 'Ingresar /
    Modificar' de nuevo -> dialogo de confirmacion real "Se registrará
    el proyecto {proyecto} del encargo {encargo}. ¿Desea continuar?".
    Devuelve (texto_confirmacion, cuerpo_respuesta, mensaje_rechazo)."""
    frame.locator("#codigoEncargo").fill(str(codigo_encargo))
    app.wait_for_timeout(500)
    campo_codigo_proyecto = frame.locator("#codigoProyecto")
    boton_ingresar_inicial = frame.locator("button", has_text=re.compile("Ingresar|Modificar")).first
    for _ in range(6):
        if campo_codigo_proyecto.is_visible() and not campo_codigo_proyecto.is_disabled():
            break
        boton_ingresar_inicial.click(force=True)
        app.wait_for_timeout(1200)
    campo_codigo_proyecto.fill(str(codigo_proyecto))
    app.wait_for_timeout(500)
    frame.locator("button", has_text="Leer").click(force=True)
    app.wait_for_timeout(1500)

    frame.locator("#descripcion").fill(descripcion)
    frame.locator("#direccionAdicional").fill(direccion_adicional)
    app.wait_for_timeout(500)

    boton_accion = frame.locator("button", has_text=re.compile("Ingresar|Modificar")).first
    texto_confirmacion = _click_hasta_confirmacion(app, frame, boton_accion)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
    app.wait_for_timeout(1500)
    cuerpo = resp_info.value.json() if resp_info.value.status != 204 else {}

    mensaje = None
    texto_pantalla = frame.locator("body").inner_text()
    if "Ventana de Validación" in texto_pantalla:
        inicio = texto_pantalla.index("Ventana de Validación")
        mensaje = texto_pantalla[inicio:inicio + 400]
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
        app.wait_for_timeout(500)
    return texto_confirmacion, cuerpo, mensaje


def modificar_proyecto(app, frame, descripcion, direccion_adicional):
    """Para un proyecto YA LEIDO (ver consultar_proyecto): clickea
    'Ingresar / Modificar', completa Descripcion/Direccion Adicional,
    confirma el dialogo real "Se modificará el proyecto {proyecto} del
    encargo {encargo}. ¿Desea continuar?" y devuelve
    (texto_confirmacion, cuerpo_respuesta, mensaje_dialogo_final) -
    mensaje_dialogo_final es el texto de la 'Ventana de Validación' si
    el backend rechaza (ej. eliminado por otro usuario), o None si la
    modificacion fue exitosa."""
    frame.locator("button", has_text=re.compile("Ingresar|Modificar")).first.click(force=True)
    app.wait_for_timeout(1000)
    frame.locator("#descripcion").fill(descripcion)
    frame.locator("#direccionAdicional").fill(direccion_adicional)
    app.wait_for_timeout(500)

    boton_accion = frame.locator("button", has_text=re.compile("Ingresar|Modificar")).first
    texto_confirmacion = _click_hasta_confirmacion(app, frame, boton_accion)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
    app.wait_for_timeout(1500)
    cuerpo = resp_info.value.json() if resp_info.value.status != 204 else {}

    mensaje = None
    texto_pantalla = frame.locator("body").inner_text()
    if "Ventana de Validación" in texto_pantalla:
        inicio = texto_pantalla.index("Ventana de Validación")
        mensaje = texto_pantalla[inicio:inicio + 400]
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
        app.wait_for_timeout(500)
    return texto_confirmacion, cuerpo, mensaje


def eliminar_proyecto(app, frame):
    """Clickea 'Eliminar', confirma el dialogo real y devuelve
    (texto_confirmacion, cuerpo_respuesta)."""
    boton_eliminar = frame.locator("button", has_text="Eliminar")
    texto_confirmacion = _click_hasta_confirmacion(app, frame, boton_eliminar)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=10000) as resp_info:
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
    app.wait_for_timeout(1500)
    cuerpo = resp_info.value.json() if resp_info.value.status != 204 else {}
    return texto_confirmacion, cuerpo
