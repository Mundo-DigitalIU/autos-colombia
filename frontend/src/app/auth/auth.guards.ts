import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/** Sin sesión, a /login. */
export const sesionGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.autenticado() ? true : inject(Router).parseUrl('/login');
};

/** Rutas de administrador: sin sesión, a /login; con rol de operador, a la pantalla "Sin permiso". */
export const administradorGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.autenticado()) return router.parseUrl('/login');
  return auth.esAdministrador() ? true : router.parseUrl('/sin-permiso');
};

/** El login no se muestra a quien ya tiene sesión. */
export const visitanteGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.autenticado() ? inject(Router).parseUrl('/entrada') : true;
};
