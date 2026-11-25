"""Fuente del notebook 06: la demo de la presentación, con la traza a la vista."""
from comun import CLONAR, entorno

NOMBRE = "06_demo.ipynb"

_, _, EXPLICA_ENTORNO, PREPARAR = entorno(gpu=True)

CELDAS = [
    ("md", """
# 06 · Demo: el agente de recetas en vivo

**Qué hace este notebook.** Es el de la presentación. Corre el agente de recetas sobre:
1. **una tarea del conjunto** que elige el equipo docente, y la puntúa igual que en la medición;
2. **una pregunta nueva**, para ver al agente fuera de lo que ensayamos.

En los dos casos muestra la traza paso a paso: el plan, cada herramienta con sus argumentos y lo que devolvió, el rechazo de la verificación si lo hubo, y cómo terminó.

**La configuración.** Usa `ambas` (planificación y verificación), la que más acertó en la medición congelada: 18,0 de 21 en promedio con tres semillas. Se puede cambiar por `base`, `plan` o `verif` para mostrar la diferencia.

**Qué necesitás.** Colab con GPU **T4**, la carpeta `TPFinal-heladera` en tu Drive y el token de GitHub de solo lectura.

**Cuánto tarda.** Unos 10 minutos de preparación (hacelo **antes** de la presentación) y de 20 segundos a un minuto por pregunta.

**Qué deja en Drive.** `corridas/recetas__demo/`, fuera de las mediciones.
"""),
    ("code", CLONAR),
    EXPLICA_ENTORNO,
    PREPARAR,
    ("md", """
## 1 · La heladera y la configuración

El inventario es estado de la sesión: el agente lo ve en el prompt de sistema, ordenado por vencimiento, con los que vencen en 3 días o menos marcados como prioritarios. Ninguna herramienta lo recibe como argumento.
"""),
    ("code", """
import json
from pathlib import Path
import evaluar
from colab import tandas
from harness import corridas, ver_traza

VARIANTE = "ambas"   # <- base, plan, verif o ambas
CONFIG = Path(f"configs/recetas_{VARIANTE}.toml").resolve()
RUTAS = entorno.rutas()
DEMO = RUTAS["corridas"] / "recetas__demo"
DEMO.mkdir(exist_ok=True)

for item in json.loads(Path("tareas/recetas_inventario.json").read_text(encoding="utf-8")):
    print(item)
print("\\nConfiguración:", CONFIG.name)
print(open(CONFIG, encoding="utf-8").read())
"""),
    ("md", """
## 2 · Una tarea del conjunto

Poné el id que elija el equipo docente (`rec-001` a `rec-021`). La celda le agrega a la pregunta el formato de respuesta de su tipo, igual que en la medición, corre el agente y la puntúa contra la respuesta calculada sobre el corpus.

Las 3 imposibles son `rec-013` (calorías), `rec-014` (una combinación sin recetas) y `rec-015` (precios): ahí lo correcto es negarse, con `respuesta = null` y el motivo.
"""),
    ("code", """
TAREA_ID = "rec-016"   # <- la que elija el equipo docente

TAREA = next(t for t in tandas.tareas("congelado") if t["id"] == TAREA_ID)
print("Pregunta:", TAREA["pregunta"], "\\n")
(DEMO / f"{TAREA_ID}.jsonl").unlink(missing_ok=True)       # si ya se corrió, se vuelve a correr de cero
corridas.corredor_agente(CONFIG, "recetas")(TAREA, DEMO)
print(ver_traza.resumen(DEMO / f"{TAREA_ID}.jsonl"))
fila = evaluar.evaluar_tarea(TAREA, DEMO, evaluar.PESOS)
print(f"\\nEsperada: {TAREA['respuesta']} · obtenida: {fila['obtenido']} · {fila['resultado']}")
"""),
    ("md", """
## 3 · Una pregunta nueva

Cualquier pregunta sobre el recetario y la heladera de arriba. Si pide un formato («respondé solo con el número»), escribilo en la pregunta: acá no hay tipo que lo agregue.
"""),
    ("code", """
PREGUNTA = "¿Qué receta vegetariana con huevo puedo hacer para 2 personas sin comprar nada? Respondé con el nombre."

ruta = DEMO / "pregunta.jsonl"
ruta.unlink(missing_ok=True)
subprocess.run([sys.executable, "agente.py", "-p", PREGUNTA, "--tarea", "pregunta", "--log", str(DEMO),
                "--config", str(CONFIG), "--dominio", "recetas"], check=False)
print(ver_traza.resumen(ruta))
"""),
    ("md", """
## 4 · La misma tarea, con otra variante al lado

Para mostrar qué cambia una decisión: corre la tarea de la sección 2 con `base` (sin plan ni verificación) y pone las dos trazas lado a lado.
"""),
    ("code", """
BASE = DEMO / "base"
BASE.mkdir(exist_ok=True)
(BASE / f"{TAREA_ID}.jsonl").unlink(missing_ok=True)
corridas.corredor_agente(Path("configs/recetas_base.toml").resolve(), "recetas")(TAREA, BASE)
print(f"{'BASE'.ljust(70)} | {VARIANTE.upper()}")
print(ver_traza.comparar(BASE / f"{TAREA_ID}.jsonl", DEMO / f"{TAREA_ID}.jsonl"))
print("\\nbase:", evaluar.evaluar_tarea(TAREA, BASE, evaluar.PESOS)["resultado"],
      f"· {VARIANTE}:", evaluar.evaluar_tarea(TAREA, DEMO, evaluar.PESOS)["resultado"])
"""),
    ("md", """
## Qué mirar en la traza

- **El plan** (evento `plan`, paso 1): qué candidatas dice que va a recorrer y con qué criterio las compara.
- **Las herramientas encadenadas:** `buscar_recetas` → `es_apta` sobre cada candidata si hay dieta → `faltantes` o `detalle_receta` con las porciones de la pregunta.
- **La verificación:** si la respuesta no sale de ningún resultado, o se salteó la dieta o las porciones, aparece el rechazo y el segundo intento.
- **El final:** `terminar` con la respuesta y el motivo, o con `null` si los datos no alcanzan.
"""),
]
