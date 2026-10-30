"""
nuevo_proyecto.py - Bootstrap de un proyecto nuevo de Web LDS EN UN SOLO
COMANDO, con la estructura de una sola carpeta raiz (ver
NUEVO_PROYECTO_CHECKLIST.md, Seccion 0).

Consolida TODO bajo C:\\AUTOMATIZACION_LDS\\PR0000NN\\ (documentos + scripts
+ evidencia + reportes, todo en la MISMA carpeta) para que arrancar un
proyecto pida acceso a UNA sola carpeta raiz (C:\\AUTOMATIZACION_LDS\\),
en vez de repartir cosas entre 2 arboles como en PR000335/PR000325 (esos
dos NO se migraron a esta estructura, siguen como estaban).

Uso:
    .venv\\Scripts\\python.exe nuevo_proyecto.py PR0000NN --excel "ruta\\a\\MCP-....xlsx"
    .venv\\Scripts\\python.exe nuevo_proyecto.py PR0000NN --excel "..." --ef "..." --et "..."

Hace, en un solo comando (pide permiso de carpeta UNA sola vez, la raiz
C:\\AUTOMATIZACION_LDS\\):
  1. Crea C:\\AUTOMATIZACION_LDS\\PR0000NN\\ y PR0000NN\\documentos\\.
  2. Copia el Excel (y EF/ET si se pasaron) a PR0000NN\\documentos\\.
  3. Corre extraer_matriz.py -> PR0000NN\\matriz_casos.json.
  4. Si se paso --ef/--et, corre extraer_docx.py sobre cada uno ->
     PR0000NN\\documentos\\EF_texto.txt + EF_media\\ (idem ET).
  5. Deja un generate_scripts.py ESQUELETO (a completar a mano - el cuerpo
     de cada caso NO es automatizable, ver NUEVO_PROYECTO_CHECKLIST.md
     Paso 3) y copia run_all.py tal cual.

Lo que NO hace (adrede, no es automatizable a ciegas): la exploracion en
vivo (Paso 2) ni escribir el cuerpo real de cada caso (Paso 3). Al
terminar, imprime esos proximos pasos manuales.

No mueve ni toca el framework existente ni proyectos ya generados - esto
es solo para EMPEZAR un proyecto nuevo con la estructura consolidada.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FRAMEWORK_DIR = Path(__file__).resolve().parent
RAIZ = FRAMEWORK_DIR.parent  # C:\AUTOMATIZACION_LDS (o donde viva _framework)
PYTHON = Path(sys.executable)

ESQUELETO_GENERATE_SCRIPTS = r'''"""
generate_scripts.py de {proyecto} - FUENTE DE VERDAD que genera los CPxxx.py.

