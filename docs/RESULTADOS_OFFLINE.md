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
