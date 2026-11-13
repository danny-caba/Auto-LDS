"""
Modulo: Mantenimiento de Empleados con Descuento (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Mantenimiento De Empleados
  Con Descuento
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.Empleado - unico RF de
  este sprint que orquesta Plataforma.Sqlgui para busqueda)

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "?" (aria-label "Buscar cliente") - abre un modal propio, titulo
  real confirmado: "Búsqueda de Clientes Registrados como Empleados"
  (SOLO busca entre clientes YA registrados como empleado con
  descuento, NO es un buscador generico de cualquier cliente - util
  para RF-07 puntual, no sirve como fuente de un cliente cualquiera
  para las otras 6 pantallas de este sprint).
- boton "Leer"
- Solo lectura tras Leer: #nombre, #direccion, #distrito, #tarifa
- #descuentoPlanilla (checkbox, nace DISABLED), #planilla, #codigo
  (nacen DISABLED - datos de la condicion de Empleado con Descuento)
- boton "Descargar PDF"
- boton "Cerrar"
- boton "Eliminar" (nace DISABLED)
- boton "Ingresar" (nace DISABLED)

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE
============================================================================
- El boton "?" resulto INTERMITENTE en la exploracion (2 de 3 intentos
  no lo encontraron visible pese a haber funcionado la primera vez,
  mismo locator `get_by_role("button", name="?")`, aria-label "Buscar
  cliente" confirmado en el primer dump) - investigar con mas tiempo
  antes de depender de el en generate_scripts.py: puede ser un timing
  de carga del boton, o requerir un estado previo de la pantalla.
- No se llego a ver el contenido de la grilla del modal de busqueda (la
  unica apertura exitosa no incluyo buscar con el formulario vacio).
- Falta un Suministro valido real para probar Ingresar (precondicion
  del EF: "el Cliente cuenta con un Suministro valido").
- Mensajes reales de Leer vacio/cliente inexistente.
============================================================================
"""

import re


def abrir_mantenimiento_empleados(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Empleados Con Descuento"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_empleado(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
