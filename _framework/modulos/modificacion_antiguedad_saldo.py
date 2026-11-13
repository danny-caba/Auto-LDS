"""
Modulo: Modificacion de Antiguedad de Saldo (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Modificacion De Antiguedad
  De Saldo
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.Antsald)

Acceso inicialmente bloqueado para DCABA_DW y SCASTI_DW (falta el rol
MODANTI, ver CONO-0023 en la memoria central) - CONFIRMADO RESUELTO
13/11/2026 tras una correccion de configuracion de roles pedida al
usuario (ver CONO-0025).

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "Leer"
- #nombre, #direccion (solo lectura tras Leer)
- #antiguedadSaldo (nace DISABLED - se habilita con "Modificar", es el
  unico dato editable de esta pantalla)
- boton "Cerrar"
- boton "Modificar" (nace DISABLED hasta un Leer exitoso; segun el EF
  tiene doble uso: 1er click habilita edicion de #antiguedadSaldo, 2do
  click confirma el cambio)

Es la pantalla con MENOS campos de las 9 del sprint (solo 1 dato
editable).

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un N.° de Cliente real para validar en vivo)
============================================================================
- Confirmar el doble-uso real del boton Modificar (1er click = habilita
  edicion, 2do click = confirma, segun EF RN-6/RN-9).
- Mensajes reales: "Cliente no existe." (RN-3), "Cliente en
  facturacion...No se puede modificar la antiguedad de deuda" (RN-4,
  sic del sistema original, sin espacio tras el punto), "Cliente no
  pertenece a Luz del Sur...No se puede modificar la antiguedad de
  deuda" (RN-5, mismo patron sic), "No hubieron modificaciones" (RN-7,
  valor sin cambio).
- Confirmacion explicita "Esta seguro de las modificaciones?" (RN-9).
- Bloqueo del campo N.° de Cliente tras Leer exitoso (RN-15).

INSUMO (NO verificado en vivo, tratar solo como hipotesis a confirmar):
el manual de usuario descargado desde el boton "Manual" de esta misma
pantalla (Documentos/Manual_RF-01_AntiguedadSaldo.pdf) da versiones de
estos mismos mensajes SIN los "sic" del sistema original que preserva
el EF (ej. "Cliente en facturación. No se puede modificar la antigüedad
de deuda." - CON espacio tras el punto, a diferencia del "sic" del EF).
Los 9 manuales del sprint comparten estructura/parrafo de cierre
identicos palabra por palabra, lo que sugiere que son generados por una
plantilla a partir del EF (no transcritos del sistema real) - no asumir
que su texto es mas preciso que el EF sin confirmarlo en vivo.
============================================================================
"""

import re


def abrir_antiguedad_saldo(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Modificacion De Antiguedad De Saldo"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_antiguedad_saldo(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
