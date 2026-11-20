# Autos Colombia

Sistema de información para el parqueadero "Autos Colombia", un parqueadero que presta el servicio por mensualidad.

Este repositorio reúne las **Iteraciones 1, 2 y 3** del proyecto de Ingeniería de Software de la IU Digital de Antioquia:

1. **Iteración 1:** gestión de la entrada y salida de vehículos.
2. **Iteración 2:** inicio de sesión con roles, cuentas de usuario, clientes con sus vehículos y administración de celdas.
3. **Iteración 3:** pagos de la mensualidad de cada vehículo, con tarifas, vigencia, comprobante y anulación.

**Autor:** Jeferson Cataño C - David Castro M - Katherine

## Tabla de contenido

- [Qué hace el sistema](#qué-hace-el-sistema)
- [Cómo iniciar el proyecto](#cómo-iniciar-el-proyecto)
- [Usar la aplicación](#usar-la-aplicación)
- [Roles y permisos](#roles-y-permisos)
- [Pagos y mensualidades](#pagos-y-mensualidades)
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

### Iteración 3: pagos de la mensualidad

| Función | Cómo funciona |
|---|---|
| Registrar un pago | El operador escribe la placa y el medio de pago (`EFECTIVO`, `TRANSFERENCIA` o `TARJETA`). El valor lo pone el servidor según la tarifa del tipo de vehículo. |
| Vigencia | Cada pago da 30 días de mensualidad, contados desde la fecha de corte del vehículo (ver [Pagos y mensualidades](#pagos-y-mensualidades)). |
| Estado de la mensualidad | Cada vehículo con cliente está `AL_DIA`, `VENCIDA` o `SIN_PAGOS`. |
| Comprobante | Cada pago tiene su comprobante con número, fecha, cliente, valor, medio y vigencia. |
| Anular un pago | Solo el administrador, con un motivo obligatorio. El pago no se borra: queda `ANULADO`. |

Los pagos no cambian nada de la entrada y la salida de vehículos.

**No incluye todavía:** novedades sobre los vehículos (iteración posterior). Las tarifas no tienen pantalla: se cargan con el seed.

## Cómo iniciar el proyecto

Los comandos son para **PowerShell en Windows**. Antes de empezar necesitas instalado:

- **Python 3.13** o superior.
- **Node.js 24** (versión 24.15 o más) con npm.
- **PostgreSQL**, con un servidor local en marcha.

El proyecto se levanta con **dos terminales abiertas a la vez**: una para el backend (la API) y otra para el frontend (las pantallas).

### Primera vez (instalación)

**1. Base de datos.** Comprueba que PostgreSQL está en marcha: `Test-NetConnection 127.0.0.1 -Port 5432` debe mostrar `TcpTestSucceeded : True` (si usas otro puerto, ajústalo en `DB_PORT` del `.env`). En PostgreSQL crea una base de datos llamada `autos_colombia` (las pruebas de integración comprueban ese nombre). Después, en la carpeta `backend`, copia la plantilla de configuración:

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

En orden, esos comandos crean el entorno virtual, instalan las dependencias, comprueban la conexión (`check_db.py` debe decir "Conexión a PostgreSQL verificada") y crean las tablas (migraciones `0001` a `0004`; la `0004` añade `tarifa` y `pago`). Para comprobar que la base quedó al día: `.\.venv\Scripts\python.exe -m alembic -c alembic.ini current` debe responder `0004 (head)`.

**3. Datos de prueba y cuentas.** Todavía en `backend`, carga las celdas, los vehículos, los clientes de ejemplo, las tres tarifas, dos pagos de ejemplo y las cuentas `admin` y `operador`. Elige tus propias contraseñas (mínimo 8 caracteres); el comando te las pide sin mostrarlas:

```powershell
$env:SEED_ADMIN_CLAVE = Read-Host 'Contraseña de admin'
$env:SEED_OPERADOR_CLAVE = Read-Host 'Contraseña de operador'
.\.venv\Scripts\python.exe seed.py
Remove-Item Env:SEED_ADMIN_CLAVE, Env:SEED_OPERADOR_CLAVE
```

Si no defines las variables, el seed genera una contraseña aleatoria para cada cuenta y la muestra **una sola vez** en pantalla: anótala en ese momento, porque en la base solo queda su hash. `seed.py` solo inserta datos y se puede ejecutar varias veces sin duplicar nada; una cuenta que ya existe conserva su contraseña, y una tarifa que ya existe conserva su valor.

Las tarifas que carga el seed (pesos por mes) están en la constante `TARIFAS` al inicio de `backend/seed.py`:

| Tipo | Tarifa mensual |
|---|---|
| `MOTO` | $100.000 |
| `AUTOMOVIL` | $250.000 |
| `CAMIONETA` | $250.000 |

Si quieres otros valores, cámbialos en esa constante **antes** de la primera vez que corras el seed: después, el seed no modifica una tarifa que ya existe (se cambia directamente en la tabla `tarifa`). Sin tarifas, registrar un pago responde 409 "No hay una tarifa configurada para este tipo de vehículo.".

El seed también deja **dos pagos de ejemplo** a nombre del administrador, en clientes distintos, calculados con la fecha del día en que lo corres: uno de hace 10 días (queda `AL_DIA`) y otro de hace 45 días (queda `VENCIDA`). Los demás vehículos con cliente quedan `SIN_PAGOS`, así que la pantalla de pagos muestra los tres estados. Si un vehículo ya tiene algún pago, el seed no le agrega otro. Si no hay clientes con vehículo suficientes, crea dos clientes ficticios (`Cliente Demo Uno` y `Cliente Demo Dos`) sin tocar los existentes.

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
| Al registrar un pago sale "No hay una tarifa configurada para este tipo de vehículo." | Falta cargar las tarifas: ejecuta `seed.py` (paso 3). |
| `/pagos` responde 404 o la pantalla de pagos no carga datos | El backend o el frontend se iniciaron antes de actualizar el código: ciérralos y vuelve a iniciarlos. |
| "Address already in use" en el puerto 8000 o 4200 | Queda un servidor anterior abierto. Ciérralo o espera unos segundos a que Windows libere el puerto. |
| Las pantallas muestran "No se pudo conectar con el servicio" | El backend (terminal 1) no está corriendo. |
| `Tu sesión terminó. Inicia sesión otra vez.` | La sesión venció (8 horas) o se cerró; vuelve a iniciar sesión. |

## Usar la aplicación

1. Entra con `operador` para el trabajo diario del parqueadero: **Entrada** y **Salida** (escribes la placa), **Dentro**, **Historial**, **Celdas** (solo consulta) y **Clientes**.
2. Entra con `admin` para además crear cuentas (**Cuentas**) y administrar las celdas (**Gestionar celdas**). El administrador también puede editar y eliminar clientes.
3. Con las celdas y vehículos del seed, prueba así: en **Entrada** escribe la placa `ABC123`; el sistema asigna la primera celda libre de automóvil. En **Dentro** aparece el vehículo; en **Salida** escribe la misma placa y la celda queda libre. El resultado queda en **Historial**.
4. Para probar los pagos, abre **Pagos**: en **Mensualidades** verás un vehículo `AL_DIA`, uno `VENCIDA` y el resto `SIN_PAGOS`. Pulsa **Registrar pago** en una fila (la placa ya queda escrita), elige el medio de pago y **Guardar pago**: se abre el comprobante. En **Pagos registrados** puedes ver el comprobante de cualquier pago y, con `admin`, anular el último pago de un vehículo escribiendo el motivo.
5. El botón **Cerrar sesión** (arriba a la derecha) revoca la sesión y vuelve al login.

## Roles y permisos

| Rol | Puede |
|---|---|
| `OPERADOR` | Registrar entradas y salidas, consultar estancias, historial y celdas, registrar y consultar clientes y vehículos, y registrar y consultar pagos y sus comprobantes. |
| `ADMINISTRADOR` | Todo lo anterior, más: gestionar cuentas (`/cuentas`) y operadores (`/operadores`), crear, editar y eliminar celdas, modificar o eliminar clientes y vehículos, y anular pagos. |

Sin sesión o con la sesión vencida la API responde 401 (`Tu sesión terminó. Inicia sesión otra vez.`); con un rol insuficiente, 403 (`No tienes permiso para entrar aquí.`). En el frontend, un operador que entra a una pantalla de administrador ve la pantalla **Sin permiso**.

## Pagos y mensualidades

Reglas de negocio de la Iteración 3:

- **Qué se paga.** La mensualidad de **un vehículo**, y el vehículo debe pertenecer a un cliente.
- **Valor.** Una tarifa mensual fija por tipo de vehículo (`MOTO`, `AUTOMOVIL`, `CAMIONETA`). El servidor pone el valor; la solicitud no lo envía. El pago guarda una **copia** del valor: si la tarifa cambia después, los pagos viejos no cambian.
- **Vigencia de 30 días desde la fecha de corte.** Cada pago guarda `vigencia_desde` y `vigencia_hasta`, con `vigencia_hasta = vigencia_desde + 30 días`.
  - Si el vehículo nunca ha tenido un pago vigente (`REGISTRADO`), `vigencia_desde` es la fecha del pago, en hora de Bogotá.
  - Si ya tiene pagos, `vigencia_desde` es la `vigencia_hasta` del último pago vigente. La mensualidad se cuenta desde la fecha de corte anterior aunque el cliente pague tarde: no se reinicia el día del pago.
  - Ejemplo: pagó el 1 de septiembre (vigencia hasta el 1 de octubre). Si vuelve a pagar el 1 de diciembre, esa nueva vigencia va del 1 al 31 de octubre y el vehículo sigue `VENCIDA` hasta que pague los periodos que le faltan.
- **Pago repetido.** No se registra un pago si la vigencia del vehículo ya llega 30 días o más hacia adelante contando desde hoy: ya está pagada (409). El cálculo y la verificación bloquean la fila del vehículo dentro de la misma transacción, así que dos solicitudes simultáneas no crean dos pagos.
- **Estado de la mensualidad.** `AL_DIA` si hoy es menor o igual a la `vigencia_hasta` del último pago vigente; `VENCIDA` si hoy es posterior; `SIN_PAGOS` si nunca ha tenido un pago vigente.
- **Anular.** Solo el administrador, con motivo obligatorio. El pago no se borra: queda `ANULADO` con quién lo anuló, cuándo y el motivo. Solo se puede anular el **último** pago vigente de cada vehículo, y al anularlo la vigencia vuelve a la del pago anterior (o a `SIN_PAGOS` si no hay otro).
- **Sin cambios en la Iteración 1.** Un vehículo con la mensualidad vencida igual puede entrar y salir.

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

### Iteración 3: pagos

| Método y ruta | Rol | Qué hace |
|---|---|---|
| `POST /pagos` | ambos | Registra el pago. Cuerpo: `{"placa", "medio_pago"}`. El operador es el de la sesión y el valor sale de la tarifa; si el cuerpo trae `operador_id` o `valor`, 422. Responde **201** con el pago completo |
| `GET /pagos` | ambos | Lista de pagos, el más reciente primero. Filtros: `q` (documento, nombre del cliente o placa), `estado` (`REGISTRADO` o `ANULADO`), `desde` y `hasta` (fecha de pago, `AAAA-MM-DD`; 422 si `desde` es mayor que `hasta`) |
| `GET /pagos/estado` | ambos | Un elemento por vehículo con cliente: `placa`, `tipo`, `cliente_nombre`, `cliente_documento`, `tarifa`, `estado` (`AL_DIA`, `VENCIDA` o `SIN_PAGOS`), `vigencia_hasta` (nulo si no tiene pagos) y `ultimo_pago_id`. Filtros: `q` y `estado` |
| `GET /pagos/{id}` | ambos | El comprobante del pago |
| `POST /pagos/{id}/anular` | administrador | Cuerpo: `{"motivo"}`. Responde 200 con el pago ya anulado |

No hay `DELETE` ni `PUT` en `/pagos`. `GET /pagos/estado` está declarado antes de `/pagos/{id}`. Las listas se paginan igual que las demás (`offset` y `limit`).

El pago y el comprobante tienen estos campos: `id` (el número del comprobante), `fecha_pago` (con hora, en hora de Bogotá), `cliente_nombre`, `cliente_documento`, `placa`, `tipo`, `valor`, `medio_pago`, `vigencia_desde`, `vigencia_hasta`, `registrado_por`, `estado` y, si está anulado, `motivo_anulacion`, `anulado_por` y `anulado_en` (si no, son nulos).

Mensajes de error de `/pagos` (siempre `{"detail": "mensaje"}`):

| Código | Mensaje | Cuándo |
|---|---|---|
| 404 | `Vehículo no encontrado.` | `POST /pagos` con una placa que no existe |
| 409 | `El vehículo no tiene un cliente asociado.` | `POST /pagos` de un vehículo sin cliente |
| 409 | `La mensualidad de este vehículo ya está pagada.` | `POST /pagos` cuando la vigencia ya llega 30 días o más hacia adelante, o dos solicitudes simultáneas |
| 409 | `No hay una tarifa configurada para este tipo de vehículo.` | `POST /pagos` si el tipo no tiene tarifa (falta cargar el seed) |
| 404 | `Pago no encontrado.` | Consultar o anular un pago que no existe |
| 409 | `El pago ya está anulado.` | Anular un pago `ANULADO` |
| 409 | `Solo se puede anular el último pago del vehículo.` | Anular un pago que no es el último vigente de su vehículo |
| 422 | `Escribe el motivo de la anulación.` | Anular con el motivo vacío, solo espacios o ausente |
| 422 | (detalle de validación) | Falta la placa o el medio de pago, o el medio no es `EFECTIVO`, `TRANSFERENCIA` o `TARJETA` |
| 401 / 403 | `Tu sesión terminó. Inicia sesión otra vez.` / `No tienes permiso para entrar aquí.` | Sin sesión; o un operador que intenta anular |

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
| `/panel/pagos` | Pagos, con dos pestañas: **Mensualidades** (estado de cada vehículo, buscador, filtro por estado y botón Registrar pago) y **Pagos registrados** (lista con filtros por texto, estado y fechas, Ver comprobante, y Anular solo para el administrador) | Ambos roles (anular: administrador) |
| `/panel/pagos/registrar` | Registrar pago: placa y medio de pago; muestra cliente, tipo, tarifa y la vigencia que quedaría (es una ayuda: la que vale es la del servidor). Acepta `?placa=` para abrir con la placa escrita | Ambos roles |
| `/panel/pagos/comprobante/:id` | Comprobante de un pago con su número de 6 dígitos (`000184`), la hora en formato de 12 horas y, si fue anulado, la franja ANULADO con el motivo, quién y cuándo | Ambos roles |
| `/panel/cuentas` | Cuentas: lista, crear y eliminar | Administrador |
| `/panel/celdas` | Gestionar celdas: buscar, filtrar por tipo y estado, crear, editar y eliminar | Administrador |
| `/sin-permiso` | Aviso que ve un operador que entra a una ruta de administrador | Con sesión |
| `/inicio` | Estado de la conexión con la API ("Servicio disponible") | Con sesión |

El menú del operador es Entrada, Salida, Dentro, Historial, Celdas, Clientes y Pagos; el del administrador añade Cuentas y Gestionar celdas. Las rutas `/panel/*` se llaman así para no chocar con los prefijos que el proxy de desarrollo (`frontend/proxy.conf.json`) envía a la API: `/estancias`, `/celdas`, `/vehiculos`, `/operadores`, `/auth`, `/cuentas`, `/clientes`, `/pagos` y `/health`. Las fechas se muestran como `dd/mm/aaaa` y los valores en pesos con separador de miles (por ejemplo `$250.000`).

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

Las de integración exigen que la base se llame `autos_colombia` y esté en la revisión `0004`.

**Frontend**, en la carpeta `frontend`:

```powershell
npm.cmd test -- --watch=false
npm.cmd run build
```

En la última ejecución completa pasaron las 258 pruebas del backend (203 sin PostgreSQL; las 55 restantes son de integración) y las 198 del frontend, y la compilación del frontend (`npm.cmd run build`) terminó sin errores ni avisos.

## Estructura del repositorio

```text
AutosColombia/
├── backend/
│   ├── app/
│   │   ├── main.py          # Aplicación FastAPI y GET /health
│   │   ├── config.py        # Lee la configuración de backend/.env
│   │   ├── database.py      # Motor y sesiones de SQLAlchemy
│   │   ├── models.py        # Tablas: Vehiculo, Celda, Operador, Estancia, Cliente, Usuario, Sesion, Tarifa y Pago
│   │   ├── security.py      # Contraseñas con scrypt y tokens de sesión
│   │   ├── auth.py          # Dependencias de sesión y de rol
│   │   ├── routers/         # Las rutas de la API
│   │   ├── services/        # La lógica del negocio
│   │   └── schemas/         # Validación y respuestas (Pydantic)
│   ├── migrations/          # Migraciones de Alembic (0001 a 0004)
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
| `tarifa` | `id`, `tipo_vehiculo` (único: MOTO, AUTOMOVIL o CAMIONETA), `valor_mensual` (mayor que 0) |
| `pago` | `id`, `vehiculo_id`, `cliente_id`, `valor` (copia de la tarifa), `medio_pago` (EFECTIVO, TRANSFERENCIA o TARJETA), `fecha_pago`, `vigencia_desde`, `vigencia_hasta`, `operador_id` (quien lo registró), `estado` (REGISTRADO o ANULADO), `anulado_en`, `anulado_por_operador_id`, `motivo_anulacion` |

`estancia` guarda cada vez que un vehículo entra y sale. Mientras el vehículo sigue dentro, `salida` y `operador_salida_id` están vacíos.

La base protege las reglas del negocio:

- Un vehículo no puede tener dos estancias abiertas, y una celda tampoco (índices únicos que solo miran las estancias sin salida).
- La salida no puede ser anterior a la entrada, y la salida y el operador de salida van juntos.
- No se puede borrar un vehículo, una celda o un operador que ya tenga estancias.
- Un cliente solo se borra si ninguno de sus vehículos tiene estancias; borrar una cuenta elimina sus sesiones pero conserva al operador para el historial.
- La migración `0004` crea `tarifa` y `pago`. En `pago`, la base exige que `vigencia_hasta` sea `vigencia_desde` más 30 días, que el valor sea mayor que 0, que un pago `ANULADO` tenga fecha, operador y motivo de anulación (y uno `REGISTRADO` no), y un índice único parcial `(vehiculo_id, vigencia_desde)` entre los `REGISTRADO` como seguro contra pagos duplicados. Las claves foráneas son `RESTRICT`: no se borra un vehículo, un cliente o un operador que tenga pagos. Su `downgrade` elimina las dos tablas y deja la base como en la `0003`.
- La migración `0003` añade la restricción del tipo de celda como `NOT VALID`: no revisa las filas que ya existían (por ejemplo `Libre`), solo las inserciones y cambios nuevos.

Para revisar el SQL de las migraciones sin tocar la base: `.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head --sql`.

## Decisiones de diseño

- **El estado de una celda no se guarda, se calcula.** Una celda está ocupada si tiene una estancia abierta. Así no puede quedar desactualizado.
- **Las fechas se guardan en UTC**, pero el historial cuenta los días en hora de Bogotá (UTC-5), y el frontend las muestra en `America/Bogota`.
- **La asignación de celda es segura con entradas simultáneas.** La consulta usa `SKIP LOCKED`, y los índices únicos de la base son la garantía final.
- **Contraseñas y sesiones.** Las contraseñas se guardan con `scrypt` y sal aleatoria. De cada sesión solo se guarda el SHA-256 del token, que vence a las 8 horas. El login responde igual y tarda parecido si el usuario no existe o la contraseña es mala.
- **El operador sale de la sesión.** El servidor toma el operador de la sesión; el cuerpo de entrada y salida ya no lo recibe, así nadie puede registrar un movimiento a nombre de otra persona.
- **Ninguna contraseña vive en el código.** El seed las lee del entorno o las genera una sola vez.
- **El pago guarda una copia del valor y la vigencia.** Cambiar una tarifa no altera los pagos ya hechos, y anular un pago no lo borra: queda como historial.
- **El "hoy" de los pagos es el de Bogotá.** La fecha de corte y el estado de la mensualidad usan el día en Bogotá, no el de UTC.
- **Los pagos se serializan por vehículo.** Registrar y anular bloquean la fila del vehículo dentro de la transacción; el índice único parcial de la base es la garantía final.
- **El valor y el operador nunca viajan en la solicitud.** Salen de la tarifa y de la sesión.

## Estado

| Parte | Estado |
|---|---|
| Base de datos y migraciones (0001 a 0004) | Listo |
| Backend de la Iteración 1 | Listo, con pruebas |
| Backend de la Iteración 2 (sesiones, roles, cuentas, clientes, celdas) | Listo, con pruebas |
| Frontend de la Iteración 1 (Entrada, Salida, Dentro, Historial y Celdas) | Listo, con inicio de sesión |
| Frontend de la Iteración 2 (login, roles, cuentas, clientes y gestión de celdas) | Listo, con pruebas |
| Backend de la Iteración 3 (tarifas, pagos, vigencia, estados, comprobante y anulación) | Listo, con pruebas |
| Frontend de la Iteración 3 (Pagos, Registrar pago, Comprobante y anulación) | Listo, con pruebas |
| Datos de prueba (`seed.py`) con tarifas y dos pagos de ejemplo | Listo |

## Iteraciones del proyecto

1. **Iteración 1:** entrada y salida de vehículos.
2. **Iteración 2:** inicio de sesión con roles, cuentas, clientes con vehículos y administración de celdas.
3. **Iteración 3:** pagos de la mensualidad.

Las novedades sobre los vehículos quedan para una iteración posterior.
