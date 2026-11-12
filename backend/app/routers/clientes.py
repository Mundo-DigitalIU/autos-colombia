from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.auth import SoloAdministrador
from app.database import get_session
from app.schemas.cliente import ClienteActualizar, ClienteCrear, ClienteRespuesta, ClientesPagina
from app.services.cliente import ServicioCliente

# Ambos roles pueden registrar y consultar; modificar y eliminar es del ADMINISTRADOR.
router = APIRouter(prefix="/clientes", tags=["Clientes"])
DatabaseSession = Annotated[Session, Depends(get_session)]
Identificador = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post("", response_model=ClienteRespuesta, status_code=201)
def crear(data: ClienteCrear, session: DatabaseSession) -> ClienteRespuesta:
    return ServicioCliente(session).crear(data)


@router.get("", response_model=ClientesPagina)
def listar(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ClientesPagina:
    return ServicioCliente(session).listar(q, offset, limit)


@router.get("/{id}", response_model=ClienteRespuesta)
def obtener(id: Identificador, session: DatabaseSession) -> ClienteRespuesta:
    return ServicioCliente(session).obtener(id)


@router.put("/{id}", response_model=ClienteRespuesta, dependencies=[SoloAdministrador])
def actualizar(id: Identificador, data: ClienteActualizar, session: DatabaseSession) -> ClienteRespuesta:
    return ServicioCliente(session).actualizar(id, data)


@router.delete("/{id}", status_code=204, dependencies=[SoloAdministrador])
def eliminar(id: Identificador, session: DatabaseSession) -> Response:
    ServicioCliente(session).eliminar(id)
    return Response(status_code=204)


@router.delete("/{id}/vehiculos/{vehiculo_id}", status_code=204, dependencies=[SoloAdministrador])
def eliminar_vehiculo(id: Identificador, vehiculo_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
                      session: DatabaseSession) -> Response:
    ServicioCliente(session).eliminar_vehiculo(id, vehiculo_id)
    return Response(status_code=204)
