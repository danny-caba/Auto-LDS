"""
memoria_central.py - Memoria central del piloto Auto-LDS (Etapa 5),
vive en disco bajo `_framework/conocimiento/` - DISTINTA de la memoria
automatica de Claude Code (la de `C:\\Users\\<usuario>\\.claude\\...\\memory\\`,
atada a esta instalacion puntual de Claude Code). Esta memoria es
PARTE DEL REPOSITORIO: cualquier sesion nueva de Claude (u otra
persona) que abra este proyecto desde cero puede leerla con solo
archivos, sin depender del historial de conversacion.

---------------------------------------------------------------------
QUE GUARDA Y COMO (ver _framework/conocimiento/README.md una vez creado)
---------------------------------------------------------------------
Una entrada = un hecho verificable (o pendiente de verificar) sobre el
proyecto: una regla documentada, un comportamiento observado en vivo,
una solucion tecnica comprobada, un dato de prueba reutilizable, una
intervencion manual, o una duda pendiente. Cada entrada es un .json
(nunca .yaml/.py - ver mas abajo "NUNCA SE EJECUTA") con un esquema
fijo (ver ESQUEMA_ENTRADA en el docstring de agregar_entrada()).

---------------------------------------------------------------------
NUNCA SE EJECUTA CONTENIDO DE MEMORIA COMO CODIGO
---------------------------------------------------------------------
Este modulo SOLO lee/escribe JSON con `json.load`/`json.dump` - nunca
`eval()`, `exec()`, `pickle`, ni importa dinamicamente nada desde
`conocimiento/`. Una entrada maliciosa o corrupta puede, como mucho,
fallar a parsear (json.JSONDecodeError) - nunca ejecutar nada.

---------------------------------------------------------------------
GARANTIAS (y sus limites)
---------------------------------------------------------------------
- `buscar(solo_vigentes=True)` (el default) EXCLUYE automaticamente
  INVALIDADO y REEMPLAZADO - invalidar una entrada hace que deje de
  recomendarse sin necesidad de que nadie se acuerde de filtrarla a
  mano.
- Invalidar/reemplazar NUNCA borra el archivo - el historial completo
  queda en disco (ver `reemplaza`/`reemplazada_por`, y
  `motivo_invalidacion`).
- Las entradas nuevas entran como PROVISIONAL por defecto -
  `verificar_entrada()` es una llamada APARTE, explicita, para pasar a
  VERIFICADO (nunca se marca solo).
- NO guarda secretos (quien agregue una entrada es responsable de no
  pegar contraseñas/tokens ahi - este modulo no sanitiza contenido
  libre, a diferencia de resultados.py que si lo hace para sus propios
  campos. Ver tambien feedback del propio piloto: preferir referenciar
  evidencias en vez de copiar documentos completos).
"""
from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

TIPOS = (
    "REGLA_DOCUMENTADA",
    "COMPORTAMIENTO_OBSERVADO",
    "SOLUCION_TECNICA_COMPROBADA",
    "DATO_DE_PRUEBA",
    "INTERVENCION_MANUAL",
    "DUDA_PENDIENTE",
)

ESTADOS = ("PROVISIONAL", "VERIFICADO", "INVALIDADO", "REEMPLAZADO")

_RAIZ_FRAMEWORK = Path(__file__).resolve().parent


def _conocimiento_dir() -> Path:
    return _RAIZ_FRAMEWORK / "conocimiento"


def _entradas_dir() -> Path:
    return _conocimiento_dir() / "entradas"


def _consultas_dir() -> Path:
    return _conocimiento_dir() / "consultas"


def _hoy() -> str:
    return date.today().isoformat()


def _cargar_indice() -> dict:
    archivo = _conocimiento_dir() / "indice.json"
    if not archivo.is_file():
        return {"entradas": {}, "actualizado_en": None}
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"entradas": {}, "actualizado_en": None}


