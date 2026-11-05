"""
validar_intervencion_local.py - Validacion LOCAL del modulo
_framework/intervencion.py (Etapa 4 del piloto Auto-LDS, MS024472).

Usa la pagina local de juguete (_exploracion/pagina_local_ejemplo.html,
sin tocar LDS) y Playwright real (SI abre un navegador real headless
para los casos normales, y un navegador VISIBLE brevemente para validar
la exploracion manual - se cierra solo en segundos, scripted). Las
respuestas de "la persona" estan scripteadas (listas de respuestas
canned) en vez de esperar input() real - asi se puede correr sin
supervision y repetir las veces que haga falta.

Uso:
    C:\\Proyectos\\PlataformaWeb\\.venv\\Scripts\\python.exe validar_intervencion_local.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_framework"))
import intervencion as iv  # noqa: E402
import resultados as r  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

PDIR = Path(__file__).resolve().parent
URL_PAGINA = (PDIR / "_exploracion" / "pagina_local_ejemplo.html").resolve().as_uri()

# Carpeta de prueba APARTE de resultados/ real (mismo patron que
# validar_resultados_local.py, para no mezclar datos de prueba con
# datos reales del piloto).
_RESULTADOS_DIR_REAL = r._resultados_dir
r._resultados_dir = lambda pdir: pdir / "resultados_TEST_INTERVENCION"

FALLOS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"  [{estado}] {nombre}" + (f" - {detalle}" if detalle and not condicion else ""))
    if not condicion:
        FALLOS.append(nombre)


def limpiar():
    carpeta_test = PDIR / "resultados_TEST_INTERVENCION"
    if carpeta_test.exists():
        shutil.rmtree(carpeta_test)


class EntradaScripteada:
    """Fake de `input()`: devuelve las respuestas de `respuestas` en
    orden, una por llamada. Si se agotan, lanza un error claro (en vez
    de colgarse esperando un input() real que nunca va a llegar) - asi
    un test mal armado (numero de respuestas que no coincide con los
    prompts reales) falla rapido y explicito."""

    def __init__(self, respuestas: list[str], salida_fn=print):
        self.respuestas = list(respuestas)
        self.salida_fn = salida_fn

    def __call__(self, prompt: str) -> str:
        if not self.respuestas:
            raise AssertionError(f"Se agotaron las respuestas scripteadas, pero el flujo sigue pidiendo input (prompt: {prompt!r})")
        resp = self.respuestas.pop(0)
        self.salida_fn(f"{prompt}{resp}  [scripteado]")
        return resp


def salida_silenciosa(_texto):
    pass  # el test imprime sus propios [OK]/[FALLO], no hace falta el log completo de intervencion.py


def buscar_en_pagina_local(codigo: str) -> str:
    """Abre la pagina local real (headless) con Playwright, busca
    `codigo` y devuelve el texto de #resultado. Esto es lo mas parecido
    a lo que haria un CPxxx.py real, pero 100% local (file://, sin LDS)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.goto(URL_PAGINA)
        page.fill("#codigo", codigo)
        page.click("#buscar")
        texto = page.inner_text("#resultado")
        browser.close()
        return texto


print("=" * 70)
print("Validacion local de intervencion.py (sin LDS, pagina HTML local)")
print("=" * 70)

limpiar()
run_id = r.nuevo_run_id()

# ------------------------------------------------------------------
# A) Bloqueo por dato faltante -> la persona aporta el dato -> reintento
#    exitoso.
# ------------------------------------------------------------------
print("\nA) Bloqueo por dato faltante + aportar dato + reintento exitoso")


def caso_A(contexto):
    codigo = contexto.get("aporte")
    if not codigo:
        raise iv.BloqueoRequiereIntervencion(
            que_intentaba="Buscar un producto en la pagina de consulta",
            que_encontro="No hay ningun codigo de producto configurado para este caso",
            que_necesita="Un codigo de producto valido (ver catalogo de la pagina: 100 o 200)",
            comprobaciones_pendientes=["El resultado debe decir 'Producto encontrado'"],
        )
    texto = buscar_en_pagina_local(codigo)
    if "Producto encontrado" in texto:
        return {
            "estado_funcional": "APROBADO",
            "esperado": "Producto encontrado",
            "obtenido": texto,
            "comprobaciones_completadas": ["El resultado dice 'Producto encontrado'"],
        }
    return {
        "estado_funcional": "INCUMPLIMIENTO_OBSERVADO",
        "esperado": "Producto encontrado",
        "obtenido": texto,
        "comprobaciones_completadas": [],
        "comprobaciones_pendientes": ["El resultado debe decir 'Producto encontrado'"],
    }


entrada_A = EntradaScripteada(["1", "100"])  # 1=Aportar dato, despues el dato en si
reg_A = iv.ejecutar_con_intervencion(
    PDIR, run_id, "CPL01", "RF-LOCAL", "CU-LOCAL", caso_A,
    entrada_fn=entrada_A, salida_fn=salida_silenciosa,
)
check("A: estado final APROBADO (el dato aportado destrabo el caso)", reg_A["estado_funcional"] == "APROBADO")
check("A: tipo_ejecucion quedo MIXTA (hubo intervencion)", reg_A["tipo_ejecucion"] == "MIXTA")
check("A: se registro la observacion con el dato aportado ('100')", reg_A["intervencion"] and reg_A["intervencion"]["observaciones"][0]["texto"] == "100")
check("A: el resultado.json quedo persistido", (PDIR / "resultados_TEST_INTERVENCION" / run_id / "CPL01" / str(reg_A["intento"]) / "resultado.json").is_file())

# ------------------------------------------------------------------
# B) Bloqueo -> exploracion manual (navegador VISIBLE real, se cierra
#    solo via respuesta scripteada "listo") -> aportar dato -> reintento.
# ------------------------------------------------------------------
print("\nB) Bloqueo + exploracion manual (navegador visible) + aportar dato")

entrada_B = EntradaScripteada([
    "2",       # Iniciar exploracion manual
    "listo",   # cierra el navegador de inmediato (scripteado, sin espera real)
    "1",       # tras explorar: Aportar dato
    "200",     # el dato
])
reg_B = iv.ejecutar_con_intervencion(
    PDIR, run_id, "CPL02", "RF-LOCAL", "CU-LOCAL", caso_A,
    url_para_exploracion=URL_PAGINA,
    entrada_fn=entrada_B, salida_fn=salida_silenciosa,
)
check("B: estado final APROBADO (tras explorar y aportar el dato)", reg_B["estado_funcional"] == "APROBADO")
check("B: tipo_ejecucion MIXTA", reg_B["tipo_ejecucion"] == "MIXTA")
acciones_B = [o["accion"] for o in reg_B["intervencion"]["observaciones"]]
check("B: quedo registrada la accion EXPLORACION_MANUAL", "EXPLORACION_MANUAL" in acciones_B)
check("B: quedo registrada la accion APORTAR_DATO despues de explorar", "APORTAR_DATO" in acciones_B)
captura_B = PDIR / "resultados_TEST_INTERVENCION" / run_id / "CPL02" / str(reg_B["intento"] - 1) / "evidencia" / "exploracion_manual_final.png"
check("B: se guardo una captura de la exploracion manual (cierre correcto del navegador)", captura_B.is_file())

# ------------------------------------------------------------------
# C) Reintentar sin cambios hasta agotar el limite -> queda BLOQUEADO
#    (reintento/continuacion segura: nunca se cuelga en un loop infinito).
# ------------------------------------------------------------------
print("\nC) Reintentar repetidamente sin cambios -> se agota el limite, queda pendiente")


def caso_C_nunca_se_arregla(contexto):
    raise iv.BloqueoRequiereIntervencion(
        que_intentaba="Verificar un dato que no existe en ningun catalogo",
        que_encontro="Codigo 999 no existe (y nunca va a existir en esta pagina de juguete)",
        que_necesita="Este caso esta pensado para NO resolverse solo reintentando",
    )


entrada_C = EntradaScripteada(["3", "3"])  # Reintentar, Reintentar (se agota en max_reintentos=2)
reg_C = iv.ejecutar_con_intervencion(
    PDIR, run_id, "CPL03", "RF-LOCAL", "CU-LOCAL", caso_C_nunca_se_arregla,
    max_reintentos=2, entrada_fn=entrada_C, salida_fn=salida_silenciosa,
)
check("C: queda BLOQUEADO_DATOS tras agotar los reintentos (no un loop infinito)", reg_C["estado_funcional"] == "BLOQUEADO_DATOS")
check("C: tipo_ejecucion MIXTA", reg_C["tipo_ejecucion"] == "MIXTA")

# ------------------------------------------------------------------
# D) Dejar pendiente de inmediato -> el lote sigue con el siguiente caso
#    (simulado con un mini-loop de 2 casos: CPL04 bloqueado+pendiente,
#    CPL05 normal sin bloqueo).
# ------------------------------------------------------------------
print("\nD) Dejar pendiente y continuar con otros casos")

entrada_D = EntradaScripteada(["4"])  # Dejar pendiente
reg_D1 = iv.ejecutar_con_intervencion(
    PDIR, run_id, "CPL04", "RF-LOCAL", "CU-LOCAL", caso_C_nunca_se_arregla,
    entrada_fn=entrada_D, salida_fn=salida_silenciosa,
)


def caso_D_sin_bloqueo(contexto):
    return {"estado_funcional": "APROBADO", "esperado": "ok", "obtenido": "ok", "comprobaciones_completadas": ["trivial"]}


reg_D2 = iv.ejecutar_con_intervencion(
    PDIR, run_id, "CPL05", "RF-LOCAL", "CU-LOCAL", caso_D_sin_bloqueo,
    entrada_fn=EntradaScripteada([]), salida_fn=salida_silenciosa,
)
check("D: CPL04 quedo BLOQUEADO_DATOS (pendiente)", reg_D1["estado_funcional"] == "BLOQUEADO_DATOS")
check("D: el lote SIGUIO con CPL05 (no se corto todo por el bloqueo de CPL04)", reg_D2["estado_funcional"] == "APROBADO")
check("D: CPL04 consumio un solo intento (no reintento solo por dejarlo pendiente)", reg_D1["intento"] == 1)

# ------------------------------------------------------------------
# E) Identificacion de ejecucion MIXTA vs AUTOMATICA.
# ------------------------------------------------------------------
print("\nE) Identificacion de ejecucion MIXTA vs AUTOMATICA")
check("E: un caso SIN bloqueo queda AUTOMATICA (no MIXTA)", reg_D2["tipo_ejecucion"] == "AUTOMATICA")
check("E: un caso CON intervencion queda MIXTA (A, B y C arriba)", reg_A["tipo_ejecucion"] == "MIXTA" and reg_B["tipo_ejecucion"] == "MIXTA" and reg_C["tipo_ejecucion"] == "MIXTA")

# ------------------------------------------------------------------
# F) ColaPendientes - modo cola (no bloquea workers paralelos).
# ------------------------------------------------------------------
print("\nF) Cola de pendientes - modo no bloqueante para batches paralelos")
cola = iv.ColaPendientes(PDIR, run_id)
try:
    caso_C_nunca_se_arregla({})
except iv.BloqueoRequiereIntervencion as b1:
    cola.encolar("CPL06", "RF-LOCAL", "CU-LOCAL", caso_C_nunca_se_arregla, b1)
try:
    caso_A({})
except iv.BloqueoRequiereIntervencion as b2:
    cola.encolar("CPL07", "RF-LOCAL", "CU-LOCAL", caso_A, b2)

check("F: la cola acumulo los 2 bloqueos sin pedir input todavia", len(cola) == 2)
entrada_F = EntradaScripteada(["4", "1", "100"])  # CPL06: pendiente | CPL07: aportar dato 100
registros_F = cola.procesar_secuencial(entrada_fn=entrada_F, salida_fn=salida_silenciosa)
check("F: la cola proceso los 2 pendientes secuencialmente", len(registros_F) == 2)
check("F: CPL06 (dejado pendiente) quedo BLOQUEADO_DATOS", registros_F[0]["estado_funcional"] == "BLOQUEADO_DATOS")
check("F: CPL07 (con dato aportado) quedo APROBADO", registros_F[1]["estado_funcional"] == "APROBADO")

# ------------------------------------------------------------------
r._resultados_dir = _RESULTADOS_DIR_REAL  # restaurar

print("\n" + "=" * 70)
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} validacion(es) fallaron: {FALLOS}")
    sys.exit(1)
else:
    print("RESULTADO: todas las validaciones OK.")
    print(f"\nPodes inspeccionar los archivos generados en:\n  {PDIR / 'resultados_TEST_INTERVENCION'}")
    sys.exit(0)
