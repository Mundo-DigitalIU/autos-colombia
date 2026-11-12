import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Rol } from '../models/auth';
import { Cliente } from '../models/cliente';
import { Vehiculo } from '../models/vehiculo';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { Clientes } from './clientes';

describe('Pantalla de clientes', () => {
  let fixture: ComponentFixture<Clientes>;
  let http: HttpTestingController;
  let c: Clientes;
  const vehiculo: Vehiculo = {
    id: 3,
    placa: 'ABC123',
    tipo: 'AUTOMOVIL',
    color: 'Rojo',
    marca: 'Mazda',
    modelo: 2020,
  };
  const cliente: Cliente = {
    id: 5,
    nombre: 'Laura Gómez',
    documento: '1000000001',
    telefono: '3101112233',
    vehiculos: [vehiculo, { ...vehiculo, id: 4, placa: 'ABC12D', tipo: 'MOTO' }],
  };
  const pagina = (items: unknown[], total = items.length) => ({
    items,
    total,
    offset: 0,
    limit: 10,
  });
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const listar = (cuerpo: object = pagina([cliente])) =>
    http.expectOne((r) => r.url === '/clientes' && r.method === 'GET').flush(cuerpo);
  const llenarVehiculo = (i: number, datos: Record<string, unknown> = {}) =>
    c.vehiculos.at(i).patchValue({
      placa: ' abc999 ',
      tipo: 'MOTO',
      color: ' Negro ',
      marca: ' Honda ',
      modelo: 2022,
      ...datos,
    });

  function crear(rol: Rol): void {
    borrarSesionDePrueba();
    guardarSesionDePrueba(rol);
    TestBed.configureTestingModule({
      imports: [Clientes],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Clientes);
    c = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
    borrarSesionDePrueba();
  });

  describe('como operador', () => {
    beforeEach(() => crear('OPERADOR'));

    it('lista clientes con sus placas y sin botones de editar ni eliminar', () => {
      const peticion = http.expectOne((r) => r.url === '/clientes');
      expect(peticion.request.params.get('limit')).toBe('10');
      peticion.flush(pagina([cliente]));
      fixture.detectChanges();
      expect(texto()).toContain('Laura Gómez');
      expect(texto()).toContain('1000000001');
      expect(texto()).toContain('ABC123, ABC12D');
      expect(texto()).not.toContain('Editar');
      expect(texto()).not.toContain('Eliminar');
      expect(texto()).not.toContain('Acciones');
    });

    it('muestra "Todavía no hay clientes registrados." si no hay ninguno', () => {
      listar(pagina([]));
      fixture.detectChanges();
      expect(texto()).toContain('Todavía no hay clientes registrados.');
    });

    it('busca por documento, nombre o placa desde la primera página', () => {
      listar();
      c.buscador.setValue(' abc12d ');
      c.buscar();
      const peticion = http.expectOne((r) => r.url === '/clientes');
      expect(peticion.request.params.get('q')).toBe('abc12d');
      expect(peticion.request.params.get('offset')).toBe('0');
      peticion.flush(pagina([]));
      fixture.detectChanges();
      expect(texto()).toContain('No hay clientes con esa búsqueda.');
      c.limpiarBusqueda();
      expect(http.expectOne((r) => r.url === '/clientes').request.params.has('q')).toBe(false);
    });

    it('un operador no puede editar ni eliminar aunque llame a los métodos', () => {
      listar();
      c.editar(cliente);
      c.confirmarEliminar(cliente);
      expect(c.pendingDelete()).toBeNull();
      http.expectNone((r) => r.method === 'GET' && r.url === '/clientes/5');
    });

    it('empieza con un vehículo y permite agregar y quitar bloques', () => {
      listar();
      c.nuevo();
      fixture.detectChanges();
      expect(c.vehiculos.length).toBe(1);
      expect(texto()).not.toContain('Quitar vehículo');
      c.agregarVehiculo();
      fixture.detectChanges();
      expect(c.vehiculos.length).toBe(2);
      expect(texto()).toContain('Vehículo 2');
      c.quitarVehiculo(1);
      c.quitarVehiculo(0);
      expect(c.vehiculos.length).toBe(1);
    });

    it('valida cliente y vehículo antes de enviar', () => {
      listar();
      c.nuevo();
      fixture.detectChanges();
      c.guardar();
      fixture.detectChanges();
      for (const mensaje of [
        'Escribe el nombre.',
        'Escribe el documento.',
        'Escribe el teléfono.',
        'Escribe la placa.',
        'Selecciona el tipo.',
        'Escribe el color.',
        'Escribe la marca.',
        'Escribe un año entre 1 y 9999.',
      ]) {
        expect(texto()).toContain(mensaje);
      }
      llenarVehiculo(0, { modelo: 0 });
      c.guardar();
      expect(c.errorVehiculo(0, 'modelo')).toBe('Escribe un año entre 1 y 9999.');
      http.expectNone((r) => r.method === 'POST');
    });

    it('registra un cliente con dos vehículos con los datos normalizados', () => {
      listar();
      c.nuevo();
      c.form.patchValue({ nombre: ' Ana Pérez ', documento: ' 123 ', telefono: ' 300 ' });
      c.agregarVehiculo();
      llenarVehiculo(0);
      llenarVehiculo(1, {
        placa: 'xyz12a',
        tipo: 'AUTOMOVIL',
        color: 'Gris',
        marca: 'Kia',
        modelo: 2018,
      });
      c.guardar();
      c.guardar();
      const peticion = http.expectOne((r) => r.method === 'POST' && r.url === '/clientes');
      expect(peticion.request.body).toEqual({
        nombre: 'Ana Pérez',
        documento: '123',
        telefono: '300',
        vehiculos: [
          { placa: 'ABC999', tipo: 'MOTO', color: 'Negro', marca: 'Honda', modelo: 2022 },
          { placa: 'XYZ12A', tipo: 'AUTOMOVIL', color: 'Gris', marca: 'Kia', modelo: 2018 },
        ],
      });
      peticion.flush(cliente, { status: 201, statusText: 'Created' });
      listar();
      fixture.detectChanges();
      expect(texto()).toContain('Cliente Laura Gómez registrado correctamente.');
      expect(c.showForm()).toBe(false);
    });

    it('muestra tal cual los 409 de documento y de placa repetidos', () => {
      listar();
      for (const detail of [
        'Ya hay un cliente con ese documento.',
        'Esa placa ya está registrada.',
      ]) {
        c.nuevo();
        c.form.patchValue({ nombre: 'Ana', documento: '123', telefono: '300' });
        llenarVehiculo(0);
        c.guardar();
        http
          .expectOne((r) => r.method === 'POST')
          .flush({ detail }, { status: 409, statusText: 'Conflict' });
        fixture.detectChanges();
        expect(texto()).toContain(detail);
        expect(c.showForm()).toBe(true);
        expect(c.saving()).toBe(false);
      }
    });
  });

  describe('como administrador', () => {
    beforeEach(() => crear('ADMINISTRADOR'));

    it('ve las acciones de editar y eliminar', () => {
      listar();
      fixture.detectChanges();
      expect(texto()).toContain('Acciones');
      expect(texto()).toContain('Editar');
      expect(texto()).toContain('Eliminar');
    });

    it('edita: carga el cliente, envía PUT con los ids de sus vehículos y recarga', () => {
      listar();
      c.editar(cliente);
      http.expectOne((r) => r.method === 'GET' && r.url === '/clientes/5').flush(cliente);
      fixture.detectChanges();
      expect(c.editing()).toBe(5);
      expect(c.vehiculos.length).toBe(2);
      expect(texto()).toContain('Editar cliente');
      c.form.patchValue({ nombre: 'Laura G.' });
      c.vehiculos.at(0).patchValue({ color: 'Azul' });
      c.agregarVehiculo();
      llenarVehiculo(2, { placa: 'nueva1' });
      c.guardar();
      const peticion = http.expectOne((r) => r.method === 'PUT' && r.url === '/clientes/5');
      expect(peticion.request.body.nombre).toBe('Laura G.');
      expect(peticion.request.body.vehiculos.map((v: { id?: number }) => v.id)).toEqual([
        3,
        4,
        undefined,
      ]);
      expect(peticion.request.body.vehiculos[0].color).toBe('Azul');
      expect(peticion.request.body.vehiculos[2].placa).toBe('NUEVA1');
      peticion.flush({ ...cliente, nombre: 'Laura G.' });
      listar();
      fixture.detectChanges();
      expect(texto()).toContain('Cliente Laura G. actualizado correctamente.');
    });

    it('al editar muestra tal cual el conflicto de la API', () => {
      listar();
      c.editar(cliente);
      http.expectOne((r) => r.url === '/clientes/5').flush(cliente);
      c.guardar();
      http
        .expectOne((r) => r.method === 'PUT')
        .flush(
          { detail: 'Esa placa ya está registrada.' },
          { status: 409, statusText: 'Conflict' },
        );
      fixture.detectChanges();
      expect(texto()).toContain('Esa placa ya está registrada.');
    });

    it('elimina un cliente tras confirmar', () => {
      listar();
      c.confirmarEliminar(cliente);
      fixture.detectChanges();
      expect(texto()).toContain('Eliminar cliente Laura Gómez');
      http.expectNone((r) => r.method === 'DELETE');
      c.eliminar();
      const peticion = http.expectOne((r) => r.method === 'DELETE');
      expect(peticion.request.url).toBe('/clientes/5');
      peticion.flush(null, { status: 204, statusText: 'No Content' });
      listar(pagina([]));
      fixture.detectChanges();
      expect(texto()).toContain('Cliente Laura Gómez eliminado correctamente.');
      expect(texto()).toContain('Todavía no hay clientes registrados.');
    });

    it('muestra tal cual el 409 cuando los vehículos ya tienen entradas y salidas', () => {
      const detail =
        'No se puede eliminar: sus vehículos ya tienen entradas y salidas registradas.';
      listar();
      c.confirmarEliminar(cliente);
      c.eliminar();
      http
        .expectOne((r) => r.method === 'DELETE')
        .flush({ detail }, { status: 409, statusText: 'Conflict' });
      fixture.detectChanges();
      expect(texto()).toContain(detail);
      expect(c.pendingDelete()).toBeNull();
    });

    it('elimina un vehículo guardado desde la edición, con confirmación', () => {
      listar();
      c.editar(cliente);
      http.expectOne((r) => r.url === '/clientes/5').flush(cliente);
      fixture.detectChanges();
      expect(c.esGuardado(0)).toBe(true);
      c.confirmarEliminarVehiculo(1);
      fixture.detectChanges();
      expect(texto()).toContain('Eliminar el vehículo ABC12D');
      http.expectNone((r) => r.method === 'DELETE');
      c.eliminarVehiculo();
      const peticion = http.expectOne((r) => r.method === 'DELETE');
      expect(peticion.request.url).toBe('/clientes/5/vehiculos/4');
      peticion.flush(null, { status: 204, statusText: 'No Content' });
      listar();
      expect(c.vehiculos.length).toBe(1);
      expect(c.success()).toContain('Vehículo ABC12D eliminado correctamente.');
    });

    it('muestra tal cual el 409 al eliminar un vehículo con historial', () => {
      const detail =
        'No se puede eliminar: sus vehículos ya tienen entradas y salidas registradas.';
      listar();
      c.editar(cliente);
      http.expectOne((r) => r.url === '/clientes/5').flush(cliente);
      c.confirmarEliminarVehiculo(0);
      c.eliminarVehiculo();
      http
        .expectOne((r) => r.method === 'DELETE')
        .flush({ detail }, { status: 409, statusText: 'Conflict' });
      fixture.detectChanges();
      expect(texto()).toContain(detail);
      expect(c.vehiculos.length).toBe(2);
    });
  });
});
