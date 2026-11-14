"""
CP012 - Generar orden de pago válida (folio y entregas emitidas)

RF: RF-02  |  CU: CU-02
Descripcion: Verificar que se genera la orden, se obtiene folio y las entregas quedan en estado emitida.
Precondiciones: Debe asignarse el rol funcional: EXPLCONC. Consulta previa en estado Procesada (CP008: encargo **`TMO`** —`0010`, TELEFONICA DEL PERU MOVILES, el encargo con comisión vigente que la pantalla sí ofrece— / oficina **`Todos`** / operador `Mayor o igual` + fecha del servidor) **sin automatismo pendiente** (la fila `LISPAGTDP` del CP011 debe estar retirada). **Bloque de folio embebido (canal Query.svc, keyBD `clientes`; base de datos técnica):** `-- PRECONDICIÓN (INSERT)` `INSERT INTO con_folios (con_empresa, con_sistema, con_documento, con_ano, con_mes, con_folio, con_pgm, con_fecha, con_folio2) VALUES ('7', 'TESO', 'ORDENP', YEAR(TODAY), MONTH(TODAY), 0, 'ORDPAG', CURRENT, 0);` · `-- SELECT DE VERIFICACIÓN` `SELECT con_ano, con_mes, con_folio FROM con_folios WHERE con_empresa = '7' AND con_sistema = 'TESO' AND con_documento = 'ORDENP' AND con_ano = YEAR(TODAY) AND con_mes = MONTH(TODAY);` → debe devolver **1 fila** con `con_folio = 0` (medido el 2026-10-16: **0 filas**; la tabla tiene filas hasta 2026/02 y ninguna del período del servidor) · `-- REVERSA` `DELETE FROM con_folios WHERE con_empresa = '7' AND con_sistema = 'TESO' AND con_documento = 'ORDENP' AND con_ano = YEAR(TODAY) AND con_mes = MONTH(TODAY);` → verificación 0 filas. **Alta previa (Tipo A, reversible) de la entrega Procesada del propio encargo `TMO`:** `INSERT INTO entrega_encargo (entrega, oficina, corr_operacion, fecha_recauda, fecha_entrega, rol_receptor, rol_usuario, importe, ruc, concepto, estado, rol_crea, fec_crea, cantidad, empresa) SELECT MAX(e.entrega) + 1, '0010', 1, TODAY, TODAY, 'QACPS9', 'QACPS9', 250.00, '20100017491', 'TMO', 'G', 'QACPS9', TODAY, 10, '7' FROM entrega_encargo e WHERE e.empresa = '7';` → **verificación:** `SELECT FIRST 5 entrega, oficina, importe, cantidad, concepto, estado, rol_crea FROM entrega_encargo WHERE empresa = '7' AND concepto = 'TMO' AND estado = 'G' AND rol_crea = 'QACPS9';` (esperado 1 fila; medido el 2026-10-15: entrega **19146**, importe 250.00, cantidad 10) · **reversa:** `DELETE FROM entrega_encargo WHERE empresa = '7' AND concepto = 'TMO' AND estado = 'G' AND rol_crea = 'QACPS9';` → verificación 0 filas. **Fotos previas obligatorias ANTES de generar — las dos del MISMO encargo `TMO`:** (a) de la entrega que el caso marca: `SELECT entrega, estado, importe, cantidad, monto_comision, corr_comision, rol_creord, fecha_orden_pago, ord_numero, estado_liquida, numero_orden_pago FROM entrega_encargo WHERE empresa = '7' AND concepto = 'TMO' AND estado = 'G' AND rol_crea = 'QACPS9';` (medido: los siete campos de la orden en NULL) · (b) de la comisión vigente: `SELECT corr_comision, ind_orden FROM enc_comision WHERE empresa = '7' AND codigo_encargo = '0010' ORDER BY corr_comision;` (medido el 2026-10-16: **corr 1 = `S`, corr 2 = `S`**; `ObtenerComisionVigente` toma el correlativo mayor, la **corr 2**). **Ejecución:** `POST <base ordpago>/OrdenPago/RegistrarOrdenPago` con `{"codigoEncargo":"TMO","codigosEntrega":[19146]}` → medido el 2026-10-15: **200** con `folio = "2026100001"`, `cantidadEntregas = 1`, `montoTotal = 170.00` (**neto**: 250.00 − 80.00 de comisión) y `bloqueado = false`. **Reversa obligatoria al terminar (Tipo B)** — la clave real de la orden es `ord_codigo = 'EC'` **+ `ord_interno` = folio** (⚠️ el folio **no** está en `ord_codigo`): `DELETE FROM tesore_ctaorden WHERE emp_codigo = '7' AND ord_codigo = 'EC' AND ord_interno = '<folio generado>';` · `DELETE FROM tesore_orden WHERE emp_codigo = '7' AND ord_codigo = 'EC' AND ord_interno = '<folio generado>';` · `UPDATE entrega_encargo SET estado = 'G', numero_orden_pago = NULL, ord_numero = NULL, fecha_orden_pago = NULL, estado_liquida = NULL, monto_comision = NULL, corr_comision = NULL, rol_creord = NULL WHERE empresa = '7' AND concepto = 'TMO' AND oficina = '0010' AND entrega IN (<la entrega del alta>);` · `UPDATE enc_comision SET ind_orden = <valor de la foto previa> WHERE empresa = '7' AND codigo_encargo = '0010' AND corr_comision = 2;` (con la foto medida el 2026-10-16 el `UPDATE` es **idempotente**: la corr 2 ya está en `S`) · `DELETE FROM con_folios WHERE con_empresa = '7' AND con_sistema = 'TESO' AND con_documento = 'ORDENP' AND con_ano = YEAR(TODAY) AND con_mes = MONTH(TODAY);`. **Verificación de la reversa:** la entrega vuelve a la foto previa, los dos `DELETE` dejan **0** filas por esa clave, la fila de `con_folios` del período a **0** y los **controles globales** de la empresa 7 vuelven a `tesore_orden` = 135.675 / `tesore_ctaorden` = 145.813 (medidos). Scripts del arnés que ejecutan los mismos bloques: `data/alta_CP012_con_folios_periodo_actual.sql` y `data/alta_CP016_entrega_procesada.sql`.
Datos: Encargo: **`TMO`** (`0010`, TELEFONICA DEL PERU MOVILES). Oficina: **`Todos`** (opción del combo; el backend la traduce a «sin filtro de oficina»). Estado: **`Procesada`**. Operador/Fecha: **`Mayor o igual`** + la **fecha del servidor** (la de `fecha_entrega` de la entrega del alta de la precondición; medido el 2026-10-15: `2026-10-15`). Entrega a marcar en la grilla: **19146** — es `MAX(entrega) + 1` (medido el 2026-10-19: el máximo de la empresa 7 es **19145**, de modo que la fila **no existe** y la crea el alta de la precondición; si el ambiente ya hubiera avanzado, la entrega es la que devuelve el `SELECT` de verificación)— (importe 250,00 · comisión 80,00 · entrega 170,00 · 10 transacciones). Comisión vigente del encargo, medida el 2026-10-16: `corr_comision = 2`, tipo `2` = monto por transacción, moneda `9`, valor `8,00`. El tipo de cambio del día **existe** (medido el 2026-10-19: `2026-10-19 · compra 3.423`), así que la consulta no pide confirmación. El bloque SQL de preparación, verificación y reversa está en la columna *Precondición*.
Resultado esperado: La orden queda generada con folio asignado y las entregas cambian a estado emitida.

Pasos a seguir:
1. Consultar órdenes en estado Procesada (CP008). 2. Presionar Generar Orden. 3. Confirmar.
"""
import os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

# Por defecto corre en segundo plano (headless), sin abrir ventana de
# Edge. Para verlo trabajar en pantalla (util para un tester que quiere
# mirar el caso paso a paso), fijar PR000349-SP9_HEADLESS=0 antes de correrlo.
HEADLESS = os.environ.get("PR000349-SP9_HEADLESS", "1") == "1"

# Con PR000349-SP9_VIDEO=1 se graba un video (.webm) de toda la ejecucion,
# ademas de las capturas por paso. Apagado por defecto (un video por caso
# pesa/tarda mas; para una corrida masiva mejor dejarlo apagado y prenderlo
# solo cuando haga falta revisar un caso en detalle).
GRABAR_VIDEO = os.environ.get("PR000349-SP9_VIDEO", "0") == "1"

# Con PR000349-SP9_WORD=0 se omite el Word de evidencia (por defecto SI se
# genera: cada CPxxx.py arma su propio .docx con sus capturas, sin
# depender de ningun otro archivo del proyecto -asi se puede copiar este
# archivo solo a otra maquina y sigue generando su evidencia completa-).
GRABAR_WORD = os.environ.get("PR000349-SP9_WORD", "1") == "1"

# Con PR000349-SP9_SLOWMO=<milisegundos> Playwright agrega esa pausa entre
# CADA accion (click, fill, etc.). Sirve sobre todo junto con
# PR000349-SP9_VIDEO=1: sin esto, un fill() llena el campo de golpe y en
# el video no alcanza a verse el cambio. 0 = sin pausa (default, no afecta
# la velocidad normal de la corrida).
try:
    SLOWMO = int(os.environ.get("PR000349-SP9_SLOWMO", "0"))
except ValueError:
    SLOWMO = 0

# Pausa (ms) que se agrega justo despues de dejar los datos listos en
# pantalla y ANTES del clic que dispara la accion (capturar_paso con una
# descripcion "antes_de_*", ej. "antes_de_buscar", "antes_de_aceptar"): sin
# esto, con fill() llenando los campos de golpe, el video pasa de campos
# vacios a clic casi en el mismo instante y no da tiempo a ver los datos ya
# cargados antes de que se dispare la busqueda/accion. Por defecto se activa
# solo si se esta grabando video (GRABAR_VIDEO); se puede ajustar o apagar
# a mano con PR000349-SP9_PAUSA_ANTES_CLIC=<ms> (0 = sin pausa).
try:
    PAUSA_ANTES_CLIC = int(os.environ.get("PR000349-SP9_PAUSA_ANTES_CLIC", "1200" if GRABAR_VIDEO else "0"))
except ValueError:
    PAUSA_ANTES_CLIC = 0


URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = 'DCABA_DW'
PASSWORD = 'Melquisedec_01'

CASO = "CP012"
EVIDENCIA = Path(__file__).resolve().parent / CASO
if EVIDENCIA.exists():
    shutil.rmtree(EVIDENCIA, ignore_errors=True)
EVIDENCIA.mkdir(parents=True, exist_ok=True)

