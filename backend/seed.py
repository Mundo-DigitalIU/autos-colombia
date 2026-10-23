"""Carga datos de prueba: 10 vehículos, 10 celdas y 1 operador.

Solo inserta datos y nunca borra ni modifica los que ya existen. Se puede
ejecutar varias veces: lo que ya está en la base se omite.

Uso, desde la carpeta backend:
    .\\.venv\\Scripts\\python.exe seed.py
"""

import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ConfigurationError, load_database_settings
from app.database import create_database_engine
from app.models import Celda, Operador, Vehiculo

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

# (codigo, tipo): el tipo de la celda usa las mismas palabras que el del vehículo
CELDAS = [
    ("C-01", "AUTOMOVIL"),
    ("C-02", "AUTOMOVIL"),
    ("C-03", "AUTOMOVIL"),
    ("C-04", "AUTOMOVIL"),
    ("C-05", "CAMIONETA"),
    ("M-01", "MOTO"),
    ("M-02", "MOTO"),
    ("M-03", "MOTO"),
    ("M-04", "MOTO"),
    ("M-05", "MOTO"),
]

# (nombre, telefono)
OPERADORES = [
    ("Operador Portería", "3000000000"),
]


def cargar(session: Session) -> dict[str, tuple[int, int]]:
    """Inserta lo que falta y devuelve (nuevos, existentes) por tabla."""
    resumen = {"vehículos": [0, 0], "celdas": [0, 0], "operadores": [0, 0]}

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

    for nombre, telefono in OPERADORES:
        existe = session.scalar(
            select(Operador).where(Operador.nombre == nombre, Operador.telefono == telefono)
        )
        if existe is None:
            session.add(Operador(nombre=nombre, telefono=telefono))
            resumen["operadores"][0] += 1
        else:
            resumen["operadores"][1] += 1

    return {tabla: (nuevos, existentes) for tabla, (nuevos, existentes) in resumen.items()}


def main() -> int:
    engine = None
    try:
        engine = create_database_engine(load_database_settings())
        with Session(engine) as session:
            with session.begin():
                resumen = cargar(session)
        for tabla, (nuevos, existentes) in resumen.items():
            print(f"{tabla.capitalize()}: {nuevos} nuevos, {existentes} ya existían.")
        print("Datos de prueba listos.")
        return 0
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (SQLAlchemyError, OSError, ValueError):
        # Los errores del driver pueden incluir credenciales o datos de conexión.
        print(
            "No se pudieron cargar los datos de prueba. No se guardó ningún cambio. "
            "Comprueba la conexión con check_db.py y que la base esté en la revisión 0002.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
