"""
Orquesta los subprocesos que hacen el trabajo real: `nuevo_proyecto.py`
(bootstrap), `claude -p` (exploracion/generacion con IA, si esta
instalado), `run_all.py` (ejecutar pruebas) y `generar_reporte_excel.py`
(reporte). No reimplementa nada de esa logica - solo los invoca como
subprocess y va actualizando `estado_actual.json` (via estado.py) para
que server.py lo sirva por polling.

Cada flujo largo corre en un hilo de fondo (threading, no
multiprocessing - el paralelismo real de navegadores ya lo hace
run_all.py con sus propios subprocess). Un registro simple evita lanzar
dos flujos a la vez sobre el mismo proyecto.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import estado
import claude_prompt

RAIZ = Path(__file__).resolve().parent.parent.parent  # C:\AUTOMATIZACION_LDS
FRAMEWORK_DIR = RAIZ / "_framework"
PYTHON = Path(sys.executable)

_LOCK = threading.Lock()
_PROCESOS_ACTIVOS: dict[str, threading.Thread] = {}

_RE_PROGRESO_SECUENCIAL = re.compile(r"^\[(\d+)/(\d+)\]\s+(\S+)\s+\.\.\.\s*(OK|FALLO|TIMEOUT|ERROR)?\s*(?:\(([\d.]+)s\))?")
_RE_PROGRESO_PARALELO = re.compile(r"^\[(\d+)/(\d+)\]\s+(\S+):\s*(OK|FALLO|TIMEOUT|ERROR)\s*\(([\d.]+)s\)")
_RE_WEBAPP_RESUMEN = re.compile(r"WEBAPP_RESUMEN:\s*(\{.*\})\s*$")


class ProcesoEnCursoError(Exception):
    pass


def proyecto_dir(proyecto: str) -> Path:
    return RAIZ / proyecto


def _generar_reporte_preliminar(pdir: Path) -> None:
    """Corre generar_reporte_excel.py apenas hay matriz_casos.json, sin
    esperar a que se ejecute ningun caso - todo CP que no aparezca en
    ningun reporte_*.csv queda como "SIN CORRER", y Nombre/Ventana por
    RF salen de rf_nombres.json si ya existe (vacios si todavia no).
    Pensado para que la pestana Reporte de la webapp tenga algo que
    mostrar apenas se carga el Excel, en vez de un 404 hasta la primera
    corrida real. Best-effort: una falla aca NO debe tumbar el flujo
    que la llama (bootstrap/exploracion siguen siendo el resultado
    principal), solo se deja constancia en el log del proyecto."""
    try:
        shutil.copy2(FRAMEWORK_DIR / "generar_reporte_excel.py", pdir / "generar_reporte_excel.py")
        rc = _correr_subprocess_lineas(
            [str(PYTHON), "-u", str(pdir / "generar_reporte_excel.py")], cwd=pdir,
            on_linea=lambda l: estado.agregar_log(pdir, l),
        )
        if rc != 0:
            estado.agregar_log(pdir, f"[aviso] reporte preliminar: generar_reporte_excel.py termino con codigo {rc}")
    except Exception as e:  # noqa: BLE001
        estado.agregar_log(pdir, f"[aviso] no se pudo generar el reporte preliminar: {e}")


def _registrar_hilo(proyecto: str, hilo: threading.Thread) -> None:
    with _LOCK:
        activo = _PROCESOS_ACTIVOS.get(proyecto)
        if activo is not None and activo.is_alive():
            raise ProcesoEnCursoError(f"Ya hay un proceso en curso para {proyecto!r}")
        _PROCESOS_ACTIVOS[proyecto] = hilo


def hay_proceso_en_curso(proyecto: str) -> bool:
    with _LOCK:
        hilo = _PROCESOS_ACTIVOS.get(proyecto)
        return hilo is not None and hilo.is_alive()


def _correr_subprocess_lineas(cmd: list[str], cwd: Path, on_linea) -> int:
    """Corre `cmd`, invocando `on_linea(texto)` por cada linea de
    stdout+stderr conforme aparece (no espera a que termine). Devuelve
    el codigo de salida.

    BUG REAL encontrado y corregido (Etapa 6 del piloto, 31/10/2026):
    `encoding="utf-8"` aca abajo solo controla como el PADRE decodifica
    los bytes que ya llegaron por el pipe - no fuerza que el HIJO
    (CPxxx.py, que puede imprimir texto de la pantalla real, ej. el
    caracter "☰" del menu de Web LDS) use UTF-8 para sus propios
    print(). Sin PYTHONIOENCODING explicito, un hijo de Python en
    Windows puede arrancar con el codepage de consola por defecto
    (cp1252/"charmap", sin soporte para esos caracteres) y crashear con
    UnicodeEncodeError apenas imprime algo asi - confirmado en vivo:
    el mismo CPxxx.py corria perfecto invocado directo desde una
    terminal, y crasheaba corrido COMO HIJO de este webapp."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None
    for linea in proc.stdout:
        on_linea(linea.rstrip("\n"))
    proc.wait()
    return proc.returncode