NOMBRE_CASO = 'Generar orden de pago válida (folio y entregas emitidas)'
RF_CASO = 'RF-02'
CU_CASO = 'CU-02'
DESCRIPCION_CASO = 'Verificar que se genera la orden, se obtiene folio y las entregas quedan en estado emitida.'
RESULTADO_ESPERADO_CASO = 'La orden queda generada con folio asignado y las entregas cambian a estado emitida.'
PASOS_CASO = '1. Consultar órdenes en estado Procesada (CP008). 2. Presionar Generar Orden. 3. Confirmar.'

PASO_CONTADOR = {"n": 0}
CAPTURAS_POR_PASO_EXCEL = {}  # numero de paso del Excel (int) -> [nombres de archivo .png]
ULTIMA_CAPTURA = {"nombre": None}  # nombre del ultimo .png tomado (ver generar_word_evidencia)


def capturar_paso(objetivo, descripcion, paso_excel=None):
    """Guarda una captura de evidencia por CADA paso relevante del caso
    (no solo al final), numerada en orden dentro de la carpeta EVIDENCIA
    (una por CP). `objetivo` es la Page donde tomar la captura (page antes
    de abrir el popup, o app una vez abierto).

    `paso_excel` (opcional): numero del paso de la columna "Pasos a
    seguir" de la matriz Excel al que corresponde esta captura (ej. 3 si
    esta screenshot ilustra el paso "3. Ingresar codigo nuevo."). Si se
    pasa, generar_word_evidencia() (ver WORD_HELPERS_FULL) agrupa la
    imagen bajo el texto real de ESE paso en vez de una etiqueta tecnica
    derivada del nombre de archivo. Una captura puede repetir el mismo
    paso_excel que otra anterior (ej. 2 capturas para el mismo paso del
    Excel) - quedan ambas bajo el mismo encabezado, en orden.

    Si la descripcion empieza con "antes_de" (ej. "antes_de_buscar",
    "antes_de_aceptar", "antes_de_limpiar", "antes_de_cancelar") se agrega
    ademas PAUSA_ANTES_CLIC despues de la captura: son justo los pasos
    donde los datos ya quedaron cargados en pantalla y lo siguiente en el
    caso es un clic, asi que sin esta pausa el video pasa de "campos
    llenos" a "clic" casi en el mismo frame."""
    PASO_CONTADOR["n"] += 1
    nombre = f"{CASO}_{PASO_CONTADOR['n']:02d}_{descripcion}.png"
    objetivo.screenshot(path=str(EVIDENCIA / nombre), full_page=True)
    ULTIMA_CAPTURA["nombre"] = nombre
    if paso_excel is not None:
        CAPTURAS_POR_PASO_EXCEL.setdefault(paso_excel, []).append(nombre)
    if PAUSA_ANTES_CLIC and descripcion.startswith("antes_de"):
        objetivo.wait_for_timeout(PAUSA_ANTES_CLIC)


def login(page, reintentos=2, paso_excel=None):
    # `paso_excel` (opcional): numero del paso de "Pasos a seguir" del Excel
    # al que corresponde el login (ej. 1, si el Excel dedica un paso propio
    # a "Ingresar a la plataforma"). Sin esto, la captura de login siempre
    # cae en la seccion generica "Otras capturas" del Word de evidencia en
    # vez de agruparse bajo el paso real (ver generar_word_evidencia()).
    #
    # Varios campos del formulario de login se completan via JS de forma
    # asincrona tras cargar la pagina, en momentos distintos (confirmado en
    # exploracion en vivo):
    #   - #servidorWCF / #servidor: vacios al cargar, se llenan ~0.3-1.5s despues.
    #   - #Dominios (combo oculto de Dominio): arranca con 0 <option> y
    #     recien se puebla un poco DESPUES de que #servidor ya tiene valor.
    # Si se envia el login en esa ventana (Playwright llena el formulario
    # mucho mas rapido que un humano tecleando), el POST sale con el
    # dominio vacio y el backend responde con mensajes inconsistentes:
    # "Invalid URI: The hostname could not be parsed.", "No existe
    # dominio.", "Ud. no tiene acceso a la empresa." Por eso a mano nunca
    # pasa (tarda de sobra) y en la automatizacion sale intermitente. Se
    # espera a que AMBAS cosas esten listas antes de tocar el formulario -
    # pero incluso asi, a veces igual falla el primer intento (confirmado
    # en vivo en PR000325 el 10/09/2026: fallo 1ra vez con "Ud. no tiene
    # acceso a la empresa", OK reintentando), por eso se reintenta el
    # formulario completo hasta `reintentos` veces antes de rendirse.
    for intento in range(reintentos):
        page.goto(URL)
        page.wait_for_function("document.querySelector('#servidor')?.value", timeout=15000)
        page.wait_for_function("document.querySelector('#Dominios')?.options?.length > 0", timeout=15000)
        page.get_by_role("textbox", name="Usuario").click()
        page.get_by_role("textbox", name="Usuario").fill(USUARIO)
        page.get_by_role("textbox", name="Usuario").press("Tab")
        page.get_by_role("textbox", name="Contraseña").fill(PASSWORD)
        page.wait_for_timeout(1000)  # confirmado en vivo el 11/09/2026: dar 1s antes de Ingresar reduce el login fallido intermitente
        page.get_by_role("button", name="Ingresar ").click()
        page.wait_for_load_state("networkidle")
        if "Login" not in page.url:
            capturar_paso(page, "login", paso_excel=paso_excel)
            return
        print(f"  (aviso) login fallo (intento {intento + 1}/{reintentos}), reintentando..." if intento < reintentos - 1 else "  (aviso) login fallo en todos los intentos")
    capturar_paso(page, "login_fallo")
    raise RuntimeError(f"No se pudo iniciar sesion tras {reintentos} intento(s) (ver captura *_login_fallo.png).")


def _click_visible(page, text):
    """Clickea el enlace <a> VISIBLE cuyo texto sea EXACTAMENTE `text` (el
    menu lateral renderiza el arbol completo oculto; hay que filtrar
    visibles).

    Usa match EXACTO (regex ancla ^...$, insensible a espacios alrededor),
    no substring: `filter(has_text=text)` con un string hace substring
    case-insensitive, y el menu real tiene decenas de items cuyo texto
    CONTIENE la etiqueta buscada como substring ademas del item exacto (ej.
    PR000325: "Facturacion" tambien aparece dentro de "Calendario
    Facturacion", "Gestion Facturacion", "Liquidacion De Promedios Fuera De
    Proceso De Facturacion", etc.). Con substring, _click_visible podia
    clickear cualquiera de esos otros items en vez del nodo de menu
    correcto.

    Ademas recorre los candidatos en orden INVERSO (del ultimo al primero):
    incluso con match exacto, una ruta con la misma etiqueta repetida en 2
    niveles anidados (ej. PR000325 RF-05: Comercial > Facturacion >
    Facturacion > Mantenedor De Contratistas) deja AMBOS "Facturacion"
    visibles a la vez tras expandir el nivel 1 (el ancestro no se oculta
    solo porque se revelo su hijo), y el ancestro aparece ANTES en el DOM
    que el descendiente recien revelado. Devolver el primer visible volvia
    a clickear el mismo ancestro (colapsando el menu) en vez de bajar de
    nivel -bug real, confirmado en vivo: la ruta RF-05 nunca llegaba a
    revelar 'Mantenedor De Contratistas'."""
    patron = re.compile(r"^\s*" + re.escape(text) + r"\s*$")
    candidatos = page.locator("a").filter(has_text=patron)
    for i in reversed(range(candidatos.count())):
        candidato = candidatos.nth(i)
        if candidato.is_visible():
            candidato.click()
            return
    raise RuntimeError(f"No se encontro un enlace de menu visible con texto exacto: {text!r}")



def abrir_aplicacion(page, ruta_menu, selector_pantalla, timeout_menu=30000, timeout_pantalla=20000, paso_excel=None):
    """Navega Aplicaciones > ruta_menu[0] > ruta_menu[1] > ... (clic final
    que abre el POPUP de la aplicacion), y espera a que selector_pantalla
    (el componente Angular raiz de la pantalla, ej. "app-listado-de-x")
    este listo dentro del iframe #aplicacion del popup.

    Generalizacion de abrir_consulta_atenciones() (PR000335): la mecanica
    de navegacion -menu lateral con arbol oculto, popup con iframe
    #aplicacion- es la MISMA para cualquier aplicacion del portal Web LDS;
    lo unico que cambia por proyecto es la ruta de menus a clickear y el
    selector de la pantalla final. Ejemplo de uso (equivalente a PR000335):
        app, frame = abrir_aplicacion(
            page,
            ["Comercial", "Atencion Integral Al Cliente", "Consulta De Atenciones Comerciales"],
            "app-listado-de-atenciones",
        )
    Requiere _click_visible() y capturar_paso() ya definidos en el archivo.

    `paso_excel` (opcional): numero del paso de "Pasos a seguir" del Excel
    al que corresponde abrir la app (comun: el mismo paso 1 que cubre
    "entrar a la plataforma" + "entrar a la aplicacion" juntos, cuando el
    Excel no los separa). Sin esto, la captura "aplicacion_abierta" siempre
    cae en la seccion generica "Otras capturas" del Word de evidencia en
    vez de agruparse bajo el paso real - confirmado en vivo en PR000325
    (59 de 62 casos con esta seccion vacia de contenido util)."""
    page.get_by_role("link", name="  Aplicaciones").click(timeout=timeout_menu)
    page.wait_for_timeout(500)
    for texto in ruta_menu[:-1]:
        _click_visible(page, texto)
        page.wait_for_timeout(500)
    with page.expect_popup() as popup_info:
        _click_visible(page, ruta_menu[-1])
    app = popup_info.value
    app.wait_for_load_state("networkidle")
    frame = app.locator("#aplicacion").content_frame
    frame.locator(selector_pantalla).wait_for(timeout=timeout_pantalla)
    capturar_paso(app, "aplicacion_abierta", paso_excel=paso_excel)
    return app, frame


def esperar_fin_de_carga(app, pantalla, timeout_ms=45000):
    """Espera a que termine de cargar una busqueda/accion antes de seguir
    (y sobre todo, antes de tomar la captura de evidencia): el boton deja
    de decir 'Cargando...' y no queda actividad de red pendiente. Sin esto,
    la captura final a veces salia a medio cargar (spinner + boton
    'Cargando...' todavia visibles), como se detecto en la evidencia real
    de CP002."""
    try:
        pantalla.get_by_role("button", name="Cargando...").wait_for(state="hidden", timeout=timeout_ms)
    except PWTimeoutError:
        pass
    try:
        app.wait_for_load_state("networkidle", timeout=10000)
    except PWTimeoutError:
        pass
    # Espera adicional: algunas grillas (confirmado en vivo 08/10/2026,
    # PR000326-SP2 Asignacion/Reasignacion de Reclamos con cientos de
    # registros) usan un mat-spinner/mat-progress-spinner que ni el boton
    # 'Cargando...' ni networkidle detectan -el request ya respondio pero
    # el render de la grilla en pantalla sigue en curso varios segundos
    # mas, a veces 30s+-. Sin esto la captura/lectura caia a mitad de
    # render (grilla vacia pese a que la API ya habia devuelto datos
    # reales). Se espera activamente (hasta timeout_ms) a que el spinner
    # desaparezca; si la pantalla no usa este tipo de spinner (el caso mas
    # comun) is_visible() da False de entrada y esto no agrega demora.
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        try:
            spinner_visible = pantalla.locator("mat-spinner, mat-progress-spinner, .mat-spinner, .mat-progress-spinner, .app-loading-overlay, .app-loading-spinner, [role='progressbar']").first.is_visible()
        except Exception:
            spinner_visible = False
        if not spinner_visible:
            break
        app.wait_for_timeout(300)
    app.wait_for_timeout(500)



