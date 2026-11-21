"""Fuente del notebook 01: el loop del Bloque 1 sobre el Mundial."""
NOMBRE = "01_bloque1_mundial.ipynb"

CELDAS = [
    ("md", """
# 01 · Bloque 1: el loop del agente sobre el Mundial

**Qué hace este notebook.** Corre las 30 tareas públicas del Mundial de dos maneras y las puntúa:
1. **Libro cerrado**: el modelo contesta de memoria, sin herramientas. Es la línea de base.
2. **El agente**: el mismo modelo, pero dentro de nuestro loop, con herramientas sobre los datos.

**Qué necesitás.** Una cuenta de Colab con GPU **T4** (*Entorno de ejecución → Cambiar tipo de entorno de ejecución → T4*, **antes** de correr nada), acceso a la carpeta compartida `TPFinal-heladera` en tu Drive (agregala a *Mi unidad* con *Agregar acceso directo*) y un token de GitHub de solo lectura para el repo.

**Cuánto tarda.** Unos 10 minutos de preparación (Ollama y el modelo) y después unos 30 a 60 minutos por corrida de 30 tareas.

**Qué deja en Drive.** `TPFinal-heladera/corridas/<corrida>/` con una traza por tarea, y `TPFinal-heladera/resultados/<corrida>.csv` con la puntuación.

**Si se corta la sesión:** volvé a abrir el notebook, corré la sección 0 y después la misma celda de corrida. Sigue desde la última tarea que quedó en Drive.
"""),
    ("md", """
## 0 · Preparar el entorno

La primera celda monta tu Drive y baja el código del repositorio. El token se pide al correr y no queda en el notebook. Para crearlo: GitHub → *Settings* → *Developer settings* → *Fine-grained tokens* → solo este repositorio, permiso **Contents: Read-only**, vencimiento corto.
"""),
    ("code", """
from google.colab import drive
drive.mount("/content/drive")

import os, subprocess, sys
from getpass import getpass

REPO = "AgustinMendez25/TPFinal-Multiagente"
CARPETA = "/content/proyecto"
if not os.path.exists(CARPETA):
    url = f"https://{getpass('Token de GitHub (solo lectura): ')}@github.com/{REPO}.git"
    subprocess.run(["git", "clone", "-q", url, CARPETA], check=True)
    del url
os.chdir(CARPETA)
subprocess.run(["git", "pull", "-q"], check=True)
sys.path.insert(0, CARPETA)
print(subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True).stdout)
"""),
    ("md", """
La segunda celda instala Ollama **0.40.10** (la versión del kit), baja `qwen3:8b`, hace una llamada de prueba y chequea que el modelo corra **100% en la GPU**. Si aparece un aviso de ATENCIÓN, leelo antes de seguir: los tiempos de una corrida que no está 100% en GPU no sirven para comparar.

Después baja los datos del Mundial (la *Fjelstul World Cup Database*, con la versión fijada) y arma la base SQLite que usan las herramientas.
"""),
    ("code", """
from colab import entorno
INFORME = entorno.preparar(gpu=True)
subprocess.run([sys.executable, "datos/descargar.py"], check=True)
QUIEN = input("Tu nombre (queda en la tanda que corras): ").strip() or "anonimo"
"""),
    ("md", """
## 1 · Cómo funciona el loop

Un agente es un programa que le deja al modelo decidir **el próximo paso**, pero se queda con todo lo demás: qué herramientas puede usar, cómo se ejecutan, qué vuelve a la ventana y cuándo se frena. Nuestro loop está en `harness/bucle.py` y es **el mismo** para el Mundial y para las recetas; lo que cambia es el `Dominio` (las herramientas y las instrucciones).

En cada **paso**:
1. Se le manda al modelo toda la conversación más las fichas JSON de las herramientas.
2. Si el modelo pide herramientas, se ejecuta cada una y se le devuelve **un resultado por llamada**.
3. Si llama a `terminar(respuesta, motivo)`, la corrida termina: con respuesta es `respondida`, con `null` es `negada` (los datos no alcanzan).
4. Si contesta con texto suelto, se le recuerda que tiene que llamar a una herramienta.

La función principal:
"""),
    ("code", """
import inspect
from harness import bucle
print(inspect.getsource(bucle.bucle))
"""),
    ("md", """
### Qué pasa cuando algo sale mal

El modelo se equivoca y las herramientas fallan. El loop **no se cae**: le devuelve el error al modelo como resultado y sigue. Cada caso de la sección 4 del enunciado:

| Caso | Qué hace el loop | Dónde |
|---|---|---|
| JSON roto en los argumentos | devuelve «los argumentos no son JSON válido» | `_parsear` |
| Herramienta que no existe | devuelve la lista de las que hay | `_atender` |
| Argumento de tipo equivocado, que falta o que sobra | devuelve qué argumento está mal y por qué | `validar_argumentos` |
| La herramienta levanta una excepción o tarda demasiado | devuelve «la herramienta falló» o «tardó más de N s» | `_ejecutar` |
| Resultado vacío | devuelve «la herramienta no encontró nada» | `_texto_resultado` |
| Resultado demasiado largo | lo recorta a `contexto.tope_resultado_caracteres` y avisa | `_texto_resultado` |
| El servidor del modelo falla | reintenta con espera creciente, hasta `frenos.reintentos` | `_llamar_modelo` |
| El prompt no entra en `num_ctx` | termina con `error` (reintentar no lo arregla) | `bucle` |
| Demasiados pasos o tokens | termina con `tope_pasos` o `tope_tokens` | `bucle` |
"""),
    ("code", """
print(inspect.getsource(bucle.validar_argumentos))
print(inspect.getsource(bucle._ejecutar))
print(inspect.getsource(bucle._llamar_modelo))
"""),
    ("md", """
### La configuración

`config.toml` fija el modelo, `num_ctx` (que se manda **en cada llamada**: Ollama usa 4.096 por defecto en una T4 y recortaría en silencio), la decodificación (temperatura 0, semilla 1337, `think` apagado) y los frenos. Se copia entera en el primer evento de cada traza.
"""),
    ("code", """
print(open("config.toml", encoding="utf-8").read())
"""),
    ("md", """
## 2 · Línea de base: libro cerrado

Las mismas 30 preguntas, al mismo modelo, **sin herramientas**. Sirve para saber cuánto sabe el modelo de memoria. Lo que compra el agente no es solo acertar: es una respuesta que sale de los datos y un «los datos no alcanzan» honesto en las 4 imposibles.

La celda corre la tanda y copia cada traza a Drive apenas termina. Si se corta, volvé a correrla: saltea lo que ya está.
"""),
    ("code", """
import json
from pathlib import Path
import config as configuracion
import evaluar
from harness import corridas

RUTAS = entorno.rutas()
TAREAS = json.loads(Path("tareas/mundial_publicas.json").read_text(encoding="utf-8"))
CONFIG = configuracion.cargar()


def correr(nombre, correr_una):
    destino = RUTAS["corridas"] / nombre
    resumen = corridas.correr_tanda(
        TAREAS, destino, RUTAS["trabajo"] / nombre, correr_una,
        manifiesto=entorno.manifiesto(nombre, "mundial", CONFIG, TAREAS), quien=QUIEN,
        antes_de_cada=entorno.asegurar_ollama)
    print(resumen)
    return destino


LIBRO = corridas.nombre_corrida("mundial", "libro-cerrado", 0, 1337)
destino_libro = correr(LIBRO, corridas.corredor_libro_cerrado(CONFIG))
"""),
    ("code", """
def puntuar(destino):
    filas, resumen = evaluar.evaluar(TAREAS, destino, evaluar.PESOS)
    evaluar.escribir_csv(filas, RUTAS["resultados"] / f"{destino.name}.csv")
    evaluar.imprimir(filas, resumen)
    return filas, resumen


filas_libro, resumen_libro = puntuar(destino_libro)
"""),
    ("md", """
## 3 · El agente

Ahora con herramientas. `ETIQUETA` distingue la corrida **antes** del arreglo de la corrida **después** (sección 5). La primera vez dejala en `"antes"`.

Cada tarea corre en su propio proceso (`agente.py`), con un tope de 10 minutos; si el proceso se cuelga, el runner cierra la traza con `error` para que la falla quede registrada.
"""),
    ("code", """
ETIQUETA = "antes"   # <- después del arreglo, cambiala a "despues"

AGENTE = corridas.nombre_corrida("mundial", f"agente-{ETIQUETA}", 0, 1337)
destino_agente = correr(AGENTE, corridas.corredor_agente(Path("config.toml").resolve(), "mundial"))
filas_agente, resumen_agente = puntuar(destino_agente)
"""),
    ("md", """
## 4 · Mirar las trazas

Una traza es la evidencia de lo que hizo el agente: cada llamada al modelo (con sus tokens), cada herramienta (con sus argumentos y lo que devolvió) y cómo terminó. Elegí una tarea para verla. Empezá por las que fallaron.
"""),
    ("code", """
from harness import ver_traza

fallidas = [f["tarea"] for f in filas_agente if f["resultado"] != "acierto"]
print("Tareas que no acertó:", fallidas)
TAREA = fallidas[0] if fallidas else "mun-001"   # <- cambiá el id para ver otra
print(ver_traza.resumen(destino_agente / f"{TAREA}.jsonl"))
"""),
    ("md", """
**Una tarea que el agente se niega a responder.** El enunciado pide mostrar una: la traza tiene que dejar ver qué dato falta. Las imposibles son las que tienen `respondible: false`.
"""),
    ("code", """
imposibles = [t["id"] for t in TAREAS if not t["respondible"]]
negadas = [f["tarea"] for f in filas_agente if f["tarea"] in imposibles and f["resultado"] == "acierto"]
print("Imposibles:", imposibles, "· bien negadas:", negadas)
if negadas:
    print(ver_traza.resumen(destino_agente / f"{negadas[0]}.jsonl"))
"""),
    ("md", """
## 5 · El arreglo explicado

Después de la corrida **antes**, analizamos las trazas, elegimos una tarea que falla, vemos qué falló **primero** según la traza, cambiamos el harness y volvemos a correr con `ETIQUETA = "despues"` (sección 3). El cambio y su motivo quedan en `decision_log.md`.

Esta celda pone lado a lado las dos trazas de la tarea arreglada. Solo funciona cuando existen las dos corridas.
"""),
    ("code", """
TAREA_ARREGLADA = "mun-001"   # <- la tarea del arreglo (está en decision_log.md)
antes = RUTAS["corridas"] / corridas.nombre_corrida("mundial", "agente-antes", 0, 1337) / f"{TAREA_ARREGLADA}.jsonl"
despues = RUTAS["corridas"] / corridas.nombre_corrida("mundial", "agente-despues", 0, 1337) / f"{TAREA_ARREGLADA}.jsonl"
if antes.exists() and despues.exists():
    print("ANTES".ljust(70), "| DESPUÉS")
    print(ver_traza.comparar(antes, despues))
else:
    print("Todavía falta alguna de las dos corridas:", antes.exists(), despues.exists())
"""),
    ("md", """
## 6 · Pregunta suelta (para la demo)

En la presentación, el equipo docente hace una pregunta nueva. Esta celda corre el agente sobre cualquier pregunta y muestra la traza. Queda en `corridas/mundial__demo/`, fuera de las mediciones.
"""),
    ("code", """
PREGUNTA = "¿Qué edad tenía el goleador del Mundial 1978 el día de la final? Respondé solo con el número."
demo = RUTAS["corridas"] / "mundial__demo"
subprocess.run([sys.executable, "agente.py", "-p", PREGUNTA, "--tarea", "demo", "--log", str(demo)], check=False)
print(ver_traza.resumen(demo / "demo.jsonl"))
"""),
    ("md", """
## Cierre

En Drive quedaron:
- `corridas/mundial__libro-cerrado__t0__s1337/` y `corridas/mundial__agente-<etiqueta>__t0__s1337/`, con una traza por tarea y el `manifiesto.json` (commit, configuración y versión de Ollama);
- `resultados/<corrida>.csv`, con la puntuación de cada tarea.

**Qué sigue:** avisar que la corrida terminó. Las trazas se analizan desde Drive para escritorio para elegir el arreglo.
"""),
]
