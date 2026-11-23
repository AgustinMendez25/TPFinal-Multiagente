"""Línea de base «camino fijo» para recetas (propuesta, §6): una llamada al modelo y un pipeline sin loop.

1. Una sola llamada, con la salida restringida a un esquema JSON, traduce la pregunta a campos:
   contiene, excluye, dieta, porciones, que_pide, ingrediente y receta_id.
2. Un pipeline escrito de antemano, sin modelo: buscar_recetas → es_apta sobre las candidatas en orden
   (si hay dieta) → detalle_receta o faltantes → una respuesta armada por plantilla según `que_pide`.

No hay loop: si la pregunta no encaja en el esquema, el pipeline responde igual con lo que tenga, o null
cuando `que_pide` es «otro». Las trazas usan el mismo esquema que el agente, así que evaluar.py las
puntúa igual.
"""
import itertools
import json
import time
from pathlib import Path

import llm
from harness import dominios
from herramientas import recetas as H
from tareas.formato import pregunta_con_formato
from trazas.registro import Registro

QUE_PIDE = ["conteo", "receta_mas_rapida", "apta_si_no", "cantidad_ingrediente", "faltan_lista", "faltan_cuantos",
            "faltan_cantidad_ingrediente", "otro"]
ESQUEMA = {
    "type": "object",
    "properties": {
        "contiene": {"type": "array", "items": {"type": "string"}},
        "excluye": {"type": "array", "items": {"type": "string"}},
        "dieta": {"type": ["string", "null"], "enum": ["vegetariana", "vegana", "sin_gluten", "sin_lactosa", None]},
        "porciones": {"type": ["integer", "null"]},
        "que_pide": {"type": "string", "enum": QUE_PIDE},
        "ingrediente": {"type": ["string", "null"]},
        "receta_id": {"type": ["integer", "null"]},
    },
    "required": ["contiene", "excluye", "dieta", "porciones", "que_pide", "ingrediente", "receta_id"],
}
INSTRUCCION = """Traducí la pregunta a estos campos, sin responderla. Poné solo lo que la pregunta dice; lo que no dice va vacío o null.
- contiene: TODOS los ingredientes que la pregunta dice que la receta lleva, en singular (si dice «con X e Y», van los dos: [X, Y]). Si la pregunta habla de un ingrediente de la heladera por su vencimiento («el que vence primero»), usá el nombre que figura arriba.
- excluye: ingredientes que la receta no puede llevar. Una dieta no va acá: va en dieta («sin carne ni pescado» = vegetariana, «para veganos» = vegana, «para celíacos» = sin_gluten, «sin lácteos» = sin_lactosa).
- dieta: vegetariana, vegana, sin_gluten o sin_lactosa SOLO si la pregunta pide una dieta; si no, null.
- porciones: para cuántas personas, comensales o porciones, si la pregunta lo dice; si no, null.
- que_pide, uno de:
  conteo (cuántas recetas hay), receta_mas_rapida (el nombre de la receta más rápida que cumple todo),
  apta_si_no (si una receta cumple una dieta), cantidad_ingrediente (cuánto de un ingrediente lleva la receta),
  faltan_lista (qué ingredientes faltan comprar), faltan_cuantos (cuántos ingredientes faltan),
  faltan_cantidad_ingrediente (cuánto falta de un ingrediente), otro (cualquier otra cosa).
- ingrediente: el ingrediente por el que pregunta (para cantidad_ingrediente o faltan_cantidad_ingrediente), o null.
- receta_id: el número de receta si la pregunta lo nombra, o null.

Ejemplos:
«¿Cuál es la receta más rápida que lleva arroz y zanahoria?» → {"contiene": ["arroz", "zanahoria"], "excluye": [], "dieta": null, "porciones": null, "que_pide": "receta_mas_rapida", "ingrediente": null, "receta_id": null}
«Somos 3: ¿qué me falta comprar para la receta más rápida con papa que no lleve cebolla y sea vegana?» → {"contiene": ["papa"], "excluye": ["cebolla"], "dieta": "vegana", "porciones": 3, "que_pide": "faltan_lista", "ingrediente": null, "receta_id": null}

Pregunta: """


def _redondear(x: float):
    x = round(x, 2)
    return int(x) if x == int(x) else x


