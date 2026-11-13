"""
encargos_cobranzaexterna.py - helpers y ficha tecnica para la pantalla
"Consulta de Cobranza Externa" (RF-03 de PR000349-SP9, modulo Encargos -
submodulo Cobranza).

Componente Angular raiz: <app-cobranzaexterna>
Ruta de menu real: Aplicaciones > Administrativo > "Consulta De
Cobranza Externa" (bajo "Administrativo", NO "Comercial" - confirmado
en vivo 11/11/2026, tras que el rol funcional AFILIACO fuera asignado a
DCABA_DW; antes de eso la pantalla no aparecia en ningun menu).

Campos reales:
  3 nz-select (input.ant-select-selection-search-input), ORDEN REAL
  (distinto del de Mantenedor de Orden de Pagos - NO asumir el mismo
  orden entre pantallas):
    [0] #operadorFecha  (Mayor o igual / Menor o igual / Igual a / Entre)
    [1] #encargo        combo de "Encargo de Cobranza".
    [2] #oficina        combo de "Oficina de Pago" - lista TODAS las
                         oficinas del sistema (no solo las que tienen
                         movimientos reales de pag_externo para el
                         encargo elegido); incluye la opcion "Todas".
  #fechaInicio / #fechaFin (type=date) - #fechaFin solo se habilita con
  operador "Entre".
  #totalTransacciones / #totalMonto (solo lectura).
  Boton "Buscar" dispara POST a .../api/... con {resumen, detalle,
  totalTransacciones, totalMonto}.

Gotcha real confirmado en vivo 11/11/2026: la data de pag_externo que
trae la matriz original (medida contra Desarrollo, encargo 0020 con
solo 21 movimientos en areas 0400/0300) NO coincide con Pruebas - el
mismo encargo 0020 en Pruebas tiene miles de movimientos reales
repartidos en oficinas totalmente distintas (Grandes Clientes 11.487,
Control Ventas 497) y su "Detalle por Producto" viene SIEMPRE VACIO
("La consulta no devolvió productos.") sin importar el rango de fechas
- no es un bug, el backend simplemente no tiene desagregado por
producto para ese encargo.

Dataset real reutilizable (confirmado en vivo 11/11/2026, estable -
son movimientos historicos, no datos que otras pruebas vayan a
modificar): Encargo `0006` (FOCOS AHORRADORES OSRAM), Oficina `Todas`,
Operador `Entre`, Fecha Inicio `2000-01-01`, Fecha Fin `2026-11-11` ->
resumen con 8 oficinas (Chacarilla 540/11204, Miraflores 2375/41632,
La República 1848/31598, Pedro Miotta 544/8718, San Juan 1082/17538,
+3 mas) y detalle con 2 productos (Focos 16 w: 7427/89124.0, Focos 20
W: 9217/121734.0); totalTransacciones=12433, totalMonto=210858. Al ser
historico (nada en el proyecto escribe pag_externo), estos numeros son
estables entre corridas.
"""
import re


def abrir_cobranza_externa(page, paso_excel=None):
    """Navega Aplicaciones > Administrativo > 'Consulta De Cobranza
    Externa' y devuelve (app, frame)."""
    return abrir_aplicacion(page, ["Administrativo", "Consulta De Cobranza Externa"], "app-cobranzaexterna", paso_excel=paso_excel)


def consultar_cobranza_externa(app, frame, codigo_encargo, oficina, operador_fecha, fecha_inicio, fecha_fin=None):
    """Selecciona Encargo (por codigo, ej. '0006'), Oficina (por texto
    visible, ej. 'Todas'), Operador de Fecha y la(s) fecha(s), y
    clickea 'Buscar'. Si operador_fecha es 'Entre', fecha_fin es
    obligatoria (se ignora si se pasa con otro operador). Devuelve el
    cuerpo real (dict) de la respuesta."""
    frame.locator("app-cobranzaexterna").wait_for(timeout=20000)
    frame.locator("#encargo").click(force=True)
    app.wait_for_timeout(1000)
    frame.locator("nz-option-item", has_text=codigo_encargo).first.click(force=True)
    app.wait_for_timeout(1500)

    frame.locator("#oficina").click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=re.compile(r"^\s*" + re.escape(oficina) + r"\s*$")).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#operadorFecha").click(force=True)
    app.wait_for_timeout(800)
    frame.locator("nz-option-item", has_text=operador_fecha).first.click(force=True)
    app.wait_for_timeout(500)

    frame.locator("#fechaInicio").fill(fecha_inicio)
    if operador_fecha == "Entre" and fecha_fin:
        frame.locator("#fechaFin").fill(fecha_fin)
    app.wait_for_timeout(500)

    with app.expect_response(lambda r: "/api/" in r.url, timeout=25000) as resp_info:
        frame.locator("button", has_text="Buscar").click(force=True)
    app.wait_for_timeout(1500)
    return resp_info.value.json()
