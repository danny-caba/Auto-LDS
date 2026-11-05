"""
Modulo: Consulta de Cortes Pendientes (Web LDS)
Componente Angular: app-cortes-pendientes
Ruta de menu confirmada en vivo: Comercial > Consulta De Cortes Pendientes
Sistema/frente de negocio: Cortes y Reconexiones (corterepos/cortependi)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
============================================================================

Pantalla ng-zorro/Ant Design. Filtros: Cliente (`#fld-cliente`), Sector
(`#fld-sector`), Zona (`#fld-zona`), Sucursal (`nz-select#fld-sucursal`),
Rol (`#fld-rol`), Contratista (`nz-select#fld-contratista`), tipo de
F. Corte (`nz-select#fld-tipo-fecha`: =, >=, Entre) + Fecha inicial/final
(inputs con `aria-label="Fecha inicial"`/`"Fecha final"`, el segundo solo
aparece con tipo "Entre"), Origen/Estado Libro/Estado Detalle (selects).
Botones Leer / "a Excel" (deshabilitado hasta tener resultado) / Limpiar.

**Sucursales reales disponibles** (confirmado en vivo): Cañete,
Chacarilla, Chorrillos, Chosica, La República, Miraflores, Pedro Miotta,
San Bartolo, San Juan, Santa Anita, Sin Sucursal. Filtrar por
CUALQUIERA de ellas ya devuelve resultados reales combinados (cortes de
libro + solicitudes especiales) - no hace falta un cliente puntual.

**gotcha de timing importante: la busqueda real (Leer con filtros
validos) tarda ENTRE 10 Y 15 SEGUNDOS** en responder (confirmado en vivo,
endpoint `BuscarCortesPendientes`) - mucho mas que cualquier otra
pantalla de este proyecto. Un `wait_for_timeout` corto (1-2s, el patron
usual de otras pantallas) deja el boton "Leer"/"Limpiar" todavia
deshabilitados y hace fallar cualquier assert posterior con un timeout
confuso. Usar SIEMPRE `leer_cortes_pendientes()` (sondeo hasta que
termine, no una espera fija).

**Mensajes reales confirmados** (via "Ventana de Validacion" modal,
`.ant-modal`/`nz-modal-container`, icono "i", boton "Aceptar"):
- "Debe Seleccionar algún filtro para la consulta" (RN-14, sin ningun filtro)
- "Fecha Inválida" (RN-08, fecha con valor calendario inexistente)
- "Debe Seleccionar Rango Inferior de Fecha" (RN-10, tipo de fecha elegido sin fecha inicial)

**Gotcha real de nz-table (mismo patron que otros modulos de este
proyecto): la fila placeholder "No hay datos" (`tr.ant-table-placeholder`)
cuenta como `<tr>` igual que la fila fantasma `ant-table-measure-now` -
excluir AMBAS siempre al contar filas reales.

**CORRECCION 02/11/2026 - el freeze del date-picker YA NO SE REPRODUCE.**
El defecto original (28/09/2026: ingresar una fecha calendario VALIDA
en el filtro F. Corte congelaba la pantalla 30s+, reproducido 5 veces
con metodos de interaccion distintos) no se reproduce mas de un mes
despues - escribir la fecha con `press_sequentially`, hacer `screenshot()`
y leer `input_value()` terminan en <2s (ver
_exploracion/explore_88_rf07_revalidar_freeze.py). Mismo patron de
recuperacion ya visto en otras pantallas de PR000349-SP2 (servicio de
informes de RF-01, backend de RF-02/03/05, servicio de ficha de RF-06).
CP052/CP053 confirmados en vivo con los mensajes EXACTOS del EF
("Debe Seleccionar Rango Superior de Fecha" / "Error, Rango de Fechas
Debe Ser Como Máximo 60 Días"). Los campos de fecha se ubican con
`frame.get_by_label("Fecha inicial")` / `"Fecha final"`.
============================================================================
"""

import re
import time
from playwright.sync_api import TimeoutError as PWTimeoutError


def abrir_consulta_cortes_pendientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Cortes Pendientes"], "app-cortes-pendientes", paso_excel=paso_excel)


def elegir_select_cortes(app, frame, select_id, texto_opcion):
    frame.locator(f"#{select_id}").click()
    app.wait_for_timeout(500)
    frame.locator(".ant-select-item-option").filter(has_text=texto_opcion).first.click()
    app.wait_for_timeout(400)


def filas_cortes_pendientes(frame):
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now):not(.ant-table-placeholder)")


def leer_cortes_pendientes(app, frame, timeout_ms=45000):
    """Pulsa Leer y espera a que termine: si aparece un dialogo de
    validacion, lo cierra y devuelve su texto; si la busqueda real
    termina (boton Limpiar se rehabilita), devuelve None. La busqueda
    real de esta pantalla puede tardar 10-15s - ver ficha tecnica."""
    boton_leer = frame.get_by_role("button", name=re.compile("Leer"))
    boton_limpiar = frame.get_by_role("button", name=re.compile("Limpiar"))
    boton_leer.click()
    plazo = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < plazo:
        dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("."))
        if dialogo.count() > 0 and dialogo.first.is_visible():
            texto = dialogo.first.inner_text()
            dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
            app.wait_for_timeout(500)
            return texto
        if boton_limpiar.get_attribute("disabled") is None:
            return None
        app.wait_for_timeout(400)
    raise PWTimeoutError(f"leer_cortes_pendientes: no termino en {timeout_ms}ms")


def limpiar_cortes_pendientes(app, frame):
    frame.get_by_role("button", name=re.compile("Limpiar")).click()
    app.wait_for_timeout(600)
