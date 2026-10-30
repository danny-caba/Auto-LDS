"""
Arma el prompt de exploracion/generacion que se le pasa a `claude -p`
(modo headless) para completar el Paso 2-6 de
`_framework\\NUEVO_PROYECTO_CHECKLIST.md` sobre un proyecto ya
bootstrapeado (matriz_casos.json ya existe).

Si el CLI `claude` no esta instalado en la maquina (ver `procesos.py`,
`shutil.which("claude")`), este MISMO texto se muestra en la web para
que el usuario lo pegue a mano en una sesion interactiva - por eso el
prompt no asume que nadie esta mirando (dice explicitamente que no debe
esperar confirmaciones), pero tampoco depende de ejecutarse headless
para ser util.
"""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent  # C:\AUTOMATIZACION_LDS
FRAMEWORK_DIR = RAIZ / "_framework"

POLITICA_AUTONOMIA = """\
Politica de autonomia (modo headless, sin nadie mirando en vivo) - segui estas
4 reglas para decidir que hacer cuando un caso no sale a la primera. La regla
de oro: NUNCA frenes el batch completo por un solo caso - si un caso puntual
necesita una persona, anotalo y segui con el resto.

a) Si el problema tiene un patron YA CONOCIDO en tu memoria de proyectos Web
   LDS anteriores (ej. el dialogo fantasma .mdl-tab-pane sin botones, algun
   .strip()/.trim() en JS, etc.): aplica el fix directo, sin pausar a pensar
   si esta bien.
b) Si falta un DATO DE PRUEBA REAL que no se puede inventar (ej. un cliente
   en un estado especifico, un codigo que solo existe en produccion): NO
   bloquees el batch. Anota el caso en pendientes_revision.json (ver formato
   abajo) con que dato exacto hace falta, y segui con el resto de los casos.
c) Si es un bug NUEVO que nunca viste: como maximo 2-3 intentos de
   diagnostico en vivo (scripts chicos en _exploracion\\, igual que siempre).
   Si no se resuelve en esos intentos, anotalo en pendientes_revision.json
   como "posible defecto real" con la evidencia que tengas (screenshot, texto
   del error), y segui - no reintentes indefinidamente.
d) Si la accion es IRREVERSIBLE contra datos reales Y hay ambiguedad de
   negocio (el manual dice una cosa, la matriz otra, o no esta claro si es
   seguro escribir ese dato): esta es la UNICA categoria que amerita frenar
   ESE caso puntual (nunca el batch completo) - anotalo tambien en
   pendientes_revision.json.

Formato de pendientes_revision.json (crealo/actualizalo en la carpeta del
proyecto si algun caso cae en (b), (c) o (d)):
{
  "CPxxx": {
    "categoria": "falta_dato_real | posible_defecto_nuevo | accion_irreversible_ambigua",
    "detalle": "texto corto explicando que hace falta o que paso",
    "intentos": 0
  }
}
"""

PASOS_FINALES = """\
Antes de terminar, en este orden:
1. Corre generate_scripts.py para materializar todos los CPxxx.py.
2. Compila todos los CPxxx.py generados con py_compile (sin excepciones).
3. Como smoke test real, corre run_all.py --solo <los primeros 2 CP que
   hayas generado> --video para confirmar que al menos esos 2 funcionan
   de punta a punta contra la app real.
4. Como ULTIMA linea de tu respuesta final, imprimi (en una sola linea,
   JSON compacto, sin texto alrededor) un resumen con este formato exacto:
   WEBAPP_RESUMEN: {"casos_generados": N, "casos_total": M, "casos_pendientes_revision": K, "notas": "..."}
   Esto lo necesita un backend automatizado para saber que paso - no lo
   omitas ni lo cambies de formato.
"""


def _listar_rf(proyecto_dir: Path) -> list[str]:
    matriz_path = proyecto_dir / "matriz_casos.json"
    if not matriz_path.exists():
        return []
    try:
        matriz = json.loads(matriz_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rfs = sorted({v.get("rf", "?") for v in matriz.values()})
    return rfs


def construir_prompt(proyecto: str, proyecto_dir: Path) -> str:
    rfs = _listar_rf(proyecto_dir)
    rfs_texto = ", ".join(rfs) if rfs else "(no se pudo leer matriz_casos.json todavia)"

    return f"""\
Estas corriendo en modo headless (nadie esta mirando en vivo, no hagas
preguntas de confirmacion - segui la politica de autonomia de abajo para
cualquier decision).

Proyecto: {proyecto}
Carpeta: {proyecto_dir}
RF en la matriz de este proyecto: {rfs_texto}

Ya existe {proyecto_dir / "matriz_casos.json"} (bootstrap ya hecho via
nuevo_proyecto.py). Tu trabajo es completar el resto del flujo siguiendo
{FRAMEWORK_DIR / "NUEVO_PROYECTO_CHECKLIST.md"} (Secciones 2 a 6):
explorar la app real en vivo con Playwright (login, selectores, rutas de
menu reales - no confiar ciegamente en lo que diga el EF/ET), y escribir
{proyecto_dir / "generate_scripts.py"} completo con todos los CPxxx.py de
la matriz, reusando los helpers/modulos ya validados en
{FRAMEWORK_DIR / "web_lds_core.py"} y {FRAMEWORK_DIR / "modulos"} en vez
de reinventar patrones ya conocidos.

Revisa primero tu memoria de proyectos Web LDS anteriores (gotchas de
Playwright, credenciales/datos de prueba reutilizables, patrones de
dialogo, etc.) antes de explorar de cero - varios ya estan documentados.

Revisa tambien {proyecto_dir / "documentos"} por completo antes de
explorar en vivo - ademas del Excel/EF/ET puede haber documentos
adicionales (manuales de usuario en PDF, capturas de referencia, etc.)
subidos a mano para este proyecto puntual, con contexto util (reglas de
negocio, pantallas, mensajes reales) que puede ahorrar exploracion.

No inventes ni pidas credenciales nuevas - reusa las que ya estan
configuradas en C:\\Proyectos\\PlataformaWeb\\.env, igual que el resto de
los proyectos.

{POLITICA_AUTONOMIA}

{PASOS_FINALES}
"""
