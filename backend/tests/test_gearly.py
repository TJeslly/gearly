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
    assert TestClient(app).get('/recomendaciones').status_code == 401


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
    otro.headers['X-Forwarded-For'] = '10.1.1.1'
    r = otro.post('/sesiones/retomar', json={'codigo': codigo})
    assert r.status_code == 200 and r.json()['disciplinas'] == ['running']
    assert otro.post('/sesiones/retomar', json={'codigo': 'G-NOPE00'}).status_code == 404


H01_OK = {'q4_relacion': 'amigo', 'q5_interes_actividad': 'si', 'q6_edad': '18_24', 'q7_frecuencia_catalogos': None,
          'q8_uso_previo': 'no', 'q9_dispositivo': 'movil'}


def participar(c, codigo='p001', **h01):
    return c.post('/participacion', json={'codigo_participante': codigo, 'acepta': True, 'h01': {**H01_OK, **h01},
                                           'tecnico': {'navegador': 'Chrome', 'ancho_pantalla': 390}})


def test_estrategia_no_se_elige_desde_url(c):
    guardar(c, disciplinas=['ciclismo'], selecciones=['T003'])
    r = c.get('/recomendaciones', params={'metodo': 'popularidad'}).json()
    assert r['metodo'] == 'hibrido'


def test_sin_consentimiento_no_guarda_nada(c):
    r = c.post('/participacion', json={'codigo_participante': 'p050', 'acepta': False, 'h01': {}})
    assert r.json()['estado'] == 'no_acepta'
    assert c.get('/sesiones/actual').json()['participacion'] is None
    assert c.post('/evaluacion').status_code == 409


def test_exclusion_por_criterio(c):
    assert participar(c, 'p051', q5_interes_actividad='no').json()['estado'] == 'excluida'
    assert c.post('/evaluacion').status_code == 409
    ex = TestClient(app).get('/admin/exportar', params={'clave': 'clave-prueba'}).json()
    fila = [x for x in ex['participantes'] if x['codigo'] == 'P051'][0]
    assert fila['estado'] == 'excluida' and fila['h01']['q5_interes_actividad'] == 'no' and fila['evaluacion_terminada'] is False


def test_no_estar_seguro_no_excluye_y_reintento_tras_exclusion(c):
    assert participar(c, 'p053', q5_interes_actividad='no').json()['estado'] == 'excluida'
    assert participar(c, 'p053', q4_relacion='familiar', q5_interes_actividad='no_seguro').json()['estado'] == 'activa'
    assert c.get('/sesiones/actual').json()['participacion']['estado'] == 'activa'


def test_h01_invalido(c):
    assert participar(c, 'p052', q9_dispositivo='nevera').status_code == 422


def test_evaluacion_ciega_y_exportacion(c):
    guardar(c, disciplinas=['entrenamiento'], selecciones=['T008'])
    assert participar(c).json()['estado'] == 'activa'
    assert c.get('/sesiones/actual').json()['participacion'] == {'codigo': 'P001', 'estado': 'activa', 'terminada': False}
    c.get('/recomendaciones')
    r = c.post('/evaluacion').json()
    ids = [p['id'] for p in r['productos']]
    assert len(ids) == len(set(ids)) and 'metodo' not in str(r)
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': {ids[0]: 5}}).status_code == 422
    juicios = {i: 4 for i in ids}; juicios[ids[0]] = None
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': juicios, 'encuesta': {'claridad': 5}}).status_code == 422  # falta SUS
    sus = {f'sus{i}': (5 if i % 2 else 1) for i in range(1, 11)}  # respuestas ideales -> 100
    assert c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': juicios, 'encuesta': {'claridad': 5, **sus}}).status_code == 200
    assert c.get('/sesiones/actual').json()['participacion']['terminada'] is True
    ex = TestClient(app).get('/admin/exportar', params={'clave': 'clave-prueba'}).json()
    fila = [f for f in ex['evaluaciones'] if f['codigo'] == 'P001'][-1]
    assert set(fila['listas']) == {'popularidad', 'contenido', 'hibrido'} and fila['media_por_lista']['hibrido'] is not None
    assert fila['sus_puntaje'] == 100.0 and fila['h01']['q9_dispositivo'] == 'movil' and fila['consentimiento'].startswith('C01')
    assert ex['latencia_recomendaciones_ms']['n'] >= 1
    assert TestClient(app).get('/admin/exportar', params={'clave': 'mala'}).status_code == 403


def test_retiro_borra_respuestas(c):
    guardar(c, disciplinas=['ciclismo'], selecciones=['T003'])
    participar(c, 'p060')
    r = c.post('/evaluacion').json()
    sus = {f'sus{i}': 3 for i in range(1, 11)}
    c.put(f'/evaluacion/{r["evaluacion_id"]}', json={'juicios': {p['id']: 3 for p in r['productos']}, 'encuesta': sus})
    assert c.post('/participacion/retiro').json()['estado'] == 'retirada'
    ex = TestClient(app).get('/admin/exportar', params={'clave': 'clave-prueba'}).json()
    assert not [f for f in ex['evaluaciones'] if f['codigo'] == 'P060']
    assert c.post('/participacion/retiro').status_code == 404


def test_limite_intentos_retomar():
    cl = TestClient(app)
    codigos = [cl.post('/sesiones/retomar', json={'codigo': f'G-X{i:04d}'}, headers={'X-Forwarded-For': '10.9.9.9'}).status_code for i in range(12)]
    assert codigos[:10] == [404] * 10 and codigos[10] == 429


def test_puntaje_sus():
    from app.main import puntaje_sus
    assert puntaje_sus({f'sus{i}': 3 for i in range(1, 11)}) == 50.0
    assert puntaje_sus({f'sus{i}': (1 if i % 2 else 5) for i in range(1, 11)}) == 0.0
    assert puntaje_sus({'sus1': 3}) is None
