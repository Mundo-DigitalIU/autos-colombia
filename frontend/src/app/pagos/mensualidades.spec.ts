import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Mensualidades } from './mensualidades';
import { mensualidadPrueba, pagina } from './datos-prueba';

describe('Mensualidades', () => {
  let fixture: ComponentFixture<Mensualidades>;
  let http: HttpTestingController;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const texto = () => raiz().textContent ?? '';
  const listar = (cuerpo: object) =>
    http.expectOne((r) => r.url === '/pagos/estado' && r.method === 'GET').flush(cuerpo);

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Mensualidades],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Mensualidades);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('pide la primera página y muestra cada vehículo con su estado, tarifa y vigencia', () => {
    expect(texto()).toContain('Cargando mensualidades');
    const peticion = http.expectOne((r) => r.url === '/pagos/estado');
    expect(peticion.request.params.get('offset')).toBe('0');
    expect(peticion.request.params.get('limit')).toBe('10');
    peticion.flush(
      pagina([
        mensualidadPrueba(),
        mensualidadPrueba({ placa: 'MNO345', estado: 'VENCIDA', vigencia_hasta: '2026-08-15', tarifa: 100000 }),
        mensualidadPrueba({ placa: 'DEF456', estado: 'SIN_PAGOS', vigencia_hasta: null, ultimo_pago_id: null }),
      ]),
    );
    fixture.detectChanges();
    const filas = Array.from(raiz().querySelectorAll('tbody tr'));
    expect(filas.length).toBe(3);
    expect(filas[0].textContent).toContain('ABC123');
    expect(filas[0].textContent).toContain('Laura Gómez');
    expect(filas[0].textContent).toContain('$250.000');
    expect(filas[0].textContent).toContain('01/10/2026');
    expect(filas[1].textContent).toContain('$100.000');
    expect(filas[1].textContent).toContain('15/08/2026');
    expect(filas[2].textContent).toContain('—');
  });

  it('el estado es una etiqueta de color: Al día en verde, Vencida en rojo y Sin pagos en gris', () => {
    listar(
      pagina([
        mensualidadPrueba(),
        mensualidadPrueba({ placa: 'MNO345', estado: 'VENCIDA' }),
        mensualidadPrueba({ placa: 'DEF456', estado: 'SIN_PAGOS', vigencia_hasta: null, ultimo_pago_id: null }),
      ]),
    );
    fixture.detectChanges();
    const etiquetas = Array.from(raiz().querySelectorAll('tbody .tag'));
    expect(etiquetas.map((e) => e.textContent?.trim())).toEqual(['Al día', 'Vencida', 'Sin pagos']);
    expect(etiquetas.map((e) => e.className)).toEqual(['tag ok', 'tag late', 'tag none']);
  });

  it('el botón Registrar pago abre el registro con la placa de la fila', () => {
    listar(pagina([mensualidadPrueba({ placa: 'MNO345' })]));
    fixture.detectChanges();
    const enlace = raiz().querySelector('tbody a') as HTMLAnchorElement;
    expect(enlace.textContent?.trim()).toBe('Registrar pago');
    expect(enlace.getAttribute('href')).toBe('/panel/pagos/registrar?placa=MNO345');
  });

  it('busca por texto y filtra por estado, y Limpiar quita los filtros', () => {
    listar(pagina([mensualidadPrueba()]));
    fixture.detectChanges();
    const buscar = raiz().querySelector('#mensualidades-buscar') as HTMLInputElement;
    const estado = raiz().querySelector('#mensualidades-estado') as HTMLSelectElement;
    buscar.value = '  laura ';
    buscar.dispatchEvent(new Event('input'));
    estado.value = 'VENCIDA';
    estado.dispatchEvent(new Event('change'));
    (raiz().querySelector('form[role="search"]') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const peticion = http.expectOne((r) => r.url === '/pagos/estado');
    expect(peticion.request.params.get('q')).toBe('laura');
    expect(peticion.request.params.get('estado')).toBe('VENCIDA');
    expect(peticion.request.params.get('offset')).toBe('0');
    peticion.flush(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No hay resultados con ese filtro.');

    const limpiar = Array.from(raiz().querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Limpiar')!;
    limpiar.click();
    const sin = http.expectOne((r) => r.url === '/pagos/estado');
    expect(sin.request.params.has('q')).toBe(false);
    expect(sin.request.params.has('estado')).toBe(false);
    sin.flush(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('Todavía no hay vehículos con cliente.');
  });

  it('pagina con Siguiente y Anterior', () => {
    listar(pagina([mensualidadPrueba()], 25));
    fixture.detectChanges();
    expect(texto()).toContain('Página 1 de 3');
    const siguiente = Array.from(raiz().querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Siguiente')!;
    siguiente.click();
    const segunda = http.expectOne((r) => r.url === '/pagos/estado');
    expect(segunda.request.params.get('offset')).toBe('10');
    segunda.flush(pagina([mensualidadPrueba()], 25, 10, 10));
    fixture.detectChanges();
    expect(texto()).toContain('Página 2 de 3');
  });

  it('muestra el error de la API tal cual', () => {
    http
      .expectOne((r) => r.url === '/pagos/estado')
      .flush({ detail: 'No se pudo completar la operación con la base de datos.' }, { status: 503, statusText: 'x' });
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain(
      'No se pudo completar la operación con la base de datos.',
    );
  });
});
