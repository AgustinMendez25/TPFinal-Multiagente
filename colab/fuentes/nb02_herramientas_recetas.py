"""Fuente del notebook 02: el corpus, el inventario y las herramientas de recetas (sin GPU)."""
from comun import entorno

NOMBRE = "02_herramientas_recetas.ipynb"

CELDAS = [
    ("md", """
# 02 · Las herramientas del agente de recetas

**Qué hace este notebook.** Muestra con qué trabaja el agente de «Rescatá la heladera»: el recetario normalizado, la heladera (el inventario) y las cuatro herramientas. Al final corre los tests que comprueban que las herramientas dan lo mismo que el generador de respuestas esperadas.

**Qué necesitás.** Cualquier entorno de Colab, **sin GPU**: acá no se usa el modelo. Acceso a la carpeta `TPFinal-heladera` en tu Drive y el token de GitHub de solo lectura.

**Cuánto tarda.** Un par de minutos.

**Qué deja en Drive.** La salida de los tests en `TPFinal-heladera/registros/`.
"""),
    *entorno(gpu=False),
    ("md", """
## 1 · El recetario

Usamos **RecetasDeLaAbuela** (SomosNLP, OpenRAIL), solo las recetas de recetasgratis.net. Un script normalizó las cantidades: **cada ingrediente tiene una sola unidad** (gramos para la harina, unidades para la cebolla, mililitros para la leche…), y cada conversión quedó registrada en `datos/normalizacion/`. Así se pueden escalar porciones y comparar con la heladera. Las 3.184 recetas finales están en `datos/recetas_final.csv` (se sacaron 14 con cantidades absurdas, como «400 kilogramos de nueces»: decisión D20).

Cada línea de ingrediente guarda: el nombre canónico, la cantidad, la unidad, si hubo que convertirla (`estado`) y el texto original.
"""),
    ("code", """
import json
from herramientas import recetas as H

corpus = H._corpus()
print(len(corpus), "recetas")
ejemplo = corpus[1383]
print(ejemplo["nombre"], "·", ejemplo["comensales"], "comensales ·", ejemplo["minutos"], "min")
for linea in ejemplo["ingredientes"]:
    print(f"  {linea['ingrediente']:<12} {str(linea['cantidad']):>7} {str(linea['unidad']):<8} {linea['estado']:<11} ← {linea['texto']}")
"""),
    ("md", """
**Los básicos** (sal, pimienta, aceite, agua, condimentos y hierbas) quedan sin cantidad: se suponen disponibles y no cuentan como faltantes.

## 2 · La heladera

El inventario es **estado de la sesión**: es el mismo para todas las tareas y ninguna herramienta lo recibe como argumento. El harness lo muestra en el prompt ordenado por vencimiento y marca como **prioritario** lo que vence en 3 días o menos. Eso lo calcula el código, no el modelo.
"""),
    ("code", """
from harness import dominios
print(dominios.tabla_inventario())
"""),
    ("md", """
## 3 · Las cuatro herramientas

Cada una hace **una sola cosa**. Devuelven datos o `{"error": ...}`; nunca levantan una excepción por un argumento que no existe, para que el loop le pueda devolver el error al modelo.

### `buscar_recetas(contiene, excluye=[])`
Filtra por ingredientes canónicos (acepta sinónimos como «patata» y plurales como «lentejas») y ordena **por duración** y, si empatan, por id. Devuelve el total y las 10 más rápidas: «la más rápida» que cumple algo es la primera de la lista que lo cumple.
"""),
    ("code", """
H.buscar_recetas(["papa", "cebolla"])
"""),
    ("code", """
H.buscar_recetas(["pollito"])   # un nombre que no existe: error con sugerencias
"""),
    ("md", """
### `detalle_receta(receta_id, porciones=None)`
Los ingredientes de una receta, con su cantidad y la línea original. Con `porciones`, escala las cantidades (regla de tres sobre los comensales de la receta).
"""),
    ("code", """
H.detalle_receta(4597, porciones=4)
"""),
    ("md", """
### `es_apta(receta_id, dieta)`
Si la receta cumple una dieta (vegetariana, vegana, sin_gluten o sin_lactosa), según las etiquetas del léxico, y qué ingredientes lo impiden.
"""),
    ("code", """
H.es_apta(4597, "vegana")
"""),
    ("md", """
### `faltantes(receta_id, porciones)`
Compara la receta escalada con la heladera: por ingrediente, cuánto necesita, cuánto hay y si alcanza. Lo que no está en la heladera falta siempre. Este cruce lo hace el código: en la prueba de factibilidad, el modelo solo, con los datos delante, dijo que faltaba tomate cuando había.
"""),
    ("code", """
H.faltantes(4597, porciones=10)
"""),
    ("md", """
## 4 · Lo que ve el modelo

El prompt de sistema del agente (con la heladera) y la ficha JSON de una herramienta. Las fichas son el contrato: el loop valida los argumentos contra ellas antes de ejecutar.
"""),
    ("code", """
print(dominios.sistema_recetas())
print(json.dumps(H.FICHAS_POR_NOMBRE["faltantes"], ensure_ascii=False, indent=1))
"""),
    ("md", """
## 5 · Los tests: herramientas contra el generador

`factibilidad/borrador_respuestas.py` calcula las respuestas esperadas de las tareas **directo sobre los datos**, sin pasar por las herramientas. Lo único que comparten las dos implementaciones es la capa de datos (léxico, básicos, dietas y el CSV). Los tests comparan las dos sobre **todo el corpus**: orden de búsqueda, aptitud, cantidades escaladas y faltantes. También corren los tests del detector de dieta y porciones y de la verificación.
"""),
    ("code", """
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pytest"], check=True)
salida = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_recetas.py", "tests/test_detector.py",
                         "tests/test_verificacion.py", "tests/test_dominio_recetas.py"], capture_output=True, text=True)
print(salida.stdout[-3000:])
_ = (entorno.rutas()["registros"] / "pytest_02.txt").write_text(salida.stdout, encoding="utf-8")
"""),
    ("md", """
## Cierre

Si los tests dieron todo en verde, las herramientas reproducen las respuestas del generador. Lo que sigue es el notebook **03 · Desarrollo**, donde el agente usa estas herramientas sobre las tareas de desarrollo.
"""),
]
