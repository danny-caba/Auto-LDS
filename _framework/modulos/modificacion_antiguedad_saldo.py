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
CONFIRMADO EN VIVO 13/11/2026 (cliente real 15, TOWER AND TOWER S.A.,
antiguedadSaldo original 1,00 - restaurado tras cada prueba)
============================================================================
- Leer con cliente valido: carga nombre/direccion/antiguedadSaldo,
  bloquea #numeroCliente (disabled) y deshabilita "Leer"; "Modificar" se
  habilita. "Cerrar" (la matriz lo llama "Cancelar" pero el boton real
  se llama "Cerrar") limpia los 3 campos y re-habilita #numeroCliente y
  "Leer" - es el UNICO camino visible para "soltar" el bloqueo (no hay
  un boton "Cancelar" en la pantalla principal, solo dentro del dialogo
  de confirmacion).
- Leer con campo vacio: el boton "Leer" NO esta deshabilitado (al
  contrario de lo que podria asumirse) - el click dispara una "Ventana
  de Validacion" con "Debe ingresar el Número de Cliente."
- Leer con cliente inexistente: HTTP 404 real del backend
  ({"statusCode":404,"mensaje":"Cliente no existe.","detalle":"Cliente
  no existe."}), Ventana de Validacion con "Cliente no existe.",
  nombre/direccion quedan vacios.
- "Modificar" nace DISABLED hasta un Leer exitoso (confirmado en una
  pantalla recien abierta, sin ningun Leer previo).
- Doble uso confirmado de "Modificar" (RN-6/RN-9): 1er click habilita
  #antiguedadSaldo para edicion; 2do click dispara UNA de dos rutas:
  (a) rechazo inmediato via Ventana de Validacion si el valor no pasa
  la validacion basica (vacio, con letras, o un numero con mas de 2
  decimales - mismo mensaje "Debe ingresar una Antigüedad de Saldo
  válida." en los 3 casos) o si el valor es igual al actual
  ("No hubieron modificaciones.") - en NINGUNO de estos casos pasa por
  el dialogo de confirmacion; (b) si el valor es numerico, distinto del
  actual y con <=2 decimales, aparece el dialogo "Confirmación -
  ¿Está seguro de la modificación a realizar?" con botones
  Cancelar/Aceptar. Aceptar dispara el POST real y muestra
  "Operación realizada." (confirmado persistido con una relectura
  fresca). Cancelar cierra el dialogo sin llamar al backend (el campo
  quedo mostrando el valor tipeado, SIN persistir - confirmado con una
  relectura tras Cerrar que seguia en el valor original).
- #antiguedadSaldo tiene maxlength=6 - un valor como "-100.00"/"100.555"
  se trunca a 6 caracteres ANTES de llegar a la validacion de negocio
  (ej. "100.555" -> "100.55", que es valido) - para probar realmente
  "mas de 2 decimales" hay que usar un valor corto que quepa entero,
  ej. "1,555".
- boton "Manual": descarga directa (Playwright expect_download, sin
  popup) de manual_usuario_antiguedad_saldo.pdf desde
  tk0s-web.luzdelsur.com.pe/comercial/gesclie/modificacion/antsald/web/assets/manuales/.

PENDIENTE (necesita datos/precondiciones que el cliente 15 no cubre):
- CP004 (cliente en proceso de facturacion), CP005 (cliente en estado
  no valido para LDS), CP006 (segundo cliente valido distinto),
  CP007 (facturacion + estado invalido a la vez), CP016 (usuario sin
  area de trabajo asignada - requiere quitar/restaurar la asignacion).
- CP015 (correlativo de orden por area de trabajo + historico): esta
  pantalla NO tiene un panel de historico visible en el DOM (solo
  Nombre/Direccion/Antiguedad de Saldo) - no se puede confirmar solo
  con UI, necesita verificacion en BD.
============================================================================
"""

import re


def abrir_antiguedad_saldo(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Modificacion De Antiguedad De Saldo"], "#numeroCliente", paso_excel=paso_excel)


def leer_cliente_antiguedad_saldo(app, frame, numero_cliente):
    frame.locator("#numeroCliente").fill(numero_cliente)
    frame.get_by_role("button", name=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(1500)
    return cerrar_ventana_validacion_si_aparece(app, frame)


def cerrar_ventana_validacion_si_aparece(app, frame, intentos=6):
    """Si aparece la 'Ventana de Validacion' (rechazo inmediato, sin pasar
    por el dialogo de confirmacion Si/No; o el aviso final tras confirmar
    con Aceptar, ej. 'Operación realizada.'), la cierra con Aceptar y
    devuelve el mensaje. Hace polling corto porque el aviso final puede
    tardar en aparecer bajo slowmo/video (confirmado en vivo: 1.2s no
    siempre alcanza). Si no aparece tras los reintentos, devuelve None."""
    texto = frame.locator("body").inner_text()
    for _ in range(intentos):
        if "Ventana de Validaci" in texto:
            break
        app.wait_for_timeout(500)
        texto = frame.locator("body").inner_text()
    if "Ventana de Validaci" not in texto:
        return None
    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    idx = lineas.index(next(l for l in lineas if l.startswith("Ventana de Validaci")))
    mensaje = lineas[idx + 2] if idx + 2 < len(lineas) else None
    frame.get_by_role("button", name=re.compile(r"^\s*Aceptar\s*$")).last.click(force=True)
    app.wait_for_timeout(600)
    return mensaje


def iniciar_modificacion_antiguedad_saldo(app, frame, nuevo_valor):
    """Ejecuta el flujo de 'Modificar' con un nuevo valor (RN-6/RN-9): si
    #antiguedadSaldo ya esta habilitado (quedo asi tras un rechazo previo
    que no lo deshabilita), reusa ese estado en vez de volver a clickear
    Modificar (evita un click extra que el boton interpretaria como el
    2do click = confirmar). Devuelve 'confirmacion' si aparecio el
    dialogo Cancelar/Aceptar (valor numerico valido y distinto del
    actual), o el mensaje de rechazo inmediato (Ventana de Validacion)
    en cualquier otro caso."""
    boton_modificar = frame.get_by_role("button", name=re.compile(r"^\s*Modificar\s*$"))
    campo = frame.locator("#antiguedadSaldo")
    if campo.is_disabled():
        boton_modificar.click(force=True)
        app.wait_for_timeout(800)
    campo.fill(nuevo_valor)
    app.wait_for_timeout(300)
    boton_modificar.click(force=True)
    app.wait_for_timeout(1200)
    texto = frame.locator("body").inner_text()
    if "está seguro" in texto.lower():
        return "confirmacion"
    return cerrar_ventana_validacion_si_aparece(app, frame)


def confirmar_modificacion_antiguedad_saldo(app, frame, aceptar=True):
    """Responde el dialogo 'Confirmación - ¿Está seguro de la modificación
    a realizar?' con Aceptar (aceptar=True, dispara el POST real) o
    Cancelar (aceptar=False, no llama al backend). Devuelve el mensaje
    final de la Ventana de Validacion si aparece despues (ej. 'Operación
    realizada.')."""
    patron = r"^\s*Aceptar\s*$" if aceptar else r"^\s*Cancelar\s*$"
    frame.get_by_role("button", name=re.compile(patron)).last.click(force=True)
    app.wait_for_timeout(1200)
    return cerrar_ventana_validacion_si_aparece(app, frame)


def cerrar_antiguedad_saldo(app, frame):
    """Click en 'Cerrar' - resetea el formulario completo (limpia los 3
    campos y re-habilita #numeroCliente y 'Leer')."""
    frame.get_by_role("button", name=re.compile(r"^\s*Cerrar\s*$")).click(force=True)
    app.wait_for_timeout(1000)
