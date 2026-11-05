"""
validar_memoria_local.py - Validacion LOCAL de _framework/memoria_central.py
(Etapa 5, MS024472). Sin LDS, sin casos funcionales - usa una dificultad
real encontrada en la Etapa 4 (pagina local de juguete) como ejemplo.

Uso:
    C:\\Proyectos\\PlataformaWeb\\.venv\\Scripts\\python.exe validar_memoria_local.py
"""
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_framework"))
import memoria_central as mc  # noqa: E402

# Carpeta de prueba APARTE de _framework/conocimiento/ real (mismo
# patron que validar_resultados_local.py y
# validar_intervencion_local.py) - BUG REAL encontrado y corregido
# 31/10/2026: la primera version de este script escribia DIRECTO sobre
# la memoria real, asi que cada vez que se re-corria esta validacion
# (ej. como parte de una verificacion integral mas grande) quedaban
# entradas de prueba duplicadas en el conocimiento real del proyecto.
_CONOCIMIENTO_DIR_REAL = mc._conocimiento_dir
_CARPETA_TEST = Path(__file__).resolve().parent.parent / "_framework" / "conocimiento_TEST"
mc._conocimiento_dir = lambda: _CARPETA_TEST

if _CARPETA_TEST.exists():
    shutil.rmtree(_CARPETA_TEST)

FALLOS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"  [{estado}] {nombre}" + (f" - {detalle}" if detalle and not condicion else ""))
    if not condicion:
        FALLOS.append(nombre)


print("=" * 70)
print("Validacion local de memoria_central.py")
print("=" * 70)

# ------------------------------------------------------------------
# 1) Registrar una dificultad + solucion VERIFICADA, real, de la
#    Etapa 4 (no inventada: es lo que de verdad se confirmo corriendo
#    validar_intervencion_local.py contra la pagina local de juguete).
# ------------------------------------------------------------------
print("\n1) Registrar dificultad + solucion verificada (real, de la Etapa 4)")

entrada = mc.agregar_entrada(
    "SOLUCION_TECNICA_COMPROBADA",
    "En la pantalla de consulta de producto (pagina de juguete "
    "_exploracion/pagina_local_ejemplo.html), page.fill('#codigo', codigo) "
    "+ page.click('#buscar') alcanza: el texto de #resultado ya esta listo "
    "apenas vuelve click() porque la pagina es 100% sincronica (sin "
    "llamadas de red) - no hace falta esperar networkidle ni agregar un "
    "wait_for_timeout extra.",
    fuente="Etapa 4 - validar_intervencion_local.py (casos CPL01/CPL02, ambos APROBADO)",
    requerimiento_origen="MS024472",
    modulo="consulta-producto-local",
    referencias_evidencia=[
        "MS024472/resultados_TEST_INTERVENCION/*/CPL01/*/resultado.json",
        "MS024472/_exploracion/pagina_local_ejemplo.html",
    ],
    estado="VERIFICADO",  # hay respaldo real: se corrio y paso en la Etapa 4
    condiciones_revalidacion="Revalidar si la pagina de ejemplo pasa a tener alguna llamada async (fetch/XHR).",
)
check("1: la entrada se creo con un id estable", entrada["id"].startswith("CONO-"))
check("1: quedo VERIFICADO (hay respaldo real, no es un PROVISIONAL sin base)", entrada["estado"] == "VERIFICADO")
check("1: el archivo entradas/<id>.json existe en disco", (mc._entradas_dir() / f"{entrada['id']}.json").is_file())
check("1: indice.md se regenero e incluye la entrada", entrada["id"] in (mc._conocimiento_dir() / "indice.md").read_text(encoding="utf-8"))

id_entrada = entrada["id"]

# ------------------------------------------------------------------
# 2) Preparar un 2do requerimiento de ejemplo relacionado, y RECUPERAR
#    la entrada DESDE ARCHIVOS (no desde el estado en memoria de este
#    mismo script - fuerzo una recarga del modulo para simular una
#    sesion/proceso nuevo que no tiene nada en memoria todavia).
# ------------------------------------------------------------------
print("\n2) 2do requerimiento de ejemplo: recuperar la entrada desde archivos")

