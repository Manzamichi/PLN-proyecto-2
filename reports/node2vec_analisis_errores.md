# Análisis de errores del modelo híbrido con node2vec

Modelo: configuración 2 (100 dimensiones, walk_length 80, num_walks 10, p = q = 1) con
suma ponderada por IDF, guardado en `data/processed/node2vec.kv`. Partición de prueba de
`particion.csv`: 14,367 definiciones de 6,583 conceptos.

Detalle por definición en `reports/node2vec_errores_prueba.csv`, generado con:

```powershell
.venv/Scripts/python.exe scripts/errores_node2vec.py
```

Se considera error cuando el concepto objetivo no queda entre los 5 primeros candidatos:
**11,753 de 14,367 definiciones (81.8 %)**. De ellas, 2,141 quedan entre los lugares 6 y 20,
y 3,414 después del lugar 1000 o sin ranking.

## Pistas automáticas

El script asigna una pista por definición con reglas simples, en este orden. Solo orientan;
la causa de los casos de la tabla siguiente se asignó a mano.

| Pista | Regla | Errores |
|---|---|---|
| Sin lemas en el grafo | la definición no tiene lemas útiles | 74 |
| Variante morfológica en top 5 | un candidato del top 5 tiene el mismo lema de spaCy que el objetivo | 71 |
| Palabras fuera del vocabulario | cobertura léxica menor a 0.5 | 232 |
| Otra acepción sí se acierta | otra definición del mismo concepto queda en el top 5 | 2,433 |
| Top 1 muy conectado | el primer candidato está en el 10 % de nodos de mayor grado (≥ 183) | 2,383 |
| Revisar | ninguna de las anteriores | 6,560 |

## Casos clasificados

Se eligieron casos en los que la falla es propia de la tarea, de las normas o del método
(polisemia, vocabulario de las normas, composición por suma), con definiciones cuyos lemas
se preprocesaron sin problemas. Rango = posición del objetivo en el ranking completo
(13,451 nodos menos los lemas de entrada).

