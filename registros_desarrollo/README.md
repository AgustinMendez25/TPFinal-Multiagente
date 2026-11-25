# Registro de desarrollo con el asistente de código

ENUNCIADO §9: «las sesiones exportadas del asistente que usaron, o un registro con los pedidos principales y
qué se aceptó o se descartó de cada uno». Esto es lo segundo.

**Qué usamos.** Claude Code (modelo Claude Opus 5.5) sobre este repositorio. Cada commit que escribió el asistente lleva la línea `Co-Authored-By: Claude`; los que no la
llevan los escribió el grupo a mano (`git log` los separa). El asistente no corrió nunca el modelo del
agente: todas las corridas las hicimos nosotros en Colab, y el asistente leyó los resultados desde Drive.

**Cómo trabajamos con él** (las pautas del ENUNCIADO §9):

- El diseño se escribió antes que el código (`docs/superpowers/specs/` y `docs/superpowers/plans/`), con
  criterios de terminado verificables: por ejemplo, «las herramientas coinciden con el generador en todo el
  corpus».
- Cada pieza tiene tests sin modelo (un LLM falso para el loop). Los tests corren en local antes de cada
  commit; las corridas con el modelo, en Colab.
- Las decisiones las tomamos nosotros a partir de las trazas, y quedaron en `decision_log.md`. El asistente
  las propone, las escribe y las implementa.
- Las tandas en paralelo se repartieron por archivos de Drive (`tomada.json`), no por convención.

## Pedidos principales

| Fecha | Pedido | Qué se aceptó | Qué se descartó o cambió |
|---|---|---|---|
| 21/11 | Pasar de la propuesta aprobada a un plan de todo el proyecto | Diseño en notebooks de Colab que clonan el repo; la lógica en módulos con tests; trazas en Drive, retomables (spec y plan de la Etapa 1) | Escribir todo dentro de los notebooks; sincronizar a Drive cada N tareas; guardar el modelo en Drive (decision log, 21/11) |
| 21/11 | El loop del Bloque 1 | Un solo loop para los dos dominios; errores devueltos al modelo con la corrección; validación contra la ficha JSON; reintentos con espera exponencial; `ContextOverflow` sin reintento | — |
| 23/11 | Arreglo del Bloque 1 después de la corrida «antes» | Rescatar `terminar` escrito como texto; no volver a ejecutar llamadas idénticas; filtros `seleccion` y `eliminatorias` en `partidos` | Rescatar cualquier texto que parezca respuesta; subir `num_ctx` o el tope de resultados; un filtro `solo_penales` hecho para una pregunta |
| 23/11 | Herramientas de recetas, detector, plan, verificación y líneas de base | Herramientas comprobadas contra el generador en todo el corpus; detector con reglas ajustadas solo con `dev-*`; verificación en código con un solo rechazo | — |
| 23/11 | Recetas con cantidades absurdas («400 kg de nueces») | Excluir 14 recetas con un error claro (D20); comprobar que ninguna tarea cambia | Corregirlas a mano; excluir también 3 plausibles (codillo, leche, ajo), que el asistente había propuesto en un primer momento |
| 23/11 | Vueltas 2 a 5 de desarrollo sobre `dev-*` | Los cambios de cada vuelta, con lo que se vio en las trazas (decision log) | Seguir ajustando por `dev-020`, que falla en las seis variantes |
| 23/11 | Análisis de las mediciones | Test de signo por pares, Wilson, pass@k, voto de mayoría y frontera, declarados antes de medir (Clase 12) | — |
| 23/11 | Correr las tandas en paralelo entre cuentas | Una cola de tandas en el notebook 04 en lugar de un reparto fijo por persona; confirmar la toma a los 30 s, después de ver una tanda duplicada en `dev-v2__base` | Un reparto de tandas por cuenta armado a mano, que el asistente había propuesto antes de ver el notebook 04 |
| 23/11 | Antes del tag `medicion-v1` | Un log de Ollama por sesión; la GPU de cada sesión guardada en la tanda | — |
| 24/11 | Cierre | Copia de las 58 corridas reportadas al repo, README, notebook de demo, cierre del decision log y borrador del informe | — |

## Qué conviene saber al leer el código

- **Lo que propuso el asistente y corregimos.** El asistente sugirió en un momento usar varias cuentas de
  Colab por persona para paralelizar, y él mismo advirtió que eso puede ir contra los términos de Colab.
- **Lo que el asistente escribió y revisamos a mano.** Las respuestas esperadas de las tareas las calcula un
  script (`factibilidad/borrador_respuestas.py`), y la revisión manual de las equivalencias de unidades
  está registrada en `datos/normalizacion/revision_equivalencias_2026-11-13_aprobada.csv`.
- **El informe.** El asistente escribió un borrador a partir de las tablas del notebook 05 y del decision
  log. El grupo lo revisa y es responsable de cada afirmación.
