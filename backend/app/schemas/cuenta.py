from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from app.models import required_text

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
NombreUsuario = Annotated[Texto, AfterValidator(str.lower), Field(max_length=100)]
Rol = Literal["ADMINISTRADOR", "OPERADOR"]


def _clave_no_vacia(value: str) -> str:
    if not value.strip():
        raise ValueError("La contraseña no puede estar vacía.")
    return value


class CuentaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Texto
    telefono: Texto
    usuario: NombreUsuario
    # No se recorta: los espacios pueden formar parte de la contraseña.
    contrasena: Annotated[str, Field(min_length=8, max_length=200), AfterValidator(_clave_no_vacia)]
    rol: Rol


class CuentaRespuesta(BaseModel):
    """Nunca incluye la contraseña ni su hash."""
    id: int
    usuario: str
    rol: Rol
    nombre: str
    telefono: str
    operador_id: int


class CuentasPagina(BaseModel):
    items: list[CuentaRespuesta]
    total: int
    offset: int
    limit: int
