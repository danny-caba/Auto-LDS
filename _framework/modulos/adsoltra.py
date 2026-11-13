"""
Modulo: Administrador de Solicitudes de Trabajo (ADSOLTRA, Web LDS)
Componente Angular raiz de la bandeja: app-bandeja-ordenes (hijos:
app-grilla-ordenes, app-paginador)
Ruta de menu confirmada en vivo: Comercial > Administrador De Solicitudes De Trabajo
(abre POPUP con iframe #aplicacion, igual mecanica que el resto de Web LDS)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en cualquier proyecto/sprint que lo toque - no depende de
PR000349-SP8 puntualmente.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP8, 06/11/2026)
============================================================================

Backend real: tabla `acl_orden` (numero_orden, numero_cliente, estado,
tipo_orden, rol_creador, rol_actual, ult_rolp_envio, ult_usuario_envio,
usuario_creador, area_creacion, sucursal, corr_flujo). Catalogo de tipos
de orden `SOLTRA`: `SEGEN` (Solicitud Especial, pantalla propia),
`EXTRAC` (Extractor, pantalla propia via acl_extractor), `MANSER`
(excluido de la grilla por regla de negocio RN-02, nunca aparece), y
otros codigos sin pantalla asociada (`ACO`=Activacion Comercial,
`NUCLI`=Nuevo Cliente) que abren la orden sin mostrar ninguna ventana.

**Rol de sesion de DCABA_DW para este aplicativo: `DACD`** (confirmado
por el usuario). La regla de visibilidad de una fila es OR de 6 criterios
sobre `acl_orden`: `rol_actual`, `ult_rolp_envio`, `rol_creador`,
`ult_usuario_envio`, `usuario_creador` = rol de sesion, O el rol_actual
de la fila esta entre los roles asignados al usuario (no exige que sea
el mismo rol de la sesion - confirmado por el propio legado
`frmprinc.frm:608-625`).

**Bandeja (pantalla principal)**: 5 botones de estado (texto completo
real incluye el codigo en una segunda linea, ej. "Ordenes Pendientes\nRQ"
- NO usar match exacto de una sola linea, usar
`frame.locator("button").filter(has_text=re.escape("Ordenes Pendientes"))`
que si funciona por substring). Antes de elegir cualquier estado, la
grilla esta vacia con el mensaje "No hay una consulta en curso. Elija una
opción del listado para obtener datos." y "Registros 0 a 0 de 0" (CP002).
**Gotcha confirmado en vivo 06/11/2026: NO usar `re.escape()` para
armar un `has_text` de tipo string.** En Python 3.13 `re.escape(" ")`
devuelve `"\\ "` (escapa el espacio) - si ese resultado se pasa tal
cual a `filter(has_text=...)` (match de SUBSTRING, no regex), Playwright
busca el backslash literal y nunca matchea nada (timeout silencioso de
30s en el click). `has_text` con un string plano ya hace substring
match sin necesitar escapar nada.

Encabezados de columna de rol/fecha SEGUN estado (confirmado en vivo
exacto):
  - Pendientes/Devueltas/Anuladas: Rol Emisor / Rol Receptor
  - Finalizadas:                   Rol Creador / Rol Finalizador
  - Todas:                         Rol Creador / Rol Actual
El titulo de la pantalla agrega el sufijo "(Ordenes Pendientes)" /
"(Ordenes Devueltas)" / "(Ordenes Finalizadas)" / "(Ordenes Anuladas)" /
"(Todas las Ordenes)" al ELEGIR explicitamente cualquiera de los 5
estados (confirmado en vivo 06/11/2026 con datos reales en Pendientes).
CORRECCION sobre una nota anterior de este mismo archivo: con la
bandeja en su estado inicial (SIN elegir ninguna opcion, ver CP002) el
titulo esta sin sufijo, pero eso es porque ahi NINGUN estado esta
elegido todavia - no porque "Pendientes" en particular lo omita. La
nota vieja ("Pendientes queda sin sufijo, no es un bug") se escribio
en una corrida con los 5 estados vacios (0 ordenes) y resulto ser un
artefacto de lectura con la grilla a medio cargar, no el comportamiento
real.

**DATO ESCASO confirmado en vivo 06/11/2026**: con DCABA_DW (rol DACD)
la bandeja devuelve 0 registros en LOS 5 ESTADOS simultaneamente -
ninguna orden real tiene DACD en ninguno de los 6 criterios de
visibilidad. Mismo patron que el H001 de mantenimiento_orden_conexion.py
(ver ese modulo). Bloquea los casos que necesitan filas reales (CP003,
CP004, CP005, CP006, CP007, CP009, CP011 de RF-01, y por la misma regla
de visibilidad probablemente tambien RF-02/03/04). Unica orden natural
confirmada accesible a DACD: la 500007 (EXTRAC), y solo tras el UPDATE
temporal `acl_orden.rol_actual = 'DACD'` (ver RF-05 mas abajo) - revertido
despues de la prueba.

**Tecnica de flip temporal ya validada** (igual patron que
`nucli.rol_creacion`/`estoc.traspaso` en mantord): `UPDATE acl_orden SET
rol_actual = 'DACD' WHERE empresa = '7' AND numero_orden = N;` antes de
la corrida, confirmar con el usuario, y revertir al valor original
inmediatamente despues con el mismo WHERE.

**Botones de accion** (todos confirmados `enabled=True` para DCABA_DW,
sin bloqueo de permisos en ninguno): `SEGEN`, `Consultar/Modificar`,
`Historial de la Orden`, `Buscar`, `Reasignación de Orden`, `Actualizar
Ventana`, `Exportar a Excel`. `SEGEN` no requiere fila seleccionada (crea
una orden nueva); el resto SI la requiere (CP008: sin seleccion, mensaje
"Ud. no ha seleccionado ninguna orden." y no abre nada).

**Manual de usuario**: boton propio con el PDF en la bandeja, en Buscar,
en Historial de la Orden, en Reasignacion de Orden y en Consultar/
Modificar. SEGEN y los buscadores internos (Consultar Usuario Destino,
Extractor) NO tienen boton Manual propio.

**DATO ESCASO confirmado en vivo 06/11/2026 (RF-06, Usuario Destino)**:
de 8 roles reales probados contra el buscador "Consultar Usuario
Destino" (MGG, OMV, SGV, LEP, EPS2, APRUEBA.2310, DIG.2310, EXPLRECAU -
mezcla de tipo U y F), NINGUNO pasa la validacion backend
`ConsultarRolAreaVigente` que se dispara al accionar "Enviar" (todos
devuelven "Debe de seleccionar un rol destino válido."). El propio rol
de sesion (DACD) ni siquiera aparece en el catalogo del buscador. Mismo
patron de escasez que el H001 de mantenimiento_orden_conexion.py -
pendiente encontrar un rol con area vigente real (ver tabla `rol`,
columnas rol/tipo/area/vigencia) antes de poder completar CP044/045/
046-D/049-C (que requieren un Enviar exitoso).

**RF-05 (Extractor)**: se abre vía Consultar/Modificar sobre una orden
tipo EXTRAC. Modal con campos Numero de ODT, Para (destino), Archivo
Adjunto, y botones Guardar/Finalizar/Cancelar. Confirmado en vivo con la
orden real 500007 (SS/cliente 1391305, ODT 14865, archivo
todas865.xls) tras el flip temporal de rol_actual.
"""

