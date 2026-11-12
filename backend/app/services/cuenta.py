from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Operador, Usuario
from app.schemas.cuenta import CuentaCrear, CuentaRespuesta, CuentasPagina
from app.security import hashear_clave
from app.services.auth import SesionActual
from app.services.comun import MENSAJE_BASE, contiene, nueva_transaccion


class CuentaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def _respuesta(usuario: Usuario, operador: Operador) -> CuentaRespuesta:
    return CuentaRespuesta(id=usuario.id, usuario=usuario.nombre_usuario, rol=usuario.rol,
                           nombre=operador.nombre, telefono=operador.telefono, operador_id=operador.id)


def crear_cuenta(session: Session, data: CuentaCrear) -> CuentaRespuesta:
    clave_hash = hashear_clave(data.contrasena)
    try:
        # Una sola transacción: si el usuario ya existe no queda un operador huérfano.
        with nueva_transaccion(session):
            operador = Operador(nombre=data.nombre, telefono=data.telefono)
            session.add(operador)
            session.flush()
            usuario = Usuario(nombre_usuario=data.usuario, clave_hash=clave_hash, rol=data.rol,
                              operador_id=operador.id)
            session.add(usuario)
            session.flush()
            return _respuesta(usuario, operador)
    except IntegrityError as error:
        session.rollback()
        restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if getattr(error.orig, "sqlstate", None) == "23505" and restriccion == "uq_usuario_nombre_usuario":
            raise CuentaError(409, "Ese usuario ya existe.") from None
        if getattr(error.orig, "sqlstate", None) in {"23502", "23514"}:
            raise CuentaError(422, "Los datos incumplen las restricciones de la cuenta.") from None
        raise CuentaError(409, "La operación entra en conflicto con los datos existentes.") from None
    except SQLAlchemyError:
        session.rollback()
        raise CuentaError(503, MENSAJE_BASE) from None


def listar_cuentas(session: Session, q: str | None, offset: int, limit: int) -> CuentasPagina:
    filtros = []
    texto = (q or "").strip()
    if texto:
        filtros.append(or_(contiene(Operador.nombre, texto), contiene(Usuario.nombre_usuario, texto)))
    try:
        with nueva_transaccion(session):
            base = select(Usuario, Operador).join(Operador, Operador.id == Usuario.operador_id).where(*filtros)
            total = session.scalar(select(func.count()).select_from(base.subquery()))
            filas = session.execute(base.order_by(Usuario.id).offset(offset).limit(limit)).all()
            items = [_respuesta(usuario, operador) for usuario, operador in filas]
            return CuentasPagina(items=items, total=total, offset=offset, limit=limit)
    except SQLAlchemyError:
        session.rollback()
        raise CuentaError(503, MENSAJE_BASE) from None


def eliminar_cuenta(session: Session, cuenta_id: int, actual: SesionActual) -> None:
    """Borra solo el usuario (sus sesiones caen en cascada); el operador queda para el historial."""
    try:
        with nueva_transaccion(session):
            usuario = session.get(Usuario, cuenta_id)
            if usuario is None:
                raise CuentaError(404, "Cuenta no encontrada.")
            if usuario.id == actual.usuario_id:
                raise CuentaError(409, "No puedes eliminar tu propia cuenta.")
            session.delete(usuario)
    except SQLAlchemyError:
        session.rollback()
        raise CuentaError(503, MENSAJE_BASE) from None
