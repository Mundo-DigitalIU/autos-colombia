from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.auth import SesionDeUsuario, SoloAdministrador
from app.database import get_session
from app.schemas.pago import EstadosMensualidadPagina, PagoAnular, PagoCrear, PagoRespuesta, PagosPagina
from app.services.pago import ServicioPago

router = APIRouter(prefix="/pagos", tags=["Pagos"])
DatabaseSession = Annotated[Session, Depends(get_session)]
IdPago = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post("", response_model=PagoRespuesta, status_code=201)
def registrar(data: PagoCrear, session: DatabaseSession, actual: SesionDeUsuario) -> PagoRespuesta:
    return ServicioPago(session).registrar(data, actual.operador_id)


@router.get("", response_model=PagosPagina)
def listar(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=50)] = None,
    estado: Literal["REGISTRADO", "ANULADO"] | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PagosPagina:
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(status_code=422, detail="La fecha desde no puede ser posterior a la fecha hasta.")
    return ServicioPago(session).listar(q, estado, desde, hasta, offset, limit)


# Debe ir antes de /{id}: si no, "estado" se interpretaría como un número de pago.
@router.get("/estado", response_model=EstadosMensualidadPagina)
def estados(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=50)] = None,
    estado: Literal["AL_DIA", "VENCIDA", "SIN_PAGOS"] | None = None,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EstadosMensualidadPagina:
    return ServicioPago(session).estados(q, estado, offset, limit)


@router.get("/{pago_id}", response_model=PagoRespuesta)
def comprobante(pago_id: IdPago, session: DatabaseSession) -> PagoRespuesta:
    return ServicioPago(session).obtener(pago_id)


@router.post("/{pago_id}/anular", response_model=PagoRespuesta, dependencies=[SoloAdministrador])
def anular(pago_id: IdPago, data: PagoAnular, session: DatabaseSession, actual: SesionDeUsuario) -> PagoRespuesta:
    return ServicioPago(session).anular(pago_id, data, actual.operador_id)
