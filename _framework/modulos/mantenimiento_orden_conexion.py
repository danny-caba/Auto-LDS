"""
Modulo: Mantenimiento de Ordenes de Conexion (Web LDS)
Componente Angular: app-mantord
Ruta de menu confirmada en vivo: Comercial > Mantenimiento De Ordenes De Conexion
Sistema/frente de negocio: Gestion de Clientes / Acticome (NUCLI)

Este archivo es el INSUMO reutilizable para generar casos de prueba de
este modulo en CUALQUIER proyecto/sprint que vuelva a tocarlo - no
depende de ningun proyecto puntual.

============================================================================
FICHA TECNICA (confirmado en vivo, PR000349-SP2, 28/10/2026)
============================================================================

**Backend confirmado operativo el 28/10/2026** - en una corrida anterior
(28/09/2026) esta pantalla daba error 503 y quedo documentada como
"backend caido"; un mes despues, misma cuenta, carga y responde
perfecto. Antes de asumir un defecto de infraestructura permanente,
reintentar en una sesion nueva (mismo patron ya documentado en el
checklist para RF-09/RF-10 de PR000349-SP1).

Requiere rol funcional con permiso sobre SRV.MANTORD - la matriz de
roles con permiso vigente sobre este recurso incluye 88 roles (ADMINIST,
CONSCLIE, JEFESUCU, GERENTE, INSPECT, RELNUCLI, entre otros). Confirmado
que DCABA_DW tiene acceso (SCASTI_DW no se probo especificamente para
este RF).

**Selectores reales**: `#numeroCliente` (input de texto), botones por
texto exacto Limpiar/Anular/Actualizar/Leer (Anular y Actualizar
deshabilitados hasta Leer). El resultado de Leer puede ser:
1. Un dialogo `.ant-modal`/`nz-modal-container` ("Ventana de
   Validacion") si NO se encontro orden, o si la orden esta bloqueada
   por un proceso externo.
2. La orden cargada SIN dialogo, con sus secciones "ORDEN DE CONEXION"
   (Nombre/Direccion/Rol de Creacion/etc.) y "PROCEDIMIENTOS/MENSAJES DE
   ENRUTAMIENTO" pobladas.

**Mensajes reales confirmados** (coinciden exacto con el EF):
- Sin orden: "No se encontró Orden de Conexión del Cliente."
- Orden generada por ACTICOME (bloqueada): "El NUCLI fue generado por
  el ACTICOME, favor trabajar en dicho módulo" - confirmado en vivo con
  clientes reales 1830410, 1764523, 1920482.
- Orden de otro usuario (no creador, sin privilegio de edicion ajena):
  tras Leer, NO aparece ningun dialogo - la orden carga directo con el
  texto "Ud. no ingresó la Orden de Conexión. Sólo puede consultar" en
  la seccion de resultado, y los botones Anular/Actualizar quedan
  deshabilitados. Confirmado en vivo con clientes reales 1259207 y
  1415959.

**Gotcha de busqueda de datos**: NO hay forma de listar/filtrar ordenes
desde esta pantalla (exige un numero de cliente puntual). Para encontrar
clientes en cada estado (sin orden / orden ajena / orden propia /
anulada), escanear una lista de clientes ya conocidos del proyecto via
Leer real (igual metodo que PR000349-SP1 con ValidarCliente) en vez de
perseguir el esquema SQL real primero.

**PENDIENTE SIN RESOLVER (confirmado 28/10/2026, documentado tambien en
la propia matriz de casos del cliente)**: no se encontro ningun cliente
real cuya orden de conexion haya sido CREADA por la cuenta de prueba
(DCABA_DW/SCASTI_DW) - la propia matriz Excel ya trae una nota de
Desarrollo: "no se encontró dato real que la satisfaga; nucli.rol_creacion
nunca coincide". Sin este dato no se puede automatizar CP009 (Leer
exitoso como creador) ni los casos de Actualizar/Anular que dependen de
serlo (CP012/013/014/015/016) salvo via el camino de usuario privilegiado
(rol JEFESUCU, ver CP072) o consiguiendo el dato por otra via (BD,
Desarrollo). Tampoco se encontro ningun cliente con orden YA ANULADA
(CP011) en el escaneo inicial de ~25 clientes conocidos del proyecto.
"""

import re


def abrir_mantord(page, paso_excel=None):
    return abrir_aplicacion(page, ["Comercial", "Mantenimiento De Ordenes De Conexion"], "app-mantord", paso_excel=paso_excel)


def leer_orden(app, frame, numero_cliente):
    """Escribe el numero de cliente y pulsa Leer. Si aparece un dialogo
    de Ventana de Validacion, lo cierra y devuelve su texto; si la orden
    carga directo (sin dialogo), devuelve None."""
    campo = frame.locator("#numeroCliente")
    campo.click()
    campo.fill("")
    campo.fill(str(numero_cliente))
    app.wait_for_timeout(300)
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2000)
    modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
    if modal.count() and modal.first.is_visible():
        mensaje = modal.first.inner_text()
        modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
        app.wait_for_timeout(500)
        return mensaje
    return None


def limpiar(app, frame):
    boton = frame.locator("button", has_text=re.compile(r"^\s*Limpiar\s*$"))
    for _ in range(15):
        if boton.is_enabled():
            boton.click()
            return
        app.wait_for_timeout(500)
