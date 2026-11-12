from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.models import required_text

NombreUsuario = Annotated[str, BeforeValidator(lambda value: required_text(value, "usuario")), Field(max_length=100)]


def _no_vacia(value: str) -> str:
    if not value.strip():
        raise ValueError("La contraseña no puede estar vacía.")
    return value


class LoginCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario: NombreUsuario
    # La contraseña no se recorta: los espacios pueden formar parte de ella.
    contrasena: Annotated[str, Field(max_length=200), AfterValidator(_no_vacia)]


class LoginRespuesta(BaseModel):
    token: str
    rol: str
    nombre: str
    expira: datetime

    @field_validator("expira")
    @classmethod
    def expira_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class MensajeRespuesta(BaseModel):
    mensaje: str
