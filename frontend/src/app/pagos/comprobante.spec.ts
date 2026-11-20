import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { Comprobante } from './comprobante';
import { pagoAnuladoPrueba, pagoPrueba } from './datos-prueba';

describe('Comprobante', () => {
  let fixture: ComponentFixture<Comprobante>;
  let http: HttpTestingController;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const texto = () => raiz().textContent ?? '';

  function crear(id: string): void {
    TestBed.configureTestingModule({
      imports: [Comprobante],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map([['id', id]]) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Comprobante);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('muestra el comprobante de un pago registrado', () => {
    crear('7');
    expect(texto()).toContain('Cargando comprobante');
    http.expectOne('/pagos/7').flush(pagoPrueba());
    fixture.detectChanges();
    const dato = (etiqueta: string) => {
      const dt = Array.from(raiz().querySelectorAll('dt')).find((x) => x.textContent?.trim() === etiqueta)!;
      return dt.nextElementSibling?.textContent?.trim();
    };
    expect(dato('Número de pago')).toBe('000007');
    expect(raiz().querySelector('.recibo-numero')?.textContent?.trim()).toBe('Pago 000007');
    expect(dato('Fecha y hora')).toBe('01/09/2026 · 12:00 p. m.');
    expect(dato('Cliente')).toBe('Laura Gómez');
    expect(dato('Documento')).toBe('1000000001');
    expect(dato('Placa')).toBe('ABC123');
    expect(dato('Tipo de vehículo')).toBe('Automóvil');
    expect(dato('Valor')).toBe('$250.000');
    expect(dato('Medio de pago')).toBe('Efectivo');
    expect(dato('Vigencia desde')).toBe('01/09/2026');
    expect(dato('Vigencia hasta')).toBe('01/10/2026');
    expect(dato('Registrado por')).toBe('Administrador');
    expect(dato('Estado')).toBe('Registrado');
    expect(texto()).not.toContain('ANULADO');
  });

  it('un pago anulado muestra la franja ANULADO con motivo, quién y cuándo', () => {
    crear('7');
    http.expectOne('/pagos/7').flush(pagoAnuladoPrueba());
    fixture.detectChanges();
    const franja = raiz().querySelector('.franja-anulado')?.textContent ?? '';
    expect(franja).toContain('ANULADO');
    expect(franja).toContain('Cobro duplicado');
    expect(franja).toContain('Administrador');
    expect(franja).toContain('02/09/2026 · 09:30 a. m.');
  });

  it('muestra el encabezado, la nota de los 30 días y el medio y tipo con mayúscula inicial', () => {
    crear('7');
    http.expectOne('/pagos/7').flush(pagoPrueba({ tipo: 'MOTO', medio_pago: 'TARJETA' }));
    fixture.detectChanges();
    expect(texto()).toContain('GESTIÓN DE PAGOS');
    expect(texto()).toContain('Detalle del pago de la mensualidad.');
    expect(texto()).toContain('Autos Colombia');
    expect(texto()).toContain('Comprobante de mensualidad');
    expect(texto()).toContain('La mensualidad dura 30 días y se cuenta desde la fecha de corte del vehículo.');
    expect(texto()).toContain('Moto');
    expect(texto()).toContain('Tarjeta');
  });

  it('tiene el botón Volver a pagos', () => {
    crear('7');
    http.expectOne('/pagos/7').flush(pagoPrueba());
    fixture.detectChanges();
    const volver = Array.from(raiz().querySelectorAll('a')).find((a) => a.textContent?.trim() === 'Volver a pagos')!;
    expect(volver.getAttribute('href')).toBe('/panel/pagos');
  });

  it('un pago inexistente muestra el mensaje de la API', () => {
    crear('999');
    http.expectOne('/pagos/999').flush({ detail: 'Pago no encontrado.' }, { status: 404, statusText: 'x' });
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain('Pago no encontrado.');
  });

  it('un número inválido no consulta la API', () => {
    crear('abc');
    fixture.detectChanges();
    expect(texto()).toContain('Pago no encontrado.');
    http.expectNone((r) => true);
  });
});
