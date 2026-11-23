"""Celdas que comparten los notebooks: montar Drive, clonar el repo y preparar el entorno."""

CLONAR = """
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
subprocess.run(["git", "checkout", "-q", "main"], check=True)   # por si el 04 dejó el código fijado en un tag
subprocess.run(["git", "pull", "-q"], check=True)
sys.path.insert(0, CARPETA)
print(subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True).stdout)
"""


def entorno(gpu: bool) -> list[tuple[str, str]]:
    explicacion = (
        "La segunda celda instala Ollama **0.40.10** (la versión del kit), baja `qwen3:8b`, hace una llamada de "
        "prueba y chequea que el modelo corra **100% en la GPU**. Si aparece un aviso de ATENCIÓN, leelo antes de "
        "seguir." if gpu else
        "Este notebook **no usa GPU** ni el modelo: la segunda celda solo prepara las carpetas de Drive.")
    preparar = ('from colab import entorno\nINFORME = entorno.preparar(gpu=True)\n'
                'QUIEN = input("Tu nombre (queda en la tanda que corras): ").strip() or "anonimo"'
                if gpu else 'from colab import entorno\nINFORME = entorno.preparar(gpu=False)')
    return [
        ("md", """
## 0 · Preparar el entorno

La primera celda monta tu Drive y baja el código del repositorio. El token de GitHub (de solo lectura) se pide al correr y no queda en el notebook. Si la sesión ya tenía el repo, hace `git pull` para traer la última versión.

**Si estás retomando una tanda que se cortó** y el código cambió en el medio, la corrida se va a negar a seguir (para no mezclar versiones) y te dice qué commit usar: corré `!git checkout <commit>` y volvé a correr la celda de la tanda.
"""),
        ("code", CLONAR),
        ("md", explicacion),
        ("code", preparar),
    ]
