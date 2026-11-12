import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';
import { Cliente, ClienteActualizar, ClienteCrear, ClientesPagina } from '../models/cliente';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class ClientesService {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/clientes`;

  list(q: string, offset: number, limit: number) {
    let params = new HttpParams();
    if (q.trim()) params = params.set('q', q.trim());
    params = params.set('offset', offset).set('limit', limit);
    return this.http.get<ClientesPagina>(this.url, { params }).pipe(timeout(15000));
  }
  get(id: number) {
    return this.http.get<Cliente>(`${this.url}/${id}`).pipe(timeout(15000));
  }
  create(data: ClienteCrear) {
    return this.http.post<Cliente>(this.url, data).pipe(timeout(15000));
  }
  update(id: number, data: ClienteActualizar) {
    return this.http.put<Cliente>(`${this.url}/${id}`, data).pipe(timeout(15000));
  }
  delete(id: number) {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(timeout(15000));
  }
  deleteVehiculo(clienteId: number, vehiculoId: number) {
    return this.http
      .delete<void>(`${this.url}/${clienteId}/vehiculos/${vehiculoId}`)
      .pipe(timeout(15000));
  }
}
