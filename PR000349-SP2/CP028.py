"""
CP028 - Confirmación al no aplicar ningún filtro

RF: RF-04  |  CU: CU-01
Descripcion: Validar la pregunta de confirmación cuando Oficina, Cajero y N.° de Sesión están vacíos.
Precondiciones: Usuario con rol ANDESE; Oficina, Cajero y N.° de Sesión vacíos.
Datos: Sin selección de Oficina/Cajero/Sesión.
Resultado esperado: Se pregunta "No ha seleccionado ningún filtro, se mostrarán todos los pagos entre las fechas seleccionadas. ¿Desea continuar?"

Pasos a seguir:
1. Dejar vacíos Oficina, Cajero y N.° de Sesión. 2. Presionar Leer. 3. Verificar la pregunta de confirmación.
"""
import os, re, shutil, struct, subprocess, time, zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as _escape_xml
from playwright.sync_api import sync_playwright, expect, TimeoutError as PWTimeoutError

# Por defecto corre en segundo plano (headless), sin abrir ventana de
# Edge. Para verlo trabajar en pantalla (util para un tester que quiere
# mirar el caso paso a paso), fijar PR000349-SP2_HEADLESS=0 antes de correrlo.
HEADLESS = os.environ.get("PR000349-SP2_HEADLESS", "1") == "1"

# Con PR000349-SP2_VIDEO=1 se graba un video (.webm) de toda la ejecucion,
# ademas de las capturas por paso. Apagado por defecto (un video por caso
# pesa/tarda mas; para una corrida masiva mejor dejarlo apagado y prenderlo
# solo cuando haga falta revisar un caso en detalle).
GRABAR_VIDEO = os.environ.get("PR000349-SP2_VIDEO", "0") == "1"

# Con PR000349-SP2_WORD=0 se omite el Word de evidencia (por defecto SI se
# genera: cada CPxxx.py arma su propio .docx con sus capturas, sin
# depender de ningun otro archivo del proyecto -asi se puede copiar este
# archivo solo a otra maquina y sigue generando su evidencia completa-).
GRABAR_WORD = os.environ.get("PR000349-SP2_WORD", "1") == "1"

# Con PR000349-SP2_SLOWMO=<milisegundos> Playwright agrega esa pausa entre
# CADA accion (click, fill, etc.). Sirve sobre todo junto con
# PR000349-SP2_VIDEO=1: sin esto, un fill() llena el campo de golpe y en
# el video no alcanza a verse el cambio. 0 = sin pausa (default, no afecta
# la velocidad normal de la corrida).
try:
    SLOWMO = int(os.environ.get("PR000349-SP2_SLOWMO", "0"))
except ValueError:
    SLOWMO = 0

# Pausa (ms) que se agrega justo despues de dejar los datos listos en
# pantalla y ANTES del clic que dispara la accion (capturar_paso con una
# descripcion "antes_de_*", ej. "antes_de_buscar", "antes_de_aceptar"): sin
# esto, con fill() llenando los campos de golpe, el video pasa de campos
# vacios a clic casi en el mismo instante y no da tiempo a ver los datos ya
# cargados antes de que se dispare la busqueda/accion. Por defecto se activa
# solo si se esta grabando video (GRABAR_VIDEO); se puede ajustar o apagar
# a mano con PR000349-SP2_PAUSA_ANTES_CLIC=<ms> (0 = sin pausa).
try:
    PAUSA_ANTES_CLIC = int(os.environ.get("PR000349-SP2_PAUSA_ANTES_CLIC", "1200" if GRABAR_VIDEO else "0"))
except ValueError:
    PAUSA_ANTES_CLIC = 0


URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = 'DCABA_DW'
PASSWORD = 'Melquisedec_01'

CASO = "CP028"
EVIDENCIA = Path(__file__).resolve().parent / CASO
if EVIDENCIA.exists():
    shutil.rmtree(EVIDENCIA, ignore_errors=True)
EVIDENCIA.mkdir(parents=True, exist_ok=True)

NOMBRE_CASO = 'Confirmación al no aplicar ningún filtro'
RF_CASO = 'RF-04'
CU_CASO = 'CU-01'
DESCRIPCION_CASO = 'Validar la pregunta de confirmación cuando Oficina, Cajero y N.° de Sesión están vacíos.'
RESULTADO_ESPERADO_CASO = 'Se pregunta "No ha seleccionado ningún filtro, se mostrarán todos los pagos entre las fechas seleccionadas. ¿Desea continuar?"'
PASOS_CASO = '1. Dejar vacíos Oficina, Cajero y N.° de Sesión. 2. Presionar Leer. 3. Verificar la pregunta de confirmación.'

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
# Modulo: Consulta de Clientes Asociados a una S.S. (Web LDS)
# Componente Angular: app-conscliesol
# Ruta de menu confirmada en vivo: Comercial > Consulta De Clientes Asociados A Una S.S.
# Sistema/frente de negocio: Gestion de Clientes (acticome/conscliesol)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 27/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design moderna (misma familia que otras pantallas
# Web LDS, pero con tabla nz-table estandar - SIN el custom `table.g` visto
# en otros modulos). Campos: `input#numeroSS` (solo digitos, maxlength 10),
# `input#correlativo` (maxlength 2, sin restriccion de formato). Botones
# "Leer" (siempre habilitado) e "Imprimir" (deshabilitado hasta ejecutar
# Leer una vez, luego SIEMPRE habilitado incluso con 0 resultados).
#
# Resultado de "Leer": grilla `nz-table` (filtrar la fila fantasma
# `ant-table-measure-now`, mismo gotcha de siempre en nz-table) + una
# linea de texto justo debajo con el total: "Clientes asociados a la SS.
# <numero>:\\n<total>" (sin correlativo) o "Clientes asociados a la SS.
# <numero> (<correlativo>):\\n<total>" (con correlativo).
#
# **Los mensajes de validacion/error usan una "Ventana de Validacion"
# modal** (`.ant-modal`/`nz-modal-container`, icono "i", boton unico
# "Aceptar") - NO son toasts ni banners inline. Confirmados en vivo:
# - "Ingrese N.° de S.S." (Leer sin S.S.)
# - "N.° de SS y Correlativo no encontrados." (con Correlativo, sin resultados)
# - "N.° de SS no encontrada." (sin Correlativo, sin resultados - documentado
#   en el EF, mismo patron simetrico que el mensaje con correlativo)
# - "No se generó informe." (fallo de generacion de Imprimir)
#
# **El campo N.° de S.S. SI descarta letras/simbolos al teclear** (confirmado
# en vivo: `type("ab12$%3")` deja solo `"123"` en el campo) - RN-08 SI es
# reproducible tal cual, a diferencia de otros "campos defensivos" de otros
# proyectos que resultaron ser mas permisivos que lo documentado.
#
# **RN-07 (modificar N.° de S.S. limpia grilla y Correlativo) SI es
# reproducible tal cual el EF** - confirmado en vivo dos veces. La primera
# verificacion dio un falso negativo (la grilla parecia no limpiarse) por
# escribir el digito nuevo via `page.keyboard.type(...)` en vez de
# `locator.press_sequentially(...)` sobre el campo correcto - con la
# correccion, la grilla SI se limpia de inmediato al modificar el campo.
# Ojo con este gotcha de automatizacion (no de la app real): escribir en
# un input DENTRO de un iframe de un popup requiere teclear sobre el
# `Locator` del campo (o su `Page`/`Frame` correspondiente), nunca sobre
# el `page` del portal original - un `page.keyboard.type(...)` fuera de
# lugar no lanza error, simplemente no le llega a nadie, dando la falsa
# impresion de que la app no reacciono a un cambio que en realidad nunca
# se escribio.
#
# **"Imprimir" (generacion de informe) confirmado en vivo que SIEMPRE
# falla con "No se generó informe."** (probado 3 veces, resultado
# consistente, no transitorio - a diferencia del caso de PR000349-SP1
# RF-09/RF-10 donde SI era transitorio). Esto coincide con un riesgo YA
# documentado explicitamente en el EF (Seccion 11, Supuestos): "la
# generación y descarga de informes de RF-01 ... depende de un servicio
# de generación de reportes externo al alcance de este sprint; su
# disponibilidad es un prerrequisito de cierre". El dialogo de
# confirmacion previo ("¿Desea generar archivos?", botones Cancelar/
# Aceptar) SI funciona normalmente - es solo la generacion real la que
# falla, consistente con el servicio externo no disponible en Pruebas.
# ============================================================================
#


