"""Etapa 2: contraseñas, sesiones, 401 y 403. Estas pruebas usan la autenticación real."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.security import hash_de_relleno, hash_token, hashear_clave, nuevo_token, verificar_clave
from utiles_bd import CLAVE_PRUEBA, crear_cuenta, entorno_bd, iniciar_sesion, solo_postgres

SIN_SESION_FALSA = True
MENSAJE_401 = "Tu sesión terminó. Inicia sesión otra vez."
MENSAJE_403 = "No tienes permiso para entrar aquí."

RUTAS_PROTEGIDAS = [
    ("get", "/vehiculos"), ("get", "/celdas"), ("get", "/operadores"), ("get", "/estancias/dentro"),
    ("get", "/estancias/historial"), ("get", "/estancias/celdas"), ("get", "/estancias/vehiculo/ABC123"),
    ("post", "/auth/logout"),
]


def test_scrypt_usa_sal_aleatoria_y_verifica():
    primero, segundo = hashear_clave("secreto-1"), hashear_clave("secreto-1")
    assert primero != segundo and primero.startswith("scrypt$")
    assert "secreto-1" not in primero
    assert verificar_clave("secreto-1", primero) and verificar_clave("secreto-1", segundo)
    assert not verificar_clave("secreto-2", primero)
    for malformado in ("", "scrypt$x", "md5$1$2$3$aa$bb", "scrypt$16384$8$1$zz$zz"):
        assert not verificar_clave("secreto-1", malformado)
    assert verificar_clave("x", hash_de_relleno()) is False


def test_token_aleatorio_y_solo_se_guarda_su_sha256():
    token = nuevo_token()
    assert len(token) >= 43 and token != nuevo_token()
    digest = hash_token(token)
    assert len(digest) == 64 and digest != token
    assert digest == hash_token(token)


@pytest.mark.parametrize("cuerpo", [
    {}, {"usuario": "admin"}, {"contrasena": "x"}, {"usuario": "", "contrasena": "x"},
    {"usuario": "   ", "contrasena": "x"}, {"usuario": "admin", "contrasena": ""},
    {"usuario": "admin", "contrasena": "   "}, {"usuario": None, "contrasena": "x"},
    {"usuario": "admin", "contrasena": "x", "rol": "ADMINISTRADOR"},
])
def test_login_con_campos_invalidos_es_422(cuerpo):
    with TestClient(app) as client:
        assert client.post("/auth/login", json=cuerpo).status_code == 422


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_rutas_protegidas_sin_sesion_son_401(metodo, ruta):
    with TestClient(app) as client:
        respuesta = getattr(client, metodo)(ruta)
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": MENSAJE_401}


@pytest.mark.parametrize("encabezado", ["", "Bearer", "Basic abc", "Bearer   "])
def test_encabezado_ausente_o_mal_formado_es_401(encabezado):
    with TestClient(app) as client:
        respuesta = client.get("/estancias/dentro", headers={"Authorization": encabezado})
        assert respuesta.status_code == 401 and respuesta.json() == {"detail": MENSAJE_401}


def test_health_no_exige_sesion():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


@solo_postgres
def test_login_logout_y_vencimiento():
    with entorno_bd() as (client, connection):
        cuenta = crear_cuenta(connection, "ADMINISTRADOR")
        # El nombre de usuario se normaliza al iniciar sesión.
        respuesta = client.post("/auth/login", json={"usuario": f"  {cuenta['usuario'].upper()} ",
                                                     "contrasena": CLAVE_PRUEBA})
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert set(cuerpo) == {"token", "rol", "nombre", "expira"}
        assert cuerpo["rol"] == "ADMINISTRADOR" and cuerpo["nombre"] == f"Operador {cuenta['usuario']}"
        # Solo se guarda el SHA-256 del token y vence a las 8 horas.
        fila = connection.execute(text(
            "SELECT token_hash, expira - creada, revocada FROM sesion WHERE usuario_id = :u"),
            {"u": cuenta["usuario_id"]}).one()
        assert fila[0] == hash_token(cuerpo["token"]) and fila[0] != cuerpo["token"]
        assert fila[1].total_seconds() == pytest.approx(8 * 3600, abs=5) and fila[2] is None

        encabezados = {"Authorization": f"Bearer {cuerpo['token']}"}
        assert client.get("/estancias/dentro", headers=encabezados).status_code == 200
        assert client.post("/auth/logout", headers=encabezados).status_code == 200
        revocada = client.get("/estancias/dentro", headers=encabezados)
        assert revocada.status_code == 401 and revocada.json() == {"detail": MENSAJE_401}
        assert connection.scalar(text("SELECT revocada IS NOT NULL FROM sesion WHERE usuario_id = :u"),
                                 {"u": cuenta["usuario_id"]}) is True

        # Una sesión vencida deja de valer.
        encabezados = iniciar_sesion(client, cuenta)
        connection.execute(text("UPDATE sesion SET expira = now() - interval '1 second' "
                                "WHERE usuario_id = :u AND revocada IS NULL"), {"u": cuenta["usuario_id"]})
        vencida = client.get("/estancias/dentro", headers=encabezados)
        assert vencida.status_code == 401 and vencida.json() == {"detail": MENSAJE_401}
        assert client.get("/estancias/dentro", headers={"Authorization": "Bearer inventado"}).status_code == 401


@solo_postgres
def test_credenciales_incorrectas_dan_el_mismo_401():
    with entorno_bd() as (client, connection):
        cuenta = crear_cuenta(connection)
        mala = client.post("/auth/login", json={"usuario": cuenta["usuario"], "contrasena": "otra-clave-cualquiera"})
        inexistente = client.post("/auth/login", json={"usuario": "no-existe-nadie", "contrasena": CLAVE_PRUEBA})
        for respuesta in (mala, inexistente):
            assert respuesta.status_code == 401
            assert respuesta.json() == {"detail": "Usuario o contraseña incorrectos."}
        assert connection.scalar(text("SELECT count(*) FROM sesion WHERE usuario_id = :u"),
                                 {"u": cuenta["usuario_id"]}) == 0


@solo_postgres
def test_roles_los_operadores_son_solo_del_administrador():
    with entorno_bd() as (client, connection):
        administrador = iniciar_sesion(client, crear_cuenta(connection, "ADMINISTRADOR"))
        operador = iniciar_sesion(client, crear_cuenta(connection, "OPERADOR"))
        prohibida = client.get("/operadores", headers=operador)
        assert prohibida.status_code == 403 and prohibida.json() == {"detail": MENSAJE_403}
        assert client.post("/operadores", headers=operador,
                           json={"nombre": "X", "telefono": "1"}).status_code == 403
        assert client.get("/operadores", headers=administrador).status_code == 200
        # Las rutas de estancias admiten ambos roles.
        for encabezados in (administrador, operador):
            assert client.get("/estancias/celdas", headers=encabezados).status_code == 200
