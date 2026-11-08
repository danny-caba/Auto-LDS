import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://pldsweb.luzdelsur.com.pe/Plataforma/PlataformaWeb"
USUARIO = "DCABA_DW"
PASSWORD = "Melquisedec_01"
OUT = Path(__file__).parent / "_dump_cp047"
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
        page.locator("a").filter(has_text=re.compile(r"^\s*Mantenedor De Inspectores De Corte\s*$", re.I)).first.click()
    app = popup_info.value
    app.wait_for_load_state("networkidle")
    app.wait_for_timeout(2000)
    frame = app.locator("#aplicacion").content_frame

    app.screenshot(path=str(OUT / "pantalla_inicial.png"), full_page=True)
    texto = frame.locator("body").inner_text()
    print("--- texto completo inicial ---")
    print(texto[:1500])

    print()
    print("--- selects visibles ---")
    selects = frame.locator("select, nz-select")
    for i in range(selects.count()):
        s = selects.nth(i)
        if s.is_visible():
            print(f"  idx={i} id={s.get_attribute('id')!r} class={s.get_attribute('class')!r}")
