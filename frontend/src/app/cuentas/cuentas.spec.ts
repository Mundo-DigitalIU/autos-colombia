import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Cuentas } from './cuentas';

describe('Pantalla de cuentas', () => {
  let fixture: ComponentFixture<Cuentas>;
  let http: HttpTestingController;
  let c: Cuentas;
  const cuenta = {
    id: 7,
    usuario: 'carla',
    rol: 'OPERADOR' as const,
    nombre: 'Carla Ruiz',
    telefono: '3001112233',
    operador_id: 12,
  };
  const pagina = (items: unknown[], total = items.length) => ({
    items,
    total,
    offset: 0,
    limit: 10,
  });
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const listar = (cuerpo = pagina([cuenta])) =>
    http.expectOne((r) => r.url === '/cuentas' && r.method === 'GET').flush(cuerpo);
  const valido = {
    nombre: ' Carla Ruiz ',
    telefono: '3001112233',
    usuario: ' carla ',
    contrasena: 'una-clave-larga',
    rol: 'OPERADOR' as const,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [Cuentas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Cuentas);
    c = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('lista las cuentas con nombre, usuario, rol y teléfono', () => {
    expect(texto()).toContain('Cargando cuentas');
    const peticion = http.expectOne((r) => r.url === '/cuentas');
    expect(peticion.request.params.get('offset')).toBe('0');
    expect(peticion.request.params.get('limit')).toBe('10');
    expect(peticion.request.params.has('q')).toBe(false);
    peticion.flush(pagina([cuenta, { ...cuenta, id: 8, usuario: 'admin', rol: 'ADMINISTRADOR' }]));
    fixture.detectChanges();
    expect(texto()).toContain('Carla Ruiz');
    expect(texto()).toContain('carla');
    expect(texto()).toContain('Administrador');
    expect(texto()).toContain('3001112233');
  });

  it('muestra "Todavía no hay cuentas creadas." cuando no hay ninguna', () => {
    listar(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('Todavía no hay cuentas creadas.');
  });

  it('busca por nombre o usuario volviendo a la primera página', () => {
    listar();
    c.buscador.setValue('  carla ');
    c.buscar();
    const peticion = http.expectOne((r) => r.url === '/cuentas');
    expect(peticion.request.params.get('q')).toBe('carla');
    expect(peticion.request.params.get('offset')).toBe('0');
    peticion.flush(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No hay cuentas con esa búsqueda.');
    c.limpiarBusqueda();
    expect(http.expectOne((r) => r.url === '/cuentas').request.params.has('q')).toBe(false);
  });

  it('muestra el error de carga con el detail de la API', () => {
    http
      .expectOne((r) => r.url === '/cuentas')
      .flush({ detail: 'No tienes permiso para entrar aquí.' }, { status: 403, statusText: 'No' });
    fixture.detectChanges();
    expect(texto()).toContain('No tienes permiso para entrar aquí.');
  });

  it('valida los campos y avisa "Mínimo 8 caracteres."', () => {
    listar();
    c.nueva();
    fixture.detectChanges();
    expect(texto()).toContain('Mínimo 8 caracteres.');
    c.guardar();
    fixture.detectChanges();
    for (const mensaje of [
      'Escribe el nombre.',
      'Escribe el teléfono.',
      'Escribe el usuario.',
      'Escribe la contraseña.',
    ]) {
      expect(texto()).toContain(mensaje);
    }
    c.form.patchValue({ ...valido, contrasena: 'corta' });
    c.guardar();
    fixture.detectChanges();
    expect(c.errorDeCampo('contrasena')).toBe('Mínimo 8 caracteres.');
    http.expectNone((r) => r.method === 'POST');
  });

  it('crea la cuenta con los datos recortados y recarga el listado', () => {
    listar();
    c.nueva();
    c.form.setValue(valido);
    c.guardar();
    c.guardar();
    const peticion = http.expectOne((r) => r.method === 'POST' && r.url === '/cuentas');
    expect(peticion.request.body).toEqual({
      nombre: 'Carla Ruiz',
      telefono: '3001112233',
      usuario: 'carla',
      contrasena: 'una-clave-larga',
      rol: 'OPERADOR',
    });
    peticion.flush(cuenta, { status: 201, statusText: 'Created' });
    listar();
    fixture.detectChanges();
    expect(texto()).toContain('Cuenta carla creada correctamente.');
    expect(c.showForm()).toBe(false);
    expect(c.form.controls.contrasena.value).toBe('');
  });

  it('permite elegir el rol Administrador', () => {
    listar();
    c.nueva();
    c.form.setValue({ ...valido, rol: 'ADMINISTRADOR' });
    c.guardar();
    const peticion = http.expectOne((r) => r.method === 'POST');
    expect(peticion.request.body.rol).toBe('ADMINISTRADOR');
    peticion.flush({ ...cuenta, rol: 'ADMINISTRADOR' }, { status: 201, statusText: 'Created' });
    listar();
  });

  it('muestra tal cual el 409 de usuario repetido y deja el formulario abierto', () => {
    listar();
    c.nueva();
    c.form.setValue(valido);
    c.guardar();
    http
      .expectOne((r) => r.method === 'POST')
      .flush({ detail: 'Ese usuario ya existe.' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    expect(texto()).toContain('Ese usuario ya existe.');
    expect(c.showForm()).toBe(true);
    expect(c.saving()).toBe(false);
  });

  it('marca el campo que rechazó la API en un 422', () => {
    listar();
    c.nueva();
    fixture.detectChanges(); // el formulario debe estar dibujado antes de enviar
    c.form.setValue(valido);
    c.guardar();
    http
      .expectOne((r) => r.method === 'POST')
      .flush(
        {
          detail: [
            {
              loc: ['body', 'contrasena'],
              msg: 'String should have at least 8 characters',
              type: 'x',
            },
          ],
        },
        { status: 422, statusText: 'Error' },
      );
    fixture.detectChanges();
    expect(c.errorDeCampo('contrasena')).toContain('at least 8');
  });

  it('pide confirmación antes de eliminar y recarga al confirmar', () => {
    listar();
    c.confirmarEliminar(cuenta);
    fixture.detectChanges();
    expect(texto()).toContain('Eliminar cuenta carla');
    http.expectNone((r) => r.method === 'DELETE');
    c.cancelar();
    expect(c.pendingDelete()).toBeNull();
    c.confirmarEliminar(cuenta);
    c.eliminar();
    const peticion = http.expectOne((r) => r.method === 'DELETE');
    expect(peticion.request.url).toBe('/cuentas/7');
    peticion.flush(null, { status: 204, statusText: 'No Content' });
    listar(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('Cuenta carla eliminada correctamente.');
    expect(texto()).toContain('Todavía no hay cuentas creadas.');
  });

  it('muestra tal cual "No puedes eliminar tu propia cuenta."', () => {
    listar();
    c.confirmarEliminar(cuenta);
    c.eliminar();
    http
      .expectOne((r) => r.method === 'DELETE')
      .flush(
        { detail: 'No puedes eliminar tu propia cuenta.' },
        { status: 409, statusText: 'Conflict' },
      );
    fixture.detectChanges();
    expect(texto()).toContain('No puedes eliminar tu propia cuenta.');
    expect(c.pendingDelete()).toBeNull();
  });

  it('pagina de diez en diez', () => {
    listar(pagina([cuenta], 25));
    expect(c.pages()).toBe(3);
    c.load(10);
    const peticion = http.expectOne((r) => r.url === '/cuentas');
    expect(peticion.request.params.get('offset')).toBe('10');
    peticion.flush({ items: [cuenta], total: 25, offset: 10, limit: 10 });
    expect(c.page()).toBe(2);
  });
});
