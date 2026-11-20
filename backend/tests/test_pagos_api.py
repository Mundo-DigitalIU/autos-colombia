"""Etapa 2 de pagos: registro, vigencia, estados, comprobante y anulación (autenticación real)."""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.services.pago as servicio_pago
from app.main import app
from utiles_bd import crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres, token_unico

SIN_SESION_FALSA = True
TARIFAS = {"MOTO": 50000, "AUTOMOVIL": 100000, "CAMIONETA": 150000}
SIN_SESION = {"detail": "Tu sesión terminó. Inicia sesión otra vez."}


@pytest.fixture
def fijar_fecha(monkeypatch):
    """Simula el día de hoy (a mediodía, hora de Bogotá)."""
    def fijar(dia: date) -> None:
        instante = datetime(dia.year, dia.month, dia.day, 12, tzinfo=servicio_pago.ZONA_LOCAL)
        monkeypatch.setattr(servicio_pago, "ahora_utc", lambda: instante.astimezone(timezone.utc))
    return fijar


@pytest.mark.parametrize("metodo, ruta", [
    ("post", "/pagos"), ("get", "/pagos"), ("get", "/pagos/estado"), ("get", "/pagos/1"),
    ("post", "/pagos/1/anular"),
])
def test_sin_sesion_es_401(metodo, ruta):
    with TestClient(app) as client:
        cuerpo = {"json": {"placa": "ABC123", "medio_pago": "EFECTIVO", "motivo": "x"}} if metodo == "post" else {}
        respuesta = getattr(client, metodo)(ruta, **cuerpo)
        assert respuesta.status_code == 401
        assert respuesta.json() == SIN_SESION


class Escenario:
    """Cuentas, tarifas y datos de un vehículo dentro de la transacción de la prueba (se revierte)."""

    def __init__(self, client, connection):
        self.client, self.connection = client, connection
        for tipo, valor in TARIFAS.items():
            connection.execute(text(
                "INSERT INTO tarifa(tipo_vehiculo, valor_mensual) VALUES (:t, :v) "
                "ON CONFLICT (tipo_vehiculo) DO UPDATE SET valor_mensual = EXCLUDED.valor_mensual"),
                {"t": tipo, "v": valor})
        self.admin = crear_cuenta(connection, "ADMINISTRADOR")
        self.operador = crear_cuenta(connection, "OPERADOR")
        self.h_admin = iniciar_sesion(client, self.admin)
        self.h_operador = iniciar_sesion(client, self.operador)

    def vehiculo(self, tipo: str = "MOTO", con_cliente: bool = True) -> dict:
        marca = token_unico("P")
        cliente = None
        if con_cliente:
            cliente = self.connection.scalar(text(
                "INSERT INTO cliente(nombre, documento, telefono) VALUES (:n, :d, '300') RETURNING id"),
                {"n": f"Cliente {marca}", "d": f"D{marca}"})
        self.connection.execute(text(
            "INSERT INTO vehiculo(placa, color, modelo, marca, tipo, cliente_id) "
            "VALUES (:p, 'Rojo', 2020, 'X', :t, :c)"), {"p": marca, "t": tipo, "c": cliente})
        return {"placa": marca, "documento": f"D{marca}", "nombre": f"Cliente {marca}"}

    def pagar(self, placa: str, medio: str = "EFECTIVO", encabezados: dict | None = None):
        return self.client.post("/pagos", json={"placa": placa, "medio_pago": medio},
                                headers=encabezados or self.h_operador)

    def anular(self, pago_id: int, motivo: str = "Error de digitación", encabezados: dict | None = None):
        return self.client.post(f"/pagos/{pago_id}/anular", json={"motivo": motivo},
                                headers=encabezados or self.h_admin)

    def estado(self, placa: str) -> dict:
        respuesta = self.client.get("/pagos/estado", params={"q": placa}, headers=self.h_operador)
        assert respuesta.status_code == 200
        (item,) = respuesta.json()["items"]
        return item


