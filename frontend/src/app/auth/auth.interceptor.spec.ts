import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let controlador: HttpTestingController;
  let auth: AuthService;
  let navegar: ReturnType<typeof vi.spyOn>;

  function preparar(conSesion: boolean): void {
    borrarSesionDePrueba();
    if (conSesion) guardarSesionDePrueba('OPERADOR', 'Ana', 'mi-token');
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    controlador = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
  }

  afterEach(() => {
    controlador.verify();
    vi.restoreAllMocks();
    borrarSesionDePrueba();
  });

  it('agrega Authorization: Bearer a todas las llamadas cuando hay sesión', () => {
    preparar(true);
    http.get('/estancias/dentro').subscribe();
    http.post('/clientes', {}).subscribe();
    expect(controlador.expectOne('/estancias/dentro').request.headers.get('Authorization')).toBe(
      'Bearer mi-token',
    );
    expect(controlador.expectOne('/clientes').request.headers.get('Authorization')).toBe(
      'Bearer mi-token',
    );
  });

  it('no agrega el encabezado si no hay sesión', () => {
    preparar(false);
    http.post('/auth/login', {}).subscribe();
    expect(controlador.expectOne('/auth/login').request.headers.has('Authorization')).toBe(false);
  });

  it('un 401 borra la sesión y manda a /login con el mensaje de sesión terminada', () => {
    preparar(true);
    let fallo: unknown;
    http.get('/estancias/dentro').subscribe({ error: (e) => (fallo = e) });
    controlador
      .expectOne('/estancias/dentro')
      .flush(
        { detail: 'Tu sesión terminó. Inicia sesión otra vez.' },
        { status: 401, statusText: 'No' },
      );
    expect(fallo).toBeTruthy();
    expect(auth.autenticado()).toBe(false);
    expect(sessionStorage.getItem('autos-colombia.sesion')).toBeNull();
    expect(navegar).toHaveBeenCalledWith('/login');
    expect(auth.aviso()).toBe('Tu sesión terminó. Inicia sesión otra vez.');
  });

  it('el 401 del propio login no cierra nada ni redirige', () => {
    preparar(false);
    http.post('/auth/login', {}).subscribe({ error: () => undefined });
    controlador
      .expectOne('/auth/login')
      .flush({ detail: 'Usuario o contraseña incorrectos.' }, { status: 401, statusText: 'No' });
    expect(navegar).not.toHaveBeenCalled();
    expect(auth.aviso()).toBe('');
  });

  it('un 403 activa el aviso de permiso y conserva la sesión', () => {
    preparar(true);
    let estado = 0;
    http.get('/cuentas').subscribe({ error: (e) => (estado = e.status) });
    controlador
      .expectOne('/cuentas')
      .flush({ detail: 'No tienes permiso para entrar aquí.' }, { status: 403, statusText: 'No' });
    expect(estado).toBe(403);
    expect(auth.sinPermiso()).toBe(true);
    expect(auth.autenticado()).toBe(true);
    expect(navegar).not.toHaveBeenCalled();
  });

  it('otros errores pasan sin tocar la sesión', () => {
    preparar(true);
    http.get('/estancias/dentro').subscribe({ error: () => undefined });
    controlador
      .expectOne('/estancias/dentro')
      .flush(null, { status: 409, statusText: 'Conflicto' });
    expect(auth.autenticado()).toBe(true);
    expect(auth.sinPermiso()).toBe(false);
  });
});
