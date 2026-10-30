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
    el codigo de salida."""
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
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


def lanzar_bootstrap_y_explorar(
    proyecto: str,
    excel_path: Path,
    ef_path: Path | None,
    et_path: Path | None,
    extra_paths: list[Path] | None = None,
) -> None:
    hilo = threading.Thread(
        target=_bootstrap_y_explorar,
        args=(proyecto, excel_path, ef_path, et_path, extra_paths or []),
        daemon=True,
    )
    _registrar_hilo(proyecto, hilo)
    hilo.start()


def _bootstrap_y_explorar(
    proyecto: str,
    excel_path: Path,
    ef_path: Path | None,
    et_path: Path | None,
    extra_paths: list[Path],
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

    estado.actualizar(pdir, fase="bootstrap_ok", mensaje="Bootstrap completo. matriz_casos.json generado.")

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

    # run_all.py y generar_reporte_excel.py son "copia textual" por
    # proyecto (ver NUEVO_PROYECTO_CHECKLIST.md Seccion 7) - se
    # refrescan aca para que un proyecto viejo herede --rf sin tener
    # que ir a mano a re-copiar el archivo.
    shutil.copy2(FRAMEWORK_DIR / "run_all.py", pdir / "run_all.py")
    shutil.copy2(FRAMEWORK_DIR / "generar_reporte_excel.py", pdir / "generar_reporte_excel.py")

    estado.actualizar(pdir, fase="ejecutando_pruebas", mensaje=f"Ejecutando RF: {', '.join(rf_list)}", log=[], progreso={"actual": 0, "total": 0, "cp_actual": ""})

    cmd = [str(PYTHON), "-u", str(pdir / "run_all.py"), "--rf", ",".join(rf_list)]
    if video:
        cmd.append("--video")

    def _on_linea(linea: str) -> None:
        estado.agregar_log(pdir, linea)
        m = _RE_PROGRESO_SECUENCIAL.match(linea) or _RE_PROGRESO_PARALELO.match(linea)
        if m:
            actual, total, cp = m.group(1), m.group(2), m.group(3)
            estado.actualizar(pdir, progreso={"actual": int(actual), "total": int(total), "cp_actual": cp})

    try:
        rc = _correr_subprocess_lineas(cmd, cwd=pdir, on_linea=_on_linea)
    except Exception as e:  # noqa: BLE001
        estado.actualizar(pdir, fase="reporte_error", mensaje=f"Excepcion al correr run_all.py: {e}")
        return

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
