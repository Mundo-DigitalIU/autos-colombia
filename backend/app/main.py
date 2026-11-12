from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.auth import CualquierRol, SoloAdministrador
from app.routers.auth import router as auth_router
from app.routers.vehiculos import router as vehiculos_router
from app.routers.cuentas import router as cuentas_router
from app.services.auth import AuthError
from app.services.cuenta import CuentaError
from app.services.vehiculo import VehiculoError
from app.routers.celdas import router as celdas_router
from app.services.celda import CeldaError
from app.routers.operadores import router as operadores_router
from app.services.operador import OperadorError
from app.routers.estancias import router as estancias_router
from app.services.estancia import EstanciaError

app = FastAPI(title="Autos Colombia API")
# Todas las rutas exigen sesión salvo POST /auth/login y GET /health.
app.include_router(auth_router)
app.include_router(vehiculos_router, dependencies=[CualquierRol])
app.include_router(celdas_router, dependencies=[CualquierRol])
app.include_router(operadores_router, dependencies=[SoloAdministrador])
app.include_router(estancias_router, dependencies=[CualquierRol])
app.include_router(cuentas_router, dependencies=[SoloAdministrador])


@app.exception_handler(VehiculoError)
@app.exception_handler(CeldaError)
@app.exception_handler(OperadorError)
@app.exception_handler(EstanciaError)
@app.exception_handler(AuthError)
@app.exception_handler(CuentaError)
async def entity_error_handler(request, error: VehiculoError | CeldaError | OperadorError | EstanciaError | AuthError | CuentaError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
