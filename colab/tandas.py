"""Correr una variante de recetas sobre un conjunto de tareas, en Drive y retomable.

Lo usan los notebooks 03 (desarrollo, tareas dev-*) y 04 (medición, tareas rec-*). Una tanda es
(conjunto, variante, temperatura, semilla); su carpeta en Drive se llama
`<conjunto>__<variante>__t<temperatura>__s<semilla>`.

Variantes:
  libro-cerrado  el modelo sin herramientas, con la heladera en el prompt;
  camino-fijo    una llamada con salida JSON y un pipeline sin loop;
  base           el agente sin planificación ni verificación;
  plan           el agente con planificación;
  verif          el agente con verificación antes de terminar;
  ambas          el agente con las dos.
"""
import json
from pathlib import Path

import config as configuracion
import evaluar
from harness import corridas, dominios

RAIZ = Path(__file__).resolve().parent.parent
CONJUNTOS = {"dev": RAIZ / "tareas" / "recetas_dev.json", "congelado": RAIZ / "tareas" / "recetas.json"}
AGENTE = ("base", "plan", "verif", "ambas")
VARIANTES = ("libro-cerrado", "camino-fijo", *AGENTE)


def tareas(conjunto: str) -> list[dict]:
    return json.loads(CONJUNTOS[conjunto].read_text(encoding="utf-8"))


def config_de(variante: str, temperatura: float, semilla: int) -> dict:
    """La configuración de la variante con la temperatura y la semilla de la tanda."""
    archivo = f"recetas_{variante}.toml" if variante in AGENTE else "recetas_base.toml"
    base = configuracion.cargar(RAIZ / "configs" / archivo)
    return corridas.config_con(base, temperatura=temperatura, semilla=semilla)


def corredor(variante: str, config: dict, trabajo: Path):
    if variante == "libro-cerrado":
        return corridas.corredor_libro_cerrado(config, dominios.sistema_libro_cerrado_recetas())
    if variante == "camino-fijo":
        return corridas.corredor_camino_fijo(config)
    if variante in AGENTE:
        trabajo.mkdir(parents=True, exist_ok=True)
        ruta = trabajo / "config_tanda.toml"          # el agente corre en otro proceso y lee la config de acá
        ruta.write_text(corridas.a_toml(config), encoding="utf-8")
        return corridas.corredor_agente(ruta, "recetas")
    raise ValueError(f"variante desconocida: {variante}. Las que hay: {', '.join(VARIANTES)}")


def correr(conjunto: str, variante: str, temperatura: float, semilla: int, *, quien: str, rutas: dict,
           manifiesto, antes_de_cada=None) -> tuple[Path, dict]:
    """Corre (o retoma) la tanda y devuelve su carpeta en Drive y el resumen de la corrida."""
    lista = tareas(conjunto)
    nombre = corridas.nombre_corrida(conjunto, variante, temperatura, semilla)
    config = config_de(variante, temperatura, semilla)
    trabajo = rutas["trabajo"] / nombre
    destino = rutas["corridas"] / nombre
    resumen = corridas.correr_tanda(lista, destino, trabajo, corredor(variante, config, trabajo),
                                    manifiesto=manifiesto(nombre, conjunto, config | {"variante": variante}, lista),
                                    quien=quien, antes_de_cada=antes_de_cada)
    return destino, resumen


def puntuar(conjunto: str, destino: Path, resultados: Path) -> tuple[list[dict], dict]:
    filas, resumen = evaluar.evaluar(tareas(conjunto), destino, evaluar.PESOS)
    evaluar.escribir_csv(filas, resultados / f"{destino.name}.csv")
    return filas, resumen
