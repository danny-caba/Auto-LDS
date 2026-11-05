"""
Modulo: Mantenedor de Inspectores de Corte (Web LDS)
Ruta de menu confirmada en vivo: Comercial > Mantenedor De Inspectores De Corte
Sistema/frente de negocio: Cortes y Reconexiones (corterepos)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/09/2026)
============================================================================

Requiere el rol funcional ANDESE1 - no visible en el menu para SCASTI_DW.
Se exploro y valido con DCABA_DW/Melquisedec_01.

Pantalla principal (`app-inspectores-listado`) SIN ningun `id` en sus
elementos - toca localizar todo por rol/texto. Botones: Leer / Siguientes
/ Filtrar / Limpiar / Agregar / Detalles / Eliminar / Excel / Imprimir.
Checkboxes: "Ampliar campos" y "Marcar todos" (label, no id). Grilla
`table.resultados` con placeholder `td.sin-datos` cuando esta vacia.

**Ventana de Filtro**: es un modal ng-zorro (`nz-modal-container`, dentro
de un `[id^="cdk-overlay-"]`) SI tiene ids: `#flt-codigo`, `#flt-ficha`,
`#flt-nombre`, `#flt-proveedor` (select), `#flt-estado` (select: ""=Todos,
"S"=Activos, "N"=Noactivos), `#flt-sucursal` (select). Botones Filtrar/
Limpiar/Cerrar DENTRO del overlay (hay 2 botones "Filtrar" en el DOM a la
vez - el de la pantalla principal y el del modal - hay que ESCOPEAR el
locator al overlay, si no Playwright tira "strict mode violation").

**Gotcha de carga asincrona**: `#flt-proveedor` y `#flt-sucursal` nacen
con `disabled=""` hasta que termina de cargar su catalogo (servicio
async) - si se lee `option` antes de que se habiliten, solo aparece
"-- Todos --"/"-- Todas --". Esperar a `is_enabled()` antes de leer o
elegir una opcion (`#flt-estado` si tiene sus opciones fijas desde el
inicio, no necesita esta espera).

**DEFECTO REAL MAYOR 1/2 confirmado en vivo 02/11/2026 (filas duplicadas
en la grilla de resultados)**: el backend de Leer/Filtrar devuelve el
mismo inspector repetido muchas veces en vez de una fila por inspector -
confirmado con Proveedor = Luz del Sur (20331898008) + Estado =
Noactivos: el primer bloque de 100 filas tiene solo 4 codigos reales
distintos (922, 315, 314, 305), repetidos 13-29 veces cada uno, fila
por fila identica. Esto es consistente con un `JOIN` del backend que
multiplica filas sin deduplicar, y explica tambien por que el filtro
por defecto (Estado=Activos, ver CP039) siempre excede el limite de
2000 registros admitidos por la grilla - el conteo real de inspectores
distintos es probablemente mucho menor, pero el backend cuenta las
filas duplicadas. Afecta la confiabilidad de CUALQUIER conteo o
paginacion en esta pantalla - no es un problema puntual de un filtro.

**DEFECTO REAL MAYOR 2/2 confirmado en vivo 02/11/2026 ("Siguientes"
ignora el filtro vigente)**: agregando Sucursal = Chacarilla (3100) al
filtro anterior (Proveedor=Luz del Sur + Estado=Noactivos), el PRIMER
bloque de 100 filas SI viene correcto (todas Estado=NoActivo,
Sucursal=Chacarilla, pie "100 de 116"). Al presionar **Siguientes**, el
pie salta a "200 de 116" (incoherente con el propio total declarado) y
las filas NUEVAS que agrega son Estado=Activo y Sucursal="0000 - Sin
Sucursal" - datos de un filtro completamente distinto - mientras la
etiqueta "Filtro vigente" sigue mostrando el filtro original sin avisar
del cambio. Conclusion: Siguientes NO reusa el filtro de la consulta
original, trae la pagina siguiente de una consulta distinta (posiblemente
sin filtro, o del ultimo filtro "por defecto"). Ambos defectos (1 y 2)
hacen que CUALQUIER resultado con mas de 1 pantalla de datos en esta
grilla sea potencialmente no confiable.

**RN-01 confirmado**: al abrir, filtro vigente = "Estado = Activos", SIN
consulta automatica. Botones Siguientes/Limpiar/Detalles/Eliminar/Excel/
Imprimir arrancan `disabled`. Leer/Filtrar/Agregar SI estan habilitados.

**HALLAZGO REAL IMPORTANTE - contradice el supuesto de la matriz para
CP039**: presionar "Leer" con el filtro por defecto (Estado=Activos, SIN
ningun otro filtro) da "Demasiados registros para ser mostrados en la
grilla." (RN-03) - el universo REAL de inspectores activos en Pruebas
supera el limite de 2000 registros. Lo mismo pasa con Estado=Noactivos
solo (tambien >2000). La matriz asumia que el filtro por defecto ya
devolveria un resultado dentro del limite (CP039 "Leer listado con
resultados dentro del límite") - en la practica, SIEMPRE hay que combinar
el default con al menos un filtro adicional (via Filtrar) para quedar
debajo del limite. Documentar como observacion de datos/ambiente, no
como bug de esta automatizacion.

**RN-05 (Filtrar restablece el filtro vigente) confirmado**: tras
CUALQUIER Filtrar (haya o no resultados), el filtro vigente vuelve a
"Estado = Activos" - un "Leer" posterior YA NO reutiliza el filtro recien
aplicado (confirmado: el resultado de Filtrar queda en pantalla, pero el
texto "Filtro vigente" ya volvio a mostrar el default apenas se cierra el
modal).

**Mensajes reales confirmados** (modal "Ventana de Validación", boton
"Aceptar"):
- "Demasiados registros para ser mostrados en la grilla." (RN-03, sin
  filtro suficiente)
- "No existen registros para las condiciones indicadas." (RN-03, filtro
  sin coincidencias - ej. Código="ZZZ999NOEXISTE")

**RN (Código y Ficha simultaneos, CP042) confirmado tal cual el EF**: si
se completan Código Y Ficha a la vez, Ficha GANA por completo - el
resultado corresponde solo al filtro de Ficha, y el texto "Filtro
vigente" muestra literalmente "Código" (la etiqueta fija, SIN el valor
tecleado) en vez de "Código = <valor>" - ej.:
"Filtro vigente: Estado = Activos | Ficha = 4504 | Código" (nunca
"Código = 1"). Confirmado con Código="1" + Ficha="4504" -> unico
resultado real: inspector 1381 (Rodriguez Medina Abel, Ficha 4504).

**OBSERVACION (no confirmada como defecto): filas duplicadas en la
grilla**. Al filtrar por Código="1" (coincidencia parcial), la grilla
devuelve los codigos reales 1378/1379/1380/1381 - pero cada codigo
aparece MULTIPLES veces como fila identica (mismos valores en todas las
columnas, no son inspectores distintos). Podria ser data real asi en
Pruebas (registros duplicados de verdad, ej. uno por sucursal en un Alta
"Todas las sucursales" - ver RN de CP047) o un comportamiento del backend
a confirmar con mas informacion - NO se concluye como bug, solo se deja
anotado.

**Estado=Todos - la etiqueta "Filtro vigente" NO SE ACTUALIZA visualmente
(sigue diciendo "Estado = Activos")** aunque el `<select>` interno SI
quedo en "" (Todos) y el resultado real parece incluir codigos que no se
habian visto en la busqueda solo-Activos-con-Codigo=1 (1378/1379/1380
ademas de 1381) - no se pudo confirmar la presencia de una fila
REALMENTE Inactiva en los primeros 100 registros para poder probar CP043
(marcado individual solo permite Activas) con datos 100% reales; queda
pendiente explorar mas o usar otro codigo/filtro.

**Alta/Modificacion/Eliminacion (CP044-048) son operaciones de
ESCRITURA real sobre Pruebas** (dan de baja, crean o modifican
inspectores reales) - no se ejecutan sin coordinar antes con el usuario,
a diferencia de las consultas de solo lectura de este modulo.

**Baja individual y masiva (CP044/CP045) CONFIRMADAS FUNCIONALES en vivo
02/11/2026** con codigos reales indicados explicitamente por el usuario
en cada corrida (301 para individual; 303+304 para masiva) - ver
secuencia completa (incluye el 2do overlay "Modo: Baja" y el boton de
confirmacion real `button.conf-btn-ok`) en
_exploracion/explore_55_56_rf06_eliminar_2408.py (primer hallazgo,
28/09) y las corridas reales de CP044/CP045 en PR000349-SP2
(generate_scripts.py). **Para marcar 2+ codigos especificos a la vez
(mass delete) cuando el filtro Codigo exacto solo admite 1 valor**:
usar un prefijo parcial (ej. "30") + Estado=Activos, y si los codigos
buscados no aparecen en el primer bloque de 100, presionar Siguientes
una vez (confirmado que el bloque acumulado de 200 SI trae codigos
distintos del prefijo) - cuidado de marcar EXCLUSIVAMENTE las filas de
los codigos buscados, el bloque trae varios codigos mezclados.
Sigue sin existir forma de generar un inspector descartable NUEVO
(Alta bloqueada, ver CP046/047) ni de revertir una baja - cada corrida
real de CP044/CP045 consume codigos reales que no vuelven a estar
disponibles, asi que para repetir estos casos en el futuro hace falta
que el usuario indique codigos Activos nuevos cada vez.
============================================================================
"""

