import { TipoVehiculo } from './vehiculo';

export const MEDIOS_PAGO = ['EFECTIVO', 'TRANSFERENCIA', 'TARJETA'] as const;
export type MedioPago = (typeof MEDIOS_PAGO)[number];

export type EstadoPago = 'REGISTRADO' | 'ANULADO';
export type EstadoMensualidad = 'AL_DIA' | 'VENCIDA' | 'SIN_PAGOS';

/** El operador y el valor no viajan: son los de la sesión y la tarifa del tipo de vehículo. */
export interface PagoCrear {
  placa: string;
  medio_pago: MedioPago;
}

export interface PagoAnular {
  motivo: string;
}

/** Pago y comprobante: `id` es el número del comprobante. Las fechas con hora vienen en hora de Bogotá. */
export interface Pago {
  id: number;
  fecha_pago: string;
  cliente_nombre: string;
  cliente_documento: string;
  placa: string;
  tipo: TipoVehiculo;
  valor: number;
  medio_pago: MedioPago;
  /** AAAA-MM-DD */
  vigencia_desde: string;
  /** AAAA-MM-DD */
  vigencia_hasta: string;
  registrado_por: string;
  estado: EstadoPago;
  /** Solo hay datos si el pago está ANULADO; si no, son null. */
  motivo_anulacion: string | null;
  anulado_por: string | null;
  anulado_en: string | null;
}

export interface EstadoMensualidadVehiculo {
  placa: string;
  tipo: TipoVehiculo;
  cliente_nombre: string;
  cliente_documento: string;
  /** Valor mensual de la tarifa del tipo; null si ese tipo no tiene tarifa. */
  tarifa: number | null;
  estado: EstadoMensualidad;
  /** Null si el vehículo no tiene pagos vigentes. */
  vigencia_hasta: string | null;
  ultimo_pago_id: number | null;
}

export interface PagosPagina {
  items: Pago[];
  total: number;
  offset: number;
  limit: number;
}

export interface EstadosMensualidadPagina {
  items: EstadoMensualidadVehiculo[];
  total: number;
  offset: number;
  limit: number;
}

export interface FiltrosPagos {
  /** Documento, nombre del cliente o placa. */
  q?: string;
  estado?: EstadoPago;
  /** AAAA-MM-DD, fecha de pago. */
  desde?: string;
  hasta?: string;
}

export interface FiltrosEstados {
  q?: string;
  estado?: EstadoMensualidad;
}
