import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { borrarSesionDePrueba } from '../testing/sesion-prueba';
import { Login } from './login';

describe('Pantalla de login', () => {
  let fixture: ComponentFixture<Login>;
  let http: HttpTestingController;
  let navegar: ReturnType<typeof vi.spyOn>;
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const campo = (id: string) =>
    (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(`#${id}`)!;

  function crear(aviso = ''): void {
    borrarSesionDePrueba();
    TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    if (aviso) TestBed.inject(AuthService).limpiar(aviso);
    http = TestBed.inject(HttpTestingController);
    navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture = TestBed.createComponent(Login);
    fixture.detectChanges();
  }
  function escribir(usuario: string, contrasena: string): void {
    campo('usuario').value = usuario;
    campo('usuario').dispatchEvent(new Event('input'));
    campo('contrasena').value = contrasena;
    campo('contrasena').dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }
  function enviar(): void {
    (fixture.nativeElement as HTMLElement)
      .querySelector('form')!
      .dispatchEvent(new Event('submit'));
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
    vi.restoreAllMocks();
    borrarSesionDePrueba();
  });

  it('pide usuario y contraseña antes de llamar a la API', () => {
    crear();
    enviar();
    expect(texto()).toContain('Escribe tu usuario.');
    expect(texto()).toContain('Escribe tu contraseña.');
    escribir('ana', '   ');
    enviar();
    expect(texto()).not.toContain('Escribe tu usuario.');
    expect(texto()).toContain('Escribe tu contraseña.');
    http.expectNone('/auth/login');
  });

  it('con datos válidos inicia sesión y va a Entrada', () => {
    crear();
    escribir('  Ana ', 'una-clave-larga');
    enviar();
    const peticion = http.expectOne('/auth/login');
    expect(peticion.request.body).toEqual({ usuario: 'Ana', contrasena: 'una-clave-larga' });
    expect(texto()).toContain('Entrando…');
    peticion.flush({
      token: 't',
      rol: 'OPERADOR',
      nombre: 'Ana',
      expira: new Date(Date.now() + 3_600_000).toISOString(),
    });
    expect(navegar).toHaveBeenCalledWith('/entrada');
    expect(TestBed.inject(AuthService).rol()).toBe('OPERADOR');
  });

  it('muestra el detail de la API si las credenciales son incorrectas y vacía la contraseña', () => {
    crear();
    escribir('ana', 'mala-clave-123');
    enviar();
    http
      .expectOne('/auth/login')
      .flush({ detail: 'Usuario o contraseña incorrectos.' }, { status: 401, statusText: 'No' });
    fixture.detectChanges();
    expect(texto()).toContain('Usuario o contraseña incorrectos.');
    expect(campo('contrasena').value).toBe('');
    expect(navegar).not.toHaveBeenCalled();
  });

  it('si no hay conexión muestra un mensaje de respaldo', () => {
    crear();
    escribir('ana', 'una-clave-larga');
    enviar();
    http.expectOne('/auth/login').error(new ProgressEvent('error'));
    fixture.detectChanges();
    expect(texto()).toContain('No se pudo conectar con el servicio');
  });

  it('muestra el aviso que dejó el cierre de sesión', () => {
    crear('Cerraste sesión.');
    expect(texto()).toContain('Cerraste sesión.');
  });

  it('muestra el aviso de sesión terminada', () => {
    crear('Tu sesión terminó. Inicia sesión otra vez.');
    expect(texto()).toContain('Tu sesión terminó. Inicia sesión otra vez.');
  });
});
