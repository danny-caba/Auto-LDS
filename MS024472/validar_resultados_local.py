"""
validar_resultados_local.py - Validacion LOCAL del modulo
_framework/resultados.py (Etapa 3 del piloto Auto-LDS, MS024472).

NO toca LDS, NO abre Playwright, NO necesita internet - simula casos
con datos de prueba FICTICIOS para probar la persistencia de
resultados/evidencias en aislamiento. Pensado para correrse las veces
que haga falta sin ningun efecto fuera de `MS024472/resultados_TEST/`
(carpeta separada de `resultados/`, que es donde van las corridas
reales - para no mezclar datos de prueba con datos reales).

Uso:
    C:\\Proyectos\\PlataformaWeb\\.venv\\Scripts\\python.exe validar_resultados_local.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_framework"))
import resultados as r  # noqa: E402

PDIR = Path(__file__).resolve().parent
# Carpeta de prueba APARTE de "resultados/" real, para no ensuciar datos
# reales del piloto con corridas ficticias de esta validacion.
_RESULTADOS_DIR_REAL = r._resultados_dir
r._resultados_dir = lambda pdir: pdir / "resultados_TEST"

FALLOS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"  [{estado}] {nombre}" + (f" - {detalle}" if detalle and not condicion else ""))
    if not condicion:
        FALLOS.append(nombre)


def limpiar():
    carpeta_test = PDIR / "resultados_TEST"
    if carpeta_test.exists():
        shutil.rmtree(carpeta_test)


def crear_evidencia_falsa(marca: str) -> Path:
    """Simula lo que dejaria un CPxxx.py real en su carpeta <CP>/: un
    .png y un .docx de juguete, con `marca` adentro para poder
    distinguir una corrida de otra en las aserciones."""
    origen = PDIR / "_evidencia_falsa_tmp"
    if origen.exists():
        shutil.rmtree(origen)
    origen.mkdir(parents=True)
    (origen / "CP001_01_paso.png").write_bytes(f"PNG-FALSO-{marca}".encode())
    (origen / "CP001_evidencia.docx").write_bytes(f"DOCX-FALSO-{marca}".encode())
    return origen


print("=" * 70)
print("Validacion local de resultados.py (sin LDS, datos ficticios)")
print("=" * 70)

limpiar()

# ------------------------------------------------------------------
# 1) Dos corridas (run_id) distintas del MISMO caso conservan sus
#    archivos - ninguna pisa a la otra.
# ------------------------------------------------------------------
print("\n1) Dos corridas del mismo caso (CP001) conservan sus archivos")
run_id_a = "TEST_RUN_A"
run_id_b = "TEST_RUN_B"

ev_a = crear_evidencia_falsa("CORRIDA-A")
reg_a = r.registrar_resultado(
    PDIR, run_id_a, "CP001", rf="RF-01", cu="CU-01",
    estado_funcional="APROBADO", inicio=time.time(), fin=time.time() + 5,
    esperado="Se visualizan los datos del cliente", obtenido="Datos visualizados correctamente",
    comprobaciones_completadas=["pestana Deuda carga", "pestana General carga"],
    origen_evidencia=ev_a,
)
ev_b = crear_evidencia_falsa("CORRIDA-B")
reg_b = r.registrar_resultado(
    PDIR, run_id_b, "CP001", rf="RF-01", cu="CU-01",
    estado_funcional="APROBADO", inicio=time.time(), fin=time.time() + 5,
    esperado="Se visualizan los datos del cliente", obtenido="Datos visualizados correctamente",
    origen_evidencia=ev_b,
)

json_a = PDIR / "resultados_TEST" / run_id_a / "CP001" / "1" / "resultado.json"
json_b = PDIR / "resultados_TEST" / run_id_b / "CP001" / "1" / "resultado.json"
check("resultado.json de la corrida A existe", json_a.is_file())
check("resultado.json de la corrida B existe", json_b.is_file())
png_a = PDIR / "resultados_TEST" / run_id_a / "CP001" / "1" / "evidencia" / "CP001_01_paso.png"
png_b = PDIR / "resultados_TEST" / run_id_b / "CP001" / "1" / "evidencia" / "CP001_01_paso.png"
check("evidencia PNG de la corrida A tiene su contenido propio (A)", png_a.is_file() and b"CORRIDA-A" in png_a.read_bytes())
check("evidencia PNG de la corrida B tiene su contenido propio (B, no pisada por A)", png_b.is_file() and b"CORRIDA-B" in png_b.read_bytes())

# Tambien 2 INTENTOS (reintentos) dentro del MISMO run_id - no deben pisarse.
intento1 = r.siguiente_intento(PDIR, run_id_a, "CP001")
ev_retry = crear_evidencia_falsa("REINTENTO")
reg_retry = r.registrar_resultado(
    PDIR, run_id_a, "CP001", rf="RF-01", cu="CU-01",
    estado_funcional="APROBADO", inicio=time.time(), fin=time.time() + 3,
    origen_evidencia=ev_retry,
)
check("el 2do intento del mismo run_id+CP se numera 2 (no pisa al 1)", reg_retry["intento"] == 2)
check("el resultado.json del intento 1 original sigue intacto", json_a.is_file() and json.loads(json_a.read_text(encoding="utf-8"))["evidencia"]["rutas"])

# ------------------------------------------------------------------
# 2) Un fallo controlado deja resultado Y evidencia (no se pierde nada
#    por el solo hecho de no ser un caso OK).
# ------------------------------------------------------------------
print("\n2) Un fallo controlado deja resultado y evidencia")
ev_fallo = crear_evidencia_falsa("FALLO-CONTROLADO")
reg_fallo = r.registrar_resultado(
    PDIR, "TEST_RUN_FALLO", "CP099", rf="RF-01", cu="CU-03",
    estado_funcional="INCUMPLIMIENTO_OBSERVADO",
    inicio=time.time(), fin=time.time() + 2,
    esperado="Mensaje de error al ingresar cliente inexistente",
    obtenido="La pantalla quedo en blanco, sin mensaje",
    paso_fallido="Verificar mensaje de error",
    excepcion="AssertionError: no aparecio ningun dialogo de validacion",
    origen_evidencia=ev_fallo,
)
json_fallo = PDIR / "resultados_TEST" / "TEST_RUN_FALLO" / "CP099" / "1" / "resultado.json"
check("el resultado de un caso fallido se persiste", json_fallo.is_file())
check("el estado_funcional queda como INCUMPLIMIENTO_OBSERVADO (no se pierde)", reg_fallo["estado_funcional"] == "INCUMPLIMIENTO_OBSERVADO")
png_fallo = PDIR / "resultados_TEST" / "TEST_RUN_FALLO" / "CP099" / "1" / "evidencia" / "CP001_01_paso.png"
check("la evidencia del caso fallido tambien se conserva", png_fallo.is_file())

# ------------------------------------------------------------------
# 3) Una interrupcion conserva los casos ya completados (simulado: se
#    registra CP001 y despues se simula una excepcion ANTES de
#    registrar CP002 - CP001 debe sobrevivir).
# ------------------------------------------------------------------
print("\n3) Una interrupcion conserva los casos ya completados")
run_id_interrumpido = "TEST_RUN_INTERRUMPIDO"
try:
    r.registrar_resultado(
        PDIR, run_id_interrumpido, "CP001", rf="RF-01", cu="CU-01",
        estado_funcional="APROBADO", inicio=time.time(), fin=time.time() + 1,
        origen_evidencia=crear_evidencia_falsa("ANTES-DE-INTERRUMPIR"),
    )
    raise KeyboardInterrupt("Simulando Ctrl+C a mitad de la corrida (CP002 nunca llega a correr)")
except KeyboardInterrupt:
    pass  # esto es lo que haria run_all.py/el adaptador: dejar lo ya corrido tal cual

json_cp001_interrumpido = PDIR / "resultados_TEST" / run_id_interrumpido / "CP001" / "1" / "resultado.json"
json_cp002_interrumpido = PDIR / "resultados_TEST" / run_id_interrumpido / "CP002" / "1" / "resultado.json"
check("CP001 (corrido antes de interrumpir) persistio", json_cp001_interrumpido.is_file())
check("CP002 (nunca llego a correr) NO existe - no se inventa un resultado", not json_cp002_interrumpido.is_file())

resumen_interrumpido = PDIR / "resultados_TEST" / run_id_interrumpido / "_resumen_corrida.json"
check("el resumen de la corrida interrumpida refleja SOLO lo que corrio", resumen_interrumpido.is_file() and json.loads(resumen_interrumpido.read_text(encoding="utf-8"))["total_registros"] == 1)

# ------------------------------------------------------------------
# 4) Un error al generar evidencia NO oculta el resultado funcional
#    (ni al reves: un caso fallido con evidencia OK no se "mejora").
# ------------------------------------------------------------------
print("\n4) Un error al generar evidencia no oculta el resultado funcional")
reg_sin_evidencia = r.registrar_resultado(
    PDIR, "TEST_RUN_EVIDENCIA_ROTA", "CP050", rf="RF-01", cu="CU-02",
    estado_funcional="APROBADO", inicio=time.time(), fin=time.time() + 1,
    origen_evidencia=PDIR / "esta_carpeta_no_existe_a_proposito",
)
check("el caso sigue APROBADO aunque la carpeta de evidencia de origen no exista", reg_sin_evidencia["estado_funcional"] == "APROBADO")
check("el problema de evidencia queda anotado aparte (SIN_ORIGEN)", reg_sin_evidencia["evidencia"]["estado_generacion"] == "SIN_ORIGEN")

# Caso mas fuerte: la copia SI arranca (origen existe) pero falla a mitad
# de camino (shutil.copy2 forzado a tirar excepcion) - el resultado
# funcional tampoco debe verse afectado.
_copy2_original = shutil.copy2


def _copy2_que_falla(*a, **kw):
    raise OSError("Disco lleno (simulado)")


shutil.copy2 = _copy2_que_falla
try:
    reg_copia_rota = r.registrar_resultado(
        PDIR, "TEST_RUN_EVIDENCIA_ROTA", "CP051", rf="RF-01", cu="CU-02",
        estado_funcional="INCUMPLIMIENTO_OBSERVADO", inicio=time.time(), fin=time.time() + 1,
        excepcion="AssertionError real del caso, no de la evidencia",
        origen_evidencia=crear_evidencia_falsa("COPIA-FALLIDA"),
    )
finally:
    shutil.copy2 = _copy2_original

check("el estado_funcional real (INCUMPLIMIENTO_OBSERVADO) se conserva pese al error de copia", reg_copia_rota["estado_funcional"] == "INCUMPLIMIENTO_OBSERVADO")
check("la excepcion FUNCIONAL original no se pierde ni se reemplaza por el error de copia", "AssertionError real del caso" in (reg_copia_rota["excepcion"] or ""))
check("el error de copia de evidencia queda anotado aparte, sin tapar lo anterior", reg_copia_rota["evidencia"]["estado_generacion"].startswith("ERROR:"))

# ------------------------------------------------------------------
# 5) Credenciales/tokens ficticios usados en la prueba NO aparecen en
#    los registros persistidos.
# ------------------------------------------------------------------
print("\n5) Credenciales y tokens ficticios no aparecen en los registros")
SECRETO_PASSWORD = "Pr3ba-S3cr3ta-NoReal-998877"
SECRETO_TOKEN = "tok_FICTICIO_xyz123456789"
reg_con_secretos = r.registrar_resultado(
    PDIR, "TEST_RUN_SECRETOS", "CP060", rf="RF-01", cu="CU-01",
    estado_funcional="ERROR_AUTOMATIZACION", inicio=time.time(), fin=time.time() + 1,
    excepcion=f"Login fallo usando password={SECRETO_PASSWORD}. Authorization: Bearer {SECRETO_TOKEN}",
    obtenido=f"Respuesta del servidor incluyo Cookie: session_token={SECRETO_TOKEN}",
)
json_secretos = PDIR / "resultados_TEST" / "TEST_RUN_SECRETOS" / "CP060" / "1" / "resultado.json"
contenido_json = json_secretos.read_text(encoding="utf-8")
check("el password ficticio NO aparece en el JSON persistido", SECRETO_PASSWORD not in contenido_json)
check("el token ficticio NO aparece en el JSON persistido", SECRETO_TOKEN not in contenido_json)
check("el campo igual quedo legible (clave visible, valor redactado)", "password=***REDACTADO***" in contenido_json)

# ------------------------------------------------------------------
# Limpieza de temporales (no de resultados_TEST/, que se deja para que
# el usuario pueda inspeccionarlo a mano si quiere).
# ------------------------------------------------------------------
shutil.rmtree(PDIR / "_evidencia_falsa_tmp", ignore_errors=True)
r._resultados_dir = _RESULTADOS_DIR_REAL  # restaurar (por si este modulo se vuelve a importar en el mismo proceso)

print("\n" + "=" * 70)
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} validacion(es) fallaron: {FALLOS}")
    sys.exit(1)
else:
    print("RESULTADO: todas las validaciones OK.")
    print(f"\nPodes inspeccionar los archivos generados en:\n  {PDIR / 'resultados_TEST'}")
    sys.exit(0)
