"""Sesión simulada para las pruebas que no verifican la autenticación.

Casi todas las pruebas ejercitan rutas que ahora exigen sesión. Para no repetir el
inicio de sesión, se sustituye la dependencia `sesion_actual` por una sesión de
ADMINISTRADOR. Un módulo de pruebas que sí necesita la autenticación real define
`SIN_SESION_FALSA = True`. La fixture `fijar_sesion` cambia rol u operador; el
encabezado `X-Operador-Prueba` elige el operador de una sola petición.
"""
import pytest
from fastapi import Request

from app.auth import sesion_actual
from app.main import app
from app.services.auth import SesionActual


def crear_sesion(rol: str = "ADMINISTRADOR", operador_id: int = 1, usuario_id: int = 1) -> SesionActual:
    return SesionActual(
        sesion_id=1, usuario_id=usuario_id, nombre_usuario="prueba", rol=rol,
        operador_id=operador_id, nombre="Usuario de prueba",
    )


@pytest.fixture(autouse=True)
def sesion_simulada(request):
    if getattr(request.module, "SIN_SESION_FALSA", False):
        yield
        return
    def simulada(peticion: Request) -> SesionActual:
        # El encabezado X-Operador-Prueba permite a una misma prueba actuar como operadores distintos.
        operador = peticion.headers.get("x-operador-prueba")
        return crear_sesion(operador_id=int(operador) if operador else 1)

    app.dependency_overrides[sesion_actual] = simulada
    yield
    app.dependency_overrides.pop(sesion_actual, None)


@pytest.fixture
def fijar_sesion():
    """Devuelve una función que reemplaza la sesión simulada del momento."""
    def fijar(rol: str = "ADMINISTRADOR", operador_id: int = 1, usuario_id: int = 1) -> SesionActual:
        sesion = crear_sesion(rol, operador_id, usuario_id)
        app.dependency_overrides[sesion_actual] = lambda: sesion
        return sesion
    return fijar
