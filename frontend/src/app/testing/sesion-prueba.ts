import { Rol } from '../models/auth';

/** Ayuda para las pruebas: deja una sesión guardada antes de crear AuthService. */
export function guardarSesionDePrueba(
  rol: Rol = 'ADMINISTRADOR',
  nombre = 'Usuario de prueba',
  token = 'token-de-prueba',
): void {
  sessionStorage.setItem(
    'autos-colombia.sesion',
    JSON.stringify({ token, rol, nombre, expira: new Date(Date.now() + 3_600_000).toISOString() }),
  );
}

export function borrarSesionDePrueba(): void {
  sessionStorage.clear();
}
