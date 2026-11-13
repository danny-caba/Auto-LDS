"""
Modulo: Asignacion de Rutas a Clientes (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Asignación De Rutas A Clientes
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.Camrut)

No confundir con "Traslado De Clientes" (modulos/traslado_clientes.py,
dominio Retiro y Castigo de Clientes - app distinta) ni con "Relacion
Sucursal - Sector - Zona" (modulos/relacion_sucursal_sector_zona.py,
mantenedor de catalogo, no de clientes).

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "Leer"
- Solo lectura tras Leer: #nombre, #direccion, #distrito, #tarifa
- #sectorActual, #zonaActual, #correlativoActual (solo lectura, ruta
  vigente)
- #sectorNuevo, #zonaNueva, #correlativoNuevo (nacen DISABLED hasta Leer
  exitoso - EDITABLES despues, es la "Ruta Nueva" del EF)
- boton "Descargar PDF" (siempre habilitado, no depende de backend segun
  el EF - exportacion local de la pantalla)
- boton "Cerrar"
- boton "Actualizar" (nace DISABLED)

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un N.° de Cliente real para validar en vivo)
============================================================================
- Confirmar si el cliente de prueba es "Antiguo" (tabla cliente, ve
  Sucursal/Saldo/Interes/Tarifa) o "Nuevo"/nucli (ve Distrito/
  Entrecalles/Cooge/Destino Servicio/Caracteristicas Medidor) - la
  pantalla muestra un set de campos distinto segun el tipo (RN-35).
- Mensajes reales: "Cliente no existe.", "Cliente se encuentra en
  proceso de facturacion...", roles MODS20/MODS24/MODS33 (RN-39/RN-40).
- Flujo de Actualizar con ruta destino valida (no asignada a otro
  cliente, misma sucursal).
============================================================================
"""

import re


def abrir_asignacion_rutas(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Asignación De Rutas A Clientes"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_rutas(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
