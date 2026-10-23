import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EstadoCeldas } from './estado-celdas';

describe('Estado de las celdas', () => {
  let fixture: ComponentFixture<EstadoCeldas>;
  let http: HttpTestingController;
  const url = '/estancias/celdas?offset=0&limit=100';
  const respuesta = {
    items: [
      { id: 1, codigo: 'C-01', tipo: 'AUTOMOVIL', estado: 'OCUPADA' },
      { id: 2, codigo: 'M-01', tipo: 'MOTO', estado: 'DISPONIBLE' },
    ],
    total: 2,
    disponibles: 1,
    ocupadas: 1,
    offset: 0,
    limit: 100,
  };
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [EstadoCeldas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(EstadoCeldas);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra el estado de carga y bloquea el botón mientras consulta', () => {
    expect(texto()).toContain('Cargando celdas');
    const boton = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    expect(boton.disabled).toBe(true);
    http.expectOne(url).flush(respuesta);
  });

  it('muestra los totales y una etiqueta por estado', () => {
    http.expectOne(url).flush(respuesta);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('[data-testid="disponibles"]')?.textContent).toBe('1');
    expect(root.querySelector('[data-testid="ocupadas"]')?.textContent).toBe('1');
    expect(root.querySelector('.tag.occupied')?.textContent).toContain('OCUPADA');
    expect(root.querySelector('.tag.available')?.textContent).toContain('DISPONIBLE');
    expect(root.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('muestra un mensaje si la API falla y permite reintentar', () => {
    http.expectOne(url).flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain(
      'No se pudo consultar',
    );
    fixture.componentInstance.load();
    http.expectOne(url).flush(respuesta);
    expect(fixture.componentInstance.error()).toBe('');
  });

  it('no envía una segunda petición mientras hay una en curso', () => {
    fixture.componentInstance.load();
    http.expectOne(url).flush(respuesta);
  });
});
