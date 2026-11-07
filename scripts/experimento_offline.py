"""Experimento offline de Gearly: compara POP, CONT, CF e HIB con el protocolo del capítulo III.

Uso:  python scripts/experimento_offline.py CARPETA_DATOS
Requiere haber ejecutado preparar_datos.py. Escribe docs/resultados_offline.json y docs/RESULTADOS_OFFLINE.md.

- Escenarios: k = 1, 3 y 5 señales visibles (prefijos del apoyo). Principal: k = 3, K = 10.
- Candidatos: catálogo menos las señales visibles. Objetivos: positivas posteriores al apoyo.
- Alfa del híbrido: se elige en validación entre 0,25 / 0,50 / 0,75 (NDCG@10, k = 3) y se aplica sin cambios en prueba.
- Incertidumbre: bootstrap por usuarios, 2000 remuestreos, semilla fija.
- Azar: media de 30 listas aleatorias por usuario.
"""
import json
import math
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'backend'))
from app.recomendador import Recomendador, _ordenar  # noqa: E402

K = 10
SEMILLA = 20261107


def metricas(lista, objetivos):
    rel = set(objetivos)
    aciertos = [1 if x in rel else 0 for x in lista[:K]]
    dcg = sum(a / math.log2(j + 2) for j, a in enumerate(aciertos))
    idcg = sum(1 / math.log2(j + 2) for j in range(min(len(rel), K)))
    return {'ndcg': dcg / idcg if idcg else 0.0, 'precision': sum(aciertos) / K, 'recall': sum(aciertos) / len(rel) if rel else 0.0}


def evaluar(rec, casos, metodo, k):
    filas, vistos = [], set()
    todos = list(rec.productos)
    for c in casos:
        visibles = c['apoyo'][:k]
        cand = [p for p in todos if p not in set(visibles)]
        puntos, _ = rec.puntajes(metodo, [], [], visibles, cand)
        lista = [p for p, _ in _ordenar(puntos, K)]
        if len(lista) < K:  # completa con popularidad y lo registra
            extra = [p for p, _ in _ordenar({p: float(rec.popularidad.get(p, 0)) for p in cand if p not in lista}, K - len(lista))]
            lista += extra
        vistos.update(lista)
        m = metricas(lista, c['objetivos'])
        m['completada'] = len(puntos) < K
        filas.append(m)
    return filas, len(vistos) / len(todos)


def azar(rec, casos, k, reps=30):
    rnd = random.Random(SEMILLA); todos = list(rec.productos); out = []
    for c in casos:
        vis = set(c['apoyo'][:k]); cand = [p for p in todos if p not in vis]
        out.append(sum(metricas(rnd.sample(cand, K), c['objetivos'])['ndcg'] for _ in range(reps)) / reps)
    return out


def bootstrap(a, b, n=2000):
    rnd = random.Random(SEMILLA); d = [x - y for x, y in zip(a, b)]; N = len(d)
    medias = sorted(sum(d[rnd.randrange(N)] for _ in range(N)) / N for _ in range(n))
    return sum(d) / N, medias[int(0.025 * n)], medias[int(0.975 * n) - 1]


def media(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def main():
    carpeta = Path(sys.argv[1]).resolve()
    catalogo = json.load(open(RAIZ / 'data/catalogo.json', encoding='utf-8'))
    modelo = json.load(open(RAIZ / 'data/modelo.json', encoding='utf-8'))
    ev = json.load(open(carpeta / 'evaluacion.json'))
    rec = Recomendador(catalogo, modelo)

    ajuste = {}
    for alfa in (0.25, 0.5, 0.75):
        rec.alfa = alfa
        ajuste[alfa] = media([m['ndcg'] for m in evaluar(rec, ev['validacion'], 'hibrido', 3)[0]])
    rec.alfa = max(ajuste, key=lambda a: (ajuste[a], -abs(a - 0.5)))
    print('Ajuste en validación (NDCG@10, k=3):', ajuste, '-> alfa =', rec.alfa)
    modelo['alfa'] = rec.alfa  # la app usa el mismo alfa elegido en validación
    json.dump(modelo, open(RAIZ / 'data/modelo.json', 'w', encoding='utf-8'), ensure_ascii=False)

    casos = ev['prueba']; res = {}; por_usuario = {}
    for k in (1, 3, 5):
        por_usuario[('azar', k)] = azar(rec, casos, k)
        res[f'azar_k{k}'] = {'ndcg10': media(por_usuario[('azar', k)])}
        for m in ('popularidad', 'contenido', 'colaborativo', 'hibrido'):
            filas, cob = evaluar(rec, casos, m, k)
            por_usuario[(m, k)] = [f['ndcg'] for f in filas]
            res[f'{m}_k{k}'] = {'ndcg10': media([f['ndcg'] for f in filas]), 'precision10': media([f['precision'] for f in filas]),
                                'recall10': media([f['recall'] for f in filas]), 'cobertura': cob,
                                'listas_completadas_con_popularidad': sum(f['completada'] for f in filas) / len(filas)}
            print(f'k={k} {m:13s} NDCG@10={res[f"{m}_k{k}"]["ndcg10"]:.4f}')
    difs = {}
    for k in (1, 3, 5):
        for a, b in (('hibrido', 'contenido'), ('hibrido', 'popularidad'), ('hibrido', 'colaborativo'), ('colaborativo', 'contenido')):
            difs[f'{a}-{b}_k{k}'] = bootstrap(por_usuario[(a, k)], por_usuario[(b, k)])
    salida = {'semilla': SEMILLA, 'K': K, 'usuarios_prueba': len(casos), 'usuarios_validacion': len(ev['validacion']),
              'modelo': modelo['version'], 'alfa_elegido': rec.alfa, 'ajuste_validacion': ajuste, 'resultados': res,
              'diferencias_ndcg10_ic95': {k: {'media': v[0], 'ic_inf': v[1], 'ic_sup': v[2]} for k, v in difs.items()}}
    (RAIZ / 'docs').mkdir(exist_ok=True)
    json.dump(salida, open(RAIZ / 'docs/resultados_offline.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    f = lambda x: f'{x:.4f}'.replace('.', ',')
    md = [f'# Resultados del experimento offline\n\nModelo `{modelo["version"]}` · {len(casos)} usuarios de prueba · '
          f'alfa = {rec.alfa} (elegido en validación) · semilla {SEMILLA}.\n',
          '| Estrategia | NDCG@10 (k=1) | NDCG@10 (k=3) | NDCG@10 (k=5) |', '|---|---|---|---|',
          '| Azar | ' + ' | '.join(f(res[f'azar_k{k}']['ndcg10']) for k in (1, 3, 5)) + ' |']
    for m in ('popularidad', 'contenido', 'colaborativo', 'hibrido'):
        md.append(f'| {m} | ' + ' | '.join(f(res[f'{m}_k{k}']['ndcg10']) for k in (1, 3, 5)) + ' |')
    md += ['', '| Diferencia (k=3) | Media | IC 95 % |', '|---|---|---|']
    for c in ('hibrido-contenido', 'hibrido-popularidad', 'hibrido-colaborativo', 'colaborativo-contenido'):
        m_, lo, hi = difs[f'{c}_k3']
        md.append(f'| {c} | {f(m_)} | [{f(lo)}; {f(hi)}] |')
    (RAIZ / 'docs/RESULTADOS_OFFLINE.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('Escrito docs/resultados_offline.json y docs/RESULTADOS_OFFLINE.md')


if __name__ == '__main__':
    main()
