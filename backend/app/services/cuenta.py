from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Operador, Usuario
from app.schemas.cuenta import CuentaCrear, CuentaRespuesta, CuentasPagina
from app.security import hashear_clave
from app.services.auth import MENSAJE_BASE, SesionActual


class CuentaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def escapar_like(texto: str) -> str:
    """Evita que % y _ escritos por el usuario actúen como comodines."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _respuesta(usuario: Usuario, operador: Operador) -> CuentaRespuesta:
    return CuentaRespuesta(id=usuario.id, usuario=usuario.nombre_usuario, rol=usuario.rol,
                           nombre=operador.nombre, telefono=operador.telefono, operador_id=operador.id)


def _transaccion_nueva(session: Session):
    if session.in_transaction():
        session.commit()
    return session.begin()


def crear_cuenta(session: Session, data: CuentaCrear) -> CuentaRespuesta:
    clave_hash = hashear_clave(data.contrasena)
    try:
        # Una sola transacción: si el usuario ya existe no queda un operador huérfano.
        with _transaccion_nueva(session):
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
        patron = f"%{escapar_like(texto)}%"
        filtros.append(or_(Operador.nombre.ilike(patron, escape="\\"),
                           Usuario.nombre_usuario.ilike(patron, escape="\\")))
    try:
        with _transaccion_nueva(session):
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
        with _transaccion_nueva(session):
            usuario = session.get(Usuario, cuenta_id)
            if usuario is None:
                raise CuentaError(404, "Cuenta no encontrada.")
            if usuario.id == actual.usuario_id:
                raise CuentaError(409, "No puedes eliminar tu propia cuenta.")
            session.delete(usuario)
    except SQLAlchemyError:
        session.rollback()
        raise CuentaError(503, MENSAJE_BASE) from None
