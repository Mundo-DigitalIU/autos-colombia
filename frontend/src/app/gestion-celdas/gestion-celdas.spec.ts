import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CeldaEstado } from '../models/estancia';
import { GestionCeldas } from './gestion-celdas';

describe('Pantalla Gestionar celdas', () => {
  let fixture: ComponentFixture<GestionCeldas>;
  let http: HttpTestingController;
  let c: GestionCeldas;
  const libre: CeldaEstado = { id: 1, codigo: 'M-01', tipo: 'MOTO', estado: 'DISPONIBLE' };
  const ocupada: CeldaEstado = { id: 2, codigo: 'A-01', tipo: 'AUTOMOVIL', estado: 'OCUPADA' };
  const pagina = (items: CeldaEstado[], total = items.length) => ({
    items,
    total,
    disponibles: 1,
    ocupadas: 1,
    offset: 0,
    limit: 10,
  });
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const listar = (cuerpo: object = pagina([libre, ocupada])) =>
    http.expectOne((r) => r.url === '/estancias/celdas').flush(cuerpo);
  const guardada = { id: 9, codigo: 'M-09', tipo: 'MOTO' };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [GestionCeldas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(GestionCeldas);
    c = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('lista código, tipo y estado, con los contadores', () => {
    const peticion = http.expectOne((r) => r.url === '/estancias/celdas');
    expect(peticion.request.params.get('limit')).toBe('10');
    expect(peticion.request.params.has('q')).toBe(false);
    peticion.flush(pagina([libre, ocupada]));
    fixture.detectChanges();
    expect(texto()).toContain('M-01');
    expect(texto()).toContain('AUTOMOVIL');
    expect(texto()).toContain('Ocupada');
    expect(texto()).toContain('Disponible');
    expect(texto()).toContain('1 disponibles · 1 ocupadas');
    expect(texto()).toContain('Editar');
    expect(texto()).toContain('Eliminar');
  });

  it('muestra "No hay celdas con ese filtro." cuando la lista llega vacía', () => {
    listar(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No hay celdas con ese filtro.');
  });

  it('envía el código, el tipo y el estado como filtros y vuelve a la primera página', () => {
    listar();
    c.buscador.setValue(' m-0 ');
    c.filtroTipo.setValue('MOTO');
    c.filtroEstado.setValue('OCUPADA');
    c.buscar();
    const peticion = http.expectOne((r) => r.url === '/estancias/celdas');
    expect(peticion.request.params.get('q')).toBe('m-0');
    expect(peticion.request.params.get('tipo')).toBe('MOTO');
    expect(peticion.request.params.get('estado')).toBe('OCUPADA');
    expect(peticion.request.params.get('offset')).toBe('0');
    peticion.flush(pagina([]));
    c.limpiarFiltros();
    const limpia = http.expectOne((r) => r.url === '/estancias/celdas');
    expect(limpia.request.params.has('q')).toBe(false);
    expect(limpia.request.params.has('tipo')).toBe(false);
    expect(limpia.request.params.has('estado')).toBe(false);
    limpia.flush(pagina([libre]));
  });

  it('muestra el error de carga con el detail de la API', () => {
    http
      .expectOne((r) => r.url === '/estancias/celdas')
      .flush({ detail: 'No tienes permiso para entrar aquí.' }, { status: 403, statusText: 'No' });
    fixture.detectChanges();
    expect(texto()).toContain('No tienes permiso para entrar aquí.');
  });

  it('el tipo es un select con MOTO, AUTOMOVIL y CAMIONETA', () => {
    listar();
    c.nueva();
    fixture.detectChanges();
    const select = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>(
      '#celda-tipo',
    )!;
    expect(Array.from(select.options).map((o) => o.value)).toEqual([
      '',
      'MOTO',
      'AUTOMOVIL',
      'CAMIONETA',
    ]);
    expect(c.tipoBloqueado()).toBe(false);
  });

  it('pide código y tipo antes de enviar', () => {
    listar();
    c.nueva();
    c.guardar();
    fixture.detectChanges();
    expect(texto()).toContain('Escribe el código de la celda.');
    expect(texto()).toContain('Selecciona el tipo.');
    http.expectNone((r) => r.method === 'POST');
  });

  it('crea una celda y recarga el listado', () => {
    listar();
    c.nueva();
    c.form.setValue({ codigo: ' m-09 ', tipo: 'MOTO' });
    c.guardar();
    c.guardar();
    const peticion = http.expectOne((r) => r.method === 'POST' && r.url === '/celdas');
    expect(peticion.request.body).toEqual({ codigo: 'm-09', tipo: 'MOTO' });
    peticion.flush(guardada, { status: 201, statusText: 'Created' });
    listar();
    fixture.detectChanges();
    expect(texto()).toContain('Celda M-09 creada correctamente.');
    expect(c.showForm()).toBe(false);
  });

  it('muestra tal cual el 409 de código repetido', () => {
    listar();
    c.nueva();
    c.form.setValue({ codigo: 'M-01', tipo: 'MOTO' });
    c.guardar();
    http
      .expectOne((r) => r.method === 'POST')
      .flush({ detail: 'Ese código de celda ya existe.' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    expect(texto()).toContain('Ese código de celda ya existe.');
    expect(c.showForm()).toBe(true);
  });

  it('muestra el mensaje del servidor si rechaza el código vacío con un 422', () => {
    listar();
    c.nueva();
    c.form.setValue({ codigo: 'X', tipo: 'MOTO' });
    c.guardar();
    http
      .expectOne((r) => r.method === 'POST')
      .flush(
        {
          detail: [
            {
              loc: ['body', 'codigo'],
              msg: 'Escribe el código de la celda.',
              type: 'codigo_vacio',
            },
          ],
        },
        { status: 422, statusText: 'Error' },
      );
    expect(c.errorCodigo()).toBe('Escribe el código de la celda.');
  });

  it('edita una celda libre: el tipo se puede cambiar y se envía PATCH', () => {
    listar();
    c.editar(libre);
    fixture.detectChanges();
    expect(texto()).toContain('Editar celda');
    expect(c.form.controls.tipo.disabled).toBe(false);
    expect(texto()).not.toContain('No puedes cambiar el tipo mientras la celda está ocupada.');
    c.form.setValue({ codigo: 'M-11', tipo: 'CAMIONETA' });
    c.guardar();
    const peticion = http.expectOne((r) => r.method === 'PATCH' && r.url === '/celdas/1');
    expect(peticion.request.body).toEqual({ codigo: 'M-11', tipo: 'CAMIONETA' });
    peticion.flush({ id: 1, codigo: 'M-11', tipo: 'CAMIONETA' });
    listar();
    fixture.detectChanges();
    expect(texto()).toContain('Celda M-11 actualizada correctamente.');
  });

  it('bloquea el tipo con aviso si la celda está ocupada, pero deja cambiar el código', () => {
    listar();
    c.editar(ocupada);
    fixture.detectChanges();
    const select = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>(
      '#celda-tipo',
    )!;
    expect(select.disabled).toBe(true);
    expect(c.tipoBloqueado()).toBe(true);
    expect(texto()).toContain('No puedes cambiar el tipo mientras la celda está ocupada.');
    c.form.controls.codigo.setValue('A-99');
    c.guardar();
    const peticion = http.expectOne((r) => r.method === 'PATCH' && r.url === '/celdas/2');
    expect(peticion.request.body).toEqual({ codigo: 'A-99', tipo: 'AUTOMOVIL' });
    peticion.flush({ id: 2, codigo: 'A-99', tipo: 'AUTOMOVIL' });
    listar();
  });

  it('muestra tal cual el 409 si la API rechaza el cambio de tipo', () => {
    listar();
    c.editar(libre);
    c.form.setValue({ codigo: 'M-01', tipo: 'AUTOMOVIL' });
    c.guardar();
    http
      .expectOne((r) => r.method === 'PATCH')
      .flush(
        { detail: 'No puedes cambiar el tipo mientras la celda está ocupada.' },
        { status: 409, statusText: 'Conflict' },
      );
    fixture.detectChanges();
    expect(texto()).toContain('No puedes cambiar el tipo mientras la celda está ocupada.');
  });

  it('pide confirmación antes de eliminar y recarga al confirmar', () => {
    listar();
    c.confirmarEliminar(libre);
    fixture.detectChanges();
    expect(texto()).toContain('Eliminar celda M-01');
    http.expectNone((r) => r.method === 'DELETE');
    c.eliminar();
    const peticion = http.expectOne((r) => r.method === 'DELETE');
    expect(peticion.request.url).toBe('/celdas/1');
    peticion.flush(null, { status: 204, statusText: 'No Content' });
    listar(pagina([ocupada]));
    fixture.detectChanges();
    expect(texto()).toContain('Celda M-01 eliminada correctamente.');
  });

  it('muestra tal cual el 409 de una celda con historial', () => {
    const detail = 'No se puede eliminar: esta celda ya tuvo entradas y salidas registradas.';
    listar();
    c.confirmarEliminar(libre);
    c.eliminar();
    http
      .expectOne((r) => r.method === 'DELETE')
      .flush({ detail }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    expect(texto()).toContain(detail);
    expect(c.pendingDelete()).toBeNull();
  });
});
