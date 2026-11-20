import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import {
  EstadosMensualidadPagina,
  FiltrosEstados,
  FiltrosPagos,
  Pago,
  PagoCrear,
  PagosPagina,
} from '../models/pago';
import { API_BASE_URL } from './api.service';

/** Solo se envían los filtros con valor; el texto se recorta. */
function parametros(filtros: Record<string, string | undefined>, offset: number, limit: number) {
  let params = new HttpParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    const texto = valor?.trim();
    if (texto) params = params.set(clave, texto);
  }
  return params.set('offset', offset).set('limit', limit);
}

@Injectable({ providedIn: 'root' })
export class PagosService {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/pagos`;

  registrar(data: PagoCrear) {
    return this.http.post<Pago>(this.url, data).pipe(timeout(15000));
  }
  listar(filtros: FiltrosPagos, offset: number, limit: number) {
    const params = parametros({ ...filtros }, offset, limit);
    return this.http.get<PagosPagina>(this.url, { params }).pipe(timeout(15000));
  }
  estado(filtros: FiltrosEstados, offset: number, limit: number) {
    const params = parametros({ ...filtros }, offset, limit);
    return this.http
      .get<EstadosMensualidadPagina>(`${this.url}/estado`, { params })
      .pipe(timeout(15000));
  }
  comprobante(id: number) {
    return this.http.get<Pago>(`${this.url}/${id}`).pipe(timeout(15000));
  }
  anular(id: number, motivo: string) {
    return this.http.post<Pago>(`${this.url}/${id}/anular`, { motivo }).pipe(timeout(15000));
  }
}
