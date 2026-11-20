# Resultados del experimento offline

Modelo `GEARLY-20261107-L50` · 840 usuarios de prueba · alfa = 0.25 (elegido en validación) · semilla 20261107.

| Estrategia | NDCG@10 (k=1) | NDCG@10 (k=3) | NDCG@10 (k=5) |
|---|---|---|---|
| Azar | 0,0026 | 0,0027 | 0,0025 |
| popularidad | 0,0186 | 0,0186 | 0,0187 |
| contenido | 0,0130 | 0,0157 | 0,0188 |
| colaborativo | 0,0240 | 0,0437 | 0,0643 |
| hibrido | 0,0250 | 0,0431 | 0,0648 |

| Diferencia (k=3) | Media | IC 95 % |
|---|---|---|
| hibrido-contenido | 0,0274 | [0,0187; 0,0362] |
| hibrido-popularidad | 0,0245 | [0,0155; 0,0343] |
| hibrido-colaborativo | -0,0006 | [-0,0031; 0,0017] |
| colaborativo-contenido | 0,0281 | [0,0187; 0,0373] |

## Listas de 5 (NDCG@5, Precision@5, Recall@5)

Mismos 840 usuarios y condiciones que K = 10. Casos con menos de 5 candidatos excluidos: 0.

| Estrategia | NDCG@5 k=1 | NDCG@5 k=3 | NDCG@5 k=5 | P@5 k=3 | R@5 k=3 |
|---|---|---|---|---|---|
| Azar | 0,0018 | 0,0020 | 0,0019 | — | — |
| popularidad | 0,0154 | 0,0155 | 0,0156 | 0,0126 | 0,0215 |
| contenido | 0,0106 | 0,0118 | 0,0145 | 0,0067 | 0,0131 |
| colaborativo | 0,0215 | 0,0356 | 0,0543 | 0,0207 | 0,0441 |
| hibrido | 0,0225 | 0,0352 | 0,0538 | 0,0207 | 0,0426 |

| Diferencia NDCG@5 (k=3) | Media | IC 95 % |
|---|---|---|
| hibrido-contenido | 0,0235 | [0,0147; 0,0323] |
| hibrido-popularidad | 0,0197 | [0,0107; 0,0291] |
| hibrido-colaborativo | -0,0003 | [-0,0037; 0,0029] |
| colaborativo-contenido | 0,0238 | [0,0146; 0,0329] |

## Métricas técnicas (k = 3, K = 10)

| Estrategia | Cobertura | Listas vacías | Mediana ms | p95 ms |
|---|---|---|---|---|
| popularidad | 0.5 % | 0.0 % | 1.2 | 2.0 |
| contenido | 68.6 % | 0.0 % | 1.8 | 3.3 |
| colaborativo | 54.4 % | 0.0 % | 1.2 | 2.2 |
| hibrido | 57.5 % | 0.0 % | 2.9 | 4.0 |

Memoria pico del proceso del experimento: 59.7 MB. Equipo: Linux-6.18.44-fc-v726-x86_64-with-glibc2.39, Python 3.13.18, 2 núcleos, 7.8 GB de memoria.
