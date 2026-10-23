from datetime import datetime, timezone
from functools import wraps

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Celda, Estancia, Operador, Vehiculo, required_text
from app.schemas.celda import CeldaRespuesta
from app.schemas.estancia import (
    EntradaCrear, SalidaCrear, EstanciaRespuesta, EstanciaAbiertaRespuesta,
    EstadoVehiculoRespuesta, VehiculoDentroRespuesta, VehiculosDentroPagina,
)
from app.schemas.vehiculo import VehiculoRespuesta


class EstanciaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def transaccion(operation):
    """Una transacción por solicitud; materializa la respuesta antes del commit."""
    @wraps(operation)
    def wrapped(self, *args, **kwargs):
        try:
            with self.session.begin():
                return operation(self, *args, **kwargs)
        except IntegrityError as error:
            self.session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505":
                if constraint == "uq_estancia_vehiculo_abierta":
                    raise EstanciaError(409, "El vehículo ya está dentro.") from None
                if constraint == "uq_estancia_celda_abierta":
                    raise EstanciaError(409, "La celda está ocupada.") from None
            if code == "23503":
                raise EstanciaError(404, "Una de las referencias ya no existe. Actualiza los datos.") from None
            if code in {"23502", "23514"}:
                raise EstanciaError(422, "Los datos incumplen las restricciones de la estancia.") from None
            raise EstanciaError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            self.session.rollback()
            raise EstanciaError(503, "No se pudo completar la operación con la base de datos.") from None
    return wrapped


class ServicioEstancia:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _vehiculo(self, placa: str) -> Vehiculo:
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        return vehiculo

    def _operador(self, operador_id: int) -> Operador:
        operador = self.session.get(Operador, operador_id)
        if operador is None:
            raise EstanciaError(404, "Operador no encontrado.")
        return operador

    def _celda_libre(self, tipo: str) -> Celda:
        """Primera celda del tipo indicado sin estancia abierta.

        SKIP LOCKED evita que dos entradas simultáneas elijan la misma celda; el
        índice único de estancias abiertas sigue siendo la garantía final.
        """
        ocupada = select(Estancia.id).where(
            Estancia.celda_id == Celda.id, Estancia.salida.is_(None)
        ).correlate(Celda).exists()
        celda = self.session.scalar(
            select(Celda).where(Celda.tipo == tipo, ~ocupada)
            .order_by(Celda.id).limit(1)
            .with_for_update(skip_locked=True, of=Celda)
        )
        if celda is None:
            raise EstanciaError(409, "No hay celdas disponibles para este tipo de vehículo.")
        return celda

    @transaccion
    def entrada(self, data: EntradaCrear) -> EstanciaRespuesta:
        vehiculo = self._vehiculo(data.placa)
        celda = None
        if data.celda_id is not None:
            celda = self.session.get(Celda, data.celda_id)
            if celda is None:
                raise EstanciaError(404, "Celda no encontrada.")
        operador = self._operador(data.operador_id)
        if self.session.scalar(select(Estancia.id).where(
            Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None)
        )) is not None:
            raise EstanciaError(409, "El vehículo ya está dentro.")
        if celda is None:
            # RF-05: sin celda indicada, el sistema asigna una libre del mismo tipo del vehículo.
            celda = self._celda_libre(vehiculo.tipo)
        elif self.session.scalar(select(Estancia.id).where(
            Estancia.celda_id == celda.id, Estancia.salida.is_(None)
        )) is not None:
            raise EstanciaError(409, "La celda está ocupada.")
        estancia = Estancia(vehiculo_id=vehiculo.id, celda_id=celda.id,
                            operador_entrada_id=operador.id, entrada=datetime.now(timezone.utc))
        self.session.add(estancia)
        # Los índices únicos deciden también cuando dos solicitudes superan las consultas previas.
        self.session.flush()
        return EstanciaRespuesta.model_validate(estancia)

    @transaccion
    def salida(self, data: SalidaCrear) -> EstanciaRespuesta:
        vehiculo = self._vehiculo(data.placa)
        operador = self._operador(data.operador_id)
        # PostgreSQL vuelve a evaluar salida IS NULL tras esperar el bloqueo.
        estancia = self.session.scalar(select(Estancia).where(
            Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None)
        ).with_for_update())
        if estancia is None:
            raise EstanciaError(409, "El vehículo no tiene una estancia abierta.")
        try:
            estancia.cerrar(datetime.now(timezone.utc), operador)
        except ValueError:
            raise EstanciaError(409, "No se puede cerrar la estancia con su estado o fecha actuales.") from None
        self.session.flush()
        return EstanciaRespuesta.model_validate(estancia)

    @transaccion
    def dentro(self, offset: int, limit: int) -> VehiculosDentroPagina:
        """Vehículos con una estancia abierta, de la entrada más antigua a la más reciente."""
        abiertas = Estancia.salida.is_(None)
        total = self.session.scalar(select(func.count()).select_from(Estancia).where(abiertas))
        filas = self.session.execute(
            select(Estancia, Vehiculo, Celda)
            .join(Vehiculo, Vehiculo.id == Estancia.vehiculo_id)
            .join(Celda, Celda.id == Estancia.celda_id)
            .where(abiertas)
            .order_by(Estancia.entrada, Estancia.id)
            .offset(offset).limit(limit)
        ).all()
        items = [
            VehiculoDentroRespuesta(estancia_id=estancia.id, placa=vehiculo.placa, tipo=vehiculo.tipo,
                                    celda_codigo=celda.codigo, entrada=estancia.entrada)
            for estancia, vehiculo, celda in filas
        ]
        return VehiculosDentroPagina(items=items, total=total, offset=offset, limit=limit)

    @transaccion
    def consultar(self, placa: str) -> EstadoVehiculoRespuesta:
        placa = required_text(placa, "placa").upper()
        # Una sola consulta da un estado consistente de vehículo, estancia y celda.
        row = self.session.execute(select(Vehiculo, Estancia, Celda).outerjoin(
            Estancia, and_(Estancia.vehiculo_id == Vehiculo.id, Estancia.salida.is_(None))
        ).outerjoin(Celda, Celda.id == Estancia.celda_id).where(Vehiculo.placa == placa)).one_or_none()
        if row is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        vehiculo, estancia, celda = row
        abierta = None
        if estancia is not None:
            abierta = EstanciaAbiertaRespuesta(
                **EstanciaRespuesta.model_validate(estancia).model_dump(),
                celda=CeldaRespuesta.model_validate(celda),
            )
        return EstadoVehiculoRespuesta(vehiculo=VehiculoRespuesta.model_validate(vehiculo),
                                       esta_dentro=estancia is not None, estancia=abierta)
