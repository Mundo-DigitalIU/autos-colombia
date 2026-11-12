"""Carga datos de prueba: 80 celdas, 10 vehículos, 3 clientes y las cuentas `admin` y `operador`.

Solo inserta datos y nunca borra ni modifica los que ya existen. Se puede
ejecutar varias veces: lo que ya está en la base se omite.

Contraseñas de las dos cuentas: se leen de SEED_ADMIN_CLAVE y SEED_OPERADOR_CLAVE
(variables de entorno, mínimo 8 caracteres). Si falta alguna, el seed genera una
aleatoria al crear la cuenta y la muestra una sola vez en pantalla. Una cuenta que
ya existe conserva su contraseña. Nunca se guardan contraseñas en el código.

Uso, desde la carpeta backend (PowerShell):
    $env:SEED_ADMIN_CLAVE = 'una-clave-segura'      # opcional
    $env:SEED_OPERADOR_CLAVE = 'otra-clave-segura'  # opcional
    .\\.venv\\Scripts\\python.exe seed.py
"""

import os
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ConfigurationError, load_database_settings
from app.database import create_database_engine
from app.models import Celda, Cliente, Operador, Usuario, Vehiculo
from app.security import hashear_clave

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


def cargar(session: Session, claves: dict[str, str] | None = None) -> tuple[dict[str, list[int]], list[tuple[str, str]]]:
    """Inserta lo que falta.

    Devuelve ({tabla: [nuevos, existentes]}, [(usuario, clave)]) con las contraseñas que
    el seed tuvo que generar. `claves` asocia el nombre de la variable de entorno con su valor.
    """
    claves = claves or {}
    resumen = {"vehículos": [0, 0], "celdas": [0, 0], "clientes": [0, 0], "operadores": [0, 0], "cuentas": [0, 0]}
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
            "Comprueba la conexión con check_db.py y que la base esté en la revisión 0003.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
