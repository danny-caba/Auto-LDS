# Índice de conocimiento (generado — no editar a mano)

_Actualizado: 2026-11-06T05:36:57.036121_

## Conocimiento general

  _(sin entradas todavia)_

## Conocimiento por módulo


### atencion-integral-informacion-general

- **CONO-0007** [VERIFICADO] — Cliente de Pruebas reutilizable para la pantalla Informacion General: numero 15 = TOWER AND TOWER S.A. (RUC 20380618797)... _(fuente: Exploracion en vivo 31/10/2026 + corrida real CP001/CP002)_
- **CONO-0008** [VERIFICADO] — La pantalla "Atencion Integral" (Comercial > Atencion Integral Al Cliente > Consulta De Clientes > Atencion Integral) ti... _(fuente: Exploracion en vivo 31/10/2026)_
- **CONO-0009** [VERIFICADO] — La ruta de menu real para Informacion General NO es la que sugiere el texto corto del EF ("Atencion Integral" a secas) -... _(fuente: Exploracion en vivo 31/10/2026 (_exploracion/explore_03 a explore_17))_

### consulta-producto-local

- **CONO-0001** [VERIFICADO] — En la pantalla de consulta de producto (pagina de juguete _exploracion/pagina_local_ejemplo.html), page.fill('#codigo', ... _(fuente: Etapa 4 - validar_intervencion_local.py (casos CPL01/CPL02, ambos APROBADO))_
- **CONO-0002** [INVALIDADO] — [ENTRADA DE PRUEBA - solo para validar el mecanismo de invalidacion de la Etapa 5, no es conocimiento real del proyecto]... _(fuente: validar_memoria_local.py (fixture de prueba))_

### framework-general

- **CONO-0010** [VERIFICADO] — Pantallas LEGACY (jQuery/DataTables, sin Angular) nunca llegan a 'networkidle' - usar wait_for_load_state('load') + un w... _(fuente: Memoria de sesion - gotchas acumulados de automatizacion Web LDS)_
- **CONO-0011** [VERIFICADO] — Las tablas legacy estilo DataTables mantienen TODAS las filas en el DOM sin importar la paginacion visual - 'tbody tr' c... _(fuente: Memoria de sesion - gotchas acumulados de automatizacion Web LDS)_
- **CONO-0012** [VERIFICADO] — Overlays/modales de ng-zorro (nz-modal-container, cdk-overlay-*): puede haber mas de un overlay coexistiendo (incluyendo... _(fuente: Memoria de sesion - gotchas acumulados de automatizacion Web LDS)_
- **CONO-0013** [VERIFICADO] — Selects/nz-select de un formulario pueden nacer con disabled='' hasta que termina de cargar su catalogo via un servicio ... _(fuente: Memoria de sesion - gotchas acumulados de automatizacion Web LDS)_
- **CONO-0014** [VERIFICADO] — Mensajes de exito/error pueden aparecer como toast EFIMERO (no un modal persistente) - hay que sondear activamente (bucl... _(fuente: Memoria de sesion - gotchas acumulados de automatizacion Web LDS)_
- **CONO-0015** [VERIFICADO] — Al automatizar flujos de Ingresar/Eliminar (altas y bajas), el caso debe confirmar la alta/baja REAL de esa misma corrid... _(fuente: Memoria de sesion - convencion establecida tras varios falsos OK)_
- **CONO-0016** [PROVISIONAL] — Validar el status code HTTP real del backend (via app.on('response', ...)) solo en casos de error/validacion o cuando el... _(fuente: Memoria de sesion - feedback de usuario sobre cuando vale la pena)_
- **CONO-0017** [VERIFICADO] — El selector de sucursal de una pantalla se activa cuando el centro_servicio del area asociada al ROL del usuario tiene 2... _(fuente: Memoria de sesion - investigacion en vivo multi-sucursal (varios proyectos))_
- **CONO-0018** [VERIFICADO] — La VM bloquea pip/npm install por un proxy MITM (error SELF_SIGNED_CERT_IN_CHAIN) - para consultas a la BD Informix de W... _(fuente: Memoria de sesion - acceso a BD Informix)_
- **CONO-0021** [PROVISIONAL] — La cuenta SCASTI_DW (clave rotativa, ver generate_scripts.py de cada proyecto para la vigente) es reutilizable entre pro... _(fuente: Memoria de sesion - cuentas de prueba reutilizables)_

### mac-atencion-integral

- **CONO-0020** [VERIFICADO] — El modulo MAC (Atencion Integral MAC) tuvo un 'Acceso Denegado' real por permiso faltante - quedo corregido del lado de ... _(fuente: Memoria de sesion - PR000335-SP5 cierre RF-04)_

### synergia-reclamos

- **CONO-0019** [PROVISIONAL] — Tablas reales de Synergia Reclamos (schema BD): csc_reclamo, csc_rclmo_est_act, csc_rclmo_req_adm, csc_acuerdo, cs_opera... _(fuente: Memoria de sesion - investigacion BD Synergia Reclamos)_

## Datos de prueba

- **CONO-0007** [VERIFICADO] — Cliente de Pruebas reutilizable para la pantalla Informacion General: numero 15 = TOWER AND TOWER S.A. (RUC 20380618797)... _(fuente: Exploracion en vivo 31/10/2026 + corrida real CP001/CP002)_
- **CONO-0019** [PROVISIONAL] — Tablas reales de Synergia Reclamos (schema BD): csc_reclamo, csc_rclmo_est_act, csc_rclmo_req_adm, csc_acuerdo, cs_opera... _(fuente: Memoria de sesion - investigacion BD Synergia Reclamos)_
- **CONO-0021** [PROVISIONAL] — La cuenta SCASTI_DW (clave rotativa, ver generate_scripts.py de cada proyecto para la vigente) es reutilizable entre pro... _(fuente: Memoria de sesion - cuentas de prueba reutilizables)_

## Intervenciones

  _(sin entradas todavia)_

## Dudas pendientes

  _(sin entradas todavia)_
