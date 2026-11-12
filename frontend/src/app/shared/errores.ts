import { HttpErrorResponse } from '@angular/common/http';
import { MENSAJE_SIN_PERMISO } from '../models/auth';

export const SIN_CONEXION =
  'No se pudo conectar con el servicio. Comprueba la conexión y vuelve a intentarlo.';

/**
 * Mensaje para mostrar al usuario: el `detail` de la API tal cual cuando es texto,
 * el aviso de permiso en un 403 y, si no, el mensaje de respaldo.
 */
export function mensajeApi(error: unknown, respaldo = SIN_CONEXION): string {
  if (!(error instanceof HttpErrorResponse)) return respaldo;
  const detail = (error.error as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (error.status === 403) return MENSAJE_SIN_PERMISO;
  return respaldo;
}

/** Mensajes de validación (422) por campo: `{ campo: mensaje }`, tal como los devuelve la API. */
export function erroresDeCampo(error: unknown): Record<string, string> {
  const resultado: Record<string, string> = {};
  if (!(error instanceof HttpErrorResponse) || error.status !== 422) return resultado;
  const detail = (error.error as { detail?: unknown } | null)?.detail;
  if (!Array.isArray(detail)) return resultado;
  for (const item of detail as { loc?: unknown[]; msg?: unknown }[]) {
    const campo = item.loc?.at(-1);
    if (typeof campo === 'string' && typeof item.msg === 'string' && !(campo in resultado)) {
      resultado[campo] = item.msg.replace(/^Value error, /, '');
    }
  }
  return resultado;
}
