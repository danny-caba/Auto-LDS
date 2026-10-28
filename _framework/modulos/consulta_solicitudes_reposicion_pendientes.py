"""
Modulo: Consulta de Solicitudes de Reposicion Pendientes (Web LDS)
Componente Angular: app-reposicion-pendiente
Ruta de menu confirmada en vivo: Comercial > Consulta De Solicitudes De Reposicion Pendientes
Sistema/frente de negocio: Cortes y Reposicion (CONREPEN)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
============================================================================

**El "combo roto" documentado el 28/09/2026 NO se reproduce un mes
despues** - ambos combos (`nz-select`) cargan con datos reales:
"Sucursal Cliente" (12 opciones: "(Todas)" + 11 sucursales reales) y
"Fecha de Solicitud" (3 opciones: "(Sin filtro)" / "=" / "Entre").
Mismo patron de "problema transitorio, no permanente" ya confirmado en
RF-02/03/05 de este mismo proyecto.

**Selectores reales**: `nz-select` x2 (Sucursal Cliente, Fecha de
Solicitud - orden de apertura en el DOM), inputs para N.° de Cliente y
Sector, botones por texto exacto Leer/Limpiar/"a Excel"/Anular (Anular
deshabilitado salvo con 1 solicitud pendiente/generada seleccionada).
Grilla de resultados con 22 columnas reales.

**Validacion real confirmada**: presionar Leer con TODOS los filtros en
su estado por defecto (sin ningun filtro puesto) -> modal "Ventana de
Validación": *"Debe Seleccionar algún filtro para la consulta"*.
============================================================================
"""

import re


def abrir_reposicion_pendientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Solicitudes De Reposicion Pendientes"], "app-reposicion-pendiente", paso_excel=paso_excel)


def leer_reposicion_pendientes(app, frame):
    """Pulsa Leer y devuelve el texto del modal de Ventana de
    Validacion si aparece (cerrandolo), o None si la consulta corrio
    directo."""
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        texto = modal.first.inner_text()
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return texto
    return None
