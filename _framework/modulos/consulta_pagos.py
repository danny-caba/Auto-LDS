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
historicos, igual que en RF-04, donde los datos reales eran de 2005 -
no se confirmo aun que rango de fecha SI trae resultados reales para
esta pantalla).
============================================================================
"""

import re


def abrir_consulta_pagos(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Pagos"], "app-consulta-pago", paso_excel=paso_excel)


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
