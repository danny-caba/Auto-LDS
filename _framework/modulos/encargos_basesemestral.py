"""
encargos_basesemestral.py - helpers y ficha tecnica para las 2 pantallas
de Medidores de PR000349-SP9: RF-05 "Importacion de Base Semestral"
(Base Semestral De Medidores) y RF-06 "Consulta de Base Semestral"
(Consulta Y Extraccion De Base Semestral). Dominio Medidores, separado
por completo del dominio Cobranza del resto del proyecto (tablas
mm_base_semestral/mm_semestre/mm_ruta_optima_cab/osi_medid_marca_eq,
BD tecnica `dbtecnica` para las ultimas dos).

Roles reales: MM.ADMIN desbloquea AMBAS pantallas (confirmado en vivo
11/11/2026, tras asignarsele a DCABA_DW) - no hizo falta MM.CONSULT/
MM.DIGITA/MM.ADM por separado para destrabar el menu.

### RF-05 - Importacion de Base Semestral
Componente: <app-importacion-basesemestral> (+ <app-resultados-validacion>)
Ruta de menu real: Aplicaciones > Comercial > "Base Semestral De
Medidores" (directo bajo Comercial).

Campos reales: nz-select #codigoSemestre (combo "Semestre de
Contraste", READONLY - no se puede tipear para filtrar, solo
seleccionar de la lista), #descripcionSemestre, #cantidadMedidores,
#porcentajeMf, #porcentajeTf, #medidoresExistentes, #medidoresSeleccionados
(todos solo lectura), input[type=file] #archivoImportar, nz-select
#formatoArchivo, #cantidadMaximaAValidar, #filaInicio (number),
#estadoProceso. Botones: "Detalles...", "Validar...", "Procesar",
"Enviar a Osinerg en formato Excel...".

Gotcha real confirmado en vivo 11/11/2026: el combo de semestre esta
VIRTUALIZADO (`cdk-virtual-scroll-viewport`) y el buscador es
`readonly` (no admite `.fill()` para filtrar) - solo se ve una ventana
de ~16 opciones a la vez, ordenadas de mas reciente a mas antigua
(2026-S2 primero). Para seleccionar un semestre que no esta en la
ventana inicial hay que hacer scroll INCREMENTAL del viewport
(`el.scrollTop += N`) hasta que la opcion aparezca - un salto directo a
`scrollHeight` SALTEA entradas intermedias (confirmado: un salto
directo no encontro 2016-S1, pero si el extremo 2003-S2).

Hallazgo real (desalineacion Desarrollo/Pruebas, igual patron que
otros RF de este proyecto): NINGUN semestre tiene 0 medidores en total
en Pruebas (la condicion de "semestre sin medidores previos" que pide
CP031 no se puede lograr por cantidad total) - la condicion real que
el backend evalua es la cantidad con SEMANA DE CONTRASTE asignada
(`mm_base_semestral.nro_semana IS NOT NULL`): el semestre 2016- S1 que
trae la matriz original YA tiene medidores con semana asignada en
Pruebas (bloquea la opcion de carga), mientras que 2003- S2 no tiene
NINGUNO con semana asignada (los radios de Opcion de Carga quedan
habilitados) - usar 2003- S2 como sustituto real de "semestre sin
medidores previos".

### RF-06 - Consulta de Base Semestral (Consulta Y Extraccion De Base Semestral)
Dos caminos de entrada reales:
1. **Desde "Detalles..." de RF-05** (boton en la pantalla de
   Importacion): abre un popup SIN iframe (`#aplicacion` no existe -
   el contenido carga directo en el body del popup) con el semestre ya
   FIJADO (no editable) - mensaje real: 'Semestre fijado al abrir esta
   consulta desde "Detalles..." de la Importación de Base Semestral:
   para cambiarlo, selecciónelo en esa pantalla.'
2. **Por el recurso de menu propio** ("Consulta Y Extraccion De Base
   Semestral", bajo Comercial): CORREGIDO por desarrollo 13/11/2026.
   Hasta esa fecha estaba roto: el recurso de menu MMEXTRAE llamaba a
   una URL con la carpeta de app equivocada (`.../medid/medid/
   basesemcons/web/home//LanzarAplicativoDebug/`, 404 real del backend
   -confirmado con bypass de CORS via route.fetch()+fulfill(), no era
   un problema de headless ni de rol- la carpeta real desplegada
   siempre fue `extracsemes`, no `basesemcons`). Confirmado en vivo
   13/11/2026 tras el fix: LanzarAplicativoDebug y el endpoint
   obtener-semestres-contraste responden 200, el iframe #aplicacion
   SI aparece, y el combo #consultaSemestre llega SIN el aviso de
   semestre fijado, editable (no disabled), posicionado en el primer
   semestre del catalogo.

Campos reales (pantalla de RF-06, confirmados por esta via 13/11/2026):
#consultaSemestre (nz-select, igual de virtualizado que #codigoSemestre
de RF-05 - ver seleccionar_semestre_consulta), #consultaDescripcion
(solo lectura), #consultaFase, #consultaTipoContraste (nz-select),
radios de Opcion de Filtro, #consultaRuta + "Seleccionar carpeta..."
(modo Excel), #consultaNombreArchivo, radios Excel/Texto, botones
"Extraer...", "Cancelar", "Ayuda".
"""
import re