def esperar_animacion_estable(locator, timeout_ms=3000, intervalo_seg=0.15):
    """Espera a que un elemento deje de moverse/cambiar de tamaño (fin de
    una transicion/animacion CSS de entrada, ej. un modal apareciendo con
    fade+slide) comparando su bounding box en dos instantes seguidos.
    Sin esto, una captura tomada apenas el elemento se vuelve "visible"
    puede salir a medio animar (confirmado con evidencia real: el dialogo
    de Restriccion de Busqueda de CP001 salio descuadrado/fantasma)."""
    plazo = time.monotonic() + timeout_ms / 1000
    anterior = None
    estable = 0
    while time.monotonic() < plazo:
        try:
            actual = locator.bounding_box()
        except Exception:
            actual = None
        if actual is not None and actual == anterior:
            estable += 1
            if estable >= 2:
                return
        else:
            estable = 0
        anterior = actual
        locator.page.wait_for_timeout(int(intervalo_seg * 1000))



def seleccionar_primera_opcion(select_locator, timeout_ms=8000):
    """Selecciona la primera opcion real (distinta del placeholder
    '-- Seleccione --') de un <select>. Los combos del modal Filtro Avanzado
    cargan sus opciones de forma asincrona luego de abrirse (confirmado en
    exploracion en vivo: hasta ~3s), por lo que se espera activamente hasta
    timeout_ms antes de rendirse. Devuelve True si pudo seleccionar."""
    plazo = time.monotonic() + timeout_ms / 1000
    while True:
        valores = [v for v in select_locator.locator("option").evaluate_all("els => els.map(e => e.value)") if v]
        if valores:
            select_locator.select_option(value=valores[0])
            return True
        if time.monotonic() >= plazo:
            break
        select_locator.page.wait_for_timeout(300)
    print("  (aviso) el combo no tiene opciones cargadas; se omite la seleccion.")
    return False



def seleccionar_opcion_por_texto(select_locator, patron, timeout_ms=8000):
    """Selecciona la opcion de un <select> cuyo texto visible matchee
    `patron` (un re.Pattern, ej. re.compile("Simple", re.I)).

    OJO: select_option(label=patron) de Playwright NO acepta un re.Pattern
    -su parametro `label` solo admite str o lista de str-; pasarle un
    Pattern directamente compila pero falla recien en tiempo de ejecucion
    con `TypeError: 're.Pattern' object is not iterable` (confirmado en
    vivo: PR000325 CP022/CP023/CP024/CP031/CP032). Por eso se leen las
    opciones del DOM y se matchea el texto a mano antes de seleccionar por
    `value`. Los combos pueden cargar sus opciones de forma asincrona, por
    lo que se espera activamente hasta timeout_ms antes de rendirse."""
    plazo = time.monotonic() + timeout_ms / 1000
    while True:
        opciones = select_locator.locator("option").evaluate_all("els => els.map(e => ({value: e.value, texto: e.textContent}))")
        for o in opciones:
            if patron.search(o["texto"] or ""):
                select_locator.select_option(value=o["value"])
                return True
        if time.monotonic() >= plazo:
            break
        select_locator.page.wait_for_timeout(300)
    raise RuntimeError(f"No se encontro una opcion que matchee {patron.pattern!r} en el combo.")


def _renombrar_video(video, destino, intentos=8, espera_seg=0.5):
    """Mueve/renombra el .webm que graba Playwright (nombre hash) al nombre
    final del caso, y devuelve la ruta que quedo REALMENTE valida (destino
    si se pudo renombrar, o el nombre-hash original si no se pudo) -nunca
    None si el video existe- para que el caller pueda seguir usando ese
    video (union con ffmpeg o guardado directo) aunque el renombre fallara.

    En Windows el proceso de ffmpeg a veces suelta el archivo un instante
    despues de que .path() ya lo devuelve, asi que se reintenta un par de
    veces antes de avisar que no se pudo. BUG REAL confirmado en vivo
    (PR000325, CP001, 10/09/2026): cuando los 8 intentos (4s) no alcanzan
    -maquina bajo carga tras correr varios casos seguidos-, el codigo
    anterior devolvia None y el caller SOLO revisaba si el archivo con el
    nombre BONITO (destino) existia; como nunca se creo, el video de ESE
    lado (portal o app) se descartaba en silencio -el caso seguia dando
    [OK] pero el .webm final quedaba INCOMPLETO (solo la mitad de la
    grabacion), sin ningun aviso salvo un print facil de pasar por alto
    entre 62 casos. Ahora el caller usa la ruta que se devuelve aca
    (renombrada o no) para la union/guardado, asi el video sigue completo
    aunque el renombre en si haya fallado."""
    origen = Path(video.path())
    for intento in range(intentos):
        try:
            origen.replace(destino)
            return destino
        except (PermissionError, OSError):
            if intento == intentos - 1:
                print(f"  (aviso) no se pudo renombrar el video {origen.name} -> {destino.name} (se sigue usando con su nombre original para la union/guardado).")
                return origen
            time.sleep(espera_seg)


def _localizar_ffmpeg():
    """Ubica un ffmpeg CON SOPORTE PARA 'concat' (el demuxer que hace
    falta para unir portal+aplicacion en un solo .webm). Primero un
    ffmpeg "completo" instalado en el sistema (PATH); si no hay, prueba el
    ffmpeg minimo que Playwright ya descarga para grabar (`playwright
    install ffmpeg`) -pero ese build viene compilado con
    --disable-everything y solo habilita a mano image2pipe/matroska/webm,
    NUNCA concat (confirmado en vivo corriendo `ffmpeg -demuxers` sobre el
    binario real: no aparece en absoluto)-. Devuelve None si NINGUNO
    soporta concat, para que el caller se ahorre el intento (que si se
    hace igual, ffmpeg no falla con un error prolijo: crashea con un
    codigo de salida basura tipo 2880417800, dificil de diagnosticar en
    medio de una corrida de 60+ casos)."""
    def soporta_concat(ruta):
        try:
            r = subprocess.run([str(ruta), "-hide_banner", "-demuxers"], capture_output=True, text=True, timeout=10)
            return "concat" in r.stdout
        except Exception:
            return False

    de_sistema = shutil.which("ffmpeg")
    if de_sistema and soporta_concat(de_sistema):
        return Path(de_sistema)
    # Ffmpeg portable dedicado, instalado a mano en la raiz AUTOMATIZACION_LDS
    # (2 niveles arriba de cada CPxxx.py: AUTOMATIZACION_LDS\\PRxxxxxx\\CPxxx.py)
    # - con soporte concat completo, a diferencia del build minimo que trae
    # Playwright.
    raiz_automatizacion = Path(__file__).resolve().parent.parent
    for candidato_portable in (raiz_automatizacion / "ffmpeg" / "ffmpeg.exe", raiz_automatizacion / "ffmpeg" / "bin" / "ffmpeg.exe"):
        if candidato_portable.is_file() and soporta_concat(candidato_portable):
            return candidato_portable
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if base.is_dir():
        candidatos = sorted(base.glob("ffmpeg-*/ffmpeg-win64.exe"), reverse=True)
        if candidatos and soporta_concat(candidatos[0]):
            return candidatos[0]
    return None


