"""Ayudas para las pruebas de integración: todo ocurre en una transacción que se revierte."""
import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_engine, get_session
from app.main import app
from app.security import hashear_clave

solo_postgres = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requiere PostgreSQL local."
)

CLAVE_PRUEBA = "clave-de-prueba-123"


def token_unico(prefijo: str = "T") -> str:
    return f"{prefijo}-{uuid4().hex[:10]}".upper()


@contextmanager
def entorno_bd():
    """Entrega (cliente, conexión). La sesión de la API comparte la transacción y se revierte al salir."""
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(text("SELECT current_database()")) == "autos_colombia"
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                def override():
                    yield session

                app.dependency_overrides[get_session] = override
                try:
                    with TestClient(app) as client:
                        yield client, connection
                finally:
                    app.dependency_overrides.pop(get_session, None)
        finally:
            transaction.rollback()


def crear_cuenta(connection, rol: str = "OPERADOR", clave: str = CLAVE_PRUEBA, usuario: str | None = None) -> dict:
    """Crea operador + usuario y devuelve sus datos (la clave en claro solo existe en la prueba)."""
    usuario = usuario or token_unico("u").lower()
    operador_id = connection.scalar(
        text("INSERT INTO operador(nombre, telefono) VALUES (:n, '3000000000') RETURNING id"),
        {"n": f"Operador {usuario}"},
    )
    usuario_id = connection.scalar(
        text("INSERT INTO usuario(nombre_usuario, clave_hash, rol, operador_id) "
             "VALUES (:u, :h, :r, :o) RETURNING id"),
        {"u": usuario, "h": hashear_clave(clave), "r": rol, "o": operador_id},
    )
    return {"usuario": usuario, "usuario_id": usuario_id, "operador_id": operador_id, "clave": clave, "rol": rol}


def iniciar_sesion(client, cuenta: dict) -> dict:
    """Inicia sesión por la API y devuelve los encabezados Authorization listos para usar."""
    respuesta = client.post("/auth/login", json={"usuario": cuenta["usuario"], "contrasena": cuenta["clave"]})
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['token']}"}
