"""Etapa 7: el seed es idempotente, crea las cuentas y nunca fija contraseñas en el código."""
import secrets
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

import seed
from app.models import Cliente, Usuario, Vehiculo
from app.security import verificar_clave
from utiles_bd import entorno_bd, solo_postgres


def test_las_80_celdas_del_seed():
    assert len(seed.CELDAS) == 80 and len({codigo for codigo, _ in seed.CELDAS}) == 80
    assert Counter(tipo for _, tipo in seed.CELDAS) == {"AUTOMOVIL": 55, "CAMIONETA": 5, "MOTO": 20}
    assert seed.CELDAS[0] == ("A-01", "AUTOMOVIL") and ("K-05", "CAMIONETA") in seed.CELDAS
    assert seed.CELDAS[-1] == ("M-20", "MOTO")


def test_los_clientes_cubren_los_vehiculos_existentes_sin_repetir():
    placas = [placa for *_, placas in seed.CLIENTES for placa in placas]
    assert len(seed.CLIENTES) == 3
    assert sorted(placas) == sorted(v[0] for v in seed.VEHICULOS)


def test_el_codigo_no_contiene_contrasenas():
    fuente = Path(seed.__file__).read_text(encoding="utf-8")
    assert "SEED_ADMIN_CLAVE" in fuente and "SEED_OPERADOR_CLAVE" in fuente
    for linea in fuente.splitlines():
        if linea.strip().startswith(("CLAVE", "ADMIN_CLAVE", "OPERADOR_CLAVE")):
            assert "=" not in linea or "CLAVE_MINIMA" in linea


def _sesion(connection) -> Session:
    return Session(bind=connection, join_transaction_mode="create_savepoint")


def _sin_cuentas(connection) -> None:
    connection.execute(text("DELETE FROM usuario WHERE nombre_usuario IN ('admin', 'operador')"))


@solo_postgres
def test_seed_idempotente_genera_claves_una_sola_vez():
    with entorno_bd() as (_, connection):
        _sin_cuentas(connection)
        with _sesion(connection) as session:
            resumen, generadas = seed.cargar(session)
            session.flush()
            assert sorted(usuario for usuario, _ in generadas) == ["admin", "operador"]
            assert all(len(clave) >= 12 for _, clave in generadas)
            assert resumen["cuentas"] == [2, 0]
            for usuario, clave in generadas:
                fila = session.scalar(select(Usuario).where(Usuario.nombre_usuario == usuario))
                assert verificar_clave(clave, fila.clave_hash) and clave not in fila.clave_hash
            roles = dict(session.execute(select(Usuario.nombre_usuario, Usuario.rol)).all())
            assert roles["admin"] == "ADMINISTRADOR" and roles["operador"] == "OPERADOR"
            nombres = dict(connection.execute(text(
                "SELECT u.nombre_usuario, o.nombre FROM usuario u JOIN operador o ON o.id = u.operador_id "
                "WHERE u.nombre_usuario IN ('admin', 'operador')")).all())
            assert nombres == {"admin": "Administrador", "operador": "Operador Portería"}

            # Datos de referencia: 80 celdas, vehículos vinculados a los 3 clientes.
            tipos = dict(connection.execute(text("SELECT codigo, tipo FROM celda")).all())
            assert all(tipos[codigo] == tipo for codigo, tipo in seed.CELDAS)
            documentos = [d for _, d, _, _ in seed.CLIENTES]
            clientes = session.scalars(select(Cliente).where(Cliente.documento.in_(documentos))).all()
            assert len(clientes) == 3
            vinculados = session.scalars(select(Vehiculo).where(
                Vehiculo.placa.in_([v[0] for v in seed.VEHICULOS]))).all()
            assert len(vinculados) == 10 and all(v.cliente_id is not None for v in vinculados)

            # Segunda ejecución: nada nuevo, ninguna contraseña nueva ni cambiada.
            antes = dict(connection.execute(text("SELECT nombre_usuario, clave_hash FROM usuario")).all())
            resumen, generadas = seed.cargar(session)
            session.flush()
            assert generadas == []
            assert all(nuevos == 0 for nuevos, _ in resumen.values())
            assert dict(connection.execute(text("SELECT nombre_usuario, clave_hash FROM usuario")).all()) == antes


@solo_postgres
def test_seed_usa_las_contrasenas_del_entorno():
    with entorno_bd() as (_, connection):
        _sin_cuentas(connection)
        claves = {"SEED_ADMIN_CLAVE": secrets.token_urlsafe(12), "SEED_OPERADOR_CLAVE": secrets.token_urlsafe(12)}
        with _sesion(connection) as session:
            _, generadas = seed.cargar(session, claves)
            session.flush()
            assert generadas == []
            for usuario, variable in (("admin", "SEED_ADMIN_CLAVE"), ("operador", "SEED_OPERADOR_CLAVE")):
                fila = session.scalar(select(Usuario).where(Usuario.nombre_usuario == usuario))
                assert verificar_clave(claves[variable], fila.clave_hash)


@solo_postgres
def test_una_clave_del_entorno_demasiado_corta_se_rechaza_sin_mostrarla():
    with entorno_bd() as (_, connection):
        _sin_cuentas(connection)
        corta = "x" + secrets.token_hex(2)[:3]
        with _sesion(connection) as session:
            with pytest.raises(seed.ClaveInvalida) as error:
                seed.cargar(session, {"SEED_ADMIN_CLAVE": corta})
            assert corta not in str(error.value) and "SEED_ADMIN_CLAVE" in str(error.value)
