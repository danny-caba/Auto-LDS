"""
Modulo: Cambio de Sucursal de Clientes (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Cambio De Sucursal De Clientes
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.Camsuc)

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "Leer"
- Solo lectura tras Leer: #direccion, #tarifa, #sucursalActual,
  #sectorActual, #zonaActual, #correlativoActual
- Un <select> de Sucursal Nueva SIN id propio en el dump (apareció como
  input disabled sin id entre #correlativoActual y #sectorNuevo - hace
  falta re-explorar con foco en ese combo especifico antes de escribir
  el cuerpo real del caso)
- #sectorNuevo, #zonaNuevo, #correlativoNuevo (nacen DISABLED hasta Leer
  exitoso)
- boton "Cerrar"
- boton "Actualizar" (nace DISABLED)

A diferencia de RF-03 (Asignacion de Rutas), esta pantalla NO tiene
"Descargar PDF" - el ET aclara que la opcion de emision del formulario
original (CAMSUC.FRM) nunca tuvo implementacion real (mostraba
"Impresion terminada" sin generar nada), por eso no se migra.

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un N.° de Cliente real para validar en vivo)
============================================================================
- Identificar el selector real del combo "Sucursal Nueva" (no capturado
  en el primer dump - posible nz-select/select sin id, re-inspeccionar).
- Mensaje real de "Cliente no existe.".
- Si la cuenta DCABA_DW tiene la sucursal de sesion distinta a la del
  cliente de prueba (RN: "SoloConsulta" - la pantalla permitiria solo
  consulta, no modificacion, en ese caso).
- Rol MODS33 si se prueba un cambio a sector 33.
============================================================================
"""

import re


def abrir_cambio_sucursal(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Cambio De Sucursal De Clientes"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_sucursal(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
