"""
Modulo: Consulta de Pagos (Web LDS)
Componente Angular: app-consulta-pago
Ruta de menu confirmada en vivo: Comercial > Consulta De Pagos
Sistema/frente de negocio: Recaudacion (CONSPAG)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
============================================================================

**Backend confirmado operativo** - en una corrida anterior (28/09/2026)
esta pantalla daba 503 y quedo documentada como "backend caido"; un mes
despues, misma cuenta (DCABA_DW), carga y responde perfecto. Mismo
patron ya confirmado en RF-02 (Mantenimiento de Ordenes de Conexion) de
este mismo proyecto - antes de asumir un defecto de infraestructura
permanente, reintentar en una sesion nueva.

**GOTCHA REAL CONFIRMADO: `get_by_role("button", name=re.compile(...))`
CRASHEA el navegador en esta pantalla (2/2 veces reproducido,
"Target crashed").** Usar SIEMPRE `frame.locator("button",
has_text=re.compile(...))` para los botones de esta pantalla, nunca
get_by_role con regex - no se investigo la causa exacta (posible
problema de calculo de accessible-name sobre el arbol de esta pantalla
en particular), pero el selector alternativo funciona sin problema.

**Selectores reales**: `#txtFechaInicial` (`<input type="date">`
NATIVO, no nz-date-picker - no tiene el defecto de freeze de RF-07/09),
`#txtMontoInicial`, `#txtNumeroCliente`, `#txtDoctoInicial`. Combo
"Referencia" con **"Actualización de Saldo" como opcion por defecto**
(coincide con CP031 "tipo por defecto"). Botones por texto exacto:
Leer (pasa a decir "Siguiente" tras el primer Leer exitoso, paginacion
de a 25 - mismo patron que otras pantallas de este proyecto),
"Calcular total" y "Guardar como..." (deshabilitados hasta Leer),
Limpiar.

**Confirmacion real confirmada (RN de "sin filtro")**: al presionar
Leer con los filtros en su estado por defecto (solo fecha, sin otro
filtro puesto), aparece el modal "Confirmación" ("?"): *"No ha
seleccionado ningún filtro, se mostrarán todos los pagos entre las
fechas seleccionadas. ¿Desea continuar?"* - mismo patron ya visto en
RF-04 (Cuadratura de Sesion) de este mismo proyecto.

**Resultado vacio real confirmado**: "No se encontraron pagos con los
filtros vigentes." + "Registros mostrados: 0 — se cargan bloques
adicionales de 25 al continuar leyendo" - con fecha desde 01/01/2026
sin mas filtro, 0 resultados (los datos reales de Pruebas pueden ser
historicos, igual que en RF-04, donde los datos reales eran de 2005).

**Dato real confirmado 28/10/2026 que destraba la busqueda**:
02/05/2002 (operador "=") tiene pagos reales tanto en "Actualización de
Saldo" como en "Otros Conceptos" (concepto EMI). Fecha "Desde" nace con
el dia de HOY precargado (a diferencia de otras pantallas del proyecto,
que nacen vacias) - por eso buscar sin tocar la fecha da 0 resultados
reales, no es que la pantalla este rota.

**Combos reales son `nz-select` (ant-design), NO `<select>` nativos**:
`cboReferencia` (5 opciones: Actualización de Saldo / Otros Conceptos /
No Ubicados / Encargos de Cobranza / Cobranza Externa), `cboFechaOperador`
(`=`/`<=`/`>=`/`entre`, "=" por defecto), `cboLote`, `cboOficinaCod`,
`cboOficinaNom`, `cboCajero`, `cboConcepto` (recarga segun Referencia:
con "Otros Conceptos" trae 6 codigos reales - AUS/CHD/CVW/EMI/ENQ/MGT),
`cboMontoOperador`, `cboSector`, `cboEstado`, `cboTipoDocumento`,
`cboLibro`, `cboDoctoOperador`, `cboOrigen` (estos ultimos 4
deshabilitados salvo con Referencia "Otros Conceptos" - confirma CP032).
Usar `elegir_nz_select()` (abajo) para elegir una opcion, nunca
`select_option()`.

**DEFECTO REAL confirmado en vivo 28/10/2026 (CP034)**: con Referencia
"No Ubicados", el backend `BuscarPagos` responde **500** siempre
(probado con operador "=" + fecha de hoy, y con "entre" + rango de 59
dias - ambos fallan igual) - la app muestra "Error de Servicio: Error
en consulta.". No se pudo validar la regla de "sin limite de dias" de
este origen porque la consulta nunca llega a ejecutarse con exito.

**`Limpiar` NO resetea el combo `cboFechaOperador`** a "=" - si una
corrida previa (en la misma sesion de navegador) dejo el operador en
otro valor, Limpiar lo deja como estaba. No afecta a los CPxxx.py
reales (cada uno abre una sesion nueva), pero es relevante si se
encadenan varias pruebas manuales en una sola sesion de exploracion.
============================================================================
"""

import re


def abrir_consulta_pagos(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Pagos"], "app-consulta-pago", paso_excel=paso_excel)


def elegir_nz_select(frame, app, select_id, texto_opcion):
    """Elige una opcion por su texto visible en un combo `nz-select`
    (ant-design) - estos combos NO son un <select> nativo, por lo que
    select_option() no sirve: hay que abrir el combo (click) y clickear
    la opcion dentro del overlay que ng-zorro agrega al DOM del propio
    frame (no al documento de nivel superior)."""
    frame.locator(f"nz-select#{select_id}").click()
    app.wait_for_timeout(400)
    opcion = frame.locator("nz-option-item, .ant-select-item-option").filter(
        has_text=re.compile(r"^\s*" + re.escape(texto_opcion) + r"\s*$")
    )
    opcion.first.click()
    app.wait_for_timeout(300)


def leer_pagos(app, frame):
    """Pulsa Leer (o Siguiente, tras el primer Leer exitoso) y cierra el
    dialogo de confirmacion ("sin filtro") si aparece, aceptandolo.
    Devuelve el texto del dialogo de VALIDACION si aparece uno
    (distinto del de confirmacion), o None si la consulta corrio
    directo."""
    frame.locator("button", has_text=re.compile(r"^\s*(Leer|Siguiente)\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        texto = modal.first.inner_text()
        if "confirmaci" in texto.lower():
            modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
            app.wait_for_timeout(3000)
            return None
        return texto
    return None
