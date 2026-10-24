import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Dentro } from './dentro';

describe('Vehículos dentro', () => {
  let fixture: ComponentFixture<Dentro>;
  let http: HttpTestingController;
  const url = '/estancias/dentro?offset=0&limit=20';
  const item = {
    estancia_id: 36,
    placa: 'ABC12D',
    tipo: 'MOTO',
    celda_codigo: 'M-01',
    entrada: '2026-10-23T21:04:21Z',
  };
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Dentro],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Dentro);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra la carga y bloquea el botón mientras consulta', () => {
    expect(texto()).toContain('Cargando vehículos');
    const boton = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    expect(boton.disabled).toBe(true);
    http.expectOne(url).flush({ items: [], total: 0, offset: 0, limit: 20 });
  });

  it('lista placa, tipo, celda y hora de entrada en Bogotá, con el conteo', () => {
    http.expectOne(url).flush({ items: [item], total: 1, offset: 0, limit: 20 });
    fixture.detectChanges();
    const celdas = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr > *'),
    ).map((c) => c.textContent?.trim());
    expect(celdas.slice(0, 3)).toEqual(['ABC12D', 'MOTO', 'M-01']);
    expect(celdas[3]).toContain('4:04:21');
    expect(fixture.nativeElement.querySelector('.count').textContent).toBe('1');
  });

  it('muestra los títulos del diseño y el botón "Actualizar listado"', () => {
    http.expectOne(url).flush({ items: [], total: 0, offset: 0, limit: 20 });
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.eyebrow')?.textContent).toBe('OCUPACIÓN ACTUAL');
    expect(root.querySelector('h1')?.textContent).toBe('Vehículos dentro del parqueadero');
    expect(root.querySelector('header button')?.textContent?.trim()).toBe('Actualizar listado');
  });

  it('muestra el estado vacío', () => {
    http.expectOne(url).flush({ items: [], total: 0, offset: 0, limit: 20 });
    fixture.detectChanges();
    expect(texto()).toContain('No hay vehículos dentro del parqueadero.');
  });

  it('muestra un error si la API falla y el botón Actualizar reintenta', () => {
    http.expectOne(url).flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain(
      'No se pudo consultar',
    );
    (fixture.nativeElement.querySelector('button') as HTMLButtonElement).click();
    http.expectOne(url).flush({ items: [item], total: 1, offset: 0, limit: 20 });
    expect(fixture.componentInstance.error()).toBe('');
    expect(fixture.componentInstance.items().length).toBe(1);
  });

  it('no envía otra petición mientras hay una en curso', () => {
    fixture.componentInstance.load();
    http.expectOne(url).flush({ items: [], total: 0, offset: 0, limit: 20 });
  });
});
