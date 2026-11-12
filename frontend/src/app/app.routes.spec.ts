import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { routes } from './app.routes';
import { Rol } from './models/auth';
import { borrarSesionDePrueba, guardarSesionDePrueba } from './testing/sesion-prueba';

describe('Rutas', () => {
  async function navegar(url: string, rol: Rol | null): Promise<{ url: string; texto: string }> {
    borrarSesionDePrueba();
    if (rol) guardarSesionDePrueba(rol);
    TestBed.configureTestingModule({
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    });
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl(url);
    const router = TestBed.inject(Router);
    const texto = (harness.routeNativeElement as HTMLElement | null)?.textContent ?? '';
    // Las pantallas piden datos al abrirse: se descartan, aquí solo importa a dónde se llega.
    TestBed.inject(HttpTestingController)
      .match(() => true)
      .forEach((r) => r.flush({}, { status: 200, statusText: 'OK' }));
    return { url: router.url, texto };
  }

  afterEach(() => borrarSesionDePrueba());

  it('usa las rutas pedidas y ninguna choca con los prefijos del proxy', () => {
    const rutas = routes.flatMap((r) => [r, ...(r.children ?? [])]).map((r) => r.path);
    for (const ruta of [
      'login',
      'entrada',
      'salida',
      'dentro',
      'historial',
      'estado-celdas',
      'panel/clientes',
      'panel/cuentas',
      'panel/celdas',
    ]) {
      expect(rutas).toContain(ruta);
    }
    const prefijos = [
      'estancias',
      'celdas',
      'vehiculos',
      'operadores',
      'auth',
      'cuentas',
      'clientes',
      'health',
    ];
    for (const ruta of rutas.filter((r): r is string => !!r)) {
      expect(prefijos).not.toContain(ruta.split('/')[0]);
    }
  });

  it('sin sesión, cualquier pantalla lleva a /login', async () => {
    for (const url of ['/entrada', '/panel/clientes', '/panel/cuentas', '/estado-celdas']) {
      TestBed.resetTestingModule();
      expect((await navegar(url, null)).url).toBe('/login');
    }
  });

  it('con sesión, /login lleva a Entrada y la raíz también', async () => {
    expect((await navegar('/login', 'OPERADOR')).url).toBe('/entrada');
    TestBed.resetTestingModule();
    expect((await navegar('/', 'OPERADOR')).url).toBe('/entrada');
  });

  it('el operador entra a las pantallas comunes', async () => {
    for (const url of [
      '/entrada',
      '/salida',
      '/dentro',
      '/historial',
      '/estado-celdas',
      '/panel/clientes',
    ]) {
      TestBed.resetTestingModule();
      expect((await navegar(url, 'OPERADOR')).url).toBe(url);
    }
  });

  it('el operador que entra a cuentas o a gestionar celdas ve "Sin permiso"', async () => {
    for (const url of ['/panel/cuentas', '/panel/celdas']) {
      TestBed.resetTestingModule();
      const destino = await navegar(url, 'OPERADOR');
      expect(destino.url).toBe('/sin-permiso');
      expect(destino.texto).toContain('Sin permiso');
    }
  });

  it('el administrador entra a cuentas y a gestionar celdas', async () => {
    for (const url of ['/panel/cuentas', '/panel/celdas']) {
      TestBed.resetTestingModule();
      expect((await navegar(url, 'ADMINISTRADOR')).url).toBe(url);
    }
  });
});
