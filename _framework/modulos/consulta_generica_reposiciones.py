"""
Modulo: Consulta Generica de Solicitudes de Reposicion (Web LDS)
Componente Angular: app-consulta-generica-reposiciones
Ruta de menu confirmada en vivo: Comercial > Consulta Generica De Solicitudes De Reposicion
Sistema/frente de negocio: Reposiciones (recauda/CONSUREP)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
============================================================================

Pantalla ng-zorro/Ant Design. Filtros: N.° de Cliente (`#fldCliente`),
Sector (`#fldSector`), Sucursal Cliente (`nz-select#fldSucursal`), N.°
Solicitud (`#fldSolicitud`), Estado Solicitud (`nz-select#fldEstado`),
tipo de filtro de fecha OBLIGATORIO (`nz-select#fldTipoFecha`: "=",
"Entre") + Fecha Inicial (`#fldFechaIni`, con calendario `nz-date-picker`
asociado) / Fecha Final (solo visible con "Entre"). Botones Leer /
Limpiar / "a Excel" (deshabilitado hasta tener resultado).

**Mensajes reales confirmados** (via "Ventana de Validacion" modal,
`.ant-modal`/`nz-modal-container`, icono "i", boton "Aceptar"):
- "Debe Seleccionar Filtro de Fechas" (RN-07, ningun tipo de fecha elegido)
- "Fecha Inválida" (RN-06, fecha con valor calendario inexistente)
- "Debe Seleccionar Rango Inferior de Fecha" (RN-08, tipo elegido sin fecha inicial)

**CORRECCION 02/11/2026 - el freeze del date-picker YA NO SE REPRODUCE
en esta pantalla tampoco** (mismo patron de recuperacion que
`consulta_cortes_pendientes.py`, ver su ficha tecnica). Confirmado en
vivo: escribir fecha + screenshot + input_value() terminan en <2s;
busqueda completa con solo el filtro de fecha (operador "=", fecha de
hoy) trae resultados reales en pocos segundos (ver
_exploracion/explore_91_rf09_revalidar_freeze.py). CP064/068/069/071
confirmados con los mensajes EXACTOS del EF.

**Dato real confirmado 02/11/2026**: fecha "=" 02/11/2026 (sin otro
filtro) trae 1 solicitud real - suministro 2353914, N. Solicitud
872378, Estado INGRESADO, Sucursal La República. Los datos reales de
Pruebas estan muy concentrados cerca de la fecha del dia - se probaron
9 rangos "Entre" de 31 dias distintos a lo largo de +1 año (dic/2025 a
nov/2026) y la mayoria dio 0 registros.

**CP070 (solicitudes Anuladas) destrabado generando el dato real**: no
se encontro ninguna Anulada preexistente, asi que se anulo una
solicitud pendiente real via RF-08 (cliente 1964154, N. Solicitud
499575, Sucursal Cañete - ver
_exploracion/explore_98_rf08_anular_499575.py). Confirmado que esta
pantalla SI la muestra con Estado Solicitud = ANULADO (a diferencia de
RF-08, que la excluye tras la baja) - ver
_exploracion/explore_100_rf09_entre_mayo2025.py.

**Gotcha de filtro de fecha confirmado en vivo**: filtrar SOLO por
fecha (sin N. de Cliente) no encontraba el registro recien anulado, ni
con operador "=" ni con "Entre" acotado a su Fecha Solicitud real
(19/05/2025) - hizo falta combinar N. de Cliente + el rango de fecha
para que el backend lo devolviera. No se investigo la causa exacta
(posible que el filtro de fecha solo indexe por otra fecha interna
distinta a "Fecha Solicitud").
============================================================================
"""

import re
import time
from playwright.sync_api import TimeoutError as PWTimeoutError


def abrir_consulta_generica_reposiciones(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta Generica De Solicitudes De Reposicion"], "app-consulta-generica-reposiciones", paso_excel=paso_excel)


def elegir_select_reposiciones(app, frame, select_id, texto_opcion=None):
    """Si texto_opcion es None, elige la primera opcion real disponible
    (util para 'tipo de fecha' cuando cualquier valor sirve, ej. '=')."""
    frame.locator(f"#{select_id}").click()
    app.wait_for_timeout(500)
    opciones = frame.locator(".ant-select-item-option")
    if texto_opcion is None:
        opciones.first.click()
    else:
        opciones.filter(has_text=texto_opcion).first.click()
    app.wait_for_timeout(400)


def cerrar_ventana_validacion_reposiciones(app, frame, timeout_ms=4000):
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
    app.wait_for_timeout(500)
    return texto


def leer_reposiciones(app, frame):
    frame.get_by_role("button", name=re.compile("Leer")).click()
    app.wait_for_timeout(1200)
