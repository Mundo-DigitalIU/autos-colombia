import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Pago } from '../models/pago';
import { AnularPago } from './anular-pago';
import { pagoAnuladoPrueba, pagoPrueba } from './datos-prueba';

describe('Diálogo de anulación', () => {
  let fixture: ComponentFixture<AnularPago>;
  let http: HttpTestingController;
  let anulados: Pago[];
  let cancelados: number;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const texto = () => raiz().textContent ?? '';
  const boton = (nombre: string) =>
    Array.from(raiz().querySelectorAll('button')).find((b) => b.textContent?.trim() === nombre)!;
  const escribir = (valor: string) => {
    const campo = raiz().querySelector('#anular-motivo') as HTMLTextAreaElement;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [AnularPago],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AnularPago);
    fixture.componentRef.setInput('pago', pagoPrueba());
    anulados = [];
    cancelados = 0;
    fixture.componentInstance.anulado.subscribe((p) => anulados.push(p));
    fixture.componentInstance.cancelado.subscribe(() => cancelados++);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('muestra el resumen: placa, cliente, valor y vigencia', () => {
    for (const dato of ['ABC123', 'Laura Gómez', '$250.000', '01/09/2026 - 01/10/2026']) {
      expect(texto()).toContain(dato);
    }
    expect(texto()).toContain('Motivo de la anulación');
  });

  it('con el motivo vacío o solo espacios pide escribirlo y no llama a la API', () => {
    boton('Anular pago').click();
    fixture.detectChanges();
    expect(texto()).toContain('Escribe el motivo de la anulación.');
    escribir('   ');
    boton('Anular pago').click();
    fixture.detectChanges();
    expect(texto()).toContain('Escribe el motivo de la anulación.');
    http.expectNone('/pagos/7/anular');
    expect(anulados).toEqual([]);
  });

  it('envía el motivo recortado y avisa al anular', () => {
    escribir('  Cobro duplicado ');
    boton('Anular pago').click();
    const peticion = http.expectOne('/pagos/7/anular');
    expect(peticion.request.body).toEqual({ motivo: 'Cobro duplicado' });
    peticion.flush(pagoAnuladoPrueba());
    expect(anulados.map((p) => p.estado)).toEqual(['ANULADO']);
  });

  it('muestra los errores 409 de la API tal cual y no cierra el diálogo', () => {
    escribir('Error de digitación');
    boton('Anular pago').click();
    http
      .expectOne('/pagos/7/anular')
      .flush({ detail: 'Solo se puede anular el último pago del vehículo.' }, { status: 409, statusText: 'x' });
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain(
      'Solo se puede anular el último pago del vehículo.',
    );
    expect(anulados).toEqual([]);
    expect(cancelados).toBe(0);
  });

  it('Cancelar cierra sin llamar a la API', () => {
    boton('Cancelar').click();
    expect(cancelados).toBe(1);
    http.expectNone('/pagos/7/anular');
  });
});
