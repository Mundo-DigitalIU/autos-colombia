"""Consulta de vehículos dentro del parqueadero (RF-08).

Las pruebas de validación no necesitan datos. La de integración se habilita con
RUN_POSTGRES_TESTS=1 y revierte todo lo que crea.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


def test_ruta_dentro_existe_en_openapi():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        assert "get" in schema["paths"]["/estancias/dentro"]


@pytest.mark.parametrize("consulta", ["limit=0", "limit=101", "offset=-1", "limit=abc", "offset=abc"])
def test_parametros_invalidos_se_rechazan(consulta):
    with TestClient(app) as client:
        assert client.get(f"/estancias/dentro?{consulta}").status_code == 422


@solo_postgres
def test_dentro_lista_solo_estancias_abiertas():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            token = "TEST-DENTRO-" + uuid4().hex[:8].upper()
            operador_id = connection.scalar(
                text("INSERT INTO operador(nombre, telefono) VALUES (:nombre, '001') RETURNING id"),
                {"nombre": token},
            )
            vehiculos, celdas = [], []
            for n in range(2):
                celdas.append(connection.scalar(
                    text("INSERT INTO celda(codigo, tipo) VALUES (:codigo, 'Libre') RETURNING id"),
                    {"codigo": f"{token}-{n}"},
                ))
                vehiculos.append(connection.scalar(
                    text("INSERT INTO vehiculo(placa, color, modelo, marca, tipo) "
                         "VALUES (:placa, 'Prueba', 2026, 'Prueba', 'MOTO') RETURNING id"),
                    {"placa": f"{token}-{n}"},
                ))
            # El vehículo 1 entró 2 horas atrás y el vehículo 0 una hora atrás.
            for n, intervalo in ((0, "1 hour"), (1, "2 hours")):
                connection.execute(
                    text("INSERT INTO estancia(vehiculo_id, celda_id, entrada, operador_entrada_id) "
                         f"VALUES (:vehiculo, :celda, now() - interval '{intervalo}', :operador)"),
                    {"vehiculo": vehiculos[n], "celda": celdas[n], "operador": operador_id},
                )

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        abiertas = connection.scalar(text("SELECT count(*) FROM estancia WHERE salida IS NULL"))
                        respuesta = client.get("/estancias/dentro?limit=100")
                        assert respuesta.status_code == 200
                        cuerpo = respuesta.json()
                        assert cuerpo["total"] == abiertas
                        placas = [item["placa"] for item in cuerpo["items"]]
                        # La entrada más antigua aparece primero.
                        assert placas.index(f"{token}-1") < placas.index(f"{token}-0")
                        item = next(i for i in cuerpo["items"] if i["placa"] == f"{token}-0")
                        assert item["celda_codigo"] == f"{token}-0" and item["tipo"] == "MOTO"

                        # Cuando un vehículo sale, deja de aparecer.
                        connection.execute(
                            text("UPDATE estancia SET salida = now(), operador_salida_id = :operador "
                                 "WHERE vehiculo_id = :vehiculo"),
                            {"operador": operador_id, "vehiculo": vehiculos[1]},
                        )
                        despues = client.get("/estancias/dentro?limit=100").json()
                        assert f"{token}-1" not in [i["placa"] for i in despues["items"]]
                        assert despues["total"] == abiertas - 1

                        # Paginación.
                        una = client.get("/estancias/dentro?offset=0&limit=1").json()
                        assert (una["offset"], una["limit"]) == (0, 1)
                        assert len(una["items"]) == 1 and una["total"] == despues["total"]
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()
