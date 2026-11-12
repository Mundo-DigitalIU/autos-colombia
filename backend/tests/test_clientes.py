"""Etapa 4: clientes y sus vehículos."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.schemas.cliente import ClienteActualizar, ClienteCrear
from utiles_bd import crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres, token_unico

SIN_SESION_FALSA = True
DOC_REPETIDO = "Ya hay un cliente con ese documento."
PLACA_REPETIDA = "Esa placa ya está registrada."
CON_ESTANCIAS = "No se puede eliminar: sus vehículos ya tienen entradas y salidas registradas."


def vehiculo(placa: str, tipo: str = "AUTOMOVIL", **cambios) -> dict:
    datos = {"placa": placa, "tipo": tipo, "color": "Rojo", "marca": "Mazda", "modelo": 2020}
    datos.update(cambios)
    return datos


def cliente(sufijo: str | None = None, vehiculos: list | None = None, **cambios) -> dict:
    sufijo = sufijo or token_unico("C")
    datos = {"nombre": "Ana Pérez", "documento": f"DOC-{sufijo}", "telefono": "3001112233",
             "vehiculos": [] if vehiculos is None else vehiculos}
    datos.update(cambios)
    return datos


def test_esquema_normaliza_y_valida():
    datos = ClienteCrear(**cliente(nombre="  Ana ", documento=" 123 ", vehiculos=[vehiculo(" abc123 ")]))
    assert (datos.nombre, datos.documento, datos.vehiculos[0].placa) == ("Ana", "123", "ABC123")
    assert ClienteCrear(nombre="A", documento="1", telefono="2").vehiculos == []
    for invalido in (cliente(nombre=" "), cliente(documento=""), cliente(telefono=None),
                     cliente(vehiculos=[vehiculo("A1", tipo="BICICLETA")]),
                     cliente(vehiculos=[vehiculo("A1", modelo=0)]), cliente(extra=1),
                     cliente(vehiculos=[vehiculo("A1")] * 21)):
        with pytest.raises(ValueError):
            ClienteCrear(**invalido)
    assert ClienteActualizar(**cliente(vehiculos=[{**vehiculo("A1"), "id": 5}])).vehiculos[0].id == 5


@pytest.mark.parametrize("metodo,ruta", [
    ("post", "/clientes"), ("get", "/clientes"), ("get", "/clientes/1"), ("put", "/clientes/1"),
    ("delete", "/clientes/1"), ("delete", "/clientes/1/vehiculos/1"),
])
def test_sin_sesion_es_401(metodo, ruta):
    with TestClient(app) as client:
        assert getattr(client, metodo)(ruta).status_code == 401


@solo_postgres
def test_crear_consultar_y_buscar_clientes():
    with entorno_bd() as (client, connection):
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        sufijo = token_unico("C")
        placa = f"  {sufijo[-6:].lower()} "
        datos = cliente(sufijo, nombre="  Luis Gómez ", documento=f"  DOC-{sufijo}  ",
                        vehiculos=[vehiculo(placa), vehiculo(f"{sufijo[-6:]}M", "MOTO", marca="Honda")])
        creado = client.post("/clientes", json=datos, headers=operador)
        assert creado.status_code == 201
        cuerpo = creado.json()
        assert cuerpo["nombre"] == "Luis Gómez" and cuerpo["documento"] == f"DOC-{sufijo}"
        assert [v["placa"] for v in cuerpo["vehiculos"]] == [sufijo[-6:], f"{sufijo[-6:]}M"]
        assert connection.scalar(text("SELECT count(*) FROM vehiculo WHERE cliente_id = :i"),
                                 {"i": cuerpo["id"]}) == 2
        assert client.get(f"/clientes/{cuerpo['id']}", headers=operador).json() == cuerpo
        assert client.get("/clientes/999999999", headers=operador).status_code == 404

        # Búsqueda por documento, nombre o placa (sin distinguir mayúsculas), paginada.
        for q in (f"doc-{sufijo}", "luis gómez", sufijo[-6:].lower()):
            pagina = client.get("/clientes", params={"q": q}, headers=operador).json()
            assert [c["id"] for c in pagina["items"]] == [cuerpo["id"]] and pagina["total"] == 1
        assert client.get("/clientes", params={"q": "%"}, headers=operador).json()["total"] == 0
        todos = client.get("/clientes", params={"limit": 1}, headers=operador)
        assert todos.status_code == 200 and len(todos.json()["items"]) <= 1
        assert client.get("/clientes", params={"limit": 0}, headers=operador).status_code == 422

        # Un cliente sin vehículos también es válido.
        assert client.post("/clientes", json=cliente(), headers=operador).json()["vehiculos"] == []
        assert client.post("/clientes", json={"nombre": "Solo", "documento": token_unico("D"), "telefono": "1"},
                           headers=operador).status_code == 201


@solo_postgres
def test_crear_rechaza_datos_invalidos_y_repetidos_sin_dejar_nada():
    with entorno_bd() as (client, connection):
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        sufijo = token_unico("C")
        original = cliente(sufijo, vehiculos=[vehiculo(f"P{sufijo[-6:]}")])
        assert client.post("/clientes", json=original, headers=operador).status_code == 201
        conteos = lambda: (connection.scalar(text("SELECT count(*) FROM cliente")),
                           connection.scalar(text("SELECT count(*) FROM vehiculo")))
        antes = conteos()

        repetido = client.post("/clientes", json=cliente(sufijo, vehiculos=[vehiculo(f"Q{sufijo[-6:]}")]),
                               headers=operador)
        assert repetido.status_code == 409 and repetido.json() == {"detail": DOC_REPETIDO}
        placa = client.post("/clientes", json=cliente(vehiculos=[vehiculo(f"  p{sufijo[-6:]}")]), headers=operador)
        assert placa.status_code == 409 and placa.json() == {"detail": PLACA_REPETIDA}
        # La misma placa dos veces en la solicitud también revierte todo, incluido el cliente.
        doble = client.post("/clientes", json=cliente(vehiculos=[vehiculo("DUP999"), vehiculo("dup999")]),
                            headers=operador)
        assert doble.status_code == 409 and doble.json() == {"detail": PLACA_REPETIDA}
        assert conteos() == antes
        for invalido in (cliente(nombre=" "), cliente(vehiculos=[vehiculo("Z1", tipo="BICICLETA")]), {}):
            assert client.post("/clientes", json=invalido, headers=operador).status_code == 422
        assert conteos() == antes


@solo_postgres
def test_editar_cliente_y_sus_vehiculos_es_del_administrador():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        sufijo = token_unico("C")
        creado = client.post("/clientes", json=cliente(sufijo, vehiculos=[vehiculo(f"E{sufijo[-6:]}")]),
                             headers=admin).json()
        propio = creado["vehiculos"][0]
        ruta = f"/clientes/{creado['id']}"
        cambio = cliente(sufijo, nombre="Nombre Nuevo", telefono="3999999999",
                         vehiculos=[{**vehiculo(propio["placa"], color="Azul"), "id": propio["id"]},
                                    vehiculo(f"N{sufijo[-6:]}", "MOTO")])
        prohibido = client.put(ruta, json=cambio, headers=operador)
        assert prohibido.status_code == 403
        assert prohibido.json() == {"detail": "No tienes permiso para entrar aquí."}

        editado = client.put(ruta, json=cambio, headers=admin)
        assert editado.status_code == 200
        cuerpo = editado.json()
        assert cuerpo["nombre"] == "Nombre Nuevo" and cuerpo["telefono"] == "3999999999"
        assert [(v["id"] == propio["id"], v["color"]) for v in cuerpo["vehiculos"]] == [(True, "Azul"), (False, "Rojo")]

        # Un vehículo de otro cliente no se puede editar por esta ruta.
        otro = client.post("/clientes", json=cliente(vehiculos=[vehiculo(f"O{sufijo[-6:]}")]), headers=admin).json()
        ajeno = cliente(sufijo, vehiculos=[{**vehiculo(f"O{sufijo[-6:]}"), "id": otro["vehiculos"][0]["id"]}])
        assert client.put(ruta, json=ajeno, headers=admin).status_code == 404
        assert client.put("/clientes/999999999", json=cambio, headers=admin).status_code == 404

        # Mismos 409 que al crear, y sin cambios parciales.
        doc_otro = client.put(ruta, json=cliente(sufijo, documento=otro["documento"]), headers=admin)
        assert doc_otro.status_code == 409 and doc_otro.json() == {"detail": DOC_REPETIDO}
        placa_otro = client.put(ruta, json=cliente(sufijo, nombre="Otro", vehiculos=[vehiculo(f"O{sufijo[-6:]}")]),
                                headers=admin)
        assert placa_otro.status_code == 409 and placa_otro.json() == {"detail": PLACA_REPETIDA}
        assert client.get(ruta, headers=admin).json()["nombre"] == "Nombre Nuevo"
        assert client.put(ruta, json=cliente(sufijo, nombre=" "), headers=admin).status_code == 422


@solo_postgres
def test_eliminar_cliente_y_vehiculos_respeta_el_historial():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        operador_cuenta = crear_cuenta(connection, "OPERADOR")
        operador = iniciar_sesion(client, operador_cuenta)
        sufijo = token_unico("C")
        con_historial = client.post("/clientes", json=cliente(sufijo, vehiculos=[
            vehiculo(f"H{sufijo[-6:]}"), vehiculo(f"I{sufijo[-6:]}")]), headers=admin).json()
        sin_historial = client.post("/clientes", json=cliente(vehiculos=[vehiculo(f"S{sufijo[-6:]}"),
                                                                         vehiculo(f"T{sufijo[-6:]}")]),
                                    headers=admin).json()
        celda = connection.scalar(text("INSERT INTO celda(codigo, tipo) VALUES (:c, 'AUTOMOVIL') RETURNING id"),
                                  {"c": sufijo})
        connection.execute(text(
            "INSERT INTO estancia(vehiculo_id, celda_id, operador_entrada_id) VALUES (:v, :c, :o)"),
            {"v": con_historial["vehiculos"][0]["id"], "c": celda, "o": operador_cuenta["operador_id"]})

        # Solo el ADMINISTRADOR puede eliminar.
        for ruta in (f"/clientes/{sin_historial['id']}",
                     f"/clientes/{sin_historial['id']}/vehiculos/{sin_historial['vehiculos'][0]['id']}"):
            assert client.delete(ruta, headers=operador).status_code == 403

        # Con estancias (aunque solo un vehículo las tenga) no se borra nada.
        bloqueado = client.delete(f"/clientes/{con_historial['id']}", headers=admin)
        assert bloqueado.status_code == 409 and bloqueado.json() == {"detail": CON_ESTANCIAS}
        bloqueado = client.delete(
            f"/clientes/{con_historial['id']}/vehiculos/{con_historial['vehiculos'][0]['id']}", headers=admin)
        assert bloqueado.status_code == 409 and bloqueado.json() == {"detail": CON_ESTANCIAS}
        assert len(client.get(f"/clientes/{con_historial['id']}", headers=admin).json()["vehiculos"]) == 2
        # El vehículo sin estancias de ese mismo cliente sí se puede quitar.
        libre = con_historial["vehiculos"][1]["id"]
        assert client.delete(f"/clientes/{con_historial['id']}/vehiculos/{libre}", headers=admin).status_code == 204

        # Sin estancias: se borran el cliente y todos sus vehículos.
        assert client.delete(f"/clientes/{sin_historial['id']}/vehiculos/999999999",
                             headers=admin).status_code == 404
        # El vehículo debe pertenecer a ese cliente.
        ajeno = sin_historial["vehiculos"][0]["id"]
        assert client.delete(f"/clientes/{con_historial['id']}/vehiculos/{ajeno}", headers=admin).status_code == 404
        assert client.delete(f"/clientes/{sin_historial['id']}", headers=admin).status_code == 204
        assert client.get(f"/clientes/{sin_historial['id']}", headers=admin).status_code == 404
        assert connection.scalar(text("SELECT count(*) FROM vehiculo WHERE id = ANY(:ids)"),
                                 {"ids": [v["id"] for v in sin_historial["vehiculos"]]}) == 0
        assert client.delete(f"/clientes/{sin_historial['id']}", headers=admin).status_code == 404
        assert client.delete("/clientes/999999999/vehiculos/1", headers=admin).status_code == 404
