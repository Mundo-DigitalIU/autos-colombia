import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  NavigationStart,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { filter } from 'rxjs';
import { MENSAJE_SIN_PERMISO } from './models/auth';
import { AuthService } from './services/auth.service';

interface Enlace {
  ruta: string;
  texto: string;
  administrador?: boolean;
}

const ENLACES: Enlace[] = [
  { ruta: '/entrada', texto: 'Entrada' },
  { ruta: '/salida', texto: 'Salida' },
  { ruta: '/dentro', texto: 'Dentro' },
  { ruta: '/historial', texto: 'Historial' },
  { ruta: '/estado-celdas', texto: 'Celdas' },
  { ruta: '/panel/clientes', texto: 'Clientes' },
  { ruta: '/panel/cuentas', texto: 'Cuentas', administrador: true },
  { ruta: '/panel/celdas', texto: 'Gestionar celdas', administrador: true },
];

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly mensajeSinPermiso = MENSAJE_SIN_PERMISO;

  constructor() {
    // El aviso de 403 dura hasta que la persona cambie de pantalla.
    this.router.events
      .pipe(
        filter((evento) => evento instanceof NavigationStart),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => this.auth.quitarSinPermiso());
  }

  /** Enlaces del menú según el rol: el administrador ve además Cuentas y Gestionar celdas. */
  enlaces(): Enlace[] {
    return ENLACES.filter((enlace) => !enlace.administrador || this.auth.esAdministrador());
  }

  rolTexto(): string {
    return this.auth.esAdministrador() ? 'Administrador' : 'Operador';
  }

  cerrarSesion(): void {
    this.auth.cerrarSesion().subscribe(() => void this.router.navigateByUrl('/login'));
  }
}
