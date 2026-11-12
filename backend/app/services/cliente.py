from functools import wraps

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models import Cliente, Estancia, Vehiculo
from app.schemas.cliente import ClienteActualizar, ClienteCrear, ClienteRespuesta, ClientesPagina
from app.services.comun import MENSAJE_BASE, contiene, nueva_transaccion

MENSAJE_CON_ESTANCIAS = "No se puede eliminar: sus vehículos ya tienen entradas y salidas registradas."


class ClienteError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def transaccion(operation):
    """Una transacción por solicitud con mensajes públicos sin detalles del driver."""
    @wraps(operation)
    def wrapped(self, *args, **kwargs):
        try:
            with nueva_transaccion(self.session):
                return operation(self, *args, **kwargs)
        except IntegrityError as error:
            self.session.rollback()
            codigo = getattr(error.orig, "sqlstate", None)
            restriccion = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if codigo == "23505" and restriccion == "uq_cliente_documento":
                raise ClienteError(409, "Ya hay un cliente con ese documento.") from None
            if codigo == "23505" and restriccion == "uq_vehiculo_placa":
                raise ClienteError(409, "Esa placa ya está registrada.") from None
            # 23001 es restrict_violation: la estancia aún referencia al vehículo.
            if codigo in {"23001", "23503"}:
                raise ClienteError(409, MENSAJE_CON_ESTANCIAS) from None
            if codigo in {"23502", "23514"}:
                raise ClienteError(422, "Los datos incumplen las restricciones del cliente.") from None
            raise ClienteError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            self.session.rollback()
            raise ClienteError(503, MENSAJE_BASE) from None
    return wrapped


class ServicioCliente:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _cliente(self, cliente_id: int) -> Cliente:
        cliente = self.session.get(Cliente, cliente_id)
        if cliente is None:
            raise ClienteError(404, "Cliente no encontrado.")
        return cliente

    def _tiene_estancias(self, *condiciones) -> bool:
        return bool(self.session.scalar(
            select(exists().where(Estancia.vehiculo_id == Vehiculo.id, *condiciones))
        ))

    @transaccion
    def crear(self, data: ClienteCrear) -> ClienteRespuesta:
        cliente = Cliente(nombre=data.nombre, documento=data.documento, telefono=data.telefono)
        self.session.add(cliente)
        self.session.flush()
        for vehiculo in data.vehiculos:
            self.session.add(Vehiculo(**vehiculo.model_dump(), cliente_id=cliente.id))
            # Un flush por vehículo: una placa repetida falla aquí y revierte todo.
            self.session.flush()
        self.session.refresh(cliente)
        return ClienteRespuesta.model_validate(cliente)

    @transaccion
    def listar(self, q: str | None, offset: int, limit: int) -> ClientesPagina:
        filtros = []
        texto = (q or "").strip()
        if texto:
            filtros.append(or_(
                contiene(Cliente.documento, texto),
                contiene(Cliente.nombre, texto),
                exists().where(Vehiculo.cliente_id == Cliente.id, contiene(Vehiculo.placa, texto)),
            ))
        total = self.session.scalar(select(func.count()).select_from(Cliente).where(*filtros))
        clientes = self.session.scalars(
            select(Cliente).where(*filtros).options(selectinload(Cliente.vehiculos))
            .order_by(Cliente.id).offset(offset).limit(limit)
        ).all()
        items = [ClienteRespuesta.model_validate(cliente) for cliente in clientes]
        return ClientesPagina(items=items, total=total, offset=offset, limit=limit)

    @transaccion
    def obtener(self, cliente_id: int) -> ClienteRespuesta:
        return ClienteRespuesta.model_validate(self._cliente(cliente_id))

    @transaccion
    def actualizar(self, cliente_id: int, data: ClienteActualizar) -> ClienteRespuesta:
        cliente = self._cliente(cliente_id)
        cliente.nombre, cliente.documento, cliente.telefono = data.nombre, data.documento, data.telefono
        self.session.flush()
        propios = {vehiculo.id: vehiculo for vehiculo in cliente.vehiculos}
        for item in data.vehiculos:
            campos = item.model_dump(exclude={"id"})
            if item.id is None:
                self.session.add(Vehiculo(**campos, cliente_id=cliente.id))
            else:
                vehiculo = propios.get(item.id)
                if vehiculo is None:
                    raise ClienteError(404, "Vehículo no encontrado.")
                for clave, valor in campos.items():
                    setattr(vehiculo, clave, valor)
            self.session.flush()
        self.session.refresh(cliente)
        return ClienteRespuesta.model_validate(cliente)

    @transaccion
    def eliminar(self, cliente_id: int) -> None:
        cliente = self._cliente(cliente_id)
        if self._tiene_estancias(Vehiculo.cliente_id == cliente.id):
            raise ClienteError(409, MENSAJE_CON_ESTANCIAS)
        # La restricción de la base de datos decide si una entrada aparece entre la consulta y el borrado.
        for vehiculo in list(cliente.vehiculos):
            self.session.delete(vehiculo)
        self.session.flush()
        self.session.delete(cliente)
        self.session.flush()

    @transaccion
    def eliminar_vehiculo(self, cliente_id: int, vehiculo_id: int) -> None:
        self._cliente(cliente_id)
        vehiculo = self.session.scalar(
            select(Vehiculo).where(Vehiculo.id == vehiculo_id, Vehiculo.cliente_id == cliente_id)
        )
        if vehiculo is None:
            raise ClienteError(404, "Vehículo no encontrado.")
        if self._tiene_estancias(Vehiculo.id == vehiculo.id):
            raise ClienteError(409, MENSAJE_CON_ESTANCIAS)
        self.session.delete(vehiculo)
        self.session.flush()
