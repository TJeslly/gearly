"""Estrategias de recomendación de Gearly.

POP   popularidad: número de usuarios con señal positiva en entrenamiento.
CONT  contenido: coseno entre el perfil y un vector TF-IDF de cada producto, formado por
      tres grupos con el mismo peso (disciplina/tipo, ruta de categorías, palabras del título y marca).
CF    colaborativo producto-producto: media de similitudes entre cada candidato y los productos elegidos.
      Las similitudes (coseno con encogimiento c/(c+10)) se calculan antes, en scripts/preparar_datos.py.
HIB   híbrido ponderado: alfa * CONT + (1 - alfa) * CF, cada parte escalada a [0, 1].

Todo es determinista: los empates se resuelven por identificador. No se entrena nada durante una petición.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

DISCIPLINAS = ('running', 'ciclismo', 'entrenamiento')
TIPOS = ('ropa', 'accesorios', 'proteccion', 'equipamiento')
METODOS = ('popularidad', 'contenido', 'colaborativo', 'hibrido')
ALFA = 0.5

NOMBRE_DISCIPLINA = {'running': 'Running', 'ciclismo': 'Ciclismo', 'entrenamiento': 'Entrenamiento'}
NOMBRE_TIPO = {'ropa': 'Ropa', 'accesorios': 'Accesorios', 'proteccion': 'Protección', 'equipamiento': 'Equipamiento'}

_PALABRAS_VACIAS = set('a an and the for with of to in on by from or at as is it your you pack set pcs piece pieces new'.split())


def _palabras(texto: str) -> list[str]:
    return [w for w in re.findall(r'[a-z0-9]+', (texto or '').lower()) if len(w) > 2 and w not in _PALABRAS_VACIAS and not w.isdigit()]


def _grupos(p: dict) -> list[list[str]]:
    g1 = [f'd:{p["disciplina"]}', f't:{p["tipo"]}']
    ruta = p.get('ruta') or []
    g2 = [f'c:{" > ".join(ruta[:i + 1])}' for i in range(len(ruta))]
    g3 = [f'w:{w}' for w in _palabras(p.get('nombre', ''))] + ([f'm:{p["marca"].lower()}'] if p.get('marca') else [])
    return [g1, g2, g3]


def _normalizar(v: dict) -> dict:
    n = math.sqrt(sum(x * x for x in v.values()))
    return {k: x / n for k, x in v.items()} if n else {}


def _sumar(*vs: dict) -> dict:
    out = defaultdict(float)
    for v in vs:
        for k, x in v.items():
            out[k] += x
    return dict(out)


def _punto(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(k, 0.0) for k, x in a.items())


class EspacioContenido:
    """Vectores TF-IDF por grupo, normalizados por grupo y combinados con peso igual."""

    def __init__(self, productos: list[dict]):
        grupos = {p['id']: _grupos(p) for p in productos}
        n = len(productos) or 1
        df = [Counter(), Counter(), Counter()]
        for gs in grupos.values():
            for j, g in enumerate(gs):
                df[j].update(set(g))
        self.idf = [{t: math.log((1 + n) / (1 + c)) + 1 for t, c in d.items()} for d in df]
        peso = 1 / math.sqrt(3)
        self.vec = {}
        for pid, gs in grupos.items():
            partes = []
            for j, g in enumerate(gs):
                tf = Counter(g)
                partes.append({t: x * peso for t, x in _normalizar({t: c * self.idf[j][t] for t, c in tf.items()}).items()})
            self.vec[pid] = _normalizar(_sumar(*partes))
        self.indice = defaultdict(list)  # término -> [(producto, peso)] para puntuar rápido
        for pid, v in self.vec.items():
            for t, x in v.items():
                self.indice[t].append((pid, x))

    def perfil(self, disciplinas, tipos, seleccionados) -> dict:
        bloques = []
        declarado = {f'd:{d}': 1.0 for d in disciplinas}
        declarado.update({f't:{t}': 1.0 for t in tipos})
        if declarado:
            bloques.append(_normalizar(declarado))
        vs = [self.vec[s] for s in seleccionados if s in self.vec]
        if vs:
            media = {k: x / len(vs) for k, x in _sumar(*vs).items()}
            bloques.append(_normalizar(media))
        return _normalizar(_sumar(*bloques)) if bloques else {}

    def puntajes(self, perfil: dict, candidatos) -> dict:
        if not perfil:
            return {}
        cand = candidatos if isinstance(candidatos, (set, frozenset)) else set(candidatos)
        out = defaultdict(float)
        for t, x in perfil.items():
            for pid, y in self.indice.get(t, ()):
                if pid in cand:
                    out[pid] += x * y
        return dict(out)


def puntajes_colaborativo(vecinos: dict, seleccionados, candidatos) -> dict:
    if not seleccionados:
        return {}
    cand = set(candidatos)
    suma = defaultdict(float)
    for s in seleccionados:
        for j, sim in vecinos.get(s, []):
            if j in cand:
                suma[j] += sim
    return {j: x / len(seleccionados) for j, x in suma.items() if x > 0}


def _escalar(p: dict) -> dict:
    m = max(p.values(), default=0.0)
    return {k: x / m for k, x in p.items()} if m > 0 else {}


def _ordenar(p: dict, limite: int) -> list[tuple[str, float]]:
    return sorted(((k, x) for k, x in p.items() if x > 0), key=lambda t: (-t[1], t[0]))[:limite]


class Recomendador:
    def __init__(self, productos: list[dict], modelo: dict, alfa: float = ALFA):
        self.productos = {p['id']: p for p in productos}
        self.espacio = EspacioContenido(productos)
        self.popularidad = modelo.get('popularidad', {})
        self.vecinos = {k: [tuple(x) for x in v] for k, v in modelo.get('vecinos', {}).items()}
        self.version = modelo.get('version', 'sin-version')
        self.alfa = alfa

    # --- puntajes por estrategia (también los usa el experimento offline) ---
    def puntajes(self, metodo, disciplinas, tipos, seleccionados, candidatos):
        if metodo == 'popularidad':
            return {c: float(self.popularidad.get(c, 0)) for c in candidatos}, None
        cont = self.espacio.puntajes(self.espacio.perfil(disciplinas, tipos, seleccionados), candidatos)
        if metodo == 'contenido':
            return cont, None
        cf = puntajes_colaborativo(self.vecinos, seleccionados, candidatos)
        if metodo == 'colaborativo':
            return cf, None
        if not cf:
            return cont, 'contenido'  # el híbrido se reduce a contenido y se informa
        c, f = _escalar(cont), _escalar(cf)
        return {k: self.alfa * c.get(k, 0.0) + (1 - self.alfa) * f.get(k, 0.0) for k in set(c) | set(f)}, None

    def recomendar(self, metodo, disciplinas, tipos, seleccionados, limite=10, excluir=()):
        fuera = set(seleccionados) | set(excluir)
        candidatos = [pid for pid in self.productos if pid not in fuera]
        puntos, reducido = self.puntajes(metodo, disciplinas, tipos, seleccionados, candidatos)
        orden = _ordenar(puntos, limite)
        metodo_real = reducido or metodo
        motivo = 'Sin productos elegidos, el híbrido usa solo contenido.' if reducido else None
        if not orden:
            # sin señal: popularidad declarada como tal, no como personalización
            orden = _ordenar({c: float(self.popularidad.get(c, 0)) for c in candidatos}, limite)
            metodo_real, motivo = 'popularidad', 'No hubo información suficiente; se muestran productos populares, no personalizados.'
        return {'metodo': metodo_real, 'motivo_alternativa': motivo,
                'resultados': [{'producto': self.productos[pid], 'puntaje': round(x, 4),
                                'explicacion': self.explicar(pid, metodo_real, disciplinas, tipos, seleccionados)} for pid, x in orden]}

    def explicar(self, pid, metodo, disciplinas, tipos, seleccionados):
        p = self.productos[pid]
        if metodo == 'popularidad':
            return 'Es de los productos con más interés en los datos de referencia. No depende de tus gustos.'
        partes = []
        if p['disciplina'] in disciplinas:
            partes.append(f'es de {NOMBRE_DISCIPLINA[p["disciplina"]]}')
        if p['tipo'] in tipos:
            partes.append(f'es del tipo {NOMBRE_TIPO[p["tipo"]].lower()} que elegiste')
        if metodo in ('colaborativo', 'hibrido') and seleccionados:
            mejor = max(((s, dict(self.vecinos.get(s, [])).get(pid, 0.0)) for s in seleccionados), key=lambda t: t[1])
            if mejor[1] > 0:
                partes.append(f'quienes valoraron bien «{_corto(self.productos[mejor[0]]["nombre"])}» también valoraron este')
        if not partes and seleccionados:
            partes.append('se parece a los productos que marcaste')
        return ('Aparece porque ' + ', '.join(partes) + '.') if partes else 'Coincide con tus intereses.'

    def parecidos(self, semilla, excluir=(), limite=6):
        r = self.recomendar('hibrido', [], [], [semilla], limite=limite, excluir=excluir)
        return [x['producto'] for x in r['resultados']]


def _corto(t, n=40):
    return t if len(t) <= n else t[:n - 1].rstrip() + '…'