import re


def abrir_adsoltra(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Administrador De Solicitudes De Trabajo"], "app-bandeja-ordenes", paso_excel=paso_excel)


def elegir_estado(app, frame, texto_boton):
    """texto_boton: 'Ordenes Pendientes' | 'Ordenes Devueltas' |
    'Ordenes Finalizadas' | 'Ordenes Anuladas' | 'Todas las Ordenes'
    (substring, SIN el codigo de la segunda linea - ver gotcha de ficha
    tecnica: el texto completo del boton es 'Ordenes Pendientes\\nRQ').

    Gotcha real confirmado en vivo 06/11/2026: 'Ordenes Finalizadas' (y
    'Todas las Ordenes', que tambien barre ese universo) puede tardar
    30+ SEGUNDOS en responder en este ambiente - la tabla SEGEN con
    estado FI tiene 2.3 millones de filas. Un wait_for_timeout fijo
    corto (2-4s, suficiente para Pendientes/Devueltas/Anuladas) deja la
    grilla leida a medio cargar ('Registros 0 a 0 de 0' == todavia
    cargando, NO necesariamente vacio de verdad) y produce falsos
    negativos. esperar_fin_de_carga() NO sirve aca (esta app no usa
    ningun boton 'Cargando...' ni mat-spinner, y su timeout interno de
    networkidle esta capado a 10s) - se espera directo la respuesta
    real de la API (POST .../api/ordenes/ConsultarOrdenes) con
    expect_response, que no depende de ninguna heuristica visual.

    Gotcha adicional confirmado en vivo 06/11/2026: ademas de lenta, la
    consulta de 'Ordenes Finalizadas'/'Todas las Ordenes' a veces falla
    de verdad con un dialogo 'Error de Servicio: Error al consultar las
    órdenes de la bandeja.' - intermitente (en 2 intentos seguidos, uno
    fallo y el otro no), consistente con una query pesada contra una
    tabla de millones de filas bajo carga variable del servidor, no un
    bug de esta automatizacion. Se reintenta hasta 3 veces cerrando ese
    dialogo antes de dejar que la excepcion/assert real se propague."""
    for intento in range(3):
        residual = frame.locator(".ant-modal, nz-modal-container")
        if residual.count() and residual.first.is_visible():
            boton_cerrar = residual.first.get_by_role("button", name=re.compile("Aceptar|Cerrar|Cancelar", re.I))
            if boton_cerrar.count():
                boton_cerrar.first.click(force=True)
            else:
                residual.first.locator(".ant-modal-close, button[aria-label='Close']").first.click(force=True)
            app.wait_for_timeout(600)
        with app.expect_response(lambda r: "ConsultarOrdenes" in r.url, timeout=45000):
            frame.locator("button").filter(has_text=texto_boton).first.click(force=True)
        app.wait_for_timeout(800)
        if not frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Error de Servicio")).count():
            return
    # Se agotaron los reintentos - dejar el estado como quedo para que
    # el assert real de quien llama reporte el fallo con contexto util.


def texto_pie_paginador(frame):
    """Devuelve (desde, hasta, total) del pie 'Registros X a Y de Z'."""
    texto = frame.locator("body").inner_text()
    m = re.search(r"Registros\s+(\d+)\s+a\s+(\d+)\s+de\s+(\d+)", texto)
    if not m:
        return None
    return tuple(int(g) for g in m.groups())


def pie_paginador_estable(app, frame, intentos=8, espera_ms=600):
    """Igual que texto_pie_paginador(), pero espera a que el valor se
    mantenga igual en 2 lecturas consecutivas antes de devolverlo.

    Gotcha confirmado en vivo 12/11/2026 (RF-02, busquedas SEGEN sin
    filtro de rol): leer el pie apenas termina el expect_response de
    ConsultarOrdenes puede capturar la grilla a medio renderizar (mismo
    patron que el buscador de Usuario Destino en CP060) y dar un total
    mas bajo que el real, de forma no determinista entre corridas (14,
    15, 23 leidos en sucesion sobre la MISMA busqueda). Si no se
    estabiliza en `intentos` lecturas, devuelve la ultima leida."""
    anterior = texto_pie_paginador(frame)
    for _ in range(intentos):
        app.wait_for_timeout(espera_ms)
        actual = texto_pie_paginador(frame)
        if actual == anterior and actual is not None:
            return actual
        anterior = actual
    return anterior


def seleccionar_fila_por_numero_orden(frame, numero_orden):
    fila = frame.locator("tr", has_text=str(numero_orden))
    fila.first.click()
    return fila.first


def abrir_buscador_dinamico(app, frame, aria_label, boton_puntos_index, modal_padre):
    """Abre un buscador dinamico (Rol/Area o Cliente) desde cualquier
    boton '...' de un modal padre (SEGEN o la Busqueda especifica de
    RF-02) y devuelve el locator correcto, ya desambiguado.

    Gotcha confirmado en vivo 06/11/2026: `frame.get_by_label(aria_label,
    exact=True)` puede resolver a 2 elementos con el MISMO aria-label
    segun el contexto - en SEGEN el real es el PRIMERO (.first), en la
    Busqueda especifica de RF-02 el real es el SEGUNDO (.last). No
    asumir cual es sin verificar: esta funcion prueba ambos extremos y
    devuelve el que realmente tiene filas (tr.sm-fila) o el que haya
    despues de esperar su carga."""
    modal_padre.locator("button", has_text="…").nth(boton_puntos_index).click(force=True)
    app.wait_for_timeout(3000)
    candidatos = frame.get_by_label(aria_label, exact=True)
    for i in range(candidatos.count()):
        candidato = candidatos.nth(i)
        if candidato.locator("tr.sm-fila").count() > 0 or candidato.locator("table").count() > 0:
            return candidato
    return candidatos.last


def abrir_buscar(app, frame):
    """Abre la Busqueda especifica (RF-02) y devuelve el locator del
    modal 'Busqueda - <estado>'. Identificado por texto (no por
    posicion/cdk-overlay-N) porque el 'Ventana de Validacion' que puede
    aparecer DESPUES queda en un overlay hermano - usar siempre
    filter(has_text=...) con el titulo real, nunca .last/.nth(0) a
    ciegas (confirmado en vivo 06/11/2026 que el conteo de
    `[id^='cdk-overlay-']` es inconsistente segun cuantos dialogos haya
    apilados)."""
    frame.locator("button", has_text="Buscar").first.click()
    app.wait_for_timeout(1500)
    return frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\s*Búsqueda\s*-"))


def buscar_y_seleccionar_orden(app, frame, numero_orden, tipo_orden=None):
    """Usa 'Todas las Ordenes' + Busqueda especifica por Numero de Orden
    (criterio '= (Todos)' de estado) para encontrar y seleccionar CUALQUIER
    orden por numero, sin importar en que estado este - evita depender de
    adivinar el estado/tab correcto. Deja la fila ya seleccionada (click),
    lista para accionar Historial/Reasignacion/Consultar-Modificar.

    Gotcha confirmado en vivo 08/11/2026: el combo 'Tipo de Orden' del
    modal de Busqueda arranca en 'EXTRAC' por default y NO tiene opcion
    '=(Todos)' (solo EXTRAC/SEGEN) - si la orden buscada es SEGEN y no se
    pasa `tipo_orden='SEGEN = Solicitudes Especiales'` explicitamente,
    la busqueda da 'No se encontro la orden solicitada' aunque la orden
    exista. Pasar `tipo_orden` (el label exacto del <option>) cuando se
    sepa que la orden NO es EXTRAC.

    Reintento confirmado en vivo 08/11/2026: el click en 'Todas las
    Ordenes' (y la busqueda posterior) puede toparse con un dialogo
    residual ('Error de Servicio' intermitente del backend, o una
    Ventana de Validacion que quedo abierta de una accion anterior) que
    intercepta el click - se cierra cualquier dialogo visible antes de
    cada intento, hasta 3 veces."""
    for _intento in range(3):
        residual = frame.locator(".ant-modal, nz-modal-container")
        if residual.count() and residual.first.is_visible():
            boton_cerrar = residual.first.get_by_role("button", name=re.compile("Aceptar|Cancelar|Cerrar", re.I))
            if boton_cerrar.count():
                boton_cerrar.first.click(force=True)
            else:
                residual.first.locator(".ant-modal-close, button[aria-label='Close']").first.click(force=True)
            app.wait_for_timeout(800)
        try:
            frame.locator("button", has_text="Todas las Ordenes").first.click(force=True, timeout=10000)
            break
        except PWTimeoutError:
            if _intento == 2:
                raise
    app.wait_for_timeout(2500)
    frame.locator("button", has_text="Buscar").first.click(force=True)
    app.wait_for_timeout(1500)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"^\s*Búsqueda\s*-")).last
    modal.first.locator("#bsqEstado").select_option(label="= (Todos)")
    app.wait_for_timeout(300)
    if tipo_orden:
        modal.first.locator("#bsqTipoOrden").select_option(label=tipo_orden)
        app.wait_for_timeout(300)
    modal.first.locator("#bsqNroOrden").fill(str(numero_orden))
    modal.first.locator("button", has_text="Buscar").click()
    app.wait_for_timeout(2000)
    frame.locator("tr", has_text=str(numero_orden)).first.click()
    app.wait_for_timeout(500)


