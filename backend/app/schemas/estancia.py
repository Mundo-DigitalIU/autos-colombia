from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.celda import CeldaRespuesta
from app.schemas.vehiculo import Placa, VehiculoRespuesta

Identificador = Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]


class EntradaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: Placa
    # Si no se envía, el servicio asigna una celda libre del mismo tipo del vehículo.
    celda_id: Identificador | None = None
    operador_id: Identificador


class SalidaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: Placa
    operador_id: Identificador


class EstanciaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehiculo_id: int
    celda_id: int
    entrada: datetime
    salida: datetime | None
    operador_entrada_id: int
    operador_salida_id: int | None

    @field_validator("entrada", "salida")
    @classmethod
    def fechas_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class EstanciaAbiertaRespuesta(EstanciaRespuesta):
    celda: CeldaRespuesta


class VehiculoDentroRespuesta(BaseModel):
    estancia_id: int
    placa: str
    tipo: str
    celda_codigo: str
    entrada: datetime

    @field_validator("entrada")
    @classmethod
    def entrada_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class VehiculosDentroPagina(BaseModel):
    items: list[VehiculoDentroRespuesta]
    total: int
    offset: int
    limit: int


class EstanciaHistorialRespuesta(BaseModel):
    estancia_id: int
    placa: str
    celda_codigo: str
    entrada: datetime
    salida: datetime | None
    operador_entrada: str
    operador_salida: str | None

    @field_validator("entrada", "salida")
    @classmethod
    def fechas_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class HistorialPagina(BaseModel):
    items: list[EstanciaHistorialRespuesta]
    total: int
    offset: int
    limit: int


class CeldaEstadoRespuesta(BaseModel):
    id: int
    codigo: str
    tipo: str
    estado: Literal["DISPONIBLE", "OCUPADA"]


class CeldasEstadoPagina(BaseModel):
    items: list[CeldaEstadoRespuesta]
    total: int
    disponibles: int
    ocupadas: int
    offset: int
    limit: int


class EstadoVehiculoRespuesta(BaseModel):
    vehiculo: VehiculoRespuesta
    esta_dentro: bool
    estancia: EstanciaAbiertaRespuesta | None
