from datetime import date, datetime, timedelta, timezone
from functools import wraps

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from app.models import Cliente, Operador, Pago, Tarifa, Vehiculo
from app.schemas.pago import (
    EstadoMensualidadRespuesta, EstadosMensualidadPagina, PagoAnular, PagoCrear, PagoRespuesta, PagosPagina,
)
from app.services.comun import contiene
from app.services.estancia import ZONA_LOCAL, rango_entrada

DIAS_VIGENCIA = 30


def ahora_utc() -> datetime:
    """Instante actual; las pruebas lo sustituyen para simular la fecha."""
    return datetime.now(timezone.utc)


def hoy_bogota() -> date:
    return ahora_utc().astimezone(ZONA_LOCAL).date()


class PagoError(Exception):
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
            if code == "23505" and constraint == "uq_pago_vehiculo_vigencia_registrado":
                raise PagoError(409, "La mensualidad de este vehículo ya está pagada.") from None
            if code == "23503":
                raise PagoError(404, "Una de las referencias ya no existe. Actualiza los datos.") from None
            if code in {"23502", "23514"}:
                raise PagoError(422, "Los datos incumplen las restricciones del pago.") from None
            raise PagoError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            self.session.rollback()
            raise PagoError(503, "No se pudo completar la operación con la base de datos.") from None
    return wrapped


def a_respuesta(pago: Pago, cliente: Cliente, vehiculo: Vehiculo, operador: Operador,
                anulador: Operador | None) -> PagoRespuesta:
    return PagoRespuesta(
        id=pago.id, fecha_pago=pago.fecha_pago, cliente_nombre=cliente.nombre,
        cliente_documento=cliente.documento, placa=vehiculo.placa, tipo=vehiculo.tipo, valor=pago.valor,
        medio_pago=pago.medio_pago, vigencia_desde=pago.vigencia_desde, vigencia_hasta=pago.vigencia_hasta,
        registrado_por=operador.nombre, estado=pago.estado, motivo_anulacion=pago.motivo_anulacion,
        anulado_por=anulador.nombre if anulador is not None else None, anulado_en=pago.anulado_en,
    )


