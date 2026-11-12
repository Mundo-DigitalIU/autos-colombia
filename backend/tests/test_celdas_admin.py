"""Etapa 5: administración de celdas, permisos y filtros del listado de estados."""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import get_engine
from app.main import app
from app.schemas.celda import CeldaActualizar, CeldaCrear
from utiles_bd import crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres, token_unico

SIN_SESION_FALSA = True
CODIGO_REPETIDO = "Ese código de celda ya existe."
CON_ESTANCIAS = "No se puede eliminar: esta celda ya tuvo entradas y salidas registradas."
TIPO_OCUPADA = "No puedes cambiar el tipo mientras la celda está ocupada."


def test_esquema_normaliza_codigo_y_valida_tipo():
    celda = CeldaCrear(codigo="  a-01 ", tipo=" MOTO ")
    assert (celda.codigo, celda.tipo) == ("A-01", "MOTO")
    for codigo in ("", "   ", None, 5):
        with pytest.raises(ValueError, match="Escribe el código de la celda."):
            CeldaCrear(codigo=codigo, tipo="MOTO")
    for tipo in ("Libre", "moto", "", None, "BICICLETA"):
        with pytest.raises(ValueError):
            CeldaCrear(codigo="A-01", tipo=tipo)
    assert CeldaActualizar(tipo="CAMIONETA").codigo is None
    for invalido in ({"codigo": None}, {"tipo": None}, {"tipo": "Otro"}, {"codigo": " "}, {"id": 1}):
        with pytest.raises(ValueError):
            CeldaActualizar(**invalido)


@pytest.mark.parametrize("metodo,ruta", [
    ("post", "/celdas"), ("get", "/celdas"), ("get", "/celdas/1"), ("patch", "/celdas/1"),
    ("delete", "/celdas/1"), ("get", "/estancias/celdas"),
])
def test_sin_sesion_es_401(metodo, ruta):
    with TestClient(app) as client:
        assert getattr(client, metodo)(ruta).status_code == 401


@solo_postgres
def test_crear_editar_y_eliminar_son_del_administrador_y_listar_de_ambos():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        creada = client.post("/celdas", json={"codigo": f"Z-{token_unico()}", "tipo": "MOTO"}, headers=admin).json()
        for respuesta in (client.post("/celdas", json={"codigo": "NUEVA-1", "tipo": "MOTO"}, headers=operador),
                          client.patch(f"/celdas/{creada['id']}", json={"tipo": "AUTOMOVIL"}, headers=operador),
                          client.delete(f"/celdas/{creada['id']}", headers=operador)):
            assert respuesta.status_code == 403
            assert respuesta.json() == {"detail": "No tienes permiso para entrar aquí."}
        assert client.get("/celdas", headers=operador).status_code == 200
        assert client.get(f"/celdas/{creada['id']}", headers=operador).json() == creada
        assert client.get("/estancias/celdas", headers=operador).status_code == 200
        assert connection.scalar(text("SELECT tipo FROM celda WHERE id = :i"), {"i": creada["id"]}) == "MOTO"


@solo_postgres
def test_crear_celda_valida_codigo_y_tipo():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        codigo = f"Y-{token_unico()}"
        creada = client.post("/celdas", json={"codigo": f"  {codigo.lower()} ", "tipo": " CAMIONETA "}, headers=admin)
        assert creada.status_code == 201
        assert creada.json()["codigo"] == codigo and creada.json()["tipo"] == "CAMIONETA"
        repetida = client.post("/celdas", json={"codigo": codigo.lower(), "tipo": "MOTO"}, headers=admin)
        assert repetida.status_code == 409 and repetida.json() == {"detail": CODIGO_REPETIDO}
        vacia = client.post("/celdas", json={"codigo": "   ", "tipo": "MOTO"}, headers=admin)
        assert vacia.status_code == 422
        assert any(e["msg"] == "Escribe el código de la celda." for e in vacia.json()["detail"])
        for invalido in ({"codigo": "A-9", "tipo": "Libre"}, {"codigo": "A-9", "tipo": "moto"}, {"codigo": "A-9"},
                         {"tipo": "MOTO"}, {"codigo": "A-9", "tipo": "MOTO", "id": 1}, {}):
            assert client.post("/celdas", json=invalido, headers=admin).status_code == 422


