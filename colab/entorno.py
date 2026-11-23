"""El entorno de Colab, igual para todos los notebooks: Drive, Ollama, el modelo y los chequeos.

Se usa después de la primera celda de cada notebook (que monta Drive y clona el repo):

    from colab import entorno
    informe = entorno.preparar(gpu=True)
"""
import datetime as dt
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import config as configuracion
import llm

DRIVE = Path(os.environ.get("TPFINAL_DRIVE", "/content/drive/MyDrive/TPFinal-heladera"))
OLLAMA_VERSION = "0.40.10"
RAIZ = Path(__file__).resolve().parent.parent

# Esta sesión de Colab: la máquina, cuándo arrancó y el estado de la GPU que midió `preparar`. Va en el
# manifiesto de cada tanda y en un archivo por sesión dentro de la tanda, para saber con qué GPU corrió.
SESION: dict = {"host": socket.gethostname(), "inicio": dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")}


def rutas() -> dict[str, Path]:
    carpetas = {"corridas": DRIVE / "corridas", "resultados": DRIVE / "resultados",
                "registros": DRIVE / "registros", "trabajo": Path("/content/trabajo")}
    for carpeta in carpetas.values():
        carpeta.mkdir(parents=True, exist_ok=True)
    return carpetas


def _sh(orden: str) -> None:
    subprocess.run(orden, shell=True, check=True)


def ollama_vivo() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            return True
    except OSError:
        return False


def instalar_ollama(version: str = OLLAMA_VERSION) -> None:
    instalada = shutil.which("ollama") and version in subprocess.run(
        ["ollama", "--version"], capture_output=True, text=True).stdout
    if not instalada:
        _sh("apt-get -qq update && apt-get -qq install -y zstd > /dev/null")
        _sh(f"curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION={version} sh")


def asegurar_ollama() -> None:
    """Levanta el servidor si no responde. Se llama antes de cada tarea: Colab a veces lo mata."""
    if ollama_vivo():
        return
    os.environ.update({"OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MAX_LOADED_MODELS": "1", "OLLAMA_NUM_PARALLEL": "1"})
    # Un log por sesión: si todas las cuentas escriben el mismo archivo de Drive, se pisan entre sí.
    log = open(rutas()["registros"] / f"ollama_{SESION['inicio']}_{SESION['host']}.log", "a")
    subprocess.Popen(["ollama", "serve"], start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(60):
        if ollama_vivo():
            return
        time.sleep(1)
    raise RuntimeError("Ollama no levantó: mirá el log en TPFinal-heladera/registros/")


def commit_actual() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=RAIZ,
                          check=True).stdout.strip()


def cambios_sin_commit() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=RAIZ,
                               check=True).stdout.strip())


def preparar(gpu: bool = True) -> dict:
    rutas()
    informe = {"commit": commit_actual(), "cambios_sin_commit": cambios_sin_commit(), "drive": str(DRIVE)}
    if gpu:
        instalar_ollama()
        asegurar_ollama()
        modelo = configuracion.cargar()["modelo"]["nombre"]
        subprocess.run(["ollama", "pull", modelo], check=True)
        respuesta = llm.chat([{"role": "user", "content": "Respondé solo con la palabra: listo"}], modelo=modelo,
                             num_ctx=configuracion.cargar()["modelo"]["num_ctx"], num_predict=20)
        ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout
        informe |= {"ollama": llm.version(), "ollama_esperada": OLLAMA_VERSION, "modelo": modelo,
                    "digest": llm.digest(modelo), "prueba": respuesta.mensaje.get("content", "").strip(),
                    "gpu": _nombre_gpu(), "gpu_100": "100% GPU" in ps}
        SESION.update({"gpu": informe["gpu"], "gpu_100": informe["gpu_100"], "ollama_ps": ps.strip()})
    for clave, valor in informe.items():
        print(f"{clave:>18}: {valor}")
    if informe["cambios_sin_commit"]:
        print("ATENCIÓN: hay cambios sin commit en la copia de Colab; las corridas registran el commit, no esos cambios.")
    if gpu and not informe["gpu_100"]:
        print("ATENCIÓN: el modelo no corre 100% en la GPU. Los tiempos no sirven para comparar.")
    if gpu and informe["ollama"] != OLLAMA_VERSION:
        print("ATENCIÓN: la versión de Ollama no es la del kit; hay que declararlo en el informe.")
    return informe


def _nombre_gpu() -> str | None:
    try:
        salida = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return salida.stdout.strip() or None


def manifiesto(corrida: str, conjunto: str, config: dict, tareas: list[dict]) -> dict:
    modelo = config["modelo"]["nombre"]
    try:
        servidor = {"ollama": llm.version(), "digest": llm.digest(modelo)}
    except llm.LLMError:
        servidor = {"ollama": None, "digest": None}
    return {"corrida": corrida, "conjunto": conjunto, "commit": commit_actual(), "config": config,
            "tareas": [t["id"] for t in tareas], "creada": dt.datetime.now(dt.timezone.utc).isoformat(), **servidor,
            "sesion": dict(SESION)}
