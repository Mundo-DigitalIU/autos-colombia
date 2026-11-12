from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.models import required_text

TIPOS_CELDA = ("MOTO", "AUTOMOVIL", "CAMIONETA")


def _codigo(value: Any) -> str:
    """Recorta y pasa a mayúsculas; un código vacío tiene un mensaje propio."""
    if not isinstance(value, str) or not value.strip():
        raise PydanticCustomError("codigo_vacio", "Escribe el código de la celda.")
    return value.strip().upper()


Codigo = Annotated[str, BeforeValidator(_codigo)]
# El tipo se recorta pero no se corrige: solo valen MOTO, AUTOMOVIL y CAMIONETA.
TipoCelda = Annotated[Literal["MOTO", "AUTOMOVIL", "CAMIONETA"], BeforeValidator(lambda value: required_text(value, "tipo"))]


class CeldaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo
    tipo: TipoCelda


class CeldaActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo | None = None
    tipo: TipoCelda | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value


class CeldaRespuesta(BaseModel):
    """El tipo se devuelve tal como está guardado: las celdas antiguas pueden tener otros textos."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    codigo: str
    tipo: str


class CeldasPagina(BaseModel):
    items: list[CeldaRespuesta]
    total: int
    offset: int
    limit: int
