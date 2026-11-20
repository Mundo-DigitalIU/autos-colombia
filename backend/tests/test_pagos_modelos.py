"""Etapa 1 de pagos: migración 0004, modelos Tarifa y Pago y sus restricciones."""
import importlib.util
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import get_engine
from app.models import Base, Pago, Tarifa

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)

RUTA_MIGRACION = Path(__file__).resolve().parents[1] / "migrations/versions/0004_tarifas_pagos.py"


def cargar_migracion():
    spec = importlib.util.spec_from_file_location("migracion_0004", RUTA_MIGRACION)
    migracion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracion)
    return migracion


def test_migracion_0004_encadena_con_la_0003():
    migracion = cargar_migracion()
    assert (migracion.revision, migracion.down_revision) == ("0004", "0003")


def test_modelos_validan_tipo_y_medio_de_pago():
    assert Tarifa(tipo_vehiculo=" MOTO ").tipo_vehiculo == "MOTO"
    with pytest.raises(ValueError):
        Tarifa(tipo_vehiculo="BUS")
    assert Pago(medio_pago="EFECTIVO").medio_pago == "EFECTIVO"
    with pytest.raises(ValueError):
        Pago(medio_pago="CHEQUE")


def test_metadatos_de_tarifa_y_pago():
    tarifa, pago = Base.metadata.tables["tarifa"], Base.metadata.tables["pago"]
    assert isinstance(tarifa.c.valor_mensual.type, sa.Numeric)
    assert (tarifa.c.valor_mensual.type.precision, tarifa.c.valor_mensual.type.scale) == (12, 2)
    assert isinstance(pago.c.vigencia_desde.type, sa.Date) and isinstance(pago.c.vigencia_hasta.type, sa.Date)
    assert pago.c.fecha_pago.type.timezone and pago.c.anulado_en.type.timezone
    for columna in ("vehiculo_id", "cliente_id", "operador_id"):
        assert not pago.c[columna].nullable
        assert next(iter(pago.c[columna].foreign_keys)).ondelete == "RESTRICT"
    assert next(iter(pago.c.anulado_por_operador_id.foreign_keys)).ondelete == "RESTRICT"
    assert all(pago.c[c].nullable for c in ("anulado_en", "anulado_por_operador_id", "motivo_anulacion"))
    assert str(pago.c.estado.server_default.arg) == "REGISTRADO"


def test_migracion_0004_coincide_con_los_modelos(monkeypatch):
    migracion = cargar_migracion()
    metadata = sa.MetaData()
    for referenciada in ("operador", "cliente", "vehiculo"):  # tablas de las claves foráneas
        Base.metadata.tables[referenciada].to_metadata(metadata)
    indices = []
    monkeypatch.setattr(migracion.op, "create_table", lambda nombre, *args: sa.Table(nombre, metadata, *args))
    monkeypatch.setattr(
        migracion.op, "create_index",
        lambda nombre, tabla, columnas, **kw: indices.append((nombre, tabla, tuple(columnas), kw.get("unique", False))),
    )
    migracion.upgrade()
    assert {"tarifa", "pago"} <= set(metadata.tables)

    def checks(t):
        return {(c.name, str(c.sqltext)) for c in t.constraints if isinstance(c, sa.CheckConstraint)}

    def unicas(t):
        return {tuple(c.columns.keys()) for c in t.constraints if isinstance(c, sa.UniqueConstraint)}

    def claves(t):
        return {(f.parent.name, f.column.table.name, f.ondelete, f.name) for f in
                (next(iter(c.elements)) for c in t.constraints if isinstance(c, sa.ForeignKeyConstraint))}

    for nombre in ("tarifa", "pago"):
        tabla = metadata.tables[nombre]
        modelo = Base.metadata.tables[nombre]
        assert [(c.name, str(c.type), c.nullable) for c in tabla.columns] == [
            (c.name, str(c.type), c.nullable) for c in modelo.columns
        ]
        assert checks(tabla) == checks(modelo)
        assert unicas(tabla) == unicas(modelo)
        assert claves(tabla) == claves(modelo)
    esperados = {(i.name, i.table.name, tuple(c.name for c in i.columns), i.unique)
                 for i in Base.metadata.tables["pago"].indexes}
    assert {i for i in indices} == esperados


@solo_postgres
def test_0004_sube_y_baja_sin_tocar_el_resto():
    migracion = cargar_migracion()
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
            antes = set(inspect(connection).get_table_names()) - {"pago", "tarifa"}
            with Operations.context(MigrationContext.configure(connection)):
                migracion.downgrade()
                inspector = inspect(connection)
                tablas = set(inspector.get_table_names())
                assert "pago" not in tablas and "tarifa" not in tablas
                assert antes <= tablas  # la base queda como en la 0003
                migracion.upgrade()
            inspector = inspect(connection)
            assert {"pago", "tarifa"} <= set(inspector.get_table_names())
            assert {i["name"] for i in inspector.get_indexes("pago")} == {
                "uq_pago_vehiculo_vigencia_registrado", "ix_pago_vehiculo_id", "ix_pago_cliente_id", "ix_pago_fecha_pago"
            }
        finally:
            transaction.rollback()


