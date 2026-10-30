"""
Servidor web local (SOLO libreria estandar de Python, sin Flask/FastAPI -
ver README.md de esta carpeta para el por que) que envuelve el flujo de
automatizacion LDS: subir los 3 documentos de un proyecto, disparar el
bootstrap + exploracion/generacion con IA, ejecutar las pruebas filtradas
por RF, y mostrar el reporte consolidado.

Uso:
    .venv\\Scripts\\python.exe _framework\\webapp\\server.py
    (por defecto en http://127.0.0.1:8765 - configurable con la variable
    de entorno WEBAPP_PORT)

No expone nada a la red (bind explicito a 127.0.0.1) - es una
herramienta de un solo usuario en esta misma maquina.
"""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado  # noqa: E402
import multipart  # noqa: E402
import procesos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent.parent  # C:\AUTOMATIZACION_LDS
WEBAPP_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEBAPP_DIR / "static"
UPLOADS_DIR = WEBAPP_DIR / "_uploads"
PUERTO = int(os.environ.get("WEBAPP_PORT", "8765"))

_RE_PROYECTO = re.compile(r"^PR\d{6}(-SP\d+)?$")

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _validar_proyecto(nombre: str) -> str:
    if not _RE_PROYECTO.match(nombre):
        raise ValueError(f"Nombre de proyecto invalido: {nombre!r} (esperado tipo PR000456 o PR000456-SP1)")
    return nombre


def _reporte_mas_nuevo(pdir: Path) -> Path | None:
    reportes_dir = pdir / "reportes"
    if not reportes_dir.exists():
        return None
    candidatos = sorted(reportes_dir.glob("reporte_consolidado_*.json"))
    return candidatos[-1] if candidatos else None


