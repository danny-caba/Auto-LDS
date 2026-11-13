"""
Modulo: Modificacion de Fecha de Contrato (Web LDS)
Componente Angular: app-root (shell generico, ver nota en PENDIENTE)
Ruta de menu confirmada en vivo: Comercial > Modificacion De Fecha De
  Contrato
Sistema/frente de negocio: Modificacion de datos de Cliente
  (PR000349-SP10, servicio backend Modificacion.FecContrat)

Es la pantalla con MENOS campos de las 7 mapeadas - formulario simple.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente)
- boton "Leer"
- #numeroContrato (nace DISABLED)
- #fechaContrato (nace DISABLED)
- un checkbox sin id (probablemente "Generar Nuevo Contrato", nace
  DISABLED - el EF aclara que esta opcion NO crea un contrato desde
  cero: cierra el vigente y genera una nueva version)
- boton "Cerrar"
- boton "Grabar" (nace DISABLED)

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'.

============================================================================
PENDIENTE (falta un cliente con contrato vigente real)
============================================================================
- Confirmar el id/selector real del checkbox "Generar Nuevo Contrato"
  (no vino con id en el dump).
- Mensajes reales de Leer vacio/cliente inexistente/sin contrato
  vigente.
- Flujo real de modificar fecha vs. generar nuevo contrato (son 2
  operaciones distintas segun el EF, con el mismo boton "Grabar"?,
  verificar en vivo).
============================================================================
"""

import re


def abrir_modificacion_fecha_contrato(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Modificacion De Fecha De Contrato"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_fecha_contrato(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
