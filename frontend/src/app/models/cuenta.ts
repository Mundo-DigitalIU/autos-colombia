import { Rol } from './auth';

export interface CuentaCrear {
  nombre: string;
  telefono: string;
  usuario: string;
  contrasena: string;
  rol: Rol;
}
export interface Cuenta {
  id: number;
  usuario: string;
  rol: Rol;
  nombre: string;
  telefono: string;
  operador_id: number;
}
export interface CuentasPagina {
  items: Cuenta[];
  total: number;
  offset: number;
  limit: number;
}