class _Pipeline:
    """Ejecuta herramientas y las registra en la traza como lo haría el loop (todas en el paso 1)."""

    def __init__(self, registro):
        self.registro = registro
        self.ids = itertools.count(1)

    def usar(self, nombre: str, **argumentos):
        ident = f"f-{next(self.ids)}"
        self.registro.evento("llamada_herramienta", paso=1, id=ident, nombre=nombre, argumentos=argumentos)
        inicio = time.perf_counter()
        datos = H.HERRAMIENTAS[nombre](**argumentos)
        texto = json.dumps(datos, ensure_ascii=False)
        self.registro.evento("resultado_herramienta", paso=1, id=ident, ok="error" not in datos, truncado=False,
                             caracteres=len(texto), duracion_ms=round((time.perf_counter() - inicio) * 1000),
                             contenido=texto[:4000])
        return datos

    @staticmethod
    def corregir(campos: dict) -> dict:
        """Regla fija del pipeline: una categoría de dieta escrita en `excluye` («carne», «gluten») pasa a `dieta`.
        Vuelta 2: dev-006, dev-011 y dev-012 terminaban en null porque buscar_recetas rechazaba «carne»."""
        excluye, dieta = [], campos.get("dieta")
        for nombre in campos.get("excluye") or []:
            categoria = H.CATEGORIAS.get(H.N.normalizar_texto(str(nombre)).strip())
            if categoria:
                dieta = dieta or categoria
            else:
                excluye.append(nombre)
        return campos | {"excluye": excluye, "dieta": dieta}

    def elegir(self, campos: dict) -> dict | None:
        """La receta del pipeline: la nombrada, o la primera candidata apta para la dieta."""
        if campos.get("receta_id"):
            return {"id": campos["receta_id"]}
        if not campos.get("contiene"):
            return None
        busqueda = self.usar("buscar_recetas", contiene=campos["contiene"], excluye=campos.get("excluye") or [])
        candidatas = busqueda.get("recetas", [])
        if campos.get("dieta"):
            return next((c for c in candidatas if self.usar("es_apta", receta_id=c["id"], dieta=campos["dieta"])
                         .get("apta")), None)
        return candidatas[0] if candidatas else None

    def responder(self, campos: dict):
        campos = self.corregir(campos)
        que_pide = campos.get("que_pide", "otro")
        if que_pide == "otro":
            return None
        if que_pide == "conteo":
            if not campos.get("contiene"):
                return None
            busqueda = self.usar("buscar_recetas", contiene=campos["contiene"], excluye=campos.get("excluye") or [])
            return None if "error" in busqueda else str(busqueda["total"])
        if que_pide == "apta_si_no":
            if not (campos.get("receta_id") and campos.get("dieta")):
                return None
            datos = self.usar("es_apta", receta_id=campos["receta_id"], dieta=campos["dieta"])
            return None if "error" in datos else ("sí" if datos["apta"] else "no")
        receta = self.elegir(campos)
        if receta is None:
            return None
        if que_pide == "receta_mas_rapida":
            return receta.get("nombre") or self.usar("detalle_receta", receta_id=receta["id"]).get("nombre")
        porciones = campos.get("porciones")
        if porciones is None:
            porciones = self.usar("detalle_receta", receta_id=receta["id"]).get("comensales")
            if porciones is None:
                return None
        ingrediente = H._canonico(campos["ingrediente"]) if campos.get("ingrediente") else None
        if que_pide == "cantidad_ingrediente":
            detalle = self.usar("detalle_receta", receta_id=receta["id"], porciones=porciones)
            cantidades = [i["cantidad"] for i in detalle.get("ingredientes", [])
                          if i["ingrediente"] == ingrediente and i["cantidad"] is not None]
            return str(_redondear(sum(cantidades))) if cantidades else None
        datos = self.usar("faltantes", receta_id=receta["id"], porciones=porciones)
        if "error" in datos:
            return None
        if que_pide == "faltan_lista":
            return "; ".join(datos["faltan"])
        if que_pide == "faltan_cuantos":
            return str(len(datos["faltan"]))
        if que_pide == "faltan_cantidad_ingrediente":
            fila = next((f for f in datos["ingredientes"] if f["ingrediente"] == ingrediente), None)
            return None if fila is None else str(fila["falta"])
        return None


def responder_tarea(tarea: dict, carpeta: Path, *, config: dict, chat=llm.chat) -> str:
    """Escribe la traza de una tarea y devuelve el estado final."""
    modelo = config["modelo"]
    registro = Registro(carpeta, tarea["id"])
    registro.evento("corrida_inicio", modelo=modelo["nombre"], config=config | {"linea_de_base": "camino_fijo"})
    pregunta = pregunta_con_formato(tarea)
    sistema = f"La heladera tiene esto, ordenado por vencimiento:\n{dominios.tabla_inventario()}"
    mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": INSTRUCCION + pregunta}]
    try:
        respuesta = chat(mensajes, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                         temperatura=modelo["temperatura"], semilla=modelo["semilla"], think=modelo["think"],
                         num_predict=modelo["num_predict"], formato=ESQUEMA, timeout_s=modelo["timeout_s"])
    except llm.LLMError as error:
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=1, motivo=str(error)[:300])
        return "error"
    contenido = respuesta.mensaje.get("content") or ""
    registro.evento("llamada_modelo", paso=1, modelo=modelo["nombre"], num_ctx=modelo["num_ctx"],
                    tokens_entrada=respuesta.tokens_entrada, tokens_salida=respuesta.tokens_salida,
                    duracion_ms=respuesta.duracion_ms, razon_fin=respuesta.razon_fin, texto=contenido[:500])
    try:
        campos = json.loads(contenido)
    except json.JSONDecodeError:
        registro.evento("corrida_fin", estado="error", respuesta=None, pasos=1, motivo="la salida no es JSON")
        return "error"
    registro.evento("campos", paso=1, campos=campos)
    final = _Pipeline(registro).responder(campos)
    estado = "respondida" if final is not None else "negada"
    registro.evento("corrida_fin", estado=estado, respuesta=final, pasos=1, motivo=f"que_pide={campos.get('que_pide')}")
    return estado
