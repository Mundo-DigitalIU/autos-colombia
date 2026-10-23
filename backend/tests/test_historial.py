"""Historial de entradas y salidas por placa y rango de fechas (RF-09).

Las pruebas de validación y de fechas no necesitan datos. La de integración se
habilita con RUN_POSTGRES_TESTS=1 y revierte todo lo que crea.
"""
import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app
from app.services.estancia import rango_entrada

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


def test_ruta_historial_existe_en_openapi():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        assert "get" in schema["paths"]["/estancias/historial"]


@pytest.mark.parametrize("consulta", [
    "desde=2026-13-01", "hasta=abc", "desde=22/10/2026",
    "limit=0", "limit=101", "offset=-1",
    "desde=2026-10-23&hasta=2026-10-22",
])
def test_parametros_invalidos_se_rechazan(consulta):
    with TestClient(app) as client:
        assert client.get(f"/estancias/historial?{consulta}").status_code == 422


def test_rango_usa_la_hora_de_bogota():
    # El 22 de octubre en Bogotá (UTC-5) empieza a las 05:00 UTC y termina a las 05:00 UTC del día siguiente.
    inicio, fin = rango_entrada(date(2026, 10, 22), date(2026, 10, 22))
    assert inicio == datetime(2026, 10, 22, 5, tzinfo=timezone.utc)
    assert fin == datetime(2026, 10, 23, 5, tzinfo=timezone.utc)


def test_rango_admite_limites_vacios():
    assert rango_entrada(None, None) == (None, None)
    assert rango_entrada(date(2026, 10, 22), None)[1] is None
    assert rango_entrada(None, date(2026, 10, 22))[0] is None
    assert rango_entrada(None, date.max)[1] is None


@solo_postgres
def test_historial_filtra_por_placa_y_fechas():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            token = "TEST-HIST-" + uuid4().hex[:8].upper()
            operadores = [
                connection.scalar(
                    text("INSERT INTO operador(nombre, telefono) VALUES (:nombre, '001') RETURNING id"),
                    {"nombre": f"{token}-OP{n}"},
                )
                for n in range(2)
            ]
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
                    {"codigo": f"{token}-C{n}"},
                )
                for n in range(3)
            ]

            def estancia(vehiculo, celda, entrada, salida=None, op_entrada=0, op_salida=None):
                connection.execute(
                    text("INSERT INTO estancia(vehiculo_id, celda_id, entrada, salida, "
                         "operador_entrada_id, operador_salida_id) "
                         "VALUES (:vehiculo, :celda, :entrada, :salida, :op_entrada, :op_salida)"),
                    {"vehiculo": vehiculos[vehiculo], "celda": celdas[celda], "entrada": entrada,
                     "salida": salida, "op_entrada": operadores[op_entrada],
                     "op_salida": operadores[op_salida] if op_salida is not None else None},
                )

            utc = timezone.utc
            # Vehículo 0: una estancia cerrada el 22/10 (hora de Bogotá) y otra cerrada el 20/10.
            estancia(0, 0, datetime(2026, 10, 22, 13, 15, tzinfo=utc), datetime(2026, 10, 22, 17, 0, tzinfo=utc),
                     op_entrada=0, op_salida=1)
            estancia(0, 1, datetime(2026, 10, 20, 13, 0, tzinfo=utc), datetime(2026, 10, 20, 14, 0, tzinfo=utc),
                     op_entrada=0, op_salida=0)
            # Vehículo 1: abierta, entró a las 23:30 del 22/10 en Bogotá (04:30 UTC del 23/10).
            estancia(1, 2, datetime(2026, 10, 23, 4, 30, tzinfo=utc))

            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        placa0, placa1 = f"{token}-0", f"{token}-1"

                        # Por placa: la más reciente primero, con celda y operadores.
                        respuesta = client.get(f"/estancias/historial?placa=%20{placa0.lower()}%20")
                        assert respuesta.status_code == 200
                        cuerpo = respuesta.json()
                        assert cuerpo["total"] == 2
                        primera, segunda = cuerpo["items"]
                        assert primera["celda_codigo"] == f"{token}-C0" and segunda["celda_codigo"] == f"{token}-C1"
                        assert primera["operador_entrada"] == f"{token}-OP0"
                        assert primera["operador_salida"] == f"{token}-OP1"
                        assert primera["salida"] is not None

                        # La estancia abierta no tiene salida ni operador de salida.
                        abierta = client.get(f"/estancias/historial?placa={placa1}").json()["items"][0]
                        assert abierta["salida"] is None and abierta["operador_salida"] is None

                        # El día se corta a medianoche de Bogotá: las 04:30 UTC del 23 son del 22.
                        for desde, hasta, esperado in [
                            ("2026-10-22", "2026-10-22", 1),
                            ("2026-10-23", "2026-10-23", 0),
                            ("2026-10-20", "2026-10-20", 0),
                        ]:
                            filtrada = client.get(
                                f"/estancias/historial?placa={placa1}&desde={desde}&hasta={hasta}"
                            ).json()
                            assert filtrada["total"] == esperado
                        assert client.get(
                            f"/estancias/historial?placa={placa0}&desde=2026-10-20&hasta=2026-10-20"
                        ).json()["total"] == 1

                        # Paginación y total sin filtros.
                        todas = connection.scalar(text("SELECT count(*) FROM estancia"))
                        pagina = client.get("/estancias/historial?offset=0&limit=1").json()
                        assert pagina["total"] == todas and len(pagina["items"]) == 1
                        assert (pagina["offset"], pagina["limit"]) == (0, 1)
                        assert client.get("/estancias/historial?placa=NOEXISTE-" + token).json()["total"] == 0
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()
