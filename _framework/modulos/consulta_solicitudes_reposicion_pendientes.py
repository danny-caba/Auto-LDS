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

**Campos de fecha reales (confirmado en vivo 29/10/2026): NI nativos
NI `nz-date-picker`** - son `<input type="text">` simples con
placeholder "dd/mm/aaaa" (`#fldFechaInicio`/`#fldFechaFin`, aparecen
recien al elegir "=" o "Entre" en el combo `fldTipoFecha`). Al ser
texto plano, SI se puede escribir una fecha de calendario inexistente
(ej. "31/02/2026") y el campo la acepta tal cual (a diferencia de los
`input[type=date]` nativos de RF-03/04/05, que la bloquean antes de
que llegue al formulario) - la app valida la fecha del lado del
backend y responde con el mensaje real de negocio.

**Mensajes reales confirmados (29/10/2026)**:
- Fecha de calendario inexistente -> *"Fecha Inválida"*.
- Tipo de filtro elegido ("=" o "Entre") con Fecha inicial vacia ->
  *"Debe Seleccionar Rango Inferior de Fecha"*.
- "Entre" con Fecha inicial puesta pero Fecha final vacia ->
  *"Debe Seleccionar Rango Superior de Fecha"*.
- "Entre" con un rango mayor a 31 dias -> *"Error, Rango de Fechas Debe
  Ser Como Máximo 31 Días"*.

**Seleccion de fila real**: no hay checkbox/radio por fila - un click
directo en cualquier parte de la fila la selecciona (resaltado celeste)
y habilita el boton "Anular". Dato real confirmado para busqueda con
resultados: Sucursal "1000 - Cañete" (sin mas filtro) trae 37
solicitudes reales, TODAS con `Estado Solicitud = "GENERADO"` (ninguna
"ANULADA" visible, confirma la regla de CP057 de solo mostrar
pendientes) y ordenadas ascendente por `Fecha Solicitud`.

**Flujo de Anular confirmado en vivo**: seleccionar una fila (click) +
Anular -> modal "Confirmación" *"¿Desea continuar?"* -> al aceptar,
modal "Operación Exitosa" *"Solicitud de Reposición Anulada"*. Accion
REAL e IRREVERSIBLE sobre el dato (no hay boton para reactivar) - cada
corrida de un caso de Anular consume una solicitud real distinta.

**Gotcha de grilla**: las filas de datos reales son `tr.ant-table-row`
- un `tr` suelto sin esa clase (o `table tr` a secas) trae de mas
filas vacias/placeholder, igual que el gotcha ya conocido de otras
`nz-table` de este proyecto (confirmar SIEMPRE `.ant-table-row` para
contar/leer filas reales de esta pantalla).
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
