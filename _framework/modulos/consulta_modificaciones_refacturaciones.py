"""
Modulo: Consulta historica de Modificaciones y Refacturaciones (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Consulta De Modificaciones
  Y Refacturaciones
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.Histmodif)

Reutiliza el modal pasivo FOCONSU (ver EF/ET) - esta es la unica
pantalla de este sprint que es de SOLO CONSULTA (no tiene operacion de
escritura propia).

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Pantalla de filtros (es la mas rica en campos de las 7 mapeadas):
- boton "Opciones" y boton "Manual"
- radios "Modificaciones" / "Refacturaciones" (sin id propio, localizar
  por aria-label) - cambia el set de resultados/columnas de la grilla
- #numeroCliente, #tipoOrden, #numeroOrden, #rol, #sector,
  #deudaMeses (filtros)
- #condicionFechaMod (<select>, opciones "Igual"/"Mayor o igual"/"Entre")
- #fechaDesde (siempre editable) y #fechaHasta (nace DISABLED - se
  habilita seguramente solo cuando condicionFechaMod = "Entre", no
  confirmado en vivo todavia)
- #tipoModificacion (<select>, ya trae opciones reales cargadas: "Todos",
  "ANULACION DE PROVISIONA...", "Accion realiz..." truncado en el dump -
  releer completo antes de escribir el cuerpo del caso)
- boton "Leer" (dispara la consulta)
- boton "Sgtes." (nace DISABLED - paginacion "en bloques" que menciona
  el EF para RF-06, se habilita con resultados)
- boton "Cancelar"
- boton "Descargar PDF"

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta al menos un cliente con historico real de
modificaciones/refacturaciones para validar resultados)
============================================================================
- Texto completo de las opciones de #tipoModificacion (el dump las
  truncó).
- Confirmar la condicion real que habilita #fechaHasta.
- Como luce la grilla de resultados (columnas reales) para
  Modificaciones vs Refacturaciones - el radio cambia el contenido pero
  no se llego a Leer con datos reales todavia.
- Comportamiento de "Sgtes." con un set de resultados grande (paginado
  "en bloques" segun el EF).
============================================================================
"""

import re


def abrir_consulta_modificaciones(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Consulta De Modificaciones Y Refacturaciones"], "#numeroCliente", paso_excel=paso_excel)
