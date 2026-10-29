"""
Ejecuta los casos de prueba CPxxx.py de este proyecto uno por uno (o en
paralelo con --workers) y genera un reporte CP -> Resultado.

Cada CPxxx.py corre como proceso aparte (aislado: si uno crashea el
navegador, no se cae la corrida completa) con
`.venv\\Scripts\\python.exe CPxxx.py`, y es TOTALMENTE autonomo: genera sus
propias capturas, video (si --video) y Word de evidencia el solito, sin
que este run_all.py tenga que hacer nada mas por cada caso (asi, un
CPxxx.py copiado solo a otra maquina sigue generando su evidencia
completa). run_all.py solo orquesta la corrida y arma el reporte
consolidado.

Video/Word solo se conservan para los casos que terminan OK (patron
_CASO_OK agregado 17/09/2026): un caso que da FALLO igual deja su
captura de error (CASO_error.png) y su entrada en reportes\\logs\\CPxxx.log
para hacer seguimiento, pero no vale la pena armar video/Word de un
flujo que no llego a completarse.

Este archivo es GENERICO (copia textual del framework, ver
C:\\AUTOMATIZACION_LDS\\_framework\\NUEVO_PROYECTO_CHECKLIST.md): no hace
falta editarlo por proyecto. El prefijo de las variables de entorno
(ej. "PR000456_VIDEO") se autodetecta del NOMBRE DE LA CARPETA donde vive
este archivo -por eso cada proyecto debe vivir en una carpeta
`automation\\PR0000NN\\` (o similar) cuyo nombre sea exactamente el
prefijo usado en generate_scripts.py/CURSOR_OVERLAY_JS/etc.

Uso:
    # Todos, sin mostrar el navegador (headless, por defecto):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py

    # Todos, mostrando el navegador (igual que correrlos sueltos con <PREFIJO>_HEADLESS=0):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --headed

    # Todos, grabando ademas el video de cada uno (.webm):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --video

    # --slowmo ya viene en 2500ms por defecto (para que el video se vea
    # bien sin correr de golpe) - bajarlo si hace falta mas velocidad:
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --video --slowmo 500

    # Solo un rango:
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --desde CP001 --hasta CP020

    # Solo algunos puntuales:
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --solo CP001,CP012,CP030

    # Solo uno o mas RF (ignora --desde/--hasta; si tambien se pasa --solo, --solo gana):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --rf RF-05,RF-06

    # En paralelo (4 navegadores a la vez; ojo con la maquina/red):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --workers 4

    # Sin que cada CP genere su Word (solo capturas/reporte, mas rapido):
    .venv\\Scripts\\python.exe automation\\PR0000NN\\run_all.py --sin-word

Nota: si algun caso espera a proposito un timeout real del backend (como
CP122/CP123 en PR000335, ~90s cada uno), subir --timeout para que no se
marquen como TIMEOUT antes de tiempo, y tener en cuenta que la corrida
completa con --workers 1 puede tardar bastante mas de una hora en una
matriz grande.
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import re

sys.path.insert(0, str(Path(__file__).parent))
from generate_scripts import CASES  # noqa: E402  (RF/CU/nombre de cada CP, sin repetirlos aqui)

DIR = Path(__file__).parent
PYTHON = Path(sys.executable)
REPORTES_DIR = DIR / "reportes"

# Prefijo de las variables de entorno (PR000335_HEADLESS, etc.): el nombre
# de esta carpeta. Cada proyecto vive en su propia carpeta automation\PR0000NN\,
# asi que esto autodetecta el prefijo correcto sin tocar el codigo.
PREFIJO = DIR.name


def numero_cp(cp: str) -> int:
    """Extrae la parte numerica de un codigo CP para poder ordenar/
    filtrar por rango. El formato del ID NO es uniforme entre proyectos -
    la mayoria usa "CP001" (digitos pegados), pero algunas matrices Excel
    traen su propia columna "#CP" ya separada con guion, ej. "CP-001"
    (confirmado en vivo, PR000325-SP4: cp[2:] daba "-001", que
    re.match(r"\\d+", ...) no matcheaba - AttributeError: 'NoneType'
    object has no attribute 'group'). Se busca el primer bloque de
    digitos en cualquier parte del string en vez de asumir que arranca
    justo en el indice 2, para cubrir ambos formatos (y el caso de
    sufijos no numericos tipo "CP045-A", que tambien deben ordenar por
    su parte numerica 45)."""
    m = re.search(r"\d+", cp)
    if not m:
        raise ValueError(f"El codigo de caso {cp!r} no tiene ninguna parte numerica.")
    return int(m.group())


METADATA = {c["cp"]: c for c in CASES}
_NUMEROS = sorted(numero_cp(c) for c in METADATA)
CP_MIN = f"CP{_NUMEROS[0]:03d}" if _NUMEROS else "CP001"
CP_MAX = f"CP{_NUMEROS[-1]:03d}" if _NUMEROS else "CP001"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--desde", default=CP_MIN, help=f"Primer CP a correr (default: {CP_MIN})")
    p.add_argument("--hasta", default=CP_MAX, help=f"Ultimo CP a correr (default: {CP_MAX})")
    p.add_argument("--solo", default=None, help="Lista puntual separada por comas, ej: CP001,CP012,CP030 (ignora --desde/--hasta)")
    p.add_argument("--rf", default=None, help="Lista de RF separados por coma, ej: RF-05,RF-06 (ignora --desde/--hasta; si tambien se pasa --solo, --solo gana)")
    p.add_argument("--headed", action="store_true", help="Mostrar el navegador (por defecto corre headless para que la tanda sea mas rapida/estable)")
    p.add_argument("--video", action="store_true", help="Grabar el video (.webm) de cada caso, ademas de las capturas (apagado por defecto: pesa/tarda mas en una tanda grande)")
    p.add_argument("--slowmo", type=int, default=2500, help="Pausa en ms entre cada accion de Playwright (util con --video para que se note el llenado de campos; default: 2500, para que el video se vea bien sin correr de golpe - usar 0 para maxima velocidad sin video)")
    p.add_argument("--workers", type=int, default=1, help="Cuantos CP correr en paralelo (default: 1 = secuencial)")
    p.add_argument("--timeout", type=int, default=180, help="Segundos maximos por CP antes de marcarlo como TIMEOUT (default: 180; subir si algun caso espera un timeout real del backend)")
    p.add_argument("--sin-word", action="store_true", help="Que cada CP NO genere su .docx de evidencia (por defecto SI lo genera cada uno solo)")
    return p.parse_args()


def seleccionar_casos(args):
    todos = sorted(METADATA.keys(), key=numero_cp)
    if args.solo:
        pedidos = [c.strip().upper() for c in args.solo.split(",") if c.strip()]
        faltantes = [c for c in pedidos if c not in METADATA]
        if faltantes:
            raise SystemExit(f"CP desconocidos en --solo: {faltantes}")
        return pedidos
    if args.rf:
        pedidos = [r.strip().upper() for r in args.rf.split(",") if r.strip()]
        rfs_existentes = {v["rf"].upper() for v in METADATA.values()}
        faltantes = [r for r in pedidos if r not in rfs_existentes]
        if faltantes:
            raise SystemExit(f"RF desconocidos en --rf: {faltantes}")
        return [c for c in todos if METADATA[c]["rf"].upper() in pedidos]
    ini, fin = numero_cp(args.desde), numero_cp(args.hasta)
    return [c for c in todos if ini <= numero_cp(c) <= fin]


def ultima_linea_relevante(texto):
    for linea in reversed(texto.strip().splitlines()):
        if linea.strip():
            return linea.strip()
    return ""


def correr_uno(cp, headless, video, word, slowmo, timeout):
    script = DIR / f"{cp}.py"
    env = {
        **os.environ,
        f"{PREFIJO}_HEADLESS": "1" if headless else "0",
        f"{PREFIJO}_VIDEO": "1" if video else "0",
        f"{PREFIJO}_WORD": "1" if word else "0",
        f"{PREFIJO}_SLOWMO": str(slowmo),
    }
    inicio = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(PYTHON), str(script)],
            cwd=str(DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        duracion = time.perf_counter() - inicio
        salida = proc.stdout + proc.stderr
        if proc.returncode == 0:
            resultado = "OK"
        else:
            resultado = "FALLO"
        detalle = ultima_linea_relevante(proc.stdout) or ultima_linea_relevante(proc.stderr)
    except subprocess.TimeoutExpired as e:
        duracion = time.perf_counter() - inicio
        resultado = "TIMEOUT"
        salida = (e.stdout or "") + (e.stderr or "")
        detalle = f"Excedio el timeout de {timeout}s"
    except Exception as e:  # noqa: BLE001
        duracion = time.perf_counter() - inicio
        resultado = "ERROR"
        salida = str(e)
        detalle = str(e)

    meta = METADATA[cp]
    return {
        "cp": cp,
        "rf": meta["rf"],
        "cu": meta["cu"],
        "nombre": meta["name"],
        "resultado": resultado,
        "duracion_seg": round(duracion, 1),
        "detalle": detalle[:300],
        "salida_completa": salida,
    }


def main():
    if not METADATA:
        raise SystemExit(
            "generate_scripts.py todavia no genero ningun caso (CASES vacio) - "
            "completar el Paso 3 del checklist (escribir los casos) antes de ejecutar pruebas."
        )
    args = parse_args()
    casos = seleccionar_casos(args)
    headless = not args.headed

    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    logs_dir = REPORTES_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_csv = REPORTES_DIR / f"reporte_{marca}.csv"

    word = not args.sin_word
    print(f"Corriendo {len(casos)} caso(s) ({casos[0]}..{casos[-1]}) | headless={headless} | video={args.video} | word={word} | slowmo={args.slowmo}ms | workers={args.workers}")
    print(f"Reporte: {reporte_csv}\n")

    resultados = []
    t0 = time.perf_counter()

    if args.workers <= 1:
        for i, cp in enumerate(casos, 1):
            print(f"[{i}/{len(casos)}] {cp} ...", end=" ", flush=True)
            r = correr_uno(cp, headless, args.video, word, args.slowmo, args.timeout)
            resultados.append(r)
            print(f"{r['resultado']} ({r['duracion_seg']}s)")
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futuros = {pool.submit(correr_uno, cp, headless, args.video, word, args.slowmo, args.timeout): cp for cp in casos}
            completados = 0
            for fut in as_completed(futuros):
                r = fut.result()
                resultados.append(r)
                completados += 1
                print(f"[{completados}/{len(casos)}] {r['cp']}: {r['resultado']} ({r['duracion_seg']}s)")

    resultados.sort(key=lambda r: numero_cp(r["cp"]))
    duracion_total = time.perf_counter() - t0

    # Log completo de cada caso (stdout+stderr), util para revisar un FALLO.
    for r in resultados:
        (logs_dir / f"{r['cp']}.log").write_text(r["salida_completa"], encoding="utf-8")

    with open(reporte_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["CP", "RF", "CU", "Nombre", "Resultado", "Duracion_seg", "Detalle"])
        for r in resultados:
            writer.writerow([r["cp"], r["rf"], r["cu"], r["nombre"], r["resultado"], r["duracion_seg"], r["detalle"]])

    conteo = {}
    for r in resultados:
        conteo[r["resultado"]] = conteo.get(r["resultado"], 0) + 1

    print("\n" + "=" * 60)
    print(f"Terminado en {duracion_total / 60:.1f} min. Resumen:")
    for estado in ("OK", "FALLO", "TIMEOUT", "ERROR"):
        if estado in conteo:
            print(f"  {estado}: {conteo[estado]}")
    print(f"\nReporte CSV: {reporte_csv}")
    print(f"Logs por caso: {logs_dir}\\CPxxx.log")

    fallidos = [r["cp"] for r in resultados if r["resultado"] != "OK"]
    if fallidos:
        print(f"\nCasos NO en OK: {', '.join(fallidos)}")

    if word:
        docx_generados = sum(1 for cp in casos if (DIR / cp / f"{cp}_evidencia.docx").exists())
        print(f"Word de evidencia generados por cada CP: {docx_generados}/{len(casos)} (dentro de cada CPxxx\\)")

    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
