"""Etapa 3: cuentas (solo ADMINISTRADOR)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.schemas.cuenta import CuentaCrear
from utiles_bd import CLAVE_PRUEBA, crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres, token_unico

SIN_SESION_FALSA = True


def cuerpo(**cambios) -> dict:
    datos = {"nombre": "Ana Pérez", "telefono": "3001112233", "usuario": token_unico("u"),
             "contrasena": CLAVE_PRUEBA, "rol": "OPERADOR"}
    datos.update(cambios)
    return datos


def test_esquema_normaliza_y_valida():
    cuenta = CuentaCrear(**cuerpo(nombre="  Ana ", usuario="  AnaP "))
    assert cuenta.nombre == "Ana" and cuenta.usuario == "anap"
    for invalido in (cuerpo(rol="JEFE"), cuerpo(rol=None), cuerpo(contrasena="corta"), cuerpo(contrasena=" " * 10),
                     cuerpo(usuario="  "), cuerpo(nombre=""), cuerpo(telefono=" "), cuerpo(extra=1)):
        with pytest.raises(ValueError):
            CuentaCrear(**invalido)


@pytest.mark.parametrize("metodo,ruta", [("post", "/cuentas"), ("get", "/cuentas"), ("delete", "/cuentas/1")])
def test_sin_sesion_es_401(metodo, ruta):
    with TestClient(app) as client:
        assert getattr(client, metodo)(ruta).status_code == 401


@solo_postgres
def test_solo_el_administrador_gestiona_cuentas():
    with entorno_bd() as (client, connection):
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        antes = connection.scalar(text("SELECT count(*) FROM operador"))
        for respuesta in (client.post("/cuentas", json=cuerpo(), headers=operador),
                          client.get("/cuentas", headers=operador),
                          client.delete("/cuentas/1", headers=operador)):
            assert respuesta.status_code == 403
            assert respuesta.json() == {"detail": "No tienes permiso para entrar aquí."}
        assert connection.scalar(text("SELECT count(*) FROM operador")) == antes


@solo_postgres
def test_crear_listar_y_eliminar_cuentas():
    with entorno_bd() as (client, connection):
        admin = crear_cuenta(connection, "ADMINISTRADOR")
        encabezados = iniciar_sesion(client, admin)
        datos = cuerpo(usuario=f"  {token_unico('Nuevo')}  ", nombre="  Carla Ruiz ")
        creada = client.post("/cuentas", json=datos, headers=encabezados)
        assert creada.status_code == 201
        item = creada.json()
        assert set(item) == {"id", "usuario", "rol", "nombre", "telefono", "operador_id"}
        assert item["usuario"] == datos["usuario"].strip().lower() and item["nombre"] == "Carla Ruiz"
        assert "contrasena" not in creada.text and "hash" not in creada.text and "scrypt" not in creada.text
        # Operador y usuario quedaron vinculados y la contraseña guardada es un hash.
        fila = connection.execute(text(
            "SELECT u.clave_hash, u.operador_id, o.nombre FROM usuario u JOIN operador o ON o.id = u.operador_id "
            "WHERE u.id = :i"), {"i": item["id"]}).one()
        assert fila[1] == item["operador_id"] and fila[2] == "Carla Ruiz"
        assert fila[0].startswith("scrypt$") and CLAVE_PRUEBA not in fila[0]
        # La cuenta nueva puede iniciar sesión.
        assert client.post("/auth/login", json={"usuario": item["usuario"],
                                                 "contrasena": CLAVE_PRUEBA}).status_code == 200

        # Búsqueda por nombre o usuario, con paginación.
        por_nombre = client.get("/cuentas", params={"q": "carla ruiz"}, headers=encabezados).json()
        assert por_nombre["total"] == 1 and por_nombre["items"][0]["id"] == item["id"]
        por_usuario = client.get("/cuentas", params={"q": item["usuario"][:8].upper()}, headers=encabezados).json()
        assert item["id"] in [c["id"] for c in por_usuario["items"]]
        assert client.get("/cuentas", params={"q": "%"}, headers=encabezados).json()["total"] == 0
        pagina = client.get("/cuentas", params={"limit": 1, "offset": 0}, headers=encabezados).json()
        assert len(pagina["items"]) == 1 and pagina["total"] >= 2 and pagina["limit"] == 1
        for parametros in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
            assert client.get("/cuentas", params=parametros, headers=encabezados).status_code == 422

        # Eliminar borra el usuario y sus sesiones, pero el operador queda.
        assert client.delete(f"/cuentas/{item['id']}", headers=encabezados).status_code == 204
        assert connection.scalar(text("SELECT count(*) FROM usuario WHERE id = :i"), {"i": item["id"]}) == 0
        assert connection.scalar(text("SELECT count(*) FROM sesion WHERE usuario_id = :i"), {"i": item["id"]}) == 0
        assert connection.scalar(text("SELECT count(*) FROM operador WHERE id = :i"),
                                 {"i": item["operador_id"]}) == 1
        inexistente = client.delete(f"/cuentas/{item['id']}", headers=encabezados)
        assert inexistente.status_code == 404
        assert client.delete("/cuentas/0", headers=encabezados).status_code == 422


@solo_postgres
def test_usuario_repetido_no_deja_operador_huerfano():
    with entorno_bd() as (client, connection):
        encabezados = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        datos = cuerpo()
        assert client.post("/cuentas", json=datos, headers=encabezados).status_code == 201
        operadores = connection.scalar(text("SELECT count(*) FROM operador"))
        repetido = client.post("/cuentas", json={**datos, "usuario": datos["usuario"].lower(), "nombre": "Otra"},
                               headers=encabezados)
        assert repetido.status_code == 409 and repetido.json() == {"detail": "Ese usuario ya existe."}
        assert connection.scalar(text("SELECT count(*) FROM operador")) == operadores
        assert client.post("/cuentas", json=cuerpo(rol="JEFE"), headers=encabezados).status_code == 422
        assert client.post("/cuentas", json=cuerpo(contrasena=""), headers=encabezados).status_code == 422
        assert connection.scalar(text("SELECT count(*) FROM operador")) == operadores


@solo_postgres
def test_no_puedes_eliminar_tu_propia_cuenta():
    with entorno_bd() as (client, connection):
        admin = crear_cuenta(connection, "ADMINISTRADOR")
        encabezados = iniciar_sesion(client, admin)
        propia = client.delete(f"/cuentas/{admin['usuario_id']}", headers=encabezados)
        assert propia.status_code == 409
        assert propia.json() == {"detail": "No puedes eliminar tu propia cuenta."}
        assert connection.scalar(text("SELECT count(*) FROM usuario WHERE id = :i"),
                                 {"i": admin["usuario_id"]}) == 1
