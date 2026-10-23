import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Entrada } from './entrada';

describe('Registrar entrada', () => {
  let fixture: ComponentFixture<Entrada>;
  let http: HttpTestingController;
  let c: Entrada;
  const operadores = {
    items: [{ id: 2, nombre: 'Operador Portería', telefono: '300' }],
    total: 1,
    offset: 0,
    limit: 1,
  };
  const estancia = {
    id: 20,
    vehiculo_id: 1,
    celda_id: 2,
    entrada: '2026-10-23T20:46:15Z',
    salida: null,
    operador_entrada_id: 2,
    operador_salida_id: null,
  };
  const estado = {
    vehiculo: {
      id: 1,
      placa: 'ABC123',
      marca: 'Mazda',
      color: 'Rojo',
      modelo: 2020,
      tipo: 'AUTOMOVIL',
    },
    esta_dentro: true,
    estancia: { ...estancia, celda: { id: 2, codigo: 'C-01', tipo: 'AUTOMOVIL' } },
  };
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const cargarOperador = () => http.expectOne('/operadores?offset=0&limit=1').flush(operadores);

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Entrada],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Entrada);
    c = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('toma el primer operador al cargar y bloquea el formulario mientras tanto', () => {
    expect(texto()).toContain('Cargando operador');
    expect(c.bloqueado()).toBe(true);
    cargarOperador();
    expect(c.operadorId()).toBe(2);
    expect(c.bloqueado()).toBe(false);
  });

  it('bloquea el registro y avisa si no se puede cargar el operador', () => {
    http.expectOne('/operadores?offset=0&limit=1').flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain(
      'No se pudo cargar el operador',
    );
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http.expectNone('/estancias/entrada');
  });

  it('no envía la petición si la placa está vacía', () => {
    cargarOperador();
    c.form.setValue({ placa: '   ' });
    c.registrar();
    fixture.detectChanges();
    http.expectNone('/estancias/entrada');
    expect(texto()).toContain('Escribe la placa del vehículo.');
  });

  it('registra la entrada sin celda_id y muestra la celda asignada', () => {
    cargarOperador();
    c.form.setValue({ placa: ' abc123 ' });
    c.registrar();
    c.registrar();
    const req = http.expectOne('/estancias/entrada');
    expect(req.request.body).toEqual({ placa: 'ABC123', operador_id: 2 });
    expect(c.saving()).toBe(true);
    req.flush(estancia);
    http.expectOne('/estancias/vehiculo/ABC123').flush(estado);
    fixture.detectChanges();
    expect(texto()).toContain('Entrada registrada');
    expect(texto()).toContain('C-01');
    expect(texto()).toContain('3:46:15');
    expect(c.saving()).toBe(false);
  });

  it('confirma la entrada aunque no se pueda consultar la celda', () => {
    cargarOperador();
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http.expectOne('/estancias/entrada').flush(estancia);
    http.expectOne('/estancias/vehiculo/ABC123').flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(texto()).toContain('Entrada registrada');
    expect(texto()).toContain('No se pudo consultar la celda asignada.');
  });

  it('muestra tal cual el mensaje de la API en los errores 404, 409 y 422', () => {
    cargarOperador();
    for (const [status, detail] of [
      [404, 'Vehículo no registrado.'],
      [409, 'El vehículo ya está dentro.'],
      [409, 'No hay celdas disponibles para este tipo de vehículo.'],
    ] as const) {
      c.form.setValue({ placa: 'ABC123' });
      c.registrar();
      http.expectOne('/estancias/entrada').flush({ detail }, { status, statusText: 'Error' });
      expect(c.error()).toBe(detail);
      expect(c.saving()).toBe(false);
    }
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http
      .expectOne('/estancias/entrada')
      .flush(
        { detail: [{ loc: ['body', 'placa'], msg: 'x', type: 'x' }] },
        { status: 422, statusText: 'Error' },
      );
    expect(c.error()).toContain('no es válida');
  });

  it('avisa si no hay conexión', () => {
    cargarOperador();
    c.form.setValue({ placa: 'ABC123' });
    c.registrar();
    http.expectOne('/estancias/entrada').error(new ProgressEvent('error'));
    expect(c.error()).toContain('No se pudo conectar');
  });
});
