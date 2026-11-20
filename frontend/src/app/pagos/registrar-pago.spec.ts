import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { mensualidadPrueba, pagina, pagoPrueba } from './datos-prueba';
import { RegistrarPago } from './registrar-pago';

describe('Registrar pago', () => {
  let fixture: ComponentFixture<RegistrarPago>;
  let http: HttpTestingController;
  let router: Router;
  const raiz = () => fixture.nativeElement as HTMLElement;
  const texto = () => raiz().textContent ?? '';
  const boton = (nombre: string) =>
    Array.from(raiz().querySelectorAll('button')).find((b) => b.textContent?.trim() === nombre)!;
  const escribir = (id: string, valor: string, evento = 'input') => {
    const campo = raiz().querySelector(id) as HTMLInputElement;
    campo.value = valor;
    campo.dispatchEvent(new Event(evento));
  };

  function crear(placaEnUrl?: string): void {
    TestBed.configureTestingModule({
      imports: [RegistrarPago],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        ...(placaEnUrl
          ? [{ provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: new Map([['placa', placaEnUrl]]) } } }]
          : []),
      ],
    });
    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(RegistrarPago);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
    vi.useRealTimers();
  });

  it('si falta un campo, muestra el aviso en el campo y no llama a la API', () => {
    crear();
    boton('Guardar pago').click();
    fixture.detectChanges();
    expect(texto()).toContain('Escribe la placa.');
    expect(texto()).toContain('Selecciona el medio de pago.');
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain('Revisa los campos');
    http.expectNone('/pagos');
  });

  it('ofrece los tres medios de pago', () => {
    crear();
    const opciones = Array.from(raiz().querySelectorAll('#pago-medio option')).map((o) => o.textContent?.trim());
    expect(opciones).toEqual(['Selecciona…', 'EFECTIVO', 'TRANSFERENCIA', 'TARJETA']);
  });

  it('al escribir la placa muestra cliente, tipo, tarifa y la vigencia que quedaría', () => {
    vi.useFakeTimers();
    crear();
    escribir('#pago-placa', ' abc123 ');
    vi.advanceTimersByTime(300);
    const consulta = http.expectOne((r) => r.url === '/pagos/estado');
    expect(consulta.request.params.get('q')).toBe('ABC123');
    consulta.flush(pagina([mensualidadPrueba({ vigencia_hasta: '2026-10-01' })]));
    fixture.detectChanges();
    const resumen = raiz().querySelector('dl')?.textContent ?? '';
    for (const dato of ['Laura Gómez', 'AUTOMOVIL', '$250.000', 'Vigente desde 01/10/2026 hasta 31/10/2026']) {
      expect(resumen).toContain(dato);
    }
  });

  it('un vehículo sin pagos cuenta la vigencia desde hoy (hora de Bogotá)', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-02T03:00:00Z')); // en Bogotá todavía es 1 de septiembre
    crear();
    escribir('#pago-placa', 'DEF456');
    vi.advanceTimersByTime(300);
    http
      .expectOne((r) => r.url === '/pagos/estado')
      .flush(pagina([mensualidadPrueba({ placa: 'DEF456', estado: 'SIN_PAGOS', vigencia_hasta: null, ultimo_pago_id: null })]));
    fixture.detectChanges();
    expect(texto()).toContain('Vigente desde 01/09/2026 hasta 01/10/2026');
  });

  it('avisa si no hay un vehículo con cliente para esa placa', () => {
    vi.useFakeTimers();
    crear();
    escribir('#pago-placa', 'ZZZ999');
    vi.advanceTimersByTime(300);
    http.expectOne((r) => r.url === '/pagos/estado').flush(pagina([]));
    fixture.detectChanges();
    expect(texto()).toContain('No encontramos un vehículo con cliente para esa placa.');
  });

  it('abre con la placa escrita cuando viene de Mensualidades', () => {
    vi.useFakeTimers();
    crear('mno345');
    expect((raiz().querySelector('#pago-placa') as HTMLInputElement).value).toBe('MNO345');
    vi.advanceTimersByTime(300);
    http
      .expectOne((r) => r.url === '/pagos/estado')
      .flush(pagina([mensualidadPrueba({ placa: 'MNO345' })]));
  });

  it('guarda el pago, avisa y abre el comprobante', () => {
    crear();
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    escribir('#pago-placa', ' abc123 ');
    escribir('#pago-medio', 'TRANSFERENCIA', 'change');
    boton('Guardar pago').click();
    const peticion = http.expectOne('/pagos');
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.body).toEqual({ placa: 'ABC123', medio_pago: 'TRANSFERENCIA' });
    peticion.flush(pagoPrueba({ id: 21 }));
    expect(navegar).toHaveBeenCalledWith(['/panel/pagos/comprobante', 21], {
      state: { aviso: 'Pago registrado.' },
    });
    http.match((r) => r.url === '/pagos/estado').forEach((r) => r.flush(pagina([])));
  });

  it('muestra los errores de la API tal cual, sin códigos técnicos', () => {
    crear();
    escribir('#pago-placa', 'ABC123');
    escribir('#pago-medio', 'EFECTIVO', 'change');
    for (const [estado, detail] of [
      [409, 'La mensualidad de este vehículo ya está pagada.'],
      [404, 'Vehículo no encontrado.'],
      [409, 'El vehículo no tiene un cliente asociado.'],
    ] as const) {
      boton('Guardar pago').click();
      http.expectOne('/pagos').flush({ detail }, { status: estado, statusText: 'x' });
      fixture.detectChanges();
      const alerta = raiz().querySelector('[role="alert"]')?.textContent ?? '';
      expect(alerta).toContain(detail);
      expect(alerta).not.toMatch(/40\d|HttpErrorResponse/);
    }
    http.match((r) => r.url === '/pagos/estado').forEach((r) => r.flush(pagina([])));
  });

  it('Cancelar vuelve a Pagos sin guardar', () => {
    crear();
    const navegar = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    boton('Cancelar').click();
    expect(navegar).toHaveBeenCalledWith('/panel/pagos');
    http.expectNone('/pagos');
  });
});