def _guardar_indice(indice: dict) -> None:
    _conocimiento_dir().mkdir(parents=True, exist_ok=True)
    indice["actualizado_en"] = datetime.now().isoformat()
    (_conocimiento_dir() / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _regenerar_indice_md(indice)


def _regenerar_indice_md(indice: dict) -> None:
    """Vista humana generada a partir de indice.json - NUNCA editar este
    .md a mano, se pisa cada vez que cambia una entrada. Secciones tal
    como las pide la Etapa 5: general / por modulo / datos de prueba /
    intervenciones / dudas pendientes."""
    entradas = indice.get("entradas", {})

    def _lista(filtro) -> list[str]:
        filas = []
        for id_, meta in sorted(entradas.items()):
            if filtro(meta):
                estado_tag = f"[{meta['estado']}]"
                filas.append(f"- **{id_}** {estado_tag} — {meta['resumen']} _(fuente: {meta.get('fuente', '?')})_")
        return filas or ["  _(sin entradas todavia)_"]

    secciones = []
    secciones.append("# Índice de conocimiento (generado — no editar a mano)\n")
    secciones.append(f"_Actualizado: {indice.get('actualizado_en', '?')}_\n")

    secciones.append("## Conocimiento general\n")
    secciones.extend(_lista(lambda m: m.get("tipo") in ("REGLA_DOCUMENTADA", "COMPORTAMIENTO_OBSERVADO", "SOLUCION_TECNICA_COMPROBADA") and not m.get("modulo")))

    secciones.append("\n## Conocimiento por módulo\n")
    modulos = sorted({m["modulo"] for m in entradas.values() if m.get("modulo")})
    if not modulos:
        secciones.append("  _(sin entradas todavia)_")
    for mod in modulos:
        secciones.append(f"\n### {mod}\n")
        secciones.extend(_lista(lambda m, mod=mod: m.get("modulo") == mod))

    secciones.append("\n## Datos de prueba\n")
    secciones.extend(_lista(lambda m: m.get("tipo") == "DATO_DE_PRUEBA"))

    secciones.append("\n## Intervenciones\n")
    secciones.extend(_lista(lambda m: m.get("tipo") == "INTERVENCION_MANUAL"))

    secciones.append("\n## Dudas pendientes\n")
    secciones.extend(_lista(lambda m: m.get("tipo") == "DUDA_PENDIENTE"))

    (_conocimiento_dir() / "indice.md").write_text("\n".join(secciones) + "\n", encoding="utf-8")


def nuevo_id() -> str:
    indice = _cargar_indice()
    numeros = [int(id_[5:]) for id_ in indice["entradas"] if id_.startswith("CONO-") and id_[5:].isdigit()]
    siguiente = (max(numeros) + 1) if numeros else 1
    return f"CONO-{siguiente:04d}"


def agregar_entrada(
    tipo: str,
    descripcion: str,
    *,
    fuente: str,
    requerimiento_origen: str,
    modulo: str | None = None,
    ambiente: str | None = None,
    version: str | None = None,
    referencias_evidencia: list[str] | None = None,
    estado: str = "PROVISIONAL",
    condiciones_revalidacion: str | None = None,
    reemplaza: str | None = None,
) -> dict:
    """ESQUEMA_ENTRADA (lo que queda guardado en entradas/<id>.json):
    id, tipo, descripcion, modulo, ambiente, version, fuente,
    requerimiento_origen, referencias_evidencia, estado,
    fecha_creacion, fecha_ultima_verificacion, condiciones_revalidacion,
    reemplaza, reemplazada_por (null hasta que algo la reemplace),
    motivo_invalidacion (null salvo que estado sea INVALIDADO).

    Si `reemplaza` apunta a una entrada existente, esa entrada pasa a
    estado REEMPLAZADO (nunca se borra) y se le completa
    `reemplazada_por` con el id nuevo - el historial completo queda
    trazable en ambos sentidos."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo invalido: {tipo!r} (debe ser uno de {TIPOS})")
    if estado not in ESTADOS:
        raise ValueError(f"estado invalido: {estado!r} (debe ser uno de {ESTADOS})")

    id_ = nuevo_id()
    _entradas_dir().mkdir(parents=True, exist_ok=True)

    entrada = {
        "id": id_,
        "tipo": tipo,
        "descripcion": descripcion,
        "modulo": modulo,
        "ambiente": ambiente,
        "version": version,
        "fuente": fuente,
        "requerimiento_origen": requerimiento_origen,
        "referencias_evidencia": referencias_evidencia or [],
        "estado": estado,
        "fecha_creacion": _hoy(),
        "fecha_ultima_verificacion": _hoy() if estado == "VERIFICADO" else None,
        "condiciones_revalidacion": condiciones_revalidacion,
        "reemplaza": reemplaza,
        "reemplazada_por": None,
        "motivo_invalidacion": None,
    }
    (_entradas_dir() / f"{id_}.json").write_text(json.dumps(entrada, ensure_ascii=False, indent=2), encoding="utf-8")

    indice = _cargar_indice()
    indice["entradas"][id_] = {
        "tipo": tipo, "modulo": modulo, "estado": estado,
        "resumen": descripcion[:120] + ("..." if len(descripcion) > 120 else ""),
        "fuente": fuente,
    }

    if reemplaza:
        anterior = leer_entrada(reemplaza)
        if anterior is None:
            raise ValueError(f"No existe la entrada a reemplazar: {reemplaza!r}")
        anterior["estado"] = "REEMPLAZADO"
        anterior["reemplazada_por"] = id_
        (_entradas_dir() / f"{reemplaza}.json").write_text(json.dumps(anterior, ensure_ascii=False, indent=2), encoding="utf-8")
        indice["entradas"][reemplaza]["estado"] = "REEMPLAZADO"

    _guardar_indice(indice)
    return entrada


def leer_entrada(id_: str) -> dict | None:
    archivo = _entradas_dir() / f"{id_}.json"
    if not archivo.is_file():
        return None
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def buscar(*, modulo: str | None = None, tipo: str | None = None, estado: str | None = None, solo_vigentes: bool = True) -> list[dict]:
    """`solo_vigentes=True` (default) excluye INVALIDADO/REEMPLAZADO -
    asi una solucion invalidada deja de aparecer en busquedas normales
    sin que nadie tenga que acordarse de filtrarla."""
    indice = _cargar_indice()
    resultado = []
    for id_, meta in indice["entradas"].items():
        if modulo is not None and meta.get("modulo") != modulo:
            continue
        if tipo is not None and meta.get("tipo") != tipo:
            continue
        if estado is not None and meta.get("estado") != estado:
            continue
        if solo_vigentes and meta.get("estado") in ("INVALIDADO", "REEMPLAZADO"):
            continue
        entrada = leer_entrada(id_)
        if entrada:
            resultado.append(entrada)
    return resultado


def verificar_entrada(id_: str) -> dict:
    entrada = leer_entrada(id_)
    if entrada is None:
        raise ValueError(f"No existe la entrada: {id_!r}")
    entrada["estado"] = "VERIFICADO"
    entrada["fecha_ultima_verificacion"] = _hoy()
    (_entradas_dir() / f"{id_}.json").write_text(json.dumps(entrada, ensure_ascii=False, indent=2), encoding="utf-8")
    indice = _cargar_indice()
    if id_ in indice["entradas"]:
        indice["entradas"][id_]["estado"] = "VERIFICADO"
    _guardar_indice(indice)
    return entrada


def invalidar_entrada(id_: str, motivo: str) -> dict:
    """Nunca borra el archivo - solo cambia estado + motivo. Despues de
    esto, `buscar()` (con solo_vigentes=True, el default) deja de
    devolverla."""
    entrada = leer_entrada(id_)
    if entrada is None:
        raise ValueError(f"No existe la entrada: {id_!r}")
    entrada["estado"] = "INVALIDADO"
    entrada["motivo_invalidacion"] = motivo
    (_entradas_dir() / f"{id_}.json").write_text(json.dumps(entrada, ensure_ascii=False, indent=2), encoding="utf-8")
    indice = _cargar_indice()
    if id_ in indice["entradas"]:
        indice["entradas"][id_]["estado"] = "INVALIDADO"
    _guardar_indice(indice)
    return entrada


def registrar_consulta(
    requerimiento: str,
    *,
    entradas_consultadas: list[str],
    entradas_aplicadas: list[str],
    entradas_descartadas: dict[str, str],
) -> Path:
    """Registro de que se consulto la memoria para `requerimiento` ANTES
    de armar el plan - `entradas_descartadas` es {id: motivo} (pedido
    explicito: registrar por que se descarto algo, no solo que se
    descarto). Se guarda en conocimiento/consultas/<requerimiento>.json
    - `tiene_registro_consulta()` chequea que este archivo exista."""
    _consultas_dir().mkdir(parents=True, exist_ok=True)
    registro = {
        "requerimiento": requerimiento,
        "fecha": datetime.now().isoformat(),
        "entradas_consultadas": entradas_consultadas,
        "entradas_aplicadas": entradas_aplicadas,
        "entradas_descartadas": entradas_descartadas,
    }
    archivo = _consultas_dir() / f"{requerimiento}.json"
    archivo.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    return archivo


def tiene_registro_consulta(requerimiento: str) -> bool:
    """Chequeo pedido para el proceso de preparacion del plan: ¿existe
    un registro de consulta para este requerimiento? OJO - limite
    explicito: esto verifica que el ARCHIVO exista, NO demuestra que la
    consulta haya sido razonada correctamente ni que se haya hecho de
    buena fe. Es un chequeo de PRESENCIA, no de CALIDAD."""
    return (_consultas_dir() / f"{requerimiento}.json").is_file()


def leer_registro_consulta(requerimiento: str) -> dict | None:
    archivo = _consultas_dir() / f"{requerimiento}.json"
    if not archivo.is_file():
        return None
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
