"""
Modulo: Reincorporacion de Clientes Retirados (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Reincorporacion De
  Clientes Retirados (OJO: el EF la llama "Asignacion de Clientes
  Reincorporados" pero el nombre real del menu es "Reincorporacion De
  Clientes Retirados")
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.CliRein)

Acceso inicialmente bloqueado para DCABA_DW y SCASTI_DW (falta el rol
LUZRETIC, ver CONO-0023) - CONFIRMADO RESUELTO 13/11/2026 tras una
correccion de configuracion de roles pedida al usuario (ver CONO-0025).

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM) - es la unica de las 9
pantallas del sprint con DOS clientes en pantalla a la vez (el
reincorporado que se consulta y el retirado que se asocia/desasocia):
- #numeroCliente (N.° de Cliente - el cliente REINCORPORADO/actual)
- boton "Leer"
- #nombre, #direccion (del cliente reincorporado, solo lectura)
- #numeroClienteRetirado (nace DISABLED - dato del Cliente Retirado a
  asociar)
- #nombreRetirado, #direccionRetirado (EDITABLES desde el inicio, no se
  desactivan - revisar si son realmente de entrada o deberian ser solo
  lectura tras buscar el retirado)
- #saldoActual (EDITABLE desde el inicio - raro para un dato que
  debería ser de solo lectura, re-explorar)
- boton "Cerrar"
- boton "Desasociar" (nace DISABLED)
- boton "Modificar" (nace DISABLED)

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un cliente reincorporado real con un posible retirado
asociable - precondicion explicita del EF: "existe un registro de
posible reincorporacion asociado al Cliente antes de poder ejecutar la
asociacion")
============================================================================
- Como se busca/selecciona el Cliente Retirado a asociar (no hay boton
  de busqueda visible en el dump - quiza se escribe #numeroClienteRetirado
  a mano pese a nacer disabled, o aparece tras Leer con datos reales).
- Por que #nombreRetirado/#direccionRetirado/#saldoActual nacen
  editables en vez de solo lectura - confirmar en vivo si es un bug de
  la pantalla o el comportamiento esperado.
- Flujo de Asociar vs Desasociar (el EF solo menciona "asociar" la
  reincorporacion con su historico - el boton real que vi es
  "Modificar", no "Asociar").
- Mensajes reales de Leer vacio/cliente inexistente/sin reincorporacion
  pendiente.

INSUMO (NO verificado en vivo, tratar solo como hipotesis a confirmar):
el manual descargado (Documentos/Manual_RF-05_ReincorporacionClientesRetirados.pdf)
describe el flujo como: Leer el cliente activo trae automaticamente el
retirado YA asociado si existe; #numeroClienteRetirado se usa para
ASOCIAR uno nuevo (consistente con nacer disabled hasta leer el activo
primero); "Modificar" = asociar (pide confirmacion), "Desasociar" =
deshacer. Mismo aviso que en modificacion_antiguedad_saldo.py: los 9
manuales del sprint comparten plantilla/cierre identicos, tratar como
hipotesis, no como fuente verificada.
============================================================================
"""

import re


def abrir_reincorporacion_clientes(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Reincorporacion De Clientes Retirados"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_reincorporacion(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