@solo_postgres
def test_primer_pago_vigencia_desde_la_fecha_del_pago(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo("AUTOMOVIL")
        fijar_fecha(date(2026, 9, 1))
        respuesta = e.pagar(v["placa"], "TRANSFERENCIA")
        assert respuesta.status_code == 201, respuesta.text
        pago = respuesta.json()
        assert (pago["vigencia_desde"], pago["vigencia_hasta"]) == ("2026-09-01", "2026-10-01")
        assert pago["valor"] == 100000  # lo pone el servidor según la tarifa
        assert pago["medio_pago"] == "TRANSFERENCIA" and pago["estado"] == "REGISTRADO"
        assert pago["registrado_por"] == f"Operador {e.operador['usuario']}"
        guardado = connection.execute(text(
            "SELECT operador_id, valor, cliente_id IS NOT NULL AS con_cliente FROM pago WHERE id = :i"),
            {"i": pago["id"]}).one()
        assert guardado.operador_id == e.operador["operador_id"] and guardado.con_cliente


@solo_postgres
def test_el_pago_usa_la_fecha_de_bogota_y_guarda_una_copia_del_valor(monkeypatch):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo("MOTO")
        # 23:30 en Bogotá del 31 de agosto ya es 1 de septiembre en UTC: la fecha de corte es la de Bogotá.
        instante = datetime(2026, 8, 31, 23, 30, tzinfo=servicio_pago.ZONA_LOCAL)
        monkeypatch.setattr(servicio_pago, "ahora_utc", lambda: instante.astimezone(timezone.utc))
        pago = e.pagar(v["placa"]).json()
        assert pago["vigencia_desde"] == "2026-08-31"
        assert pago["fecha_pago"] == "2026-08-31T23:30:00-05:00"
        # Si la tarifa cambia, el pago ya registrado conserva su valor.
        connection.execute(text("UPDATE tarifa SET valor_mensual = 99999 WHERE tipo_vehiculo = 'MOTO'"))
        assert client.get(f"/pagos/{pago['id']}", headers=e.h_operador).json()["valor"] == 50000


@solo_postgres
def test_segundo_pago_suma_30_dias_desde_la_vigencia_anterior(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        primero = e.pagar(v["placa"]).json()
        fijar_fecha(date(2026, 10, 2))  # faltan 29 días: aún se puede pagar
        segundo = e.pagar(v["placa"])
        assert segundo.status_code == 201, segundo.text
        assert (segundo.json()["vigencia_desde"], segundo.json()["vigencia_hasta"]) == (
            primero["vigencia_hasta"], "2026-10-31")
        assert e.estado(v["placa"])["ultimo_pago_id"] == segundo.json()["id"]


@solo_postgres
def test_pago_tardio_cuenta_desde_la_fecha_de_corte_y_sigue_vencida(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        assert e.pagar(v["placa"]).status_code == 201
        fijar_fecha(date(2026, 12, 1))
        tardio = e.pagar(v["placa"])
        assert tardio.status_code == 201
        assert (tardio.json()["vigencia_desde"], tardio.json()["vigencia_hasta"]) == ("2026-10-01", "2026-10-31")
        assert e.estado(v["placa"])["estado"] == "VENCIDA"
        # Debe los periodos que le faltan: el siguiente pago continúa desde el 31 de octubre.
        otro = e.pagar(v["placa"])
        assert otro.status_code == 201
        assert (otro.json()["vigencia_desde"], otro.json()["vigencia_hasta"]) == ("2026-10-31", "2026-11-30")
        assert e.estado(v["placa"])["estado"] == "VENCIDA"


@solo_postgres
def test_pago_repetido_es_409(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        assert e.pagar(v["placa"]).status_code == 201
        repetido = e.pagar(v["placa"])
        assert repetido.status_code == 409
        assert repetido.json() == {"detail": "La mensualidad de este vehículo ya está pagada."}
        fijar_fecha(date(2026, 10, 1))  # el 1 de octubre la vigencia ya solo llega hoy: se puede pagar de nuevo
        assert e.pagar(v["placa"]).status_code == 201
        assert connection.scalar(text("SELECT count(*) FROM pago p JOIN vehiculo v ON v.id = p.vehiculo_id "
                                      "WHERE v.placa = :p"), {"p": v["placa"]}) == 2


@solo_postgres
def test_vehiculo_inexistente_y_vehiculo_sin_cliente(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        fijar_fecha(date(2026, 9, 1))
        inexistente = e.pagar(token_unico("NO"))
        assert (inexistente.status_code, inexistente.json()) == (404, {"detail": "Vehículo no encontrado."})
        sin_cliente = e.vehiculo(con_cliente=False)
        respuesta = e.pagar(sin_cliente["placa"])
        assert (respuesta.status_code, respuesta.json()) == (
            409, {"detail": "El vehículo no tiene un cliente asociado."})
        assert connection.scalar(text("SELECT count(*) FROM pago p JOIN vehiculo v ON v.id = p.vehiculo_id "
                                      "WHERE v.placa = :p"), {"p": sin_cliente["placa"]}) == 0


@solo_postgres
def test_placa_con_espacios_y_minusculas_se_normaliza(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        assert e.pagar(f" {v['placa'].lower()} ").status_code == 201


@solo_postgres
def test_estados_al_dia_vencida_y_sin_pagos(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        con_pago, sin_pagos, sin_cliente = e.vehiculo("CAMIONETA"), e.vehiculo(), e.vehiculo(con_cliente=False)
        fijar_fecha(date(2026, 9, 1))
        pago = e.pagar(con_pago["placa"]).json()

        item = e.estado(con_pago["placa"])
        assert item == {
            "placa": con_pago["placa"], "tipo": "CAMIONETA", "cliente_nombre": con_pago["nombre"],
            "cliente_documento": con_pago["documento"], "tarifa": 150000, "estado": "AL_DIA",
            "vigencia_hasta": "2026-10-01", "ultimo_pago_id": pago["id"],
        }
        fijar_fecha(date(2026, 10, 1))  # el último día de vigencia todavía está al día
        assert e.estado(con_pago["placa"])["estado"] == "AL_DIA"
        fijar_fecha(date(2026, 10, 2))
        assert e.estado(con_pago["placa"])["estado"] == "VENCIDA"

        nuevo = e.estado(sin_pagos["placa"])
        assert (nuevo["estado"], nuevo["vigencia_hasta"], nuevo["ultimo_pago_id"], nuevo["tarifa"]) == (
            "SIN_PAGOS", None, None, 50000)
        # Un vehículo sin cliente no aparece.
        vacio = client.get("/pagos/estado", params={"q": sin_cliente["placa"]}, headers=e.h_operador).json()
        assert vacio["items"] == [] and vacio["total"] == 0

        # Filtro por estado y paginación.
        por_estado = client.get("/pagos/estado", params={"estado": "VENCIDA", "q": con_pago["placa"]},
                                headers=e.h_operador).json()
        assert [i["placa"] for i in por_estado["items"]] == [con_pago["placa"]]
        assert client.get("/pagos/estado", params={"estado": "AL_DIA", "q": con_pago["placa"]},
                          headers=e.h_operador).json()["items"] == []
        assert client.get("/pagos/estado", params={"estado": "NADA"}, headers=e.h_operador).status_code == 422
        pagina = client.get("/pagos/estado", params={"limit": 1}, headers=e.h_operador).json()
        assert len(pagina["items"]) == 1 and pagina["total"] >= 2 and pagina["limit"] == 1


@solo_postgres
def test_comprobante(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo("AUTOMOVIL")
        fijar_fecha(date(2026, 9, 1))
        pago = e.pagar(v["placa"], "TARJETA").json()
        comprobante = client.get(f"/pagos/{pago['id']}", headers=e.h_operador)
        assert comprobante.status_code == 200
        assert comprobante.json() == {
            "id": pago["id"], "fecha_pago": "2026-09-01T12:00:00-05:00", "cliente_nombre": v["nombre"],
            "cliente_documento": v["documento"], "placa": v["placa"], "tipo": "AUTOMOVIL", "valor": 100000,
            "medio_pago": "TARJETA", "vigencia_desde": "2026-09-01", "vigencia_hasta": "2026-10-01",
            "registrado_por": f"Operador {e.operador['usuario']}", "estado": "REGISTRADO",
            "motivo_anulacion": None, "anulado_por": None, "anulado_en": None,
        }
        # También lo ve el administrador; y un número inexistente o inválido responde con claridad.
        assert client.get(f"/pagos/{pago['id']}", headers=e.h_admin).status_code == 200
        faltante = client.get("/pagos/9223372036854775807", headers=e.h_operador)
        assert (faltante.status_code, faltante.json()) == (404, {"detail": "Pago no encontrado."})
        assert client.get("/pagos/0", headers=e.h_operador).status_code == 422
        assert client.get("/pagos/abc", headers=e.h_operador).status_code == 422


@solo_postgres
def test_anular_el_ultimo_pago_devuelve_la_vigencia_anterior(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        primero = e.pagar(v["placa"]).json()
        fijar_fecha(date(2026, 10, 2))
        segundo = e.pagar(v["placa"]).json()
        assert e.estado(v["placa"])["vigencia_hasta"] == "2026-10-31"

        # Solo el último: el primero depende de él.
        no_ultimo = e.anular(primero["id"])
        assert (no_ultimo.status_code, no_ultimo.json()) == (
            409, {"detail": "Solo se puede anular el último pago del vehículo."})

        fijar_fecha(date(2026, 10, 3))
        anulado = e.anular(segundo["id"], "  Cobro duplicado  ")
        assert anulado.status_code == 200, anulado.text
        datos = anulado.json()
        assert datos["estado"] == "ANULADO" and datos["motivo_anulacion"] == "Cobro duplicado"
        assert datos["anulado_por"] == f"Operador {e.admin['usuario']}"
        assert datos["anulado_en"] == "2026-10-03T12:00:00-05:00"
        guardado = connection.execute(text(
            "SELECT anulado_por_operador_id FROM pago WHERE id = :i"), {"i": segundo["id"]}).scalar_one()
        assert guardado == e.admin["operador_id"]  # el pago no se borra, queda ANULADO

        # La vigencia vuelve a la del pago anterior.
        item = e.estado(v["placa"])
        assert (item["vigencia_hasta"], item["ultimo_pago_id"], item["estado"]) == (
            "2026-10-01", primero["id"], "VENCIDA")

        # Anular dos veces es 409.
        otra_vez = e.anular(segundo["id"])
        assert (otra_vez.status_code, otra_vez.json()) == (409, {"detail": "El pago ya está anulado."})

        # Ahora el primero es el último vigente; al anularlo no quedan pagos.
        assert e.anular(primero["id"]).status_code == 200
        item = e.estado(v["placa"])
        assert (item["estado"], item["vigencia_hasta"], item["ultimo_pago_id"]) == ("SIN_PAGOS", None, None)
        # Con todo anulado, un pago nuevo cuenta desde hoy.
        nuevo = e.pagar(v["placa"])
        assert nuevo.status_code == 201 and nuevo.json()["vigencia_desde"] == "2026-10-03"


@solo_postgres
def test_anular_motivo_vacio_o_ausente_es_422_y_pago_inexistente_404(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        pago = e.pagar(v["placa"]).json()
        for cuerpo in ({"motivo": ""}, {"motivo": "   \t"}, {}):
            respuesta = client.post(f"/pagos/{pago['id']}/anular", json=cuerpo, headers=e.h_admin)
            assert (respuesta.status_code, respuesta.json()) == (422, {"detail": "Escribe el motivo de la anulación."})
        assert client.post(f"/pagos/{pago['id']}/anular", json={"motivo": "x", "otro": 1},
                           headers=e.h_admin).status_code == 422
        assert client.get(f"/pagos/{pago['id']}", headers=e.h_admin).json()["estado"] == "REGISTRADO"
        faltante = e.anular(9223372036854775807)
        assert (faltante.status_code, faltante.json()) == (404, {"detail": "Pago no encontrado."})


@solo_postgres
def test_operador_no_puede_anular_y_si_registrar_y_consultar(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo()
        fijar_fecha(date(2026, 9, 1))
        pago = e.pagar(v["placa"], encabezados=e.h_operador).json()
        respuesta = e.anular(pago["id"], encabezados=e.h_operador)
        assert respuesta.status_code == 403
        assert client.get(f"/pagos/{pago['id']}", headers=e.h_operador).json()["estado"] == "REGISTRADO"
        assert client.get("/pagos", headers=e.h_operador).status_code == 200
        # El administrador también registra pagos.
        otro = e.vehiculo()
        assert e.pagar(otro["placa"], encabezados=e.h_admin).json()["registrado_por"] == (
            f"Operador {e.admin['usuario']}")


@solo_postgres
def test_listado_filtros_orden_y_paginacion(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        a, b = e.vehiculo(), e.vehiculo("CAMIONETA")
        fijar_fecha(date(2026, 9, 1))
        pago_a = e.pagar(a["placa"]).json()
        fijar_fecha(date(2026, 9, 5))
        pago_b = e.pagar(b["placa"], "TARJETA").json()
        fijar_fecha(date(2026, 9, 6))
        assert e.anular(pago_b["id"]).status_code == 200

        def listar(**filtros):
            respuesta = client.get("/pagos", params=filtros, headers=e.h_operador)
            assert respuesta.status_code == 200, respuesta.text
            return respuesta.json()

        todos = listar(desde="2026-09-01", hasta="2026-09-30")
        assert [p["id"] for p in todos["items"]] == [pago_b["id"], pago_a["id"]]  # el más reciente primero
        assert todos["total"] == 2 and todos["offset"] == 0 and todos["limit"] == 20
        assert [p["id"] for p in listar(q=a["placa"].lower())["items"]] == [pago_a["id"]]
        assert [p["id"] for p in listar(q=b["documento"])["items"]] == [pago_b["id"]]
        assert [p["id"] for p in listar(q=a["nombre"])["items"]] == [pago_a["id"]]
        assert [p["id"] for p in listar(q="%")["items"]] == []  # el comodín se escapa
        assert [p["id"] for p in listar(estado="ANULADO", desde="2026-09-01", hasta="2026-09-30")["items"]] == [pago_b["id"]]
        assert [p["id"] for p in listar(estado="REGISTRADO", q=b["placa"])["items"]] == []
        # La fecha de pago se compara en hora de Bogotá, con el día completo incluido.
        assert [p["id"] for p in listar(desde="2026-09-05", hasta="2026-09-05")["items"]] == [pago_b["id"]]
        assert listar(desde="2026-09-02", hasta="2026-09-04")["items"] == []
        pagina = listar(desde="2026-09-01", hasta="2026-09-30", limit=1, offset=1)
        assert [p["id"] for p in pagina["items"]] == [pago_a["id"]] and pagina["total"] == 2
        mala = client.get("/pagos", params={"desde": "2026-09-30", "hasta": "2026-09-01"}, headers=e.h_operador)
        assert mala.status_code == 422
        assert client.get("/pagos", params={"estado": "NADA"}, headers=e.h_operador).status_code == 422
        assert client.get("/pagos", params={"limit": 0}, headers=e.h_operador).status_code == 422


@solo_postgres
def test_sin_tarifa_configurada_es_409(fijar_fecha):
    with entorno_bd() as (client, connection):
        e = Escenario(client, connection)
        v = e.vehiculo("MOTO")
        connection.execute(text("DELETE FROM tarifa WHERE tipo_vehiculo = 'MOTO'"))
        fijar_fecha(date(2026, 9, 1))
        respuesta = e.pagar(v["placa"])
        assert (respuesta.status_code, respuesta.json()) == (
            409, {"detail": "No hay una tarifa configurada para este tipo de vehículo."})
