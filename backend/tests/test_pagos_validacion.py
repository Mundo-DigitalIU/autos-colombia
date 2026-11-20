"""Pagos con sesión simulada: validación del cuerpo, permisos por rol y concurrencia real."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.orm import Session

from app.database import get_engine
from app.main import app
from app.services.auth import MENSAJE_PERMISO
from app.models import Cliente, Operador, Pago, Tarifa, Vehiculo


def test_medio_de_pago_invalido_o_ausente_es_422():
    with TestClient(app) as client:
        for cuerpo in (
            {"placa": "ABC123", "medio_pago": "CHEQUE"},
            {"placa": "ABC123", "medio_pago": "efectivo"},
            {"placa": "ABC123", "medio_pago": ""},
            {"placa": "ABC123"},
            {"medio_pago": "EFECTIVO"},
            {"placa": "   ", "medio_pago": "EFECTIVO"},
        ):
            assert client.post("/pagos", json=cuerpo).status_code == 422, cuerpo


def test_el_operador_y_el_valor_no_viajan_en_el_cuerpo():
    with TestClient(app) as client:
        base = {"placa": "ABC123", "medio_pago": "EFECTIVO"}
        assert client.post("/pagos", json={**base, "operador_id": 1}).status_code == 422
        assert client.post("/pagos", json={**base, "valor": 1}).status_code == 422


def test_no_hay_delete_ni_put():
    with TestClient(app) as client:
        assert client.delete("/pagos/1").status_code == 405
        assert client.put("/pagos/1", json={}).status_code == 405


def test_el_operador_no_puede_anular(fijar_sesion):
    fijar_sesion("OPERADOR")
    with TestClient(app) as client:
        respuesta = client.post("/pagos/1/anular", json={"motivo": "Error"})
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": MENSAJE_PERMISO}


@pytest.mark.parametrize("rol", ["OPERADOR", "ADMINISTRADOR"])
def test_ambos_roles_pasan_la_validacion_de_las_rutas_de_consulta(rol, fijar_sesion):
    """Con un rol válido las rutas no devuelven 401 ni 403 (aquí la fecha inválida corta antes de la base)."""
    fijar_sesion(rol)
    with TestClient(app) as client:
        respuesta = client.get("/pagos", params={"desde": "2026-09-30", "hasta": "2026-09-01"})
        assert respuesta.status_code == 422
        assert respuesta.json() == {"detail": "La fecha desde no puede ser posterior a la fecha hasta."}


@pytest.fixture
def datos():
    if os.getenv("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Requiere PostgreSQL local.")
    engine = get_engine()
    token = "TEST-PAG-" + uuid4().hex.upper()
    with Session(engine) as s, s.begin():
        assert s.scalar(text("SELECT current_database()")) == "autos_colombia"
        assert s.scalar(text("SELECT version_num FROM alembic_version")) == "0004"
        tarifa = s.scalar(select(Tarifa).where(Tarifa.tipo_vehiculo == "MOTO"))
        creada = None
        if tarifa is None:  # sin tarifas cargadas: se crea una y se retira al terminar
            creada = Tarifa(tipo_vehiculo="MOTO", valor_mensual=50000)
            s.add(creada)
        cliente = Cliente(nombre=token, documento=token, telefono="001")
        operadores = [Operador(nombre=f"{token}-{n}", telefono="001") for n in range(2)]
        s.add_all([cliente, *operadores])
        s.flush()
        vehiculo = Vehiculo(placa=token, color="Prueba", modelo=2026, marca="Prueba", tipo="MOTO",
                            cliente_id=cliente.id)
        s.add(vehiculo)
        s.flush()
        data = {"placa": token, "vehiculo": vehiculo.id, "cliente": cliente.id,
                "operadores": [o.id for o in operadores], "tarifa": creada.id if creada else None}
    try:
        yield data
    finally:
        with Session(engine) as s, s.begin():
            s.execute(delete(Pago).where(Pago.vehiculo_id == data["vehiculo"]))
            s.execute(delete(Vehiculo).where(Vehiculo.id == data["vehiculo"]))
            s.execute(delete(Cliente).where(Cliente.id == data["cliente"]))
            s.execute(delete(Operador).where(Operador.id.in_(data["operadores"])))
            if data["tarifa"]:
                s.execute(delete(Tarifa).where(Tarifa.id == data["tarifa"]))
        with Session(engine) as s:
            assert s.scalar(select(func.count()).select_from(Pago).where(Pago.vehiculo_id == data["vehiculo"])) == 0


def test_dos_registros_simultaneos_del_mismo_vehiculo_crean_un_solo_pago(datos):
    barrier = Barrier(2, timeout=15)

    def sincronizar(conn, cursor, statement, parameters, context, executemany):
        # Las dos solicitudes llegan juntas al bloqueo del vehículo; la segunda debe esperar a la primera.
        if "FROM vehiculo" in statement and "FOR UPDATE" in statement:
            barrier.wait()

    def enviar(n):
        with TestClient(app) as client:
            return client.post("/pagos", json={"placa": datos["placa"], "medio_pago": "EFECTIVO"},
                               headers={"X-Operador-Prueba": str(datos["operadores"][n])})

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", sincronizar)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respuestas = list(pool.map(enviar, range(2)))
    finally:
        event.remove(engine, "before_cursor_execute", sincronizar)
    assert sorted(r.status_code for r in respuestas) == [201, 409]
    perdedora = next(r.json() for r in respuestas if r.status_code == 409)
    assert perdedora == {"detail": "La mensualidad de este vehículo ya está pagada."}
    with Session(engine) as s:
        pagos = s.scalars(select(Pago).where(Pago.vehiculo_id == datos["vehiculo"])).all()
        assert len(pagos) == 1 and pagos[0].estado == "REGISTRADO"
        ganadora = next(r.json() for r in respuestas if r.status_code == 201)
        assert pagos[0].id == ganadora["id"]