def _unir_videos(destino, *videos, timeout_seg=60):
    """Concatena N .webm (portal + aplicacion + cualquier pagina extra
    que Playwright haya grabado, ej. una pestana efimera abierta
    durante una descarga) en un solo archivo con ffmpeg (stream copy,
    sin recodificar: todos comparten resolucion/codec porque los graba
    el mismo record_video_size). Si no encuentra un ffmpeg con soporte
    'concat' o falla la union, no toca los archivos originales y
    devuelve False para que el caller los deje como videos separados
    (ver _localizar_ffmpeg: en una maquina sin ffmpeg completo en el
    PATH, esto es la norma, no un error - instalar un ffmpeg "completo"
    y agregarlo al PATH si se quiere un solo .webm por caso).

    BUG REAL confirmado en vivo 22/09/2026 (PR000335-SP5, casos con
    descarga real via expect_download): Chromium a veces abre una
    pagina efimera adicional para servir la descarga, que Playwright
    graba igual (record_video_dir aplica a TODO el contexto) pero
    nunca queda referenciada por ninguna variable page/app del caller -
    por eso la firma acepta *videos en vez de exactamente 2, para que
    el caller pueda barrer y sumar cualquier page@*.webm huerfano que
    haya quedado en la carpeta de evidencia antes de llamar a esta
    funcion."""
    videos = [v for v in videos if v is not None]
    if len(videos) < 2:
        return False
    ffmpeg = _localizar_ffmpeg()
    if not ffmpeg:
        print("  (aviso) no hay un ffmpeg con soporte 'concat' disponible (el de Playwright no lo trae); quedan los videos separados. Instalar ffmpeg completo y agregarlo al PATH para unirlos en uno solo.")
        return False
    lista = destino.parent / f"{destino.stem}_lista.txt"
    lista.write_text("".join(f"file '{v.name}'\n" for v in videos), encoding="utf-8")
    try:
        resultado = subprocess.run(
            [str(ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(destino)],
            cwd=str(destino.parent),
            capture_output=True,
            text=True,
            timeout=timeout_seg,
        )
        if resultado.returncode == 0 and destino.exists():
            # La union en si ya funciono (destino existe y esta completo) -
            # la limpieza de los originales es best-effort: si Windows
            # todavia tiene el archivo bloqueado un instante despues de
            # browser.close(), NO se debe reportar la union como fallida
            # (bug real confirmado en vivo 17/09/2026: un WinError 32 aca
            # tapaba un merge exitoso con el aviso "no se pudieron unir").
            for video_origen in videos:
                for intento_borrado in range(14):
                    try:
                        video_origen.unlink(missing_ok=True)
                        break
                    except (PermissionError, OSError) as e:
                        if intento_borrado == 13:
                            print(f"  (aviso) la union de videos funciono, pero no se pudo borrar {video_origen.name}: {e}")
                        else:
                            time.sleep(0.5)
            return True
        print(f"  (aviso) no se pudieron unir los videos (ffmpeg devolvio {resultado.returncode}); quedan separados.")
        return False
    except Exception as e:
        print(f"  (aviso) no se pudieron unir los videos: {e}; quedan separados.")
        return False
    finally:
        lista.unlink(missing_ok=True)


#
# encargos_fonavi.py - helpers y ficha tecnica para la pantalla
# "Informacion FONAVI" (RF-01 de PR000349-SP9, modulo Encargos - submodulo
# Cobranza).
#
# Componente Angular raiz: <app-fonavi>
# Ruta de menu real: Aplicaciones > Comercial > "Informacion Fonavi"
# (aparece directo en el arbol de Comercial, sin categoria intermedia -
# confirmado en vivo 10/11/2026). Abre en popup con iframe #aplicacion,
# igual que cualquier otra app de Web LDS.
#
# Campos reales (solo 4 tienen id - el resto de la pantalla, Nombre,
# Direccion, Tipo de Cliente, Categoria, Sucursal, Distrito y los datos
# del proyecto/cuotas/importe/mora, son de solo lectura SIN id: no hay
# forma confiable de leerlos por selector, hay que verificar via la
# respuesta real de la API en vez del DOM):
#   #numeroCliente                input, placeholder "Ej. 10458231"
#   #digitoVerificador             input, 1 caracter
#   #numeroIdentidadRepresentante  input, solo se usa para emitir constancia
#   #nombreRepresentante           input, solo se usa para emitir constancia
#
# Botones: "Leer" (dispara la consulta), "Imprimir" (emite constancia,
# descarga archivo), "Cancelar" (limpia todo el formulario).
#
# Estados de habilitacion confirmados en vivo 10/11/2026:
# - "Leer": deshabilitado si #numeroCliente esta vacio - se habilita con
#   CUALQUIER valor en ese campo, sin necesitar el digito verificador
#   todavia (el DV solo se valida/usa al clickear Leer, no antes).
# - "Imprimir": deshabilitado hasta que #numeroIdentidadRepresentante Y
#   #nombreRepresentante tengan valor (ademas de haber consultado antes
#   con exito - sin una consulta previa el boton tampoco se habilita).
#
# Gotcha real confirmado en vivo 10/11/2026: la matriz dice "se dispara la
# consulta automaticamente" tras ingresar el digito verificador, pero en
# la pantalla real hace falta clickear el boton "Leer" explicitamente -
# un Tab o un Enter en #digitoVerificador NO dispara nada (0 llamadas de
# red capturadas en ninguno de los 2 casos). Siempre clickear "Leer"
# despues de llenar ambos campos, nunca asumir que el blur alcanza.
#
# Validacion del digito verificador: es 100% client-side (NUNCA llega a
# tocar la red si el DV no corresponde al algoritmo real del numero de
# cliente) - confirmado con el cliente 1006406 (DV real=6), probando con
# DV=5: 0 llamadas a la API, aparece directo la "Ventana de Validacion":
# "El dígito verificador no corresponde al N.° de Cliente ingresado." Los
# campos NO se limpian en este caso (a diferencia de un cliente sin
# registro FONAVI, que SI limpia #numeroCliente tras el error).
#
# Endpoints reales confirmados (API real del backend, no documentada en
# el EF):
#   .../api/fonavi/obtener-informacion-fonavi
#       Dispara al clickear "Leer" con ambos campos llenos y el DV
#       correcto. Body real exitoso (cliente CON registro FONAVI):
#       {"nombre":..., "direccion":..., "rutaLectura":..., "tipoCliente":...,
#       "categoria":..., "sucursal":..., "distrito":..., "numeroProyecto":...,
#       "nombreProyecto":..., "cuotas":N, "importe":N, "mora":N, "historial":[...]}
#       Body real SIN registro FONAVI (HTTP 200, no es un error de
#       transporte): {"sinDatos":true,"mensajeUsuario":"No existe datos
#       del FONAVI para el cliente."} - la pantalla lo muestra como
#       "Ventana de Validacion" igual que un error de verdad.
#   .../api/fonavi/exportar-constancia-fonavi
#       Dispara al clickear "Imprimir" con los datos del representante
#       completos. Descarga real confirmada: archivo de texto plano
#       "ConstanciaFonavi_<numeroCliente>.txt" con el texto formal de la
#       constancia (fecha, datos del cliente, proyecto, referencia al
#       Decreto Supremo N° 041-99-EF).
#
# Datos de prueba reutilizables (confirmados en vivo 10/11/2026, coinciden
# con lo que ya trae la matriz):
# - Cliente CON registro FONAVI: numero 1006406, DV 6 -> ALVAREZ LANCHIPA
#   NOLBERTO FERNANDO, sucursal "Pedro Miotta", Villa El Salvador, proyecto
#   880333 "A.H. V.SALV. VI ST. GPO. 1 (D.S.#Ol0)", 40 cuotas, importe
#   334.30, mora 15.22, historial vacio (0 constancias previas emitidas).
# - Cliente SIN registro FONAVI (para CP002): numero 1, DV 9 (NO usar
#   DV=0 - es un valor historico de una numeracion de cliente antigua, ya
#   invalido bajo el algoritmo de DV actual segun la propia nota de la
#   matriz v1.9).
#


def abrir_fonavi(app_o_page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Informacion Fonavi' y devuelve
    (app, frame) con el popup + iframe #aplicacion listos."""
    return abrir_aplicacion(app_o_page, ["Comercial", "Informacion Fonavi"], "app-fonavi", paso_excel=paso_excel)


def consultar_cliente_fonavi(app, frame, numero_cliente, digito_verificador):
    """Llena numeroCliente + digitoVerificador y clickea 'Leer'. Devuelve
    (datos, mensaje_dialogo):
    - Consulta valida con registro FONAVI: (dict real de la API, None).
    - Cliente sin registro FONAVI, o DV incorrecto (nunca toca la red):
      (None, texto real del dialogo de error, ya cerrado con Aceptar).

    Gotcha real confirmado en vivo 10/11/2026: con slow_mo+video activos
    (run_all.py real), un listener 'response' + wait_for_timeout fijo
    llega tarde la mayoria de las veces (la respuesta real demora mas de
    lo que tarda el wait bajo esas condiciones) - usar expect_response(),
    que espera de forma determinista en vez de adivinar un timeout, es
    el fix. El DV invalido NUNCA dispara el request (validacion
    client-side), asi que expect_response() se arma solo si hace falta."""
    frame.locator("#numeroCliente").fill(str(numero_cliente))
    frame.locator("#digitoVerificador").fill(str(digito_verificador))

    try:
        with app.expect_response(lambda r: "obtener-informacion-fonavi" in r.url, timeout=10000) as resp_info:
            frame.locator("button", has_text="Leer").click(force=True)
        cuerpo = resp_info.value.json()
    except PWTimeoutError:
        cuerpo = None

    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
    if dialogo.count() and dialogo.first.is_visible():
        mensaje = dialogo.first.inner_text()
        dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
        app.wait_for_timeout(500)
        return None, mensaje

    if cuerpo and not cuerpo.get("sinDatos"):
        # respiro: el estado disabled de Imprimir se recalcula un
        # instante despues de que la respuesta llega (confirmado en vivo
        # 10/11/2026 - sin esto, CP006 ve Imprimir todavia habilitado
        # por el frame anterior al cambio de deteccion de Angular).
        app.wait_for_timeout(1500)
        return cuerpo, None
    if cuerpo and cuerpo.get("sinDatos"):
        return None, cuerpo.get("mensajeUsuario")
    return None, None


def emitir_constancia_fonavi(app, frame, numero_identidad, nombre_representante):
    """Llena los datos del representante y clickea 'Imprimir'. Devuelve
    el objeto Download real de Playwright (espera la descarga real,
    hasta 10s)."""
    frame.locator("#numeroIdentidadRepresentante").fill(numero_identidad)
    frame.locator("#nombreRepresentante").fill(nombre_representante)
    boton = frame.locator("button", has_text="Imprimir")
    with app.expect_download(timeout=10000) as descarga_info:
        boton.click(force=True)
    return descarga_info.value


#
# encargos_proyectos.py - helpers y ficha tecnica para la pantalla
# "Mantenimiento de Proyectos de Encargos" (RF-04 de PR000349-SP9, modulo
# Encargos - submodulo Cobranza).
#
# Componente Angular raiz: <app-proyecto>
# Ruta de menu real: Aplicaciones > Comercial > "Mantenimiento De Proyectos
# De Encargos" (directo bajo Comercial, sin categoria intermedia -
# confirmado en vivo 10/11/2026).
#
# Campos reales:
#   #codigoEncargo    input de texto simple (NO es combo), hasta 4 digitos.
#   (combo "Proyecto")   nz-select con scroll virtual - ver nota de abajo.
#   #descripcion      input, habilitado para Ingresar/Modificar.
#   #direccionAdicional input, habilitado para Ingresar/Modificar.
#   Estado: texto de solo lectura (Activo/Eliminado/etc, sin id propio).
#
# Gotcha real confirmado en vivo 10-11/11/2026: la pagina tiene DOS
# elementos `input.ant-select-selection-search-input` (no uno solo) -
# `.first` NO es el combo de "Proyecto" (es otro, probablemente oculto o
# de otro control). Usar siempre `.nth(1)` para el combo real de
# Proyecto. Las opciones vienen de `nz-option-item` una vez que
# #codigoEncargo tiene un valor valido (dispara la carga de la lista de
# proyectos de ese encargo) - no hace falta tipear para filtrar, basta
# con abrir el combo y clickear la opcion visible (lista corta, 8
# elementos para el encargo 0001 en la primera carga).
#
# Boton "Leer": deshabilitado mientras #codigoEncargo este vacio - NO
# depende de tener un Proyecto seleccionado para habilitarse (confirmado
# en vivo: con solo el encargo lleno ya se habilita, igual al patron de
# "Leer" de encargos_fonavi.py).
#
# Gotcha real confirmado en vivo 10/11/2026 (CP030): tipear directamente
# un codigo de encargo invalido en #codigoEncargo (reemplazando el valor,
# con un Proyecto ya seleccionado antes) limpia AMBOS combos (Encargo Y
# Proyecto vuelven a "Seleccione...") al perder el foco - no hace falta
# ninguna accion adicional para que se dispare la limpieza.
#
# Endpoint real confirmado: la consulta (boton "Leer") dispara un POST
# a .../api/... (ver on('response') en consultar_proyecto) con body real:
# {"codigoEncargo":"0001","codigoProyecto":"880390","descripcion":"A.H.PAMPL. ALTA  ST.VILLA AMP.F,G,H,I,K,",
# "direccionAdicional":"SAN JUAN MIRAFLORES","estado":"Activo","modo":""}
#
# Datos de prueba reutilizables (confirmados en vivo 10-11/11/2026,
# visibles en el combo real de Proyecto bajo el encargo 0001 - NO se usa
# el proyecto 880333 que trae la matriz original porque esta verificado
# contra Desarrollo, no Pruebas, y no aparece en el combo real de
# Pruebas; 880390 SI esta confirmado real y visible):
# - Encargo 0001, Proyecto 880390: "A.H.PAMPL. ALTA ST.VILLA AMP.F,G,H,I,K,",
#   direccion "SAN JUAN MIRAFLORES", estado Activo.
# - Otros proyectos reales visibles bajo el mismo encargo 0001: 930001
#   (C.P. SAN ANTONIO DE JICARMARCA), 930093, 930200, 930216, 930250,
#   930271, 930292 (los primeros 8 que trae el combo sin filtrar).
#
# Gotcha real confirmado en vivo 11/11/2026 (CP025/alta de proyecto
# NUEVO): el combo "Proyecto" (`input.ant-select-selection-search-input`
# .nth(1)) SOLO lista proyectos que YA EXISTEN - no permite tipear un
# codigo libre para crear uno. El campo real para un codigo NUEVO es
# `#codigoProyecto` (`<input type="text">` simple, DISTINTO del combo,
# oculto/deshabilitado hasta clickear 'Ingresar / Modificar' la PRIMERA
# vez sin nada seleccionado). Flujo real: llenar #codigoEncargo -> click
# 'Ingresar / Modificar' (revela #codigoProyecto) -> llenar
# #codigoProyecto -> click 'Leer' (si no existe, estado pasa a "Nuevo" y
# habilita Descripcion/Direccion Adicional) -> llenar esos 2 campos ->
# click 'Ingresar / Modificar' de nuevo -> dialogo real de confirmacion.
#
# Boton 'Ingresar / Modificar' (un SOLO boton con ese texto fijo, no
# cambia segun el modo) puede reportar `is_enabled() == False` via
# Playwright en varios momentos del flujo (ej. sin proyecto
# seleccionado) pero el click con `force=True` SIEMPRE dispara su
# handler igual (mismo patron ya visto en la pantalla de Comision de
# Encargo de encargos_ordenpago.py) - no hace falta esperar a que
# is_enabled() de True antes de clickear.
#
# Dialogos de confirmacion reales (antes del POST, requieren Aceptar):
# - Alta: "Se registrará el proyecto {proyecto} del encargo {encargo}.
#   ¿Desea continuar?"
# - Modificacion: "Se modificará el proyecto {proyecto} del encargo
#   {encargo}. ¿Desea continuar?"
# - Eliminacion (baja logica): "El proyecto {proyecto} del encargo
#   {encargo} será eliminado lógicamente. ¿Desea continuar?"
# Los 3 tienen Cancelar/Aceptar; solo Aceptar dispara el POST real.
#
# Mensaje real confirmado en vivo 11/11/2026 (CP028, modificar un
# proyecto eliminado por otro usuario DESPUES de haberlo leido activo):
# HTTP 400, "El proyecto fue eliminado por otro usuario. Vuelva a
# consultarlo." (distinto al texto de la matriz original, "El proyecto
# está Eliminado...", pero la misma validacion real).
#


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


#
# encargos_ordenpago.py - helpers y ficha tecnica para la pantalla
# "Mantenedor de Orden de Pagos" (RF-02 de PR000349-SP9, modulo Encargos -
# submodulo Cobranza).
#
# Componente Angular raiz: <app-ordenpago>
# Ruta de menu real: Aplicaciones > Comercial > "Mantenedor De Orden De
# Pagos" (directo bajo Comercial, confirmado en vivo 11/11/2026).
#
# Campos reales:
#   3 nz-select (input.ant-select-selection-search-input, en este orden):
#     [0] #encargo        combo de "Encargo de Cobranza" (TMO, AON *, etc).
#     [1] #oficina        combo de "Oficina de Recaudacion" - SIEMPRE
#                          deshabilitado (ant-select-disabled) una vez
#                          elegido el encargo; el backend ya lo trata como
#                          "sin filtro de oficina" (coincide con la nota de
#                          la matriz "Todos -> sin filtro"), NO hace falta
#                          (ni se puede) clickearlo.
#     [2] #operadorFecha  combo del operador de "Fecha Inicio" (Igual a /
#                          Menor o igual / Mayor o igual / Entre).
#   input[name='estadoOrdenPago'] (radio x3): Procesada / Generada / Liquidar.
#   #fechaInicio          input type=date nativo.
#   Boton "Leer" dispara POST a .../ordpago/web/api/ordenpago/obtener-ordenes-pago.
#   Totales de la grilla (solo lectura, inputs con id):
#     #totalRecaudado, #totalComision, #totalEntrega, #totalCantidad.
#
# Gotcha real confirmado en vivo 11/11/2026: tras seleccionar el Encargo,
# el popup puede tardar en terminar de re-renderizar los 3 nz-select; si
# se intenta abrir cualquier combo antes de que `app-ordenpago` y el
# primer buscador ant-select esten listos (`wait_for` explicito), el
# conteo de buscadores puede salir en 0 de forma intermitente - no es un
# problema del combo de Oficina (ese SIEMPRE da 0 opciones porque esta
# deshabilitado a proposito, ver arriba).
#
# Datos de prueba reutilizables (confirmados en vivo 11/11/2026, CP008):
# Encargo TMO (TELEFONICA DEL PERU MOVILES) + estado Procesada + operador
# "Mayor o igual" + fechaInicio = fecha del dia -> con la fila de alta de
# precondicion (`entrega_encargo.estado='G'`, importe 250.00, cantidad 10,
# comision 8.00/transaccion) la grilla devuelve 1 fila y los totales
# 250,00 / 80,00 / 170,00 / 10 - exacto a lo que pide la matriz.
#
# Grilla de resultados: cada fila tiene un checkbox de seleccion (columna
# "Seleccion"); "Generar Orden" dispara primero un dialogo de
# confirmacion propio del front ("Se generara la Orden de Pago con N
# entrega(s) seleccionada(s). Desea continuar?") - DISTINTO del POST real
# a RegistrarOrdenPago, que recien se dispara al aceptar ese dialogo.
#
# Hallazgo real confirmado en vivo 11/11/2026 (CP011): con una fila en
# `control_proceso` (codigo='LISPAGTDP', estado='E') el POST a
# RegistrarOrdenPago responde 200 (no 4xx/5xx) con
# `{"folio":"","cantidadEntregas":0,"montoTotal":0,"bloqueado":true,
# "mensajeUsuario":"Existe algún proceso de automata de pagos externos
# pendiente, No se puede Generar orden."}` y aparece un dialogo de
# "Ventana de Validacion" con ese mismo mensaje - la entrega marcada NO
# se consume (sigue en estado 'G', reutilizable para el siguiente caso
# que la necesite, ej. CP012, sin volver a insertarla).
#
# Modo Liquidar (radio "Liquidar"): la grilla muestra ordenes ya
# generadas (estado_liquida='A'=GENERADO), cada una con checkbox propio.
# "Liquidar" abre un modal "Ingreso de EMIDOC" con campos reales:
# #ingemiRazonSocial, #ingemiProducto (ambos solo lectura), #ingemiMonto
# (precargado desde la comision real de la orden - NO editable salvo
# tipo de comision = 3), #ingemiTipoDocumento (nz-select: Boleta/Factura/
# etc), #ingemiFechaIngreso (date), #ingemiLibro, #ingemiNumeroDocumento.
#
# Gotchas reales confirmados en vivo 11/11/2026 (CP013/CP014):
# - Las ordenes HISTORICAS de TFI/TMO en Liquidar casi siempre tienen
#   comision 0 (monto_comision=0 en entrega_encargo) - con Monto de Pago
#   en 0,00 el front corta ANTES de llegar al backend con "Ventana de
#   Validacion: Monto a Liquidar debe ser mayor a cero". Para probar el
#   flujo real hace falta una orden con comision > 0 - la unica forma
#   confirmada de conseguirla en Pruebas es generar una fresca (mismo
#   ciclo de alta+Generar Orden que CP012, encargo TMO, comision 8.00/
#   transaccion -> 80.00 con 10 transacciones).
# - El rango valido de "N.° de Documento" depende del libro+proveedor
#   real de la orden, NO es el mismo numero para todos los encargos: con
#   TMO (RUC 20100017491, TELEFONICA DEL PERU S.A.A.) y Libro 001 el
#   rango real medido es "mayor a 4012 y menor a 5012" (el rango
#   20119-20169 que trae la matriz original era especifico del
#   encargo/proveedor YEL, que no es seleccionable en este ambiente -
#   ver abajo).
# - El periodo EMIDOC (con_periodos, sistema/modulo='EMIDOC') que esta
#   realmente ABIERTO en Pruebas varia con el tiempo: medido en vivo
#   11/11/2026 solo existe fila para 2026/01 (estado 'A'); cualquier otro
#   mes de 2026 (incluido el que media la matriz original, 2026/08) da
#   "Periodo no Existe." en vez de llegar al corte real por EMIDOC. Para
#   un periodo CERRADO (CP014) 2025/12 esta confirmado 'C' en vivo.
# - El encargo `YEL` (PRODUCTOS YEL, concepto YEL) que usaba la matriz
#   original para CP013/CP014 tiene `ind_vigente='N'` en Pruebas (
#   confirmado por SQL) y por eso NO aparece en el combo de Encargo de
#   Cobranza - mismo patron de desalineacion Desarrollo/Pruebas visto en
#   otros RF de este proyecto. TMO (vigente, con una orden fresca
#   generada) sirve como sustituto real y valido.
# - El mensaje real de bloqueo EMIDOC (B-01) es "No se puede registrar
#   el comprobante EMIDOC de liquidación: el contrato de emisión no está
#   especificado para este servicio. Comuníquese con el área de
#   Informática." (la matriz original citaba "...Área de Sistemas",
#   variante de redaccion del mismo mensaje).
#


def abrir_orden_pagos(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Mantenedor De Orden De Pagos'
    y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Comercial", "Mantenedor De Orden De Pagos"], "app-ordenpago", timeout_pantalla=35000, paso_excel=paso_excel)


def seleccionar_encargo(app, frame, nombre_encargo):
    """Selecciona un Encargo de Cobranza por su nombre visible y espera a
    que el estado de habilitado/deshabilitado del boton 'Leer' termine de
    asentarse (gotcha real confirmado en vivo 11/11/2026: leer
    is_enabled() del boton con menos de ~3s de espera tras elegir el
    encargo puede devolver el valor ANTERIOR, todavia no actualizado por
    Angular - aunque el click posterior con force=True si llega a
    funcionar incluso con una espera mas corta)."""
    frame.locator("app-ordenpago").wait_for(timeout=20000)
    buscadores = frame.locator("input.ant-select-selection-search-input")
    buscadores.first.wait_for(timeout=20000)
    opcion = frame.locator("nz-option-item", has_text=nombre_encargo)
    for _ in range(10):
        buscadores.nth(0).click(force=True)
        app.wait_for_timeout(1000)
        if opcion.count():
            break
    opcion.first.click(force=True)
    try:
        app.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    app.wait_for_timeout(4500)


def consultar_ordenes_pago(app, frame, nombre_encargo, estado, operador_fecha, fecha_inicio):
    """Selecciona Encargo (por nombre visible en el combo), el radio de
    Estado, el operador de Fecha Inicio y la fecha, y clickea 'Leer'.
    La Oficina NO se toca (ver ficha tecnica: siempre deshabilitada,
    efectivamente "Todos"/sin filtro). Devuelve el cuerpo real (dict)
    de la respuesta de la consulta."""
    seleccionar_encargo(app, frame, nombre_encargo)
    buscadores = frame.locator("input.ant-select-selection-search-input")

    frame.locator("label", has_text=estado).first.click(force=True)
    app.wait_for_timeout(500)

    buscadores.nth(2).click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=operador_fecha).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#fechaInicio").fill(fecha_inicio)
    app.wait_for_timeout(500)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=15000) as resp_info:
        frame.locator("button", has_text="Leer").click(force=True)
    app.wait_for_timeout(1500)
    return resp_info.value.json()


def marcar_entregas_y_generar(app, frame):
    """Marca TODAS las entregas visibles en la grilla (checkbox) y
    clickea 'Generar Orden', confirmando el dialogo de 'Se generara la
    Orden de Pago...'. Devuelve el cuerpo real (dict) de la respuesta de
    RegistrarOrdenPago (con bloqueado=True/False segun corresponda)."""
    checks = frame.locator("table input[type='checkbox'], .ant-table-tbody input[type='checkbox']")
    for i in range(checks.count()):
        checks.nth(i).click(force=True)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Generar Orden").click(force=True)
    app.wait_for_timeout(1000)
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text="Se generará la Orden de Pago")
    with app.expect_response(lambda r: "/api/" in r.url, timeout=15000) as resp_info:
        dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(1500)
    cuerpo = resp_info.value.json()

    dialogo_final = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación|Validacion"))
    mensaje = None
    if dialogo_final.count() and dialogo_final.first.is_visible():
        mensaje = dialogo_final.first.inner_text()
        dialogo_final.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
        app.wait_for_timeout(500)
    return cuerpo, mensaje


