"""
ejecutar_con_resultados.py - GENERICO (copia textual del framework, igual
que run_all.py y generar_reporte_excel.py - no hace falta editarlo por
proyecto). Corre los CPxxx.py de este proyecto exactamente igual que
`run_all.py` (reusa su misma funcion `correr_uno()`, sin duplicar
logica), pero ademas persiste cada resultado + su evidencia en
`resultados/<run_id>/<CP>/<intento>/` via `_framework/resultados.py`,
para no perder el historial de corridas - los CPxxx.py borran su propia
carpeta <CP>/ al arrancar, asi que sin esto una 2da corrida pisa la
evidencia de la 1ra (ver docstring de resultados.py).

Nace del piloto Auto-LDS (MS024472, Etapa 3/6) - validado ahi primero
contra LDS real antes de generalizarse a cualquier proyecto.

Uso (identico a run_all.py, mismos flags):
    .venv\\Scripts\\python.exe ejecutar_con_resultados.py --solo CP001,CP002 --video
    .venv\\Scripts\\python.exe ejecutar_con_resultados.py --rf RF-01

Al final imprime una linea "WEBAPP_RESUMEN: {...}" (JSON compacto) que
la webapp (_framework/webapp/procesos.py) parsea para mostrar el
resultado - no omitir ni cambiar ese formato si se edita este archivo.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "_framework") if (DIR.parent / "_framework").is_dir() else str(DIR.parent))

import resultados as r  # noqa: E402

# Carga explicita por RUTA DE ARCHIVO (no "import run_all") - cada
# proyecto tiene su PROPIA copia de run_all.py, y _framework/ tambien
# tiene una (el template generico) con el MISMO nombre de modulo. Un
# simple `import run_all` es ambiguo (depende del orden de sys.path) -
# BUG REAL confirmado en vivo (MS024472, Etapa 6): goteaba la version
# equivocada (el DIR del run_all.py de _framework/, buscando los
# CPxxx.py en el lugar equivocado). Cargar por ruta de archivo elimina
# esa ambiguedad para siempre.
_spec = importlib.util.spec_from_file_location(f"run_all_{DIR.name}", DIR / "run_all.py")
_run_all = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_all)
CASES = _run_all.CASES
METADATA = _run_all.METADATA
correr_uno = _run_all.correr_uno
numero_cp = _run_all.numero_cp
parse_args = _run_all.parse_args
seleccionar_casos = _run_all.seleccionar_casos


def main():
    if not METADATA:
        raise SystemExit(
            "generate_scripts.py todavia no genero ningun caso (CASES vacio) - "
            "completar el Paso 3 del checklist (escribir los casos) antes de ejecutar pruebas."
        )

    args = parse_args()
    casos = seleccionar_casos(args)
    headless = not args.headed
    word = not args.sin_word

    run_id = r.nuevo_run_id()
    print(f"Corriendo {len(casos)} caso(s) con registro de resultados | run_id={run_id}")
    print(f"Resultados en: {DIR / 'resultados' / run_id}\n")

    # Ademas de resultados/ (Etapa 3), se escribe el MISMO reporte CSV
    # que run_all.py (reportes/reporte_<marca>.csv) - asi
    # generar_reporte_excel.py (que lee de ahi) sigue funcionando sin
    # cambios para cualquier proyecto, use o no este script.
    reportes_dir = DIR / "reportes"
    logs_dir = reportes_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_csv = reportes_dir / f"reporte_{marca}.csv"
    filas_csv = []

    aprobados = 0
    fallidos = []  # [(cp, detalle)] - para el resumen y el prompt de ayuda
    for i, cp in enumerate(casos, 1):
        meta = METADATA[cp]
        print(f"[{i}/{len(casos)}] {cp} ...", end=" ", flush=True)
        inicio = time.time()
        resultado_crudo = correr_uno(cp, headless, args.video, word, args.slowmo, args.timeout)
        fin = time.time()
        print(f"{resultado_crudo['resultado']} ({resultado_crudo['duracion_seg']}s)")

        (logs_dir / f"{cp}.log").write_text(resultado_crudo["salida_completa"], encoding="utf-8")
        filas_csv.append([cp, meta["rf"], meta["cu"], meta["name"], resultado_crudo["resultado"], resultado_crudo["duracion_seg"], resultado_crudo["detalle"]])

        estado_funcional = r.mapear_resultado_crudo(resultado_crudo["resultado"])
        registro = r.registrar_resultado(
            DIR, run_id, cp,
            rf=meta["rf"], cu=meta["cu"],
            estado_funcional=estado_funcional,
            inicio=inicio, fin=fin,
            tipo_ejecucion="AUTOMATICA",
            esperado=meta.get("esperado"),
            obtenido=resultado_crudo["detalle"],
            excepcion=resultado_crudo["detalle"] if resultado_crudo["resultado"] != "OK" else None,
            origen_evidencia=DIR / cp,
        )
        if registro["estado_funcional"] == "APROBADO":
            aprobados += 1
        else:
            fallidos.append((cp, resultado_crudo["detalle"]))

        # Nota de clasificacion: `estado_funcional` arriba viene del mapeo
        # CONSERVADOR OK->APROBADO / cualquier otra cosa->ERROR_AUTOMATIZACION
        # (ver mapear_resultado_crudo() en resultados.py) - run_all.py hoy
        # no distingue POR QUE fallo un caso. Para clasificar de verdad
        # entre INCUMPLIMIENTO_OBSERVADO / BLOQUEADO_DATOS /
        # BLOQUEADO_PERMISOS_AMBIENTE hace falta revisar el log de cada
        # CP fallido a mano y corregir el campo en el resultado.json
        # correspondiente - este script no inventa esa distincion solo.

    reportes_dir.mkdir(parents=True, exist_ok=True)
    with open(reporte_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["CP", "RF", "CU", "Nombre", "Resultado", "Duracion_seg", "Detalle"])
        writer.writerows(filas_csv)

    print(f"\nTerminado. {aprobados}/{len(casos)} APROBADO (clasificacion automatica conservadora).")
    print(f"Reporte CSV (compatible con generar_reporte_excel.py): {reporte_csv}")
    print(f"Resumen de esta corrida: {DIR / 'resultados' / run_id / '_resumen_corrida.json'}")
    print(f"Ultimo estado por CP (todas las corridas): {DIR / 'resultados' / '_ultimo_estado.json'}")

    prompt_ayuda = None
    if fallidos:
        print(
            "\nOJO: los casos que no dieron OK quedaron clasificados como "
            "ERROR_AUTOMATIZACION por defecto (mapeo conservador) - revisar "
            "a mano cada resultado.json fallido y corregir estado_funcional "
            "si en realidad es INCUMPLIMIENTO_OBSERVADO, BLOQUEADO_DATOS o "
            "BLOQUEADO_PERMISOS_AMBIENTE segun corresponda."
        )
        detalle_fallidos = "\n".join(f"- {cp}: {detalle}" for cp, detalle in fallidos)
        prompt_ayuda = (
            f"Proyecto: {DIR.name}\n"
            f"Corrida: {run_id}\n\n"
            f"{len(fallidos)} de {len(casos)} caso(s) no dieron OK:\n{detalle_fallidos}\n\n"
            "Revisa cada resultado.json en resultados/" + run_id + "/<CP>/<intento>/ "
            "(capturas, video, Word en la carpeta evidencia/) y el log en "
            "reportes/logs/<CP>.log. Para cada uno, diagnostica si es: dato de "
            "prueba agotado/invalido, un defecto real de la app, o un bug de "
            "esta automatizacion - y corrige generate_scripts.py si corresponde."
        )

    resumen = {
        "casos_totales": len(casos), "casos_aprobados": aprobados,
        "casos_fallidos": len(fallidos), "run_id": run_id,
        "prompt_ayuda": prompt_ayuda,
    }
    print("WEBAPP_RESUMEN: " + json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    main()
