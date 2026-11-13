"""
encargos_ordenpago.py - helpers y ficha tecnica para la pantalla
"Mantenedor de Orden de Pagos" (RF-02 de PR000349-SP9, modulo Encargos -
submodulo Cobranza).

Componente Angular raiz: <app-ordenpago>
Ruta de menu real: Aplicaciones > Comercial > "Mantenedor De Orden De
Pagos" (directo bajo Comercial, confirmado en vivo 11/11/2026).

Campos reales:
  3 nz-select (input.ant-select-selection-search-input, en este orden):
    [0] #encargo        combo de "Encargo de Cobranza" (TMO, AON *, etc).
    [1] #oficina        combo de "Oficina de Recaudacion" - SIEMPRE
                         deshabilitado (ant-select-disabled) una vez
                         elegido el encargo; el backend ya lo trata como
                         "sin filtro de oficina" (coincide con la nota de
                         la matriz "Todos -> sin filtro"), NO hace falta
                         (ni se puede) clickearlo.
    [2] #operadorFecha  combo del operador de "Fecha Inicio" (Igual a /
                         Menor o igual / Mayor o igual / Entre).
  input[name='estadoOrdenPago'] (radio x3): Procesada / Generada / Liquidar.
  #fechaInicio          input type=date nativo.
  Boton "Leer" dispara POST a .../ordpago/web/api/ordenpago/obtener-ordenes-pago.
  Totales de la grilla (solo lectura, inputs con id):
    #totalRecaudado, #totalComision, #totalEntrega, #totalCantidad.

Gotcha real confirmado en vivo 11/11/2026: tras seleccionar el Encargo,
el popup puede tardar en terminar de re-renderizar los 3 nz-select; si
se intenta abrir cualquier combo antes de que `app-ordenpago` y el
primer buscador ant-select esten listos (`wait_for` explicito), el
conteo de buscadores puede salir en 0 de forma intermitente - no es un
problema del combo de Oficina (ese SIEMPRE da 0 opciones porque esta
deshabilitado a proposito, ver arriba).

Datos de prueba reutilizables (confirmados en vivo 11/11/2026, CP008):
Encargo TMO (TELEFONICA DEL PERU MOVILES) + estado Procesada + operador
"Mayor o igual" + fechaInicio = fecha del dia -> con la fila de alta de
precondicion (`entrega_encargo.estado='G'`, importe 250.00, cantidad 10,
comision 8.00/transaccion) la grilla devuelve 1 fila y los totales
250,00 / 80,00 / 170,00 / 10 - exacto a lo que pide la matriz.

Grilla de resultados: cada fila tiene un checkbox de seleccion (columna
"Seleccion"); "Generar Orden" dispara primero un dialogo de
confirmacion propio del front ("Se generara la Orden de Pago con N
entrega(s) seleccionada(s). Desea continuar?") - DISTINTO del POST real
a RegistrarOrdenPago, que recien se dispara al aceptar ese dialogo.

Hallazgo real confirmado en vivo 11/11/2026 (CP011): con una fila en
`control_proceso` (codigo='LISPAGTDP', estado='E') el POST a
RegistrarOrdenPago responde 200 (no 4xx/5xx) con
`{"folio":"","cantidadEntregas":0,"montoTotal":0,"bloqueado":true,
"mensajeUsuario":"Existe algún proceso de automata de pagos externos
pendiente, No se puede Generar orden."}` y aparece un dialogo de
"Ventana de Validacion" con ese mismo mensaje - la entrega marcada NO
se consume (sigue en estado 'G', reutilizable para el siguiente caso
que la necesite, ej. CP012, sin volver a insertarla).

Modo Liquidar (radio "Liquidar"): la grilla muestra ordenes ya
generadas (estado_liquida='A'=GENERADO), cada una con checkbox propio.
"Liquidar" abre un modal "Ingreso de EMIDOC" con campos reales:
#ingemiRazonSocial, #ingemiProducto (ambos solo lectura), #ingemiMonto
(precargado desde la comision real de la orden - NO editable salvo
tipo de comision = 3), #ingemiTipoDocumento (nz-select: Boleta/Factura/
etc), #ingemiFechaIngreso (date), #ingemiLibro, #ingemiNumeroDocumento.

Gotchas reales confirmados en vivo 11/11/2026 (CP013/CP014):
- Las ordenes HISTORICAS de TFI/TMO en Liquidar casi siempre tienen
  comision 0 (monto_comision=0 en entrega_encargo) - con Monto de Pago
  en 0,00 el front corta ANTES de llegar al backend con "Ventana de
  Validacion: Monto a Liquidar debe ser mayor a cero". Para probar el
  flujo real hace falta una orden con comision > 0 - la unica forma
  confirmada de conseguirla en Pruebas es generar una fresca (mismo
  ciclo de alta+Generar Orden que CP012, encargo TMO, comision 8.00/
  transaccion -> 80.00 con 10 transacciones).
- El rango valido de "N.° de Documento" depende del libro+proveedor
  real de la orden, NO es el mismo numero para todos los encargos: con
  TMO (RUC 20100017491, TELEFONICA DEL PERU S.A.A.) y Libro 001 el
  rango real medido es "mayor a 4012 y menor a 5012" (el rango
  20119-20169 que trae la matriz original era especifico del
  encargo/proveedor YEL, que no es seleccionable en este ambiente -
  ver abajo).
- El periodo EMIDOC (con_periodos, sistema/modulo='EMIDOC') que esta
  realmente ABIERTO en Pruebas varia con el tiempo: medido en vivo
  11/11/2026 solo existe fila para 2026/01 (estado 'A'); cualquier otro
  mes de 2026 (incluido el que media la matriz original, 2026/08) da
  "Periodo no Existe." en vez de llegar al corte real por EMIDOC. Para
  un periodo CERRADO (CP014) 2025/12 esta confirmado 'C' en vivo.
- El encargo `YEL` (PRODUCTOS YEL, concepto YEL) que usaba la matriz
  original para CP013/CP014 tiene `ind_vigente='N'` en Pruebas (
  confirmado por SQL) y por eso NO aparece en el combo de Encargo de
  Cobranza - mismo patron de desalineacion Desarrollo/Pruebas visto en
  otros RF de este proyecto. TMO (vigente, con una orden fresca
  generada) sirve como sustituto real y valido.
- El mensaje real de bloqueo EMIDOC (B-01) es "No se puede registrar
  el comprobante EMIDOC de liquidación: el contrato de emisión no está
  especificado para este servicio. Comuníquese con el área de
  Informática." (la matriz original citaba "...Área de Sistemas",
  variante de redaccion del mismo mensaje).
"""
import re


