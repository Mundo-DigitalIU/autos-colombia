import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { pagina } from './datos-prueba';
import { Pagos } from './pagos';

describe('Pantalla de pagos', () => {
  let fixture: ComponentFixture<Pagos>;
  let http: HttpTestingController;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const pestanas = () => Array.from(raiz().querySelectorAll('[role="tab"]')) as HTMLButtonElement[];

  beforeEach(() => {
    borrarSesionDePrueba();
    guardarSesionDePrueba('OPERADOR');
    TestBed.configureTestingModule({
      imports: [Pagos],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Pagos);
    fixture.detectChanges();
  });
  afterEach(() => {
    http.verify();
    borrarSesionDePrueba();
  });

  it('tiene las pestañas Mensualidades y Pagos registrados, y abre Mensualidades', () => {
    expect(pestanas().map((p) => p.textContent?.trim())).toEqual(['Mensualidades', 'Pagos registrados']);
    expect(pestanas()[0].getAttribute('aria-selected')).toBe('true');
    http.expectOne((r) => r.url === '/pagos/estado').flush(pagina([]));
    fixture.detectChanges();
    expect(raiz().querySelector('app-mensualidades')).not.toBeNull();
    expect(raiz().querySelector('app-pagos-registrados')).toBeNull();
  });

  it('cambia a Pagos registrados y pide sus datos', () => {
    http.expectOne((r) => r.url === '/pagos/estado').flush(pagina([]));
    pestanas()[1].click();
    fixture.detectChanges();
    expect(pestanas()[1].getAttribute('aria-selected')).toBe('true');
    http.expectOne((r) => r.url === '/pagos').flush(pagina([]));
    fixture.detectChanges();
    expect(raiz().querySelector('app-pagos-registrados')).not.toBeNull();
    expect(raiz().textContent).toContain('Todavía no hay pagos registrados.');
  });

  it('ofrece el acceso a Registrar pago', () => {
    http.expectOne((r) => r.url === '/pagos/estado').flush(pagina([]));
    const enlace = raiz().querySelector('header a') as HTMLAnchorElement;
    expect(enlace.textContent?.trim()).toBe('Registrar pago');
    expect(enlace.getAttribute('href')).toBe('/panel/pagos/registrar');
  });
});
