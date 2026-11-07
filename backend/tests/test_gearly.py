import pytest
from fastapi.testclient import TestClient
from app.main import app, REC
from app.recomendador import Recomendador


@pytest.fixture
def c():
    cl = TestClient(app)
    r = cl.post('/sesiones'); assert r.status_code == 200
    cl.headers['X-CSRF'] = r.json()['csrf']
    return cl


def guardar(c, **kw):
    v = c.get('/sesiones/actual').json()['version']
    return c.put('/perfil', json={'version': v, **kw})


def test_contenido_respeta_intereses():
    r = REC.recomendar('contenido', ['ciclismo'], ['accesorios'], [])
    assert r['metodo'] == 'contenido'
    assert r['resultados'][0]['producto']['disciplina'] == 'ciclismo'


def test_hibrido_sin_selecciones_se_reduce_a_contenido():
    r = REC.recomendar('hibrido', ['running'], [], [])
    assert r['metodo'] == 'contenido' and r['motivo_alternativa']


def test_sin_senal_usa_popularidad_declarada():
    r = REC.recomendar('hibrido', [], [], [])
    assert r['metodo'] == 'popularidad' and r['resultados'][0]['producto']['id'] == 'T000'


def test_colaborativo_y_exclusion():
    r = REC.recomendar('colaborativo', [], [], ['T003'])
    ids = [x['producto']['id'] for x in r['resultados']]
    assert ids[0] == 'T004' and 'T003' not in ids


def test_alfa_extremos_igualan_estrategias():
    rec = Recomendador(list(REC.productos.values()), {'version': 'x', 'popularidad': REC.popularidad, 'vecinos': {k: list(v) for k, v in REC.vecinos.items()}}, alfa=1.0)
    hib = [x['producto']['id'] for x in rec.recomendar('hibrido', [], [], ['T008'])['resultados']]
    cont = [x['producto']['id'] for x in rec.recomendar('contenido', [], [], ['T008'])['resultados']]
    assert hib == cont


def test_sin_sesion_401():
    assert TestClient(app).get('/perfil' if False else '/recomendaciones').status_code == 401


def test_sin_csrf_403(c):
    v = c.get('/sesiones/actual').json()['version']
    del c.headers['X-CSRF']
    assert c.put('/perfil', json={'version': v}).status_code == 403


def test_validaciones_perfil(c):
    assert guardar(c, selecciones=['T001', 'T001']).status_code == 422
    assert guardar(c, selecciones=['T001', 'T002', 'T003', 'T004', 'T005', 'T006']).status_code == 422
    assert guardar(c, disciplinas=['natacion']).status_code == 422
    assert guardar(c, selecciones=['NOEXISTE']).status_code == 422
    assert c.put('/perfil', json={'version': 999}).status_code == 409


def test_recorrido_completo(c):
    assert guardar(c, disciplinas=['ciclismo'], tipos=['accesorios'], selecciones=['T003']).status_code == 200
    r = c.get('/recomendaciones').json()
    ids = [x['producto']['id'] for x in r['resultados']]
    assert r['metodo'] == 'hibrido' and 'T003' not in ids and ids[0] == 'T004'
    assert all(x['explicacion'] for x in r['resultados'])
    assert c.get('/parecidos', params={'de': 'T008'}).json()['productos'][0]['id'] == 'T009'
    assert c.delete('/perfil').json()['selecciones'] == []


def test_retomar_con_codigo(c):
    guardar(c, disciplinas=['running'])
    codigo = c.get('/sesiones/actual').json()['codigo']
    otro = TestClient(app)
    r = otro.post('/sesiones/retomar', json={'codigo': codigo})
    assert r.status_code == 200 and r.json()['disciplinas'] == ['running']
    assert otro.post('/sesiones/retomar', json={'codigo': 'G-NOPE00'}).status_code == 404


def test_evaluacion_ciega_y_exportacion(c):
    guardar(c, disciplinas=['entrenamiento'], selecciones=['T008'])
    r = c.post('/evaluacion', json={'codigo_participante': 'p001'}).json()
    ids = [p['id'] for p in r['productos']]
    assert len(ids) == len(set(ids)) and 'metodo' not in str(r)
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': {ids[0]: 5}}).status_code == 422
    juicios = {i: 4 for i in ids}; juicios[ids[0]] = None
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': juicios, 'encuesta': {'claridad': 5}}).status_code == 422  # falta SUS
    sus = {f'sus{i}': (5 if i % 2 else 1) for i in range(1, 11)}  # respuestas ideales -> 100
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': juicios, 'encuesta': {'claridad': 5, **sus}}).status_code == 200
    ex = TestClient(app).get('/admin/exportar', params={'clave': 'clave-prueba'}).json()
    fila = [f for f in ex['evaluaciones'] if f['codigo'] == 'P001'][-1]
    assert set(fila['listas']) == {'popularidad', 'contenido', 'hibrido'} and fila['media_por_lista']['hibrido'] is not None
    assert fila['sus_puntaje'] == 100.0
    assert TestClient(app).get('/admin/exportar', params={'clave': 'mala'}).status_code == 403


def test_puntaje_sus():
    from app.main import puntaje_sus
    assert puntaje_sus({f'sus{i}': 3 for i in range(1, 11)}) == 50.0
    assert puntaje_sus({f'sus{i}': (1 if i % 2 else 5) for i in range(1, 11)}) == 0.0
    assert puntaje_sus({'sus1': 3}) is None