def lanzar_bootstrap(
    proyecto: str,
    excel_path: Path,
    ef_path: Path | None,
    et_path: Path | None,
    extra_paths: list[Path] | None = None,
    proyecto_base: str | None = None,
) -> None:
    """Solo carga documentos + extrae matriz/EF/ET (`nuevo_proyecto.py`).
    NO dispara exploracion/generacion con IA - eso es `lanzar_explorar()`,
    una accion aparte que el usuario dispara explicitamente despues de
    revisar que la carga quedo bien (separacion pedida para el piloto
    MS024472, antes esto estaba encadenado sin pausa en una sola
    funcion).

    `proyecto_base` (opcional): si se pasa, es una NUEVA ITERACION de un
    proyecto existente - se copia su `generate_scripts.py` (y
    `casos_fallidos_confirmados.json` si tiene) en vez de dejar el
    esqueleto vacio. SIEMPRE pedido de forma explicita (nunca se
    adivina por el nombre) - decision tomada en la Etapa 6 del piloto."""
    hilo = threading.Thread(
        target=_bootstrap,
        args=(proyecto, excel_path, ef_path, et_path, extra_paths or [], proyecto_base),
        daemon=True,
    )
    _registrar_hilo(proyecto, hilo)
    hilo.start()


def _bootstrap(
    proyecto: str,
    excel_path: Path,
    ef_path: Path | None,
    et_path: Path | None,
    extra_paths: list[Path],
    proyecto_base: str | None = None,
) -> None:
    pdir = proyecto_dir(proyecto)
    estado.actualizar(pdir, fase="bootstrap", mensaje="Creando estructura y extrayendo matriz...", log=[])

    cmd = [str(PYTHON), "-u", str(FRAMEWORK_DIR / "nuevo_proyecto.py"), proyecto, "--excel", str(excel_path)]
    if ef_path is not None:
        cmd += ["--ef", str(ef_path)]
    if et_path is not None:
        cmd += ["--et", str(et_path)]
    for extra_path in extra_paths:
        cmd += ["--extra", str(extra_path)]

    try:
        rc = _correr_subprocess_lineas(cmd, cwd=FRAMEWORK_DIR, on_linea=lambda l: estado.agregar_log(pdir, l))
    except Exception as e:  # noqa: BLE001
        estado.actualizar(pdir, fase="bootstrap_error", mensaje=f"Excepcion al correr nuevo_proyecto.py: {e}")
        return

    if rc != 0:
        estado.actualizar(pdir, fase="bootstrap_error", mensaje=f"nuevo_proyecto.py termino con codigo {rc}")
        return

    if not (pdir / "matriz_casos.json").exists():
        estado.actualizar(pdir, fase="bootstrap_error", mensaje="nuevo_proyecto.py termino OK pero no se genero matriz_casos.json")
        return

    if proyecto_base:
        _copiar_de_proyecto_base(proyecto, proyecto_base, pdir)

    _generar_reporte_preliminar(pdir)

    estado.actualizar(pdir, fase="bootstrap_ok", mensaje="Bootstrap completo. matriz_casos.json generado. Revisa la carga y, cuando quieras, dispara la exploracion con IA aparte.")


