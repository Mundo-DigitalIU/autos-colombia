"""Etapa 1: usuario, sesión, cliente, vehiculo.cliente_id y restricción del tipo de celda."""
import os
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import get_engine
from app.models import Base, Celda, Cliente, Sesion, Usuario, Vehiculo

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)


def test_modelos_normalizan_y_validan():
    usuario = Usuario(nombre_usuario="  Admin ", clave_hash="x", rol="ADMINISTRADOR", operador_id=1)
    assert usuario.nombre_usuario == "admin"
    with pytest.raises(ValueError):
        Usuario(rol="SUPERUSUARIO")
    with pytest.raises(ValueError):
        Usuario(nombre_usuario="   ")
    cliente = Cliente(nombre=" Ana ", documento=" 123 ", telefono=" 300 ")
    assert (cliente.nombre, cliente.documento, cliente.telefono) == ("Ana", "123", "300")
    with pytest.raises(ValueError):
        Cliente(documento=" \t")


def test_metadatos_de_las_tablas_nuevas():
    tablas = Base.metadata.tables
    usuario, sesion, cliente = tablas["usuario"], tablas["sesion"], tablas["cliente"]
    assert usuario.c.operador_id.foreign_keys and not usuario.c.operador_id.nullable
    assert next(iter(usuario.c.operador_id.foreign_keys)).ondelete == "RESTRICT"
    assert next(iter(sesion.c.usuario_id.foreign_keys)).ondelete == "CASCADE"
    assert sesion.c.revocada.nullable and not sesion.c.expira.nullable
    assert tablas["vehiculo"].c.cliente_id.nullable
    assert next(iter(tablas["vehiculo"].c.cliente_id.foreign_keys)).ondelete == "RESTRICT"
    assert {"documento"} in [set(c.columns.keys()) for c in cliente.constraints if isinstance(c, sa.UniqueConstraint)]
    assert {"token_hash"} in [set(c.columns.keys()) for c in sesion.constraints if isinstance(c, sa.UniqueConstraint)]


def test_migracion_0003_encadena_con_la_0002():
    import importlib.util
    from pathlib import Path
    ruta = Path(__file__).resolve().parents[1] / "migrations/versions/0003_usuarios_clientes.py"
    spec = importlib.util.spec_from_file_location("migracion_0003", ruta)
    migracion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracion)
    assert (migracion.revision, migracion.down_revision) == ("0003", "0002")


@solo_postgres
def test_restricciones_en_postgres():
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
            token = uuid4().hex[:10]
            operador = connection.scalar(text(
                "INSERT INTO operador(nombre, telefono) VALUES (:n, '1') RETURNING id"), {"n": token})

            def fallo(sql: str, params: dict, sqlstate: str) -> None:
                with pytest.raises(IntegrityError) as error:
                    with connection.begin_nested():
                        connection.execute(text(sql), params)
                assert error.value.orig.sqlstate == sqlstate

            insertar_usuario = ("INSERT INTO usuario(nombre_usuario, clave_hash, rol, operador_id) "
                                "VALUES (:u, :h, :r, :o) RETURNING id")
            usuario = connection.scalar(text(insertar_usuario),
                                        {"u": f"u-{token}", "h": "hash", "r": "OPERADOR", "o": operador})
            fallo(insertar_usuario, {"u": f"u-{token}", "h": "hash", "r": "OPERADOR", "o": operador}, "23505")
            otro_operador = connection.scalar(text(
                "INSERT INTO operador(nombre, telefono) VALUES (:n, '1') RETURNING id"), {"n": token + "b"})
            fallo(insertar_usuario, {"u": f"u-{token}", "h": "hash", "r": "OPERADOR", "o": otro_operador}, "23505")
            fallo(insertar_usuario, {"u": f"V-{token}", "h": "hash", "r": "OPERADOR", "o": otro_operador}, "23514")
            fallo(insertar_usuario, {"u": f"w-{token}", "h": " ", "r": "OPERADOR", "o": otro_operador}, "23514")
            fallo(insertar_usuario, {"u": f"w-{token}", "h": "hash", "r": "JEFE", "o": otro_operador}, "23514")
            # El operador de una cuenta no se puede borrar (RESTRICT).
            fallo("DELETE FROM operador WHERE id = :o", {"o": operador}, "23001")

            # Sesiones: token único y borrado en cascada con el usuario.
            insertar_sesion = ("INSERT INTO sesion(usuario_id, token_hash, expira) "
                               "VALUES (:u, :t, now() + interval '8 hours')")
            connection.execute(text(insertar_sesion), {"u": usuario, "t": f"t-{token}"})
            fallo(insertar_sesion, {"u": usuario, "t": f"t-{token}"}, "23505")
            connection.execute(text("DELETE FROM usuario WHERE id = :u"), {"u": usuario})
            assert connection.scalar(text("SELECT count(*) FROM sesion WHERE token_hash = :t"),
                                     {"t": f"t-{token}"}) == 0

            # Clientes: documento único, recortado y no vacío; vehículo con FK RESTRICT.
            insertar_cliente = ("INSERT INTO cliente(nombre, documento, telefono) "
                                "VALUES ('Ana', :d, '300') RETURNING id")
            cliente = connection.scalar(text(insertar_cliente), {"d": f"D{token}"})
            fallo(insertar_cliente, {"d": f"D{token}"}, "23505")
            fallo(insertar_cliente, {"d": f" D{token}x "}, "23514")
            fallo(insertar_cliente, {"d": "  "}, "23514")
            connection.execute(text(
                "INSERT INTO vehiculo(placa, color, modelo, marca, tipo, cliente_id) "
                "VALUES (:p, 'Rojo', 2020, 'X', 'MOTO', :c)"), {"p": f"CL-{token}".upper(), "c": cliente})
            fallo("DELETE FROM cliente WHERE id = :c", {"c": cliente}, "23001")

            # El tipo de celda: las inserciones nuevas solo admiten los tres tipos.
            insertar_celda = "INSERT INTO celda(codigo, tipo) VALUES (:c, :t)"
            connection.execute(text(insertar_celda), {"c": f"T-{token}".upper(), "t": "CAMIONETA"})
            fallo(insertar_celda, {"c": f"U-{token}".upper(), "t": "Libre"}, "23514")
            fallo(insertar_celda, {"c": f"U-{token}".upper(), "t": "moto"}, "23514")
            # NOT VALID: la restricción existe pero no revisó las filas antiguas.
            assert connection.scalar(text(
                "SELECT convalidated FROM pg_constraint WHERE conname = 'ck_celda_tipo_valido'")) is False
        finally:
            transaction.rollback()