class Handler(BaseHTTPRequestHandler):
    server_version = "LDSWebapp/1.0"

    def log_message(self, fmt, *args):  # silenciar el log por defecto ruidoso a stderr
        pass

    # ---- helpers de respuesta ----

    def _json(self, datos, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _error_json(self, codigo: int, mensaje: str) -> None:
        self._json({"error": mensaje}, codigo)

    def _archivo_estatico(self, ruta_relativa: str) -> None:
        # guard contra path traversal: resolver y confirmar que sigue
        # dentro de STATIC_DIR.
        destino = (STATIC_DIR / ruta_relativa).resolve()
        if STATIC_DIR not in destino.parents and destino != STATIC_DIR:
            self._error_json(403, "Ruta no permitida")
            return
        if not destino.is_file():
            self._error_json(404, "No encontrado")
            return
        content_type = _CONTENT_TYPES.get(destino.suffix, "application/octet-stream")
        datos = destino.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _leer_cuerpo(self) -> bytes:
        largo = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(largo) if largo else b""

    # ---- GET ----

    def do_GET(self):
        try:
            ruta = urlparse(self.path).path
            if ruta == "/":
                self._archivo_estatico("index.html")
                return
            if ruta.startswith("/static/"):
                self._archivo_estatico(unquote(ruta[len("/static/"):]))
                return
            if ruta == "/api/proyectos":
                self._get_proyectos()
                return
            m = re.match(r"^/api/estado/([^/]+)$", ruta)
            if m:
                self._get_estado(unquote(m.group(1)))
                return
            m = re.match(r"^/api/rf/([^/]+)$", ruta)
            if m:
                self._get_rf(unquote(m.group(1)))
                return
            m = re.match(r"^/api/reporte/([^/]+)$", ruta)
            if m:
                self._get_reporte(unquote(m.group(1)))
                return
            self._error_json(404, "Ruta no encontrada")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._error_json(500, str(e))

    def _get_proyectos(self):
        proyectos = sorted(
            p.name for p in RAIZ.iterdir()
            if p.is_dir() and (p / "matriz_casos.json").exists()
        )
        self._json({"proyectos": proyectos})

    def _get_estado(self, proyecto: str):
        try:
            _validar_proyecto(proyecto)
        except ValueError as e:
            self._error_json(400, str(e))
            return
        self._json(estado.leer(procesos.proyecto_dir(proyecto)))

    def _get_rf(self, proyecto: str):
        try:
            _validar_proyecto(proyecto)
        except ValueError as e:
            self._error_json(400, str(e))
            return
        pdir = procesos.proyecto_dir(proyecto)
        matriz_path = pdir / "matriz_casos.json"
        if not matriz_path.exists():
            self._error_json(404, "El proyecto no tiene matriz_casos.json todavia")
            return
        matriz = json.loads(matriz_path.read_text(encoding="utf-8"))
        por_rf: dict[str, dict] = {}
        for cp, info in matriz.items():
            rf = info.get("rf", "?")
            entrada = por_rf.setdefault(rf, {"rf": rf, "cp_total": 0, "cp_generados": 0})
            entrada["cp_total"] += 1
            if (pdir / f"{cp}.py").exists():
                entrada["cp_generados"] += 1
        rfs = [por_rf[k] for k in sorted(por_rf, key=lambda r: (len(r), r))]
        self._json({"rf": rfs})

    def _get_reporte(self, proyecto: str):
        try:
            _validar_proyecto(proyecto)
        except ValueError as e:
            self._error_json(400, str(e))
            return
        pdir = procesos.proyecto_dir(proyecto)
        archivo = _reporte_mas_nuevo(pdir)
        if archivo is None:
            self._error_json(404, "Todavia no hay una corrida completa para este proyecto")
            return
        self._json(json.loads(archivo.read_text(encoding="utf-8")))

    # ---- POST ----

    def do_POST(self):
        try:
            ruta = urlparse(self.path).path
            if ruta == "/api/proyectos/analizar":
                self._post_analizar()
                return
            m = re.match(r"^/api/ejecutar/([^/]+)$", ruta)
            if m:
                self._post_ejecutar(unquote(m.group(1)))
                return
            self._error_json(404, "Ruta no encontrada")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._error_json(500, str(e))

    def _post_analizar(self):
        content_type = self.headers.get("Content-Type", "")
        cuerpo = self._leer_cuerpo()
        try:
            campos = multipart.parsear(cuerpo, content_type)
        except multipart.MultipartError as e:
            self._error_json(400, f"Cuerpo multipart invalido: {e}")
            return

        if "proyecto" not in campos or "excel" not in campos:
            self._error_json(400, "Faltan campos requeridos: proyecto, excel")
            return

        proyecto = campos["proyecto"][0].texto().strip()
        try:
            _validar_proyecto(proyecto)
        except ValueError as e:
            self._error_json(400, str(e))
            return

        if procesos.hay_proceso_en_curso(proyecto):
            self._error_json(409, "ya_hay_un_proceso_en_curso")
            return

        UPLOADS_DIR.mkdir(exist_ok=True)
        stage = UPLOADS_DIR / f"{proyecto}_{os.getpid()}_{id(cuerpo)}"
        stage.mkdir(parents=True, exist_ok=True)

        excel_parte = campos["excel"][0]
        excel_path = stage / (excel_parte.nombre_archivo or "matriz.xlsx")
        excel_path.write_bytes(excel_parte.datos)

        ef_path = None
        if "ef" in campos and campos["ef"][0].datos:
            ef_parte = campos["ef"][0]
            ef_path = stage / (ef_parte.nombre_archivo or "EF.docx")
            ef_path.write_bytes(ef_parte.datos)

        et_path = None
        if "et" in campos and campos["et"][0].datos:
            et_parte = campos["et"][0]
            et_path = stage / (et_parte.nombre_archivo or "ET.docx")
            et_path.write_bytes(et_parte.datos)

        extra_paths = []
        for i, extra_parte in enumerate(campos.get("extra", [])):
            if not extra_parte.datos:
                continue
            nombre = extra_parte.nombre_archivo or f"adicional_{i + 1}"
            extra_path = stage / nombre
            extra_path.write_bytes(extra_parte.datos)
            extra_paths.append(extra_path)

        try:
            procesos.lanzar_bootstrap_y_explorar(proyecto, excel_path, ef_path, et_path, extra_paths)
        except procesos.ProcesoEnCursoError:
            self._error_json(409, "ya_hay_un_proceso_en_curso")
            return

        self._json({"proyecto": proyecto, "fase": "bootstrap"}, 202)

    def _post_ejecutar(self, proyecto: str):
        try:
            _validar_proyecto(proyecto)
        except ValueError as e:
            self._error_json(400, str(e))
            return

        cuerpo = self._leer_cuerpo()
        try:
            datos = json.loads(cuerpo) if cuerpo else {}
        except json.JSONDecodeError:
            self._error_json(400, "Cuerpo JSON invalido")
            return

        rf_list = datos.get("rf") or []
        if not rf_list:
            self._error_json(400, "Debe indicar al menos un RF en 'rf'")
            return
        video = bool(datos.get("video", True))

        pdir = procesos.proyecto_dir(proyecto)
        if not (pdir / "matriz_casos.json").exists():
            self._error_json(404, "El proyecto no existe o no tiene matriz_casos.json")
            return

        if procesos.hay_proceso_en_curso(proyecto):
            self._error_json(409, "ya_hay_un_proceso_en_curso")
            return

        try:
            procesos.lanzar_ejecutar_pruebas(proyecto, rf_list, video)
        except procesos.ProcesoEnCursoError:
            self._error_json(409, "ya_hay_un_proceso_en_curso")
            return

        self._json({"proyecto": proyecto, "fase": "ejecutando_pruebas", "rf": rf_list}, 202)


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Handler)
    print(f"Webapp LDS corriendo en http://127.0.0.1:{PUERTO}  (Ctrl+C para detener)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
