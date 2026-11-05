"""
CP002 - Rechazo por cartera sin forzar

RF: RF-01  |  CU: CU-01
Descripcion: Verificar que un cliente de Cobranza Externa a Retirado con cartera asociada, sin marcar "Forzar", es rechazado.
Precondiciones: Debe asignarse el rol funcional: LUZGENACT. Debe existir un cliente en Cobranza Externa con cartera asociada.
Datos: Cliente en Cobranza Externa con cartera asociada; casilla "Forzar Retiro de Carteras" sin marcar.
Resultado esperado: El sistema rechaza el traslado del cliente y no cambia su estado.

Pasos a seguir:
1. Ingresar a Traslado de Clientes. 2. Seleccionar "Cobranza Externa a Retirado". 3. Agregar el cliente con cartera asociada. 4. No marcar "Forzar Retiro de Carteras". 5. Pulsar "Trasladar".
"""
import os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

# Por defecto corre en segundo plano (headless), sin abrir ventana de
# Edge. Para verlo trabajar en pantalla (util para un tester que quiere
# mirar el caso paso a paso), fijar PR000349-SP1-IT4_HEADLESS=0 antes de correrlo.
HEADLESS = os.environ.get("PR000349-SP1-IT4_HEADLESS", "1") == "1"

# Con PR000349-SP1-IT4_VIDEO=1 se graba un video (.webm) de toda la ejecucion,
# ademas de las capturas por paso. Apagado por defecto (un video por caso
# pesa/tarda mas; para una corrida masiva mejor dejarlo apagado y prenderlo
# solo cuando haga falta revisar un caso en detalle).
GRABAR_VIDEO = os.environ.get("PR000349-SP1-IT4_VIDEO", "0") == "1"

# Con PR000349-SP1-IT4_WORD=0 se omite el Word de evidencia (por defecto SI se
# genera: cada CPxxx.py arma su propio .docx con sus capturas, sin
# depender de ningun otro archivo del proyecto -asi se puede copiar este
# archivo solo a otra maquina y sigue generando su evidencia completa-).
GRABAR_WORD = os.environ.get("PR000349-SP1-IT4_WORD", "1") == "1"

# Con PR000349-SP1-IT4_SLOWMO=<milisegundos> Playwright agrega esa pausa entre
# CADA accion (click, fill, etc.). Sirve sobre todo junto con
# PR000349-SP1-IT4_VIDEO=1: sin esto, un fill() llena el campo de golpe y en
# el video no alcanza a verse el cambio. 0 = sin pausa (default, no afecta
# la velocidad normal de la corrida).
try:
    SLOWMO = int(os.environ.get("PR000349-SP1-IT4_SLOWMO", "0"))
except ValueError:
    SLOWMO = 0

# Pausa (ms) que se agrega justo despues de dejar los datos listos en
# pantalla y ANTES del clic que dispara la accion (capturar_paso con una
# descripcion "antes_de_*", ej. "antes_de_buscar", "antes_de_aceptar"): sin
# esto, con fill() llenando los campos de golpe, el video pasa de campos
# vacios a clic casi en el mismo instante y no da tiempo a ver los datos ya
# cargados antes de que se dispare la busqueda/accion. Por defecto se activa
# solo si se esta grabando video (GRABAR_VIDEO); se puede ajustar o apagar
# a mano con PR000349-SP1-IT4_PAUSA_ANTES_CLIC=<ms> (0 = sin pausa).
try:
    PAUSA_ANTES_CLIC = int(os.environ.get("PR000349-SP1-IT4_PAUSA_ANTES_CLIC", "1200" if GRABAR_VIDEO else "0"))
except ValueError:
    PAUSA_ANTES_CLIC = 0


# Ambiente Pruebas confirmado (decision del usuario, ver docstring) - el
# portal es el mismo para cualquier ambiente, la diferencia de Pruebas vs
# Produccion la resuelve el backend segun la sesion/usuario, no la URL.
URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "SCASTI_DW"      # cuenta de prueba reutilizable, rol LUZGENACT ya asignado
PASSWORD = "Melquisedec_01"

CASO = "CP002"
EVIDENCIA = Path(__file__).resolve().parent / CASO
if EVIDENCIA.exists():
    shutil.rmtree(EVIDENCIA, ignore_errors=True)
EVIDENCIA.mkdir(parents=True, exist_ok=True)

NOMBRE_CASO = 'Rechazo por cartera sin forzar'
RF_CASO = 'RF-01'
CU_CASO = 'CU-01'
DESCRIPCION_CASO = 'Verificar que un cliente de Cobranza Externa a Retirado con cartera asociada, sin marcar "Forzar", es rechazado.'
RESULTADO_ESPERADO_CASO = 'El sistema rechaza el traslado del cliente y no cambia su estado.'
PASOS_CASO = '1. Ingresar a Traslado de Clientes. 2. Seleccionar "Cobranza Externa a Retirado". 3. Agregar el cliente con cartera asociada. 4. No marcar "Forzar Retiro de Carteras". 5. Pulsar "Trasladar".'

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


def boton_por_texto(frame, texto):
    return frame.locator("button", has_text=re.compile(r"^\s*" + re.escape(texto) + r"\s*$"))


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
        celda_anio = frame.locator(f'.ant-picker-cell[title="{anio}"]').last
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
    frame.locator(f'.ant-picker-cell[title="{MESES_ABREV_NZ[mes - 1]}"]').last.click()
    app.wait_for_timeout(400)
    objetivo = f"{dia:02d}/{mes:02d}/{anio}"
    frame.locator(f'.ant-picker-cell[title="{objetivo}"]').last.click()
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


