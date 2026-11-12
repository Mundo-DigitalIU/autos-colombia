import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  CanActivateFn,
  RouterStateSnapshot,
  provideRouter,
} from '@angular/router';
import { Rol } from '../models/auth';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { administradorGuard, sesionGuard, visitanteGuard } from './auth.guards';

describe('guards de sesión y de rol', () => {
  function ejecutar(guard: CanActivateFn, rol: Rol | null): string | boolean {
    borrarSesionDePrueba();
    if (rol) guardarSesionDePrueba(rol);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const resultado = TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    );
    return typeof resultado === 'boolean' ? resultado : String(resultado);
  }

  afterEach(() => borrarSesionDePrueba());

  it('sesionGuard: sin sesión manda a /login y con sesión deja pasar', () => {
    expect(ejecutar(sesionGuard, null)).toBe('/login');
    expect(ejecutar(sesionGuard, 'OPERADOR')).toBe(true);
    expect(ejecutar(sesionGuard, 'ADMINISTRADOR')).toBe(true);
  });

  it('administradorGuard: sin sesión a /login, operador a "Sin permiso", administrador pasa', () => {
    expect(ejecutar(administradorGuard, null)).toBe('/login');
    expect(ejecutar(administradorGuard, 'OPERADOR')).toBe('/sin-permiso');
    expect(ejecutar(administradorGuard, 'ADMINISTRADOR')).toBe(true);
  });

  it('visitanteGuard: quien ya tiene sesión no ve el login', () => {
    expect(ejecutar(visitanteGuard, null)).toBe(true);
    expect(ejecutar(visitanteGuard, 'OPERADOR')).toBe('/entrada');
  });
});