class ServicioPago:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _comprobante(self, pago_id: int) -> PagoRespuesta:
        op, anulador = aliased(Operador), aliased(Operador)
        fila = self.session.execute(
            select(Pago, Cliente, Vehiculo, op, anulador)
            .join(Cliente, Cliente.id == Pago.cliente_id)
            .join(Vehiculo, Vehiculo.id == Pago.vehiculo_id)
            .join(op, op.id == Pago.operador_id)
            .outerjoin(anulador, anulador.id == Pago.anulado_por_operador_id)
            .where(Pago.id == pago_id)
            .execution_options(populate_existing=True)
        ).one_or_none()
        if fila is None:
            raise PagoError(404, "Pago no encontrado.")
        return a_respuesta(*fila)

    def _ultimo_vigente(self, vehiculo_id: int) -> Pago | None:
        """Último pago REGISTRADO del vehículo: el de mayor vigencia."""
        return self.session.scalar(
            select(Pago).where(Pago.vehiculo_id == vehiculo_id, Pago.estado == "REGISTRADO")
            .order_by(Pago.vigencia_hasta.desc(), Pago.id.desc()).limit(1)
        )

    @transaccion
    def registrar(self, data: PagoCrear, operador_id: int) -> PagoRespuesta:
        # Se bloquea la fila del vehículo: dos pagos simultáneos del mismo vehículo se serializan.
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == data.placa).with_for_update())
        if vehiculo is None:
            raise PagoError(404, "Vehículo no encontrado.")
        if vehiculo.cliente_id is None:
            raise PagoError(409, "El vehículo no tiene un cliente asociado.")
        if self.session.get(Operador, operador_id) is None:
            raise PagoError(404, "Operador no encontrado.")
        hoy = hoy_bogota()
        ultimo = self._ultimo_vigente(vehiculo.id)
        if ultimo is not None and ultimo.vigencia_hasta >= hoy + timedelta(days=DIAS_VIGENCIA):
            raise PagoError(409, "La mensualidad de este vehículo ya está pagada.")
        tarifa = self.session.scalar(select(Tarifa).where(Tarifa.tipo_vehiculo == vehiculo.tipo))
        if tarifa is None:
            raise PagoError(409, "No hay una tarifa configurada para este tipo de vehículo.")
        # La vigencia se cuenta desde la fecha de corte anterior, aunque el cliente pague tarde.
        desde = ultimo.vigencia_hasta if ultimo is not None else hoy
        pago = Pago(
            vehiculo_id=vehiculo.id, cliente_id=vehiculo.cliente_id, valor=tarifa.valor_mensual,
            medio_pago=data.medio_pago, fecha_pago=ahora_utc(), vigencia_desde=desde,
            vigencia_hasta=desde + timedelta(days=DIAS_VIGENCIA), operador_id=operador_id,
        )
        self.session.add(pago)
        # El índice único parcial decide también si algo superó las comprobaciones previas.
        self.session.flush()
        return self._comprobante(pago.id)

    @transaccion
    def anular(self, pago_id: int, data: PagoAnular, operador_id: int) -> PagoRespuesta:
        motivo = data.motivo.strip()
        if not motivo:
            raise PagoError(422, "Escribe el motivo de la anulación.")
        vehiculo_id = self.session.scalar(select(Pago.vehiculo_id).where(Pago.id == pago_id))
        if vehiculo_id is None:
            raise PagoError(404, "Pago no encontrado.")
        # Se bloquea el vehículo (igual que al registrar) y se vuelve a leer el pago ya bloqueado.
        self.session.scalar(select(Vehiculo.id).where(Vehiculo.id == vehiculo_id).with_for_update())
        pago = self.session.scalar(
            select(Pago).where(Pago.id == pago_id).execution_options(populate_existing=True)
        )
        if pago.estado == "ANULADO":
            raise PagoError(409, "El pago ya está anulado.")
        if self._ultimo_vigente(vehiculo_id).id != pago.id:
            raise PagoError(409, "Solo se puede anular el último pago del vehículo.")
        if self.session.get(Operador, operador_id) is None:
            raise PagoError(404, "Operador no encontrado.")
        pago.estado = "ANULADO"
        pago.anulado_en = ahora_utc()
        pago.anulado_por_operador_id = operador_id
        pago.motivo_anulacion = motivo
        self.session.flush()
        return self._comprobante(pago.id)

    @transaccion
    def obtener(self, pago_id: int) -> PagoRespuesta:
        return self._comprobante(pago_id)

    @transaccion
    def listar(self, q: str | None, estado: str | None, desde: date | None, hasta: date | None,
               offset: int, limit: int) -> PagosPagina:
        """Pagos del más reciente al más antiguo; `desde` y `hasta` filtran la fecha de pago (hora de Bogotá)."""
        filtros = []
        texto = (q or "").strip()
        if texto:
            filtros.append(or_(contiene(Cliente.documento, texto), contiene(Cliente.nombre, texto),
                               contiene(Vehiculo.placa, texto)))
        if estado is not None:
            filtros.append(Pago.estado == estado)
        inicio, fin = rango_entrada(desde, hasta)
        if inicio is not None:
            filtros.append(Pago.fecha_pago >= inicio)
        if fin is not None:
            filtros.append(Pago.fecha_pago < fin)
        union = (Cliente.id == Pago.cliente_id, Vehiculo.id == Pago.vehiculo_id)
        total = self.session.scalar(
            select(func.count()).select_from(Pago).join(Cliente, union[0]).join(Vehiculo, union[1]).where(*filtros)
        )
        op, anulador = aliased(Operador), aliased(Operador)
        filas = self.session.execute(
            select(Pago, Cliente, Vehiculo, op, anulador)
            .join(Cliente, union[0]).join(Vehiculo, union[1])
            .join(op, op.id == Pago.operador_id)
            .outerjoin(anulador, anulador.id == Pago.anulado_por_operador_id)
            .where(*filtros)
            .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
            .offset(offset).limit(limit)
        ).all()
        return PagosPagina(items=[a_respuesta(*fila) for fila in filas], total=total, offset=offset, limit=limit)

    @transaccion
    def estados(self, q: str | None, estado: str | None, offset: int, limit: int) -> EstadosMensualidadPagina:
        """Un elemento por vehículo con cliente, con el estado de su mensualidad a la fecha de hoy."""
        hoy = hoy_bogota()
        ultimo = (
            select(Pago.vehiculo_id, func.max(Pago.vigencia_hasta).label("hasta"))
            .where(Pago.estado == "REGISTRADO").group_by(Pago.vehiculo_id).subquery()
        )
        # (vehiculo_id, vigencia_desde) es único entre los REGISTRADO y hasta = desde + 30: un solo pago por vehículo.
        estado_sql = case((Pago.id.is_(None), "SIN_PAGOS"), (Pago.vigencia_hasta >= hoy, "AL_DIA"), else_="VENCIDA")
        desde_vehiculos = (
            select(Vehiculo, Cliente, Tarifa.valor_mensual, Pago.id, Pago.vigencia_hasta, estado_sql.label("estado"))
            .join(Cliente, Cliente.id == Vehiculo.cliente_id)
            .outerjoin(Tarifa, Tarifa.tipo_vehiculo == Vehiculo.tipo)
            .outerjoin(ultimo, ultimo.c.vehiculo_id == Vehiculo.id)
            .outerjoin(Pago, (Pago.vehiculo_id == Vehiculo.id) & (Pago.estado == "REGISTRADO")
                       & (Pago.vigencia_hasta == ultimo.c.hasta))
        )
        texto = (q or "").strip()
        if texto:
            desde_vehiculos = desde_vehiculos.where(or_(
                contiene(Cliente.documento, texto), contiene(Cliente.nombre, texto), contiene(Vehiculo.placa, texto)))
        if estado is not None:
            desde_vehiculos = desde_vehiculos.where(estado_sql == estado)
        total = self.session.scalar(select(func.count()).select_from(desde_vehiculos.order_by(None).subquery()))
        filas = self.session.execute(desde_vehiculos.order_by(Vehiculo.placa).offset(offset).limit(limit)).all()
        items = [
            EstadoMensualidadRespuesta(
                placa=vehiculo.placa, tipo=vehiculo.tipo, cliente_nombre=cliente.nombre,
                cliente_documento=cliente.documento, tarifa=tarifa, estado=estado_fila,
                vigencia_hasta=vigencia_hasta, ultimo_pago_id=pago_id,
            )
            for vehiculo, cliente, tarifa, pago_id, vigencia_hasta, estado_fila in filas
        ]
        return EstadosMensualidadPagina(items=items, total=total, offset=offset, limit=limit)
