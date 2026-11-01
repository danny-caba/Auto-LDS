"""
resultados.py - Persistencia de resultados y evidencias POR CORRIDA, por
caso y por intento.

Nace para el piloto MS024472 (Etapa 3 del plan de piloto Auto-LDS).
Importante: este archivo, por si solo, NO CAMBIA el comportamiento de
ningun proyecto existente - ningun run_all.py lo importa. Hace falta un
adaptador explicito que lo use (ver MS024472/ejecutar_con_resultados.py).
No es parte del flujo generico que nuevo_proyecto.py copia a cada
proyecto nuevo.

---------------------------------------------------------------------
QUE PROBLEMA RESUELVE
---------------------------------------------------------------------
Cada CPxxx.py generado borra su propia carpeta de evidencia
(`<CP>/`) al arrancar (`if EVIDENCIA.exists(): shutil.rmtree(...)`,
patron presente en el HEADER_TEMPLATE de cada generate_scripts.py) -
por diseno, para que cada corrida individual quede con evidencia
limpia. Eso significa que una 2da corrida del mismo caso BORRA la
evidencia de la 1ra. Para el piloto, donde necesitamos conservar el
historial de intentos (no solo "la ultima corrida"), este modulo copia
la evidencia generada a una estructura aparte ANTES de que la proxima
corrida la pise, y guarda un registro estructurado (JSON) de cada
intento.

---------------------------------------------------------------------
ESTRUCTURA EN DISCO (dentro de la carpeta del proyecto)
---------------------------------------------------------------------
resultados/
  <run_id>/
    <CP>/
      <intento>/
        resultado.json      - ver ESQUEMA_RESULTADO mas abajo
        evidencia/            - copia de capturas/.docx/.webm de ESE
                                 intento puntual (best-effort, ver
                                 copiar_evidencia())
    _resumen_corrida.json   - resumen de ESTA corrida (se recalcula
                               incrementalmente despues de cada caso,
                               asi que una corrida interrumpida deja
                               el resumen de lo que SI llego a correr)
  _ultimo_estado.json       - ultimo resultado conocido POR CP,
                               combinando TODAS las corridas (distinto
                               del resumen de una corrida puntual)

---------------------------------------------------------------------
GARANTIAS Y LIMITES (leer antes de confiar en esto a ciegas)
---------------------------------------------------------------------
- `registrar_resultado()` escribe a disco de forma SINCRONA apenas
  termina cada caso - si la corrida se interrumpe despues (Ctrl+C,
  crash), los casos YA registrados quedan intactos en disco.
- El resultado FUNCIONAL (`estado_funcional`) y el resultado de
  GENERAR LA EVIDENCIA (`evidencia.estado_generacion`) se calculan y
  guardan por separado, a proposito: si copiar_evidencia() falla (ej.
  disco lleno, archivo bloqueado), NO cambia `estado_funcional` - un
  caso que paso funcionalmente sigue figurando como tal, con el error
  de evidencia anotado aparte.
- `_sanitizar_texto()` es BEST-EFFORT: busca patrones de texto conocidos
  (password=, token=, Authorization:, Cookie:, etc.) en los campos de
  texto libre (excepcion, obtenido, detalle, comprobaciones) y los
  redacta. NO escanea el CONTENIDO de capturas/video/.docx copiados a
  `evidencia/` - esos archivos se copian tal cual los genero el CPxxx.py
  original. Este modulo NUNCA debe describirse como que "garantiza" que
  las evidencias esten libres de datos sensibles - solo que los campos
  de texto estructurado pasan por este filtro best-effort.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ESTADOS_FUNCIONALES = (
    "APROBADO",
    "INCUMPLIMIENTO_OBSERVADO",
    "BLOQUEADO_DATOS",
    "BLOQUEADO_PERMISOS_AMBIENTE",
    "ERROR_AUTOMATIZACION",
)

TIPOS_EJECUCION = ("AUTOMATICA", "MANUAL", "MIXTA")

# Mapeo por defecto desde el resultado crudo de run_all.py (OK/FALLO/
# TIMEOUT/ERROR) a un estado funcional de los 5 de arriba. Es un punto
# de partida CONSERVADOR, no una clasificacion real: run_all.py hoy no
# distingue POR QUE fallo un caso (dato faltante vs. permiso vs. defecto
# real vs. bug de automatizacion) - esa distincion fina requiere mirar
# el log/la intervencion manual (Etapa 4) o que el caso la reporte
# explicitamente. Un caller puede pasar `estado_funcional` explicito a
# registrar_resultado() para no depender de este mapeo.
_MAPEO_RESULTADO_CRUDO = {
    "OK": "APROBADO",
    "FALLO": "ERROR_AUTOMATIZACION",
    "TIMEOUT": "ERROR_AUTOMATIZACION",
    "ERROR": "ERROR_AUTOMATIZACION",
}

# 2 patrones encadenados: primero el caso especifico "Authorization:
# Bearer <token>" (el esquema "Bearer" mete una palabra extra entre la
# clave y el valor real, que el patron generico de abajo no cubre),
# despues el generico "clave[:=]valor" para password/token/cookie/etc.
_PATRON_BEARER = re.compile(r"(?i)(authorization)\s*[:=]\s*Bearer\s+(\S+)")
_PATRON_SECRETOS = re.compile(
    r"(?i)([a-z0-9_-]*"
    r"(?:password|contrase[nñ]a|pwd|passwd|token|secret|authorization|cookie|api[_-]?key)"
    r"[a-z0-9_-]*)"
    r"\s*[:=]\s*(\S+)"
)


def mapear_resultado_crudo(resultado_crudo: str) -> str:
    """OK/FALLO/TIMEOUT/ERROR (convencion de run_all.py) -> uno de los 5
    ESTADOS_FUNCIONALES, con el mapeo conservador de arriba. Documentar
    siempre en el caller si este mapeo por defecto se uso tal cual o si
    se sobreescribio con una clasificacion real."""
    return _MAPEO_RESULTADO_CRUDO.get(resultado_crudo.upper(), "ERROR_AUTOMATIZACION")


def nuevo_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resultados_dir(pdir: Path) -> Path:
    return pdir / "resultados"


def _carpeta_intento(pdir: Path, run_id: str, cp: str, intento: int) -> Path:
    return _resultados_dir(pdir) / run_id / cp / str(intento)


def siguiente_intento(pdir: Path, run_id: str, cp: str) -> int:
    """Primer numero de intento libre (arranca en 1) para este run_id+CP -
    nunca pisa un intento ya registrado, ni dentro del mismo run_id ni
    entre corridas distintas (cada run_id vive en su propia carpeta)."""
    carpeta_cp = _resultados_dir(pdir) / run_id / cp
    if not carpeta_cp.is_dir():
        return 1
    existentes = [int(p.name) for p in carpeta_cp.iterdir() if p.is_dir() and p.name.isdigit()]
    return (max(existentes) + 1) if existentes else 1


def _sanitizar_texto(texto: Any) -> Any:
    """Best-effort: redacta el VALOR de patrones conocidos de secretos en
    un string, dejando la clave visible para trazabilidad (ej.
    'password=Ejemplo123' -> 'password=***REDACTADO***'). No toca
    nada que no sea texto (numeros, None, bool pasan tal cual)."""
    if not isinstance(texto, str):
        return texto
    texto = _PATRON_BEARER.sub(lambda m: f"{m.group(1)}=***REDACTADO***", texto)
    texto = _PATRON_SECRETOS.sub(lambda m: f"{m.group(1)}=***REDACTADO***", texto)
    return texto


def _sanitizar_valor(valor: Any) -> Any:
    if isinstance(valor, str):
        return _sanitizar_texto(valor)
    if isinstance(valor, dict):
        return {k: _sanitizar_valor(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_sanitizar_valor(v) for v in valor]
    return valor


def copiar_evidencia(pdir: Path, origen_dir: Path | None, destino_dir: Path) -> dict:
    """Copia el contenido de `origen_dir` (la carpeta <CP>/ que el
    CPxxx.py acaba de llenar) a `destino_dir` (resultados/<run_id>/<CP>/
    <intento>/evidencia/). Nunca lanza excepcion hacia el caller -
    cualquier error queda en el dict devuelto, para que un fallo ACA no
    se confunda nunca con un fallo del caso en si (ver docstring del
    modulo, "GARANTIAS Y LIMITES"). `pdir` se usa solo para guardar
    rutas RELATIVAS a la carpeta del proyecto en el registro (mas legible
    que rutas absolutas de la maquina)."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    if origen_dir is None or not origen_dir.is_dir():
        return {"estado_generacion": "SIN_ORIGEN", "detalle": f"No existe la carpeta de origen: {origen_dir}", "rutas": []}
    rutas: list[str] = []
    try:
        for item in origen_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, destino_dir / item.name)
                rutas.append(str((destino_dir / item.name).relative_to(pdir)))
        return {"estado_generacion": "OK", "detalle": None, "rutas": rutas}
    except Exception as e:  # noqa: BLE001 - best-effort, nunca debe tumbar al caller
        return {"estado_generacion": f"ERROR: {e}", "detalle": str(e), "rutas": rutas}