importlib.reload(mc)  # simula un proceso/sesion nueva: sin estado en memoria previo
# BUG REAL encontrado y corregido 31/10/2026: reload() re-ejecuta el
# modulo entero, lo que PISA el monkeypatch de _conocimiento_dir de
# arriba (vuelve a apuntar a la carpeta real) - sin esto, todo lo que
# sigue en el script (pasos 2, 3 y 4) terminaba escribiendo sobre
# _framework/conocimiento/ real en vez de la carpeta de prueba.
mc._conocimiento_dir = lambda: _CARPETA_TEST

REQUERIMIENTO_2 = "MS999001-EJEMPLO"
candidatas = mc.buscar(modulo="consulta-producto-local")
check("2: la busqueda por modulo encuentra la entrada (leida de disco, no de memoria)", any(e["id"] == id_entrada for e in candidatas))

mc.registrar_consulta(
    REQUERIMIENTO_2,
    entradas_consultadas=[id_entrada],
    entradas_aplicadas=[id_entrada],
    entradas_descartadas={},
)
check("2: el registro de consulta quedo persistido", mc.tiene_registro_consulta(REQUERIMIENTO_2))
registro_leido = mc.leer_registro_consulta(REQUERIMIENTO_2)
check("2: el registro de consulta referencia la entrada real (no inventada)", registro_leido is not None and id_entrada in registro_leido["entradas_aplicadas"])

# ------------------------------------------------------------------
# 3) Invalidar una solucion y comprobar que deja de recomendarse.
#    OJO: uso una 2da entrada DEDICADA y explicitamente marcada como de
#    prueba para esto (no la CONO-0001 real de arriba) - esa es
#    conocimiento real y util del proyecto, no tiene sentido dejarla
#    invalidada solo por haber corrido este script de validacion.
# ------------------------------------------------------------------
print("\n3) Invalidar una solucion de prueba -> deja de recomendarse como vigente")

entrada_descartable = mc.agregar_entrada(
    "SOLUCION_TECNICA_COMPROBADA",
    "[ENTRADA DE PRUEBA - solo para validar el mecanismo de invalidacion de "
    "la Etapa 5, no es conocimiento real del proyecto] Hallazgo ficticio de "
    "ejemplo.",
    fuente="validar_memoria_local.py (fixture de prueba)",
    requerimiento_origen="MS024472",
    modulo="consulta-producto-local",
    estado="VERIFICADO",
)
id_descartable = entrada_descartable["id"]

check("3 (antes de invalidar): la entrada de prueba SI aparece en busqueda normal", any(e["id"] == id_descartable for e in mc.buscar(modulo="consulta-producto-local")))

mc.invalidar_entrada(id_descartable, "Motivo de ejemplo para esta validacion - era una entrada ficticia creada solo para probar el mecanismo de invalidacion, no describe nada real.")

check("3 (despues de invalidar): NO aparece en busqueda normal (solo_vigentes=True, default)", not any(e["id"] == id_descartable for e in mc.buscar(modulo="consulta-producto-local")))
check("3: SI aparece si se pide explicitamente estado=INVALIDADO", any(e["id"] == id_descartable for e in mc.buscar(modulo="consulta-producto-local", solo_vigentes=False, estado="INVALIDADO")))
check("3: la entrada REAL (CONO-0001, fill()+click()) sigue vigente, sin tocar", any(e["id"] == id_entrada for e in mc.buscar(modulo="consulta-producto-local")))
entrada_invalidada = mc.leer_entrada(id_descartable)
check("3: el archivo NO se borro (historial conservado)", entrada_invalidada is not None)
check("3: el motivo de invalidacion quedo registrado", "probar el mecanismo" in (entrada_invalidada.get("motivo_invalidacion") or ""))

# ------------------------------------------------------------------
# 4) Chequeo de "falta el registro de consulta" (para el plan-prep).
# ------------------------------------------------------------------
print("\n4) Chequeo de registro de consulta faltante")
check("4: un requerimiento que nunca se consulto da False", mc.tiene_registro_consulta("MS000000-NUNCA-CONSULTADO") is False)
check("4: el requerimiento 2 (que SI se registro) da True", mc.tiene_registro_consulta(REQUERIMIENTO_2) is True)

carpeta_inspeccion = mc._conocimiento_dir()
mc._conocimiento_dir = _CONOCIMIENTO_DIR_REAL  # restaurar

print("\n" + "=" * 70)
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} validacion(es) fallaron: {FALLOS}")
    sys.exit(1)
else:
    print("RESULTADO: todas las validaciones OK.")
    print(f"\nPodes inspeccionar:\n  {carpeta_inspeccion}")
    sys.exit(0)