import re
from playwright.sync_api import TimeoutError as PWTimeoutError


def abrir_mantenedor_inspectores(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenedor De Inspectores De Corte"], "app-inspectores-listado", paso_excel=paso_excel)


def abrir_filtro_inspectores(app, frame):
    frame.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(800)
    return frame.locator("[id^='cdk-overlay-']").last


def aplicar_filtro_inspectores(app, overlay, codigo=None, ficha=None, nombre=None, estado_index=None, sucursal_label=None):
    if codigo is not None:
        overlay.locator("#flt-codigo").fill(codigo)
    if ficha is not None:
        overlay.locator("#flt-ficha").fill(ficha)
    if nombre is not None:
        overlay.locator("#flt-nombre").fill(nombre)
    if estado_index is not None:
        overlay.locator("#flt-estado").select_option(index=estado_index)
    if sucursal_label is not None:
        overlay.locator("#flt-sucursal").select_option(label=sucursal_label)
    app.wait_for_timeout(300)
    overlay.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(2000)


def cerrar_modal_inspectores(frame, boton="Aceptar"):
    boton_locator = frame.get_by_role("button", name=re.compile(rf"^\s*{boton}\s*$"))
    if boton_locator.count() > 0 and boton_locator.first.is_visible():
        boton_locator.first.click()
        return True
    return False


def filas_inspectores(frame):
    return frame.locator("table.resultados tbody tr").filter(has_not_text=re.compile("Sin registros"))