#
# Modulo: Traslado de Clientes (Web LDS)
# Componente Angular: app-traslado-clientes
# Ruta de menu confirmada en vivo: Comercial > Traslado De Clientes
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual. Un generate_scripts.py de proyecto
# importa lo que necesite de aca y le agrega solo los cuerpos de caso (los
# CPxxx puntuales de SU matriz), sin tener que re-descubrir nada de lo que
# ya esta documentado aca.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 25/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Flujo: elegir Tipo de Traslado (radio
# "RACE" = Retirado a Cobranza Externa, default; o "CEAR" = Cobranza
# Externa a Retirado), opcionalmente marcar "Forzar Retiro de Carteras"
# (solo tiene efecto real al trasladar de Cobranza Externa a Retirado),
# agregar uno o mas clientes al lote (input "N° Cliente" + boton
# "Agregar"), y pulsar "Trasladar".
#
# "Trasladar" abre un dialogo de confirmacion ("¿Esta seguro...?",
# .ant-modal/nz-modal-container) - DISTINTO del popover de resultado que
# aparece despues (`button.conf-btn-ok`). El resultado exitoso muestra el
# mensaje "se procesaron todos los clientes" (comparar en minusculas). El
# popover de resultado puede aparecer 1 vez (exito) o 2 veces superpuestas
# (fallo: toast "Operacion Exitosa" + "Ventana de Validacion" con el
# detalle) - un click generico sobre "Aceptar" puede colgar por
# strict-mode/interceptacion de puntero entre ambos; cerrar en bucle el
# primero visible hasta que no quede ninguno (ver
# cerrar_dialogos_resultado_traslado()).
#
# **Gotcha real (nz-table, ant-design)**: la grilla de clientes del lote
# siempre trae una fila oculta extra "ant-table-measure-now" (uso interno
# de layout, nz-table-measure-row) que un `nz-table tbody tr` sin filtrar
# cuenta de mas - confirmado en vivo (un caso esperaba 3 filas y veia 4).
# Excluirla siempre (ver filas_clientes_traslado()).
#
# **Datos de prueba**: no hay forma de saber el estado de un cliente sin
# consultarlo - la propia UI expone su validacion (`ValidarCliente`,
# llamada por el frontend en CADA "Agregar") con el estado real de
# cualquier numero de cliente. Reusar `app.request` (mismas cookies de
# sesion que el browser) para escanear varios numeros de cliente conocidos
# y encontrar uno en el estado que se necesite (estadoCliente: "2" =
# Retirado, "0" = Activo/no elegible) es mucho mas rapido y confiable que
# buscar en la BD Informix real. Metodo: interceptar la request real que
# dispara la UI al hacer click en "Agregar" (`app.on("request", ...)`,
# filtrar por "ValidarCliente"), guardar URL/headers/post_data, y
# reproducirla con `app.request.post(...)` sustituyendo el numero de
# cliente en el post_data via regex.
#
# **Cuidado con "quemar" clientes de prueba**: cada traslado exitoso es
# una escritura REAL en el ambiente de Pruebas - un cliente usado una vez
# para "Retirado -> Cobranza Externa" deja de calificar para ese mismo
# escenario en una corrida futura (queda en estado "pendiente de
# validacion" o similar). Si un caso que antes daba OK empieza a fallar
# sin haber cambiado el script, sospechar PRIMERO que el numero de cliente
# hardcodeado ya fue consumido, antes de asumir un bug nuevo - resolver
# buscando un cliente fresco con el mismo metodo de arriba.
# ============================================================================
#


def abrir_traslado_clientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Traslado De Clientes"], "app-traslado-clientes", paso_excel=paso_excel)


def seleccionar_tipo_traslado(frame, valor):
    """valor: "RACE" (Retirado a Cobranza Externa, default) o "CEAR" (Cobranza Externa a Retirado)."""
    frame.locator(f'label[nzvalue="{valor}"]').click()


def marcar_forzar_retiro_carteras(frame):
    frame.get_by_text("Forzar Retiro de Carteras", exact=True).click()


def agregar_cliente_traslado(app, frame, numero):
    campo = frame.locator('input[placeholder="N° Cliente"]')
    boton_agregar = frame.locator("button", has_text=re.compile(r"^\s*Agregar\s*$"))
    campo.fill(numero)
    app.wait_for_timeout(500)
    boton_agregar.click()
    app.wait_for_timeout(800)


def encontrar_cliente_en_estado(app, frame, semillas, estado_deseado, radio=15):
    """Escanea en vivo, via la propia API ValidarCliente (solo lectura, NO
    ejecuta ningun traslado), candidatos alrededor de cada numero de
    `semillas` (+/- `radio`) y devuelve el primero cuyo estadoCliente real
    coincida con `estado_deseado` ("2"=Retirado, "6"=Cobranza Externa,
    "0"=Activo/no elegible).

    CONFIRMADO EN VIVO (PR000349-SP1, 25/09/2026 - PR000349-SP1-IT2,
    15/10/2026, misma falla reproducida una 3ra vez): cualquier numero de
    cliente HARDCODEADO en este modulo (o en el cuerpo de un caso) para un
    escenario "Retirado"/"Cobranza Externa" se "quema" (deja de calificar)
    la PRIMERA vez que un Traslado real se ejecuta con el - no solo entre
    sprints distintos semanas despues, sino inclusive DENTRO de la MISMA
    sesion de pruebas si el caso se corre mas de una vez (confirmado: una
    corrida de verificacion manual del mismo caso ya deja el numero
    inservible para la corrida automatica siguiente). Usar esta funcion en
    vez de un numero fijo en cualquier caso NUEVO que necesite un cliente
    en un estado puntual - evita tener que re-descubrir manualmente un
    numero fresco cada vez que se re-corre el proyecto."""
    campo = frame.locator('input[placeholder="N° Cliente"]')
    boton_agregar = frame.locator("button", has_text=re.compile(r"^\s*Agregar\s*$"))

    solicitudes = []

    def _on_request(req):
        if "ValidarCliente" in req.url:
            solicitudes.append({"method": req.method, "url": req.url, "headers": dict(req.headers), "post_data": req.post_data})

    app.on("request", _on_request)
    campo.fill(str(semillas[0]))
    boton_agregar.click()
    app.wait_for_timeout(1200)
    app.remove_listener("request", _on_request)

    if not solicitudes:
        raise RuntimeError("No se pudo capturar la llamada real a ValidarCliente para clonarla.")
    r = solicitudes[0]

    candidatos = set()
    for semilla in semillas:
        for delta in range(-radio, radio + 1):
            candidatos.add(semilla + delta)

    for numero in sorted(candidatos):
        if r["method"] == "GET":
            url_intento = re.sub(r"\d{6,}", str(numero), r["url"]) if re.search(r"\d{6,}", r["url"]) else f"{r['url']}?numeroCliente={numero}"
            resp = app.request.get(url_intento, headers=r["headers"])
        else:
            body = r["post_data"]
            body_nuevo = re.sub(r"\d{6,}", str(numero), body) if body else f'{{"numeroCliente":"{numero}"}}'
            resp = app.request.post(r["url"], headers=r["headers"], data=body_nuevo)
        try:
            datos = resp.json()
        except Exception:
            continue
        if isinstance(datos, dict) and datos.get("estadoCliente") == estado_deseado:
            # limpiar el lote (el escaneo deja el primer candidato agregado)
            # - "Quitar" exige seleccionar la fila primero (queda disabled
            # sin eso), mas simple vaciar todo el lote con "Limpiar".
            boton_limpiar = frame.locator("button", has_text=re.compile(r"^\s*Limpiar\s*$"))
            if boton_limpiar.count():
                boton_limpiar.first.click()
                app.wait_for_timeout(400)
            return str(numero)

    raise RuntimeError(f"No se encontro ningun cliente con estadoCliente={estado_deseado!r} entre {len(candidatos)} candidatos escaneados.")


def trasladar_y_confirmar(app, frame):
    """Pulsa Trasladar y acepta el dialogo de confirmacion (¿Esta seguro...?,
    clase .ant-modal/nz-modal-container) - DISTINTO del popover de resultado
    (.conf-btn-ok) que aparece despues, ver cerrar_dialogos_resultado_traslado()."""
    boton_trasladar = frame.locator("button", has_text=re.compile(r"^\s*Trasladar\s*$"))
    boton_trasladar.click()
    app.wait_for_timeout(1500)
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    dialogo.first.wait_for(state="visible", timeout=8000)
    dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$", re.I)).first.click()
    app.wait_for_timeout(2500)
    try:
        app.wait_for_load_state("networkidle", timeout=10000)
    except PWTimeoutError:
        pass
    app.wait_for_timeout(1000)


