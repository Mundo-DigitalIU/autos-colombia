"""Carga datos de prueba: 80 celdas, 10 vehículos, 3 clientes, las cuentas `admin` y `operador`,
las tres tarifas mensuales y dos pagos de ejemplo.

Solo inserta datos y nunca borra ni modifica los que ya existen. Se puede
ejecutar varias veces: lo que ya está en la base se omite.

Contraseñas de las dos cuentas: se leen de SEED_ADMIN_CLAVE y SEED_OPERADOR_CLAVE
(variables de entorno, mínimo 8 caracteres). Si falta alguna, el seed genera una
aleatoria al crear la cuenta y la muestra una sola vez en pantalla. Una cuenta que
ya existe conserva su contraseña. Nunca se guardan contraseñas en el código.

Tarifas: una tarifa que ya existe no se cambia (se edita en la base, no aquí). Pagos de ejemplo:
uno de hace 10 días (AL_DIA) y otro de hace 45 días (VENCIDA), en clientes distintos y a nombre
del administrador; sus fechas se calculan con la fecha actual. Un vehículo que ya tiene algún
pago no recibe otro, así que volver a ejecutar el seed no los duplica.

Uso, desde la carpeta backend (PowerShell):
    $env:SEED_ADMIN_CLAVE = 'una-clave-segura'      # opcional
    $env:SEED_OPERADOR_CLAVE = 'otra-clave-segura'  # opcional
    .\\.venv\\Scripts\\python.exe seed.py
"""

import os
import secrets
import sys
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ConfigurationError, load_database_settings
from app.database import create_database_engine
from app.models import Celda, Cliente, Operador, Pago, Tarifa, Usuario, Vehiculo
from app.security import hashear_clave
from app.services.estancia import ZONA_LOCAL
from app.services.pago import DIAS_VIGENCIA, ahora_utc

# Valor mensual por tipo de vehículo, en pesos. Cámbialos aquí antes de cargar el seed por primera vez.
TARIFAS = {"MOTO": 100000, "AUTOMOVIL": 250000, "CAMIONETA": 250000}

# Días atrás en que se hizo cada pago de ejemplo: con 10 días la vigencia sigue abierta (AL_DIA)
# y con 45 días ya terminó (VENCIDA).
DIAS_PAGOS_EJEMPLO = (10, 45)

# Clientes ficticios que solo se crean si los de ejemplo no bastan para los dos pagos.
# (nombre, documento, telefono, placa, color, modelo, marca, tipo)
CLIENTES_DEMO = [
    ("Cliente Demo Uno", "1000000101", "3001000101", "DEM01A", "Blanco", 2021, "Honda", "MOTO"),
    ("Cliente Demo Dos", "1000000102", "3001000102", "DEM02B", "Negro", 2022, "Yamaha", "MOTO"),
]

# (placa, color, modelo, marca, tipo)
VEHICULOS = [
    ("ABC123", "Rojo", 2020, "Mazda", "AUTOMOVIL"),
    ("DEF456", "Gris", 2018, "Chevrolet", "AUTOMOVIL"),
    ("GHI789", "Blanco", 2019, "Renault", "AUTOMOVIL"),
    ("JKL012", "Azul", 2021, "Kia", "AUTOMOVIL"),
    ("MNO345", "Negro", 2022, "Toyota", "CAMIONETA"),
    ("ABC12D", "Negro", 2019, "Yamaha", "MOTO"),
    ("EFG34H", "Rojo", 2021, "Honda", "MOTO"),
    ("IJK56L", "Azul", 2020, "Suzuki", "MOTO"),
    ("MNO78P", "Verde", 2022, "AKT", "MOTO"),
    ("QRS90T", "Gris", 2018, "Bajaj", "MOTO"),
]

# (codigo, tipo): 55 de automóvil, 5 de camioneta y 20 de moto = 80 celdas
CELDAS = (
    [(f"A-{n:02d}", "AUTOMOVIL") for n in range(1, 56)]
    + [(f"K-{n:02d}", "CAMIONETA") for n in range(1, 6)]
    + [(f"M-{n:02d}", "MOTO") for n in range(1, 21)]
)