def abrir_consulta_clientes_ss(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Clientes Asociados A Una S.S."], "app-conscliesol", paso_excel=paso_excel)


def cerrar_ventana_validacion(app, frame, timeout_ms=4000):
    """Cierra la "Ventana de Validacion" (.ant-modal/nz-modal-container,
    icono "i", boton unico "Aceptar") si aparece, y devuelve su texto.
    Tolerante: devuelve None si no aparece ninguna."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
    app.wait_for_timeout(500)
    return texto


def leer_clientes_ss(app, frame, numero_ss=None, correlativo=None):
    """Completa N.° de S.S. y/o Correlativo (si se pasan) y pulsa Leer.
    Pasar None en cualquiera de los 2 para no tocar ese campo (dejarlo
    con lo que ya tenia)."""
    if numero_ss is not None:
        frame.locator("#numeroSS").fill(numero_ss)
        app.wait_for_timeout(300)
    if correlativo is not None:
        frame.locator("#correlativo").fill(correlativo)
        app.wait_for_timeout(300)
    frame.get_by_role("button", name=re.compile("Leer")).click()
    app.wait_for_timeout(1500)


def filas_clientes_ss(frame):
    """nz-table trae 2 filas que NO son datos reales y hay que excluir
    siempre: la fila fantasma de medicion interna
    (`tr.ant-table-measure-now`, gotcha ya visto en otros modulos) Y la
    fila placeholder "No hay datos" (`tr.ant-table-placeholder`, con un
    componente nz-empty adentro) que esta pantalla muestra cuando la
    grilla esta vacia - confirmado en vivo que un conteo ingenuo
    (solo excluyendo measure-now) da 1 fila incluso sin resultados."""
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now):not(.ant-table-placeholder)")


def confirmar_imprimir(app, frame):
    """Pulsa Imprimir y confirma el dialogo ("¿Desea generar archivos?").
    Devuelve el texto final de la pantalla tras la confirmacion (puede
    ser el mensaje de exito+descarga, o la Ventana de Validacion de
    fallo "No se generó informe." - ver ficha tecnica del modulo)."""
    frame.get_by_role("button", name=re.compile("Imprimir")).click()
    app.wait_for_timeout(800)
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    dialogo.first.wait_for(state="visible", timeout=4000)
    dialogo.first.get_by_role("button", name=re.compile("^S[ií]$|^Aceptar$", re.I)).first.click()
    app.wait_for_timeout(1200)


#
# Modulo: Mantenimiento de Ordenes de Conexion (Web LDS)
# Componente Angular: app-mantord
# Ruta de menu confirmada en vivo: Comercial > Mantenimiento De Ordenes De Conexion
# Sistema/frente de negocio: Gestion de Clientes / Acticome (NUCLI)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
# ============================================================================
#
# **Backend confirmado operativo el 28/10/2026** - en una corrida anterior
# (28/09/2026) esta pantalla daba error 503 y quedo documentada como
# "backend caido"; un mes despues, misma cuenta, carga y responde
# perfecto. Antes de asumir un defecto de infraestructura permanente,
# reintentar en una sesion nueva (mismo patron ya documentado en el
# checklist para RF-09/RF-10 de PR000349-SP1).
#
# Requiere rol funcional con permiso sobre SRV.MANTORD - la matriz de
# roles con permiso vigente sobre este recurso incluye 88 roles (ADMINIST,
# CONSCLIE, JEFESUCU, GERENTE, INSPECT, RELNUCLI, entre otros). Confirmado
# que DCABA_DW tiene acceso (SCASTI_DW no se probo especificamente para
# este RF).
#
# **Selectores reales**: `#numeroCliente` (input de texto), botones por
# texto exacto Limpiar/Anular/Actualizar/Leer (Anular y Actualizar
# deshabilitados hasta Leer). El resultado de Leer puede ser:
# 1. Un dialogo `.ant-modal`/`nz-modal-container` ("Ventana de
#    Validacion") si NO se encontro orden, o si la orden esta bloqueada
#    por un proceso externo.
# 2. La orden cargada SIN dialogo, con sus secciones "ORDEN DE CONEXION"
#    (Nombre/Direccion/Rol de Creacion/etc.) y "PROCEDIMIENTOS/MENSAJES DE
#    ENRUTAMIENTO" pobladas.
#
# **Mensajes reales confirmados** (coinciden exacto con el EF):
# - Sin orden: "No se encontró Orden de Conexión del Cliente."
# - Orden generada por ACTICOME (bloqueada): "El NUCLI fue generado por
#   el ACTICOME, favor trabajar en dicho módulo" - confirmado en vivo con
#   clientes reales 1830410, 1764523, 1920482.
# - Orden de otro usuario (no creador, sin privilegio de edicion ajena):
#   tras Leer, NO aparece ningun dialogo - la orden carga directo con el
#   texto "Ud. no ingresó la Orden de Conexión. Sólo puede consultar" en
#   la seccion de resultado, y los botones Anular/Actualizar quedan
#   deshabilitados. Confirmado en vivo con clientes reales 1259207 y
#   1415959.
#
# **Gotcha de busqueda de datos**: NO hay forma de listar/filtrar ordenes
# desde esta pantalla (exige un numero de cliente puntual). Para encontrar
# clientes en cada estado (sin orden / orden ajena / orden propia /
# anulada), escanear una lista de clientes ya conocidos del proyecto via
# Leer real (igual metodo que PR000349-SP1 con ValidarCliente) en vez de
# perseguir el esquema SQL real primero.
#
# **PENDIENTE SIN RESOLVER (confirmado 28/10/2026, documentado tambien en
# la propia matriz de casos del cliente)**: no se encontro ningun cliente
# real cuya orden de conexion haya sido CREADA por la cuenta de prueba
# (DCABA_DW/SCASTI_DW) - la propia matriz Excel ya trae una nota de
# Desarrollo: "no se encontró dato real que la satisfaga; nucli.rol_creacion
# nunca coincide". Sin este dato no se puede automatizar CP009 (Leer
# exitoso como creador) ni los casos de Actualizar/Anular que dependen de
# serlo (CP012/013/014/015/016) salvo via el camino de usuario privilegiado
# (rol JEFESUCU, ver CP072) o consiguiendo el dato por otra via (BD,
# Desarrollo). Tampoco se encontro ningun cliente con orden YA ANULADA
# (CP011) en el escaneo inicial de ~25 clientes conocidos del proyecto.
#


def abrir_mantord(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Ordenes De Conexion"], "app-mantord", paso_excel=paso_excel)


def leer_orden(app, frame, numero_cliente):
    """Escribe el numero de cliente y pulsa Leer. Si aparece un dialogo
    de Ventana de Validacion, lo cierra y devuelve su texto; si la orden
    carga directo (sin dialogo), devuelve None."""
    campo = frame.locator("#numeroCliente")
    campo.click()
    campo.fill("")
    campo.fill(str(numero_cliente))
    app.wait_for_timeout(300)
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        mensaje = modal.first.inner_text()
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return mensaje
    return None


def limpiar(app, frame):
    boton = frame.locator("button", has_text=re.compile(r"^\s*Limpiar\s*$"))
    for _ in range(15):
        if boton.is_enabled():
            boton.click()
            return
        app.wait_for_timeout(500)


#
# Modulo: Consulta de Cortes y Reconexiones (Web LDS)
# Componente Angular: app-cortes-reconexiones
# Ruta de menu confirmada en vivo: Comercial > Consulta De Cortes Y Reconexiones
# Sistema/frente de negocio: Gestion de Cortes (CONCRCLI)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
# ============================================================================
#
# **Backend confirmado operativo** - en una corrida anterior (28/09/2026)
# esta pantalla daba 504 y quedo documentada como "backend caido"; un mes
# despues, misma cuenta (DCABA_DW), carga y responde perfecto. Mismo
# patron ya confirmado en RF-02 y RF-05 de este mismo proyecto.
#
# **Selectores reales**: 2 radios de Tipo de Corte (el primero,
# "Inconsistencias Corte Fresco", viene MARCADO por defecto - confirma
# CP017; el segundo es "Verificaciones"), `#fldNumeroCliente`,
# `#fldProcesos` (select, "(Sin selección)" + 3 motivos reales),
# `#fldSucursal` (10 sucursales reales + "Sin Sucursal"), `#fldSector`,
# `#fldZona`, `#fldProveedor`, `#fldTipoFiltroFecha` (select: `=`, `<=`,
# `>=`, `entre` - **"entre" es el valor por defecto**, por lo que hacen
# falta AMBOS campos de fecha). Los campos de fecha reales son
# `input[type=date]` NATIVOS (hay 2: inicial y final) - no tienen el
# defecto de freeze de RF-07/09 (nz-date-picker). Botones Leer / "Guardar
# como..." (deshabilitado hasta Leer) / Limpiar.
#
# **Confirmacion real confirmada (RN de "sin filtro")**: con ambas fechas
# puestas (operador "entre" por defecto) pero SIN ningun otro filtro
# (Procesos, Sucursal, etc.), aparece el modal "Confirmación": *"No ha
# seleccionado ningún filtro, se mostrarán todos los datos entre las
# fechas seleccionadas. ¿Desea continuar?"* - mismo patron ya visto en
# RF-04 y RF-05 de este proyecto.
#
# **Validacion real confirmada**: con el operador "entre" por defecto y
# solo UNA fecha llena (falta la otra), modal "Ventana de Validación":
# *"Debe ingresar los dos valores del rango."*
# ============================================================================
#


def abrir_cortes_reconexiones(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Cortes Y Reconexiones"], "app-cortes-reconexiones", paso_excel=paso_excel)


def leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True):
    """Pulsa Leer y maneja el dialogo que aparezca. Devuelve una tupla
    (tipo, texto): tipo es 'validacion', 'confirmacion' o None (sin
    dialogo, consulta corrio directo)."""
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if not (modal.count() and modal.first.is_visible()):
        return None, None
    texto = modal.first.inner_text()
    if "confirmaci" in texto.lower() and aceptar_confirmacion:
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(3000)
        return "confirmacion", texto
    if "validaci" in texto.lower():
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return "validacion", texto
    return "confirmacion", texto


#
# Modulo: Consulta de Cuadratura de Sesion (Web LDS)
# Ruta de menu confirmada en vivo: Comercial > Consulta De Cuadratura De Sesion
# Sistema/frente de negocio: Recaudacion (recauda/pagoscent/cuadrasesion)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
# ============================================================================
#
# **Requiere el rol funcional ANDESE - no visible en el menu para la cuenta
# SCASTI_DW.** Se explorto y valido con DCABA_DW/Melquisedec_01.
#
# A diferencia de RF-07/RF-09 (ng-zorro/Ant Design), esta pantalla es HTML
# plano: `<select id="fld-oficina">` (con `(Todos)` + oficinas reales) y su
# combo sincronizado `#fld-nombre-oficina`; `#fld-cajero` y `#fld-sesion` son
# inputs de TEXTO con un `<datalist>` asociado (`lst-cajeros`/`lst-sesiones`,
# NO son `<select>` reales, son "combo editable": aceptan cualquier valor
# tecleado aunque no figure en las sugerencias); `#fld-operador` es un
# `<select>` con `=`, `<=`, `>=`, `entre`; `#fld-fecha-inicio` es un
# `<input type="date">` NATIVO (a diferencia del `nz-date-picker` de
# RF-07/RF-09 - ver mas abajo, esto es justamente lo que lo salva del
# defecto de esas 2 pantallas); al elegir operador "entre" aparece un
# segundo campo `#fld-fecha-fin` (tambien `<input type="date">` nativo).
# Checkbox `#fld-ampliar-campos` (deshabilitado hasta un Leer exitoso).
# Botones Limpiar / "Guardar como..." / Leer (que pasa a decir "Siguiente"
# tras el primer clic, para paginacion de a 50 - RN-10).
#
# **Cascada Oficina -> Cajero (RN-06): el datalist de Cajero se VACIA (no
# se llena) al elegir una Oficina especifica** - confirmado en vivo: con
# "(Todos)" trae ~200 codigos de cajero; al elegir Oficina "0010" el
# datalist queda vacio, porque la cascada esta acotada tambien al RANGO DE
# FECHA vigente (que por defecto es "hoy" - normalmente sin sesiones para
# ese dia). Esto es una cascada real funcionando, NO un bug: para probar el
# flujo completo con datos reales, es mas simple TECLEAR el codigo de
# cajero conocido directamente en el input (es un combo editable, RN-08)
# en vez de depender del datalist.
#
# **Cajero/Oficina reales confirmados con datos historicos**: Oficina
# "0010" (Chacarilla) + Cajero "1324" + operador "<=" + fecha inicial
# "01/01/2026" trae 50 filas reales (sesiones 0002-0004, fecha real de
# sesion 9/6/2005 - los datos de prueba en Pruebas son historicos, no del
# dia de hoy).
#
# **GOTCHA CRITICO DE TIMING - MUY IMPORTANTE, distinto de "freeze"
# real: el clic en "Leer" (o en "Guardar como...") dispara una consulta
# que puede tardar HASTA ~60 SEGUNDOS en responder** (mucho mas lento que
# cualquier otra pantalla de este proyecto, incluida RF-07 con sus 10-15s).
# Mientras esa consulta esta en curso, CUALQUIER operacion de Playwright
# que necesite evaluar JS dentro del frame (`is_enabled()`, `input_value()`,
# `inner_text()`, incluso un `click()` nuevo) se queda esperando hasta SU
# PROPIO timeout (tipicamente 30s) antes de fallar o de finalmente
# responder - dando la falsa impresion de que la pantalla esta "congelada"
# igual que el defecto real de RF-07/RF-09. La diferencia clave, confirmada
# en vivo: aca NO es un defecto, es una consulta lenta que SI termina bien
# sola (sin excepcion JS, sin error de consola) - basta con esperar con un
# `app.wait_for_timeout(...)` (que no toca el frame, por lo que no se
# bloquea) el tiempo suficiente ANTES de intentar leer el frame. Usar
# SIEMPRE `leer_cuadratura_sesion()` (espera ciega de bloque, no un sondeo
# que toque el frame a cada rato - un sondeo corto Y FRECUENTE es
# CONTRAPRODUCENTE aca, porque cada intento de tocar el frame durante la
# consulta puede el mismo tardar hasta 30s en resolver).
#
# **Mensajes reales confirmados** (via modal "Ventana de Validación",
# icono "i", boton "Aceptar" - RN-07):
# - "Debe ingresar los dos valores del rango." (operador "entre" con solo 1 fecha)
# - "Fecha inicial debe ser menor o igual que fecha final." (fecha inicial > fecha final)
#
# **Confirmacion real confirmada** (modal "Confirmación", icono "?",
# botones "Cancelar"/"Aceptar" - RN-09, al presionar Leer con Oficina,
# Cajero y Sesion los 3 vacios):
# "No ha seleccionado ningún filtro, se mostrarán todos los pagos entre
# las fechas seleccionadas. ¿Desea continuar?"
#
# **Ampliar Campos (RN-12) confirmado**: la casilla queda deshabilitada
# hasta un Leer exitoso; al marcarla, la grilla pasa de 11 a 39 columnas
# (detalle monetario extendido).
#
# **"Guardar como..." (RN-14/15/16) confirmado**: es una descarga real de
# archivo de texto (Playwright: evento `download`, NO un dialogo nativo de
# guardado ni un `page.on("dialog")`), nombre
# `CuadraturaSesion_<timestamp>.txt`. Vuelve a ejecutar la consulta
# COMPLETA (mismo gotcha de ~60s) antes de generar el archivo. El archivo
# exportado trae una fila de encabezado con 39 columnas pero cada fila de
# datos real solo trae ~20 valores (columnas de mas en el encabezado que
# datos reales) - comportamiento heredado documentado en el EF (RN-16), NO
# un bug de esta automatizacion.
#
# **Por que esta pantalla SI se pudo probar con fecha valida y RF-07/RF-09
# NO**: la fecha aca es un `<input type="date">` NATIVO del navegador; el
# defecto real de freeze de RF-07/RF-09 esta acotado al componente
# `nz-date-picker` (ng-zorro) - confirmado por contraste directo, no por
# suposicion.
# ============================================================================
#


def abrir_consulta_cuadratura_sesion(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Cuadratura De Sesion"], "app-cuadratura-sesion", paso_excel=paso_excel)


def leer_cuadratura_sesion(app, frame, timeout_ms=90000, espera_bloque_ms=60000):
    """Pulsa Leer y espera el resultado. Las validaciones (RN-07) y la
    confirmacion (RN-09) son de cliente y aparecen de inmediato: se
    detectan leyendo el texto del body justo despues del clic. Si NO
    aparecio ningun modal, es una consulta real (lenta, ver ficha
    tecnica) - se espera en UN SOLO bloque `espera_bloque_ms` SIN tocar
    el frame (un sondeo corto y frecuente es contraproducente aca: cada
    intento de leer el frame mientras la consulta esta en curso puede el
    mismo tardar hasta 30s). Devuelve el texto del modal si aparecio, o
    None si la busqueda real termino (con o sin resultados)."""
    boton_leer = frame.get_by_role("button", name=re.compile(r"^\s*(Leer|Siguiente)\s*$"))
    boton_leer.click()
    app.wait_for_timeout(1200)
    texto = frame.locator("body").inner_text()
    if "Ventana de Validaci" in texto or "Confirmaci" in texto:
        return texto
    app.wait_for_timeout(espera_bloque_ms)
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        try:
            texto = frame.locator("body").inner_text(timeout=15000)
            return texto if ("Ventana de Validaci" in texto or "Confirmaci" in texto) else None
        except PWTimeoutError:
            app.wait_for_timeout(10000)
    raise PWTimeoutError(f"leer_cuadratura_sesion: no termino en {timeout_ms + espera_bloque_ms}ms")


def cerrar_modal_cuadratura(frame, boton="Aceptar"):
    frame.get_by_role("button", name=re.compile(rf"^\s*{boton}\s*$")).click()


def filas_cuadratura_sesion(frame):
    return frame.locator("table.grid tbody tr")


#
# Modulo: Consulta de Pagos (Web LDS)
# Componente Angular: app-consulta-pago
# Ruta de menu confirmada en vivo: Comercial > Consulta De Pagos
# Sistema/frente de negocio: Recaudacion (CONSPAG)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
# ============================================================================
#
# **Backend confirmado operativo** - en una corrida anterior (28/09/2026)
# esta pantalla daba 503 y quedo documentada como "backend caido"; un mes
# despues, misma cuenta (DCABA_DW), carga y responde perfecto. Mismo
# patron ya confirmado en RF-02 (Mantenimiento de Ordenes de Conexion) de
# este mismo proyecto - antes de asumir un defecto de infraestructura
# permanente, reintentar en una sesion nueva.
#
# **GOTCHA REAL CONFIRMADO: `get_by_role("button", name=re.compile(...))`
# CRASHEA el navegador en esta pantalla (2/2 veces reproducido,
# "Target crashed").** Usar SIEMPRE `frame.locator("button",
# has_text=re.compile(...))` para los botones de esta pantalla, nunca
# get_by_role con regex - no se investigo la causa exacta (posible
# problema de calculo de accessible-name sobre el arbol de esta pantalla
# en particular), pero el selector alternativo funciona sin problema.
#
# **Selectores reales**: `#txtFechaInicial` (`<input type="date">`
# NATIVO, no nz-date-picker - no tiene el defecto de freeze de RF-07/09),
# `#txtMontoInicial`, `#txtNumeroCliente`, `#txtDoctoInicial`. Combo
# "Referencia" con **"Actualización de Saldo" como opcion por defecto**
# (coincide con CP031 "tipo por defecto"). Botones por texto exacto:
# Leer (pasa a decir "Siguiente" tras el primer Leer exitoso, paginacion
# de a 25 - mismo patron que otras pantallas de este proyecto),
# "Calcular total" y "Guardar como..." (deshabilitados hasta Leer),
# Limpiar.
#
# **Confirmacion real confirmada (RN de "sin filtro")**: al presionar
# Leer con los filtros en su estado por defecto (solo fecha, sin otro
# filtro puesto), aparece el modal "Confirmación" ("?"): *"No ha
# seleccionado ningún filtro, se mostrarán todos los pagos entre las
# fechas seleccionadas. ¿Desea continuar?"* - mismo patron ya visto en
# RF-04 (Cuadratura de Sesion) de este mismo proyecto.
#
# **Resultado vacio real confirmado**: "No se encontraron pagos con los
# filtros vigentes." + "Registros mostrados: 0 — se cargan bloques
# adicionales de 25 al continuar leyendo" - con fecha desde 01/01/2026
# sin mas filtro, 0 resultados (los datos reales de Pruebas pueden ser
# historicos, igual que en RF-04, donde los datos reales eran de 2005).
#
# **Dato real confirmado 28/10/2026 que destraba la busqueda**:
# 02/05/2002 (operador "=") tiene pagos reales tanto en "Actualización de
# Saldo" como en "Otros Conceptos" (concepto EMI). Fecha "Desde" nace con
# el dia de HOY precargado (a diferencia de otras pantallas del proyecto,
# que nacen vacias) - por eso buscar sin tocar la fecha da 0 resultados
# reales, no es que la pantalla este rota.
#
# **Combos reales son `nz-select` (ant-design), NO `<select>` nativos**:
# `cboReferencia` (5 opciones: Actualización de Saldo / Otros Conceptos /
# No Ubicados / Encargos de Cobranza / Cobranza Externa), `cboFechaOperador`
# (`=`/`<=`/`>=`/`entre`, "=" por defecto), `cboLote`, `cboOficinaCod`,
# `cboOficinaNom`, `cboCajero`, `cboConcepto` (recarga segun Referencia:
# con "Otros Conceptos" trae 6 codigos reales - AUS/CHD/CVW/EMI/ENQ/MGT),
# `cboMontoOperador`, `cboSector`, `cboEstado`, `cboTipoDocumento`,
# `cboLibro`, `cboDoctoOperador`, `cboOrigen` (estos ultimos 4
# deshabilitados salvo con Referencia "Otros Conceptos" - confirma CP032).
# Usar `elegir_nz_select()` (abajo) para elegir una opcion, nunca
# `select_option()`.
#
# **DEFECTO REAL confirmado en vivo 28/10/2026 (CP034)**: con Referencia
# "No Ubicados", el backend `BuscarPagos` responde **500** siempre
# (probado con operador "=" + fecha de hoy, y con "entre" + rango de 59
# dias - ambos fallan igual) - la app muestra "Error de Servicio: Error
# en consulta.". No se pudo validar la regla de "sin limite de dias" de
# este origen porque la consulta nunca llega a ejecutarse con exito.
#
# **`Limpiar` NO resetea el combo `cboFechaOperador`** a "=" - si una
# corrida previa (en la misma sesion de navegador) dejo el operador en
# otro valor, Limpiar lo deja como estaba. No afecta a los CPxxx.py
# reales (cada uno abre una sesion nueva), pero es relevante si se
# encadenan varias pruebas manuales en una sola sesion de exploracion.
# ============================================================================
#


def abrir_consulta_pagos(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Pagos"], "app-consulta-pago", paso_excel=paso_excel)


def elegir_nz_select(frame, app, select_id, texto_opcion):
    """Elige una opcion por su texto visible en un combo `nz-select`
    (ant-design) - estos combos NO son un <select> nativo, por lo que
    select_option() no sirve: hay que abrir el combo (click) y clickear
    la opcion dentro del overlay que ng-zorro agrega al DOM del propio
    frame (no al documento de nivel superior)."""
    frame.locator(f"nz-select#{select_id}").click()
    app.wait_for_timeout(400)
    opcion = frame.locator("nz-option-item, .ant-select-item-option").filter(
        has_text=re.compile(r"^\s*" + re.escape(texto_opcion) + r"\s*$")
    )
    opcion.first.click()
    app.wait_for_timeout(300)


def leer_pagos(app, frame):
    """Pulsa Leer (o Siguiente, tras el primer Leer exitoso) y cierra el
    dialogo de confirmacion ("sin filtro") si aparece, aceptandolo.
    Devuelve el texto del dialogo de VALIDACION si aparece uno
    (distinto del de confirmacion), o None si la consulta corrio
    directo."""
    frame.locator("button", has_text=re.compile(r"^\s*(Leer|Siguiente)\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        texto = modal.first.inner_text()
        if "confirmaci" in texto.lower():
            modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
            app.wait_for_timeout(3000)
            return None
        return texto
    return None


#
# Modulo: Mantenedor de Inspectores de Corte (Web LDS)
# Ruta de menu confirmada en vivo: Comercial > Mantenedor De Inspectores De Corte
# Sistema/frente de negocio: Cortes y Reconexiones (corterepos)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
# ============================================================================
#
# Requiere el rol funcional ANDESE1 - no visible en el menu para SCASTI_DW.
# Se exploro y valido con DCABA_DW/Melquisedec_01.
#
# Pantalla principal (`app-inspectores-listado`) SIN ningun `id` en sus
# elementos - toca localizar todo por rol/texto. Botones: Leer / Siguientes
# / Filtrar / Limpiar / Agregar / Detalles / Eliminar / Excel / Imprimir.
# Checkboxes: "Ampliar campos" y "Marcar todos" (label, no id). Grilla
# `table.resultados` con placeholder `td.sin-datos` cuando esta vacia.
#
# **Ventana de Filtro**: es un modal ng-zorro (`nz-modal-container`, dentro
# de un `[id^="cdk-overlay-"]`) SI tiene ids: `#flt-codigo`, `#flt-ficha`,
# `#flt-nombre`, `#flt-proveedor` (select), `#flt-estado` (select: ""=Todos,
# "S"=Activos, "N"=Noactivos), `#flt-sucursal` (select). Botones Filtrar/
# Limpiar/Cerrar DENTRO del overlay (hay 2 botones "Filtrar" en el DOM a la
# vez - el de la pantalla principal y el del modal - hay que ESCOPEAR el
# locator al overlay, si no Playwright tira "strict mode violation").
#
# **RN-01 confirmado**: al abrir, filtro vigente = "Estado = Activos", SIN
# consulta automatica. Botones Siguientes/Limpiar/Detalles/Eliminar/Excel/
# Imprimir arrancan `disabled`. Leer/Filtrar/Agregar SI estan habilitados.
#
# **HALLAZGO REAL IMPORTANTE - contradice el supuesto de la matriz para
# CP039**: presionar "Leer" con el filtro por defecto (Estado=Activos, SIN
# ningun otro filtro) da "Demasiados registros para ser mostrados en la
# grilla." (RN-03) - el universo REAL de inspectores activos en Pruebas
# supera el limite de 2000 registros. Lo mismo pasa con Estado=Noactivos
# solo (tambien >2000). La matriz asumia que el filtro por defecto ya
# devolveria un resultado dentro del limite (CP039 "Leer listado con
# resultados dentro del límite") - en la practica, SIEMPRE hay que combinar
# el default con al menos un filtro adicional (via Filtrar) para quedar
# debajo del limite. Documentar como observacion de datos/ambiente, no
# como bug de esta automatizacion.
#
# **RN-05 (Filtrar restablece el filtro vigente) confirmado**: tras
# CUALQUIER Filtrar (haya o no resultados), el filtro vigente vuelve a
# "Estado = Activos" - un "Leer" posterior YA NO reutiliza el filtro recien
# aplicado (confirmado: el resultado de Filtrar queda en pantalla, pero el
# texto "Filtro vigente" ya volvio a mostrar el default apenas se cierra el
# modal).
#
# **Mensajes reales confirmados** (modal "Ventana de Validación", boton
# "Aceptar"):
# - "Demasiados registros para ser mostrados en la grilla." (RN-03, sin
#   filtro suficiente)
# - "No existen registros para las condiciones indicadas." (RN-03, filtro
#   sin coincidencias - ej. Código="ZZZ999NOEXISTE")
#
# **RN (Código y Ficha simultaneos, CP042) confirmado tal cual el EF**: si
# se completan Código Y Ficha a la vez, Ficha GANA por completo - el
# resultado corresponde solo al filtro de Ficha, y el texto "Filtro
# vigente" muestra literalmente "Código" (la etiqueta fija, SIN el valor
# tecleado) en vez de "Código = <valor>" - ej.:
# "Filtro vigente: Estado = Activos | Ficha = 4504 | Código" (nunca
# "Código = 1"). Confirmado con Código="1" + Ficha="4504" -> unico
# resultado real: inspector 1381 (Rodriguez Medina Abel, Ficha 4504).
#
# **OBSERVACION (no confirmada como defecto): filas duplicadas en la
# grilla**. Al filtrar por Código="1" (coincidencia parcial), la grilla
# devuelve los codigos reales 1378/1379/1380/1381 - pero cada codigo
# aparece MULTIPLES veces como fila identica (mismos valores en todas las
# columnas, no son inspectores distintos). Podria ser data real asi en
# Pruebas (registros duplicados de verdad, ej. uno por sucursal en un Alta
# "Todas las sucursales" - ver RN de CP047) o un comportamiento del backend
# a confirmar con mas informacion - NO se concluye como bug, solo se deja
# anotado.
#
# **Estado=Todos - la etiqueta "Filtro vigente" NO SE ACTUALIZA visualmente
# (sigue diciendo "Estado = Activos")** aunque el `<select>` interno SI
# quedo en "" (Todos) y el resultado real parece incluir codigos que no se
# habian visto en la busqueda solo-Activos-con-Codigo=1 (1378/1379/1380
# ademas de 1381) - no se pudo confirmar la presencia de una fila
# REALMENTE Inactiva en los primeros 100 registros para poder probar CP043
# (marcado individual solo permite Activas) con datos 100% reales; queda
# pendiente explorar mas o usar otro codigo/filtro.
#
# **Alta/Modificacion/Eliminacion (CP044-048) son operaciones de
# ESCRITURA real sobre Pruebas** (dan de baja, crean o modifican
# inspectores reales) - no se ejecutan sin coordinar antes con el usuario,
# a diferencia de las consultas de solo lectura de este modulo.
# ============================================================================
#


def abrir_mantenedor_inspectores(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenedor De Inspectores De Corte"], "app-inspectores-listado", paso_excel=paso_excel)


def abrir_filtro_inspectores(app, frame):
    frame.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(800)
    return frame.locator("[id^='cdk-overlay-']").last


def aplicar_filtro_inspectores(app, overlay, codigo=None, ficha=None, nombre=None, estado_index=None, sucursal_label=None):
    if codigo is not None:
        overlay.locator("#flt-codigo").fill(codigo)
    if ficha is not None:
        overlay.locator("#flt-ficha").fill(ficha)
    if nombre is not None:
        overlay.locator("#flt-nombre").fill(nombre)
    if estado_index is not None:
        overlay.locator("#flt-estado").select_option(index=estado_index)
    if sucursal_label is not None:
        overlay.locator("#flt-sucursal").select_option(label=sucursal_label)
    app.wait_for_timeout(300)
    overlay.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(2000)


def cerrar_modal_inspectores(frame, boton="Aceptar"):
    boton_locator = frame.get_by_role("button", name=re.compile(rf"^\s*{boton}\s*$"))
    if boton_locator.count() > 0 and boton_locator.first.is_visible():
        boton_locator.first.click()
        return True
    return False


def filas_inspectores(frame):
    return frame.locator("table.resultados tbody tr").filter(has_not_text=re.compile("Sin registros"))


#
# Modulo: Consulta de Cortes Pendientes (Web LDS)
# Componente Angular: app-cortes-pendientes
# Ruta de menu confirmada en vivo: Comercial > Consulta De Cortes Pendientes
# Sistema/frente de negocio: Cortes y Reconexiones (corterepos/cortependi)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Filtros: Cliente (`#fld-cliente`), Sector
# (`#fld-sector`), Zona (`#fld-zona`), Sucursal (`nz-select#fld-sucursal`),
# Rol (`#fld-rol`), Contratista (`nz-select#fld-contratista`), tipo de
# F. Corte (`nz-select#fld-tipo-fecha`: =, >=, Entre) + Fecha inicial/final
# (inputs con `aria-label="Fecha inicial"`/`"Fecha final"`, el segundo solo
# aparece con tipo "Entre"), Origen/Estado Libro/Estado Detalle (selects).
# Botones Leer / "a Excel" (deshabilitado hasta tener resultado) / Limpiar.
#
# **Sucursales reales disponibles** (confirmado en vivo): Cañete,
# Chacarilla, Chorrillos, Chosica, La República, Miraflores, Pedro Miotta,
# San Bartolo, San Juan, Santa Anita, Sin Sucursal. Filtrar por
# CUALQUIERA de ellas ya devuelve resultados reales combinados (cortes de
# libro + solicitudes especiales) - no hace falta un cliente puntual.
#
# **gotcha de timing importante: la busqueda real (Leer con filtros
# validos) tarda ENTRE 10 Y 15 SEGUNDOS** en responder (confirmado en vivo,
# endpoint `BuscarCortesPendientes`) - mucho mas que cualquier otra
# pantalla de este proyecto. Un `wait_for_timeout` corto (1-2s, el patron
# usual de otras pantallas) deja el boton "Leer"/"Limpiar" todavia
# deshabilitados y hace fallar cualquier assert posterior con un timeout
# confuso. Usar SIEMPRE `leer_cortes_pendientes()` (sondeo hasta que
# termine, no una espera fija).
#
# **Mensajes reales confirmados** (via "Ventana de Validacion" modal,
# `.ant-modal`/`nz-modal-container`, icono "i", boton "Aceptar"):
# - "Debe Seleccionar algún filtro para la consulta" (RN-14, sin ningun filtro)
# - "Fecha Inválida" (RN-08, fecha con valor calendario inexistente)
# - "Debe Seleccionar Rango Inferior de Fecha" (RN-10, tipo de fecha elegido sin fecha inicial)
#
# **Gotcha real de nz-table (mismo patron que otros modulos de este
# proyecto): la fila placeholder "No hay datos" (`tr.ant-table-placeholder`)
# cuenta como `<tr>` igual que la fila fantasma `ant-table-measure-now` -
# excluir AMBAS siempre al contar filas reales.
#
# **DEFECTO REAL confirmado en vivo (28/09/2026): ingresar una fecha
# CALENDARIO VALIDA en el filtro F. Corte congela la pantalla por
# completo** - reproducido 5 veces con metodos de interaccion distintos
# (`press_sequentially`, `.fill()`, click en el calendario visual sobre un
# dia, click en el boton "Hoy") tanto en modo "=" como en modo "Entre".
# Sintomas: cualquier operacion posterior sobre el popup (`screenshot()`,
# `input_value()`, un nuevo `click()`) cuelga por 30s+ sin excepcion de
# JS ni error de consola ni llamada de red disparada (se descarto que sea
# un dialogo nativo bloqueante - no se detecto ninguno via
# `page.on("dialog")`). La ventana PRINCIPAL del portal (`page`, fuera del
# popup) sigue respondiendo con normalidad - el freeze es especifico del
# popup/pantalla. Una fecha INVALIDA (ej. "31/02/2026") o dejar el campo
# vacio NO producen el freeze (validan rapido, ver CP050/CP051). Esto
# bloquea cualquier caso de este modulo que necesite una fecha REAL para
# ejecutar una busqueda (ej. rango de fechas, filtro por fecha exacta
# valida) - documentar como defecto real a reportar, no reintentar mas sin
# un cambio real en el ambiente.
# ============================================================================
#


def abrir_consulta_cortes_pendientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Cortes Pendientes"], "app-cortes-pendientes", paso_excel=paso_excel)


def elegir_select_cortes(app, frame, select_id, texto_opcion):
    frame.locator(f"#{select_id}").click()
    app.wait_for_timeout(500)
    frame.locator(".ant-select-item-option").filter(has_text=texto_opcion).first.click()
    app.wait_for_timeout(400)


def filas_cortes_pendientes(frame):
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now):not(.ant-table-placeholder)")


def leer_cortes_pendientes(app, frame, timeout_ms=45000):
    """Pulsa Leer y espera a que termine: si aparece un dialogo de
    validacion, lo cierra y devuelve su texto; si la busqueda real
    termina (boton Limpiar se rehabilita), devuelve None. La busqueda
    real de esta pantalla puede tardar 10-15s - ver ficha tecnica."""
    boton_leer = frame.get_by_role("button", name=re.compile("Leer"))
    boton_limpiar = frame.get_by_role("button", name=re.compile("Limpiar"))
    boton_leer.click()
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
        if dialogo.count() > 0 and dialogo.first.is_visible():
            texto = dialogo.first.inner_text()
            dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
            app.wait_for_timeout(500)
            return texto
        if boton_limpiar.get_attribute("disabled") is None:
            return None
        app.wait_for_timeout(400)
    raise PWTimeoutError(f"leer_cortes_pendientes: no termino en {timeout_ms}ms")


def limpiar_cortes_pendientes(app, frame):
    frame.get_by_role("button", name=re.compile("Limpiar")).click()
    app.wait_for_timeout(600)


#
# Modulo: Consulta de Solicitudes de Reposicion Pendientes (Web LDS)
# Componente Angular: app-reposicion-pendiente
# Ruta de menu confirmada en vivo: Comercial > Consulta De Solicitudes De Reposicion Pendientes
# Sistema/frente de negocio: Cortes y Reposicion (CONREPEN)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
# ============================================================================
#
# **El "combo roto" documentado el 28/09/2026 NO se reproduce un mes
# despues** - ambos combos (`nz-select`) cargan con datos reales:
# "Sucursal Cliente" (12 opciones: "(Todas)" + 11 sucursales reales) y
# "Fecha de Solicitud" (3 opciones: "(Sin filtro)" / "=" / "Entre").
# Mismo patron de "problema transitorio, no permanente" ya confirmado en
# RF-02/03/05 de este mismo proyecto.
#
# **Selectores reales**: `nz-select` x2 (Sucursal Cliente, Fecha de
# Solicitud - orden de apertura en el DOM), inputs para N.° de Cliente y
# Sector, botones por texto exacto Leer/Limpiar/"a Excel"/Anular (Anular
# deshabilitado salvo con 1 solicitud pendiente/generada seleccionada).
# Grilla de resultados con 22 columnas reales.
#
# **Validacion real confirmada**: presionar Leer con TODOS los filtros en
# su estado por defecto (sin ningun filtro puesto) -> modal "Ventana de
# Validación": *"Debe Seleccionar algún filtro para la consulta"*.
# ============================================================================
#


def abrir_reposicion_pendientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Solicitudes De Reposicion Pendientes"], "app-reposicion-pendiente", paso_excel=paso_excel)


def leer_reposicion_pendientes(app, frame):
    """Pulsa Leer y devuelve el texto del modal de Ventana de
    Validacion si aparece (cerrandolo), o None si la consulta corrio
    directo."""
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        texto = modal.first.inner_text()
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return texto
    return None


#
# Modulo: Consulta Generica de Solicitudes de Reposicion (Web LDS)
# Componente Angular: app-consulta-generica-reposiciones
# Ruta de menu confirmada en vivo: Comercial > Consulta Generica De Solicitudes De Reposicion
# Sistema/frente de negocio: Reposiciones (recauda/CONSUREP)
#
# Este archivo es el INSUMO reutilizable para generar casos de prueba de
# este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
# depende de ningun proyecto puntual.
#
# ============================================================================
# FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
# ============================================================================
#
# Pantalla ng-zorro/Ant Design. Filtros: N.° de Cliente (`#fldCliente`),
# Sector (`#fldSector`), Sucursal Cliente (`nz-select#fldSucursal`), N.°
# Solicitud (`#fldSolicitud`), Estado Solicitud (`nz-select#fldEstado`),
# tipo de filtro de fecha OBLIGATORIO (`nz-select#fldTipoFecha`: "=",
# "Entre") + Fecha Inicial (`#fldFechaIni`, con calendario `nz-date-picker`
# asociado) / Fecha Final (solo visible con "Entre"). Botones Leer /
# Limpiar / "a Excel" (deshabilitado hasta tener resultado).
#
# **Mensajes reales confirmados** (via "Ventana de Validacion" modal,
# `.ant-modal`/`nz-modal-container`, icono "i", boton "Aceptar"):
# - "Debe Seleccionar Filtro de Fechas" (RN-07, ningun tipo de fecha elegido)
# - "Fecha Inválida" (RN-06, fecha con valor calendario inexistente)
# - "Debe Seleccionar Rango Inferior de Fecha" (RN-08, tipo elegido sin fecha inicial)
#
# **DEFECTO REAL CRITICO, confirmado en 2 PANTALLAS DISTINTAS del mismo
# proyecto (ver tambien `consulta_cortes_pendientes.py`): ingresar una
# fecha calendario VALIDA en cualquier campo de fecha de este tipo
# (`nz-date-picker` + input asociado) congela la pantalla por completo.**
# Reproducido aca con `press_sequentially` normal Y con delay de 300ms por
# caracter (descarta que sea un artefacto de automatizacion "demasiado
# rapida" - el freeze ocurre incluso escribiendo lento, a mitad de la
# cadena de caracteres). Sintoma identico al de RF-07: cualquier operacion
# posterior sobre el popup (`screenshot()`, etc.) cuelga 30s+ sin
# excepcion de JS, sin error de consola, sin dialogo nativo. Una fecha
# INVALIDA o el campo vacio NO producen el freeze (validan rapido). Dado
# que se reproduce IGUAL en 2 aplicativos Angular distintos (con
# estructura de date-picker ligeramente distinta en el HTML), es probable
# que sea un defecto compartido de una libreria/version de componente
# comun a varias pantallas de este sprint - **cualquier caso que necesite
# ingresar una fecha calendario real y valida en un filtro de este tipo
# queda bloqueado hasta que se resuelva en el ambiente.**
# ============================================================================
#


def abrir_consulta_generica_reposiciones(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta Generica De Solicitudes De Reposicion"], "app-consulta-generica-reposiciones", paso_excel=paso_excel)


def elegir_select_reposiciones(app, frame, select_id, texto_opcion=None):
    """Si texto_opcion es None, elige la primera opcion real disponible
    (util para 'tipo de fecha' cuando cualquier valor sirve, ej. '=')."""
    frame.locator(f"#{select_id}").click()
    app.wait_for_timeout(500)
    opciones = frame.locator(".ant-select-item-option")
    if texto_opcion is None:
        opciones.first.click()
    else:
        opciones.filter(has_text=texto_opcion).first.click()
    app.wait_for_timeout(400)


def cerrar_ventana_validacion_reposiciones(app, frame, timeout_ms=4000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
    app.wait_for_timeout(500)
    return texto


def leer_reposiciones(app, frame):
    frame.get_by_role("button", name=re.compile("Leer")).click()
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
            login(page)
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
                rutas_videos.extend(sorted(EVIDENCIA.glob("page@*.webm")))
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