def liquidar_con_emidoc(app, frame, tipo_documento, fecha_ingreso, libro, numero_documento):
    """Marca la PRIMERA entrega/orden visible en la grilla (modo
    Liquidar) y clickea 'Liquidar', abriendo el modal 'Ingreso de
    EMIDOC'. Completa Tipo de Documento (nz-select #ingemiTipoDocumento),
    Fecha de Ingreso (#ingemiFechaIngreso), Libro (#ingemiLibro) y
    Documento (#ingemiNumeroDocumento), y clickea 'Aceptar'.

    Devuelve (monto_precargado, mensaje_dialogo): el valor real de
    '#ingemiMonto' ANTES de aceptar (para verificar que vino precargado
    de la orden, no editado a mano) y el texto del dialogo de
    'Ventana de Validacion' si aparece uno tras aceptar (None si no
    aparece ninguno - caso no confirmado aun en este proyecto).

    Gotcha real confirmado en vivo 11/11/2026: el dialogo de resultado
    (bloqueo/rechazo) NO usa la misma clase CSS que el de 'Generar
    Orden' (`.ant-modal, nz-modal-container` da 0 coincidencias aca) -
    se lee por texto plano de toda la pantalla en vez de un selector
    estructurado."""
    checks = frame.locator("table input[type='checkbox'], .ant-table-tbody input[type='checkbox']")
    checks.first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Liquidar").first.click(force=True)
    app.wait_for_timeout(2000)

    monto_precargado = frame.locator("#ingemiMonto").input_value()

    tipo_doc = frame.locator("#ingemiTipoDocumento")
    tipo_doc.click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=tipo_documento).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#ingemiFechaIngreso").fill(fecha_ingreso)
    frame.locator("#ingemiLibro").fill(libro)
    frame.locator("#ingemiNumeroDocumento").fill(numero_documento)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Aceptar").last.click(force=True)
    app.wait_for_timeout(2500)

    texto_pantalla = frame.locator("body").inner_text()
    mensaje = None
    if "Ventana de Validación" in texto_pantalla:
        inicio = texto_pantalla.index("Ventana de Validación")
        mensaje = texto_pantalla[inicio:inicio + 400]
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
        app.wait_for_timeout(500)
    return monto_precargado, mensaje


