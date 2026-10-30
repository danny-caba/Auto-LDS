# Manual de instalación — Webapp de Automatización LDS

Guía paso a paso para dejar funcionando la webapp (`http://127.0.0.1:8765`)
en una máquina nueva. Si ya tenés el entorno de automatización LDS
funcionando (Python + venv + Playwright ya instalados), saltá directo a
la sección **"Arranque rápido"**.

## Arranque rápido (entorno ya configurado)

1. Abrir una terminal en `C:\AUTOMATIZACION_LDS`.
2. Ejecutar:
   ```
   C:\Proyectos\PlataformaWeb\.venv\Scripts\python.exe _framework\webapp\server.py
   ```
3. Abrir `http://127.0.0.1:8765` en el navegador.
4. Dejar la terminal abierta mientras se use la webapp (es el servidor).
   Para apagarla, `Ctrl+C` en esa terminal.

Si el puerto 8765 ya está en uso, cambiarlo con una variable de entorno
antes de arrancar:
```
set WEBAPP_PORT=8766
C:\Proyectos\PlataformaWeb\.venv\Scripts\python.exe _framework\webapp\server.py
```

## Instalación completa (máquina nueva)

### 1. Requisitos previos

| Programa | Para qué | Dónde conseguirlo |
|---|---|---|
| Python 3.13+ | Correr el servidor y los scripts de prueba | https://www.python.org/downloads/ |
| Visual Studio Code | Editor (opcional pero recomendado) | https://code.visualstudio.com/ |
| Microsoft Edge | Navegador que usa Playwright para las pruebas | Ya viene en Windows |

Al instalar Python, marcar la casilla **"Add python.exe to PATH"** en el
instalador.

### 2. Clonar o copiar el repositorio

El framework completo (`_framework/`) y la carpeta de cada proyecto
viven en `C:\AUTOMATIZACION_LDS`. Si se trabaja desde GitHub:
```
git clone https://github.com/danny-caba/Auto-LDS.git C:\AUTOMATIZACION_LDS
```

### 3. Crear el entorno virtual de Python

La webapp y todos los `CPxxx.py` generados corren sobre un venv
compartido en `C:\Proyectos\PlataformaWeb`:
```
mkdir C:\Proyectos\PlataformaWeb
cd C:\Proyectos\PlataformaWeb
python -m venv .venv
.venv\Scripts\pip install -r C:\AUTOMATIZACION_LDS\requirements.txt
.venv\Scripts\python -m playwright install
```
Esto instala Playwright (único paquete externo que usa todo el
proyecto) y descarga los navegadores que necesita.

**Nota:** la webapp en sí (`server.py`) **no necesita ningún paquete
adicional** — el backend usa solo librería estándar de Python
(`http.server`), sin Flask/FastAPI. Esto es intencional: en VMs
corporativas con proxy que bloquea instalaciones nuevas por `pip`, la
webapp sigue funcionando igual. Ver la sección "Por qué sin
dependencias" del `README.md` de esta misma carpeta para el detalle.

### 4. Arrancar la webapp

Igual que en "Arranque rápido" arriba:
```
C:\Proyectos\PlataformaWeb\.venv\Scripts\python.exe C:\AUTOMATIZACION_LDS\_framework\webapp\server.py
```

### 5. Verificar que funciona

Abrir `http://127.0.0.1:8765` — debería verse la pestaña **"Nuevo
proyecto"** con un formulario para subir la matriz Excel. Si la página
no carga, revisar que la terminal del paso 4 no muestre ningún error
(puerto ocupado, Python no encontrado, etc.).

## Uso de la webapp

La webapp tiene 3 pestañas:

1. **Nuevo proyecto** — subir la matriz de casos (Excel, obligatoria) y
   opcionalmente las Especificaciones Funcionales/Técnicas (Word).
   Completar el "Código de proyecto" (ej. `PR000456` o `PR000456-SP1`)
   y presionar **Analizar**. Esto arma la carpeta del proyecto
   (`C:\AUTOMATIZACION_LDS\<codigo>\`) con la matriz extraída a JSON.
2. **Ejecutar pruebas** — elegir uno o más RF del proyecto y correr los
   casos (con o sin video).
3. **Reporte** — ver el resultado consolidado (OK/FALLO) de la última
   corrida.

### Sobre el botón "Analizar" y la IA

El botón "Analizar" intenta dos cosas:
- **Bootstrap del proyecto** (siempre funciona): arma la carpeta,
  extrae la matriz Excel a JSON, deja todo listo para generar los
  casos.
- **Exploración y generación automática de los casos con IA**: solo
  funciona si el CLI `claude` (Claude Code) está instalado en esta
  máquina como programa standalone (no la extensión de VS Code/IDE,
  que es algo distinto). **Hoy ese CLI no está instalado en esta VM**
  (ver sección siguiente) — la webapp lo detecta y, en su lugar,
  muestra el prompt completo con un botón **"Copiar"** para pegarlo a
  mano en una sesión interactiva de Claude Code. Este punto de entrada
  manual es el que se viene usando hasta ahora y sigue siendo 100%
  válido - no es un paso roto, es el modo normal de operar mientras no
  se instale el CLI.

## Problemas comunes

- **"No se pudo conectar" al abrir la URL**: el servidor no está
  corriendo, o se cerró la terminal del paso 4. Volver a ejecutar el
  comando de arranque.
- **Puerto 8765 ocupado**: usar `WEBAPP_PORT` (ver "Arranque rápido").
- **El botón "Analizar" nunca avanza / queda colgado**: revisar la
  terminal del servidor por errores. Un proyecto solo puede tener un
  proceso de fondo a la vez (bootstrap O ejecución) — si se intenta
  disparar dos a la vez, la webapp responde con error 409
  intencionalmente.
