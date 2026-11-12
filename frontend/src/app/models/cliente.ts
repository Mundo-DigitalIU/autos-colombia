import { Vehiculo, VehiculoCrear } from './vehiculo';

export interface ClienteCrear {
  nombre: string;
  documento: string;
  telefono: string;
  vehiculos: VehiculoCrear[];
}
/** En la edición, un vehículo con `id` se modifica y uno sin `id` se crea; los demás se conservan. */
export interface ClienteActualizar {
  nombre: string;
  documento: string;
  telefono: string;
  vehiculos: (VehiculoCrear & { id?: number })[];
}
export interface Cliente {
  id: number;
  nombre: string;
  documento: string;
  telefono: string;
  vehiculos: Vehiculo[];
}
export interface ClientesPagina {
  items: Cliente[];
  total: number;
  offset: number;
  limit: number;
}