def registrar_resultado(
    pdir: Path,
    run_id: str,
    cp: str,
    *,
    rf: str,
    cu: str,
    estado_funcional: str,
    inicio: float | str,
    fin: float | str,
    intento: int | None = None,
    ambiente: str | None = None,
    version_probada: str | None = None,
    tipo_ejecucion: str = "AUTOMATICA",
    esperado: str | None = None,
    obtenido: str | None = None,
    comprobaciones_completadas: list[str] | None = None,
    comprobaciones_pendientes: list[str] | None = None,
    paso_fallido: str | None = None,
    excepcion: str | None = None,
    origen_evidencia: Path | None = None,
    intervencion: dict | None = None,
) -> dict:
    """Punto de entrada principal: arma el registro, copia evidencia
    (best-effort, separado del resultado funcional) y escribe
    resultado.json de forma SINCRONA (si la corrida se corta despues de
    este return, este intento ya quedo persistido). Tambien actualiza
    `_ultimo_estado.json` (ultimo conocido por CP) y
    `_resumen_corrida.json` (resumen de ESTE run_id)."""
    if estado_funcional not in ESTADOS_FUNCIONALES:
        raise ValueError(f"estado_funcional invalido: {estado_funcional!r} (debe ser uno de {ESTADOS_FUNCIONALES})")
    if tipo_ejecucion not in TIPOS_EJECUCION:
        raise ValueError(f"tipo_ejecucion invalido: {tipo_ejecucion!r} (debe ser uno de {TIPOS_EJECUCION})")

    if intento is None:
        intento = siguiente_intento(pdir, run_id, cp)
    carpeta = _carpeta_intento(pdir, run_id, cp, intento)
    carpeta.mkdir(parents=True, exist_ok=True)

    info_evidencia = copiar_evidencia(pdir, origen_evidencia, carpeta / "evidencia")

    duracion_seg = None
    if isinstance(inicio, (int, float)) and isinstance(fin, (int, float)):
        duracion_seg = round(fin - inicio, 2)

    registro = {
        "proyecto": pdir.name,
        "cp": cp,
        "rf": rf,
        "cu": cu,
        "run_id": run_id,
        "intento": intento,
        "ambiente": ambiente,
        "version_probada": version_probada,
        "inicio": inicio if isinstance(inicio, str) else datetime.fromtimestamp(inicio).isoformat(),
        "fin": fin if isinstance(fin, str) else datetime.fromtimestamp(fin).isoformat(),
        "duracion_seg": duracion_seg,
        "tipo_ejecucion": tipo_ejecucion,
        "estado_funcional": estado_funcional,
        "esperado": esperado,
        "obtenido": obtenido,
        "comprobaciones_completadas": comprobaciones_completadas or [],
        "comprobaciones_pendientes": comprobaciones_pendientes or [],
        "paso_fallido": paso_fallido,
        "excepcion": excepcion,
        "evidencia": info_evidencia,
        "intervencion": intervencion,
        "registrado_en": datetime.now().isoformat(),
    }
    registro = _sanitizar_valor(registro)

    (carpeta / "resultado.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")

    _actualizar_ultimo_estado(pdir, registro)
    _actualizar_resumen_corrida(pdir, run_id)

    return registro


