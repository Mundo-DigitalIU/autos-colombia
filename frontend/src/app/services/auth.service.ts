import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, map, Observable, of, tap, timeout } from 'rxjs';
import { LoginCrear, LoginRespuesta, MENSAJE_SESION_CERRADA, Rol } from '../models/auth';
import { API_BASE_URL } from './api.service';

const CLAVE_ALMACEN = 'autos-colombia.sesion';

interface Sesion {
  token: string;
  rol: Rol;
  nombre: string;
  expira: string;
}

/** Lee la sesión guardada; si el navegador no deja usar sessionStorage o ya venció, no hay sesión. */
function leerSesion(): Sesion | null {
  try {
    const texto = sessionStorage.getItem(CLAVE_ALMACEN);
    if (!texto) return null;
    const dato = JSON.parse(texto) as Partial<Sesion>;
    const valida =
      typeof dato.token === 'string' &&
      dato.token !== '' &&
      (dato.rol === 'ADMINISTRADOR' || dato.rol === 'OPERADOR') &&
      typeof dato.nombre === 'string' &&
      typeof dato.expira === 'string' &&
      Date.parse(dato.expira) > Date.now();
    return valida ? (dato as Sesion) : null;
  } catch {
    return null;
  }
}

function guardarSesion(sesion: Sesion | null): void {
  try {
    if (sesion) sessionStorage.setItem(CLAVE_ALMACEN, JSON.stringify(sesion));
    else sessionStorage.removeItem(CLAVE_ALMACEN);
  } catch {
    // Sin almacenamiento la sesión dura lo que dure la pestaña abierta.
  }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/auth`;
  private readonly inicial = leerSesion();
  private readonly _token = signal<string | null>(this.inicial?.token ?? null);
  private readonly _rol = signal<Rol | null>(this.inicial?.rol ?? null);
  private readonly _nombre = signal<string>(this.inicial?.nombre ?? '');
  private readonly _aviso = signal('');
  private readonly _sinPermiso = signal(false);

  readonly token = this._token.asReadonly();
  readonly rol = this._rol.asReadonly();
  readonly nombre = this._nombre.asReadonly();
  readonly autenticado = computed(() => this._token() !== null);
  readonly esAdministrador = computed(() => this._rol() === 'ADMINISTRADOR');
  /** Mensaje de una sola lectura para la pantalla de inicio de sesión. */
  readonly aviso = this._aviso.asReadonly();
  /** La API respondió 403: se muestra "No tienes permiso para entrar aquí." hasta cambiar de pantalla. */
  readonly sinPermiso = this._sinPermiso.asReadonly();

  login(data: LoginCrear): Observable<LoginRespuesta> {
    return this.http.post<LoginRespuesta>(`${this.base}/login`, data).pipe(
      timeout(15000),
      tap((r) => {
        this._token.set(r.token);
        this._rol.set(r.rol);
        this._nombre.set(r.nombre);
        this._aviso.set('');
        guardarSesion({ token: r.token, rol: r.rol, nombre: r.nombre, expira: r.expira });
      }),
    );
  }

  /** Revoca la sesión en el servidor; pase lo que pase, la sesión local se borra. */
  cerrarSesion(): Observable<void> {
    return this.http.post<unknown>(`${this.base}/logout`, {}).pipe(
      timeout(15000),
      map(() => undefined),
      catchError(() => of(undefined)),
      finalize(() => this.limpiar(MENSAJE_SESION_CERRADA)),
    );
  }

  /** Borra la sesión local y deja un aviso para la pantalla de inicio de sesión. */
  limpiar(aviso = ''): void {
    this._token.set(null);
    this._rol.set(null);
    this._nombre.set('');
    this._aviso.set(aviso);
    this._sinPermiso.set(false);
    guardarSesion(null);
  }

  consumirAviso(): string {
    const aviso = this._aviso();
    this._aviso.set('');
    return aviso;
  }

  avisarSinPermiso(): void {
    this._sinPermiso.set(true);
  }
  quitarSinPermiso(): void {
    this._sinPermiso.set(false);
  }
}
