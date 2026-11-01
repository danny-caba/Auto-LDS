"""
intervencion.py - Intervencion manual y exploracion asistida (Etapa 4
del piloto Auto-LDS, MS024472).

Permite que un caso de prueba, cuando no puede seguir solo (falta un
dato, hay una duda funcional, o la automatizacion se traba), pause y le
pida ayuda a la persona desde la terminal integrada de VS Code, en vez
de fallar en silencio o inventar un resultado.

No depende de Claude CLI ni de ninguna API de IA - es interaccion
humano<->terminal directa (input()/print()), mas Playwright para la
exploracion visible. No se integra solo a ningun proyecto - hace falta
que el `caso_fn` de cada caso este escrito para lanzar
`BloqueoRequiereIntervencion` explicitamente (ver mas abajo).

---------------------------------------------------------------------
QUE CAPTURA ESTE MECANISMO Y QUE NO (leer antes de confiar en el registro)
---------------------------------------------------------------------
SI registra: el motivo que el caso declaro al bloquearse, la opcion que
elegiste, el texto que escribiste como observacion/dato, el timestamp
de cada paso, y (si elegiste exploracion manual) una captura de
pantalla tomada justo antes de cerrar el navegador.

NO registra: cualquier otra accion que hagas dentro del navegador
durante la exploracion manual (clics, scrolls, que pantallas mirates) -
el mecanismo NO instrumenta tu sesion de exploracion, solo abre el
navegador y espera a que le digas "listo". No declarar en ningun reporte
que se "grabaron las acciones manuales" mas alla de lo que esta lista
cubre.

---------------------------------------------------------------------
MODELO DE EJECUCION (limitacion a tener presente)
---------------------------------------------------------------------
Este modulo esta pensado para `caso_fn` ejecutado EN EL MISMO PROCESO
(como se valida en validar_intervencion_local.py, con una pagina HTML
local via Playwright). Los CPxxx.py reales de cualquier proyecto corren
hoy como SUBPROCESOS aislados (ver run_all.py) - integrar esto con esa
arquitectura (p.ej. un CPxxx.py que puede "pausar" a mitad de su propio
proceso hijo y que el padre lo sepa) es un trabajo de integracion
pendiente, fuera del alcance de esta etapa. Por ahora, "suspender el
timeout" se implementa como contabilidad de tiempo EN PROCESO (no
cuenta el tiempo de espera humana contra el reloj del caso) - no como
una pausa real del `subprocess.run(timeout=...)` de run_all.py, que
hoy no sabe nada de esto.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resultados as r  # noqa: E402

ACCIONES = ("APORTAR_DATO", "EXPLORACION_MANUAL", "REINTENTAR", "PENDIENTE")


class BloqueoRequiereIntervencion(Exception):
    """Un `caso_fn` lanza esto cuando no puede seguir solo. Los 3
    primeros campos son obligatorios y se le muestran tal cual a la
    persona - escribirlos pensando en que alguien que no vio el codigo
    los tiene que entender."""

    def __init__(self, que_intentaba: str, que_encontro: str, que_necesita: str,
                 comprobaciones_pendientes: list[str] | None = None):
        self.que_intentaba = que_intentaba
        self.que_encontro = que_encontro
        self.que_necesita = que_necesita
        self.comprobaciones_pendientes = comprobaciones_pendientes or []
        super().__init__(que_encontro)


@dataclass
class _Observacion:
    accion: str
    texto: str | None
    marca_tiempo: str = field(default_factory=lambda: datetime.now().isoformat())


def _mostrar_bloqueo(bloqueo: BloqueoRequiereIntervencion, cp: str, salida_fn: Callable[[str], None]) -> None:
    salida_fn("=" * 60)
    salida_fn(f"BLOQUEO - {cp} necesita tu ayuda")
    salida_fn("=" * 60)
    salida_fn(f"Que intentaba verificar: {bloqueo.que_intentaba}")
    salida_fn(f"Que encontro: {bloqueo.que_encontro}")
    salida_fn(f"Que necesita: {bloqueo.que_necesita}")
    if bloqueo.comprobaciones_pendientes:
        salida_fn("Comprobaciones pendientes:")
        for c in bloqueo.comprobaciones_pendientes:
            salida_fn(f"  - {c}")
    salida_fn("")
    salida_fn("Opciones:")
    salida_fn("  [1] Aportar un dato o una observacion")
    salida_fn("  [2] Iniciar exploracion manual (navegador visible)")
    salida_fn("  [3] Reintentar (sin cambios)")
    salida_fn("  [4] Dejar pendiente y continuar con otros casos")


def _pedir_accion(entrada_fn: Callable[[str], str], salida_fn: Callable[[str], None]) -> str:
    while True:
        resp = entrada_fn("> ").strip()
        mapa = {"1": "APORTAR_DATO", "2": "EXPLORACION_MANUAL", "3": "REINTENTAR", "4": "PENDIENTE"}
        if resp in mapa:
            return mapa[resp]
        salida_fn(f"Opcion no reconocida: {resp!r} - escribi 1, 2, 3 o 4.")


def exploracion_manual_visible(
    url: str | None,
    *,
    entrada_fn: Callable[[str], str] = input,
    salida_fn: Callable[[str], None] = print,
    channel: str = "msedge",
    carpeta_evidencia: Path | None = None,
) -> dict:
    """Abre un navegador VISIBLE (headless=False) en `url` (si se pasa)
    y espera a que la persona escriba 'listo' en la terminal para
    cerrarlo. Devuelve {"captura": ruta_o_None, "duracion_seg": N}.
    Cierra el browser/context/playwright SIEMPRE (try/finally), incluso
    si algo falla a mitad de la exploracion - nunca deja un proceso de
    Chromium/Edge huerfano."""
    from playwright.sync_api import sync_playwright

    salida_fn("\nAbriendo navegador visible para exploracion manual...")
    salida_fn("Navega libremente. Escribi 'listo' + Enter cuando termines (esto cierra el navegador).")
    inicio = time.monotonic()
    captura_ruta = None
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel, headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            if url:
                page.goto(url)
            while True:
                resp = entrada_fn("(escribi 'listo' para cerrar) > ").strip().lower()
                if resp == "listo":
                    break
                salida_fn("Todavia no escribiste 'listo' - seguis en exploracion manual.")
            if carpeta_evidencia is not None:
                carpeta_evidencia.mkdir(parents=True, exist_ok=True)
                captura_ruta = carpeta_evidencia / "exploracion_manual_final.png"
                try:
                    page.screenshot(path=str(captura_ruta))
                except Exception as e:  # noqa: BLE001 - best-effort, no debe tumbar el cierre
                    salida_fn(f"(aviso) no se pudo capturar la pantalla final: {e}")
                    captura_ruta = None
        finally:
            browser.close()
    duracion = time.monotonic() - inicio
    salida_fn(f"Navegador cerrado. Exploracion manual duro {duracion:.1f}s.\n")
    return {"captura": str(captura_ruta) if captura_ruta else None, "duracion_seg": round(duracion, 1)}


def ejecutar_con_intervencion(
    pdir: Path,
    run_id: str,
    cp: str,
    rf: str,
    cu: str,
    caso_fn: Callable[[dict], dict],
    *,
    max_reintentos: int = 3,
    url_para_exploracion: str | None = None,
    entrada_fn: Callable[[str], str] = input,
    salida_fn: Callable[[str], None] = print,
    origen_evidencia: Path | None = None,
) -> dict:
    """Corre `caso_fn(contexto)` en modo asistido SECUENCIAL (ver
    ColaPendientes para el modo cola, pensado para no bloquear
    workers paralelos). `caso_fn` recibe un dict `contexto` (mutable,
    se le van agregando los datos que la persona aporte entre
    reintentos) y debe devolver un dict con al menos
    {"estado_funcional", "esperado", "obtenido",
    "comprobaciones_completadas"} (ver ESTADOS_FUNCIONALES en
    resultados.py), o lanzar BloqueoRequiereIntervencion si no puede
    terminar.

    Reintentar SIEMPRE vuelve a correr `caso_fn` desde el principio
    (nunca retoma una linea a mitad de script) - si `caso_fn` hace
    escrituras no idempotentes, es responsabilidad de quien lo escribe
    dejarlo seguro para reintentar (mismo patron ya usado en otros
    proyectos: un caso que registra su propio dato descartable al
    inicio en vez de depender de estado previo incierto)."""
    contexto: dict = {}
    observaciones: list[_Observacion] = []
    hubo_intervencion = False
    intento_anterior: int | None = None
    tiempo_activo_acumulado = 0.0

    # time.time() (reloj de pared) a proposito, no time.monotonic(): estos
    # valores se persisten tal cual como inicio/fin reales del caso (ver
    # registrar_resultado() en resultados.py, que los convierte con
    # datetime.fromtimestamp() - monotonic() no es un timestamp real y
    # daria fechas sin sentido, ej. 1970).
    inicio_total = time.time()
    intento_actual = 1
    while True:
        t_inicio_intento = time.time()
        try:
            resultado_caso = caso_fn(contexto)
            tiempo_activo_acumulado += time.time() - t_inicio_intento
            break
        except BloqueoRequiereIntervencion as bloqueo:
            tiempo_activo_acumulado += time.time() - t_inicio_intento
            hubo_intervencion = True

            _mostrar_bloqueo(bloqueo, cp, salida_fn)
            accion = _pedir_accion(entrada_fn, salida_fn)

            if accion == "APORTAR_DATO":
                dato = entrada_fn("Dato/observacion a aportar: ")
                contexto["aporte"] = dato
                observaciones.append(_Observacion("APORTAR_DATO", dato))
                salida_fn("Dato guardado. Reintentando con ese dato...\n")
                intento_anterior = intento_actual
                intento_actual += 1
                continue

            if accion == "EXPLORACION_MANUAL":
                carpeta_ev = r._carpeta_intento(pdir, run_id, cp, intento_actual) / "evidencia"
                info_exploracion = exploracion_manual_visible(
                    url_para_exploracion, entrada_fn=entrada_fn, salida_fn=salida_fn,
                    carpeta_evidencia=carpeta_ev,
                )
                observaciones.append(_Observacion("EXPLORACION_MANUAL", f"duracion={info_exploracion['duracion_seg']}s captura={info_exploracion['captura']}"))
                salida_fn("Exploracion terminada. Elegi que hacer ahora:")
                # Tras explorar, se vuelve a preguntar (reintentar o pendiente) con el mismo menu completo
                _mostrar_bloqueo(bloqueo, cp, salida_fn)
                accion2 = _pedir_accion(entrada_fn, salida_fn)
                if accion2 == "REINTENTAR" or accion2 == "APORTAR_DATO":
                    if accion2 == "APORTAR_DATO":
                        dato = entrada_fn("Dato/observacion a aportar: ")
                        contexto["aporte"] = dato
                        observaciones.append(_Observacion("APORTAR_DATO", dato))
                    intento_anterior = intento_actual
                    intento_actual += 1
                    continue
                else:
                    resultado_caso = {
                        "estado_funcional": "BLOQUEADO_DATOS",
                        "esperado": None, "obtenido": None,
                        "comprobaciones_completadas": [], "comprobaciones_pendientes": bloqueo.comprobaciones_pendientes,
                    }
                    break

            if accion == "REINTENTAR":
                if intento_actual >= max_reintentos:
                    salida_fn(f"Se llego al maximo de reintentos ({max_reintentos}) - queda PENDIENTE.")
                    resultado_caso = {
                        "estado_funcional": "BLOQUEADO_DATOS",
                        "esperado": None, "obtenido": bloqueo.que_encontro,
                        "comprobaciones_completadas": [], "comprobaciones_pendientes": bloqueo.comprobaciones_pendientes,
                    }
                    break
                observaciones.append(_Observacion("REINTENTAR", None))
                intento_anterior = intento_actual
                intento_actual += 1
                continue

            if accion == "PENDIENTE":
                observaciones.append(_Observacion("PENDIENTE", None))
                resultado_caso = {
                    "estado_funcional": "BLOQUEADO_DATOS",
                    "esperado": None, "obtenido": bloqueo.que_encontro,
                    "comprobaciones_completadas": [], "comprobaciones_pendientes": bloqueo.comprobaciones_pendientes,
                }
                break

    fin_total = time.time()

    registro_intervencion = None
    if hubo_intervencion:
        registro_intervencion = {
            "motivo": observaciones[0].accion if observaciones else None,
            "observaciones": [{"accion": o.accion, "texto": o.texto, "marca_tiempo": o.marca_tiempo} for o in observaciones],
            "intento_anterior": intento_anterior,
            "tiempo_activo_total_seg": round(tiempo_activo_acumulado, 1),
            "tiempo_total_con_espera_seg": round(fin_total - inicio_total, 1),
        }

    tipo_ejecucion = "MIXTA" if hubo_intervencion else "AUTOMATICA"

    registro = r.registrar_resultado(
        pdir, run_id, cp,
        rf=rf, cu=cu,
        intento=intento_actual,
        estado_funcional=resultado_caso["estado_funcional"],
        inicio=inicio_total, fin=fin_total,
        tipo_ejecucion=tipo_ejecucion,
        esperado=resultado_caso.get("esperado"),
        obtenido=resultado_caso.get("obtenido"),
        comprobaciones_completadas=resultado_caso.get("comprobaciones_completadas"),
        comprobaciones_pendientes=resultado_caso.get("comprobaciones_pendientes"),
        origen_evidencia=origen_evidencia,
        intervencion=registro_intervencion,
    )
    return registro


@dataclass
class _Pendiente:
    cp: str
    rf: str
    cu: str
    caso_fn: Callable[[dict], dict]
    bloqueo: BloqueoRequiereIntervencion
    origen_evidencia: Path | None = None


class ColaPendientes:
    """Alternativa a `ejecutar_con_intervencion()` para cuando varios
    casos corren en paralelo (--workers > 1): en vez de que CADA worker
    se quede esperando input() y bloquee a los demas, un worker que
    choca con un bloqueo lo ENCOLA aca (encolar()) y sigue con el
    siguiente caso. Despues del batch, se procesa la cola completa en
    modo secuencial (procesar_secuencial()) - la persona atiende los
    bloqueos de a uno, sin que ningun worker haya quedado trabado
    esperandola."""

    def __init__(self, pdir: Path, run_id: str):
        self.pdir = pdir
        self.run_id = run_id
        self._pendientes: list[_Pendiente] = []

    def encolar(self, cp: str, rf: str, cu: str, caso_fn, bloqueo: BloqueoRequiereIntervencion, origen_evidencia: Path | None = None) -> None:
        self._pendientes.append(_Pendiente(cp, rf, cu, caso_fn, bloqueo, origen_evidencia))

    def __len__(self) -> int:
        return len(self._pendientes)

    def procesar_secuencial(self, *, entrada_fn: Callable[[str], str] = input, salida_fn: Callable[[str], None] = print, url_para_exploracion: str | None = None) -> list[dict]:
        registros = []
        salida_fn(f"\n{len(self._pendientes)} caso(s) quedaron pendientes de intervencion - procesando de a uno.\n")
        for p in self._pendientes:
            registro = ejecutar_con_intervencion(
                self.pdir, self.run_id, p.cp, p.rf, p.cu, p.caso_fn,
                url_para_exploracion=url_para_exploracion,
                entrada_fn=entrada_fn, salida_fn=salida_fn,
                origen_evidencia=p.origen_evidencia,
            )
            registros.append(registro)
        self._pendientes.clear()
        return registros