def leer_mensaje_resultado_traslado(frame):
    return frame.locator("body").inner_text()


def filas_clientes_traslado(frame):
    """nz-table (ant-design) siempre trae una fila oculta extra
    'ant-table-measure-now' (uso interno de layout, ver
    nz-table-measure-row en el HTML del componente) que un
    `nz-table tbody tr` sin filtrar cuenta de mas - confirmado en vivo el
    25/09/2026 (un caso esperaba 3 filas y veia 4; otro esperaba 1 y veia 2).
    Excluirla siempre al contar filas reales de esta grilla."""
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now)")


def cerrar_dialogos_resultado_traslado(app, frame, intentos=4):
    """El popover de resultado (.conf-btn-ok) puede aparecer 1 vez (exito) o
    2 veces superpuestas (fallo: toast "Operacion Exitosa" + "Ventana de
    Validacion" con el detalle) - confirmado en vivo que un click(name=...)
    generico sobre "Aceptar" cuelga por strict-mode/intercepcion de puntero
    entre ambos; cerrar en bucle el primero visible hasta que no quede ninguno."""
    for _ in range(intentos):
        boton = frame.locator("button.conf-btn-ok")
        if boton.count() == 0:
            break
        try:
            boton.first.click(timeout=2000)
            app.wait_for_timeout(400)
        except Exception:
            break


