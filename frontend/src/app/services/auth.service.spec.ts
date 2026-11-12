import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let http: HttpTestingController;
  const respuesta = {
    token: 'abc.def',
    rol: 'OPERADOR' as const,
    nombre: 'Operador Portería',
    expira: new Date(Date.now() + 3_600_000).toISOString(),
  };

  function crear(): AuthService {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    return TestBed.inject(AuthService);
  }

  beforeEach(() => borrarSesionDePrueba());
  afterEach(() => {
    http?.verify();
    vi.restoreAllMocks();
    borrarSesionDePrueba();
  });

  it('sin sesión guardada no hay sesión', () => {
    const auth = crear();
    expect(auth.autenticado()).toBe(false);
    expect(auth.token()).toBeNull();
    expect(auth.rol()).toBeNull();
  });

  it('el login envía usuario y contrasena y guarda token, rol y nombre', () => {
    const auth = crear();
    let recibido: unknown;
    auth
      .login({ usuario: 'operador', contrasena: 'una-clave-larga' })
      .subscribe((r) => (recibido = r));
    const peticion = http.expectOne('/auth/login');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ usuario: 'operador', contrasena: 'una-clave-larga' });
    peticion.flush(respuesta);
    expect(recibido).toEqual(respuesta);
    expect(auth.autenticado()).toBe(true);
    expect(auth.token()).toBe('abc.def');
    expect(auth.rol()).toBe('OPERADOR');
    expect(auth.nombre()).toBe('Operador Portería');
    expect(auth.esAdministrador()).toBe(false);
    expect(JSON.parse(sessionStorage.getItem('autos-colombia.sesion')!).token).toBe('abc.def');
  });

  it('recupera la sesión guardada al crearse', () => {
    guardarSesionDePrueba('ADMINISTRADOR', 'Ana', 'tok');
    const auth = crear();
    expect(auth.token()).toBe('tok');
    expect(auth.esAdministrador()).toBe(true);
    expect(auth.nombre()).toBe('Ana');
  });

  it('descarta una sesión vencida o dañada', () => {
    sessionStorage.setItem(
      'autos-colombia.sesion',
      JSON.stringify({ ...respuesta, expira: '2020-01-01T00:00:00Z' }),
    );
    expect(crear().autenticado()).toBe(false);
    TestBed.resetTestingModule();
    sessionStorage.setItem('autos-colombia.sesion', '{no es json');
    expect(crear().autenticado()).toBe(false);
    TestBed.resetTestingModule();
    sessionStorage.setItem('autos-colombia.sesion', JSON.stringify({ ...respuesta, rol: 'JEFE' }));
    expect(crear().autenticado()).toBe(false);
  });

  it('si sessionStorage falla, la sesión sigue funcionando en memoria', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    const auth = crear();
    expect(auth.autenticado()).toBe(false);
    auth.login({ usuario: 'a', contrasena: 'b' }).subscribe();
    http.expectOne('/auth/login').flush(respuesta);
    expect(auth.autenticado()).toBe(true);
    auth.limpiar();
    expect(auth.autenticado()).toBe(false);
  });

  it('un login rechazado no deja sesión', () => {
    const auth = crear();
    auth.login({ usuario: 'a', contrasena: 'b' }).subscribe({ error: () => undefined });
    http
      .expectOne('/auth/login')
      .flush({ detail: 'Usuario o contraseña incorrectos.' }, { status: 401, statusText: 'No' });
    expect(auth.autenticado()).toBe(false);
    expect(sessionStorage.getItem('autos-colombia.sesion')).toBeNull();
  });

  it('cerrar sesión llama a /auth/logout y deja el aviso "Cerraste sesión."', () => {
    guardarSesionDePrueba();
    const auth = crear();
    let terminado = false;
    auth.cerrarSesion().subscribe(() => (terminado = true));
    const peticion = http.expectOne('/auth/logout');
    expect(peticion.request.method).toBe('POST');
    peticion.flush({ mensaje: 'Sesión cerrada.' });
    expect(terminado).toBe(true);
    expect(auth.autenticado()).toBe(false);
    expect(sessionStorage.getItem('autos-colombia.sesion')).toBeNull();
    expect(auth.consumirAviso()).toBe('Cerraste sesión.');
    expect(auth.consumirAviso()).toBe('');
  });

  it('cerrar sesión borra la sesión local aunque el servidor falle', () => {
    guardarSesionDePrueba();
    const auth = crear();
    auth.cerrarSesion().subscribe();
    http.expectOne('/auth/logout').flush(null, { status: 500, statusText: 'Error' });
    expect(auth.autenticado()).toBe(false);
    expect(auth.aviso()).toBe('Cerraste sesión.');
  });
});