def _copiar_de_proyecto_base(proyecto: str, proyecto_base: str, pdir: Path) -> None:
    """Copia generate_scripts.py (pisando el esqueleto vacio que ya dejo
    nuevo_proyecto.py) y casos_fallidos_confirmados.json (si existe) del
    proyecto base, y corrige la linea `PROYECTO = "..."` para que
    coincida con el nombre de la carpeta NUEVA.

    BUG REAL que esto evita (confirmado en vivo, PR000349-SP3-IT2,
    29/10/2026): si se clona `generate_scripts.py` de un proyecto a otro
    sin actualizar `PROYECTO`, TODOS los toggles de entorno de cada
    CPxxx.py generado (GRABAR_VIDEO, etc.) quedan esperando el prefijo
    VIEJO en silencio, sin ningun error - costo una sesion entera
    detectarlo la primera vez que paso a mano."""
    pdir_base = proyecto_dir(proyecto_base)
    origen = pdir_base / "generate_scripts.py"
    destino = pdir / "generate_scripts.py"
    contenido = origen.read_text(encoding="utf-8")
    contenido_corregido = re.sub(
        r'PROYECTO\s*=\s*"[^"]*"',
        f'PROYECTO = "{proyecto}"',
        contenido,
        count=1,
    )
    cambio_proyecto = contenido_corregido != contenido
    destino.write_text(contenido_corregido, encoding="utf-8")
    estado.agregar_log(pdir, f"[iteracion] generate_scripts.py copiado de {proyecto_base} (PROYECTO actualizado: {cambio_proyecto}).")

    casos_fallidos_base = pdir_base / "casos_fallidos_confirmados.json"
    if casos_fallidos_base.is_file():
        shutil.copy2(casos_fallidos_base, pdir / "casos_fallidos_confirmados.json")
        estado.agregar_log(pdir, f"[iteracion] casos_fallidos_confirmados.json tambien copiado de {proyecto_base} - revisar si sigue vigente.")


def lanzar_explorar(proyecto: str) -> None:
    """Dispara la exploracion/generacion con IA sobre un proyecto YA
    bootstrapeado (requiere matriz_casos.json existente - ver
    `lanzar_bootstrap()`). Accion separada y explicita, nunca encadenada
    automaticamente despues de la carga."""
    pdir = proyecto_dir(proyecto)
    if not (pdir / "matriz_casos.json").exists():
        raise FileNotFoundError(f"{proyecto} no tiene matriz_casos.json todavia - correr lanzar_bootstrap() primero")
    hilo = threading.Thread(target=_explorar, args=(proyecto,), daemon=True)
    _registrar_hilo(proyecto, hilo)
    hilo.start()


