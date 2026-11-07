"""Prepara el catálogo, el modelo congelado y los conjuntos de evaluación de Gearly.

Uso:  python scripts/preparar_datos.py CARPETA_DATOS [--max-por-disciplina 1000]

Entradas (en CARPETA_DATOS, ver descargar_datos.py):
  Sports_and_Outdoors.csv          user_id, parent_asin, rating, timestamp (5-core)
  meta_Sports_and_Outdoors.jsonl   metadatos de productos
Salidas:
  data/catalogo.json               productos del catálogo (sí se versiona; no contiene reseñas)
  data/modelo.json                 popularidad y vecinos colaborativos, solo con entrenamiento antes de T0
  CARPETA_DATOS/evaluacion.json    usuarios de validación y prueba con señales de apoyo y objetivos
  data/manifiesto.json             conteos de cada regla, fechas de corte y semilla (ficha D01/D02)

Protocolo (capítulo III del documento):
  - Positiva = calificación 4 o 5. Se conserva la primera reseña por par usuario-producto.
  - Usuarios a entrenamiento / validación / prueba por hash con semilla: 70 / 15 / 15 %.
  - T0 = percentil 60 de las fechas; T1 = percentil 80.
  - El modelo (popularidad y vecinos) usa solo usuarios de entrenamiento y eventos antes de T0.
  - Protocolo v2: validación y prueba usan toda la historia de sus usuarios (disjuntos del entrenamiento).
    Apoyo = primeras 5 positivas distintas en el catálogo; objetivos = positivas posteriores; mínimo 6.
    (v1 exigía eventos posteriores a T0/T1 y dejaba solo 9 usuarios de prueba; T1 queda registrado pero sin uso.)
"""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = '20261107'
VECINOS_L = 50
ENCOGIMIENTO = 10

# --- clasificación por ruta de categorías de Amazon -------------------------------------------
def disciplina(ruta):
    ruta = [c for c in ruta if not c.startswith(('PD2', 'Holiday', 'Prime Day', 'Gift'))]  # rutas promocionales
    r = ' > '.join(ruta).lower()
    if 'cycling' in r or 'bike' in r:
        return 'ciclismo'
    if 'running' in r:
        return 'running'
    if 'exercise & fitness' in r or 'strength training' in r or 'yoga' in r or 'cardio training' in r:
        return 'entrenamiento'
    return None


def tipo(ruta):
    r = ' > '.join(ruta).lower()
    if any(k in r for k in ('clothing', 'apparel', 'shoes', 'shirts', 'shorts', 'socks', 'jackets', 'pants', 'jerseys')):
        return 'ropa'
    if any(k in r for k in ('helmet', 'protective', 'pads', 'guards', 'braces', 'supports', 'gloves')):
        return 'proteccion'
    if any(k in r for k in ('accessories', 'lights', 'bags', 'hydration', 'bottles', 'electronics', 'locks', 'mirrors', 'bells', 'computers', 'racks',
                            'packs', 'belts', 'flask', 'armband', 'trackers', 'monitors', 'straps')):
        return 'accesorios'
    return 'equipamiento'