# (nombre, documento, telefono, placas de sus vehículos): datos ficticios
CLIENTES = [
    ("Laura Gómez", "1000000001", "3101112233", ["ABC123", "DEF456", "ABC12D"]),
    ("Carlos Ramírez", "1000000002", "3204445566", ["MNO345", "GHI789", "EFG34H"]),
    ("Marta Rojas", "1000000003", "3157778899", ["JKL012", "IJK56L", "MNO78P", "QRS90T"]),
]

# (nombre del perfil, teléfono)
OPERADOR_PORTERIA = ("Operador Portería", "3000000000")
ADMINISTRADOR = ("Administrador", "3000000001")

# (perfil, usuario, rol, variable de entorno con la contraseña)
CUENTAS = [
    (ADMINISTRADOR, "admin", "ADMINISTRADOR", "SEED_ADMIN_CLAVE"),
    (OPERADOR_PORTERIA, "operador", "OPERADOR", "SEED_OPERADOR_CLAVE"),
]

CLAVE_MINIMA = 8


class ClaveInvalida(ValueError):
    """La contraseña del entorno no cumple el mínimo; el mensaje nunca incluye su valor."""


def _vehiculos_para_pagos(session: Session) -> list[Vehiculo]:
    """Un vehículo con cliente por cada pago de ejemplo, de clientes distintos.

    Se prefieren los vehículos del seed y el orden es fijo, para que cada ejecución elija los mismos.
    Si no alcanzan, se crean clientes ficticios con su vehículo; los clientes existentes no se tocan.
    """
    elegidos: list[Vehiculo] = []
    for placa, *_ in VEHICULOS:
        vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is not None and vehiculo.cliente_id is not None                 and all(vehiculo.cliente_id != otro.cliente_id for otro in elegidos):
            elegidos.append(vehiculo)
    for nombre, documento, telefono, placa, color, modelo, marca, tipo in CLIENTES_DEMO:
        if len(elegidos) >= len(DIAS_PAGOS_EJEMPLO):
            break
        cliente = session.scalar(select(Cliente).where(Cliente.documento == documento))
        if cliente is None:
            cliente = Cliente(nombre=nombre, documento=documento, telefono=telefono)
            session.add(cliente)
            session.flush()
        vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            vehiculo = Vehiculo(placa=placa, color=color, modelo=modelo, marca=marca, tipo=tipo, cliente_id=cliente.id)
            session.add(vehiculo)
            session.flush()
        if vehiculo.cliente_id == cliente.id:
            elegidos.append(vehiculo)
    return elegidos[:len(DIAS_PAGOS_EJEMPLO)]


def _cargar_pagos_ejemplo(session: Session, administrador: Operador, resumen: dict[str, list[int]]) -> None:
    for vehiculo, dias in zip(_vehiculos_para_pagos(session), DIAS_PAGOS_EJEMPLO):
        if session.scalar(select(Pago.id).where(Pago.vehiculo_id == vehiculo.id).limit(1)) is not None:
            resumen["pagos"][1] += 1
            continue
        tarifa = session.scalar(select(Tarifa).where(Tarifa.tipo_vehiculo == vehiculo.tipo))
        fecha_pago = ahora_utc() - timedelta(days=dias)
        # La vigencia se cuenta desde la fecha del pago en hora de Bogotá (es el primer pago del vehículo).
        desde = fecha_pago.astimezone(ZONA_LOCAL).date()
        session.add(Pago(
            vehiculo_id=vehiculo.id, cliente_id=vehiculo.cliente_id, valor=tarifa.valor_mensual,
            medio_pago="EFECTIVO", fecha_pago=fecha_pago, vigencia_desde=desde,
            vigencia_hasta=desde + timedelta(days=DIAS_VIGENCIA), operador_id=administrador.id,
        ))
        resumen["pagos"][0] += 1
    session.flush()


