from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.auth import SoloAdministrador
from app.database import get_session
from app.schemas.celda import CeldaActualizar, CeldaCrear, CeldaRespuesta, CeldasPagina
from app.services import celda as service

# Listar y consultar: ambos roles. Crear, editar y eliminar: solo ADMINISTRADOR.
router = APIRouter(prefix="/celdas", tags=["Celdas"])
DatabaseSession = Annotated[Session, Depends(get_session)]
CellId = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post("", response_model=CeldaRespuesta, status_code=201, dependencies=[SoloAdministrador])
def create(data: CeldaCrear, session: DatabaseSession):
    return service.create_cell(session, data)


@router.get("", response_model=CeldasPagina)
def list_all(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.list_cells(session, offset, limit)


@router.get("/{id}", response_model=CeldaRespuesta)
def get_one(id: CellId, session: DatabaseSession):
    return service.get_cell(session, id)


@router.patch("/{id}", response_model=CeldaRespuesta, dependencies=[SoloAdministrador])
def update(id: CellId, data: CeldaActualizar, session: DatabaseSession):
    return service.update_cell(session, id, data)


@router.delete("/{id}", status_code=204, dependencies=[SoloAdministrador])
def delete(id: CellId, session: DatabaseSession) -> Response:
    service.delete_cell(session, id)
    return Response(status_code=204)

