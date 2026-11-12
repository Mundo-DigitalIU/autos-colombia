from fastapi.testclient import TestClient
import pytest

from app.main import app


def test_openapi_y_salud():
    with TestClient(app) as client:
        schema = client.get('/openapi.json').json()
        for path, method in [('/estancias/entrada', 'post'), ('/estancias/salida', 'post'),
                             ('/estancias/vehiculo/{placa}', 'get')]:
            assert method in schema['paths'][path]
        assert client.get('/health').json() == {'status': 'ok'}


@pytest.mark.parametrize('payload', [
    {}, {'placa': ' ', 'celda_id': 1},
    {'placa': None, 'celda_id': 1},
    {'placa': 'TEST', 'celda_id': 0},
    {'placa': 'TEST', 'celda_id': True},
    {'placa': 'TEST', 'celda_id': '1'},
    {'placa': 'TEST', 'celda_id': 1, 'entrada': '2026-01-01'},
    # El operador sale de la sesión: enviarlo en el cuerpo ya no se admite.
    {'placa': 'TEST', 'celda_id': 1, 'operador_id': 1},
    {'placa': 'TEST', 'operador_id': None},
])
def test_entrada_invalida(payload):
    with TestClient(app) as client:
        assert client.post('/estancias/entrada', json=payload).status_code == 422


def test_salida_no_admite_celda_ni_fecha():
    with TestClient(app) as client:
        for extra in ({'celda_id': 1}, {'salida': '2026-01-01'}, {'id': 1}, {'operador_id': 1}):
            assert client.post('/estancias/salida', json={'placa': 'TEST', **extra}).status_code == 422
        assert client.get('/estancias/vehiculo/%20%20').status_code == 422
