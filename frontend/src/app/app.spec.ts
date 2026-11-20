import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { Rol } from './models/auth';
import { App } from './app';
import { AuthService } from './services/auth.service';
import { borrarSesionDePrueba, guardarSesionDePrueba } from './testing/sesion-prueba';

describe('Navegación', () => {
  let fixture: ComponentFixture<App>;

  async function crear(rol: Rol | null, nombre = 'Ana Pérez'): Promise<void> {
    borrarSesionDePrueba();
    if (rol) guardarSesionDePrueba(rol, nombre);
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(App);
    fixture.detectChanges();
  }
  const raiz = () => fixture.nativeElement as HTMLElement;
  const enlaces = () =>
    Array.from(raiz().querySelectorAll('nav a')).map((a) => [
      a.textContent?.trim(),
      a.getAttribute('href'),
    ]);

  afterEach(() => borrarSesionDePrueba());

  it('sin sesión no muestra menú ni datos de sesión', async () => {
    await crear(null);
    expect(raiz().querySelector('nav')).toBeNull();
    expect(raiz().textContent).not.toContain('Cerrar sesión');
  });

  it('el operador ve Entrada, Salida, Dentro, Historial, Celdas, Clientes y Pagos, con su nombre y rol', async () => {
    await crear('OPERADOR');
    expect(enlaces()).toEqual([
      ['Entrada', '/entrada'],
      ['Salida', '/salida'],
      ['Dentro', '/dentro'],
      ['Historial', '/historial'],
      ['Celdas', '/estado-celdas'],
      ['Clientes', '/panel/clientes'],
      ['Pagos', '/panel/pagos'],
    ]);
    expect(raiz().textContent).toContain('Ana Pérez');
    expect(raiz().textContent).toContain('Operador');
    expect(raiz().textContent).toContain('Cerrar sesión');
  });

  it('el administrador ve Pagos y además Cuentas y Gestionar celdas', async () => {
    await crear('ADMINISTRADOR');
    expect(enlaces()).toEqual([
      ['Entrada', '/entrada'],
      ['Salida', '/salida'],
      ['Dentro', '/dentro'],
      ['Historial', '/historial'],
      ['Celdas', '/estado-celdas'],
      ['Clientes', '/panel/clientes'],
      ['Pagos', '/panel/pagos'],
      ['Cuentas', '/panel/cuentas'],
      ['Gestionar celdas', '/panel/celdas'],
    ]);
    expect(raiz().textContent).toContain('Administrador');
  });

  it('Cerrar sesión llama a /auth/logout y vuelve a /login', async () => {
    await crear('OPERADOR');
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const http = TestBed.inject(HttpTestingController);
    const boton = Array.from(raiz().querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Cerrar sesión'),
    )!;
    boton.click();
    http.expectOne('/auth/logout').flush({ mensaje: 'Sesión cerrada.' });
    fixture.detectChanges();
    expect(navegar).toHaveBeenCalledWith('/login');
    expect(TestBed.inject(AuthService).autenticado()).toBe(false);
    expect(TestBed.inject(AuthService).aviso()).toBe('Cerraste sesión.');
    expect(raiz().querySelector('nav')).toBeNull();
    http.verify();
  });

  it('un 403 muestra "No tienes permiso para entrar aquí." en una alerta', async () => {
    await crear('OPERADOR');
    TestBed.inject(AuthService).avisarSinPermiso();
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain(
      'No tienes permiso para entrar aquí.',
    );
  });
});