Completar siguiendo C:\\AUTOMATIZACION_LDS\\_framework\\NUEVO_PROYECTO_CHECKLIST.md
(Paso 3): HEADER_TEMPLATE, render(), CASES y un add(...) por cada caso de
matriz_casos.json. El cuerpo de cada caso (selectores/asserts reales) NO
es automatizable a ciegas - hay que escribirlo mirando la matriz + la
exploracion en vivo (Paso 2), recien despues de tener este esqueleto.
"""
import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT_DIR.parent / "_framework"))
import web_lds_core as core  # noqa: E402

PROYECTO = "{proyecto}"  # debe coincidir con el nombre de esta carpeta
MATRIZ = json.loads((OUT_DIR / "matriz_casos.json").read_text(encoding="utf-8"))

ENV_TOGGLES = core.ENV_TOGGLES_CODE.replace("__PROYECTO__", PROYECTO)

# TODO: HEADER_TEMPLATE, render(), CASES y add(...) por caso - ver
# NUEVO_PROYECTO_CHECKLIST.md Paso 3 para el esqueleto completo de
# referencia (o PR000335/generate_scripts.py como ejemplo real de 123
# casos ya resuelto).

CASES = []

def add(cp, rf, cu, name, desc, precond, datos, esperado, body):
    CASES.append(dict(cp=cp, rf=rf, cu=cu, name=name, desc=desc, precond=precond, datos=datos, esperado=esperado, body=body))

if __name__ == "__main__":
    if not CASES:
        raise SystemExit(
            "generate_scripts.py todavia es un esqueleto vacio - completar HEADER_TEMPLATE/"
            "render()/CASES siguiendo NUEVO_PROYECTO_CHECKLIST.md (Paso 3) antes de correr esto."
        )
    for c in CASES:
        (OUT_DIR / f"{{c['cp']}}.py").write_text(..., encoding="utf-8")  # TODO: render(c)
    print(f"Generados {{len(CASES)}} scripts en {{OUT_DIR}}")
'''


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("proyecto", help="Codigo del proyecto, ej. PR000456")
    p.add_argument("--excel", required=True, help="Ruta al .xlsx de la matriz de casos (MCP-...)")
    p.add_argument("--ef", default=None, help="Ruta al .docx de Especificacion Funcional (opcional)")
    p.add_argument("--et", default=None, help="Ruta al .docx de Diseno Tecnico (opcional)")
    p.add_argument("--extra", action="append", default=[], help="Ruta a un documento adicional (PDF, Word, manual de usuario, etc.) - repetir la opcion para varios. Se copia a documentos/; si es .docx tambien se le extrae texto+imagenes, igual que EF/ET.")
    p.add_argument("--hoja", default=None, help="Nombre exacto de la hoja del Excel (default: autodetecta)")
    args = p.parse_args()

    proyecto_dir = RAIZ / args.proyecto
    documentos_dir = proyecto_dir / "documentos"
    documentos_dir.mkdir(parents=True, exist_ok=True)
    print(f"[1/5] Carpeta del proyecto: {proyecto_dir}")

    excel_origen = Path(args.excel)
    if not excel_origen.is_file():
        raise SystemExit(f"No existe el Excel: {excel_origen}")
    excel_destino = documentos_dir / excel_origen.name
    if excel_destino.resolve() != excel_origen.resolve():
        shutil.copy2(excel_origen, excel_destino)
    print(f"[2/5] Excel en {excel_destino}")

    matriz_json = proyecto_dir / "matriz_casos.json"
    cmd = [str(PYTHON), str(FRAMEWORK_DIR / "extraer_matriz.py"), str(excel_destino), str(matriz_json)]
    if args.hoja:
        cmd += ["--hoja", args.hoja]
    print("[3/5] Extrayendo matriz de casos...")
    subprocess.run(cmd, check=True)

    for etiqueta, ruta in (("EF", args.ef), ("ET", args.et)):
        if not ruta:
            continue
        origen = Path(ruta)
        if not origen.is_file():
            print(f"  (aviso) no existe el {etiqueta}: {origen} - se omite.")
            continue
        destino = documentos_dir / origen.name
        if destino.resolve() != origen.resolve():
            shutil.copy2(origen, destino)
        print(f"[4/5] {etiqueta} en {destino}, extrayendo texto+imagenes...")
        subprocess.run([str(PYTHON), str(FRAMEWORK_DIR / "extraer_docx.py"), str(destino)], check=True)

    for ruta_extra in args.extra:
        origen = Path(ruta_extra)
        if not origen.is_file():
            print(f"  (aviso) no existe el documento adicional: {origen} - se omite.")
            continue
        destino = documentos_dir / origen.name
        if destino.resolve() != origen.resolve():
            shutil.copy2(origen, destino)
        if destino.suffix.lower() == ".docx":
            print(f"[4/5] Adicional {destino.name} en {destino}, extrayendo texto+imagenes...")
            subprocess.run([str(PYTHON), str(FRAMEWORK_DIR / "extraer_docx.py"), str(destino)], check=True)
        else:
            print(f"[4/5] Adicional {destino.name} copiado a {destino} (sin extraccion, no es .docx).")

    generate_scripts_py = proyecto_dir / "generate_scripts.py"
    if not generate_scripts_py.exists():
        generate_scripts_py.write_text(ESQUELETO_GENERATE_SCRIPTS.format(proyecto=args.proyecto), encoding="utf-8")
        print(f"[5/5] Esqueleto de generate_scripts.py -> {generate_scripts_py}")
    else:
        print(f"[5/5] generate_scripts.py ya existe, no se toca -> {generate_scripts_py}")

    run_all_py = proyecto_dir / "run_all.py"
    if not run_all_py.exists():
        shutil.copy2(FRAMEWORK_DIR / "run_all.py", run_all_py)
        print(f"      run_all.py copiado (generico, sin editar) -> {run_all_py}")

    print(f"\nListo. Todo el proyecto queda en una sola carpeta:\n  {proyecto_dir}")
    print("\nProximos pasos MANUALES (no automatizables, ver NUEVO_PROYECTO_CHECKLIST.md):")
    print("  1. Exploracion en vivo de la app real (Paso 2) - guardar capturas en _exploracion\\.")
    print("  2. Completar generate_scripts.py con tus selectores/casos reales (Paso 3).")
    print(f"  3. <tu_venv>\\python.exe {generate_scripts_py}")
    print(f"  4. <tu_venv>\\python.exe {run_all_py} --solo CP001,CP002 --video")


if __name__ == "__main__":
    main()
