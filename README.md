# Autos Colombia

Sistema de información para el parqueadero "Autos Colombia", un parqueadero que presta el servicio por mensualidad.

Este repositorio es la **Iteración 1: gestión de la entrada y salida de vehículos**, del proyecto de Ingeniería de Software de la IU Digital de Antioquia.

**Autor:** Jeferson Cataño

## Qué hace esta iteración

En esta primera entrega me enfoqué en controlar quién entra y quién sale del parqueadero:

| Función | Requisito | Cómo funciona |
|---|---|---|
| Registrar la entrada | RF-01 a RF-04 | El operador escribe la placa. El sistema la normaliza, revisa que el vehículo esté registrado y que no esté ya dentro. |
| Asignar la celda | RF-05 | Si no se indica una celda, el sistema elige la primera libre del mismo tipo del vehículo. |
| Registrar la salida | RF-06, RF-07 | Se guarda la hora de salida y la celda queda libre. |
| Ver los vehículos dentro | RF-08 | Lista de los vehículos con una estancia abierta, con su celda y su hora de entrada. |
| Ver el historial | RF-09 | Entradas y salidas, filtradas por placa y por rango de fechas. |
| Ver las celdas | RF-11 | Cada celda con su estado (`DISPONIBLE` u `OCUPADA`) y los totales. |

Cuando algo no se puede hacer (vehículo no registrado, ya está dentro, no hay celdas), el sistema responde con un mensaje claro en español (RF-10).

**No incluye todavía:** inicio de sesión, gestión de usuarios y celdas, novedades ni pagos. Eso queda para las siguientes iteraciones. Por ahora hay un solo operador, que se carga con datos de prueba.

## De dónde parte este proyecto

Parte de la base que entregó el profesor, que ya traía la conexión a PostgreSQL, las migraciones, el CRUD de vehículos, celdas y operadores, y el registro de entrada y salida. Sobre esa base agregué:

- La **asignación automática de celda** al registrar la entrada.
- Las tres **consultas nuevas**: vehículos dentro, historial y celdas con estado.
- El script de **datos de prueba** (`backend/seed.py`).
- Las **pruebas** de todo lo anterior.
- Las **pantallas** de la iteración, a partir de mi diseño en Figma (ver "Estado").

No cambié las migraciones ni las tablas de la base.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Base de datos | PostgreSQL |
| Backend | Python con FastAPI, SQLAlchemy 2, Alembic y psycopg |
| Frontend | Angular 22 con TypeScript |
| Pruebas | pytest (backend) |

Las versiones exactas están en `backend/requirements.txt` y `frontend/package.json`.

## Estructura del repositorio

```text
AutosColombia/
├── backend/
│   ├── app/
│   │   ├── main.py          # Aplicación FastAPI y GET /health
│   │   ├── config.py        # Lee la configuración de backend/.env
│   │   ├── database.py      # Motor y sesiones de SQLAlchemy
│   │   ├── models.py        # Tablas: Vehiculo, Celda, Operador y Estancia
│   │   ├── routers/         # Las rutas de la API
│   │   ├── services/        # La lógica del negocio
│   │   └── schemas/         # Validación y respuestas (Pydantic)
│   ├── migrations/          # Migraciones de Alembic (0001 y 0002)
│   ├── tests/               # Pruebas con pytest
│   ├── seed.py              # Datos de prueba
│   ├── check_db.py          # Comprueba la conexión a PostgreSQL
│   ├── requirements.txt
│   └── .env.example         # Plantilla de configuración (sin datos reales)
└── frontend/
    └── src/app/             # Pantallas, servicios y modelos de Angular
```

## Modelo de datos

Son cuatro tablas:

| Tabla | Columnas principales |
|---|---|
| `vehiculo` | `id`, `placa` (única), `color`, `modelo`, `marca`, `tipo` (MOTO, AUTOMOVIL o CAMIONETA) |
| `celda` | `id`, `codigo` (único), `tipo` |
| `operador` | `id`, `nombre`, `telefono` |
| `estancia` | `id`, `vehiculo_id`, `celda_id`, `entrada`, `salida`, `operador_entrada_id`, `operador_salida_id` |

`estancia` guarda cada vez que un vehículo entra y sale. Mientras el vehículo sigue dentro, `salida` y `operador_salida_id` están vacíos.

La base protege las reglas del negocio:

