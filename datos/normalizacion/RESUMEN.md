# Resumen de la normalización de unidades

Generado por `factibilidad/preparar_dataset.py`. No editar a mano.

## Embudo

| Paso | Recetas |
|---|---|
| recetasgratis.net | 18187 |
| con comensales, duración y al menos 3 líneas | 12473 |
| con todas las líneas reconocidas por el léxico (corpus base) | 5197 |
| sin problema o corregidas | 3198 |
| menos las excluidas por cantidad absurda (D20) | 3184 |
| **dataset final** | **3184** |

## Recetas del corpus base

| Estado | Recetas | Qué significa |
|---|---|---|
| sin_problema | 772 (15%) | todas sus cantidades ya venían en la unidad elegida |
| corregida | 2426 (47%) | al menos una cantidad se convirtió con una equivalencia «ok» |
| dudosa | 28 (1%) | usa al menos una equivalencia «dudosa»: apartada para revisión |
| descartada | 1971 (38%) | tiene una línea sin cantidad convertible |

## Líneas de ingrediente del corpus base

| Estado | Líneas | % de las no básicas |
|---|---|---|
| basico (sal, aceite, condimentos, hierbas) | 13910 | — |
| sin_cambio | 16376 | 59% |
| corregida | 8385 | 30% |
| dudosa | 58 | 0% |
| descartada | 2875 | 10% |

## Por qué se descartan líneas

| Motivo | Líneas |
|---|---|
| la línea no trae cantidad | 781 |
| sin equivalencia de «unidad» a «g» | 311 |
| «pizca» no es una cantidad convertible | 305 |
| sin equivalencia de «trozo» a «unidad» | 205 |
| «puñado» no es una cantidad convertible | 191 |
| sin equivalencia de «paquete» a «g» | 115 |
| sin equivalencia de «trozo» a «g» | 100 |
| «chorro» no es una cantidad convertible | 98 |
| sin equivalencia de «envase» a «ml» | 87 |
| sin equivalencia de «manojo» a «g» | 74 |
| sin equivalencia de «envase» a «g» | 73 |
| sin equivalencia de «barra» a «g» | 43 |
| sin equivalencia de «rodaja» a «g» | 42 |
| sin equivalencia de «rama» a «g» | 42 |
| sin equivalencia de «envase» a «unidad» | 37 |

## Equivalencias

La tabla tiene 126 equivalencias: 123 «ok» y 3 «dudosa». Se usan 124, más «PAR» (la cantidad que la propia receta escribe entre paréntesis).

Equivalencias dudosas, ordenadas por cuántas recetas destrabaría aprobarlas (recetas cuya única duda es esa):

| id | Equivalencia | Recetas que la usan | Se destraban si se aprueba | Nota |
|---|---|---|---|---|
| E38 | leche evaporada: 1 lata = 410 ml | 42 | 21 | latas de 315 a 410 g según la marca |
| P29 | tortilla de maiz: 1 unidad = 30 g | 16 | 7 | tortilla de maíz mediana ≈ 30 g; las de taco son más chicas |
| P30 | tortilla de harina: 1 unidad = 45 g | 0 | 0 | tortilla de harina mediana ≈ 45 g; las de burrito, más |