| # | Concepto | Definición (Wikcionario) | Lemas en el grafo | Rango | Top 5 | Causa | Explicación |
|---|---|---|---|---|---|---|---|
| 1 | dragón | Soldado de cualquiera de varios antiguos cuerpos de infantería… | soldado, antiguo, cuerpo, montura, combate, caballería, … | 3,411 | caudillo, caballo, jinete, gaucho, yelmo | Polisemia del objetivo | Sentido militar poco común. Las respuestas a `dragón` son `fuego`, `mitología`, `fantasía`, y la acepción del animal fantástico sí queda en el lugar 2. |
| 2 | grillo | Uno de dos anillos de hierro que se ponen en los tobillos… | anillo, hierro, tobillo, impedir, movimiento, esclavo, … | 7,480 | cadenas, caminar, pierna, pantorrilla, andando | Polisemia del objetivo | Sentido de grillete; las respuestas a `grillo` son `insecto`, `ruido`, `bicho`, `noche`, y la acepción del insecto sí queda en el lugar 3. |
| 3 | capaz | Dicho de un recinto o recipiente, de gran volumen. | recinto, recipiente, volumen | 7,411 | espacio, envase, área, pote, contenedor | Polisemia del objetivo | En SWOW-RP las respuestas más fuertes a `capaz` son `quizás` y `tal vez` (uso rioplatense) e `inteligente`, `apto`, `hábil`; ninguna remite a capacidad física. |
| 4 | condicionado | Dicho de un video o una película: pornográfico. | video, película, pornográfico | 5,143 | videos, porno, filmación, audiovisual, cine | Polisemia del objetivo | Sentido poco común: las respuestas a `condicionado` son `aire`, `limitado`, `restringido`. La acepción «limitado por alguna condición» queda en el lugar 3. |
| 5 | cuello | Parte superior angosta de una vasija u otro recipiente | superior, angosta, vasija, recipiente | 959 | estrecha, ancha, cuenco, tupper, vajilla | Polisemia del objetivo | Las respuestas a `cuello` son sobre todo del cuerpo (`cabeza`, `garganta`, `jirafa`). Las acepciones del cuerpo y de la ropa quedan en los lugares 62 y 48. |
| 6 | olfatear | Buscar información, particularmente secreta o no obvia, con mucho interés, curiosidad o empeño. | buscar, información, secreto, obvio, interés, curiosidad, empeño | 742 | investigar, averiguar, indagar, investigación, saber | Polisemia (sentido figurado) | Los candidatos describen bien el sentido figurado, pero las respuestas a `olfatear` son literales (`oler`, `nariz`, `perro`, `olor`). |
| 7 | mórbido | Propio de o relativo a una enfermedad. | relativo, enfermedad | 191 | patología, síntomas, síndrome, contagio, antibiótico | Polisemia (colocación dominante) | Las respuestas a `mórbido` son `muerte`, `obeso`, `morboso`, `gordo`, `obesidad`: domina la colocación «obesidad mórbida» y no el sentido médico general. |
| 8 | liberar | Poner fin a una ocupación militar u otro yugo. | ocupación, militar, yugo | 5,587 | trabajo, laburo, labor, empleo, empleado | Polisemia de un lema de la definición | `ocupación` se interpreta como empleo y arrastra a `trabajo` (grado 2,422). |
| 9 | veterano | De edad avanzada, senil. | edad, avanzado | 33 | adelantado, madurez, adultez, años, envejecimiento | Polisemia de un lema de la definición | `avanzado` se lee como `adelantado` (progreso) y no como vejez; con solo dos lemas, ese sentido decide el primer lugar. |
| 10 | inmutable | Que no es mudable. | (ninguno) | — | — | Palabras fuera del vocabulario | `mudable` no está en las normas y la negación no se puede representar con una suma de vectores. |
| 11 | agraciado | Que es grato a la vista; bien parecido, bello. | grato, vista, parecido, bello | 25 | lindo, hermoso, pintoresco, vistoso, bonito | Sesgo hacia nodos muy conectados | Los candidatos son sinónimos correctos, pero muy conectados (`lindo`, grado 1,046) frente al objetivo (grado 86). |
| 12 | inaudito | Bajo, despreciable, ruin, vil. | despreciable, ruin, vil | 1,292 | malo, mala persona, malvado, malicioso, maldito | Sesgo hacia nodos muy conectados | `malo` (grado 1,432) concentra el sentido de la definición; además es un sentido poco común de `inaudito` (grado 73). |
| 13 | infumable | Persona insoportable o difícil de tratar. | persona, insoportable, difícil, tratar | 8 | inaguantable, intolerable, insufrible, problemático, imbancable | Sinónimos válidos | Los cinco candidatos son respuestas aceptables; la evaluación solo acepta la palabra exacta. |
| 14 | despelote | Grupo de personas en desorden y haciendo ruido; barullo. | grupo de personas, desorden, ruido, barullo | 13 | bullicio, bochinche, alboroto, quilombo, ruidoso | Sinónimos válidos | Los candidatos son sinónimos rioplatenses del objetivo (`bochinche`, `quilombo`). Otra acepción de `despelote` sí queda en el lugar 4. |
| 15 | pensador | Que piensa, especialmente si se dedica a eso como afición u oficio. | pensar, dedicar, afición, oficio | 1,568 | dedicación, hobbie, hobby, pasatiempos, actividad | Ponderación de la composición | El núcleo es `pensar`, pero la IDF da más peso a palabras secundarias menos frecuentes (`afición`, `oficio`). |
| 16 | honrar | Mostrar o tratar con un alto nivel de respeto. | mostrar, tratar, alto, nivel, respeto | 53 | estatus, categoría, valoración, escalafón, estatura | Composición por suma | `alto` y `nivel` suman en la misma dirección y llevan la definición hacia jerarquías (`estatus`, `escalafón`), por encima de `respeto`. |
| 17 | puerco | Animal mamífero, artiodáctilo, de cuerpo robusto y piel gruesa… | animal, mamífero, cuerpo, piel, carne, cuero, jabalí, … | 57 | bisonte, carnívoro, búfalo, bovino, carpincho | Descripción poco discriminante | Los rasgos son compartidos por muchos mamíferos; la suma cae en la zona de animales grandes, pero no distingue al objetivo. |

## Observaciones generales

- **Definiciones cortas.** Con 1 o 2 lemas útiles el MRR es 0.103 y p@5 0.151; con 10 o más
  lemas sube a 0.170 y 0.243. Con pocos lemas, uno genérico o mal interpretado decide el ranking.
- **Polisemia.** En 2,504 errores otra definición del mismo concepto sí queda en el top 5. Las
  normas reflejan el sentido más común de cada palabra y Wikcionario incluye acepciones raras.
  node2vec da un solo vector por nodo, así que no puede separar sentidos.
- **Sesgo hacia nodos conectados.** Es moderado: entre los errores, el grado mediano del primer
  candidato es 109 frente a 92 del objetivo, y en el 57.4 % de los errores el primer candidato
  tiene más grado que el objetivo.
- **Plantillas de diccionario.** Las 514 definiciones del tipo «Acción y efecto de…» tienen MRR
  0.190, mayor que el resto (0.125), porque el verbo base suele ser nodo. Cuando no lo es,
  quedan `acción` y `efecto` y el modelo responde `consecuencia` (107 de esas definiciones).

## Limitaciones del análisis

Las pistas automáticas no son excluyentes y una definición puede tener varias causas; la
tabla asigna la principal. La comparación de errores con los modelos de centralidad (pregunta
guía 5) requiere su detalle por definición con los mismos `id`.
