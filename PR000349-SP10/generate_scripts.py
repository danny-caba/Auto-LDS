"""
generate_scripts.py de PR000349-SP10 - FUENTE DE VERDAD que genera los CPxxx.py.

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

PROYECTO = "PR000349-SP10"  # debe coincidir con el nombre de esta carpeta
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
        (OUT_DIR / f"{c['cp']}.py").write_text(..., encoding="utf-8")  # TODO: render(c)
    print(f"Generados {len(CASES)} scripts en {OUT_DIR}")
