"""Dependencias de FastAPI: sesión obligatoria y permiso por rol."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.services.auth import MENSAJE_PERMISO, AuthError, SesionActual, sesion_por_token

ADMINISTRADOR = "ADMINISTRADOR"
OPERADOR = "OPERADOR"

# auto_error=False: el mensaje de 401 lo decide AuthError, igual en todos los casos.
esquema_bearer = HTTPBearer(auto_error=False)


def sesion_actual(
    session: Annotated[Session, Depends(get_session)],
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
) -> SesionActual:
    return sesion_por_token(session, credenciales.credentials if credenciales else None)


def requiere_rol(*roles: str):
    """Dependencia que exige sesión y que el rol esté entre los indicados (403 si no)."""
    def comprobar(actual: Annotated[SesionActual, Depends(sesion_actual)]) -> SesionActual:
        if actual.rol not in roles:
            raise AuthError(403, MENSAJE_PERMISO)
        return actual
    return comprobar


SesionDeUsuario = Annotated[SesionActual, Depends(sesion_actual)]
SoloAdministrador = Depends(requiere_rol(ADMINISTRADOR))
CualquierRol = Depends(sesion_actual)