def _actualizar_ultimo_estado(pdir: Path, registro: dict) -> None:
    """`resultados/_ultimo_estado.json`: 1 entrada por CP, con el
    resultado MAS RECIENTE visto (puede venir de distintos run_id) -
    distinto del resumen de una corrida puntual, que solo mira UN
    run_id. No se sobreescribe nada del historial por intento (eso vive
    en resultado.json de cada carpeta) - esto es solo un indice rapido
    de "como quedo cada CP la ultima vez"."""
    archivo = _resultados_dir(pdir) / "_ultimo_estado.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    datos = {}
    if archivo.is_file():
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            datos = {}
    datos[registro["cp"]] = {
        "run_id": registro["run_id"],
        "intento": registro["intento"],
        "estado_funcional": registro["estado_funcional"],
        "fin": registro["fin"],
        "ruta": f"resultados/{registro['run_id']}/{registro['cp']}/{registro['intento']}/resultado.json",
    }
    archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def _actualizar_resumen_corrida(pdir: Path, run_id: str) -> None:
    """Recalcula `_resumen_corrida.json` leyendo TODOS los resultado.json
    que existan hasta ahora bajo resultados/<run_id>/ (se llama despues
    de CADA caso, no solo al final - asi una corrida interrumpida deja
    el resumen de lo que si llego a correr, en vez de nada)."""
    carpeta_run = _resultados_dir(pdir) / run_id
    registros = []
    for resultado_json in sorted(carpeta_run.glob("*/*/resultado.json")):
        try:
            registros.append(json.loads(resultado_json.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue

    conteo: dict[str, int] = {}
    for r in registros:
        conteo[r["estado_funcional"]] = conteo.get(r["estado_funcional"], 0) + 1

    resumen = {
        "run_id": run_id,
        "proyecto": pdir.name,
        "actualizado_en": datetime.now().isoformat(),
        "total_registros": len(registros),
        "por_estado": conteo,
        "casos": [{"cp": r["cp"], "intento": r["intento"], "estado_funcional": r["estado_funcional"]} for r in registros],
    }
    (carpeta_run / "_resumen_corrida.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_ultimo_estado(pdir: Path) -> dict:
    archivo = _resultados_dir(pdir) / "_ultimo_estado.json"
    if not archivo.is_file():
        return {}
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
