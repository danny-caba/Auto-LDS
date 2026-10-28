"""
Modulo: Consulta de Cortes y Reconexiones (Web LDS)
Componente Angular: app-cortes-reconexiones
Ruta de menu confirmada en vivo: Comercial > Consulta De Cortes Y Reconexiones
Sistema/frente de negocio: Gestion de Cortes (CONCRCLI)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
============================================================================

**Backend confirmado operativo** - en una corrida anterior (28/09/2026)
esta pantalla daba 504 y quedo documentada como "backend caido"; un mes
despues, misma cuenta (DCABA_DW), carga y responde perfecto. Mismo
patron ya confirmado en RF-02 y RF-05 de este mismo proyecto.

**Selectores reales**: 2 radios de Tipo de Corte (el primero,
"Inconsistencias Corte Fresco", viene MARCADO por defecto - confirma
CP017; el segundo es "Verificaciones"), `#fldNumeroCliente`,
`#fldProcesos` (select, "(Sin selección)" + 3 motivos reales),
`#fldSucursal` (10 sucursales reales + "Sin Sucursal"), `#fldSector`,
`#fldZona`, `#fldProveedor`, `#fldTipoFiltroFecha` (select: `=`, `<=`,
`>=`, `entre` - **"entre" es el valor por defecto**, por lo que hacen
falta AMBOS campos de fecha). Los campos de fecha reales son
`input[type=date]` NATIVOS (hay 2: inicial y final) - no tienen el
defecto de freeze de RF-07/09 (nz-date-picker). Botones Leer / "Guardar
como..." (deshabilitado hasta Leer) / Limpiar.

**Confirmacion real confirmada (RN de "sin filtro")**: con ambas fechas
puestas (operador "entre" por defecto) pero SIN ningun otro filtro
(Procesos, Sucursal, etc.), aparece el modal "Confirmación": *"No ha
seleccionado ningún filtro, se mostrarán todos los datos entre las
fechas seleccionadas. ¿Desea continuar?"* - mismo patron ya visto en
RF-04 y RF-05 de este proyecto.

**Validacion real confirmada**: con el operador "entre" por defecto y
solo UNA fecha llena (falta la otra), modal "Ventana de Validación":
*"Debe ingresar los dos valores del rango."*
============================================================================
"""

import re


def abrir_cortes_reconexiones(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Cortes Y Reconexiones"], "app-cortes-reconexiones", paso_excel=paso_excel)


def leer_cortes_reconexiones(app, frame, aceptar_confirmacion=True):
    """Pulsa Leer y maneja el dialogo que aparezca. Devuelve una tupla
    (tipo, texto): tipo es 'validacion', 'confirmacion' o None (sin
    dialogo, consulta corrio directo)."""
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if not (modal.count() and modal.first.is_visible()):
        return None, None
    texto = modal.first.inner_text()
    if "confirmaci" in texto.lower() and aceptar_confirmacion:
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(3000)
        return "confirmacion", texto
    if "validaci" in texto.lower():
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return "validacion", texto
    return "confirmacion", texto