# Traducción de las categorías más frecuentes. Lo que no está aquí se describe con disciplina y tipo.
CATEGORIAS_ES = {
    'Lights & Reflectors': 'Luces y reflectores', 'Bike Lights': 'Luces para bicicleta', 'Headlights': 'Luces delanteras',
    'Taillights': 'Luces traseras', 'Bike Locks': 'Candados para bicicleta', 'Locks': 'Candados', 'Bike Pumps': 'Bombas de aire',
    'Pumps': 'Bombas de aire', 'Bike Tools & Maintenance': 'Herramientas y mantenimiento', 'Tool Kits': 'Kits de herramientas',
    'Tires & Tubes': 'Llantas y neumáticos', 'Tubes': 'Neumáticos', 'Tires': 'Llantas', 'Bike Helmets': 'Cascos de ciclismo',
    'Helmets': 'Cascos', 'Water Bottle Cages': 'Portacaramañolas', 'Hydration': 'Hidratación', 'Water Bottles': 'Botellas de agua',
    'Bags': 'Bolsos', 'Saddle Bags': 'Bolsos de sillín', 'Frame Bags': 'Bolsos de marco', 'Panniers': 'Alforjas', 'Racks': 'Portaequipajes',
    'Bike Racks': 'Portabicicletas', 'Saddles': 'Sillines', 'Saddles & Seats': 'Sillines', 'Pedals': 'Pedales', 'Grips': 'Puños',
    'Handlebars': 'Manubrios', 'Chains': 'Cadenas', 'Mirrors': 'Espejos', 'Bells': 'Timbres', 'Bike Computers': 'Ciclocomputadores',
    'Fenders': 'Guardabarros', 'Kickstands': 'Paradores', 'Trainers': 'Rodillos de entrenamiento', 'Indoor Bike Trainers': 'Rodillos de entrenamiento',
    'Cycling Gloves': 'Guantes de ciclismo', 'Gloves': 'Guantes', 'Cycling Shorts': 'Pantalonetas de ciclismo', 'Jerseys': 'Camisetas de ciclismo',
    'Running': 'Running', 'Hydration Belts': 'Cinturones de hidratación', 'Running Belts': 'Cinturones para correr', 'Armbands': 'Brazaletes',
    'Reflective Gear': 'Elementos reflectivos', 'Socks': 'Medias', 'Compression': 'Compresión', 'Shoes': 'Calzado', 'Insoles': 'Plantillas',
    'Strength Training Equipment': 'Equipo de fuerza', 'Dumbbells': 'Mancuernas', 'Kettlebells': 'Pesas rusas', 'Resistance Bands': 'Bandas de resistencia',
    'Weight Plates': 'Discos de peso', 'Barbells': 'Barras', 'Benches': 'Bancos', 'Pull Up Bars': 'Barras de dominadas', 'Push Up Bars': 'Soportes para flexiones',
    'Ab Rollers': 'Ruedas abdominales', 'Ab Wheels': 'Ruedas abdominales', 'Weightlifting Belts': 'Cinturones de levantamiento',
    'Weight Lifting Gloves': 'Guantes de levantamiento', 'Wrist Wraps': 'Muñequeras', 'Yoga': 'Yoga', 'Mats': 'Colchonetas', 'Yoga Mats': 'Colchonetas de yoga',
    'Foam Rollers': 'Rodillos de espuma', 'Jump Ropes': 'Cuerdas para saltar', 'Exercise Balls': 'Balones de ejercicio', 'Balance Trainers': 'Equilibrio',
    'Activity & Fitness Trackers': 'Relojes y pulseras de actividad', 'Heart Rate Monitors': 'Monitores de ritmo cardíaco',
    'Cardio Training': 'Entrenamiento cardiovascular', 'Waist Packs': 'Riñoneras para correr', 'Straps': 'Correas',
    'Exercise Mats': 'Colchonetas de ejercicio', 'Bike Mirrors': 'Espejos para bicicleta', 'Bike Bells': 'Timbres para bicicleta',
    'Bike Pack Accessories': 'Accesorios para bolsos de bicicleta', 'Gyroscopic Hand Exercise Balls': 'Ejercitadores de mano',
    'Exercise Machine Attachments': 'Accesorios para máquinas', 'Weights & Accessories': 'Pesas y accesorios', 'Parts & Components': 'Partes y componentes',
    'Bike Tires': 'Llantas', 'Inner Tubes': 'Neumáticos', 'Cycling Computers': 'Ciclocomputadores', 'Bike Baskets': 'Canastas',
    'Bike Saddle Bags': 'Bolsos de sillín', 'Bike Trunk Bags': 'Bolsos de portaequipaje', 'Handlebar Bags': 'Bolsos de manubrio',
    'Hand Grips': 'Ejercitadores de mano', 'Push-Up Stands': 'Soportes para flexiones', 'Ab Rollers & Wheels': 'Ruedas abdominales',
    'Weight Lifting Belts': 'Cinturones de levantamiento', 'Gloves & Wraps': 'Guantes y vendas', 'Hydration Belts & Packs': 'Cinturones de hidratación', 'Accessories': 'Accesorios', 'Clothing': 'Ropa', 'Protective Gear': 'Protección',
}
NOMBRE_TIPO = {'ropa': 'Ropa', 'accesorios': 'Accesorio', 'proteccion': 'Protección', 'equipamiento': 'Equipo'}
NOMBRE_DISC = {'running': 'running', 'ciclismo': 'ciclismo', 'entrenamiento': 'entrenamiento'}