#
# Modulo: Mantenimiento de Carteras (Web LDS)
# Componente Angular: app-carteras
# Ruta de menu confirmada en vivo: Comercial > Mantenimiento De Carteras
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 25/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design: ABM de carteras (codigo "OT" + proveedor
# asociado). Boton "Ingresar" abre el formulario (input `#cartera` para el
# codigo, select `#proveedor` con opciones `nz-option-item`/
# `.ant-select-item-option`). "Ingresar"/"Modificar"/"Anular" piden
# confirmacion via `.ant-modal`/`nz-modal-container` ("¿Esta
# seguro/sera ingresada/modificada?").
#
# **Bug real de framework (ya generico a varias pantallas ant-design de
# este proyecto): el toast de exito se autodesvanece rapido.** El mensaje
# ("Cartera creada/modificada/anulada exitosamente.") se AUTODESVANECE en
# pocos segundos (a diferencia de "Traslado de Clientes", que usa un
# popover `.conf-btn-ok` persistente) - leer `body.inner_text()` despues
# de esperas largas (networkidle + pausas de sobra) lo pierde SIEMPRE,
# dando un falso FALLO aunque la operacion SI funciono (confirmado
# revisando la grilla: la cartera quedaba creada igual). Solucion:
# `confirmar_y_leer_resultado_cartera()` lee el texto INMEDIATAMENTE
# (~1s) tras cerrar el dialogo de confirmacion, antes de que el toast
# tenga chance de desvanecerse. Si la operacion es rechazada en cambio,
# aparece una SEGUNDA ventana ("Ventana de Validacion", con su propio
# boton Aceptar) que NO se autodesvanece.
#
# **La grilla NO se refresca sola** tras Ingresar/Modificar/Anular
# (confirmado en vivo: sigue mostrando los mismos registros de antes) -
# `recargar_carteras()` recarga el popup entero para forzar un fetch
# nuevo. Tras llamarla, hay que volver a obtener `frame` con
# `app.locator("#aplicacion").content_frame`.
#
# **Grilla sin buscador (59+ paginas reales) y con orden ASCII, no
# numerico**: la grilla "Carteras registradas" ordena por string ASCII
# (confirmado en vivo: "01.03" < "04.06" < "1 PRUE" < "10.12" < "12") y no
# tiene campo de busqueda/filtro. `generar_codigo_ot()` genera un codigo
# con prefijo "00" a proposito para que caiga siempre en la pagina 1 tras
# recargar. Aun asi, si se acumulan suficientes carteras de prueba con el
# mismo patron en la misma sesion, un codigo "00xxxx" puede dejar de
# aparecer en la pagina 1 - usar SIEMPRE `buscar_fila_en_paginas_carteras()`
# (pagina hasta encontrar) en vez de asumir pagina 1, incluso para
# registros "recien creados".
#
# Requiere del framework compartido (web_lds_core.py, ya inyectado en la
# plantilla de cada proyecto via los bloques NAV / HELPERS_ESPERA):
# `abrir_aplicacion`. Y del bloque de helpers genericos del proyecto:
# `boton_por_texto(frame, texto)` (buscar un `<button>` por texto exacto).
# ============================================================================
#


def abrir_mantenimiento_carteras(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Carteras"], "app-carteras", paso_excel=paso_excel)


def generar_codigo_ot():
    """Genera un codigo de Orden de Trabajo de 6 caracteres, unico por
    timestamp. Prefijo "00" a proposito: la grilla "Carteras registradas"
    ordena por string ASCII y NO tiene campo de busqueda/filtro (59+
    paginas reales) - "00xxxx" siempre cae en la pagina 1 tras recargar,
    evitando tener que paginar para encontrar una cartera recien creada."""
    return f"00{int(time.time()) % 10000:04d}"


def click_ingresar_cartera(frame):
    boton_por_texto(frame, "Ingresar").click()


def completar_ot_proveedor(app, frame, ot, indice_proveedor=0):
    frame.locator("#cartera").fill(ot)
    app.wait_for_timeout(400)
    frame.locator("#proveedor").click()
    app.wait_for_timeout(800)
    opciones = frame.locator("nz-option-item, .ant-select-item-option")
    opciones.nth(indice_proveedor).click()
    app.wait_for_timeout(400)


def confirmar_y_leer_resultado_cartera(app, frame):
    """Cierra el dialogo de confirmacion ("Esta seguro/sera ingresada/
    modificada?", clase .ant-modal/nz-modal-container) y devuelve el
    resultado real.

    BUG REAL confirmado en vivo: el toast de exito ("Cartera creada/
    modificada/anulada exitosamente.") se AUTODESVANECE en pocos
    segundos (a diferencia de Traslado de Clientes, que usa un popover
    .conf-btn-ok persistente) - leer `body.inner_text()` despues de
    esperas largas (networkidle + pausas de sobra) lo pierde siempre,
    dando un falso FALLO aunque la operacion SI funciono (confirmado
    revisando la grilla: la cartera quedaba creada igual). Por eso esta
    funcion lee el texto INMEDIATAMENTE (espera corta, ~1s) tras cerrar
    el dialogo de confirmacion, antes de que el toast tenga chance de
    desvanecerse.

    Si en cambio la operacion es rechazada, aparece una SEGUNDA ventana
    ("Ventana de Validacion", con su propio boton Aceptar) que NO se
    autodesvanece - si se detecta, se cierra y se devuelve SU texto en su
    lugar (mas especifico que el mensaje generico de exito)."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    dialogo.first.wait_for(state="visible", timeout=8000)
    dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$|^S[ií]$", re.I)).first.click()
    app.wait_for_timeout(1000)
    mensaje = frame.locator("body").inner_text()

    segunda = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    if segunda.count() > 0 and segunda.first.is_visible():
        mensaje = segunda.first.inner_text()
        segunda.first.get_by_role("button", name=re.compile(r"^Aceptar$", re.I)).first.click()
        app.wait_for_timeout(500)

    try:
        app.wait_for_load_state("networkidle", timeout=8000)
    except PWTimeoutError:
        pass
    return mensaje


def leer_mensaje_resultado_cartera(frame):
    return frame.locator("body").inner_text()


def recargar_carteras(app):
    """La grilla NO se refresca sola tras Ingresar/Modificar/Anular
    (confirmado en vivo: sigue mostrando los mismos registros de antes) -
    recargar el popup entero fuerza un CargarDatos nuevo. Tras llamar a
    esto, hay que volver a obtener `frame` con
    app.locator("#aplicacion").content_frame."""
    app.reload()
    app.wait_for_load_state("networkidle", timeout=20000)
    app.wait_for_timeout(2000)


def buscar_fila_en_paginas_carteras(app, frame, codigo, max_paginas=65):
    """Esta grilla no tiene buscador/filtro (59+ paginas reales) - recorre
    paginas con "Pagina siguiente" hasta encontrar `codigo` o llegar al
    final. Devuelve el locator de la fila (ya en la pagina donde esta
    visible) o None si no se encontro."""
    boton_siguiente = frame.locator("li.ant-pagination-next button")
    for _ in range(max_paginas):
        fila = frame.locator("nz-table tbody tr:not(.ant-table-measure-now)").filter(has_text=codigo)
        if fila.count() > 0:
            return fila.first
        if boton_siguiente.get_attribute("disabled") is not None:
            return None
        boton_siguiente.click()
        app.wait_for_timeout(600)
    return None


#
# Modulo: Asignacion de Clientes a Carteras (Web LDS)
# Componente Angular: app-asignacion-carteras
# Ruta de menu confirmada en vivo: Comercial > Asignacion De Clientes A Carteras
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Selector de cartera tipo "buscar y elegir"
# (`.cartera-select`, click para abrir, input de busqueda interno
# `.ant-select-selection-search-input`, opciones `nz-option-item`/
# `.ant-select-item-option`). Panel(es) con grillas identificadas por su
# titulo visible (`.grid-panel` filtrado por texto).
#
# **Gotcha real, distinto de Mantenimiento de Carteras/Traslado de
# Clientes: "Asignar" NO muestra dialogo de confirmacion**, procesa
# DIRECTO al click - confirmado en vivo (varios casos fallaron la 1ra vez
# esperando un dialogo que nunca llega). No se confirmo si "Quitar" si lo
# muestra - por eso `confirmar_dialogo_asignacion()` es TOLERANTE (si
# aparece un dialogo lo cierra, si no aparece nada en unos segundos sigue
# sin fallar), en vez de asumir que siempre hay uno.
#
# **Ojo con el efecto colateral real**: si un caso choca esperando un
# dialogo que nunca llega, el CLICK que disparo la accion YA SE EJECUTO -
# el backend puede haber procesado el cambio de verdad aunque el script
# termine en FALLO. Confirmado en vivo: un cliente quedo asignado de
# verdad a una cartera en una corrida marcada como FALLO por este motivo,
# dejando ese dato de prueba "quemado" (ya no elegible) para el siguiente
# intento - si un caso vuelve a fallar tras corregir el timeout, sospechar
# primero que el dato de prueba ya fue consumido por el intento anterior
# antes de asumir un bug nuevo.
#
# **La grilla NO se refresca sola** tras Agregar/Asignar/Quitar - hay que
# RE-SELECCIONAR la cartera (dispara un nuevo fetch) para ver el estado
# real, no confiar en lo que se ve inmediatamente despues de la accion.
#
# **PENDIENTE-DUDA sin resolver** (anotado por si se repite en otro
# modulo): una cartera con un cliente asociado confirmado desde el
# mensaje de rechazo de "Traslado de Clientes" aparecio VACIA ("No hay
# clientes asociados") al seleccionarla desde esta pantalla. Hipotesis sin
# confirmar: los 2 endpoints (ValidarCliente/Trasladar de Traslado de
# Clientes vs listar-clientes-asociados de esta pantalla) podrian leer de
# tablas o vistas distintas, o aplicar un filtro adicional que el otro no
# aplica. **Cuando dos pantallas parecen relacionadas por el mismo dato de
# negocio (ej. "que cliente esta en que cartera"), preferir SIEMPRE la
# pantalla que hace la consulta DIRECTAMENTE afectada como fuente de
# verdad, no un mensaje/tabla cruzado de otra pantalla, por mas
# relacionado que parezca.**
# ============================================================================
#


def abrir_asignacion_clientes_carteras(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Asignacion De Clientes A Carteras"], "app-asignacion-carteras", paso_excel=paso_excel)


def seleccionar_cartera_asignacion(app, frame, codigo):
    frame.locator(".cartera-select").click(timeout=20000)
    app.wait_for_timeout(700)
    frame.locator(".cartera-select input.ant-select-selection-search-input").fill(codigo)
    app.wait_for_timeout(1000)
    frame.locator("nz-option-item, .ant-select-item-option").filter(has_text=codigo).first.click()
    app.wait_for_timeout(2000)


def agregar_cliente_asignacion(frame, numero):
    frame.locator('input[placeholder="Máx. 7 dígitos"]').fill(numero)


def filas_panel_asignacion(frame, titulo_panel):
    panel = frame.locator(".grid-panel").filter(has_text=titulo_panel)
    return panel.locator("tbody tr:not(.ant-table-measure-now)")


def confirmar_dialogo_asignacion(app, frame, timeout_ms=4000):
    """Cierra el dialogo de confirmacion si aparece (mismo patron
    .ant-modal/nz-modal-container que otras pantallas del mismo sistema)
    - TOLERANTE a que no aparezca ninguno. Confirmado en vivo: a
    diferencia de otras pantallas, "Asignar" en esta NO muestra dialogo
    de confirmacion, procesa directo al click. No se confirmo aun si
    "Quitar" si lo muestra - por eso esta version no asume ninguno de los
    2 casos, simplemente sigue si no aparece nada."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return False
    dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$|^S[ií]$", re.I)).first.click()
    app.wait_for_timeout(1500)
    return True


#
# Modulo: Investigacion de Clientes (Web LDS)
# Componente Angular: app-clientes-investigar
# Ruta de menu confirmada en vivo: Comercial > Investigacion De Clientes
#   (OJO: el EF/ET de origen la llama "Clientes a Investigar" - el nombre
#   real del menu NO coincide, confirmado en vivo)
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Selector de cartera (`.sel-cartera`, mismo
# patron "buscar y elegir" que Asignacion de Clientes a Carteras) + boton
# "Leer / Consultar" (texto exacto con espacios alrededor de la barra) ->
# grilla de clientes de la cartera (`nz-table tbody tr`, filtrar la fila
# fantasma `.ant-table-measure-now`). Cada fila tiene un checkbox para
# marcar el cliente antes de pulsar "A Investigar" / "Normalizar".
#
# **Gotcha real: los botones de accion quedan REALMENTE deshabilitados
# (atributo `disabled`, no solo estilo) mientras no haya ninguna fila
# marcada** - confirmado en vivo que esto NO es un bug de reactividad
# (se probo explicitamente marcar y desmarcar, el boton se re-deshabilita
# correctamente). Un caso que espera un mensaje de advertencia al pulsar
# el boton "sin seleccion" nunca lo va a ver porque el click ni siquiera
# llega a dispararse - verificar el atributo `disabled` en vez de intentar
# el click y esperar un mensaje que no existe.
# ============================================================================
#


def abrir_investigacion_clientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Investigacion De Clientes"], "app-clientes-investigar", paso_excel=paso_excel)


def seleccionar_cartera_investigacion(app, frame, codigo):
    frame.locator(".sel-cartera").click(timeout=20000)
    app.wait_for_timeout(700)
    frame.locator(".sel-cartera input.ant-select-selection-search-input").fill(codigo)
    app.wait_for_timeout(1000)
    frame.locator("nz-option-item, .ant-select-item-option").filter(has_text=codigo).first.click()
    app.wait_for_timeout(1000)


def leer_clientes_investigacion(app, frame):
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*/\s*Consultar\s*$")).click()
    app.wait_for_timeout(1500)


def fila_cliente_investigacion(frame, numero):
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now)").filter(has_text=numero)


def marcar_cliente_investigacion(frame, numero):
    fila = fila_cliente_investigacion(frame, numero)
    fila.locator('input[type="checkbox"]').click()


#
# Modulo: Emision de Cartas Masivas (Web LDS)
# Componente Angular: app-cartas-masivas
# Ruta de menu confirmada en vivo: Comercial > Emisión De Cartas Masivas
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. **Al abrir la pantalla aparece SIEMPRE un
# dialogo inicial** ("Ventana de Validacion": "No existen datos
# registrados con su rol", sobre el Responsable) que hay que cerrar antes
# de tocar cualquier otro control - si no se cierra, los siguientes clicks
# (ej. "Agregar") quedan bloqueados por el modal (invisible pero aun
# presente en el DOM). Campo cliente: `input[placeholder="Ej. 1002345"]` +
# boton "Agregar". Datos del responsable: nombre (`input[maxlength="23"]`),
# anexo (`input[maxlength="6"][inputmode="numeric"]`), celular
# (`input[placeholder="9XXXXXXXX"]`). Los checkboxes "Carta Art. 90"/
# "Carta Art. 178" vienen MARCADOS por defecto.
#
# **Campo Fecha defensivo**: SIEMPRE revierte a la fecha de hoy si se
# intenta dejar vacio o escribir texto invalido - no es posible provocar
# "Fecha no es valida." via UI real (la pantalla se defiende antes de
# llegar a esa validacion).
#
# **Gotcha mas sutil confirmado en este proyecto: el toast de exito se
# autodesvanece EXTREMADAMENTE rapido.** El mensaje ("Impresion finalizada
# con exito.") NO usa dialogo `.ant-modal` (a diferencia de otras
# pantallas del mismo sistema) - es un toast que desaparece tan rapido que
# ni siquiera una pausa fija de 2000ms alcanza a leerlo (la captura de
# pantalla en el momento del fallo ya no mostraba nada, el formulario ya
# se habia reseteado, dando la falsa impresion de que la operacion fallo
# cuando en realidad si funciono). Resuelto con un SONDEO en bucle corto
# (`esperar_mensaje_exito_impresion`, cada 150ms hasta 4s) en vez de
# cualquier pausa fija. El dialogo de rechazo de esta misma pantalla
# ("Error de Servicio") SI usa `.ant-modal`, pero con boton "Cerrar" en
# vez de "Aceptar" - `cerrar_dialogo_cartas_masivas()` acepta ambos
# textos (ademas de "Si").
#
# **"Sin medidor activo" no es facilmente reproducible con un cliente
# real**: un cliente con direccion/distrito reales completos genera carta
# real igual aunque el campo "medidor" venga vacio (no excluye per se). No
# se encontro la condicion exacta que la matriz describe para ese
# escenario - usar un numero de cliente INEXISTENTE junto a uno valido en
# el mismo lote logra el mismo efecto practico ("dato incompleto que no
# debe bloquear al resto del lote").
# ============================================================================
#


def abrir_emision_cartas_masivas(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Emisión De Cartas Masivas"], "app-cartas-masivas", paso_excel=paso_excel)


def cerrar_dialogo_cartas_masivas(app, frame, timeout_ms=3000, timeout_aparicion_ms=1500):
    """Cierra cualquier dialogo visible (.ant-modal/nz-modal-container) -
    usa Aceptar, Cerrar o Si segun cual tenga (confirmado en vivo: esta
    pantalla usa "Cerrar" para su dialogo de error de servicio, distinto
    de "Aceptar" en otras pantallas del mismo sistema). Espera un poco a
    que aparezca antes de descartar que hay uno - confirmado en vivo: el
    dialogo inicial ("No existen datos registrados con su rol") puede
    tardar en renderizar, y un chequeo inmediato sin esperar lo pasaba
    por alto, dejando ese dialogo bloqueando el siguiente click (ej.
    "Agregar" nunca llegaba a agregar nada)."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_aparicion_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    try:
        dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$|^Cerrar$|^S[ií]$", re.I)).first.click(timeout=timeout_ms)
        app.wait_for_timeout(500)
    except PWTimeoutError:
        pass
    return texto


def agregar_cliente_carta(app, frame, numero):
    frame.locator('input[placeholder="Ej. 1002345"]').fill(numero)
    app.wait_for_timeout(400)
    frame.locator("button", has_text=re.compile(r"^\s*Agregar\s*$")).click()
    app.wait_for_timeout(1000)


def completar_responsable_carta(frame, nombre="PRUEBA AUTOMATIZADA", anexo="1234", celular="987654321"):
    frame.locator('input[maxlength="23"]').fill(nombre)
    frame.locator('input[maxlength="6"][inputmode="numeric"]').fill(anexo)
    frame.locator('input[placeholder="9XXXXXXXX"]').fill(celular)


def esperar_mensaje_exito_impresion(app, frame, timeout_ms=4000, intervalo_ms=150):
    """El mensaje de exito ("Impresion finalizada con exito.") NO usa
    dialogo .ant-modal - es un toast que se autodesvanece MUY rapido
    (confirmado en vivo: hasta 2000ms de espera fija ya lo perdia
    siempre, la captura de pantalla en el momento del fallo ya no
    mostraba nada). Sondea el texto del body cada `intervalo_ms` en vez
    de una espera fija, devolviendo apenas aparece la frase esperada (o
    el ultimo texto visto, si nunca aparecio, para poder diagnosticar)."""
    plazo = time.monotonic() + timeout_ms / 1000
    ultimo = ""
    while time.monotonic() < plazo:
        ultimo = frame.locator("body").inner_text()
        if "impresion finalizada" in ultimo.lower():
            return ultimo
        app.wait_for_timeout(intervalo_ms)
    return ultimo


#
# Modulo: Anulacion de Facturas (Web LDS)
# Componente Angular: app-anulamiento-factura
# Ruta de menu confirmada en vivo: Comercial > Anulacion De Facturas
#   (OJO: el EF/ET de origen la llama "Anulamiento de Facturas" - el
#   nombre real del menu NO coincide, confirmado en vivo)
# Sistema/frente de negocio: Retiro y Castigo de Clientes
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Input de cliente (primer `<input>` de la
# pantalla) + boton "Leer" -> carga facturas anulables, refacturaciones y
# totales del cliente. Mensaje de rechazo confirmado EXACTO para cliente
# en estado invalido: "Cliente no está retirado o en cobranza externa."
#
# **Dependencia fuerte de datos reales de facturacion**: a diferencia de
# la mayoria de pantallas de este sistema, esta SI depende de datos de
# facturacion reales que no se pueden fabricar via UI (transiciones de
# estado de cliente no alcanzan para generar facturas anulables). Si el
# ambiente de Pruebas no tiene ningun cliente con facturas anulables
# reales, los casos de anulacion/reversion/calculo de IGV/exclusion de
# consumos quedan bloqueados por falta de dato, no por un bug de
# automatizacion - confirmar esto probando varios numeros de cliente
# reales antes de asumir un problema de script.
# ============================================================================
#


def abrir_anulacion_facturas(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Anulacion De Facturas"], "app-anulamiento-factura", paso_excel=paso_excel)


def consultar_cliente_facturas(app, frame, numero):
    frame.locator("input").first.fill(numero)
    app.wait_for_timeout(300)
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)


def cerrar_dialogo_anulacion_facturas(app, frame, timeout_ms=3000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    if dialogo.count() == 0 or not dialogo.first.is_visible():
        return None
    texto = dialogo.first.inner_text()
    try:
        dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$|^Cerrar$", re.I)).first.click(timeout=timeout_ms)
        app.wait_for_timeout(500)
    except PWTimeoutError:
        pass
    return texto


#
# Modulo: Consulta de Movimientos de Saldos (Web LDS)
# Componente Angular: app-consulta-movimientos
# Ruta de menu confirmada en vivo: Comercial > Consulta De Movimientos De Saldos
# Sistema/frente de negocio: Cuadratura de Saldos (distinto de "Retiro y
#   Castigo de Clientes")
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design, pero con grillas HTML planas (`<table
# class="g">`, NO `nz-table`) - sin el problema de fila fantasma de otras
# pantallas del proyecto. Filtros: Fecha Inicio/Fin
# (`input[placeholder="Seleccionar fecha"]`), Tipo de Movimiento, Estado
# (radios, ej. `label[nzvalue="R"]` = Retirado), checkboxes "Agrupar por
# Sucursal/Sector/Zona". Boton "Consultar" -> "Resumen de Movimientos"
# (con boton "Copiar" propio) y, al seleccionar una fila del resumen,
# "Detalle" (grilla propia, tambien con boton "Copiar").
#
# **Gotcha real, distinto de otras pantallas del proyecto: el panel
# ENTERO de filtros queda DESHABILITADO tras cada "Consultar"** (no solo
# el campo tocado) hasta pulsar "Limpiar" - hay que limpiar entre
# consultas sucesivas dentro del mismo caso, a diferencia de "Anulacion de
# Facturas" donde solo el campo cliente se bloqueaba.
#
# **Los botones "Copiar" (Resumen y Detalle) copian al portapapeles un TSV
# con headers** - confirmado leyendo `navigator.clipboard.readText()`
# tras conceder permisos al contexto
# (`context.grant_permissions(["clipboard-read", "clipboard-write"])`).
#
# **La pantalla es mas permisiva que lo que describe la matriz/EF en
# varios escenarios de fecha vacia**: dejar Desde o Hasta vacio NO
# bloquea la consulta (corre igual, "Sin registros" si no hay datos, sin
# ningun mensaje de validacion) - confirmar SIEMPRE en vivo antes de
# asumir que un mensaje "Debe ingresar fecha de..." es alcanzable. El
# rango invertido (Hasta anterior a Desde) SI se valida, con el mensaje
# exacto: "Fecha de inicio no debe ser mayor a fecha de término."
#
# **Datos de prueba (tabla `cuadra_saldo`)**: la grilla de Resumen queda
# vacia para cualquier rango de fechas si no hay filas reales en
# `cuadra_saldo` para la empresa/periodo consultado - un INSERT minimo
# (sucursal/sector/zona fijos, un tipo de movimiento, fecha_movimiento =
# hoy) es suficiente para que aparezca de inmediato.
# ============================================================================
#


def abrir_consulta_movimientos_saldos(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Movimientos De Saldos"], "app-consulta-movimientos", paso_excel=paso_excel)


def llenar_fecha_movimientos(app, frame, indice, valor):
    campo = frame.locator('input[placeholder="Seleccionar fecha"]').nth(indice)
    campo.click()
    app.wait_for_timeout(300)
    campo.fill(valor)
    frame.locator("body").press("Enter")
    app.wait_for_timeout(300)
    frame.locator("body").press("Escape")
    app.wait_for_timeout(300)


def limpiar_filtros_movimientos(frame):
    frame.locator("button", has_text=re.compile(r"^\s*Limpiar\s*$")).click()


def consultar_movimientos(app, frame):
    frame.locator("button", has_text=re.compile(r"^\s*Consultar\s*$")).click()
    app.wait_for_timeout(1500)


def cerrar_dialogo_movimientos(app, frame, timeout_ms=3000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    if dialogo.count() == 0 or not dialogo.first.is_visible():
        return None
    texto = dialogo.first.inner_text()
    try:
        dialogo.first.get_by_role("button", name=re.compile(r"^Aceptar$|^Cerrar$", re.I)).first.click(timeout=timeout_ms)
        app.wait_for_timeout(500)
    except PWTimeoutError:
        pass
    return texto


#
# Modulo: Listados de Facilidad de Pago por Deuda de Energia (Web LDS)
# Componente Angular: app-listado-convenios-deuda
# Ruta de menu confirmada en vivo: Comercial > Listados De Facilidades De
#   Pago Por Deuda De Energía
# Sistema/frente de negocio: Convenios de Pago
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla simple: radio Vigentes ("V") / Cancelados y Revocados ("CT"),
# campo Fecha (`input[placeholder="Seleccionar fecha"]`), boton "Generar"
# -> descarga directa de un informe XLSX (sin grilla intermedia en
# pantalla). El mensaje "No existen registros para el requerimiento."
# aparece como banner INLINE (no dialogo `.ant-modal`) - se lee de
# `body.inner_text()` directo. El mensaje de exito real es "Listado
# generado."
#
# **Campo Fecha defensivo** (mismo patron que otras pantallas del
# proyecto): fecha en blanco O fecha futura ambas terminan usando la fecha
# de hoy al pulsar "Generar" - no es posible provocar un mensaje de
# rechazo de fecha invalida via UI real.
#
# **Datos de prueba (tabla `conve`)**: sin un convenio real para el
# cliente consultado, "Generar" siempre da "No existen registros para el
# requerimiento." - necesita un INSERT en `conve` con `estado` = 'V'
# (Vigentes) o 'C' (Cancelados/Revocados). **Verificar el esquema REAL de
# la tabla antes de insertar** (`SELECT * FROM conve WHERE 1=0`): un
# INSERT "ya validado en Desarrollo" puede referirse a un esquema
# DISTINTO al del ambiente actual - confirmado en vivo que las columnas
# `tasa_fija`/`id_tasa_convenio` ya no existen en esta version de la
# tabla, y que las fechas deben construirse con `MDY(mes, dia, anio)` en
# vez de string literal (`'01/01/2026'` fallo con "String to date
# conversion error" por el `DBDATE` de la sesion Informix). El
# `fecha_termino` de un convenio Cancelado debe coincidir EXACTAMENTE con
# la fecha de corte que se ingrese en pantalla para que aparezca en la
# consulta.
#
# **Confirmado un caso puntual sin explicar del todo**: un convenio
# Vigente insertado sin error a veces NO aparece en "Vigentes" pese a que
# un convenio Cancelado (mismo cliente, mismo tipo de INSERT) SI aparecio
# de inmediato - hipotesis sin confirmar: falta la columna real
# `ind_caduca` (ausente del INSERT de referencia) o `saldo_origen`/
# `deuda_convenida` en 0 no califican como "vigente" para la regla de
# negocio real. Investigar esto primero si se retoma el escenario
# "Vigentes" de este modulo.
# ============================================================================
#


def abrir_listado_facilidades_deuda_energia(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Listados De Facilidades De Pago Por Deuda De Energía"], "app-listado-convenios-deuda", paso_excel=paso_excel)


def generar_informe_facilidades(app, frame):
    frame.locator("button", has_text=re.compile(r"^\s*Generar\s*$")).click()
    app.wait_for_timeout(1500)


#
# Modulo: Listados de Ingresos de CNR por Deuda de Servicios (Web LDS)
# Componente Angular: app-listado-facilidades-no-deuda
# Ruta de menu confirmada en vivo: Comercial > Listados De Ingresos De Cnr
#   Por Deuda De Servicios
# Sistema/frente de negocio: Convenios de Pago
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla IDENTICA en estructura a "Listados de Facilidad de Pago por
# Deuda de Energia" (mismo sistema "Convenios de Pago"): radio Vigentes /
# Cancelados y Revocados, campo Fecha, boton "Generar" -> descarga XLSX
# directa, banner inline "No existen registros para el requerimiento."
# Mismo patron defensivo de Fecha (blanco o futura -> usa la fecha de hoy
# al pulsar Generar).
#
# **Falso "defecto real de infraestructura" - LECCION IMPORTANTE**: en la
# sesion de automatizacion de PR000349-SP1, esta app fallo con un error
# CORS real en consola (endpoint interno `LanzarAplicativoDebug`, el
# iframe `#aplicacion` nunca se creaba) 2 veces seguidas y se documento
# como "defecto real de infraestructura, no transitorio", bloqueando 6
# casos de prueba. Horas despues, en una sesion nueva, la MISMA app abrio
# perfecto 3/3 veces sin ningun error. Era una falla TRANSITORIA del
# backend (sobrecarga puntual), no un defecto reproducible. **No concluir
# "defecto real" a partir de 2 fallos seguidos en la misma sesion corta -
# reintentar en una sesion separada por horas antes de reportarlo como
# defecto permanente.**
#
# **Datos de prueba (tabla `fac_cli`)**: sin una facilidad real para el
# cliente consultado, "Generar" siempre da "No existen registros para el
# requerimiento." Igual que con `conve` (ver
# `listado_facilidades_deuda_energia.py`), verificar el esquema REAL de
# `fac_cli` (`SELECT * FROM fac_cli WHERE 1=0`) antes de correr cualquier
# INSERT "ya validado en Desarrollo" - el esquema real del ambiente puede
# haber cambiado.
# ============================================================================
#


def abrir_listado_ingresos_cnr_deuda_servicios(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Listados De Ingresos De Cnr Por Deuda De Servicios"], "app-listado-facilidades-no-deuda", paso_excel=paso_excel)


def generar_informe_cnr(app, frame):
    frame.locator("button", has_text=re.compile(r"^\s*Generar\s*$")).click()
    app.wait_for_timeout(1500)


#
# Modulo: Aprobacion de Informes DWH (Web LDS)
# Componente Angular: app-aprobacion-informes
# Ruta de menu confirmada en vivo: Comercial > Aprobación De Informes Dwh
#   (OJO: se confirmaron 2 entradas de menu DUPLICADAS con el mismo texto
#   exacto "Aprobación De Informes Dwh" bajo Comercial - ambas abren esta
#   misma pantalla igual de bien, no es un bug de seleccion de menu)
# Sistema/frente de negocio: Aprobacion de Informes del Datawarehouse
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla Angular simple (sin ng-zorro): select Informe (4 opciones fijas:
# Informe de Ventas / Liquidacion de IGV / Morosidad Semanal / Recaudacion
# Semanal) + badge "Periodicidad: Mensual" (no editable) + select Mes /
# input Año + boton "Leer" -> grilla de aprobaciones (`table.g`, confirmada
# ordenada por fecha descendente con datos historicos reales) + botones
# "Aprobar"/"Revocar".
#
# **Gotcha real: select Mes e input Año quedan DESHABILITADOS hasta pulsar
# "Leer"**, incluso DESPUES de elegir un Informe (confirmado en vivo: la
# clase `ng-dirty` del select Informe muestra que Angular SI registro el
# cambio, pero Mes/Año no se habilitan hasta la respuesta de "Leer").
#
# "Aprobar" y "Revocar" (con fila seleccionada) piden confirmacion via
# `.ant-modal` ("¿Desea aprobar el informe?" / "¿Desea eliminar la
# aprobación del informe?"). **"Revocar" SIN fila seleccionada muestra un
# dialogo DISTINTO** ("Ventana de Validación" con icono "i", texto EXACTO
# "Debe seleccionar el informe.", boton "Aceptar") - no es un `.ant-modal`
# de confirmacion, es un modal de validacion/aviso; el boton en si NO esta
# deshabilitado (a diferencia del patron de "Investigacion de Clientes"),
# valida recien al click.
#
# **Falso "defecto real de infraestructura" - misma leccion que
# `listado_ingresos_cnr_deuda_servicios.py`**: esta app fallo con el mismo
# error CORS 2 veces seguidas en la sesion original (incluso habiendo
# funcionado bien ANTES en la misma sesion) y se documento como defecto
# permanente, bloqueando 6 casos. Horas despues abrio perfecto 3/3 veces.
# Era transitorio. No concluir "defecto real" de 2 fallos seguidos en poco
# tiempo.
#
# **Buena practica de aislamiento al escribir casos de escritura**: usar
# un informe poco tocado (ej. "Liquidacion de IGV", con historial real
# 2000-2014) y un periodo lejano a cualquier dato historico (ej. un mes/
# año futuro sin uso) para Aprobar/Revocar de prueba, revocando la propia
# aprobacion de prueba al final del caso para dejar el ambiente igual a
# como estaba.
# ============================================================================
#


def abrir_aprobacion_informes_dwh(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Aprobación De Informes Dwh"], "app-aprobacion-informes", paso_excel=paso_excel)


def leer_aprobaciones(app, frame):
    frame.get_by_role("button", name=re.compile("Leer")).click()
    app.wait_for_timeout(1200)


def confirmar_dialogo_aprobacion(app, frame, timeout_ms=4000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile(r"S[ií]|Aceptar|Confirmar", re.I)).first.click()
    app.wait_for_timeout(1200)
    return texto


#
# Modulo: Mantenimiento de Informes DWH (Web LDS)
# Componente Angular: app-mantenimiento-informes
# Ruta de menu confirmada en vivo: Comercial > Mantenimiento De Informes Dwh
# Sistema/frente de negocio: Aprobacion de Informes del Datawarehouse
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla Angular simple (sin ng-zorro): 2 `<select>` (Informe,
# Agrupacion - el 2do se RECALCULA segun el 1ro, ej. "Morosidad Semanal"
# no tiene NINGUNA agrupacion configurada) + boton "Leer" -> grilla de
# grupos (`table.g`). Seleccionar una fila carga "DETALLE DEL GRUPO" en
# solo-lectura; "Nuevo"/"Modificar" habilitan los campos (Descripcion,
# Tipo radio Blanco/Elemento/Formula/Texto, Formato, Valor1/2, Texto1/2).
#
# "Guardar" y "Eliminar" SIEMPRE piden confirmacion via `.ant-modal`
# ("¿Desea guardar los cambios realizados?" / "¿Desea eliminar el
# grupo?"). El boton "Leer" exige AMBOS combos (Informe Y Agrupacion)
# elegidos - queda deshabilitado si falta cualquiera de los dos.
#
# "Ordenar" cambia la grilla a modo reordenamiento (columna "#"
# recalculada 1..N secuencial, botones Inicio/Subir/Bajar/Fin) y el boton
# de guardar pasa a decir "Guardar Orden" - el nuevo orden persiste al
# volver a consultar.
#
# **Crear un grupo (tipo Blanco) recibe el siguiente numero de orden
# disponible** (confirmado en vivo: grupo creado quedo con el numero
# inmediatamente posterior al maximo existente). **Crear un grupo tipo
# Elemento** habilita mover elementos entre "No seleccionados"/
# "Seleccionados" (tabla dual con botones Agregar/Quitar/Agregar todos/
# Quitar todos) - el elemento movido queda asignado tras Guardar.
# **Eliminar** deja el grupo fuera de toda consulta posterior (baja
# logica, no vuelve a aparecer al re-Leer).
#
# **Buena practica al escribir casos**: usar un informe poco tocado (ej.
# "Liquidacion de IGV") en vez del mas usado en produccion ("Informe de
# Ventas") para las pruebas de escritura, y ELIMINAR cualquier grupo de
# prueba creado al final de cada caso (verificado con un Leer posterior
# mostrando la grilla de vuelta a su tamaño original).
# ============================================================================
#


def abrir_mantenimiento_informes_dwh(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Informes Dwh"], "app-mantenimiento-informes", paso_excel=paso_excel)


def confirmar_dialogo_mantenimiento_informes(app, frame, timeout_ms=4000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile(r"S[ií]|Aceptar|Confirmar", re.I)).first.click()
    app.wait_for_timeout(1200)
    return texto


def leer_grupos_informe(app, frame, informe_val, agrupacion_val):
    selects = frame.locator("select")
    selects.nth(0).select_option(informe_val)
    app.wait_for_timeout(400)
    selects.nth(1).select_option(agrupacion_val)
    app.wait_for_timeout(400)
    frame.get_by_role("button", name=re.compile("Leer")).click()
    app.wait_for_timeout(1200)


def fila_grupo_informe(frame, texto):
    return frame.locator("table.g").first.locator("tbody tr", has_text=texto)


#
# Modulo: Log de Carga de Datawarehouse (Web LDS)
# Componente Angular: app-log-carga
# Ruta de menu confirmada en vivo: Comercial > Log De Carga De Datawarehouse
# Sistema/frente de negocio: Aprobacion de Informes del Datawarehouse
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP1, 26/09/2026)
# ============================================================================
#
# Pantalla Angular simple: 2 `<select>` (Proceso - 12 opciones fijas +
# "(Todos)", Etapa - se recalcula segun el Proceso), 2 `<input type=date>`
# NATIVOS del navegador (Desde/Hasta) + boton "Buscar" -> grilla "LOG DE
# CARGA" (`table.g`); al hacer click en una fila carga la grilla "ETAPAS
# DEL PROCESO" (2do `table.g`).
#
# **Campo Fecha defensivo, variante NATIVA**: el `<input type=date>`
# propio del navegador RECHAZA cualquier texto no valido tecleado (queda
# vacio, sin dialogo ni mensaje) - la busqueda corre igual con el campo
# vacio, sin bloquear la pantalla. "Fecha inicial no válida."/"Fecha
# final no válida." de la matriz/EF no son alcanzables via UI real por
# este motivo (mismo patron defensivo de campo Fecha ya visto en otras
# pantallas del proyecto, pero aca resuelto a nivel de navegador en vez de
# por logica Angular).
#
# **Datos de prueba (tablas `etl_log_carga_cli` / `etl_log_etapa_cli` /
# `etl_log_carga_sif`)**: el hallazgo de "tabla completamente VACIA" de
# IT1/IT2 (26/09 y 16/10/2026) fue DESCARTADO en IT3 (21/10/2026) -
# confirmado con captura de red real que el servicio SI devuelve datos
# (176 registros historicos reales 2026 + los sembrados por la matriz).
# La causa real de "siempre devuelve []" en IT1/IT2 era otra, ver abajo.
#
# **Buscar con TODOS los filtros vacios (Proceso=Todos, Etapa=Todos,
# fechas vacias) NO FUNCIONA via UI real - y no es un simple "no-op"**:
# confirmado en vivo dos veces de forma independiente (21/10/2026): la
# sonda automatizada mostro 0 llamadas de red al backend (el boton
# Buscar no dispara ConsultarLogCarga en absoluto con todo vacio), y el
# usuario, probandolo a mano en el navegador real, confirmo que la
# pantalla se queda colgada ("esperando") y al rato termina mostrando una
# **Ventana de Error por timeout/espera** - mas grave que un simple no-op
# silencioso. **Cualquier caso futuro que la matriz describa como
# "sin filtros"/"fechas vacias" debe adaptarse a un Proceso especifico +
# rango de fechas acotado** (igual resultado esperado - integra ambas
# fuentes, cli y sif, en una sola lista - sin pasar por este camino roto).
# No perder tiempo reintentando la busqueda literal sin filtros.
# ============================================================================
#


def abrir_log_carga_datawarehouse(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Log De Carga De Datawarehouse"], "app-log-carga", paso_excel=paso_excel)


def buscar_log_carga(app, frame):
    frame.get_by_role("button", name=re.compile("Buscar")).click()
    app.wait_for_timeout(1200)


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
