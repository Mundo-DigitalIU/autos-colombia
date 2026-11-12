export type Rol = 'ADMINISTRADOR' | 'OPERADOR';

export interface LoginCrear {
  usuario: string;
  contrasena: string;
}
export interface LoginRespuesta {
  token: string;
  rol: Rol;
  nombre: string;
  expira: string;
}

export const MENSAJE_SESION_TERMINADA = 'Tu sesión terminó. Inicia sesión otra vez.';
export const MENSAJE_SIN_PERMISO = 'No tienes permiso para entrar aquí.';
export const MENSAJE_SESION_CERRADA = 'Cerraste sesión.';
