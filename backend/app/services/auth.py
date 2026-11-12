from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Operador, Sesion, Usuario
from app.schemas.auth import LoginCrear, LoginRespuesta
from app.services.comun import MENSAJE_BASE, nueva_transaccion
from app.security import hash_de_relleno, hash_token, nuevo_token, verificar_clave

DURACION_SESION = timedelta(hours=8)
MENSAJE_LOGIN = "Usuario o contraseña incorrectos."
MENSAJE_SESION = "Tu sesión terminó. Inicia sesión otra vez."
MENSAJE_PERMISO = "No tienes permiso para entrar aquí."


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class SesionActual:
    """Datos de la sesión activa, sin objetos ORM para que sigan válidos tras el commit."""
    sesion_id: int
    usuario_id: int
    nombre_usuario: str
    rol: str
    operador_id: int
    nombre: str


def iniciar_sesion(session: Session, data: LoginCrear) -> LoginRespuesta:
    nombre_usuario = data.usuario.strip().lower()
    try:
        with nueva_transaccion(session):
            fila = session.execute(
                select(Usuario, Operador.nombre).join(Operador, Operador.id == Usuario.operador_id)
                .where(Usuario.nombre_usuario == nombre_usuario)
            ).first()
            # Se verifica siempre una contraseña para que ambos fallos tarden parecido.
            clave_hash = fila[0].clave_hash if fila is not None else hash_de_relleno()
            correcta = verificar_clave(data.contrasena, clave_hash)
            if fila is None or not correcta:
                raise AuthError(401, MENSAJE_LOGIN)
            usuario, nombre = fila
            token = nuevo_token()
            expira = datetime.now(timezone.utc) + DURACION_SESION
            session.add(Sesion(usuario_id=usuario.id, token_hash=hash_token(token), expira=expira))
            return LoginRespuesta(token=token, rol=usuario.rol, nombre=nombre, expira=expira)
    except SQLAlchemyError:
        session.rollback()
        raise AuthError(503, MENSAJE_BASE) from None


def sesion_por_token(session: Session, token: str | None) -> SesionActual:
    """Devuelve la sesión vigente o lanza 401; termina su propia transacción."""
    if not token:
        raise AuthError(401, MENSAJE_SESION)
    try:
        with nueva_transaccion(session):
            fila = session.execute(
                select(Sesion, Usuario, Operador.nombre)
                .join(Usuario, Usuario.id == Sesion.usuario_id)
                .join(Operador, Operador.id == Usuario.operador_id)
                .where(Sesion.token_hash == hash_token(token))
            ).first()
            if fila is None:
                raise AuthError(401, MENSAJE_SESION)
            sesion, usuario, nombre = fila
            if sesion.revocada is not None or sesion.expira <= datetime.now(timezone.utc):
                raise AuthError(401, MENSAJE_SESION)
            return SesionActual(sesion.id, usuario.id, usuario.nombre_usuario, usuario.rol,
                                usuario.operador_id, nombre)
    except SQLAlchemyError:
        session.rollback()
        raise AuthError(503, MENSAJE_BASE) from None


def cerrar_sesion(session: Session, sesion_id: int) -> None:
    try:
        with nueva_transaccion(session):
            sesion = session.get(Sesion, sesion_id)
            if sesion is not None and sesion.revocada is None:
                sesion.revocada = datetime.now(timezone.utc)
    except SQLAlchemyError:
        session.rollback()
        raise AuthError(503, MENSAJE_BASE) from None
