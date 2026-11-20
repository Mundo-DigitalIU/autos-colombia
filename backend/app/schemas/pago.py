from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_serializer, field_validator

from app.models import required_text
from app.schemas.vehiculo import Placa
from app.services.estancia import ZONA_LOCAL

MedioPago = Annotated[
    Literal["EFECTIVO", "TRANSFERENCIA", "TARJETA"],
    BeforeValidator(lambda value: required_text(value, "medio_pago")),
]


class PagoCrear(BaseModel):
    """El operador y el valor no viajan en el cuerpo: son los de la sesión y la tarifa."""
    model_config = ConfigDict(extra="forbid")
    placa: Placa
    medio_pago: MedioPago


class PagoAnular(BaseModel):
    """El motivo vacío lo rechaza el servicio con su mensaje en español."""
    model_config = ConfigDict(extra="forbid")
    motivo: Annotated[str, Field(max_length=500)] = ""


class PagoRespuesta(BaseModel):
    """Comprobante de pago: `id` es el número del comprobante. Las horas van en hora de Bogotá."""
    id: int
    fecha_pago: datetime
    cliente_nombre: str
    cliente_documento: str
    placa: str
    tipo: str
    valor: Decimal
    medio_pago: str
    vigencia_desde: date
    vigencia_hasta: date
    registrado_por: str
    estado: Literal["REGISTRADO", "ANULADO"]
    motivo_anulacion: str | None
    anulado_por: str | None
    anulado_en: datetime | None

    @field_validator("fecha_pago", "anulado_en")
    @classmethod
    def hora_bogota(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(ZONA_LOCAL) if value is not None else None

    @field_serializer("valor")
    def valor_numero(self, value: Decimal) -> float:
        return float(value)


class PagosPagina(BaseModel):
    items: list[PagoRespuesta]
    total: int
    offset: int
    limit: int


class EstadoMensualidadRespuesta(BaseModel):
    placa: str
    tipo: str
    cliente_nombre: str
    cliente_documento: str
    tarifa: Decimal | None
    estado: Literal["AL_DIA", "VENCIDA", "SIN_PAGOS"]
    vigencia_hasta: date | None
    ultimo_pago_id: int | None

    @field_serializer("tarifa")
    def tarifa_numero(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class EstadosMensualidadPagina(BaseModel):
    items: list[EstadoMensualidadRespuesta]
    total: int
    offset: int
    limit: int