def exportar_a_excel(app, frame):
    """Clickea 'A Excel...' y devuelve el objeto Download real (sin
    guardarlo) - el caller decide donde guardarlo y como validar su
    contenido."""
    with app.expect_download(timeout=15000) as descarga_info:
        frame.locator("button", has_text="A Excel").click(force=True)
    return descarga_info.value


#
# encargos_cobranzaexterna.py - helpers y ficha tecnica para la pantalla
# "Consulta de Cobranza Externa" (RF-03 de PR000349-SP9, modulo Encargos -
# submodulo Cobranza).
#
# Componente Angular raiz: <app-cobranzaexterna>
# Ruta de menu real: Aplicaciones > Administrativo > "Consulta De
# Cobranza Externa" (bajo "Administrativo", NO "Comercial" - confirmado
# en vivo 11/11/2026, tras que el rol funcional AFILIACO fuera asignado a
# DCABA_DW; antes de eso la pantalla no aparecia en ningun menu).
#
# Campos reales:
#   3 nz-select (input.ant-select-selection-search-input), ORDEN REAL
#   (distinto del de Mantenedor de Orden de Pagos - NO asumir el mismo
#   orden entre pantallas):
#     [0] #operadorFecha  (Mayor o igual / Menor o igual / Igual a / Entre)
#     [1] #encargo        combo de "Encargo de Cobranza".
#     [2] #oficina        combo de "Oficina de Pago" - lista TODAS las
#                          oficinas del sistema (no solo las que tienen
#                          movimientos reales de pag_externo para el
#                          encargo elegido); incluye la opcion "Todas".
#   #fechaInicio / #fechaFin (type=date) - #fechaFin solo se habilita con
#   operador "Entre".
#   #totalTransacciones / #totalMonto (solo lectura).
#   Boton "Buscar" dispara POST a .../api/... con {resumen, detalle,
#   totalTransacciones, totalMonto}.
#
# Gotcha real confirmado en vivo 11/11/2026: la data de pag_externo que
# trae la matriz original (medida contra Desarrollo, encargo 0020 con
# solo 21 movimientos en areas 0400/0300) NO coincide con Pruebas - el
# mismo encargo 0020 en Pruebas tiene miles de movimientos reales
# repartidos en oficinas totalmente distintas (Grandes Clientes 11.487,
# Control Ventas 497) y su "Detalle por Producto" viene SIEMPRE VACIO
# ("La consulta no devolvió productos.") sin importar el rango de fechas
# - no es un bug, el backend simplemente no tiene desagregado por
# producto para ese encargo.
#
# Dataset real reutilizable (confirmado en vivo 11/11/2026, estable -
# son movimientos historicos, no datos que otras pruebas vayan a
# modificar): Encargo `0006` (FOCOS AHORRADORES OSRAM), Oficina `Todas`,
# Operador `Entre`, Fecha Inicio `2000-01-01`, Fecha Fin `2026-11-11` ->
# resumen con 8 oficinas (Chacarilla 540/11204, Miraflores 2375/41632,
# La República 1848/31598, Pedro Miotta 544/8718, San Juan 1082/17538,
# +3 mas) y detalle con 2 productos (Focos 16 w: 7427/89124.0, Focos 20
# W: 9217/121734.0); totalTransacciones=12433, totalMonto=210858. Al ser
# historico (nada en el proyecto escribe pag_externo), estos numeros son
# estables entre corridas.
#


