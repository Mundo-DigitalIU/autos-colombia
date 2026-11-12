"""Etapa 6: la entrada y la salida usan el operador de la sesión (autenticación real)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from utiles_bd import crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres, token_unico

SIN_SESION_FALSA = True


@pytest.mark.parametrize("ruta", ["/estancias/entrada", "/estancias/salida"])
def test_sin_sesion_es_401(ruta):
    with TestClient(app) as client:
        respuesta = client.post(ruta, json={"placa": "ABC123"})
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": "Tu sesión terminó. Inicia sesión otra vez."}


@pytest.mark.parametrize("ruta", ["/estancias/entrada", "/estancias/salida"])
def test_el_operador_ya_no_viaja_en_el_cuerpo(ruta, fijar_sesion):
    # Esta prueba usa la sesión simulada: basta con que el cuerpo con operador_id se rechace.
    from app.auth import sesion_actual
    from conftest import crear_sesion
    app.dependency_overrides[sesion_actual] = lambda: crear_sesion()
    try:
        with TestClient(app) as client:
            assert client.post(ruta, json={"placa": "ABC123", "operador_id": 1}).status_code == 422
    finally:
        app.dependency_overrides.pop(sesion_actual, None)


@solo_postgres
@pytest.mark.parametrize("rol", ["OPERADOR", "ADMINISTRADOR"])
def test_entrada_y_salida_quedan_a_nombre_del_operador_de_la_sesion(rol):
    with entorno_bd() as (client, connection):
        entra = crear_cuenta(connection, rol)
        sale = crear_cuenta(connection, "OPERADOR" if rol == "ADMINISTRADOR" else "ADMINISTRADOR")
        placa = token_unico("S")
        celda = connection.scalar(text("INSERT INTO celda(codigo, tipo) VALUES (:c, 'MOTO') RETURNING id"),
                                  {"c": placa})
        connection.execute(text("INSERT INTO vehiculo(placa, color, modelo, marca, tipo) "
                                "VALUES (:p, 'Rojo', 2020, 'X', 'MOTO')"), {"p": placa})

        entrada = client.post("/estancias/entrada", json={"placa": placa, "celda_id": celda},
                              headers=iniciar_sesion(client, entra))
        assert entrada.status_code == 201
        assert entrada.json()["operador_entrada_id"] == entra["operador_id"]
        assert entrada.json()["operador_salida_id"] is None

        salida = client.post("/estancias/salida", json={"placa": placa}, headers=iniciar_sesion(client, sale))
        assert salida.status_code == 200
        assert salida.json()["operador_entrada_id"] == entra["operador_id"]
        assert salida.json()["operador_salida_id"] == sale["operador_id"]
        guardada = connection.execute(text(
            "SELECT operador_entrada_id, operador_salida_id FROM estancia WHERE id = :i"),
            {"i": entrada.json()["id"]}).one()
        assert tuple(guardada) == (entra["operador_id"], sale["operador_id"])

        # El historial muestra el nombre de los operadores de la sesión.
        historial = client.get("/estancias/historial", params={"placa": placa},
                               headers=iniciar_sesion(client, entra)).json()["items"][0]
        assert historial["operador_entrada"] == f"Operador {entra['usuario']}"
        assert historial["operador_salida"] == f"Operador {sale['usuario']}"

        # Con el cuerpo antiguo (operador_id) la solicitud se rechaza sin tocar nada.
        rechazada = client.post("/estancias/entrada", json={"placa": placa, "operador_id": entra["operador_id"]},
                                headers=iniciar_sesion(client, entra))
        assert rechazada.status_code == 422
        assert connection.scalar(text("SELECT count(*) FROM estancia WHERE celda_id = :c"), {"c": celda}) == 1