@solo_postgres
def test_editar_celda_con_sus_restricciones():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        cuenta = crear_cuenta(connection, "OPERADOR")
        sufijo = token_unico()
        celda = client.post("/celdas", json={"codigo": f"E1-{sufijo}", "tipo": "MOTO"}, headers=admin).json()
        otra = client.post("/celdas", json={"codigo": f"E2-{sufijo}", "tipo": "MOTO"}, headers=admin).json()
        ruta = f"/celdas/{celda['id']}"

        editada = client.patch(ruta, json={"codigo": f" e3-{sufijo.lower()} ", "tipo": "AUTOMOVIL"}, headers=admin)
        assert editada.status_code == 200
        assert editada.json() == {"id": celda["id"], "codigo": f"E3-{sufijo}", "tipo": "AUTOMOVIL"}
        # Reenviar su propio código no es un conflicto.
        assert client.patch(ruta, json={"codigo": f"E3-{sufijo}"}, headers=admin).status_code == 200
        choque = client.patch(ruta, json={"codigo": otra["codigo"].lower()}, headers=admin)
        assert choque.status_code == 409 and choque.json() == {"detail": CODIGO_REPETIDO}
        for invalido in ({"codigo": " "}, {"tipo": "Libre"}, {"tipo": None}, {"codigo": None}, {"id": 5}):
            assert client.patch(ruta, json=invalido, headers=admin).status_code == 422
        assert client.patch("/celdas/999999999", json={"tipo": "MOTO"}, headers=admin).status_code == 404

        # Ocupada: el código se puede cambiar, el tipo no (pero repetir el mismo tipo sí).
        vehiculo = connection.scalar(text(
            "INSERT INTO vehiculo(placa, color, modelo, marca, tipo) VALUES (:p, 'Rojo', 2020, 'X', 'AUTOMOVIL') "
            "RETURNING id"), {"p": f"V{sufijo}"})
        connection.execute(text("INSERT INTO estancia(vehiculo_id, celda_id, operador_entrada_id) "
                                "VALUES (:v, :c, :o)"),
                           {"v": vehiculo, "c": celda["id"], "o": cuenta["operador_id"]})
        ocupada = client.patch(ruta, json={"tipo": "MOTO"}, headers=admin)
        assert ocupada.status_code == 409 and ocupada.json() == {"detail": TIPO_OCUPADA}
        assert client.patch(ruta, json={"tipo": "AUTOMOVIL", "codigo": f"E4-{sufijo}"}, headers=admin).status_code == 200
        assert connection.scalar(text("SELECT tipo FROM celda WHERE id = :i"), {"i": celda["id"]}) == "AUTOMOVIL"
        # Al salir el vehículo, el tipo vuelve a poder cambiarse.
        connection.execute(text("UPDATE estancia SET salida = now(), operador_salida_id = :o WHERE celda_id = :c"),
                           {"c": celda["id"], "o": cuenta["operador_id"]})
        assert client.patch(ruta, json={"tipo": "MOTO"}, headers=admin).status_code == 200


@solo_postgres
def test_eliminar_celda_solo_sin_historial():
    with entorno_bd() as (client, connection):
        admin = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        cuenta = crear_cuenta(connection, "OPERADOR")
        sufijo = token_unico()
        usada = client.post("/celdas", json={"codigo": f"D1-{sufijo}", "tipo": "MOTO"}, headers=admin).json()
        libre = client.post("/celdas", json={"codigo": f"D2-{sufijo}", "tipo": "MOTO"}, headers=admin).json()
        vehiculo = connection.scalar(text(
            "INSERT INTO vehiculo(placa, color, modelo, marca, tipo) VALUES (:p, 'Rojo', 2020, 'X', 'MOTO') "
            "RETURNING id"), {"p": f"W{sufijo}"})
        # Una estancia ya cerrada también impide eliminar la celda, aunque esté libre.
        connection.execute(text(
            "INSERT INTO estancia(vehiculo_id, celda_id, operador_entrada_id, salida, operador_salida_id) "
            "VALUES (:v, :c, :o, now(), :o)"),
            {"v": vehiculo, "c": usada["id"], "o": cuenta["operador_id"]})
        bloqueada = client.delete(f"/celdas/{usada['id']}", headers=admin)
        assert bloqueada.status_code == 409 and bloqueada.json() == {"detail": CON_ESTANCIAS}
        assert client.get(f"/celdas/{usada['id']}", headers=admin).status_code == 200

        borrada = client.delete(f"/celdas/{libre['id']}", headers=admin)
        assert borrada.status_code == 204 and borrada.content == b""
        assert client.get(f"/celdas/{libre['id']}", headers=admin).status_code == 404
        assert client.delete(f"/celdas/{libre['id']}", headers=admin).status_code == 404
        assert client.delete("/celdas/0", headers=admin).status_code == 422


