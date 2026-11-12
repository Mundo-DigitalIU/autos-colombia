"""Entrada con celda_id explícita: la celda debe ser del tipo del vehículo.

La comparación de tipos recorta espacios y no distingue mayúsculas. La prueba de
integración se habilita con RUN_POSTGRES_TESTS=1 y revierte todo lo que crea.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app
from app.services.estancia import normalizar_tipo

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


@pytest.mark.parametrize("tipo", ["MOTO", "moto", "  Moto ", "\tmoto\n"])
def test_normalizar_tipo_ignora_mayusculas_y_espacios(tipo):
    assert normalizar_tipo(tipo) == "MOTO"


@solo_postgres
def test_entrada_con_celda_valida_el_tipo_del_vehiculo(fijar_sesion):
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            token = "TEST-TIPO-" + uuid4().hex[:8].upper()
            operador_id = connection.scalar(
                text("INSERT INTO operador(nombre, telefono) VALUES (:nombre, '001') RETURNING id"),
                {"nombre": token},
            )
            placas = {nombre: f"{token}-{nombre}" for nombre in ("A", "B", "C")}
            for placa in placas.values():
                connection.execute(
                    text("INSERT INTO vehiculo(placa, color, modelo, marca, tipo) "
                         "VALUES (:placa, 'Prueba', 2026, 'Prueba', 'MOTO')"),
                    {"placa": placa},
                )

            fijar_sesion(operador_id=operador_id)

            def crear_celda(sufijo: str, tipo: str) -> int:
                return connection.scalar(
                    text("INSERT INTO celda(codigo, tipo) VALUES (:codigo, :tipo) RETURNING id"),
                    {"codigo": f"{token}-{sufijo}", "tipo": tipo},
                )

            # Las celdas anteriores a la migración 0003 pueden tener tipos sucios; la restricción
            # nueva ya no deja crearlos, así que se retira dentro de esta transacción (se revierte).
            connection.execute(text("ALTER TABLE celda DROP CONSTRAINT ck_celda_tipo_valido"))
            celda_otro_tipo = crear_celda("X", "AUTOMOVIL")
            celda_tipo_exacto = crear_celda("E", "MOTO")
            celda_tipo_sucio = crear_celda("S", "  moto ")

            def estancias() -> int:
                return connection.scalar(text("SELECT count(*) FROM estancia"))

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        antes = estancias()
                        rechazada = client.post("/estancias/entrada", json={
                            "placa": placas["A"], "celda_id": celda_otro_tipo})
                        assert rechazada.status_code == 409
                        assert rechazada.json()["detail"] == "La celda no es del tipo del vehículo."
                        assert estancias() == antes

                        correcta = client.post("/estancias/entrada", json={
                            "placa": placas["A"], "celda_id": celda_tipo_exacto})
                        assert correcta.status_code == 201
                        assert correcta.json()["celda_id"] == celda_tipo_exacto

                        # Solo difiere en mayúsculas y espacios: es del mismo tipo.
                        sucia = client.post("/estancias/entrada", json={
                            "placa": placas["B"], "celda_id": celda_tipo_sucio})
                        assert sucia.status_code == 201
                        assert sucia.json()["celda_id"] == celda_tipo_sucio

                        # El orden de validación se mantiene: celda ocupada antes que tipo.
                        ocupada = client.post("/estancias/entrada", json={
                            "placa": placas["C"], "celda_id": celda_tipo_exacto})
                        assert ocupada.status_code == 409
                        assert ocupada.json()["detail"] == "La celda está ocupada."
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()