def _explorar(proyecto: str) -> None:
    pdir = proyecto_dir(proyecto)
    estado.actualizar(pdir, fase="explorando_preparando", mensaje="Preparando la exploracion...", log=[])

    claude_disponible = shutil.which("claude") is not None
    estado.actualizar(pdir, claude_disponible=claude_disponible)

    prompt = claude_prompt.construir_prompt(proyecto, pdir)
    (pdir / "prompt_exploracion.txt").write_text(prompt, encoding="utf-8")

    if not claude_disponible:
        estado.actualizar(
            pdir,
            fase="exploracion_manual_pendiente",
            mensaje="El CLI 'claude' no esta instalado en esta maquina - continua la exploracion en una sesion interactiva de Claude Code con el prompt de abajo.",
            prompt_exploracion=prompt,
        )
        return

    estado.actualizar(pdir, fase="exploracion_ia", mensaje="Explorando la app y generando casos con IA (esto puede tardar bastante)...")

    def _on_linea_claude(linea: str) -> None:
        estado.agregar_log(pdir, linea)
        m = _RE_WEBAPP_RESUMEN.search(linea)
        if m:
            try:
                resumen = json.loads(m.group(1))
                estado.actualizar(pdir, resultado_final=resumen)
            except json.JSONDecodeError:
                pass

    cmd_claude = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
    ]
    try:
        rc = _correr_subprocess_lineas(cmd_claude, cwd=pdir, on_linea=_on_linea_claude)
    except Exception as e:  # noqa: BLE001
        estado.actualizar(pdir, fase="exploracion_error", mensaje=f"Excepcion al correr claude -p: {e}")
        return

    # Fuente de verdad del progreso real: contar CPxxx.py en disco, no
    # confiar solo en el parseo (best-effort) del stream de claude.
    n_generados = len(list(pdir.glob("CP*.py")))
    matriz_path = pdir / "matriz_casos.json"
    n_total = 0
    if matriz_path.exists():
        try:
            n_total = len(json.loads(matriz_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass

    pendientes_path = pdir / "pendientes_revision.json"
    n_pendientes = 0
    if pendientes_path.exists():
        try:
            n_pendientes = len(json.loads(pendientes_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass

    resultado_final = {"casos_generados": n_generados, "casos_total": n_total, "casos_pendientes_revision": n_pendientes}

    # Best-effort: si la exploracion escribio/actualizo rf_nombres.json,
    # el reporte preliminar se refresca con el Nombre/Ventana reales -
    # sigue "SIN CORRER" en todos los CP (ningun caso corrio todavia).
    _generar_reporte_preliminar(pdir)

    if rc != 0:
        estado.actualizar(pdir, fase="exploracion_error", mensaje=f"claude -p termino con codigo {rc}", resultado_final=resultado_final)
    else:
        estado.actualizar(pdir, fase="exploracion_terminada", mensaje="Exploracion y generacion terminada.", resultado_final=resultado_final)


def lanzar_ejecutar_pruebas(proyecto: str, rf_list: list[str], video: bool) -> None:
    hilo = threading.Thread(target=_ejecutar_pruebas, args=(proyecto, rf_list, video), daemon=True)
    _registrar_hilo(proyecto, hilo)
    hilo.start()


def _ejecutar_pruebas(proyecto: str, rf_list: list[str], video: bool) -> None:
    pdir = proyecto_dir(proyecto)

    # run_all.py, generar_reporte_excel.py y ejecutar_con_resultados.py
    # son "copia textual" por proyecto (ver NUEVO_PROYECTO_CHECKLIST.md
    # Seccion 7) - se refrescan aca para que un proyecto viejo herede
    # --rf/la persistencia de resultados sin tener que ir a mano a
    # re-copiar el archivo.
    shutil.copy2(FRAMEWORK_DIR / "run_all.py", pdir / "run_all.py")
    shutil.copy2(FRAMEWORK_DIR / "generar_reporte_excel.py", pdir / "generar_reporte_excel.py")
    shutil.copy2(FRAMEWORK_DIR / "ejecutar_con_resultados.py", pdir / "ejecutar_con_resultados.py")

    estado.actualizar(pdir, fase="ejecutando_pruebas", mensaje=f"Ejecutando RF: {', '.join(rf_list)}", log=[], progreso={"actual": 0, "total": 0, "cp_actual": ""}, prompt_ejecucion=None)

    # Se usa ejecutar_con_resultados.py (no run_all.py directo) para que
    # cada corrida desde la web tambien quede persistida en
    # resultados/<run_id>/<CP>/<intento>/ (Etapa 3) - no pisa evidencia
    # de corridas anteriores, a diferencia de correr run_all.py solo.
    cmd = [str(PYTHON), "-u", str(pdir / "ejecutar_con_resultados.py"), "--rf", ",".join(rf_list)]
    if video:
        cmd.append("--video")

    resumen_ejecucion = {}

    def _on_linea(linea: str) -> None:
        estado.agregar_log(pdir, linea)
        m = _RE_PROGRESO_SECUENCIAL.match(linea) or _RE_PROGRESO_PARALELO.match(linea)
        if m:
            actual, total, cp = m.group(1), m.group(2), m.group(3)
            estado.actualizar(pdir, progreso={"actual": int(actual), "total": int(total), "cp_actual": cp})
            return
        m2 = _RE_WEBAPP_RESUMEN.search(linea)
        if m2:
            try:
                resumen_ejecucion.update(json.loads(m2.group(1)))
            except json.JSONDecodeError:
                pass

    try:
        rc = _correr_subprocess_lineas(cmd, cwd=pdir, on_linea=_on_linea)
    except Exception as e:  # noqa: BLE001
        estado.actualizar(pdir, fase="reporte_error", mensaje=f"Excepcion al correr ejecutar_con_resultados.py: {e}")
        return

    # Si algun caso no dio OK, ejecutar_con_resultados.py arma un prompt
    # de ayuda (diagnostico) en su WEBAPP_RESUMEN - se muestra en la web
    # con el mismo patron que el prompt de exploracion (texto + boton de
    # copiar), para llevarlo a una sesion de Claude Code.
    prompt_ejecucion = resumen_ejecucion.get("prompt_ayuda")
    if prompt_ejecucion:
        estado.actualizar(pdir, prompt_ejecucion=prompt_ejecucion)

    estado.actualizar(pdir, fase="generando_reporte", mensaje="Corrida terminada, generando reporte consolidado...")

    try:
        rc_reporte = _correr_subprocess_lineas(
            [str(PYTHON), "-u", str(pdir / "generar_reporte_excel.py")], cwd=pdir,
            on_linea=lambda l: estado.agregar_log(pdir, l),
        )
    except Exception as e:  # noqa: BLE001
        estado.actualizar(pdir, fase="reporte_error", mensaje=f"Excepcion al generar el reporte: {e}")
        return

    if rc_reporte != 0:
        estado.actualizar(pdir, fase="reporte_error", mensaje=f"generar_reporte_excel.py termino con codigo {rc_reporte}")
        return

    estado.actualizar(
        pdir,
        fase="listo",
        mensaje="Reporte listo.",
        resultado_final={"codigo_salida_pruebas": rc},
    )