def abrir_historial_de_orden(app, frame):
    """Con una orden ya seleccionada en la grilla (ver
    buscar_y_seleccionar_orden), abre su Historial de la Orden y devuelve
    el locator del modal. Filas reales = tr.his-fila (NO 'tr' generico,
    que tambien matchea el <tr> del thead); panel de observaciones =
    .his-obs-box, un DIV role=textbox aria-readonly=true (NO un
    textarea) - confirmado en vivo 06/11/2026."""
    frame.locator("button", has_text="Historial de la Orden").first.click()
    app.wait_for_timeout(2000)
    return frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Historia de la Orden")).last


def abrir_segen(app, frame):
    """Abre la Creacion de una Solicitud Especial (RF-06) y devuelve el
    locator del modal. Identificado por texto (no por posicion) porque
    los buscadores que abre (RF-07) quedan NESTED dentro del mismo DOM
    del modal SEGEN (no son overlays hermanos como Busqueda/Ventana de
    Validacion de RF-02) - confirmado en vivo 06/11/2026."""
    frame.locator("button", has_text=re.compile(r"^\s*SEGEN\s*$")).click()
    app.wait_for_timeout(2000)
    return frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Creación de una Solicitud Especial")).last


def abrir_buscador_usuario_destino(app, frame, overlay_segen):
    """Click en el primer boton '...' del modal SEGEN (Usuario Destino) y
    devuelve el locator del buscador 'Consultar Usuario Destino'.

    Gotcha confirmado en vivo 06/11/2026: el buscador NO es un overlay
    hermano (a diferencia de RF-02) - esta anidado dentro del propio DOM
    de SEGEN, asi que `.filter(has_text=...)` sobre '.ant-modal,
    nz-modal-container' matchea el modal SEGEN COMPLETO (que tambien
    contiene el texto del buscador) y produce un strict-mode violation
    con 2 botones "Cancelar" (uno de SEGEN, otro del buscador). La
    propia pista de error de Playwright da el selector correcto: el
    buscador tiene `aria-label="Consultar Usuario Destino"` exacto - usar
    `frame.get_by_label(..., exact=True)` para escoparlo sin ambiguedad.
    Las filas de la grilla son `tr.sm-fila` (NO el "tr" generico, que
    tambien matchea el <tr> del thead) y tardan ~2-3s en poblarse tras
    el click (la llamada real es a
    .../api/sqlgui/Sqlgui/Modal/AST_ROL_AREA + .../Sqlgui/Ejecutar)."""
    overlay_segen.locator("button", has_text="…").nth(0).click(force=True)
    app.wait_for_timeout(2500)
    return frame.get_by_label("Consultar Usuario Destino", exact=True)


def cerrar_dialogo_validacion_si_aparece(app, frame, timeout_ms=2500):
    """Si aparece 'Ventana de Validación' (mensaje de error de la
    busqueda/formulario), lo cierra con Aceptar y devuelve su texto;
    si no aparece, devuelve None. No afecta al modal de Busqueda, que
    puede seguir abierto detras (es un overlay hermano, no el mismo)."""
    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(r"Ventana de Validación"))
    for _ in range(timeout_ms // 250):
        if dialogo.count() and dialogo.first.is_visible():
            mensaje = dialogo.first.inner_text()
            dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
            app.wait_for_timeout(500)
            return mensaje
        app.wait_for_timeout(250)
    return None