def abrir_cobranza_externa(page, paso_excel=None):
    """Navega Aplicaciones > Administrativo > 'Consulta De Cobranza
    Externa' y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Administrativo", "Consulta De Cobranza Externa"], "app-cobranzaexterna", paso_excel=paso_excel)


def consultar_cobranza_externa(app, frame, codigo_encargo, oficina, operador_fecha, fecha_inicio, fecha_fin=None):
    """Selecciona Encargo (por codigo, ej. '0006'), Oficina (por texto
    visible, ej. 'Todas'), Operador de Fecha y la(s) fecha(s), y
    clickea 'Buscar'. Si operador_fecha es 'Entre', fecha_fin es
    obligatoria (se ignora si se pasa con otro operador). Devuelve el
    cuerpo real (dict) de la respuesta."""
    frame.locator("app-cobranzaexterna").wait_for(timeout=20000)
    frame.locator("#encargo").click(force=True)
    app.wait_for_timeout(1000)
    frame.locator("nz-option-item", has_text=codigo_encargo).first.click(force=True)
    app.wait_for_timeout(1500)

    frame.locator("#oficina").click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=re.compile(r"^\s*" + re.escape(oficina) + r"\s*$")).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#operadorFecha").click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=operador_fecha).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#fechaInicio").fill(fecha_inicio)
    if operador_fecha == "Entre" and fecha_fin:
        frame.locator("#fechaFin").fill(fecha_fin)
    app.wait_for_timeout(500)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=25000) as resp_info:
        frame.locator("button", has_text="Buscar").click(force=True)
    app.wait_for_timeout(1500)
    return resp_info.value.json()


#
# encargos_basesemestral.py - helpers y ficha tecnica para las 2 pantallas
# de Medidores de PR000349-SP9: RF-05 "Importacion de Base Semestral"
# (Base Semestral De Medidores) y RF-06 "Consulta de Base Semestral"
# (Consulta Y Extraccion De Base Semestral). Dominio Medidores, separado
# por completo del dominio Cobranza del resto del proyecto (tablas
# mm_base_semestral/mm_semestre/mm_ruta_optima_cab/osi_medid_marca_eq,
# BD tecnica `dbtecnica` para las ultimas dos).
#
# Roles reales: MM.ADMIN desbloquea AMBAS pantallas (confirmado en vivo
# 11/11/2026, tras asignarsele a DCABA_DW) - no hizo falta MM.CONSULT/
# MM.DIGITA/MM.ADM por separado para destrabar el menu.
#
# ### RF-05 - Importacion de Base Semestral
# Componente: <app-importacion-basesemestral> (+ <app-resultados-validacion>)
# Ruta de menu real: Aplicaciones > Comercial > "Base Semestral De
# Medidores" (directo bajo Comercial).
#
# Campos reales: nz-select #codigoSemestre (combo "Semestre de
# Contraste", READONLY - no se puede tipear para filtrar, solo
# seleccionar de la lista), #descripcionSemestre, #cantidadMedidores,
# #porcentajeMf, #porcentajeTf, #medidoresExistentes, #medidoresSeleccionados
# (todos solo lectura), input[type=file] #archivoImportar, nz-select
# #formatoArchivo, #cantidadMaximaAValidar, #filaInicio (number),
# #estadoProceso. Botones: "Detalles...", "Validar...", "Procesar",
# "Enviar a Osinerg en formato Excel...".
#
# Gotcha real confirmado en vivo 11/11/2026: el combo de semestre esta
# VIRTUALIZADO (`cdk-virtual-scroll-viewport`) y el buscador es
# `readonly` (no admite `.fill()` para filtrar) - solo se ve una ventana
# de ~16 opciones a la vez, ordenadas de mas reciente a mas antigua
# (2026-S2 primero). Para seleccionar un semestre que no esta en la
# ventana inicial hay que hacer scroll INCREMENTAL del viewport
# (`el.scrollTop += N`) hasta que la opcion aparezca - un salto directo a
# `scrollHeight` SALTEA entradas intermedias (confirmado: un salto
# directo no encontro 2016-S1, pero si el extremo 2003-S2).
#
# Hallazgo real (desalineacion Desarrollo/Pruebas, igual patron que
# otros RF de este proyecto): NINGUN semestre tiene 0 medidores en total
# en Pruebas (la condicion de "semestre sin medidores previos" que pide
# CP031 no se puede lograr por cantidad total) - la condicion real que
# el backend evalua es la cantidad con SEMANA DE CONTRASTE asignada
# (`mm_base_semestral.nro_semana IS NOT NULL`): el semestre 2016- S1 que
# trae la matriz original YA tiene medidores con semana asignada en
# Pruebas (bloquea la opcion de carga), mientras que 2003- S2 no tiene
# NINGUNO con semana asignada (los radios de Opcion de Carga quedan
# habilitados) - usar 2003- S2 como sustituto real de "semestre sin
# medidores previos".
#
# ### RF-06 - Consulta de Base Semestral (Consulta Y Extraccion De Base Semestral)
# Dos caminos de entrada reales:
# 1. **Desde "Detalles..." de RF-05** (boton en la pantalla de
#    Importacion): abre un popup SIN iframe (`#aplicacion` no existe -
#    el contenido carga directo en el body del popup) con el semestre ya
#    FIJADO (no editable) - mensaje real: 'Semestre fijado al abrir esta
#    consulta desde "Detalles..." de la Importación de Base Semestral:
#    para cambiarlo, selecciónelo en esa pantalla.'
# 2. **Por el recurso de menu propio** ("Consulta Y Extraccion De Base
#    Semestral", bajo Comercial): CORREGIDO por desarrollo 13/11/2026.
#    Hasta esa fecha estaba roto: el recurso de menu MMEXTRAE llamaba a
#    una URL con la carpeta de app equivocada (`.../medid/medid/
#    basesemcons/web/home//LanzarAplicativoDebug/`, 404 real del backend
#    -confirmado con bypass de CORS via route.fetch()+fulfill(), no era
#    un problema de headless ni de rol- la carpeta real desplegada
#    siempre fue `extracsemes`, no `basesemcons`). Confirmado en vivo
#    13/11/2026 tras el fix: LanzarAplicativoDebug y el endpoint
#    obtener-semestres-contraste responden 200, el iframe #aplicacion
#    SI aparece, y el combo #consultaSemestre llega SIN el aviso de
#    semestre fijado, editable (no disabled), posicionado en el primer
#    semestre del catalogo.
#
# Campos reales (pantalla de RF-06, confirmados por esta via 13/11/2026):
# #consultaSemestre (nz-select, igual de virtualizado que #codigoSemestre
# de RF-05 - ver seleccionar_semestre_consulta), #consultaDescripcion
# (solo lectura), #consultaFase, #consultaTipoContraste (nz-select),
# radios de Opcion de Filtro, #consultaRuta + "Seleccionar carpeta..."
# (modo Excel), #consultaNombreArchivo, radios Excel/Texto, botones
# "Extraer...", "Cancelar", "Ayuda".
#


def abrir_base_semestral(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Base Semestral De Medidores'
    (RF-05) y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Comercial", "Base Semestral De Medidores"], "app-importacion-basesemestral", paso_excel=paso_excel)


def abrir_consulta_base_semestral_directo(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Consulta Y Extraccion De Base
    Semestral' (RF-06, entrada directa por el recurso de menu MMEXTRAE,
    SIN pasar por RF-05/Detalles) y devuelve (app, frame) con el
    combo de Semestre editable (sin fijar). Requiere el fix de
    desarrollo del 13/11/2026 (ver ficha tecnica arriba) - antes de esa
    fecha esta entrada daba 404 real."""
    return abrir_aplicacion(page, ["Comercial", "Consulta Y Extraccion De Base Semestral"], "#consultaSemestre", paso_excel=paso_excel)


def seleccionar_semestre_consulta(app, frame, anno_sem_texto, max_scrolls=40, paso_scroll=150):
    """Igual que seleccionar_semestre() pero para el combo #consultaSemestre
    de RF-06 (entrada directa) - mismo patron virtualizado."""
    frame.locator("#consultaSemestre").click(force=True)
    app.wait_for_timeout(1000)
    opcion = frame.locator("nz-option-item", has_text=anno_sem_texto)
    if opcion.count():
        opcion.first.click(force=True)
        app.wait_for_timeout(1500)
        return
    viewport = frame.locator("cdk-virtual-scroll-viewport")
    viewport.first.evaluate("el => el.scrollTop = 0")
    app.wait_for_timeout(300)
    for _ in range(max_scrolls):
        if opcion.count():
            break
        viewport.first.evaluate(f"el => el.scrollTop += {paso_scroll}")
        app.wait_for_timeout(250)
    assert opcion.count(), f"No se encontro el semestre {anno_sem_texto!r} en el combo (ni visible ni tras scroll)"
    opcion.first.click(force=True)
    app.wait_for_timeout(1500)


def seleccionar_semestre(app, frame, anno_sem_texto, max_scrolls=40, paso_scroll=150):
    """Selecciona un semestre del combo #codigoSemestre (ej. '2003- S2').
    El combo esta virtualizado y es readonly (no se puede tipear para
    filtrar) - hace scroll incremental del viewport hasta encontrar la
    opcion, o usa las ~16 que ya estan visibles sin scrollear."""
    frame.locator("#codigoSemestre").click(force=True)
    app.wait_for_timeout(1000)
    opcion = frame.locator("nz-option-item", has_text=anno_sem_texto)
    if opcion.count():
        opcion.first.click(force=True)
        app.wait_for_timeout(1500)
        return
    viewport = frame.locator("cdk-virtual-scroll-viewport")
    viewport.first.evaluate("el => el.scrollTop = 0")
    app.wait_for_timeout(300)
    for _ in range(max_scrolls):
        if opcion.count():
            break
        viewport.first.evaluate(f"el => el.scrollTop += {paso_scroll}")
        app.wait_for_timeout(250)
    assert opcion.count(), f"No se encontro el semestre {anno_sem_texto!r} en el combo (ni visible ni tras scroll)"
    opcion.first.click(force=True)
    app.wait_for_timeout(1500)


def abrir_consulta_desde_detalles(app, frame):
    """Clickea 'Detalles...' en la pantalla de RF-05 (con un semestre ya
    seleccionado) y devuelve (app2, frame2) de la pantalla de Consulta
    de Base Semestral (RF-06) con el semestre fijado. OJO: esta
    pantalla NO usa iframe #aplicacion - frame2 es directamente la
    Page del popup."""
    with app.expect_popup(timeout=15000) as popup_info:
        frame.locator("button", has_text="Detalles").click(force=True)
    app2 = popup_info.value
    app2.wait_for_load_state("networkidle")
    app2.wait_for_timeout(3000)
    return app2, app2


_EMU_POR_PULGADA = 914400
_ANCHO_MAX_PULGADAS = 6.3


def _tamano_png(ruta):
    """Lee ancho/alto (px) del header IHDR de un PNG, sin depender de Pillow."""
    with open(ruta, "rb") as f:
        data = f.read(33)
    ancho, alto = struct.unpack(">II", data[16:24])
    return ancho, alto


def _calcular_extent_emu(ancho_px, alto_px, dpi=96):
    ancho_in = ancho_px / dpi
    alto_in = alto_px / dpi
    if ancho_in > _ANCHO_MAX_PULGADAS:
        factor = _ANCHO_MAX_PULGADAS / ancho_in
        ancho_in *= factor
        alto_in *= factor
    return int(ancho_in * _EMU_POR_PULGADA), int(alto_in * _EMU_POR_PULGADA)


def _etiqueta_paso_png(ruta_png):
    """'CP002_03_antes_de_buscar.png' -> 'Paso 3: antes de buscar'."""
    base = ruta_png.stem
    resto = base[len(CASO) + 1:] if base.startswith(CASO + "_") else base
    m = re.match(r"^(\d{2})_(.+)$", resto)
    if m:
        numero, desc = m.groups()
        return f"Paso {int(numero)}: {desc.replace('_', ' ')}"
    if resto == "error":
        return "Captura de error"
    return resto.replace("_", " ")


_DOCX_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_DOCX_RELS_RAIZ = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)

_DOCX_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)


def _docx_parrafo(texto, estilo=None):
    pPr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
    return f'<w:p>{pPr}<w:r><w:t xml:space="preserve">{_escape_xml(texto)}</w:t></w:r></w:p>'


