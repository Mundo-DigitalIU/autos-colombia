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


def test_tarifas_y_pagos_de_ejemplo_declarados_al_inicio():
    assert seed.TARIFAS == {"MOTO": 100000, "AUTOMOVIL": 250000, "CAMIONETA": 250000}
    assert seed.DIAS_PAGOS_EJEMPLO == (10, 45)


def _contar(connection, tabla: str) -> int:
    return connection.scalar(text(f"SELECT count(*) FROM {tabla}"))


def _estado(client, placa: str) -> str:
    (item,) = client.get("/pagos/estado", params={"q": placa}).json()["items"]
    return item["estado"]


@solo_postgres
def test_seed_carga_tarifas_y_dos_pagos_sin_duplicar():
    from datetime import timedelta
    from app.services.pago import hoy_bogota

    with entorno_bd() as (client, connection):
        # Una tarifa que ya existe conserva su valor; las que faltan se crean.
        connection.execute(text("DELETE FROM pago"))
        connection.execute(text("DELETE FROM tarifa WHERE tipo_vehiculo <> 'MOTO'"))
        connection.execute(text(
            "INSERT INTO tarifa(tipo_vehiculo, valor_mensual) VALUES ('MOTO', 123456) "
            "ON CONFLICT (tipo_vehiculo) DO UPDATE SET valor_mensual = 123456"))
        with _sesion(connection) as session:
            resumen, _ = seed.cargar(session)
            session.flush()
            assert resumen["tarifas"] == [2, 1] and resumen["pagos"] == [2, 0]
            tarifas = dict(connection.execute(text("SELECT tipo_vehiculo, valor_mensual FROM tarifa")).all())
            assert tarifas == {"MOTO": 123456, "AUTOMOVIL": 250000, "CAMIONETA": 250000}

            pagos = connection.execute(text(
                "SELECT p.cliente_id, p.vehiculo_id, p.valor, p.vigencia_desde, p.vigencia_hasta, p.estado, "
                "o.nombre AS operador, v.placa, v.tipo FROM pago p "
                "JOIN operador o ON o.id = p.operador_id JOIN vehiculo v ON v.id = p.vehiculo_id "
                "ORDER BY p.vigencia_desde DESC")).all()
            assert len(pagos) == 2 and pagos[0].cliente_id != pagos[1].cliente_id
            assert all(p.operador == "Administrador" and p.estado == "REGISTRADO" for p in pagos)
            assert all(p.vigencia_hasta == p.vigencia_desde + timedelta(days=30) for p in pagos)
            assert all(p.valor == tarifas[p.tipo] for p in pagos)
            reciente, antiguo = pagos
            hoy = hoy_bogota()
            assert reciente.vigencia_desde == hoy - timedelta(days=10)
            assert antiguo.vigencia_desde == hoy - timedelta(days=45)
            assert _estado(client, reciente.placa) == "AL_DIA"
            assert _estado(client, antiguo.placa) == "VENCIDA"
            otros = client.get("/pagos/estado", params={"estado": "SIN_PAGOS", "limit": 100}).json()["items"]
            assert reciente.placa not in {i["placa"] for i in otros} and len(otros) >= 1

            # Segunda ejecución seguida: no se duplica nada.
            antes = (_contar(connection, "pago"), _contar(connection, "tarifa"), _contar(connection, "cliente"),
                     _contar(connection, "vehiculo"))
            resumen, _ = seed.cargar(session)
            session.flush()
            assert resumen["tarifas"] == [0, 3] and resumen["pagos"] == [0, 2]
            assert antes == (_contar(connection, "pago"), _contar(connection, "tarifa"),
                             _contar(connection, "cliente"), _contar(connection, "vehiculo")) == (2, 3, antes[2], antes[3])


@solo_postgres
def test_seed_crea_clientes_de_ejemplo_si_no_hay_vehiculos_suficientes(monkeypatch):
    monkeypatch.setattr(seed, "VEHICULOS", [])
    monkeypatch.setattr(seed, "CLIENTES", [])
    with entorno_bd() as (_, connection):
        connection.execute(text("DELETE FROM pago"))
        existentes = connection.execute(text("SELECT id, nombre FROM cliente ORDER BY id")).all()
        with _sesion(connection) as session:
            seed.cargar(session)
            session.flush()
            clientes = connection.execute(text(
                "SELECT c.documento, count(p.id) AS pagos FROM cliente c JOIN pago p ON p.cliente_id = c.id "
                "GROUP BY c.documento ORDER BY c.documento")).all()
            assert [tuple(c) for c in clientes] == [("1000000101", 1), ("1000000102", 1)]
            assert connection.execute(text(
                "SELECT id, nombre FROM cliente WHERE id <= :m ORDER BY id"),
                {"m": existentes[-1].id if existentes else 0}).all() == existentes  # los existentes siguen igual
            antes = (_contar(connection, "pago"), _contar(connection, "cliente"), _contar(connection, "vehiculo"))
            seed.cargar(session)
            session.flush()
            assert antes == (_contar(connection, "pago"), _contar(connection, "cliente"), _contar(connection, "vehiculo"))
