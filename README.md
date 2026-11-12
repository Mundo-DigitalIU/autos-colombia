# Autos Colombia

Sistema de información para el parqueadero "Autos Colombia", un parqueadero que presta el servicio por mensualidad.

Este repositorio reúne las **Iteraciones 1 y 2** del proyecto de Ingeniería de Software de la IU Digital de Antioquia:

1. **Iteración 1:** gestión de la entrada y salida de vehículos.
2. **Iteración 2:** inicio de sesión con roles, cuentas de usuario, clientes con sus vehículos y administración de celdas.

**Autor:** Jeferson Cataño C - David Castro M - Katherine

## Tabla de contenido

- [Qué hace el sistema](#qué-hace-el-sistema)
- [Cómo iniciar el proyecto](#cómo-iniciar-el-proyecto)
- [Usar la aplicación](#usar-la-aplicación)
- [Roles y permisos](#roles-y-permisos)
- [Rutas de la API](#rutas-de-la-api)
- [Pantallas del frontend](#pantallas-del-frontend)
- [Pruebas](#pruebas)
- [Estructura, modelo de datos y decisiones](#estructura-del-repositorio)
- [Estado e iteraciones](#estado)

## Qué hace el sistema

### Iteración 1: entrada y salida

| Función | Requisito | Cómo funciona |
|---|---|---|
| Registrar la entrada | RF-01 a RF-04 | El operador escribe la placa. El sistema la normaliza, revisa que el vehículo esté registrado y que no esté ya dentro. |
| Asignar la celda | RF-05 | Si no se indica una celda, el sistema elige la primera libre del mismo tipo del vehículo. |
| Registrar la salida | RF-06, RF-07 | Se guarda la hora de salida y la celda queda libre. |
| Ver los vehículos dentro | RF-08 | Lista de los vehículos con una estancia abierta, con su celda y su hora de entrada. |
| Ver el historial | RF-09 | Entradas y salidas, filtradas por placa y por rango de fechas. |
| Ver las celdas | RF-11 | Cada celda con su estado (`DISPONIBLE` u `OCUPADA`) y los totales. |

Cuando algo no se puede hacer (vehículo no registrado, ya está dentro, no hay celdas), el sistema responde con un mensaje claro en español (RF-10).

### Iteración 2: sesiones, roles, clientes y celdas

| Función | Cómo funciona |
|---|---|
| Inicio de sesión | Cada persona entra con su usuario y contraseña. La sesión dura 8 horas y se puede cerrar antes. |
| Roles | `OPERADOR` y `ADMINISTRADOR`. Cada pantalla y cada ruta de la API revisa el rol. |
| Cuentas | El administrador crea y elimina cuentas. Al crear una cuenta se crea también su perfil de operador. |
| Clientes | Se registra un cliente con uno o varios vehículos. Se busca por documento, nombre o placa. |
| Gestión de celdas | El administrador crea, edita y elimina celdas, y las filtra por código, tipo y estado. |
| Operador de la sesión | Al registrar una entrada o una salida, el operador es el de la persona que tiene la sesión abierta. |

**No incluye todavía:** pagos ni novedades sobre los vehículos (iteraciones posteriores).

## Cómo iniciar el proyecto

Los comandos son para **PowerShell en Windows**. Antes de empezar necesitas instalado:

- **Python 3.13** o superior.
- **Node.js 24** (versión 24.15 o más) con npm.
- **PostgreSQL**, con un servidor local en marcha.

El proyecto se levanta con **dos terminales abiertas a la vez**: una para el backend (la API) y otra para el frontend (las pantallas).

### Primera vez (instalación)

**1. Base de datos.** En PostgreSQL crea una base de datos llamada `autos_colombia` (las pruebas de integración comprueban ese nombre). Después, en la carpeta `backend`, copia la plantilla de configuración:

```powershell
cd backend
Copy-Item .env.example .env
```

Abre `backend/.env` y completa `DB_NAME`, `DB_USER` y `DB_PASSWORD` con los datos de tu PostgreSQL. Ese archivo es privado y está excluido de Git: nunca lo subas.

**2. Backend.** En la carpeta `backend`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_db.py
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

En orden, esos comandos crean el entorno virtual, instalan las dependencias, comprueban la conexión (`check_db.py` debe decir "Conexión a PostgreSQL verificada") y crean las tablas (migraciones `0001` a `0003`).

**3. Datos de prueba y cuentas.** Todavía en `backend`, carga las celdas, los vehículos, los clientes de ejemplo y las cuentas `admin` y `operador`. Elige tus propias contraseñas (mínimo 8 caracteres); el comando te las pide sin mostrarlas:

```powershell
$env:SEED_ADMIN_CLAVE = Read-Host 'Contraseña de admin'
$env:SEED_OPERADOR_CLAVE = Read-Host 'Contraseña de operador'
.\.venv\Scripts\python.exe seed.py
Remove-Item Env:SEED_ADMIN_CLAVE, Env:SEED_OPERADOR_CLAVE
```

Si no defines las variables, el seed genera una contraseña aleatoria para cada cuenta y la muestra **una sola vez** en pantalla: anótala en ese momento, porque en la base solo queda su hash. `seed.py` solo inserta datos y se puede ejecutar varias veces sin duplicar nada; una cuenta que ya existe conserva su contraseña.

**4. Frontend.** En la carpeta `frontend`:

```powershell
cd ..\frontend
npm.cmd ci
```

### Cada vez que quieras ejecutarlo

**Terminal 1, backend** (desde la carpeta `backend`):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2, frontend** (desde la carpeta `frontend`):

```powershell
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Espera a que el frontend termine de compilar y abre <http://127.0.0.1:4200>. Verás la pantalla **Iniciar sesión**: entra con `admin` u `operador` y la contraseña que definiste en el paso 3.

| Dirección | Qué es |
|---|---|
| <http://127.0.0.1:4200> | La aplicación (frontend) |
| <http://127.0.0.1:8000/health> | Salud de la API: responde `{"status":"ok"}` |
| <http://127.0.0.1:8000/docs> | Documentación interactiva de la API (las rutas piden sesión, salvo el login) |

Para **detener** el proyecto, pulsa `Ctrl + C` en cada terminal. Para **reiniciarlo**, vuelve a ejecutar los dos comandos de arriba. Si cambias `frontend/proxy.conf.json` hay que reiniciar el frontend, porque el proxy no se recarga solo.

### Si algo falla

| Síntoma | Qué revisar |
|---|---|
| `check_db.py` no conecta | PostgreSQL está en marcha y `backend/.env` tiene los datos correctos. |
| El login responde "Usuario o contraseña incorrectos." | Ejecutaste `seed.py` (paso 3) y usas la contraseña que definiste. Si no recuerdas una generada, crea una cuenta nueva desde otra cuenta de administrador. |
| La API responde 500 o 503 tras actualizar el código | Falta aplicar las migraciones: `alembic upgrade head` (paso 2). |
| "Address already in use" en el puerto 8000 o 4200 | Queda un servidor anterior abierto. Ciérralo o espera unos segundos a que Windows libere el puerto. |
| Las pantallas muestran "No se pudo conectar con el servicio" | El backend (terminal 1) no está corriendo. |
| `Tu sesión terminó. Inicia sesión otra vez.` | La sesión venció (8 horas) o se cerró; vuelve a iniciar sesión. |

## Usar la aplicación

1. Entra con `operador` para el trabajo diario del parqueadero: **Entrada** y **Salida** (escribes la placa), **Dentro**, **Historial**, **Celdas** (solo consulta) y **Clientes**.
2. Entra con `admin` para además crear cuentas (**Cuentas**) y administrar las celdas (**Gestionar celdas**). El administrador también puede editar y eliminar clientes.
3. Con las celdas y vehículos del seed, prueba así: en **Entrada** escribe la placa `ABC123`; el sistema asigna la primera celda libre de automóvil. En **Dentro** aparece el vehículo; en **Salida** escribe la misma placa y la celda queda libre. El resultado queda en **Historial**.
4. El botón **Cerrar sesión** (arriba a la derecha) revoca la sesión y vuelve al login.

## Roles y permisos

| Rol | Puede |
|---|---|
| `OPERADOR` | Registrar entradas y salidas, consultar estancias, historial y celdas, y registrar y consultar clientes y vehículos. |
| `ADMINISTRADOR` | Todo lo anterior, más: gestionar cuentas (`/cuentas`) y operadores (`/operadores`), crear, editar y eliminar celdas, y modificar o eliminar clientes y vehículos. |

Sin sesión o con la sesión vencida la API responde 401 (`Tu sesión terminó. Inicia sesión otra vez.`); con un rol insuficiente, 403 (`No tienes permiso para entrar aquí.`). En el frontend, un operador que entra a una pantalla de administrador ve la pantalla **Sin permiso**.

## Rutas de la API

Todas las rutas exigen sesión (`Authorization: Bearer <token>`), salvo `POST /auth/login` y `GET /health`.

### Iteración 1: estancias

| Método y ruta | Qué hace | Respuesta |
|---|---|---|
| `POST /estancias/entrada` | Registra una entrada. Recibe `placa`; `celda_id` es opcional. El operador es el de la sesión | 201 |
| `POST /estancias/salida` | Registra una salida. Recibe `placa`. El operador es el de la sesión | 200 |
| `GET /estancias/vehiculo/{placa}` | Estado de un vehículo: si está dentro y en qué celda | 200 |
| `GET /estancias/dentro` | Vehículos que están dentro | 200 |
| `GET /estancias/historial` | Historial. Filtros opcionales: `placa`, `desde`, `hasta` (formato `AAAA-MM-DD`) | 200 |
| `GET /estancias/celdas` | Celdas con su estado y los totales. Filtros opcionales: `q` (código), `tipo` y `estado` | 200 |

### Iteración 2: sesión, cuentas, clientes y celdas

| Método y ruta | Rol | Qué hace |
|---|---|---|
| `POST /auth/login` | público | Recibe `usuario` y `contrasena`; devuelve `token`, `rol`, `nombre` y `expira`. 401 si no coinciden |
| `POST /auth/logout` | cualquiera | Revoca la sesión actual |
| `POST /cuentas`, `GET /cuentas?q=`, `DELETE /cuentas/{id}` | administrador | Crea (operador y usuario en una transacción), lista y elimina cuentas. No se puede eliminar la propia |
| `POST /clientes`, `GET /clientes?q=`, `GET /clientes/{id}` | ambos | Registra un cliente con sus vehículos, busca por documento, nombre o placa y consulta |
| `PUT /clientes/{id}`, `DELETE /clientes/{id}`, `DELETE /clientes/{id}/vehiculos/{vehiculo_id}` | administrador | Edita, y elimina solo si los vehículos no tienen estancias |
| `GET /celdas`, `GET /celdas/{id}` | ambos | Lista y consulta celdas |
| `POST /celdas`, `PATCH /celdas/{id}`, `DELETE /celdas/{id}` | administrador | Crea, edita (el tipo no cambia mientras está ocupada) y elimina (solo sin historial) |

Notas:

- El tipo de una celda solo puede ser `MOTO`, `AUTOMOVIL` o `CAMIONETA`, y al registrar una entrada con `celda_id` la celda debe ser del tipo del vehículo.
- En `PUT /clientes/{id}` los vehículos con `id` se editan y los que no lo traen se crean; los que no aparecen en la lista se conservan.
- La base del profesor también incluye el CRUD de `/vehiculos` y `/operadores`; ahora exigen sesión, y `/operadores` es solo del administrador.
- Los listados se paginan con `offset` y `limit` (de 1 a 100).
- Los errores salen como `{"detail": "mensaje"}` con estos códigos: 401 sin sesión, 403 sin permiso, 404 si algo no existe, 409 si hay un conflicto (por ejemplo, el vehículo ya está dentro o la celda ya existe), 422 si los datos no son válidos y 503 si falla la base de datos.

Ejemplo de inicio de sesión desde PowerShell:

```powershell
$clave = Read-Host 'Contraseña' -AsSecureString
$cuerpo = @{ usuario = 'admin'; contrasena = [System.Net.NetworkCredential]::new('', $clave).Password } | ConvertTo-Json
$sesion = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/auth/login -ContentType 'application/json' -Body $cuerpo
Invoke-RestMethod -Uri http://127.0.0.1:8000/estancias/dentro -Headers @{ Authorization = "Bearer $($sesion.token)" }
```

## Pantallas del frontend

Sin sesión, cualquier pantalla lleva a `/login`. Con sesión, el menú superior muestra el nombre, el rol y el botón **Cerrar sesión**. Si la API responde 401 se borra la sesión y se vuelve a `/login` con "Tu sesión terminó. Inicia sesión otra vez."; si responde 403 se muestra "No tienes permiso para entrar aquí.". El token se guarda en `sessionStorage` (solo dura mientras la pestaña esté abierta) y un interceptor lo envía en `Authorization: Bearer`.

| Ruta | Pantalla | Quién entra |
|---|---|---|
| `/login` | Iniciar sesión | Público |
| `/entrada`, `/salida` | Registrar entrada y salida (el operador es el de la sesión) | Ambos roles |
| `/dentro`, `/historial` | Vehículos dentro e historial | Ambos roles |
| `/estado-celdas` | Estado de las celdas, solo consulta | Ambos roles |
| `/panel/clientes` | Clientes: buscar y registrar con uno o varios vehículos; editar y eliminar solo el administrador | Ambos roles |
| `/panel/cuentas` | Cuentas: lista, crear y eliminar | Administrador |
| `/panel/celdas` | Gestionar celdas: buscar, filtrar por tipo y estado, crear, editar y eliminar | Administrador |
| `/sin-permiso` | Aviso que ve un operador que entra a una ruta de administrador | Con sesión |
| `/inicio` | Estado de la conexión con la API ("Servicio disponible") | Con sesión |

El menú del operador es Entrada, Salida, Dentro, Historial, Celdas y Clientes; el del administrador añade Cuentas y Gestionar celdas. Las rutas `/panel/*` se llaman así para no chocar con los prefijos que el proxy de desarrollo (`frontend/proxy.conf.json`) envía a la API: `/estancias`, `/celdas`, `/vehiculos`, `/operadores`, `/auth`, `/cuentas`, `/clientes` y `/health`.

## Pruebas

**Backend**, en la carpeta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Esto corre las pruebas que no necesitan la base de datos. Para correr **todas**, incluidas las de integración con PostgreSQL (crean datos temporales y los revierten o borran al terminar):

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_POSTGRES_TESTS
```

Las de integración exigen que la base se llame `autos_colombia` y esté en la revisión `0003`.

**Frontend**, en la carpeta `frontend`:

```powershell
npm.cmd test -- --watch=false
npm.cmd run build
```

En la última ejecución completa pasaron las 223 pruebas del backend (187 sin PostgreSQL; las 36 restantes son de integración) y las 146 del frontend, y la compilación del frontend terminó sin errores.

## Estructura del repositorio

```text
AutosColombia/
├── backend/
│   ├── app/
│   │   ├── main.py          # Aplicación FastAPI y GET /health
│   │   ├── config.py        # Lee la configuración de backend/.env
│   │   ├── database.py      # Motor y sesiones de SQLAlchemy
│   │   ├── models.py        # Tablas: Vehiculo, Celda, Operador, Estancia, Cliente, Usuario y Sesion
│   │   ├── security.py      # Contraseñas con scrypt y tokens de sesión
│   │   ├── auth.py          # Dependencias de sesión y de rol
│   │   ├── routers/         # Las rutas de la API
│   │   ├── services/        # La lógica del negocio
│   │   └── schemas/         # Validación y respuestas (Pydantic)
│   ├── migrations/          # Migraciones de Alembic (0001, 0002 y 0003)
│   ├── tests/               # Pruebas con pytest
│   ├── seed.py              # Datos de prueba y cuentas iniciales
│   ├── check_db.py          # Comprueba la conexión a PostgreSQL
│   ├── requirements.txt
│   └── .env.example         # Plantilla de configuración (sin datos reales)
└── frontend/
    ├── proxy.conf.json      # Proxy de desarrollo hacia la API
    └── src/app/             # Pantallas, servicios, guards y modelos de Angular
```

## Tecnologías

| Parte | Tecnología |
|---|---|
| Base de datos | PostgreSQL |
| Backend | Python con FastAPI, SQLAlchemy 2, Alembic y psycopg |
| Frontend | Angular 22 con TypeScript |
| Pruebas | pytest (backend) y Vitest (frontend) |

Las versiones exactas están en `backend/requirements.txt` y `frontend/package.json`.

## Modelo de datos

| Tabla | Columnas principales |
|---|---|
| `vehiculo` | `id`, `placa` (única), `color`, `modelo`, `marca`, `tipo` (MOTO, AUTOMOVIL o CAMIONETA), `cliente_id` (opcional) |
| `celda` | `id`, `codigo` (único), `tipo` (MOTO, AUTOMOVIL o CAMIONETA en los datos nuevos) |
| `operador` | `id`, `nombre`, `telefono` |
| `estancia` | `id`, `vehiculo_id`, `celda_id`, `entrada`, `salida`, `operador_entrada_id`, `operador_salida_id` |
| `cliente` | `id`, `nombre`, `documento` (único), `telefono` |
| `usuario` | `id`, `nombre_usuario` (único, en minúsculas), `clave_hash`, `rol` (ADMINISTRADOR u OPERADOR), `operador_id` (único) |
| `sesion` | `id`, `usuario_id`, `token_hash` (único), `creada`, `expira`, `revocada` |

`estancia` guarda cada vez que un vehículo entra y sale. Mientras el vehículo sigue dentro, `salida` y `operador_salida_id` están vacíos.

La base protege las reglas del negocio:

- Un vehículo no puede tener dos estancias abiertas, y una celda tampoco (índices únicos que solo miran las estancias sin salida).
- La salida no puede ser anterior a la entrada, y la salida y el operador de salida van juntos.
- No se puede borrar un vehículo, una celda o un operador que ya tenga estancias.
- Un cliente solo se borra si ninguno de sus vehículos tiene estancias; borrar una cuenta elimina sus sesiones pero conserva al operador para el historial.
- La migración `0003` añade la restricción del tipo de celda como `NOT VALID`: no revisa las filas que ya existían (por ejemplo `Libre`), solo las inserciones y cambios nuevos.

Para revisar el SQL de las migraciones sin tocar la base: `.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head --sql`.

## Decisiones de diseño

- **El estado de una celda no se guarda, se calcula.** Una celda está ocupada si tiene una estancia abierta. Así no puede quedar desactualizado.
- **Las fechas se guardan en UTC**, pero el historial cuenta los días en hora de Bogotá (UTC-5), y el frontend las muestra en `America/Bogota`.
- **La asignación de celda es segura con entradas simultáneas.** La consulta usa `SKIP LOCKED`, y los índices únicos de la base son la garantía final.
- **Contraseñas y sesiones.** Las contraseñas se guardan con `scrypt` y sal aleatoria. De cada sesión solo se guarda el SHA-256 del token, que vence a las 8 horas. El login responde igual y tarda parecido si el usuario no existe o la contraseña es mala.
- **El operador sale de la sesión.** El servidor toma el operador de la sesión; el cuerpo de entrada y salida ya no lo recibe, así nadie puede registrar un movimiento a nombre de otra persona.
- **Ninguna contraseña vive en el código.** El seed las lee del entorno o las genera una sola vez.

## Estado

| Parte | Estado |
|---|---|
| Base de datos y migraciones (0001 a 0003) | Listo |
| Backend de la Iteración 1 | Listo, con pruebas |
| Backend de la Iteración 2 (sesiones, roles, cuentas, clientes, celdas) | Listo, con pruebas |
| Frontend de la Iteración 1 (Entrada, Salida, Dentro, Historial y Celdas) | Listo, con inicio de sesión |
| Frontend de la Iteración 2 (login, roles, cuentas, clientes y gestión de celdas) | Listo, con pruebas |

## Iteraciones del proyecto

1. **Iteración 1:** entrada y salida de vehículos.
2. **Iteración 2:** inicio de sesión con roles, cuentas, clientes con vehículos y administración de celdas.
3. **Iteración 3:** pagos.

Las novedades sobre los vehículos también quedan para una iteración posterior.
