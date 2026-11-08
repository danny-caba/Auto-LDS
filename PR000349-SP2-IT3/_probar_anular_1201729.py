import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "DCABA_DW"
PASSWORD = "Melquisedec_01"
OUT = Path(__file__).parent / "_dump_anular"
OUT.mkdir(exist_ok=True, parents=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    context = browser.new_context(viewport={"width": 1700, "height": 1100})
    page = context.new_page()
    page.goto(URL)
    page.wait_for_function("document.querySelector('#servidor')?.value", timeout=15000)
    page.wait_for_function("document.querySelector('#Dominios')?.options?.length > 0", timeout=15000)
    page.get_by_role("textbox", name="Usuario").click()
    page.get_by_role("textbox", name="Usuario").fill(USUARIO)
    page.get_by_role("textbox", name="Usuario").press("Tab")
    page.get_by_role("textbox", name="Contraseña").fill(PASSWORD)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Ingresar ").click()
    page.wait_for_load_state("networkidle")

    page.get_by_role("link", name="  Aplicaciones").click(timeout=30000)
    page.wait_for_timeout(800)
    page.locator("a").filter(has_text=re.compile(r"^\s*Comercial\s*$")).first.click()
    page.wait_for_timeout(800)
    with page.expect_popup(timeout=15000) as popup_info:
        page.locator("a").filter(has_text=re.compile(r"^\s*Mantenimiento De Ordenes De Conexion\s*$", re.I)).first.click()
    app = popup_info.value
    app.wait_for_load_state("networkidle")
    app.wait_for_timeout(2000)
    frame = app.locator("#aplicacion").content_frame

    respuestas = []
    app.on("response", lambda r: respuestas.append((r.status, r.url, r.text())) if "mantord" in r.url.lower() else None)

    campo = frame.locator("#numeroCliente")
    campo.click()
    campo.fill("1201729")
    app.wait_for_timeout(300)
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2500)
    print("ANTES -> anulado?:", [r for r in respuestas if "leer" in r[1].lower()][-1][2][:400])

    radios = frame.locator("input[type=radio]")
    radios.nth(1).click(force=True)
    app.wait_for_timeout(500)

    boton_anular = frame.locator("button", has_text=re.compile(r"^\s*Anular\s*$"))
    print("Anular enabled:", boton_anular.is_enabled())
    boton_anular.click()
    app.wait_for_timeout(1500)
    app.screenshot(path=str(OUT / "confirmacion.png"), full_page=True)
    frame.get_by_role("button", name=re.compile(r"^\s*Aceptar\s*$")).click()
    app.wait_for_timeout(3000)
    app.screenshot(path=str(OUT / "resultado.png"), full_page=True)

    texto = frame.locator("body").inner_text()
    print()
    print("Texto tras Anular:")
    print(texto[-600:])

    print()
    print("--- respuestas de red /mantord/ ---")
    for status, url, body in respuestas:
        print(status, url)
        print("  ", body[:400])
