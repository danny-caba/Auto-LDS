"""
encargos_fonavi.py - helpers y ficha tecnica para la pantalla
"Informacion FONAVI" (RF-01 de PR000349-SP9, modulo Encargos - submodulo
Cobranza).

Componente Angular raiz: <app-fonavi>
Ruta de menu real: Aplicaciones > Comercial > "Informacion Fonavi"
(aparece directo en el arbol de Comercial, sin categoria intermedia -
confirmado en vivo 10/11/2026). Abre en popup con iframe #aplicacion,
igual que cualquier otra app de Web LDS.

Campos reales (solo 4 tienen id - el resto de la pantalla, Nombre,
Direccion, Tipo de Cliente, Categoria, Sucursal, Distrito y los datos
del proyecto/cuotas/importe/mora, son de solo lectura SIN id: no hay
forma confiable de leerlos por selector, hay que verificar via la
respuesta real de la API en vez del DOM):
  #numeroCliente                input, placeholder "Ej. 10458231"
  #digitoVerificador             input, 1 caracter
  #numeroIdentidadRepresentante  input, solo se usa para emitir constancia
  #nombreRepresentante           input, solo se usa para emitir constancia

Botones: "Leer" (dispara la consulta), "Imprimir" (emite constancia,
descarga archivo), "Cancelar" (limpia todo el formulario).

Estados de habilitacion confirmados en vivo 10/11/2026:
- "Leer": deshabilitado si #numeroCliente esta vacio - se habilita con
  CUALQUIER valor en ese campo, sin necesitar el digito verificador
  todavia (el DV solo se valida/usa al clickear Leer, no antes).
- "Imprimir": deshabilitado hasta que #numeroIdentidadRepresentante Y
  #nombreRepresentante tengan valor (ademas de haber consultado antes
  con exito - sin una consulta previa el boton tampoco se habilita).

Gotcha real confirmado en vivo 10/11/2026: la matriz dice "se dispara la
consulta automaticamente" tras ingresar el digito verificador, pero en
la pantalla real hace falta clickear el boton "Leer" explicitamente -
un Tab o un Enter en #digitoVerificador NO dispara nada (0 llamadas de
red capturadas en ninguno de los 2 casos). Siempre clickear "Leer"
despues de llenar ambos campos, nunca asumir que el blur alcanza.

Validacion del digito verificador: es 100% client-side (NUNCA llega a
tocar la red si el DV no corresponde al algoritmo real del numero de
cliente) - confirmado con el cliente 1006406 (DV real=6), probando con
DV=5: 0 llamadas a la API, aparece directo la "Ventana de Validacion":
"El dígito verificador no corresponde al N.° de Cliente ingresado." Los
campos NO se limpian en este caso (a diferencia de un cliente sin
registro FONAVI, que SI limpia #numeroCliente tras el error).

Endpoints reales confirmados (API real del backend, no documentada en
el EF):
  .../api/fonavi/obtener-informacion-fonavi
      Dispara al clickear "Leer" con ambos campos llenos y el DV
      correcto. Body real exitoso (cliente CON registro FONAVI):
      {"nombre":..., "direccion":..., "rutaLectura":..., "tipoCliente":...,
      "categoria":..., "sucursal":..., "distrito":..., "numeroProyecto":...,
      "nombreProyecto":..., "cuotas":N, "importe":N, "mora":N, "historial":[...]}
      Body real SIN registro FONAVI (HTTP 200, no es un error de
      transporte): {"sinDatos":true,"mensajeUsuario":"No existe datos
      del FONAVI para el cliente."} - la pantalla lo muestra como
      "Ventana de Validacion" igual que un error de verdad.
  .../api/fonavi/exportar-constancia-fonavi
      Dispara al clickear "Imprimir" con los datos del representante
      completos. Descarga real confirmada: archivo de texto plano
      "ConstanciaFonavi_<numeroCliente>.txt" con el texto formal de la
      constancia (fecha, datos del cliente, proyecto, referencia al
      Decreto Supremo N° 041-99-EF).

Datos de prueba reutilizables (confirmados en vivo 10/11/2026, coinciden
con lo que ya trae la matriz):
- Cliente CON registro FONAVI: numero 1006406, DV 6 -> ALVAREZ LANCHIPA
  NOLBERTO FERNANDO, sucursal "Pedro Miotta", Villa El Salvador, proyecto
  880333 "A.H. V.SALV. VI ST. GPO. 1 (D.S.#Ol0)", 40 cuotas, importe
  334.30, mora 15.22, historial vacio (0 constancias previas emitidas).
- Cliente SIN registro FONAVI (para CP002): numero 1, DV 9 (NO usar
  DV=0 - es un valor historico de una numeracion de cliente antigua, ya
  invalido bajo el algoritmo de DV actual segun la propia nota de la
  matriz v1.9).
"""
import re


