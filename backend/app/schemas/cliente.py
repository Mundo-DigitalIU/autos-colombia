from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.models import required_text
from app.schemas.vehiculo import VehiculoCrear, VehiculoRespuesta

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
MAXIMO_VEHICULOS = 20


class VehiculoActualizarCliente(VehiculoCrear):
    """Vehículo dentro de PUT /clientes/{id}: con `id` edita uno existente; sin `id` crea uno nuevo."""
    id: Annotated[int | None, Field(strict=True, ge=1, le=9223372036854775807)] = None


class ClienteCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Texto
    documento: Texto
    telefono: Texto
    vehiculos: Annotated[list[VehiculoCrear], Field(max_length=MAXIMO_VEHICULOS)] = []


class ClienteActualizar(BaseModel):
    """Los vehículos del cliente que no aparezcan aquí se conservan; quitarlos exige DELETE."""
    model_config = ConfigDict(extra="forbid")
    nombre: Texto
    documento: Texto
    telefono: Texto
    vehiculos: Annotated[list[VehiculoActualizarCliente], Field(max_length=MAXIMO_VEHICULOS)] = []


class ClienteRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    documento: str
    telefono: str
    vehiculos: list[VehiculoRespuesta]


class ClientesPagina(BaseModel):
    items: list[ClienteRespuesta]
    total: int
    offset: int
    limit: int
