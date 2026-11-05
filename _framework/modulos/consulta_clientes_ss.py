"""
Modulo: Consulta de Clientes Asociados a una S.S. (Web LDS)
Componente Angular: app-conscliesol
Ruta de menu confirmada en vivo: Comercial > Consulta De Clientes Asociados A Una S.S.
Sistema/frente de negocio: Gestion de Clientes (acticome/conscliesol)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 27/09/2026)
============================================================================

Pantalla ng-zorro/Ant Design moderna (misma familia que otras pantallas
Web LDS, pero con tabla nz-table estandar - SIN el custom `table.g` visto
en otros modulos). Campos: `input#numeroSS` (solo digitos, maxlength 10),
`input#correlativo` (maxlength 2, sin restriccion de formato). Botones
"Leer" (siempre habilitado) e "Imprimir" (deshabilitado hasta ejecutar
Leer una vez, luego SIEMPRE habilitado incluso con 0 resultados).

Resultado de "Leer": grilla `nz-table` (filtrar la fila fantasma
`ant-table-measure-now`, mismo gotcha de siempre en nz-table) + una
linea de texto justo debajo con el total: "Clientes asociados a la SS.
<numero>:\\n<total>" (sin correlativo) o "Clientes asociados a la SS.
<numero> (<correlativo>):\\n<total>" (con correlativo).

**Los mensajes de validacion/error usan una "Ventana de Validacion"
modal** (`.ant-modal`/`nz-modal-container`, icono "i", boton unico
"Aceptar") - NO son toasts ni banners inline. Confirmados en vivo:
- "Ingrese N.° de S.S." (Leer sin S.S.)
- "N.° de SS y Correlativo no encontrados." (con Correlativo, sin resultados)
- "N.° de SS no encontrada." (sin Correlativo, sin resultados - documentado
  en el EF, mismo patron simetrico que el mensaje con correlativo)
- "No se generó informe." (fallo de generacion de Imprimir)

**El campo N.° de S.S. SI descarta letras/simbolos al teclear** (confirmado
en vivo: `type("ab12$%3")` deja solo `"123"` en el campo) - RN-08 SI es
reproducible tal cual, a diferencia de otros "campos defensivos" de otros
proyectos que resultaron ser mas permisivos que lo documentado.

**RN-07 (modificar N.° de S.S. limpia grilla y Correlativo) SI es
reproducible tal cual el EF** - confirmado en vivo dos veces. La primera
verificacion dio un falso negativo (la grilla parecia no limpiarse) por
escribir el digito nuevo via `page.keyboard.type(...)` en vez de
`locator.press_sequentially(...)` sobre el campo correcto - con la
correccion, la grilla SI se limpia de inmediato al modificar el campo.
Ojo con este gotcha de automatizacion (no de la app real): escribir en
un input DENTRO de un iframe de un popup requiere teclear sobre el
`Locator` del campo (o su `Page`/`Frame` correspondiente), nunca sobre
el `page` del portal original - un `page.keyboard.type(...)` fuera de
lugar no lanza error, simplemente no le llega a nadie, dando la falsa
impresion de que la app no reacciono a un cambio que en realidad nunca
se escribio.

**CORRECCION 02/11/2026 - "Imprimir" (generacion de informe) NO esta
permanentemente caido, es simplemente MUY LENTO.** El hallazgo original
(27/09/2026, "SIEMPRE falla con 'No se generó informe.'", 3/3 veces) era
un falso negativo de automatizacion: las 3 verificaciones esperaron solo
unos pocos segundos tras confirmar "¿Desea generar archivos?". Con S.S.
1234567 (2 clientes reales) y esperando hasta 240s, el informe SI se
genera y se descarga ("ODESS_Informe_1234567.txt" real confirmado en
vivo) - mismo patron de backend lento ya visto en RF-03 CP024 (hasta
~220s). El dialogo de confirmacion previo ("¿Desea generar archivos?",
botones Cancelar/Aceptar) funciona normalmente. Cualquier automatizacion
futura de esta pantalla debe esperar en bucle (no un timeout corto fijo)
tras confirmar Imprimir.
============================================================================
"""

import re
from playwright.sync_api import TimeoutError as PWTimeoutError


def abrir_consulta_clientes_ss(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Clientes Asociados A Una S.S."], "app-conscliesol", paso_excel=paso_excel)


def cerrar_ventana_validacion(app, frame, timeout_ms=4000):
    """Cierra la "Ventana de Validacion" (.ant-modal/nz-modal-container,
    icono "i", boton unico "Aceptar") si aparece, y devuelve su texto.
    Tolerante: devuelve None si no aparece ninguna."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    try:
        dialogo.first.wait_for(state="visible", timeout=timeout_ms)
    except PWTimeoutError:
        return None
    texto = dialogo.first.inner_text()
    dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).first.click()
    app.wait_for_timeout(500)
    return texto


def leer_clientes_ss(app, frame, numero_ss=None, correlativo=None):
    """Completa N.° de S.S. y/o Correlativo (si se pasan) y pulsa Leer.
    Pasar None en cualquiera de los 2 para no tocar ese campo (dejarlo
    con lo que ya tenia)."""
    if numero_ss is not None:
        frame.locator("#numeroSS").fill(numero_ss)
        app.wait_for_timeout(300)
    if correlativo is not None:
        frame.locator("#correlativo").fill(correlativo)
        app.wait_for_timeout(300)
    frame.get_by_role("button", name=re.compile("Leer")).click()
    app.wait_for_timeout(1500)


def filas_clientes_ss(frame):
    """nz-table trae 2 filas que NO son datos reales y hay que excluir
    siempre: la fila fantasma de medicion interna
    (`tr.ant-table-measure-now`, gotcha ya visto en otros modulos) Y la
    fila placeholder "No hay datos" (`tr.ant-table-placeholder`, con un
    componente nz-empty adentro) que esta pantalla muestra cuando la
    grilla esta vacia - confirmado en vivo que un conteo ingenuo
    (solo excluyendo measure-now) da 1 fila incluso sin resultados."""
    return frame.locator("nz-table tbody tr:not(.ant-table-measure-now):not(.ant-table-placeholder)")


def confirmar_imprimir(app, frame):
    """Pulsa Imprimir y confirma el dialogo ("¿Desea generar archivos?").
    Devuelve el texto final de la pantalla tras la confirmacion (puede
    ser el mensaje de exito+descarga, o la Ventana de Validacion de
    fallo "No se generó informe." - ver ficha tecnica del modulo)."""
    frame.get_by_role("button", name=re.compile("Imprimir")).click()
    app.wait_for_timeout(800)
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r".", re.S))
    dialogo.first.wait_for(state="visible", timeout=4000)
    dialogo.first.get_by_role("button", name=re.compile("^S[ií]$|^Aceptar$", re.I)).first.click()
    app.wait_for_timeout(1200)
