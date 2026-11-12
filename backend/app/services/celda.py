from functools import wraps

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Celda, Estancia
from app.schemas.celda import CeldaActualizar, CeldaCrear
from app.services.comun import normalizar_sql

MENSAJE_CODIGO_REPETIDO = "Ese código de celda ya existe."
MENSAJE_CON_ESTANCIAS = "No se puede eliminar: esta celda ya tuvo entradas y salidas registradas."
MENSAJE_TIPO_OCUPADA = "No puedes cambiar el tipo mientras la celda está ocupada."


class CeldaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def database_operation(operation):
    """Centraliza rollback y mensajes públicos sin detalles del driver."""
    @wraps(operation)
    def wrapped(session: Session, *args, **kwargs):
        try:
            return operation(session, *args, **kwargs)
        except IntegrityError as error:
            session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505" and constraint == "uq_celda_codigo":
                raise CeldaError(409, MENSAJE_CODIGO_REPETIDO) from None
            # 23001 es restrict_violation (ON DELETE RESTRICT); 23503, foreign_key_violation.
            if code in {"23001", "23503"}:
                raise CeldaError(409, MENSAJE_CON_ESTANCIAS) from None
            if code in {"23502", "23514"}:
                raise CeldaError(422, "Los datos incumplen las restricciones de la celda.") from None
            raise CeldaError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            session.rollback()
            raise CeldaError(503, "No se pudo completar la operación con la base de datos.") from None
    return wrapped


def find_cell(session: Session, cell_id: int, lock: bool = False) -> Celda:
    query = select(Celda).where(Celda.id == cell_id)
    if lock:
        query = query.with_for_update()
    cell = session.scalar(query)
    if cell is None:
        raise CeldaError(404, "Celda no encontrada.")
    return cell


@database_operation
def create_cell(session: Session, data: CeldaCrear) -> Celda:
    # La restricción única decide cuando dos solicitudes crean el mismo código a la vez.
    cell = Celda(**data.model_dump())
    session.add(cell)
    session.commit()
    session.refresh(cell)
    return cell


@database_operation
def list_cells(session: Session, offset: int, limit: int) -> dict:
    total = session.scalar(select(func.count()).select_from(Celda))
    items = list(session.scalars(select(Celda).order_by(Celda.id).offset(offset).limit(limit)))
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@database_operation
def get_cell(session: Session, cell_id: int) -> Celda:
    return find_cell(session, cell_id)


@database_operation
def update_cell(session: Session, cell_id: int, data: CeldaActualizar) -> Celda:
    # Bloquea la fila para que dos ediciones simultáneas de la misma celda se serialicen.
    cell = find_cell(session, cell_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    nuevo_tipo = changes.get("tipo")
    if nuevo_tipo is not None and nuevo_tipo.strip().upper() != cell.tipo.strip().upper():
        ocupada = session.scalar(select(exists().where(Estancia.celda_id == cell.id, Estancia.salida.is_(None))))
        if ocupada:
            session.rollback()
            raise CeldaError(409, MENSAJE_TIPO_OCUPADA)
    for key, value in changes.items():
        setattr(cell, key, value)
    session.commit()
    session.refresh(cell)
    return cell


@database_operation
def delete_cell(session: Session, cell_id: int) -> None:
    cell = find_cell(session, cell_id, lock=True)
    # Cualquier estancia, abierta o cerrada, forma parte del historial.
    if session.scalar(select(exists().where(Estancia.celda_id == cell.id))):
        session.rollback()
        raise CeldaError(409, MENSAJE_CON_ESTANCIAS)
    session.delete(cell)
    session.commit()