def abrir_orden_pagos(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Mantenedor De Orden De Pagos'
    y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Comercial", "Mantenedor De Orden De Pagos"], "app-ordenpago", timeout_pantalla=35000, paso_excel=paso_excel)


def seleccionar_encargo(app, frame, nombre_encargo):
    """Selecciona un Encargo de Cobranza por su nombre visible y espera a
    que el estado de habilitado/deshabilitado del boton 'Leer' termine de
    asentarse (gotcha real confirmado en vivo 11/11/2026: leer
    is_enabled() del boton con menos de ~3s de espera tras elegir el
    encargo puede devolver el valor ANTERIOR, todavia no actualizado por
    Angular - aunque el click posterior con force=True si llega a
    funcionar incluso con una espera mas corta)."""
    frame.locator("app-ordenpago").wait_for(timeout=20000)
    buscadores = frame.locator("input.ant-select-selection-search-input")
    buscadores.first.wait_for(timeout=20000)
    opcion = frame.locator("nz-option-item", has_text=nombre_encargo)
    for _ in range(10):
        buscadores.nth(0).click(force=True)
        app.wait_for_timeout(1000)
        if opcion.count():
            break
    opcion.first.click(force=True)
    try:
        app.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    app.wait_for_timeout(4500)


def consultar_ordenes_pago(app, frame, nombre_encargo, estado, operador_fecha, fecha_inicio):
    """Selecciona Encargo (por nombre visible en el combo), el radio de
    Estado, el operador de Fecha Inicio y la fecha, y clickea 'Leer'.
    La Oficina NO se toca (ver ficha tecnica: siempre deshabilitada,
    efectivamente "Todos"/sin filtro). Devuelve el cuerpo real (dict)
    de la respuesta de la consulta."""
    seleccionar_encargo(app, frame, nombre_encargo)
    buscadores = frame.locator("input.ant-select-selection-search-input")

    frame.locator("label", has_text=estado).first.click(force=True)
    app.wait_for_timeout(500)

    buscadores.nth(2).click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=operador_fecha).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#fechaInicio").fill(fecha_inicio)
    app.wait_for_timeout(500)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=15000) as resp_info:
        frame.locator("button", has_text="Leer").click(force=True)
    app.wait_for_timeout(1500)
    return resp_info.value.json()


