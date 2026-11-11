# Resultados y discusión

Partición de prueba: 14,367 definiciones de 6,583 conceptos. Los candidatos son los 13,451
nodos del grafo menos los lemas de la definición. Las definiciones sin lemas en el grafo (74)
y aquellas cuyo objetivo no aparece en el ranking cuentan como fallo. Las pruebas de
significancia (McNemar sobre aciertos pareados) y los desgloses se reproducen con
`python scripts/analizar_resultados.py` (`reports/analisis_resultados.json`).

## Tabla comparativa

| Modelo | Grafo | Ponderación | p@1 | p@3 | p@5 | MRR | Cobertura | s/definición |
|---|---|---|---|---|---|---|---|---|
| node2vec, suma IDF | no dirigido, completo | p | **0.066** | **0.139** | **0.182** | **0.128** | 99.5 % | 0.005 |
| node2vec, suma | no dirigido, completo | p | 0.053 | 0.115 | 0.155 | 0.108 | 99.5 % | 0.005 |
| Grado | no dirigido, reducido | p | 0.023 | 0.056 | 0.083 | 0.061 | 71.6 % | 0.31 |
| Intermediación | dirigido, reducido | −log p | 0.008 | 0.021 | 0.032 | 0.026 | 42.1 % | 1.84 |
| Intermediación | dirigido, reducido | 100 − FA | 0.007 | 0.020 | 0.030 | 0.025 | 42.1 % | 2.30 |
| Cercanía | dirigido, reducido | 100 − FA | 0.009 | 0.022 | 0.032 | 0.024 | 42.1 % | 0.06 |
| Cercanía | dirigido, reducido | −log p | 0.009 | 0.022 | 0.032 | 0.024 | 42.1 % | 0.06 |
| Popularidad (referencia) | — | p | 0.000 | 0.000 | 0.000 | 0.001 | 99.5 % | 0.001 |

Cobertura = proporción de definiciones cuyo ranking contiene al objetivo. Tiempos medidos con
6 procesos en paralelo en un MacBook Air; la intermediación tardó unos 95 minutos por esquema
sobre la partición de prueba completa. node2vec usa la configuración elegida en desarrollo
(100 dimensiones, caminatas de longitud 80, 10 caminatas por nodo, p = q = 1); la exploración de
configuraciones está en `reports/node2vec_resultados.csv`.

**Comparación con la Tabla 1 (NAP).** En clase, la mejor centralidad alcanzó p@5 = 0.518 con
276 descripciones de 56 conceptos. Nuestros valores son mucho menores, pero no son
comparables directamente: (1) evaluamos 14,367 glosas de diccionario para 6,583 conceptos, no
descripciones escritas por personas para un conjunto pequeño de conceptos; (2) las glosas de
Wikcionario son formales e incluyen acepciones poco frecuentes (en 2,504 errores de node2vec
otra acepción del mismo concepto sí se acierta); (3) cada definición compite contra 13,451
candidatos. El modelo de popularidad, que ignora la definición, obtiene p@5 = 0.0003, lo que
sitúa los resultados entre 100 y 600 veces por encima del azar informado.

## P1. ¿Qué se pierde al modelar con un grafo no dirigido?

Las asociaciones son asimétricas: solo el 17.2 % de las aristas son recíprocas, así que
simetrizar el grafo mezcla dos relaciones distintas (lo que una palabra evoca y lo que la
evoca). Pero en esta tarea la dirección "correcta" resultó ser la inversa a la de las aristas.
Las palabras de una definición suelen ser respuestas que el objetivo evoca (*perro → ladrar*),
no estímulos que lo evoquen. El subgrafo reducido dirigido sigue solo las aristas salientes
de los lemas, y el objetivo quedó fuera de él en el 57.4 % de las definiciones (8,247 de 14,367):
ninguna medida calculada sobre ese subgrafo puede recuperarlo. Grado, que trabaja sobre la
versión no dirigida, alcanza una cobertura de 71.6 % y duplica el MRR de cercanía e
intermediación. En node2vec se observa lo mismo: caminar sobre el grafo dirigido bajó el MRR de
desarrollo de 0.125 a 0.087 (`reports/node2vec_resultados_dirigido.csv`).

