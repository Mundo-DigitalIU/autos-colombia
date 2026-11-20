import { EstadoMensualidadVehiculo, Pago } from '../models/pago';

/** Datos de ejemplo para las pruebas de las pantallas de pagos. */
export const pagoPrueba = (cambios: Partial<Pago> = {}): Pago => ({
  id: 7,
  fecha_pago: '2026-09-01T12:00:00-05:00',
  cliente_nombre: 'Laura Gómez',
  cliente_documento: '1000000001',
  placa: 'ABC123',
  tipo: 'AUTOMOVIL',
  valor: 250000,
  medio_pago: 'EFECTIVO',
  vigencia_desde: '2026-09-01',
  vigencia_hasta: '2026-10-01',
  registrado_por: 'Administrador',
  estado: 'REGISTRADO',
  motivo_anulacion: null,
  anulado_por: null,
  anulado_en: null,
  ...cambios,
});

export const pagoAnuladoPrueba = (cambios: Partial<Pago> = {}): Pago =>
  pagoPrueba({
    estado: 'ANULADO',
    motivo_anulacion: 'Cobro duplicado',
    anulado_por: 'Administrador',
    anulado_en: '2026-09-02T09:30:00-05:00',
    ...cambios,
  });

export const mensualidadPrueba = (
  cambios: Partial<EstadoMensualidadVehiculo> = {},
): EstadoMensualidadVehiculo => ({
  placa: 'ABC123',
  tipo: 'AUTOMOVIL',
  cliente_nombre: 'Laura Gómez',
  cliente_documento: '1000000001',
  tarifa: 250000,
  estado: 'AL_DIA',
  vigencia_hasta: '2026-10-01',
  ultimo_pago_id: 7,
  ...cambios,
});

export const pagina = <T>(items: T[], total = items.length, limit = 10, offset = 0) => ({
  items,
  total,
  offset,
  limit,
});
