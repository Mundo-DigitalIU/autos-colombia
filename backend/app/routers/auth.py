from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import SesionDeUsuario
from app.database import get_session
from app.schemas.auth import LoginCrear, LoginRespuesta, MensajeRespuesta
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Autenticación"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/login", response_model=LoginRespuesta)
def login(data: LoginCrear, session: DatabaseSession) -> LoginRespuesta:
    return service.iniciar_sesion(session, data)


@router.post("/logout", response_model=MensajeRespuesta)
def logout(actual: SesionDeUsuario, session: DatabaseSession) -> MensajeRespuesta:
    service.cerrar_sesion(session, actual.sesion_id)
    return MensajeRespuesta(mensaje="Sesión cerrada.")
