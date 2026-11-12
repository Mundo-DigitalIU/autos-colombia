import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Salida } from './salida';

describe('Registrar salida', () => {
  let fixture: ComponentFixture<Salida>;
  let http: HttpTestingController;
  let c: Salida;
  const estancia = {
    id: 20,
    vehiculo_id: 1,
    celda_id: 2,
    entrada: '2026-10-23T20:46:15Z',
    salida: '2026-10-23T22:00:00Z',
    operador_entrada_id: 2,
    operador_salida_id: 2,
  };
  const celda = { id: 2, codigo: 'C-01', tipo: 'AUTOMOVIL' };
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Salida],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Salida);
    c = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('no envía la petición si la placa está vacía', () => {
    c.form.setValue({ placa: '' });
    c.registrar();
    fixture.detectChanges();
    http.expectNone('/estancias/salida');
    expect(texto()).toContain('Escribe la placa del vehículo.');
  });

  it('registra la salida con placa y operador y muestra la celda liberada', () => {
    c.form.setValue({ placa: ' abc123 ' });
    c.registrar();
    c.registrar();
    const req = http.expectOne('/estancias/salida');
    expect(req.request.body).toEqual({ placa: 'ABC123' });
    expect(c.saving()).toBe(true);
    req.flush(estancia);
    http.expectOne('/celdas/2').flush(celda);
    fixture.detectChanges();
    expect(texto()).toContain('Salida registrada');
    expect(texto()).toContain('C-01');
    expect(texto()).toContain('5:00:00');
    expect(c.saving()).toBe(false);
  });

  it('confirma la salida aunque no se pueda consultar la celda', () => {
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http.expectOne('/estancias/salida').flush(estancia);
    http.expectOne('/celdas/2').flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(texto()).toContain('Salida registrada');
    expect(texto()).toContain('No se pudo consultar la celda liberada.');
  });

  it('muestra tal cual el mensaje de la API en los errores 404, 409 y 422', () => {
    for (const [status, detail] of [
      [404, 'Vehículo no registrado.'],
      [409, 'El vehículo no está dentro del parqueadero.'],
    ] as const) {
      c.form.setValue({ placa: 'ABC123' });
      c.registrar();
      http.expectOne('/estancias/salida').flush({ detail }, { status, statusText: 'Error' });
      expect(c.error()).toBe(detail);
      expect(c.saving()).toBe(false);
    }
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http
      .expectOne('/estancias/salida')
      .flush(
        { detail: [{ loc: ['body', 'placa'], msg: 'x', type: 'x' }] },
        { status: 422, statusText: 'Error' },
      );
    expect(c.error()).toContain('no es válida');
  });

  it('avisa si no hay conexión', () => {
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http.expectOne('/estancias/salida').error(new ProgressEvent('error'));
    expect(c.error()).toContain('No se pudo conectar');
  });

  it('el formulario no pide operador y el cuerpo solo lleva la placa', () => {
    expect(fixture.nativeElement.querySelector('select')).toBeNull();
    expect(texto()).not.toContain('operador');
    expect(Object.keys(c.form.controls)).toEqual(['placa']);
    expect(c.bloqueado()).toBe(false);
    c.form.setValue({ placa: 'abc123' });
    c.registrar();
    const req = http.expectOne('/estancias/salida');
    expect(Object.keys(req.request.body)).toEqual(['placa']);
    req.flush({}, { status: 403, statusText: 'Prohibido' });
    expect(c.error()).toBe('No tienes permiso para entrar aquí.');
  });
});