- Un vehículo no puede tener dos estancias abiertas, y una celda tampoco (índices únicos que solo miran las estancias sin salida).
- La salida no puede ser anterior a la entrada.
- La salida y el operador de salida van juntos: o los dos están vacíos o los dos tienen valor.
- No se puede borrar un vehículo, una celda o un operador que ya tenga estancias.

## Decisiones de diseño

- **El estado de una celda no se guarda, se calcula.** Una celda está ocupada si tiene una estancia abierta. Así no puede quedar desactualizado.
- **Las fechas se guardan en UTC**, pero el historial cuenta los días en hora de Bogotá (UTC-5). Un vehículo que entra a las 11:30 p. m. aparece en el día en que entró.
- **La asignación de celda es segura con entradas simultáneas.** La consulta usa `SKIP LOCKED`, y los índices únicos de la base son la garantía final.
- **Todavía no hay inicio de sesión.** El operador se carga con datos de prueba, y el login llega en la Iteración 2.

## Cómo ejecutarlo

Los comandos son para PowerShell en Windows. Necesitas Python 3.13 o superior, Node.js 24 (versión 24.15 o más) y PostgreSQL.

### 1. Base de datos

1. Crea en PostgreSQL una base de datos llamada `autos_colombia`. Las pruebas de integración comprueban ese nombre.
2. En la carpeta `backend`, copia la plantilla y complétala con tus datos:

```powershell
Copy-Item .env.example .env
```

   Edita `backend/.env` y completa `DB_NAME`, `DB_USER` y `DB_PASSWORD`. Ese archivo es privado y está excluido de Git: nunca lo subas.

### 2. Backend

En la carpeta `backend`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_db.py
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En orden, esos comandos: crean el entorno virtual, instalan las dependencias, comprueban la conexión, crean las tablas, cargan los datos de prueba y encienden la API.

- La salud de la API: <http://127.0.0.1:8000/health>
- La documentación interactiva, donde se puede probar cada ruta: <http://127.0.0.1:8000/docs>

`seed.py` solo inserta datos y se puede ejecutar varias veces sin duplicar nada. Carga 10 vehículos (4 automóviles, 1 camioneta y 5 motos), 10 celdas y 1 operador.

### 3. Frontend

En otra terminal, en la carpeta `frontend`:

```powershell
npm.cmd ci
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Abre <http://127.0.0.1:4200>. En la pantalla de inicio debe aparecer "Servicio disponible", que confirma que el frontend se comunica con el backend.

## Rutas de la API

Estas son las de esta iteración, todas bajo `/estancias`:

| Método y ruta | Qué hace | Respuesta |
|---|---|---|
| `POST /estancias/entrada` | Registra una entrada. Recibe `placa` y `operador_id`; `celda_id` es opcional | 201 |
| `POST /estancias/salida` | Registra una salida. Recibe `placa` y `operador_id` | 200 |
| `GET /estancias/vehiculo/{placa}` | Estado de un vehículo: si está dentro y en qué celda | 200 |
| `GET /estancias/dentro` | Vehículos que están dentro | 200 |
| `GET /estancias/historial` | Historial. Filtros opcionales: `placa`, `desde`, `hasta` (formato `AAAA-MM-DD`) | 200 |
| `GET /estancias/celdas` | Celdas con su estado y los totales | 200 |

Los listados se paginan con `offset` y `limit` (de 1 a 100). Los errores usan estos códigos: 404 si algo no existe, 409 si hay un conflicto (por ejemplo, el vehículo ya está dentro o no hay celdas), 422 si los datos no son válidos y 503 si falla la base de datos.

La base del profesor también incluye el CRUD de `/vehiculos`, `/celdas` y `/operadores`.

## Pruebas

En la carpeta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Esto corre las pruebas que no necesitan la base de datos. Para correr **todas**, incluidas las de integración con PostgreSQL, que crean datos temporales y los revierten o borran al terminar:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_POSTGRES_TESTS
```

En la última ejecución completa pasaron 143 pruebas. Las de integración exigen que la base se llame `autos_colombia` y esté en la revisión `0002`.

## Estado

| Parte | Estado |
|---|---|
| Base de datos y migraciones | Listo |
| Backend de la Iteración 1 | Listo, con pruebas |
| Pantallas de Entrada, Salida, Dentro, Historial y Celdas | En construcción |

## Iteraciones del proyecto

1. **Iteración 1** (este repositorio): entrada y salida de vehículos.
2. **Iteración 2:** gestión de usuarios y celdas, con inicio de sesión.
3. **Iteración 3:** pagos.

Las novedades sobre los vehículos también quedan para una iteración posterior.