Lo que se pierde al simetrizar es la fuerza propia de cada dirección: la arista no dirigida
promedia p(u→v) y p(v→u), así que una asociación fuerte en un sentido y nula en el otro queda a
la mitad. Una alternativa que conservaría ambas informaciones es buscar sobre el grafo
transpuesto (aristas respuesta → estímulo) o expandir la vecindad por predecesores.

## P2. ¿La cercanía mejora p@5 respecto a la intermediación, pero no p@1?

No se reproduce el patrón de clase. Con 100 − FA, la cercanía supera a la intermediación tanto
en p@1 (0.0090 frente a 0.0072, p = 0.052) como en p@5 (0.0321 frente a 0.0298, p = 0.13); con
−log p las diferencias son mínimas y no significativas (p@1 0.0086 frente a 0.0079, p = 0.50; p@5
0.0315 frente a 0.0323, p = 0.62). Ambas medidas comparten el mismo subgrafo y por tanto el
mismo techo de cobertura (42.1 %); con más de la mitad de los objetivos fuera de su alcance, el
orden dentro del subgrafo pesa poco. La diferencia relevante con nuestro recurso es de costo:
la intermediación es entre 30 y 40 veces más lenta para el mismo desempeño.

## P3. ¿Qué ponderación funciona mejor y por qué?

En cercanía las dos ponderaciones son equivalentes (p@5 0.0321 frente a 0.0315, p = 0.62). En
intermediación, −log p es mejor de forma significativa (p@5 0.0323 frente a 0.0298, p < 0.001;
p@1 0.0079 frente a 0.0072, p = 0.044). La explicación está en la transformación: como FA rara
vez supera 30, 100 − FA comprime casi todos los costos entre 70 y 100, de modo que el camino más
corto se parece al de menos saltos y muchos caminos empatan. −log p separa más las asociaciones
débiles de las fuertes, lo que cambia qué nodos quedan en los caminos más cortos, que es
justo lo que mide la intermediación. La cercanía, en cambio, suma distancias de uno o dos saltos
desde los lemas, y ambas transformaciones son monótonas en p, así que el orden apenas cambia.
Para node2vec se usa p como probabilidad de transición, no un costo.

## P4. ¿Cómo afectan las respuestas vacías, mal escritas o no normalizadas?

- **Vacías:** 25.7 % de las respuestas posibles estaban vacías o eran `NA` / `No more
  responses`. Si se contaran en el denominador, todas las fuerzas bajarían y los marcadores
  aparecerían como nodos muy conectados. Al compararnos con las fuerzas oficiales vimos que los
  autores conservan algunos de esos marcadores como respuestas, lo que cambia el denominador en
  1 para 18 estímulos (`reports/validacion_fuerzas.json`).