def categoria_es(ruta, d, t):
    for c in reversed(ruta):
        if c in CATEGORIAS_ES:
            return CATEGORIAS_ES[c]
    return f'{NOMBRE_TIPO[t]} de {NOMBRE_DISC[d]}'


def imagen(meta):
    for im in meta.get('images') or []:
        for k in ('large', 'hi_res', 'thumb'):
            if im.get(k):
                return im[k]
    return None


def grupo(usuario):
    h = int(hashlib.sha256((SEMILLA + usuario).encode()).hexdigest(), 16) % 100
    return 'entrenamiento' if h < 70 else 'validacion' if h < 85 else 'prueba'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('carpeta')
    ap.add_argument('--max-por-disciplina', type=int, default=1000)
    a = ap.parse_args()
    carpeta = Path(a.carpeta).resolve()
    conteos = {}

    # 1. interacciones
    df = pd.read_csv(carpeta / 'Sports_and_Outdoors.csv', dtype={'user_id': str, 'parent_asin': str})
    conteos['reseñas_iniciales'] = len(df)
    df = df.dropna(subset=['user_id', 'parent_asin', 'rating', 'timestamp'])
    df = df.sort_values(['timestamp', 'user_id', 'parent_asin']).drop_duplicates(['user_id', 'parent_asin'], keep='first')
    conteos['tras_primera_reseña_por_par'] = len(df)
    asins = set(df['parent_asin'])

    # 2. metadatos y clasificación
    productos = {}
    sin = Counter()
    with open(carpeta / 'meta_Sports_and_Outdoors.jsonl', encoding='utf-8') as f:
        for linea in f:
            r = linea.rfind('"parent_asin": "')  # filtro rápido antes de interpretar el JSON
            if r >= 0 and linea[r + 16:linea.find('"', r + 16)] not in asins:
                continue
            m = json.loads(linea)
            pid = m.get('parent_asin')
            if pid not in asins:
                continue
            ruta = [c for c in (m.get('categories') or []) if c not in ('Sports & Outdoors', 'Sports')]
            d = disciplina(ruta)
            if not d:
                sin['sin_disciplina'] += 1; continue
            if not m.get('title'):
                sin['sin_titulo'] += 1; continue
            img = imagen(m)
            if not img:
                sin['sin_imagen'] += 1; continue
            t = tipo(ruta)
            productos[pid] = {'id': pid, 'nombre': m['title'].strip(), 'marca': (m.get('store') or '').strip(), 'disciplina': d, 'tipo': t,
                              'ruta': ruta, 'categoria_es': categoria_es(ruta, d, t), 'imagen': img}
    conteos['productos_con_interacciones'] = len(asins)
    conteos['productos_clasificados'] = len(productos)
    conteos.update({f'excluidos_{k}': v for k, v in sin.items()})

    # 3. particiones temporales y por usuario
    t0, t1 = (int(x) for x in df['timestamp'].quantile([0.6, 0.8]))
    df['grupo'] = df['user_id'].map(grupo)
    df['positiva'] = df['rating'] >= 4
    ent = df[(df.grupo == 'entrenamiento') & (df.timestamp < t0) & df.positiva & df.parent_asin.isin(productos)]

    # 4. catálogo: productos con señal en entrenamiento, los más populares por disciplina
    pop = ent.groupby('parent_asin')['user_id'].nunique()
    catalogo = []
    for d in ('running', 'ciclismo', 'entrenamiento'):
        ids = [p for p in pop.sort_values(ascending=False).index if productos[p]['disciplina'] == d][:a.max_por_disciplina]
        catalogo += [productos[p] for p in ids]
        conteos[f'catalogo_{d}'] = len(ids)
    catalogo.sort(key=lambda p: p['id'])
    cat_ids = {p['id'] for p in catalogo}

    # 5. modelo congelado: popularidad y vecinos producto-producto (coseno con encogimiento)
    ent = ent[ent.parent_asin.isin(cat_ids)]
    por_usuario = ent.groupby('user_id')['parent_asin'].apply(lambda s: sorted(set(s)))
    n_item = Counter(); co = defaultdict(Counter)
    for items in por_usuario:
        n_item.update(items)
        if len(items) > 200:
            continue  # evita usuarios atípicos que dominan las coocurrencias
        for i in items:
            for j in items:
                if i != j:
                    co[i][j] += 1
    vecinos = {}
    for i, cs in co.items():
        sims = [(j, c / math.sqrt(n_item[i] * n_item[j]) * c / (c + ENCOGIMIENTO)) for j, c in cs.items()]
        sims.sort(key=lambda x: (-x[1], x[0]))
        vecinos[i] = [[j, round(s, 5)] for j, s in sims[:VECINOS_L]]
    version = f'GEARLY-{SEMILLA}-L{VECINOS_L}'
    modelo = {'version': version, 'popularidad': {p: int(n_item[p]) for p in cat_ids if n_item[p]}, 'vecinos': vecinos}
    conteos['usuarios_entrenamiento_modelo'] = int(len(por_usuario))

    # 6. evaluación (protocolo v2, 7 nov 2026; ver docs/DECISIONES.md): usuarios de validación y prueba,
    #    disjuntos del entrenamiento, con TODA su historia. Apoyo = 5 primeras positivas en el catálogo;
    #    objetivos = positivas posteriores. Mínimo 6 positivas. Se decidió con conteos, antes de calcular métricas.
    evaluacion = {}
    for g in ('validacion', 'prueba'):
        sub = df[(df.grupo == g) & df.positiva & df.parent_asin.isin(cat_ids)]
        casos = []
        for u, s in sub.sort_values(['timestamp', 'parent_asin']).groupby('user_id'):
            items = list(dict.fromkeys(s['parent_asin']))
            if len(items) >= 6:
                casos.append({'usuario': hashlib.sha256(u.encode()).hexdigest()[:12], 'apoyo': items[:5], 'objetivos': items[5:]})
        evaluacion[g] = casos
        conteos[f'usuarios_{g}'] = len(casos)

    for p in catalogo:
        p['ruta'] = p['ruta'][-3:]
    (RAIZ / 'data').mkdir(exist_ok=True)
    json.dump(catalogo, open(RAIZ / 'data/catalogo.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(modelo, open(RAIZ / 'data/modelo.json', 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(evaluacion, open(carpeta / 'evaluacion.json', 'w', encoding='utf-8'))
    manifiesto = {'semilla': SEMILLA, 'version_modelo': version, 'T0': t0, 'T1': t1, 'vecinos_L': VECINOS_L,
                  'encogimiento': ENCOGIMIENTO, 'regla_positiva': 'rating >= 4', 'protocolo_evaluacion': 'v2: usuarios disjuntos, historia completa, apoyo 5, minimo 6', 'conteos': conteos}
    json.dump(manifiesto, open(RAIZ / 'data/manifiesto.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(manifiesto, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
