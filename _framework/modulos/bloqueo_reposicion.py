"""
Modulo: Bloqueo de Reposicion / "Bloqueo De Reconexion" (Web LDS)
Componente Angular: app-root (shell generico de la plataforma - el
  componente interno real de la pantalla todavia no se identifico, ver
  PENDIENTE abajo)
Ruta de menu confirmada en vivo: Tecnico > Bloqueo De Reconexion (OJO:
  bajo "Tecnico", NO bajo "Comercial" como el resto de pantallas de
  PR000349-SP10 - y el nombre real del menu es "Bloqueo De Reconexion",
  no "Bloqueo de Reposicion" como lo llama el EF; el propio EF aclara
  que "bloqueo de reconexion" es el termino literal del sistema)
Sistema/frente de negocio: Modificacion de datos de Cliente (PR000349-SP10,
  servicio backend Modificacion.Bloqrcnx)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP10, 13/11/2026)
============================================================================

Campos reales del formulario (ids confirmados via dump del DOM):
- #numeroCliente (N.° de Cliente) + #dvNumeroCliente (digito verificador,
  campo separado, NO se digita segun el EF)
- boton "Leer" (sin aria especial, texto exacto "Leer")
- Solo lectura tras Leer: #saldo, #antiguedad, #nombre, #direccion,
  #tipoCliente, #tarifa, #categoria, #sucursal, #rutaLectura,
  #dvRutaLectura, #comuna, #accionCorte, #fechaCorte
- #comentario (textarea, PLACEHOLDER "Obligatorio unicamente al activar
  el bloqueo" - nace DISABLED, se habilita recien al activar el bloqueo)
- boton "Bloquear" (nace DISABLED hasta un Leer exitoso; el EF dice que
  cambia de texto a "Desbloquear" segun el estado vigente del cliente -
  no confirmado en vivo todavia, ver PENDIENTE)
- boton "Cerrar"

selector_pantalla recomendado para abrir_aplicacion(): '#numeroCliente'
(el componente raiz es app-root generico de la plataforma, no sirve
para confirmar que ESTA pantalla en particular cargo).

============================================================================
PENDIENTE (no se pudo verificar en vivo todavia - falta un N.° de
Cliente real que cumpla las condiciones del EF: activo o retirado CON
bloqueo de reconexion vigente, sector no excluido (NO 20/33), no
Alumbrado Publico, suministro no totalizador)
============================================================================
- Mensaje real de "Cliente no existe." / Leer sin numero (RN-17/RN-18).
- Si el boton realmente cambia de texto "Bloquear" <-> "Desbloquear"
  segun el estado vigente (RN-26).
- Flujo completo de Bloquear (comentario obligatorio, RN-24) y
  Desbloquear.
- Autorizacion adicional MODES5 (Estado_Cliente='5') - RN-22, cuenta
  DCABA_DW no se probo todavia contra un cliente en ese estado.
============================================================================
"""

import re


def abrir_bloqueo_reposicion(page, paso_excel=None):
    return abrir_aplicacion(page, ["Tecnico", "Bloqueo De Reconexion"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_bloqueo(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
