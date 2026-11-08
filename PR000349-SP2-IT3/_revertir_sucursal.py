import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "DCABA_DW"
PASSWORD = "Melquisedec_01"

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

    campo = frame.locator("#numeroCliente")
    campo.click()
    campo.fill("1305674")
    app.wait_for_timeout(300)
    frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
    app.wait_for_timeout(2500)

    sucursal_actual = frame.locator("#sucursal").input_value()
    print("Sucursal actual:", repr(sucursal_actual))

    if sucursal_actual != "3100":
        campo_suc = frame.locator("#sucursal")
        campo_suc.click()
        campo_suc.fill("3100")
        app.wait_for_timeout(500)
        frame.locator("button", has_text=re.compile(r"^\s*Actualizar\s*$")).click()
        app.wait_for_timeout(2500)
        modal = frame.locator(".ant-modal, nz-modal-container").filter(has_text=re.compile(".", re.S))
        if modal.count() and modal.first.is_visible():
            print("Mensaje:", repr(modal.first.inner_text()))
            modal.first.get_by_role("button", name=re.compile("Aceptar", re.I)).click()
            app.wait_for_timeout(1000)

        frame.locator("button", has_text=re.compile(r"^\s*Leer\s*$")).click()
        app.wait_for_timeout(2500)
        print("Sucursal final:", repr(frame.locator("#sucursal").input_value()))
    else:
        print("Ya estaba en 3100, nada que hacer.")
