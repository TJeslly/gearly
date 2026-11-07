"""API de Gearly (FastAPI).

Sesión anónima por cookie HttpOnly + token CSRF en cabecera para cambios. Sin nombres ni correos.
El catálogo y el modelo se cargan de data/ al iniciar; la base guarda perfiles, listas y evaluaciones.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .recomendador import DISCIPLINAS, METODOS, TIPOS, Recomendador

RAIZ = Path(__file__).resolve().parents[2]
DATOS = Path(os.getenv('GEARLY_DATOS', RAIZ / 'data'))
MIN_SELECCIONES, MAX_SELECCIONES = 0, 5
DIAS_SESION = 7
TAM_LISTA_EVAL = 5
METODOS_EVAL = ('popularidad', 'contenido', 'hibrido')

url = os.getenv('DATABASE_URL', f'sqlite:///{RAIZ / "backend" / "gearly.db"}')
if url.startswith('postgres://'):
    url = 'postgresql+psycopg://' + url[len('postgres://'):]
elif url.startswith('postgresql://'):
    url = 'postgresql+psycopg://' + url[len('postgresql://'):]
engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()
ahora = lambda: datetime.now(timezone.utc)


class Perfil(Base):
    __tablename__ = 'perfiles'
    id = Column(String, primary_key=True)
    token_hash = Column(String, unique=True, nullable=False)
    csrf = Column(String, nullable=False)
    codigo = Column(String, unique=True, nullable=False)
    disciplinas = Column(Text, nullable=False, default='[]')
    tipos = Column(Text, nullable=False, default='[]')
    selecciones = Column(Text, nullable=False, default='[]')
    version = Column(Integer, nullable=False, default=0)
    creado = Column(DateTime(timezone=True), nullable=False)
    expira = Column(DateTime(timezone=True), nullable=False)


class Lista(Base):
    __tablename__ = 'listas'
    id = Column(String, primary_key=True)
    perfil_id = Column(String, ForeignKey('perfiles.id'), nullable=False, index=True)
    perfil_version = Column(Integer, nullable=False)
    metodo_solicitado = Column(String, nullable=False)
    metodo_resultante = Column(String, nullable=False)
    modelo_version = Column(String, nullable=False)
    productos = Column(Text, nullable=False)
    creado = Column(DateTime(timezone=True), nullable=False)


class Evaluacion(Base):
    __tablename__ = 'evaluaciones'
    id = Column(String, primary_key=True)
    perfil_id = Column(String, ForeignKey('perfiles.id'), nullable=False, index=True)
    codigo_participante = Column(String, nullable=False)
    perfil_congelado = Column(Text, nullable=False)
    listas = Column(Text, nullable=False)      # {metodo: [ids]} — nunca se envía al navegador
    orden = Column(Text, nullable=False)       # unión sin duplicados, en orden aleatorio
    juicios = Column(Text, nullable=True)      # {id: 1..5 | null = no puedo valorar}
    encuesta = Column(Text, nullable=True)
    modelo_version = Column(String, nullable=False)
    creado = Column(DateTime(timezone=True), nullable=False)
    terminado = Column(DateTime(timezone=True), nullable=True)


def cargar_datos():
    try:
        catalogo = json.load(open(DATOS / 'catalogo.json', encoding='utf-8'))
        modelo = json.load(open(DATOS / 'modelo.json', encoding='utf-8'))
    except FileNotFoundError:
        catalogo, modelo = [], {'version': 'sin-datos'}
    return Recomendador(catalogo, modelo)


REC = cargar_datos()
Base.metadata.create_all(engine)
app = FastAPI(title='Gearly API', version='1.0.0')


def _utc(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


def sesion(request: Request, s: Session = Depends(db)) -> Perfil:
    tok = request.cookies.get('gearly_sesion')
    p = s.query(Perfil).filter_by(token_hash=_hash(tok)).first() if tok else None
    if not p:
        raise HTTPException(401, 'Sesión no encontrada. Recarga la página.')
    if _utc(p.expira) < ahora():
        raise HTTPException(401, 'La sesión expiró. Empieza de nuevo.')
    return p


def con_csrf(request: Request, p: Perfil = Depends(sesion)) -> Perfil:
    if not secrets.compare_digest(request.headers.get('X-CSRF', ''), p.csrf):
        raise HTTPException(403, 'Token de seguridad inválido. Recarga la página.')
    return p


def _poner_cookie(resp: Response, token: str):
    resp.set_cookie('gearly_sesion', token, httponly=True, samesite='lax', max_age=DIAS_SESION * 86400,
                    secure=os.getenv('COOKIE_SEGURA', '0') == '1')


def _estado(p: Perfil):
    return {'codigo': p.codigo, 'version': p.version, 'disciplinas': json.loads(p.disciplinas), 'tipos': json.loads(p.tipos),
            'selecciones': [REC.productos[i] for i in json.loads(p.selecciones) if i in REC.productos]}


# ------------------------------------------------------------------ endpoints
@app.get('/salud')
def salud():
    return {'estado': 'ok', 'productos': len(REC.productos), 'modelo': REC.version}


@app.post('/sesiones')
def nueva_sesion(resp: Response, s: Session = Depends(db)):
    token = secrets.token_urlsafe(32)
    p = Perfil(id=str(uuid.uuid4()), token_hash=_hash(token), csrf=secrets.token_urlsafe(24),
               codigo='G-' + secrets.token_hex(3).upper(), creado=ahora(), expira=ahora() + timedelta(days=DIAS_SESION))
    s.add(p); s.commit()
    _poner_cookie(resp, token)
    return {'csrf': p.csrf, **_estado(p)}


@app.get('/sesiones/actual')
def sesion_actual(p: Perfil = Depends(sesion)):
    return {'csrf': p.csrf, **_estado(p)}


class RetomarIn(BaseModel):
    codigo: str = Field(min_length=3, max_length=20)


@app.post('/sesiones/retomar')
def retomar(data: RetomarIn, resp: Response, s: Session = Depends(db)):
    p = s.query(Perfil).filter_by(codigo=data.codigo.strip().upper()).first()
    if not p or _utc(p.expira) < ahora():
        raise HTTPException(404, 'No encontramos ese código o ya expiró.')
    token = secrets.token_urlsafe(32)
    p.token_hash = _hash(token); p.csrf = secrets.token_urlsafe(24); s.commit()
    _poner_cookie(resp, token)
    return {'csrf': p.csrf, **_estado(p)}


@app.get('/vocabulario')
def vocabulario():
    conteo = {t: sum(p['tipo'] == t for p in REC.productos.values()) for t in TIPOS}
    return {'disciplinas': DISCIPLINAS, 'tipos': TIPOS, 'conteo_tipos': conteo, 'min_selecciones': MIN_SELECCIONES, 'max_selecciones': MAX_SELECCIONES}


@app.get('/productos')
def productos(q: str = '', disciplina: str = '', tipo: str = '', pagina: int = Query(1, ge=1), limite: int = Query(24, ge=1, le=60)):
    q = q.strip().lower()
    items = [p for p in REC.productos.values()
             if (not disciplina or p['disciplina'] in disciplina.split(',')) and (not tipo or p['tipo'] in tipo.split(','))
             and (not q or q in p['nombre'].lower() or q in p['categoria_es'].lower() or q in (p.get('marca') or '').lower())]
    items.sort(key=lambda p: (-REC.popularidad.get(p['id'], 0), p['id']))
    ini = (pagina - 1) * limite
    return {'total': len(items), 'pagina': pagina, 'productos': items[ini:ini + limite]}


class PerfilIn(BaseModel):
    disciplinas: list[str] = []
    tipos: list[str] = []
    selecciones: list[str] = []
    version: int


@app.put('/perfil')
def guardar_perfil(data: PerfilIn, p: Perfil = Depends(con_csrf), s: Session = Depends(db)):
    if data.version != p.version:
        raise HTTPException(409, 'Tu perfil cambió en otra pestaña. Recarga la página.')
    if any(d not in DISCIPLINAS for d in data.disciplinas) or any(t not in TIPOS for t in data.tipos):
        raise HTTPException(422, 'Opción no válida.')
    if len(set(data.selecciones)) != len(data.selecciones):
        raise HTTPException(422, 'No puedes repetir productos.')
    if len(data.selecciones) > MAX_SELECCIONES:
        raise HTTPException(422, f'Puedes elegir hasta {MAX_SELECCIONES} productos.')
    if any(i not in REC.productos for i in data.selecciones):
        raise HTTPException(422, 'Producto desconocido.')
    p = s.merge(p)
    p.disciplinas = json.dumps(sorted(set(data.disciplinas))); p.tipos = json.dumps(sorted(set(data.tipos)))
    p.selecciones = json.dumps(data.selecciones); p.version += 1
    s.commit()
    return _estado(p)


@app.delete('/perfil')
def borrar_perfil(p: Perfil = Depends(con_csrf), s: Session = Depends(db)):
    p = s.merge(p)
    p.disciplinas = p.tipos = p.selecciones = '[]'; p.version += 1
    s.commit()
    return _estado(p)


def _calcular(p, metodo, limite):
    return REC.recomendar(metodo, json.loads(p.disciplinas), json.loads(p.tipos), json.loads(p.selecciones), limite=limite)


@app.get('/recomendaciones')
def recomendaciones(metodo: str = 'hibrido', p: Perfil = Depends(sesion), s: Session = Depends(db)):
    if metodo not in METODOS:
        raise HTTPException(422, 'Método no válido.')
    r = _calcular(p, metodo, 10)
    lista = Lista(id=str(uuid.uuid4()), perfil_id=p.id, perfil_version=p.version, metodo_solicitado=metodo, metodo_resultante=r['metodo'],
                  modelo_version=REC.version, productos=json.dumps([x['producto']['id'] for x in r['resultados']]), creado=ahora())
    s.add(lista); s.commit()
    return {'lista_id': lista.id, 'metodo': r['metodo'], 'motivo_alternativa': r['motivo_alternativa'], 'resultados': r['resultados']}


@app.get('/parecidos')
def parecidos(de: str, excluir: str = '', p: Perfil = Depends(sesion)):
    if de not in REC.productos:
        raise HTTPException(422, 'Producto desconocido.')
    return {'productos': REC.parecidos(de, excluir=[x for x in excluir.split(',') if x], limite=6)}


# ------------------------------------------------------------------ evaluación formativa (H03 y H04 dentro de la app)
class EvalIn(BaseModel):
    codigo_participante: str = Field(min_length=2, max_length=20)


@app.post('/evaluacion')
def iniciar_evaluacion(data: EvalIn, p: Perfil = Depends(con_csrf), s: Session = Depends(db)):
    """Congela el perfil, genera POP, CONT e HIB (5 cada una), une sin duplicados y mezcla. El navegador no ve el método."""
    listas = {m: [x['producto']['id'] for x in _calcular(p, m, TAM_LISTA_EVAL)['resultados']] for m in METODOS_EVAL}
    union = sorted({i for ids in listas.values() for i in ids})
    random.Random(p.id + str(p.version)).shuffle(union)
    e = Evaluacion(id=str(uuid.uuid4()), perfil_id=p.id, codigo_participante=data.codigo_participante.strip().upper(),
                   perfil_congelado=json.dumps(_estado(p) | {'selecciones': json.loads(p.selecciones)}), listas=json.dumps(listas),
                   orden=json.dumps(union), modelo_version=REC.version, creado=ahora())
    s.add(e); s.commit()
    return {'evaluacion_id': e.id, 'productos': [REC.productos[i] for i in union]}


class JuiciosIn(BaseModel):
    juicios: dict[str, int | None]
    encuesta: dict[str, int | str | None] = {}


@app.put('/evaluacion/{eid}')
def guardar_evaluacion(eid: str, data: JuiciosIn, p: Perfil = Depends(con_csrf), s: Session = Depends(db)):
    e = s.get(Evaluacion, eid)
    if not e or e.perfil_id != p.id:
        raise HTTPException(404, 'Evaluación no encontrada.')
    orden = set(json.loads(e.orden))
    if set(data.juicios) != orden:
        raise HTTPException(422, 'Falta valorar algún producto.')
    if any(v is not None and not 1 <= v <= 5 for v in data.juicios.values()):
        raise HTTPException(422, 'Las valoraciones van de 1 a 5.')
    e.juicios = json.dumps(data.juicios); e.encuesta = json.dumps(data.encuesta, ensure_ascii=False); e.terminado = ahora()
    s.commit()
    return {'ok': True}


@app.get('/admin/exportar')
def exportar(clave: str = '', s: Session = Depends(db)):
    esperada = os.getenv('ADMIN_CLAVE', '')
    if not esperada:
        raise HTTPException(404, 'No disponible')
    if not secrets.compare_digest(clave, esperada):
        raise HTTPException(403, 'Clave inválida')
    filas = []
    for e in s.query(Evaluacion).order_by(Evaluacion.creado).all():
        juicios = json.loads(e.juicios) if e.juicios else {}
        listas = json.loads(e.listas)
        medias = {}
        for m, ids in listas.items():
            v = [juicios[i] for i in ids if juicios.get(i) is not None]
            medias[m] = round(sum(v) / len(v), 3) if v else None
        filas.append({'codigo': e.codigo_participante, 'creado': e.creado.isoformat(), 'terminado': e.terminado.isoformat() if e.terminado else None,
                      'modelo': e.modelo_version, 'perfil': json.loads(e.perfil_congelado), 'listas': listas, 'juicios': juicios,
                      'media_por_lista': medias, 'encuesta': json.loads(e.encuesta) if e.encuesta else {}})
    return {'total': len(filas), 'evaluaciones': filas}


# ------------------------------------------------------------------ servicio único: API en /api y la interfaz compilada en /
web = FastAPI(title='Gearly')
web.mount('/api', app)
_dist = RAIZ / 'frontend' / 'dist'
if _dist.exists():
    web.mount('/', StaticFiles(directory=_dist, html=True), name='web')
