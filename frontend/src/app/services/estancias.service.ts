import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { EMPTY, Observable, expand, reduce, throwError, timeout } from 'rxjs';
import { Celda } from '../models/celda';
import { Operador } from '../models/operador';
import {
  CeldasEstadoPagina,
  DentroPagina,
  EntradaCrear,
  Estancia,
  EstadoVehiculo,
  FiltrosHistorial,
  HistorialPagina,
  SalidaCrear,
} from '../models/estancia';
import { API_BASE_URL } from './api.service';
import { CeldasService } from './celdas.service';
import { OperadoresService } from './operadores.service';

interface Pagina<T> {
  items: T[];
  offset: number;
  limit: number;
  total: number;
}

@Injectable({ providedIn: 'root' })
export class EstanciasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/estancias`;
  private readonly cells = inject(CeldasService);
  private readonly operators = inject(OperadoresService);

  entrada(data: EntradaCrear) {
    return this.http.post<Estancia>(`${this.base}/entrada`, data).pipe(timeout(15000));
  }
  salida(data: SalidaCrear) {
    return this.http.post<Estancia>(`${this.base}/salida`, data).pipe(timeout(15000));
  }
  consultar(placa: string) {
    return this.http
      .get<EstadoVehiculo>(`${this.base}/vehiculo/${encodeURIComponent(placa)}`)
      .pipe(timeout(15000));
  }
  dentro(offset: number, limit: number) {
    return this.http
      .get<DentroPagina>(`${this.base}/dentro`, { params: { offset, limit } })
      .pipe(timeout(15000));
  }
  historial(filtros: FiltrosHistorial, offset: number, limit: number) {
    let params = new HttpParams();
    for (const key of ['placa', 'desde', 'hasta'] as const) {
      const value = filtros[key]?.trim();
      if (value) params = params.set(key, value);
    }
    params = params.set('offset', offset).set('limit', limit);
    return this.http
      .get<HistorialPagina>(`${this.base}/historial`, { params })
      .pipe(timeout(15000));
  }
  celdasEstado(offset = 0, limit = 100) {
    return this.http
      .get<CeldasEstadoPagina>(`${this.base}/celdas`, { params: { offset, limit } })
      .pipe(timeout(15000));
  }
  celdas(): Observable<Celda[]> {
    return this.todas((offset) => this.cells.list(offset, 100));
  }
  operadores(): Observable<Operador[]> {
    return this.todas((offset) => this.operators.list(offset, 100));
  }

  private todas<T>(load: (offset: number) => Observable<Pagina<T>>): Observable<T[]> {
    return load(0).pipe(
      expand((page) => {
        const next = page.offset + page.items.length;
        if (next >= page.total) return EMPTY;
        if (!page.items.length)
          return throwError(() => new Error('Catálogo incompleto. Recarga las opciones.'));
        return load(next);
      }),
      reduce((items, page) => [...items, ...page.items], [] as T[]),
    );
  }
}