def marcar_entregas_y_generar(app, frame):
    """Marca TODAS las entregas visibles en la grilla (checkbox) y
    clickea 'Generar Orden', confirmando el dialogo de 'Se generara la
    Orden de Pago...'. Devuelve el cuerpo real (dict) de la respuesta de
    RegistrarOrdenPago (con bloqueado=True/False segun corresponda)."""
    checks = frame.locator("table input[type='checkbox'], .ant-table-tbody input[type='checkbox']")
    for i in range(checks.count()):
        checks.nth(i).click(force=True)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Generar Orden").click(force=True)
    app.wait_for_timeout(1000)
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text="Se generará la Orden de Pago")
    with app.expect_response(lambda r: "/api/" in r.url, timeout=15000) as resp_info:
        dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
    app.wait_for_timeout(1500)
    cuerpo = resp_info.value.json()

    dialogo_final = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación|Validacion"))
    mensaje = None
    if dialogo_final.count() and dialogo_final.first.is_visible():
        mensaje = dialogo_final.first.inner_text()
        dialogo_final.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
        app.wait_for_timeout(500)
    return cuerpo, mensaje


def liquidar_con_emidoc(app, frame, tipo_documento, fecha_ingreso, libro, numero_documento):
    """Marca la PRIMERA entrega/orden visible en la grilla (modo
    Liquidar) y clickea 'Liquidar', abriendo el modal 'Ingreso de
    EMIDOC'. Completa Tipo de Documento (nz-select #ingemiTipoDocumento),
    Fecha de Ingreso (#ingemiFechaIngreso), Libro (#ingemiLibro) y
    Documento (#ingemiNumeroDocumento), y clickea 'Aceptar'.

    Devuelve (monto_precargado, mensaje_dialogo): el valor real de
    '#ingemiMonto' ANTES de aceptar (para verificar que vino precargado
    de la orden, no editado a mano) y el texto del dialogo de
    'Ventana de Validacion' si aparece uno tras aceptar (None si no
    aparece ninguno - caso no confirmado aun en este proyecto).

    Gotcha real confirmado en vivo 11/11/2026: el dialogo de resultado
    (bloqueo/rechazo) NO usa la misma clase CSS que el de 'Generar
    Orden' (`.ant-modal, nz-modal-container` da 0 coincidencias aca) -
    se lee por texto plano de toda la pantalla en vez de un selector
    estructurado."""
    checks = frame.locator("table input[type='checkbox'], .ant-table-tbody input[type='checkbox']")
    checks.first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Liquidar").first.click(force=True)
    app.wait_for_timeout(2000)

    monto_precargado = frame.locator("#ingemiMonto").input_value()

    tipo_doc = frame.locator("#ingemiTipoDocumento")
    tipo_doc.click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=tipo_documento).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#ingemiFechaIngreso").fill(fecha_ingreso)
    frame.locator("#ingemiLibro").fill(libro)
    frame.locator("#ingemiNumeroDocumento").fill(numero_documento)
    app.wait_for_timeout(500)

    frame.locator("button", has_text="Aceptar").last.click(force=True)
    app.wait_for_timeout(2500)

    texto_pantalla = frame.locator("body").inner_text()
    mensaje = None
    if "Ventana de Validación" in texto_pantalla:
        inicio = texto_pantalla.index("Ventana de Validación")
        mensaje = texto_pantalla[inicio:inicio + 400]
        frame.get_by_role("button", name=re.compile("Aceptar", re.I)).last.click(force=True)
        app.wait_for_timeout(500)
    return monto_precargado, mensaje


def exportar_a_excel(app, frame):
    """Clickea 'A Excel...' y devuelve el objeto Download real (sin
    guardarlo) - el caller decide donde guardarlo y como validar su
    contenido."""
    with app.expect_download(timeout=15000) as descarga_info:
        frame.locator("button", has_text="A Excel").click(force=True)
    return descarga_info.value
