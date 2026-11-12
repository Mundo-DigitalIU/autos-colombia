import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { MENSAJE_SESION_TERMINADA } from '../models/auth';
import { AuthService } from '../services/auth.service';

const esLogin = (url: string): boolean => /\/auth\/login(\?|$)/.test(url);

/**
 * Agrega el token a todas las llamadas. Un 401 (salvo en el login) termina la sesión y
 * lleva a /login; un 403 activa el aviso "No tienes permiso para entrar aquí.".
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.token();
  const peticion = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
  return next(peticion).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        if (error.status === 401 && !esLogin(req.url)) {
          auth.limpiar(MENSAJE_SESION_TERMINADA);
          void router.navigateByUrl('/login');
        } else if (error.status === 403) {
          auth.avisarSinPermiso();
        }
      }
      return throwError(() => error);
    }),
  );
};
