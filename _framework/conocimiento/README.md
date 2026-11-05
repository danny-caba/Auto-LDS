# Memoria central del piloto Auto-LDS

Conocimiento verificable sobre el proyecto, guardado en archivos de
**este repositorio** — a diferencia de la memoria automática de Claude
Code (que vive fuera del repo, atada a una instalación puntual), esto
lo puede leer cualquier sesión nueva de Claude (u otra persona) con
solo abrir estos archivos, sin depender del historial de conversación.

Implementado y mantenido por `_framework/memoria_central.py` — ver su
docstring para la API completa. **No editar `indice.json`/`indice.md`
a mano**, se regeneran solos; sí se puede editar un `entradas/<id>.json`
a mano si hace falta corregir algo (es texto plano).

## Estructura

```
conocimiento/
  README.md          <- este archivo
  indice.json          <- fuente de verdad del índice (generado)
  indice.md             <- vista humana del índice (generado, por secciones)
  entradas/
    CONO-0001.json       <- una entrada completa
    ...
  consultas/
    <requerimiento>.json <- registro de que se consultó la memoria para ese requerimiento
```

## Tipos de entrada

- `REGLA_DOCUMENTADA` — algo que dice explícitamente un EF/ET/manual.
- `COMPORTAMIENTO_OBSERVADO` — algo confirmado en vivo (puede coincidir
  o no con lo documentado).
- `SOLUCION_TECNICA_COMPROBADA` — un fix/patrón de automatización que
  funcionó, verificado.
- `DATO_DE_PRUEBA` — un dato reutilizable (código, cliente, cuenta) y
  dónde/cuándo se confirmó que sirve.
- `INTERVENCION_MANUAL` — una intervención humana registrada (ver
  Etapa 4, `_framework/intervencion.py`).
- `DUDA_PENDIENTE` — algo sin resolver, que necesita confirmación.

## Estados

`PROVISIONAL` (default al crear) → `VERIFICADO` (llamada aparte,
explícita, nunca automática) · `INVALIDADO` (se descartó, con motivo,
nunca se borra) · `REEMPLAZADO` (una entrada nueva la reemplazó,
vinculadas en ambos sentidos).

**`buscar()` con el default (`solo_vigentes=True`) excluye
`INVALIDADO`/`REEMPLAZADO` automáticamente** — invalidar algo hace que
dejé de recomendarse sin que haga falta acordarse de filtrarlo a mano.

## Cómo consultar antes de un requerimiento nuevo

```python
import sys; sys.path.insert(0, r"C:\AUTOMATIZACION_LDS\_framework")
import memoria_central as mc

candidatas = mc.buscar(modulo="mi-modulo")          # o tipo=, o sin filtro
mc.registrar_consulta(
    "MS000000",
    entradas_consultadas=["CONO-0001", "CONO-0002"],
    entradas_aplicadas=["CONO-0001"],
    entradas_descartadas={"CONO-0002": "era de otro ambiente, no aplica"},
)
```

`mc.tiene_registro_consulta("MS000000")` confirma si ese archivo
existe — **solo prueba que el registro existe, no que el razonamiento
detrás fue correcto.**

## Cómo agregar, verificar e invalidar

```python
nueva = mc.agregar_entrada(
    "SOLUCION_TECNICA_COMPROBADA",
    "Descripción clara de la solución...",
    fuente="EF MS000000, sección 3",
    requerimiento_origen="MS000000",
    modulo="mi-modulo",
    referencias_evidencia=["MS000000/resultados/.../resultado.json"],
)
mc.verificar_entrada(nueva["id"])                 # PROVISIONAL -> VERIFICADO
mc.invalidar_entrada(nueva["id"], "motivo claro")  # deja de recomendarse, pero no se borra

# Reemplazar una entrada por una mejor (vincula ambas, conserva historial):
mc.agregar_entrada(..., reemplaza=nueva["id"])
```

## Importante — no guardar secretos ni duplicar documentos

El campo `descripcion` es texto libre: quien lo escriba es responsable
de no pegar contraseñas/tokens ahí (este módulo no sanitiza contenido
libre, a diferencia de `resultados.py`). Usar `referencias_evidencia`
para **apuntar** a un archivo/resultado real en vez de copiar su
contenido completo acá.
