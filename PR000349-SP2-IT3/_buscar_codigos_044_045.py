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
        page.locator("a").filter(has_text=re.compile(r"^\s*Mantenedor De Inspectores De Corte\s*$", re.I)).first.click()
    app = popup_info.value
    app.wait_for_load_state("networkidle")
    app.wait_for_timeout(2000)
    frame = app.locator("#aplicacion").content_frame

    frame.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(800)
    overlay = frame.locator("[id^='cdk-overlay-']").last
    overlay.locator("#flt-codigo").fill("137")
    overlay.locator("#flt-estado").select_option(value="S")
    overlay.get_by_role("button", name=re.compile(r"^\s*Filtrar\s*$")).click()
    app.wait_for_timeout(2500)

    tabla = frame.locator("table.resultados tbody tr").filter(has_not_text=re.compile("Sin registros"))
    n = tabla.count()
    print(f"filtro codigo=137, Estado=Activos -> {n} filas")
    for i in range(n):
        celdas = tabla.nth(i).locator("td")
        print(" ", celdas.nth(1).inner_text().strip(), celdas.nth(2).inner_text().strip())