def cargar(session: Session, claves: dict[str, str] | None = None) -> tuple[dict[str, list[int]], list[tuple[str, str]]]:
    """Inserta lo que falta.

    Devuelve ({tabla: [nuevos, existentes]}, [(usuario, clave)]) con las contraseñas que
    el seed tuvo que generar. `claves` asocia el nombre de la variable de entorno con su valor.
    """
    claves = claves or {}
    resumen = {"vehículos": [0, 0], "celdas": [0, 0], "clientes": [0, 0], "operadores": [0, 0], "cuentas": [0, 0],
               "tarifas": [0, 0], "pagos": [0, 0]}
    generadas: list[tuple[str, str]] = []

    for placa, color, modelo, marca, tipo in VEHICULOS:
        existe = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if existe is None:
            session.add(Vehiculo(placa=placa, color=color, modelo=modelo, marca=marca, tipo=tipo))
            resumen["vehículos"][0] += 1
        else:
            resumen["vehículos"][1] += 1

    for codigo, tipo in CELDAS:
        existe = session.scalar(select(Celda).where(Celda.codigo == codigo))
        if existe is None:
            session.add(Celda(codigo=codigo, tipo=tipo))
            resumen["celdas"][0] += 1
        else:
            resumen["celdas"][1] += 1
    session.flush()

    for nombre, documento, telefono, placas in CLIENTES:
        cliente = session.scalar(select(Cliente).where(Cliente.documento == documento))
        if cliente is None:
            cliente = Cliente(nombre=nombre, documento=documento, telefono=telefono)
            session.add(cliente)
            session.flush()
            resumen["clientes"][0] += 1
        else:
            resumen["clientes"][1] += 1
        # Solo se vinculan vehículos que todavía no tienen cliente: nunca se reasignan.
        for placa in placas:
            vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
            if vehiculo is not None and vehiculo.cliente_id is None:
                vehiculo.cliente_id = cliente.id

    operadores: dict[tuple[str, str], Operador] = {}
    for nombre, telefono in (OPERADOR_PORTERIA, ADMINISTRADOR):
        operador = session.scalar(select(Operador).where(Operador.nombre == nombre, Operador.telefono == telefono))
        if operador is None:
            operador = Operador(nombre=nombre, telefono=telefono)
            session.add(operador)
            session.flush()
            resumen["operadores"][0] += 1
        else:
            resumen["operadores"][1] += 1
        operadores[(nombre, telefono)] = operador

    for perfil, usuario, rol, variable in CUENTAS:
        operador = operadores[perfil]
        existe = session.scalar(
            select(Usuario).where((Usuario.nombre_usuario == usuario) | (Usuario.operador_id == operador.id))
        )
        if existe is not None:
            resumen["cuentas"][1] += 1
            continue
        clave = claves.get(variable)
        if clave:
            if len(clave) < CLAVE_MINIMA:
                raise ClaveInvalida(f"{variable} debe tener al menos {CLAVE_MINIMA} caracteres.")
        else:
            clave = secrets.token_urlsafe(12)
            generadas.append((usuario, clave))
        session.add(Usuario(nombre_usuario=usuario, clave_hash=hashear_clave(clave), rol=rol, operador_id=operador.id))
        resumen["cuentas"][0] += 1

    for tipo, valor in TARIFAS.items():
        # Una tarifa existente no se duplica ni cambia de valor.
        if session.scalar(select(Tarifa).where(Tarifa.tipo_vehiculo == tipo)) is None:
            session.add(Tarifa(tipo_vehiculo=tipo, valor_mensual=valor))
            resumen["tarifas"][0] += 1
        else:
            resumen["tarifas"][1] += 1
    session.flush()

    _cargar_pagos_ejemplo(session, operadores[ADMINISTRADOR], resumen)

    return {tabla: [nuevos, existentes] for tabla, (nuevos, existentes) in resumen.items()}, generadas


def main() -> int:
    engine = None
    try:
        claves = {variable: os.environ.get(variable, "") for *_, variable in CUENTAS}
        engine = create_database_engine(load_database_settings())
        with Session(engine) as session:
            with session.begin():
                resumen, generadas = cargar(session, claves)
        for tabla, (nuevos, existentes) in resumen.items():
            print(f"{tabla.capitalize()}: {nuevos} nuevos, {existentes} ya existían.")
        for usuario, clave in generadas:
            print(f"Contraseña generada para '{usuario}': {clave}")
        if generadas:
            print("Guárdala ahora: no se vuelve a mostrar y en la base solo queda su hash.")
        print("Datos de prueba listos.")
        return 0
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ClaveInvalida as error:
        print(f"{error} No se guardó ningún cambio.", file=sys.stderr)
        return 2
    except (SQLAlchemyError, OSError, ValueError):
        # Los errores del driver pueden incluir credenciales o datos de conexión.
        print(
            "No se pudieron cargar los datos de prueba. No se guardó ningún cambio. "
            "Comprueba la conexión con check_db.py y que la base esté en la revisión 0004.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