def abrir_fonavi(app_o_page, paso_excel=None):
    """Navega Aplicaciones > Comercial > 'Informacion Fonavi' y devuelve
    (app, frame) con el popup + iframe #aplicacion listos."""
    return abrir_aplicacion(app_o_page, ["Comercial", "Informacion Fonavi"], "app-fonavi", paso_excel=paso_excel)


def consultar_cliente_fonavi(app, frame, numero_cliente, digito_verificador):
    """Llena numeroCliente + digitoVerificador y clickea 'Leer'. Devuelve
    (datos, mensaje_dialogo):
    - Consulta valida con registro FONAVI: (dict real de la API, None).
    - Cliente sin registro FONAVI, o DV incorrecto (nunca toca la red):
      (None, texto real del dialogo de error, ya cerrado con Aceptar).

    Gotcha real confirmado en vivo 10/11/2026: con slow_mo+video activos
    (run_all.py real), un listener 'response' + wait_for_timeout fijo
    llega tarde la mayoria de las veces (la respuesta real demora mas de
    lo que tarda el wait bajo esas condiciones) - usar expect_response(),
    que espera de forma determinista en vez de adivinar un timeout, es
    el fix. El DV invalido NUNCA dispara el request (validacion
    client-side), asi que expect_response() se arma solo si hace falta."""
    frame.locator("#numeroCliente").fill(str(numero_cliente))
    frame.locator("#digitoVerificador").fill(str(digito_verificador))

    try:
        with app.expect_response(lambda r: "obtener-informacion-fonavi" in r.url, timeout=10000) as resp_info:
            frame.locator("button", has_text="Leer").click(force=True)
        cuerpo = resp_info.value.json()
    except PWTimeoutError:
        cuerpo = None

    dialogo = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile("Ventana de Validación"))
    if dialogo.count() and dialogo.first.is_visible():
        mensaje = dialogo.first.inner_text()
        dialogo.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click(force=True)
        app.wait_for_timeout(500)
        return None, mensaje

    if cuerpo and not cuerpo.get("sinDatos"):
        # respiro: el estado disabled de Imprimir se recalcula un
        # instante despues de que la respuesta llega (confirmado en vivo
        # 10/11/2026 - sin esto, CP006 ve Imprimir todavia habilitado
        # por el frame anterior al cambio de deteccion de Angular).
        app.wait_for_timeout(1500)
        return cuerpo, None
    if cuerpo and cuerpo.get("sinDatos"):
        return None, cuerpo.get("mensajeUsuario")
    return None, None


def emitir_constancia_fonavi(app, frame, numero_identidad, nombre_representante):
    """Llena los datos del representante y clickea 'Imprimir'. Devuelve
    el objeto Download real de Playwright (espera la descarga real,
    hasta 10s)."""
    frame.locator("#numeroIdentidadRepresentante").fill(numero_identidad)
    frame.locator("#nombreRepresentante").fill(nombre_representante)
    boton = frame.locator("button", has_text="Imprimir")
    with app.expect_download(timeout=10000) as descarga_info:
        boton.click(force=True)
    return descarga_info.value