def abrir_base_semestral(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Base Semestral De Medidores'
    (RF-05) y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Comercial", "Base Semestral De Medidores"], "app-importacion-basesemestral", paso_excel=paso_excel)


def abrir_consulta_base_semestral_directo(page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Consulta Y Extraccion De Base
    Semestral' (RF-06, entrada directa por el recurso de menu MMEXTRAE,
    SIN pasar por RF-05/Detalles) y devuelve (app, frame) con el
    combo de Semestre editable (sin fijar). Requiere el fix de
    desarrollo del 13/11/2026 (ver ficha tecnica arriba) - antes de esa
    fecha esta entrada daba 404 real."""
    return abrir_aplicacion(page, ["Comercial", "Consulta Y Extraccion De Base Semestral"], "#consultaSemestre", paso_excel=paso_excel)


def seleccionar_semestre_consulta(app, frame, anno_sem_texto, max_scrolls=40, paso_scroll=150):
    """Igual que seleccionar_semestre() pero para el combo #consultaSemestre
    de RF-06 (entrada directa) - mismo patron virtualizado."""
    frame.locator("#consultaSemestre").click(force=True)
    app.wait_for_timeout(1000)
    opcion = frame.locator("nz-option-item", has_text=anno_sem_texto)
    if opcion.count():
        opcion.first.click(force=True)
        app.wait_for_timeout(1500)
        return
    viewport = frame.locator("cdk-virtual-scroll-viewport")
    viewport.first.evaluate("el => el.scrollTop = 0")
    app.wait_for_timeout(300)
    for _ in range(max_scrolls):
        if opcion.count():
            break
        viewport.first.evaluate(f"el => el.scrollTop += {paso_scroll}")
        app.wait_for_timeout(250)
    assert opcion.count(), f"No se encontro el semestre {anno_sem_texto!r} en el combo (ni visible ni tras scroll)"
    opcion.first.click(force=True)
    app.wait_for_timeout(1500)


def seleccionar_semestre(app, frame, anno_sem_texto, max_scrolls=40, paso_scroll=150):
    """Selecciona un semestre del combo #codigoSemestre (ej. '2003- S2').
    El combo esta virtualizado y es readonly (no se puede tipear para
    filtrar) - hace scroll incremental del viewport hasta encontrar la
    opcion, o usa las ~16 que ya estan visibles sin scrollear."""
    frame.locator("#codigoSemestre").click(force=True)
    app.wait_for_timeout(1000)
    opcion = frame.locator("nz-option-item", has_text=anno_sem_texto)
    if opcion.count():
        opcion.first.click(force=True)
        app.wait_for_timeout(1500)
        return
    viewport = frame.locator("cdk-virtual-scroll-viewport")
    viewport.first.evaluate("el => el.scrollTop = 0")
    app.wait_for_timeout(300)
    for _ in range(max_scrolls):
        if opcion.count():
            break
        viewport.first.evaluate(f"el => el.scrollTop += {paso_scroll}")
        app.wait_for_timeout(250)
    assert opcion.count(), f"No se encontro el semestre {anno_sem_texto!r} en el combo (ni visible ni tras scroll)"
    opcion.first.click(force=True)
    app.wait_for_timeout(1500)


def abrir_consulta_desde_detalles(app, frame):
    """Clickea 'Detalles...' en la pantalla de RF-05 (con un semestre ya
    seleccionado) y devuelve (app2, frame2) de la pantalla de Consulta
    de Base Semestral (RF-06) con el semestre fijado. OJO: esta
    pantalla NO usa iframe #aplicacion - frame2 es directamente la
    Page del popup."""
    with app.expect_popup(timeout=15000) as popup_info:
        frame.locator("button", has_text="Detalles").click(force=True)
    app2 = popup_info.value
    app2.wait_for_load_state("networkidle")
    app2.wait_for_timeout(3000)
    return app2, app2
