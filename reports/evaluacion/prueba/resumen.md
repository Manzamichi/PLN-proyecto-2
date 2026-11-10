# Evaluación — prueba

| modelo | n | p@1 | p@3 | p@5 | mrr | cobertura_modelo | cobertura_lexica | rango_mediano_encontrados | segundos_por_definicion |
|---|---|---|---|---|---|---|---|---|---|
| node2vec_suma_idf | 14,367 | 0.0661 | 0.1390 | 0.1819 | 0.1276 | 0.9948 | 0.8540 | 81.0000 | 0.0052 |
| node2vec_suma | 14,367 | 0.0533 | 0.1149 | 0.1549 | 0.1083 | 0.9948 | 0.8540 | 104.0000 | 0.0051 |
| grado | 14,367 | 0.0228 | 0.0559 | 0.0829 | 0.0608 | 0.7158 | 0.8540 | 63.0000 | 0.3066 |
| intermediacion_logp | 14,367 | 0.0079 | 0.0208 | 0.0323 | 0.0255 | 0.4208 | 0.8540 | 81.0000 | 1.8356 |
| intermediacion_fa | 14,367 | 0.0072 | 0.0203 | 0.0298 | 0.0246 | 0.4208 | 0.8540 | 82.0000 | 2.2989 |
| cercania_fa | 14,367 | 0.0090 | 0.0221 | 0.0321 | 0.0242 | 0.4208 | 0.8540 | 126.0000 | 0.0556 |
| cercania_logp | 14,367 | 0.0086 | 0.0217 | 0.0315 | 0.0238 | 0.4208 | 0.8540 | 114.5000 | 0.0588 |
| popularidad | 14,367 | 0.0002 | 0.0002 | 0.0003 | 0.0011 | 0.9948 | 0.8540 | 5511.0000 | 0.0007 |

p@k y mrr cuentan como fallo las definiciones sin lemas en el grafo o cuyo objetivo no aparece en el ranking.
