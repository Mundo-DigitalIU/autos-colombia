from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.auth import SesionDeUsuario
from app.database import get_session
from app.schemas.cuenta import CuentaCrear, CuentaRespuesta, CuentasPagina
from app.services import cuenta as service

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])
DatabaseSession = Annotated[Session, Depends(get_session)]
CuentaId = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post("", response_model=CuentaRespuesta, status_code=201)
def crear(data: CuentaCrear, session: DatabaseSession) -> CuentaRespuesta:
    return service.crear_cuenta(session, data)


@router.get("", response_model=CuentasPagina)
def listar(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CuentasPagina:
    return service.listar_cuentas(session, q, offset, limit)


@router.delete("/{id}", status_code=204)
def eliminar(id: CuentaId, session: DatabaseSession, actual: SesionDeUsuario) -> Response:
    service.eliminar_cuenta(session, id, actual)
    return Response(status_code=204)