@solo_postgres
def test_listado_de_estados_con_filtros():
    with entorno_bd() as (client, connection):
        encabezados = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        cuenta = crear_cuenta(connection, "OPERADOR")
        sufijo = token_unico("F")
        ids = {}
        for nombre, tipo in (("A", "MOTO"), ("B", "MOTO"), ("C", "CAMIONETA")):
            ids[nombre] = connection.scalar(text("INSERT INTO celda(codigo, tipo) VALUES (:c, :t) RETURNING id"),
                                            {"c": f"{sufijo}-{nombre}", "t": tipo})
        vehiculo = connection.scalar(text(
            "INSERT INTO vehiculo(placa, color, modelo, marca, tipo) VALUES (:p, 'Rojo', 2020, 'X', 'MOTO') "
            "RETURNING id"), {"p": f"F{sufijo}"})
        connection.execute(text("INSERT INTO estancia(vehiculo_id, celda_id, operador_entrada_id) "
                                "VALUES (:v, :c, :o)"), {"v": vehiculo, "c": ids["A"], "o": cuenta["operador_id"]})

        def consultar(**parametros):
            respuesta = client.get("/estancias/celdas", params={"q": sufijo.lower(), "limit": 100, **parametros},
                                   headers=encabezados)
            assert respuesta.status_code == 200
            return respuesta.json()

        todas = consultar()
        assert set(todas) == {"items", "total", "disponibles", "ocupadas", "offset", "limit"}
        assert [i["codigo"] for i in todas["items"]] == [f"{sufijo}-{n}" for n in "ABC"]
        assert (todas["total"], todas["ocupadas"], todas["disponibles"]) == (3, 1, 2)
        assert set(todas["items"][0]) == {"id", "codigo", "tipo", "estado"}

        motos = consultar(tipo="MOTO")
        assert [i["codigo"][-1] for i in motos["items"]] == ["A", "B"] and motos["total"] == 2
        assert (motos["ocupadas"], motos["disponibles"]) == (1, 1)
        ocupadas = consultar(estado="OCUPADA")
        assert [i["codigo"][-1] for i in ocupadas["items"]] == ["A"] and ocupadas["total"] == 1
        # El estado acota la lista, no los contadores.
        assert (ocupadas["ocupadas"], ocupadas["disponibles"]) == (1, 2)
        libres = consultar(estado="DISPONIBLE", tipo="MOTO")
        assert [i["codigo"][-1] for i in libres["items"]] == ["B"] and libres["total"] == 1
        assert consultar(q=f"{sufijo.lower()}-c")["total"] == 1
        assert consultar(q="%")["total"] == 0
        # Sin filtros, los contadores siguen siendo los de siempre: abarcan todas las celdas.
        general = client.get("/estancias/celdas", params={"limit": 1}, headers=encabezados).json()
        assert general["total"] == general["disponibles"] + general["ocupadas"] and len(general["items"]) == 1
        for parametros in ({"tipo": "Libre"}, {"estado": "LIBRE"}, {"limit": 0}):
            assert client.get("/estancias/celdas", params=parametros, headers=encabezados).status_code == 422


@solo_postgres
def test_dos_solicitudes_simultaneas_con_el_mismo_codigo():
    """Usa dos conexiones reales (sin reversión exterior) y borra lo que crea."""
    codigo = token_unico("RACE")
    barrera = threading.Barrier(2)
    from app.auth import sesion_actual
    from conftest import crear_sesion
    app.dependency_overrides[sesion_actual] = lambda: crear_sesion()

    def crear() -> int:
        with TestClient(app) as client:
            barrera.wait(timeout=10)
            return client.post("/celdas", json={"codigo": codigo, "tipo": "MOTO"}).status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            estados = sorted(f.result(timeout=30) for f in [pool.submit(crear), pool.submit(crear)])
        assert estados == [201, 409]
        with get_engine().connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM celda WHERE codigo = :c"), {"c": codigo}) == 1
    finally:
        app.dependency_overrides.pop(sesion_actual, None)
        with get_engine().begin() as connection:
            connection.execute(text("DELETE FROM celda WHERE codigo = :c"), {"c": codigo})
