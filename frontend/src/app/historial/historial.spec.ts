import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Historial } from './historial';

describe('Historial', () => {
  let fixture: ComponentFixture<Historial>;
  let http: HttpTestingController;
  let c: Historial;
  const abierta = {
    estancia_id: 20,
    placa: 'ABC123',
    celda_codigo: 'C-01',
    entrada: '2026-10-23T20:46:15Z',
    salida: null,
    operador_entrada: 'Operador Portería',
    operador_salida: null,
  };
  const cerrada = {
    ...abierta,
    estancia_id: 19,
    salida: '2026-10-23T22:00:00Z',
    operador_salida: 'Operador Salida',
  };
  const pagina = (items: unknown[], total = items.length, offset = 0) => ({
    items,
    total,
    offset,
    limit: 20,
  });
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const inicial = () => http.expectOne('/estancias/historial?offset=0&limit=20');

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Historial],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Historial);
    c = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra la carga y bloquea el botón Buscar mientras consulta', () => {
    expect(texto()).toContain('Cargando historial');
    const campos = fixture.nativeElement.querySelector('fieldset') as HTMLFieldSetElement;
    expect(campos.disabled).toBe(true);
    c.buscar();
    inicial().flush(pagina([]));
    fixture.detectChanges();
    expect(campos.disabled).toBe(false);
  });

  it('muestra "Dentro" cuando la estancia sigue abierta y la salida cuando ya cerró', () => {
    inicial().flush(pagina([abierta, cerrada]));
    fixture.detectChanges();
    const filas = (fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr');
    expect(filas[0].querySelector('.tag')?.textContent).toBe('Dentro');
    expect(filas[0].textContent).toContain('—');
    expect(filas[1].querySelector('.tag')).toBeNull();
    expect(filas[1].textContent).toContain('5:00:00');
    expect(filas[1].textContent).toContain('Operador Salida');
    expect(filas[0].textContent).toContain('3:46:15');
  });

  it('envía los filtros normalizados al pulsar Buscar y vuelve a la primera página', () => {
    inicial().flush(pagina([]));
    c.form.setValue({ placa: ' abc123 ', desde: '2026-10-22', hasta: '2026-10-23' });
    c.buscar();
    const req = http.expectOne(
      (r) => r.url === '/estancias/historial' && r.params.get('placa') === 'ABC123',
    );
    expect(req.request.params.get('desde')).toBe('2026-10-22');
    expect(req.request.params.get('hasta')).toBe('2026-10-23');
    expect(req.request.params.get('offset')).toBe('0');
    req.flush(pagina([abierta]));
    expect(c.form.controls.placa.value).toBe('ABC123');
  });

  it('no envía filtros vacíos', () => {
    inicial().flush(pagina([]));
    c.buscar();
    const req = http.expectOne('/estancias/historial?offset=0&limit=20');
    expect(req.request.params.has('placa')).toBe(false);
    req.flush(pagina([]));
  });

  it('no consulta si "Desde" es posterior a "Hasta"', () => {
    inicial().flush(pagina([]));
    c.form.setValue({ placa: '', desde: '2026-10-24', hasta: '2026-10-23' });
    c.buscar();
    http.expectNone((r) => r.url === '/estancias/historial');
    expect(c.error()).toContain('no puede ser posterior');
  });

  it('muestra los títulos del diseño', () => {
    inicial().flush(pagina([]));
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.eyebrow')?.textContent).toBe('CONSULTA');
    expect(root.querySelector('h1')?.textContent).toBe('Historial de movimientos');
  });

  it('muestra el estado vacío', () => {
    inicial().flush(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No hay movimientos con esos filtros.');
  });

  it('pagina conservando los filtros aplicados', () => {
    inicial().flush(pagina([]));
    c.form.setValue({ placa: 'ABC123', desde: '', hasta: '' });
    c.buscar();
    http.expectOne((r) => r.params.get('placa') === 'ABC123').flush(pagina([abierta], 45));
    c.cargar(20);
    const req = http.expectOne((r) => r.params.get('offset') === '20');
    expect(req.request.params.get('placa')).toBe('ABC123');
    req.flush(pagina([cerrada], 45, 20));
    expect(c.page()).toBe(2);
    expect(c.pages()).toBe(3);
  });

  it('muestra un error si la API falla', () => {
    inicial().flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain(
      'No se pudo consultar el historial',
    );
  });
});
