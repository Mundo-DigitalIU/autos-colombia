import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { Cuenta, CuentaCrear, CuentasPagina } from '../models/cuenta';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class CuentasService {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/cuentas`;

  list(q: string, offset: number, limit: number) {
    let params = new HttpParams();
    if (q.trim()) params = params.set('q', q.trim());
    params = params.set('offset', offset).set('limit', limit);
    return this.http.get<CuentasPagina>(this.url, { params }).pipe(timeout(15000));
  }
  create(data: CuentaCrear) {
    return this.http.post<Cuenta>(this.url, data).pipe(timeout(15000));
  }
  delete(id: number) {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(timeout(15000));
  }
}
