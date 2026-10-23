from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.estancia import (
    EntradaCrear, SalidaCrear, EstanciaRespuesta, EstadoVehiculoRespuesta, HistorialPagina,
    VehiculosDentroPagina,
)
from app.schemas.vehiculo import Placa
from app.services.estancia import ServicioEstancia

router = APIRouter(prefix="/estancias", tags=["Estancias"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/entrada", response_model=EstanciaRespuesta, status_code=201)
def entrada(data: EntradaCrear, session: DatabaseSession) -> EstanciaRespuesta:
    return ServicioEstancia(session).entrada(data)


@router.post("/salida", response_model=EstanciaRespuesta)
def salida(data: SalidaCrear, session: DatabaseSession) -> EstanciaRespuesta:
    return ServicioEstancia(session).salida(data)


@router.get("/dentro", response_model=VehiculosDentroPagina)
def dentro(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VehiculosDentroPagina:
    return ServicioEstancia(session).dentro(offset, limit)


@router.get("/historial", response_model=HistorialPagina)
def historial(
    session: DatabaseSession,
    placa: Annotated[str | None, Query(max_length=50)] = None,
    desde: date | None = None,
    hasta: date | None = None,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HistorialPagina:
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(status_code=422, detail="La fecha desde no puede ser posterior a la fecha hasta.")
    return ServicioEstancia(session).historial(placa, desde, hasta, offset, limit)


@router.get("/vehiculo/{placa}", response_model=EstadoVehiculoRespuesta)
def consultar(placa: Placa, session: DatabaseSession) -> EstadoVehiculoRespuesta:
    return ServicioEstancia(session).consultar(placa)
