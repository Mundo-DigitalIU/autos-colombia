import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Rol } from '../models/auth';
import { borrarSesionDePrueba, guardarSesionDePrueba } from '../testing/sesion-prueba';
import { pagina, pagoAnuladoPrueba, pagoPrueba } from './datos-prueba';
import { PagosRegistrados } from './pagos-registrados';

describe('Pagos registrados', () => {
  let fixture: ComponentFixture<PagosRegistrados>;
  let http: HttpTestingController;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const texto = () => raiz().textContent ?? '';
  const boton = (nombre: string) =>
    Array.from(raiz().querySelectorAll('button')).find((b) => b.textContent?.trim() === nombre);
  const listar = (cuerpo: object) =>
    http.expectOne((r) => r.url === '/pagos' && r.method === 'GET').flush(cuerpo);

  function crear(rol: Rol): void {
    borrarSesionDePrueba();
    guardarSesionDePrueba(rol);
    TestBed.configureTestingModule({
      imports: [PagosRegistrados],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(PagosRegistrados);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
    borrarSesionDePrueba();
  });

  it('lista fecha, placa, cliente, valor, medio, vigencia, quién registró y estado', () => {
    crear('OPERADOR');
    const peticion = http.expectOne((r) => r.url === '/pagos');
    expect(peticion.request.params.get('offset')).toBe('0');
    expect(peticion.request.params.get('limit')).toBe('10');
    peticion.flush(pagina([pagoPrueba(), pagoAnuladoPrueba({ id: 8, placa: 'DEF456' })]));
    fixture.detectChanges();
    const filas = Array.from(raiz().querySelectorAll('tbody tr'));
    expect(filas.length).toBe(2);
    const primera = filas[0].textContent ?? '';
    for (const dato of ['01/09/2026 12:00', 'ABC123', 'Laura Gómez', '$250.000', 'EFECTIVO',
      '01/09/2026 - 01/10/2026', 'Administrador', 'Registrado']) {
      expect(primera).toContain(dato);
    }
    expect(filas[1].textContent).toContain('Anulado');
  });

  it('cada fila tiene Ver comprobante', () => {
    crear('OPERADOR');
    listar(pagina([pagoPrueba({ id: 42 })]));
    fixture.detectChanges();
    const enlace = raiz().querySelector('tbody a') as HTMLAnchorElement;
    expect(enlace.textContent?.trim()).toBe('Ver comprobante');
    expect(enlace.getAttribute('href')).toBe('/panel/pagos/comprobante/42');
  });

  it('muestra los mensajes vacíos: sin pagos y sin resultados', () => {
    crear('OPERADOR');
    listar(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('Todavía no hay pagos registrados.');
    (raiz().querySelector('#pagos-buscar') as HTMLInputElement).value = 'zzz';
    (raiz().querySelector('#pagos-buscar') as HTMLInputElement).dispatchEvent(new Event('input'));
    (raiz().querySelector('form[role="search"]') as HTMLFormElement).dispatchEvent(new Event('submit'));
    listar(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No hay resultados con ese filtro.');
    expect(texto()).not.toContain('Todavía no hay pagos registrados.');
  });

  it('filtra por texto, estado y fechas', () => {
    crear('OPERADOR');
    listar(pagina([pagoPrueba()]));
    fixture.detectChanges();
    const poner = (id: string, valor: string, evento = 'input') => {
      const campo = raiz().querySelector(id) as HTMLInputElement;
      campo.value = valor;
      campo.dispatchEvent(new Event(evento));
    };
    poner('#pagos-buscar', ' 1000000001 ');
    poner('#pagos-estado', 'ANULADO', 'change');
    poner('#pagos-desde', '2026-09-01');
    poner('#pagos-hasta', '2026-09-30');
    (raiz().querySelector('form[role="search"]') as HTMLFormElement).dispatchEvent(new Event('submit'));
    const peticion = http.expectOne((r) => r.url === '/pagos');
    const p = peticion.request.params;
    expect([p.get('q'), p.get('estado'), p.get('desde'), p.get('hasta'), p.get('offset')]).toEqual([
      '1000000001', 'ANULADO', '2026-09-01', '2026-09-30', '0',
    ]);
    peticion.flush(pagina([pagoAnuladoPrueba()]));
  });

  it('no consulta si la fecha desde es posterior a la hasta', () => {
    crear('OPERADOR');
    listar(pagina([pagoPrueba()]));
    fixture.detectChanges();
    const desde = raiz().querySelector('#pagos-desde') as HTMLInputElement;
    const hasta = raiz().querySelector('#pagos-hasta') as HTMLInputElement;
    desde.value = '2026-09-30';
    desde.dispatchEvent(new Event('input'));
    hasta.value = '2026-09-01';
    hasta.dispatchEvent(new Event('input'));
    (raiz().querySelector('form[role="search"]') as HTMLFormElement).dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    expect(texto()).toContain('La fecha desde no puede ser posterior a la fecha hasta.');
    http.expectNone((r) => r.url === '/pagos');
  });

  it('pagina con Siguiente', () => {
    crear('OPERADOR');
    listar(pagina([pagoPrueba()], 25));
    fixture.detectChanges();
    expect(texto()).toContain('Página 1 de 3');
    boton('Siguiente')!.click();
    const segunda = http.expectOne((r) => r.url === '/pagos');
    expect(segunda.request.params.get('offset')).toBe('10');
    segunda.flush(pagina([pagoPrueba()], 25, 10, 10));
    fixture.detectChanges();
    expect(texto()).toContain('Página 2 de 3');
  });

  it('el operador no ve el botón Anular', () => {
    crear('OPERADOR');
    listar(pagina([pagoPrueba()]));
    fixture.detectChanges();
    expect(boton('Anular')).toBeUndefined();
  });

  it('el administrador ve Anular solo en los pagos REGISTRADO', () => {
    crear('ADMINISTRADOR');
    listar(pagina([pagoPrueba(), pagoAnuladoPrueba({ id: 8 })]));
    fixture.detectChanges();
    const filas = Array.from(raiz().querySelectorAll('tbody tr'));
    expect(filas[0].textContent).toContain('Anular');
    expect(filas[1].textContent).not.toContain('Anular');
    expect(filas[1].textContent).toContain('Ver comprobante');
  });

  it('anular abre el diálogo, anula, muestra "Pago anulado." y actualiza la lista', () => {
    crear('ADMINISTRADOR');
    listar(pagina([pagoPrueba()]));
    fixture.detectChanges();
    boton('Anular')!.click();
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alertdialog"]')?.textContent).toContain('ABC123');
    const motivo = raiz().querySelector('#anular-motivo') as HTMLTextAreaElement;
    motivo.value = 'Cobro duplicado';
    motivo.dispatchEvent(new Event('input'));
    boton('Anular pago')!.click();
    const anulacion = http.expectOne('/pagos/7/anular');
    expect(anulacion.request.body).toEqual({ motivo: 'Cobro duplicado' });
    anulacion.flush(pagoAnuladoPrueba());
    fixture.detectChanges();
    expect(texto()).toContain('Pago anulado.');
    expect(raiz().querySelector('[role="alertdialog"]')).toBeNull();
    listar(pagina([pagoAnuladoPrueba()]));
    fixture.detectChanges();
    expect(raiz().querySelector('tbody')?.textContent).toContain('Anulado');
    expect(boton('Anular')).toBeUndefined();
  });
});