- **No normalizadas:** pasar a minúsculas fusionó 5 estímulos duplicados y variantes de
  respuestas como *Rexona*/*rexona*, que sumaron su frecuencia. El costo es fusionar nombres
  propios con sustantivos (*Boca*, el club, con *boca*).
- **Mal escritas e idiosincrásicas:** de 1,056,083 pares estímulo–respuesta solo 835,616 (79 %)
  tienen como respuesta otro estímulo. Restringir el grafo a estímulos funciona como filtro
  ortográfico (una respuesta mal escrita casi nunca es estímulo), a cambio de perder respuestas
  válidas pero raras. Además, 42 estímulos quedaron fuera de la mayor componente fuertemente
  conexa (el grafo previo tenía 43 componentes fuertes).
- El vocabulario final incluye 19 nodos con dígitos o puntuación (`covid-19`, `mcdonald's`,
  `8 horas`), que son asociaciones legítimas.

## P5. ¿En qué definiciones gana el grafo y en cuáles node2vec?

Comparando por definición la mejor centralidad (grado) con node2vec suma IDF: node2vec obtiene
mejor rango recíproco en el 71.5 % de las definiciones, grado en el 25.8 % y empatan en el 2.7 %.
node2vec gana en todas las categorías gramaticales y tamaños de definición:

| Subconjunto | Definiciones | p@5 grado | p@5 node2vec | Gana grado |
|---|---|---|---|---|
| Sustantivos | 8,732 | 0.086 | 0.196 | 26.6 % |
| Adjetivos | 3,261 | 0.067 | 0.144 | 27.0 % |
| Verbos | 2,374 | 0.093 | 0.182 | 21.1 % |
| 1–2 lemas | 2,497 | 0.080 | 0.152 | 22.9 % |
| 3–5 lemas | 7,098 | 0.079 | 0.183 | 25.8 % |
| 6–9 lemas | 3,458 | 0.084 | 0.182 | 27.4 % |
| 10 o más lemas | 1,240 | 0.111 | 0.244 | 28.6 % |

La ventaja relativa del grafo crece con la longitud de la definición (gana en el 22.9 % de las
definiciones de 1–2 lemas y en el 28.6 % de las de 10 o más). Una explicación plausible es que
con muchos lemas las conexiones directas acumulan evidencia, mientras que con pocos lemas
node2vec aprovecha la vecindad extendida que capturan las caminatas. Los verbos son la
categoría donde el grafo gana con menos frecuencia (21.1 %). Los modelos son complementarios: 371 definiciones
solo las acierta grado en el top 5, 1,794 solo node2vec y 820 ambos. Un oráculo que eligiera el
mejor de los dos por definición llegaría a p@5 = 0.208 (frente a 0.182), lo que motiva una
fusión de rankings como trabajo futuro.

## Análisis de errores

Se considera error que el objetivo no quede en el top 5.

| Modelo | Errores | Sin lemas | Objetivo fuera del ranking | Rango 6–20 | Rango > 20 |
|---|---|---|---|---|---|
| node2vec suma IDF | 11,753 | 74 | 0 | 2,141 | 9,538 |
| Grado | 13,176 | 74 | 4,009 | 1,725 | 7,368 |
| Cercanía 100 − FA | 13,906 | 74 | 8,247 | 591 | 4,994 |
| Intermediación −log p | 13,903 | 74 | 8,247 | 791 | 4,791 |

En las centralidades la causa dominante es estructural (objetivo fuera del subgrafo, P1). El
análisis cualitativo de 17 casos de node2vec, clasificados por causa (polisemia del objetivo o
de un lema de la definición, palabras fuera del vocabulario, sesgo hacia nodos muy conectados,
sinónimos válidos, composición por suma y descripciones poco discriminantes), está en
`reports/node2vec_analisis_errores.md`.

## Costo computacional y grafo completo

Las centralidades se evaluaron solo sobre el grafo reducido. El grafo completo tiene 13,451
nodos y 833,440 aristas, y cada medida depende de la definición, así que se recalcula para cada
una de las 14,367 definiciones de prueba. Estimaciones sobre un grafo sintético del mismo número
de nodos: un Dijkstra desde una fuente tarda alrededor de 0.25 s, por lo que la cercanía desde
~5 lemas costaría unas 5 horas de CPU y la intermediación por subconjunto (fuentes y destinos
= lemas) unas 10 horas; la intermediación exacta de todos los nodos tarda del orden de 1.7 horas
por cálculo, pero no depende de la definición. Con el grafo reducido, cercanía tardó unos 2
minutos e intermediación unos 95 minutos por esquema (6 procesos). Evaluar la intermediación por
subconjunto en el grafo completo, que fue la mejor medida en clase, queda como trabajo futuro.

## Limitaciones

- Las glosas de diccionario son más formales que las descripciones de personas, y no
  recolectamos descripciones propias.
- Restringir el grafo a estímulos excluye respuestas válidas pero raras.
- node2vec asigna un vector por nodo y no separa sentidos (polisemia).
- La partición es por concepto; los resultados de prueba no comparten objetivos con desarrollo,
  pero sí el mismo grafo y las mismas normas.
