"""Entrada con asignación automática de celda (RF-05).

Las pruebas de esquema no necesitan base de datos. La de integración se habilita
con RUN_POSTGRES_TESTS=1 y revierte todo lo que crea.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app
from app.models import Celda
from app.schemas.estancia import EntradaCrear

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


def test_entrada_sin_celda_es_valida():
    data = EntradaCrear(placa="TEST", operador_id=1)
    assert data.celda_id is None


def test_entrada_con_celda_sigue_funcionando():
    assert EntradaCrear(placa="TEST", celda_id=3, operador_id=1).celda_id == 3


@pytest.mark.parametrize("celda_id", [0, True, "1", 9223372036854775808])
def test_celda_invalida_se_sigue_rechazando(celda_id):
    with pytest.raises(ValidationError):
        EntradaCrear(placa="TEST", celda_id=celda_id, operador_id=1)


@solo_postgres
def test_entrada_asigna_celda_libre_del_mismo_tipo():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            libres = connection.scalar(text(
                "SELECT count(*) FROM celda c WHERE c.tipo = 'MOTO' AND NOT EXISTS "
                "(SELECT 1 FROM estancia e WHERE e.celda_id = c.id AND e.salida IS NULL)"
            ))
            token = "TEST-AUTO-" + uuid4().hex[:8].upper()
            operador_id = connection.scalar(
                text("INSERT INTO operador(nombre, telefono) VALUES (:nombre, '001') RETURNING id"),
                {"nombre": token},
            )
            placas = [f"{token}-{n}" for n in range(libres + 1)]
            for placa in placas:
                connection.execute(
                    text("INSERT INTO vehiculo(placa, color, modelo, marca, tipo) "
                         "VALUES (:placa, 'Prueba', 2026, 'Prueba', 'MOTO')"),
                    {"placa": placa},
                )

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        celdas_usadas = []
                        for placa in placas[:libres]:
                            respuesta = client.post(
                                "/estancias/entrada", json={"placa": placa, "operador_id": operador_id}
                            )
                            assert respuesta.status_code == 201
                            celda_id = respuesta.json()["celda_id"]
                            assert connection.scalar(select(Celda.tipo).where(Celda.id == celda_id)) == "MOTO"
                            celdas_usadas.append(celda_id)
                        assert len(set(celdas_usadas)) == libres

                        # Sin celdas libres de moto: 409 y sin cambios.
                        sin_celda = client.post(
                            "/estancias/entrada", json={"placa": placas[libres], "operador_id": operador_id}
                        )
                        assert sin_celda.status_code == 409
                        assert sin_celda.json()["detail"] == "No hay celdas disponibles para este tipo de vehículo."

                        # Un vehículo que ya está dentro no puede volver a entrar.
                        if libres:
                            repetida = client.post(
                                "/estancias/entrada", json={"placa": placas[0], "operador_id": operador_id}
                            )
                            assert repetida.status_code == 409
                            assert repetida.json()["detail"] == "El vehículo ya está dentro."
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()
