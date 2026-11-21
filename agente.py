"""El agente: recibe una pregunta y la responde llamando herramientas.

    uv run agente.py -p "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?" --log trazas/mi_corrida
    uv run agente.py -p "..." --tarea mun-024 --log trazas/mi_corrida --config config.toml --dominio mundial

El loop vive en `harness/bucle.py` y es el mismo para todos los dominios; `harness/dominios.py` arma
las herramientas y el prompt de cada uno. Este archivo lee y valida la configuración, abre la traza,
escribe `corrida_inicio` (con la configuración, el dominio y la versión de Ollama) y `corrida_fin`.
"""
import argparse
import sys
import traceback
from pathlib import Path

import config as configuracion
import llm
from harness import bucle as harness_bucle
from harness import dominios
from trazas.registro import Registro, SinRegistro

RAIZ = Path(__file__).resolve().parent


def bucle(pregunta: str, config: dict, registro, dominio: str = "mundial") -> harness_bucle.Fin:
    return harness_bucle.bucle(pregunta, config, registro, dominios.construir(dominio))


def entorno_del_servidor(modelo: str) -> dict:
    """La versión de Ollama y el digest del modelo; null si el servidor no responde."""
    try:
        return {"ollama_version": llm.version(), "modelo_digest": llm.digest(modelo)}
    except llm.LLMError:
        return {"ollama_version": None, "modelo_digest": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Responde una pregunta llamando herramientas.")
    parser.add_argument("-p", "--pregunta", required=True)
    parser.add_argument("--tarea", help="id de la tarea, para la traza")
    parser.add_argument("--log", type=Path, help="carpeta de trazas; sin esto no se escribe ninguna")
    parser.add_argument("--config", type=Path, default=configuracion.CONFIG)
    parser.add_argument("--dominio", default="mundial", choices=dominios.DOMINIOS)
    argumentos = parser.parse_args()

    config = configuracion.cargar(argumentos.config)
    registro = Registro(argumentos.log, argumentos.tarea) if argumentos.log else SinRegistro()
    modelo = config["modelo"]["nombre"]
    registro.evento("corrida_inicio", modelo=modelo,
                    config=config | {"dominio": argumentos.dominio} | entorno_del_servidor(modelo))
    try:
        fin = bucle(argumentos.pregunta, config, registro, argumentos.dominio)
    except Exception as error:  # noqa: BLE001 (la traza tiene que cerrarse pase lo que pase)
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=0,
                        motivo=f"{type(error).__name__}: {error}", detalle=traceback.format_exc()[-2000:])
        print(traceback.format_exc(), file=sys.stderr)
        return 1
    registro.evento("corrida_fin", estado=fin.estado, respuesta=fin.respuesta, pasos=fin.pasos, motivo=fin.motivo)
    print(fin.respuesta if fin.respuesta is not None else f"({fin.estado}: {fin.motivo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
