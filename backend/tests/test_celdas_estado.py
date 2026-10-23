"""Consulta de celdas con su estado (RF-11).

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

CELDAS_OCUPADAS = (
    "SELECT count(*) FROM celda c WHERE EXISTS "
    "(SELECT 1 FROM estancia e WHERE e.celda_id = c.id AND e.salida IS NULL)"
)


def test_ruta_celdas_existe_en_openapi():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        assert "get" in schema["paths"]["/estancias/celdas"]


@pytest.mark.parametrize("consulta", ["limit=0", "limit=101", "offset=-1", "limit=abc", "offset=abc"])
def test_parametros_invalidos_se_rechazan(consulta):
    with TestClient(app) as client:
        assert client.get(f"/estancias/celdas?{consulta}").status_code == 422


@solo_postgres
def test_celdas_muestra_ocupada_o_disponible():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            token = "TEST-CELDAS-" + uuid4().hex[:8].upper()
            operador_id = connection.scalar(
                text("INSERT INTO operador(nombre, telefono) VALUES (:nombre, '001') RETURNING id"),
                {"nombre": token},
            )
            vehiculos = [
                connection.scalar(
                    text("INSERT INTO vehiculo(placa, color, modelo, marca, tipo) "
                         "VALUES (:placa, 'Prueba', 2026, 'Prueba', 'MOTO') RETURNING id"),
                    {"placa": f"{token}-{n}"},
                )
                for n in range(2)
            ]
            celdas = [
                connection.scalar(
                    text("INSERT INTO celda(codigo, tipo) VALUES (:codigo, 'Libre') RETURNING id"),
                    {"codigo": f"{token}-{n}"},
                )
                for n in range(3)
            ]
            # Celda 0: libre y sin historial. Celda 1: ocupada. Celda 2: tuvo una estancia que ya cerró.
            connection.execute(
                text("INSERT INTO estancia(vehiculo_id, celda_id, entrada, operador_entrada_id) "
                     "VALUES (:vehiculo, :celda, now() - interval '1 hour', :operador)"),
                {"vehiculo": vehiculos[0], "celda": celdas[1], "operador": operador_id},
            )
            connection.execute(
                text("INSERT INTO estancia(vehiculo_id, celda_id, entrada, salida, "
                     "operador_entrada_id, operador_salida_id) "
                     "VALUES (:vehiculo, :celda, now() - interval '2 hours', now() - interval '1 hour', "
                     ":operador, :operador)"),
                {"vehiculo": vehiculos[1], "celda": celdas[2], "operador": operador_id},
            )

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        def estados(cuerpo):
                            return {i["codigo"]: i["estado"] for i in cuerpo["items"]}

                        respuesta = client.get("/estancias/celdas?limit=100")
                        assert respuesta.status_code == 200
                        cuerpo = respuesta.json()
                        total = connection.scalar(text("SELECT count(*) FROM celda"))
                        ocupadas = connection.scalar(text(CELDAS_OCUPADAS))
                        assert cuerpo["total"] == total
                        assert cuerpo["ocupadas"] == ocupadas
                        assert cuerpo["disponibles"] == total - ocupadas
                        actual = estados(cuerpo)
                        assert actual[f"{token}-0"] == "DISPONIBLE"
                        assert actual[f"{token}-1"] == "OCUPADA"
                        assert actual[f"{token}-2"] == "DISPONIBLE"
                        item = next(i for i in cuerpo["items"] if i["codigo"] == f"{token}-1")
                        assert item["tipo"] == "Libre"

                        # Cuando el vehículo sale, su celda queda disponible.
                        connection.execute(
                            text("UPDATE estancia SET salida = now(), operador_salida_id = :operador "
                                 "WHERE celda_id = :celda AND salida IS NULL"),
                            {"operador": operador_id, "celda": celdas[1]},
                        )
                        despues = client.get("/estancias/celdas?limit=100").json()
                        assert estados(despues)[f"{token}-1"] == "DISPONIBLE"
                        assert despues["ocupadas"] == ocupadas - 1
                        assert despues["disponibles"] == cuerpo["disponibles"] + 1

                        # Paginación: los totales no dependen de la página.
                        pagina = client.get("/estancias/celdas?offset=0&limit=1").json()
                        assert len(pagina["items"]) == 1
                        assert (pagina["offset"], pagina["limit"]) == (0, 1)
                        assert pagina["total"] == total and pagina["ocupadas"] == despues["ocupadas"]
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()
