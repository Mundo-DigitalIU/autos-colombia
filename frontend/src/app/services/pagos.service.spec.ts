import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { PagosService } from './pagos.service';

describe('PagosService', () => {
  let servicio: PagosService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    servicio = TestBed.inject(PagosService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('registrar envía solo la placa y el medio de pago', () => {
    servicio.registrar({ placa: 'ABC123', medio_pago: 'EFECTIVO' }).subscribe();
    const peticion = http.expectOne('/pagos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ placa: 'ABC123', medio_pago: 'EFECTIVO' });
    peticion.flush({});
  });

  it('listar envía solo los filtros con valor, recortados, y la paginación', () => {
    servicio.listar({ q: '  ana ', estado: 'ANULADO', desde: '', hasta: '2026-09-30' }, 20, 10).subscribe();
    const peticion = http.expectOne((r) => r.url === '/pagos');
    expect(peticion.request.method).toBe('GET');
    expect(peticion.request.params.get('q')).toBe('ana');
    expect(peticion.request.params.get('estado')).toBe('ANULADO');
    expect(peticion.request.params.has('desde')).toBe(false);
    expect(peticion.request.params.get('hasta')).toBe('2026-09-30');
    expect(peticion.request.params.get('offset')).toBe('20');
    expect(peticion.request.params.get('limit')).toBe('10');
    peticion.flush({ items: [], total: 0, offset: 20, limit: 10 });
  });

  it('estado consulta /pagos/estado con los filtros', () => {
    servicio.estado({ q: 'ABC', estado: 'VENCIDA' }, 0, 20).subscribe();
    const peticion = http.expectOne((r) => r.url === '/pagos/estado');
    expect(peticion.request.params.get('q')).toBe('ABC');
    expect(peticion.request.params.get('estado')).toBe('VENCIDA');
    expect(peticion.request.params.get('offset')).toBe('0');
    peticion.flush({ items: [], total: 0, offset: 0, limit: 20 });
  });

  it('comprobante pide el pago por su número', () => {
    servicio.comprobante(7).subscribe();
    const peticion = http.expectOne('/pagos/7');
    expect(peticion.request.method).toBe('GET');
    peticion.flush({});
  });

  it('anular envía el motivo a /pagos/{id}/anular', () => {
    servicio.anular(7, 'Cobro duplicado').subscribe();
    const peticion = http.expectOne('/pagos/7/anular');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ motivo: 'Cobro duplicado' });
    peticion.flush({});
  });
});
