import { Celda } from './celda';
import { TipoVehiculo, Vehiculo } from './vehiculo';

export interface EntradaCrear {
  placa: string;
  celda_id: number;
  operador_id: number;
}
export interface SalidaCrear {
  placa: string;
  operador_id: number;
}
export interface Estancia {
  id: number;
  vehiculo_id: number;
  celda_id: number;
  entrada: string;
  salida: string | null;
  operador_entrada_id: number;
  operador_salida_id: number | null;
}
export interface EstadoVehiculo {
  vehiculo: Vehiculo;
  esta_dentro: boolean;
  estancia: (Estancia & { celda: Celda }) | null;
}

export interface PaginaEstancias<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
export interface EstanciaDentro {
  estancia_id: number;
  placa: string;
  tipo: TipoVehiculo;
  celda_codigo: string;
  entrada: string;
}
export type DentroPagina = PaginaEstancias<EstanciaDentro>;
export interface MovimientoHistorial {
  estancia_id: number;
  placa: string;
  celda_codigo: string;
  entrada: string;
  salida: string | null;
  operador_entrada: string;
  operador_salida: string | null;
}
export type HistorialPagina = PaginaEstancias<MovimientoHistorial>;
export interface FiltrosHistorial {
  placa?: string;
  desde?: string;
  hasta?: string;
}
export type EstadoCelda = 'DISPONIBLE' | 'OCUPADA';
export interface CeldaEstado {
  id: number;
  codigo: string;
  tipo: string;
  estado: EstadoCelda;
}
export interface CeldasEstadoPagina extends PaginaEstancias<CeldaEstado> {
  disponibles: number;
  ocupadas: number;
}
