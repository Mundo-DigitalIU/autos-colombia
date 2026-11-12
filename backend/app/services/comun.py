"""Utilidades compartidas por los servicios."""

from sqlalchemy import func
from sqlalchemy.orm import Session

MENSAJE_BASE = "No se pudo completar la operación con la base de datos."


def nueva_transaccion(session: Session):
    """Abre una transacción nueva; si una consulta anterior dejó una abierta, la cierra antes."""
    if session.in_transaction():
        session.commit()
    return session.begin()


def escapar_like(texto: str) -> str:
    """Evita que % y _ escritos por el usuario actúen como comodines."""
    return texto.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")


def contiene(columna, texto: str):
    """Condición: la columna contiene el texto, sin distinguir mayúsculas."""
    return columna.ilike(f"%{escapar_like(texto)}%", escape="\\")


def normalizar_sql(columna):
    """Recorta espacios y pasa a mayúsculas en SQL, igual que normalizar_tipo en Python."""
    return func.upper(func.regexp_replace(columna, "^[[:space:]]+|[[:space:]]+$", "", "g"))