def _docx_parrafo_imagen(indice, rid, nombre_media, cx, cy):
    return (
        "<w:p><w:r><w:drawing>"
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{indice}" name="{_escape_xml(nombre_media)}"/>'
        "<a:graphic><a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">"
        "<pic:pic>"
        f'<pic:nvPicPr><pic:cNvPr id="{indice}" name="{_escape_xml(nombre_media)}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )


def _parsear_pasos_excel(texto_pasos):
    """"1. Ingresar codigo nuevo.\n2. Presionar Leer." -> {1: "1. Ingresar
    codigo nuevo.", 2: "2. Presionar Leer."} - conserva la linea completa
    (con el numero) como texto del encabezado, solo la indexa por numero."""
    pasos = {}
    for linea in texto_pasos.splitlines():
        linea = linea.strip()
        m = re.match(r"^(\d+)\.\s*.+$", linea)
        if m:
            pasos[int(m.group(1))] = linea
    return pasos


def generar_word_evidencia():
    """Arma CASO_evidencia.docx con todas las capturas .png que ya existen
    en EVIDENCIA. No depende de python-docx/lxml (arma el .docx a mano con
    zipfile, libreria estandar) ni de ningun otro archivo del proyecto.
    Pensado para revision FUNCIONAL (no tecnica): cada captura se agrupa
    bajo el texto REAL del paso de la matriz Excel al que corresponde
    (via CAPTURAS_POR_PASO_EXCEL, poblado por capturar_paso(...,
    paso_excel=N) - ver CAPTURAR_PASO_CODE), en vez de listar el texto de
    "Pasos a seguir" aparte y las capturas con una etiqueta tecnica
    derivada del nombre de archivo. La ULTIMA captura tomada en el caso (ULTIMA_CAPTURA, actualizada por
    capturar_paso() en cada llamada) se excluye SIEMPRE de su grupo por
    paso numerico y se coloca junto a "Resultado esperado" al final del
    documento, para que quien revisa el Word vea de forma inequivoca la
    imagen que valida el resultado esperado. Las capturas sin
    paso_excel asignado (no deberian existir si cada capturar_paso()
    del caso pasa ese parametro) se incluyen igual, con su etiqueta
    tecnica de siempre, sin agruparlas bajo un encabezado generico."""
    pngs = sorted(EVIDENCIA.glob("*.png"))
    if not pngs:
        return
    rels = []
    medias = []
    cuerpo = [_docx_parrafo(f"{CASO} - {NOMBRE_CASO}", "Title")]
    cuerpo.append(_docx_parrafo(f"RF: {RF_CASO}  |  CU: {CU_CASO}"))
    cuerpo.append(_docx_parrafo(f"Descripcion: {DESCRIPCION_CASO}"))

    contador_imagen = [0]

    def agregar_imagen(ruta_png):
        contador_imagen[0] += 1
        i = contador_imagen[0]
        ancho_px, alto_px = _tamano_png(ruta_png)
        cx, cy = _calcular_extent_emu(ancho_px, alto_px)
        rid = f"rId{i + 1}"
        nombre_media = f"image{i}.png"
        rels.append(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{nombre_media}"/>'
        )
        medias.append((f"word/media/{nombre_media}", ruta_png))
        cuerpo.append(_docx_parrafo_imagen(i, rid, nombre_media, cx, cy))

    pngs_por_nombre = {p.name: p for p in pngs}
    usados = set()
    nombre_ultima = ULTIMA_CAPTURA.get("nombre")

    if CAPTURAS_POR_PASO_EXCEL:
        textos_paso = _parsear_pasos_excel(PASOS_CASO)
        for numero in sorted(CAPTURAS_POR_PASO_EXCEL):
            nombres_paso = [n for n in CAPTURAS_POR_PASO_EXCEL[numero] if n != nombre_ultima]
            if not nombres_paso:
                continue
            cuerpo.append(_docx_parrafo(textos_paso.get(numero, f"Paso {numero}"), "Heading2"))
            for nombre_archivo in nombres_paso:
                ruta_png = pngs_por_nombre.get(nombre_archivo)
                if ruta_png is not None:
                    agregar_imagen(ruta_png)
                    usados.add(nombre_archivo)

    pngs_restantes = [p for p in pngs if p.name not in usados and p.name != nombre_ultima and not p.name.endswith("_error.png")]
    for ruta_png in pngs_restantes:
        cuerpo.append(_docx_parrafo(_etiqueta_paso_png(ruta_png), "Heading2"))
        agregar_imagen(ruta_png)
        usados.add(ruta_png.name)

    cuerpo.append(_docx_parrafo("Resultado esperado:", "Heading2"))
    if nombre_ultima:
        ruta_ultima = pngs_por_nombre.get(nombre_ultima)
        if ruta_ultima is not None:
            agregar_imagen(ruta_ultima)
    cuerpo.append(_docx_parrafo(RESULTADO_ESPERADO_CASO))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {_DOCX_NS}><w:body>"
        + "".join(cuerpo)
        + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>"
    )
    document_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels)
        + "</Relationships>"
    )

    destino = EVIDENCIA / f"{CASO}_evidencia.docx"
    try:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _DOCX_CONTENT_TYPES)
            z.writestr("_rels/.rels", _DOCX_RELS_RAIZ)
            z.writestr("word/document.xml", document_xml)
            z.writestr("word/_rels/document.xml.rels", document_rels)
            for nombre_interno, ruta_png in medias:
                z.write(ruta_png, nombre_interno)
        print(f"  Word de evidencia: {destino.name} ({len(pngs)} captura(s))")
    except Exception as e:
        print(f"  (aviso) no se pudo generar el Word de evidencia: {e}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=HEADLESS, slow_mo=SLOWMO)
        opciones_contexto = {"viewport": {"width": 1600, "height": 900}}
        if GRABAR_VIDEO:
            opciones_contexto["record_video_dir"] = str(EVIDENCIA)
            opciones_contexto["record_video_size"] = {"width": 1600, "height": 900}
        context = browser.new_context(**opciones_contexto)
        if GRABAR_VIDEO:
            context.add_init_script('(() => {\n  if (window.__pwCursorInjected) return;\n  window.__pwCursorInjected = true;\n\n  const ES_TOP = window.top === window.self;\n\n  function estilizarBase(el, tam) {\n    el.style.position = \'fixed\';\n    el.style.width = tam + \'px\';\n    el.style.height = tam + \'px\';\n    el.style.borderRadius = \'50%\';\n    el.style.pointerEvents = \'none\';\n    el.style.zIndex = \'2147483647\';\n    el.style.transform = \'translate(-50%,-50%)\';\n  }\n\n  if (ES_TOP) {\n    // Documento de nivel superior (page o popup "app"): dibuja el cursor\n    // real. Recibe coordenadas propias (mousemove/mousedown locales) Y\n    // las reenviadas por iframes hijos via postMessage.\n    let cursorEl = null;\n    function asegurarCursor() {\n      if (!document.documentElement) return null;\n      if (!cursorEl) {\n        cursorEl = document.createElement(\'div\');\n        cursorEl.id = \'__pw_cursor\';\n        estilizarBase(cursorEl, 46);\n        cursorEl.style.background = \'rgba(255,0,0,.45)\';\n        cursorEl.style.border = \'5px solid rgba(220,0,0,.95)\';\n        cursorEl.style.boxShadow = \'0 0 14px 4px rgba(255,0,0,.65)\';\n        cursorEl.style.opacity = \'0\';\n        cursorEl.style.transition = \'left .35s ease, top .35s ease, opacity .2s ease\';\n        document.documentElement.appendChild(cursorEl);\n      }\n      return cursorEl;\n    }\n    function moverCursor(x, y) {\n      const el = asegurarCursor();\n      if (!el) return;\n      el.style.left = x + \'px\';\n      el.style.top = y + \'px\';\n      el.style.opacity = \'1\';\n    }\n    function ripple(x, y) {\n      if (!document.documentElement) return;\n      const r = document.createElement(\'div\');\n      estilizarBase(r, 24);\n      r.style.background = \'rgba(255,0,0,.6)\';\n      r.style.left = x + \'px\';\n      r.style.top = y + \'px\';\n      document.documentElement.appendChild(r);\n      const inicio = performance.now();\n      const duracionMs = 1400;\n      function paso(ahora) {\n        const t = Math.min(1, (ahora - inicio) / duracionMs);\n        const tam = 24 + t * (120 - 24);\n        r.style.width = tam + \'px\';\n        r.style.height = tam + \'px\';\n        r.style.opacity = String(0.95 * (1 - t));\n        if (t < 1) requestAnimationFrame(paso);\n        else r.remove();\n      }\n      requestAnimationFrame(paso);\n    }\n\n    document.addEventListener(\'mousemove\', (e) => moverCursor(e.clientX, e.clientY), true);\n    document.addEventListener(\'mousedown\', (e) => ripple(e.clientX, e.clientY), true);\n\n    window.addEventListener(\'message\', (ev) => {\n      const datos = ev.data;\n      if (!datos || datos.__pwCursor !== true) return;\n      let iframeOrigen = null;\n      for (const f of document.querySelectorAll(\'iframe\')) {\n        if (f.contentWindow === ev.source) { iframeOrigen = f; break; }\n      }\n      if (!iframeOrigen) return;\n      const rect = iframeOrigen.getBoundingClientRect();\n      const x = rect.left + datos.x;\n      const y = rect.top + datos.y;\n      if (datos.tipo === \'move\') moverCursor(x, y);\n      else if (datos.tipo === \'click\') ripple(x, y);\n    });\n  } else {\n    // Dentro de un iframe: position:fixed ahi queda acotado al viewport\n    // DEL IFRAME (no de la ventana completa), y ademas el grabador de\n    // video de Playwright no compone bien un overlay asi cuando el\n    // iframe es de otro origen (confirmado en vivo el 10/09/2026 con\n    // PR000325: el cursor SI se veia en captura de pantalla normal pero\n    // NUNCA en el video). Se reenvian las coordenadas al documento de\n    // nivel superior, que es quien realmente dibuja el cursor.\n    document.addEventListener(\'mousemove\', (e) => {\n      window.top.postMessage({ __pwCursor: true, tipo: \'move\', x: e.clientX, y: e.clientY }, \'*\');\n    }, true);\n    document.addEventListener(\'mousedown\', (e) => {\n      window.top.postMessage({ __pwCursor: true, tipo: \'click\', x: e.clientX, y: e.clientY }, \'*\');\n    }, true);\n  }\n})();')
        page = context.new_page()
        app = None
        _CASO_OK = False
        try:
            login(page, paso_excel=1)
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

            capturar_paso(app, "estado_final_del_caso", paso_excel=max(_parsear_pasos_excel(PASOS_CASO), default=None))
            _CASO_OK = True

        except (PWTimeoutError, AssertionError) as e:
            print(f"[FALLO] {CASO} FALLO: {e}")
            (app if app else page).screenshot(path=str(EVIDENCIA / f"{CASO}_error.png"), full_page=True)
            raise
        finally:
            if GRABAR_VIDEO:
                (app if app else page).wait_for_timeout(3000)
            video_portal = page.video
            video_app = app.video if app else None
            browser.close()
            if _CASO_OK:
                ruta_portal = _renombrar_video(video_portal, EVIDENCIA / f"{CASO}-1.webm") if video_portal is not None else None
                ruta_app = _renombrar_video(video_app, EVIDENCIA / f"{CASO}-2.webm") if video_app is not None else None
                rutas_videos = [r for r in (ruta_portal, ruta_app) if r is not None]
                rutas_videos.extend(p for p in sorted(EVIDENCIA.glob("page@*.webm")) if p not in rutas_videos)
                if len(rutas_videos) > 1:
                    _unir_videos(EVIDENCIA / f"{CASO}_video.webm", *rutas_videos)
                elif len(rutas_videos) == 1:
                    try:
                        rutas_videos[0].replace(EVIDENCIA / f"{CASO}_video.webm")
                    except (PermissionError, OSError) as e:
                        print(f"  (aviso) no se pudo renombrar el video final: {e}")
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