@solo_postgres
def test_restricciones_de_tarifa_y_pago_en_postgres():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
            token = uuid4().hex[:10]

            def fallo(sql: str, params: dict, sqlstate: str) -> None:
                with pytest.raises(IntegrityError) as error:
                    with connection.begin_nested():
                        connection.execute(text(sql), params)
                assert error.value.orig.sqlstate == sqlstate

            # Tarifa: tipo único y válido, valor positivo.
            insertar_tarifa = "INSERT INTO tarifa(tipo_vehiculo, valor_mensual) VALUES (:t, :v)"
            tipos_existentes = set(connection.scalars(text("SELECT tipo_vehiculo FROM tarifa")))
            libre = next((t for t in ("MOTO", "AUTOMOVIL", "CAMIONETA") if t not in tipos_existentes), None)
            if libre:
                connection.execute(text(insertar_tarifa), {"t": libre, "v": Decimal("100000.00")})
                repetido = libre
            else:
                repetido = "MOTO"
            fallo(insertar_tarifa, {"t": repetido, "v": Decimal("1.00")}, "23505")
            connection.execute(text("DELETE FROM tarifa WHERE tipo_vehiculo = :t"), {"t": repetido})
            fallo(insertar_tarifa, {"t": "BUS", "v": Decimal("1.00")}, "23514")
            fallo(insertar_tarifa, {"t": repetido, "v": Decimal("0")}, "23514")
            fallo(insertar_tarifa, {"t": repetido, "v": Decimal("-5")}, "23514")

            # Datos base: dos operadores, un cliente y un vehículo.
            operador = connection.scalar(text(
                "INSERT INTO operador(nombre, telefono) VALUES (:n, '1') RETURNING id"), {"n": token})
            otro = connection.scalar(text(
                "INSERT INTO operador(nombre, telefono) VALUES (:n, '1') RETURNING id"), {"n": token + "b"})
            cliente = connection.scalar(text(
                "INSERT INTO cliente(nombre, documento, telefono) VALUES ('Ana', :d, '300') RETURNING id"),
                {"d": f"D{token}"})
            vehiculo = connection.scalar(text(
                "INSERT INTO vehiculo(placa, color, modelo, marca, tipo, cliente_id) "
                "VALUES (:p, 'Rojo', 2020, 'X', 'MOTO', :c) RETURNING id"),
                {"p": f"PG-{token}".upper(), "c": cliente})

            insertar_pago = (
                "INSERT INTO pago(vehiculo_id, cliente_id, valor, medio_pago, vigencia_desde, vigencia_hasta, "
                "operador_id, estado, anulado_en, anulado_por_operador_id, motivo_anulacion) "
                "VALUES (:v, :c, :valor, :medio, :desde, :hasta, :o, :estado, :en, :por, :motivo) RETURNING id"
            )
            base = {"v": vehiculo, "c": cliente, "valor": Decimal("50000.00"), "medio": "EFECTIVO",
                    "desde": date(2026, 9, 1), "hasta": date(2026, 10, 1), "o": operador,
                    "estado": "REGISTRADO", "en": None, "por": None, "motivo": None}
            pago = connection.scalar(text(insertar_pago), base)
            fila = connection.execute(text("SELECT estado, fecha_pago FROM pago WHERE id = :i"), {"i": pago}).one()
            assert fila.estado == "REGISTRADO" and fila.fecha_pago.utcoffset() is not None

            # Valores > 0, medio y estado válidos.
            fallo(insertar_pago, {**base, "valor": Decimal("0"), "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1)}, "23514")
            fallo(insertar_pago, {**base, "valor": Decimal("-1"), "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1)}, "23514")
            fallo(insertar_pago, {**base, "medio": "CHEQUE", "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1)}, "23514")
            fallo(insertar_pago, {**base, "estado": "PENDIENTE", "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1)}, "23514")

            # CHECK de 30 días exactos.
            fallo(insertar_pago, {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 11, 30)}, "23514")
            fallo(insertar_pago, {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 2)}, "23514")

            # Índice único parcial: mismo vehículo y misma vigencia_desde solo una vez mientras esté REGISTRADO.
            fallo(insertar_pago, base, "23505")

            # Coherencia de la anulación.
            anulado = {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1), "estado": "ANULADO",
                       "en": "2026-11-02T10:00:00+00:00", "por": otro, "motivo": "Error de digitación"}
            fallo(insertar_pago, {**anulado, "en": None}, "23514")
            fallo(insertar_pago, {**anulado, "por": None}, "23514")
            fallo(insertar_pago, {**anulado, "motivo": None}, "23514")
            fallo(insertar_pago, {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1), "motivo": "x"}, "23514")
            fallo(insertar_pago, {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1), "por": otro}, "23514")
            fallo(insertar_pago, {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1),
                                  "en": "2026-11-02T10:00:00+00:00"}, "23514")
            ok = connection.scalar(text(insertar_pago), anulado)
            assert ok

            # Un pago ANULADO no bloquea volver a registrar la misma vigencia.
            otro_pago = connection.scalar(text(insertar_pago), {**base, "desde": date(2026, 11, 1), "hasta": date(2026, 12, 1)})
            assert otro_pago and otro_pago != ok

            # Las claves foráneas son RESTRICT.
            fallo("DELETE FROM vehiculo WHERE id = :i", {"i": vehiculo}, "23001")
            fallo("DELETE FROM cliente WHERE id = :i", {"i": cliente}, "23001")
            fallo("DELETE FROM operador WHERE id = :i", {"i": operador}, "23001")
            fallo("DELETE FROM operador WHERE id = :i", {"i": otro}, "23001")
        finally:
            transaction.rollback()
