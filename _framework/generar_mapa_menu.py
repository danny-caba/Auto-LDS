"""Genera un arbol de navegacion legible (_framework/mapa_menu.md) a
partir de Opciones_Menu_Principal.xlsx (la fuente ya curada a mano,
acumulativa por proyecto/RF - ver memoria del usuario). Pensado para
escanear en segundos antes de arrancar un proyecto nuevo y ver si una
pantalla ya se mapeo en otro sprint, en vez de reexplorar a ciegas.

Tambien hace un cruce best-effort contra las lineas "Ruta de menu..."
de _framework/modulos/*.py para avisar de pantallas que ya tienen un
modulo escrito pero ninguna fila en el Excel - NO edita el Excel solo
(la regla del usuario es "no reemplazar filas existentes", y el texto
de esas lineas es demasiado inconsistente entre modulos para confiar
en insertarlo automaticamente); solo deja la lista para que el usuario
decida si agregarlas a mano.

Uso: .venv\\Scripts\\python.exe _framework\\generar_mapa_menu.py
"""
import re
import unicodedata
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
EXCEL = RAIZ / "Opciones_Menu_Principal.xlsx"
MODULOS_DIR = Path(__file__).resolve().parent / "modulos"
SALIDA = Path(__file__).resolve().parent / "mapa_menu.md"


def normalizar(texto: str) -> str:
    """Para comparar nombres de pantalla sin pelearse con tildes/mayusculas."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def leer_excel(ruta=EXCEL):
    wb = openpyxl.load_workbook(ruta)
    ws = wb.active
    filas = []
    for primer, segundo, opcion, proyecto, rf in ws.iter_rows(min_row=2, values_only=True):
        if not primer or not opcion:
            continue
        niveles = [primer] + ([segundo] if segundo else []) + [p.strip() for p in opcion.split(">")]
        filas.append((niveles, proyecto or "", rf or ""))
    return filas


def construir_arbol(filas):
    arbol = {}
    for niveles, proyecto, rf in filas:
        nodo = arbol
        for nivel in niveles[:-1]:
            nodo = nodo.setdefault(nivel, {}).setdefault("_hijos", {})
        hoja = nodo.setdefault(niveles[-1], {})
        hoja.setdefault("_usos", []).append((proyecto, rf))
    return arbol


def renderizar(arbol, nivel=0, lineas=None):
    if lineas is None:
        lineas = []
    for nombre in sorted(k for k in arbol if k not in ("_hijos", "_usos")):
        nodo = arbol[nombre]
        usos = nodo.get("_usos")
        if usos:
            partes = "; ".join(f"{proyecto} ({rf})" if rf else proyecto for proyecto, rf in usos)
            lineas.append(f"{'  ' * nivel}- **{nombre}** — {partes}")
        else:
            lineas.append(f"{'  ' * nivel}- {nombre}")
        hijos = nodo.get("_hijos")
        if hijos:
            renderizar(hijos, nivel + 1, lineas)
    return lineas


PATRON_RUTA = re.compile(r"Ruta de menu[^:\n]*:\s*(.+)", re.IGNORECASE)
TERMINADORES = (".", ":", '"', ")")


def extraer_rutas_de_modulos(max_lineas_extra=3):
    """Best-effort: localiza la linea 'Ruta de menu...:' y, si no termina
    en un caracter que cierre la frase (el docstring suele cortar a los
    ~70-80 caracteres), va sumando las lineas siguientes hasta encontrar
    un terminador o quedarse sin pinta de continuacion (linea en blanco,
    o que ya no es parte de la misma frase)."""
    hallazgos = []
    for archivo in sorted(MODULOS_DIR.glob("*.py")):
        lineas = archivo.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, linea in enumerate(lineas):
            m = PATRON_RUTA.search(linea)
            if not m:
                continue
            partes = [m.group(1).strip()]
            j = i + 1
            while (not partes[-1].endswith(TERMINADORES)) and j < len(lineas) and j < i + 1 + max_lineas_extra:
                siguiente = lineas[j].strip()
                if not siguiente or siguiente.startswith(("Componente", "Sistema", "Roles", "===")):
                    break
                partes.append(siguiente)
                j += 1
            ruta = " ".join(partes)
            ruta = ruta.rstrip(".").strip()  # punto final ANTES de buscar el parentesis final
            ruta = re.sub(r"\s*\([^)]*\)\s*$", "", ruta)  # aside final tipo "(OJO: ...)"
            ruta = ruta.rstrip(".").strip('"').strip()
            if not ruta or ruta.lower().startswith("confirmados en vivo") or ruta.lower().startswith("confirmada en vivo"):
                continue  # linea sin ruta real (ej. "confirmados en vivo el 10/09/2026.")
            hallazgos.append((archivo.name, ruta))
            break  # 1 sola ruta por modulo (la primera que aparece)
    return hallazgos


def pantallas_del_excel(filas):
    return {normalizar(niveles[-1]) for niveles, _, _ in filas}


def main():
    filas = leer_excel()
    arbol = construir_arbol(filas)
    lineas_arbol = renderizar(arbol)

    conocidas = pantallas_del_excel(filas)
    sin_fila = []
    for archivo, ruta in extraer_rutas_de_modulos():
        ultimo_segmento = ruta.split(">")[-1].strip()
        if normalizar(ultimo_segmento) not in conocidas:
            sin_fila.append((archivo, ruta))

    salida = ["# Mapa de navegacion Web LDS", "",
              f"Generado desde `{EXCEL.name}` ({len(filas)} filas). "
              "Escanear antes de un proyecto nuevo para ver si una pantalla ya se mapeo.",
              ""]
    salida.extend(lineas_arbol)

    if sin_fila:
        salida += ["", "---", "",
                   "## Posibles pantallas sin fila en el Excel (best-effort, revisar a mano)",
                   "",
                   "Encontradas en `_framework/modulos/*.py` pero su nombre de pantalla no "
                   "aparece en ninguna fila del Excel - puede ser una variacion de redaccion, "
                   "no necesariamente una omision real:", ""]
        for archivo, ruta in sin_fila:
            salida.append(f"- `{archivo}` → {ruta}")

    SALIDA.write_text("\n".join(salida) + "\n", encoding="utf-8")
    print(f"Mapa generado: {SALIDA} ({len(lineas_arbol)} lineas, {len(sin_fila)} posibles omisiones)")


if __name__ == "__main__":
    main()
