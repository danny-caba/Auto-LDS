"""
Modulo: Modificacion de Direccion de Reparto (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Modificacion De Direccion
  De Reparto (OJO: el EF la llama "Modificacion de Direcciones" pero el
  nombre real en el menu es "Modificacion De Direccion De Reparto")
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.DirPostal)

Es la pantalla con MAS campos de direccion estructurada de las 7
mapeadas (via/puerta/manzana/lote/interior/block/grupo/sector/
urbanizacion, todos por separado).

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "Leer"
- #fechaModificacion (EDITABLE desde el inicio, no se desactiva - raro,
  confirmar si es un filtro o un dato que se escribe)
- Solo lectura tras Leer: #nombre (aria "Nombre / Razón Social"),
  #direccionSuministro, #distritoSuministro
- #direccionPostal, #ciudadPostal (EDITABLES desde el inicio)
- un checkbox sin id (probablemente "Tiene dirección postal de Reparto"
  del EF - activa/desactiva los "Cambios Restringidos")
- Direccion estructurada (todos EDITABLES, nacen DISABLED hasta Leer):
  #nombreVia, #puerta, #manzana, #lote, #interiorNro, #blockNro,
  #grupoNro, #sectorNro, #urbanizacion (+ varios inputs SIN id
  intercalados entre estos - probablemente los selects de Tipo de Via/
  Tipo de Urbanizacion que menciona el EF, re-explorar con mas detalle)
- boton "Limpiar" (nace DISABLED)
- #referenciaReparto, #referenciaLectura (EDITABLES, nacen DISABLED)
- boton "Descargar PDF"
- boton "Cerrar"
- boton "Modificar" (nace DISABLED)

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un cliente real para validar en vivo)
============================================================================
- Identificar los selectores de los inputs sin id (varios, probablemente
  <select> de Tipo de Via y Tipo de Urbanizacion segun el EF - precondicion
  explicita: "Existen catalogos de Tipos de Via, Tipos de Urbanizacion y
  Distritos disponibles").
- Por que #fechaModificacion aparece editable desde el inicio (sin Leer
  previo) - confirmar si es realmente un campo de la cabecera o un
  filtro de otra naturaleza.
- La regla de "Cambios Restringidos" (el checkbox sin id) y que exactamente
  bloquea.
- Mensajes reales de Leer vacio/cliente inexistente.
============================================================================
"""

import re


def abrir_modificacion_direccion(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Modificacion De Direccion De Reparto"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_direccion(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
