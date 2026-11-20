import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { EstadoPago, Pago } from '../models/pago';
import { AuthService } from '../services/auth.service';
import { PagosService } from '../services/pagos.service';
import { mensajeApi } from '../shared/errores';
import { fechaCorta, fechaHoraCorta, pesos } from '../shared/formato';
import { AnularPago } from './anular-pago';

export const MENSAJE_FECHAS = 'La fecha desde no puede ser posterior a la fecha hasta.';

@Component({
  selector: 'app-pagos-registrados',
  imports: [ReactiveFormsModule, RouterLink, AnularPago],
  templateUrl: './pagos-registrados.html',
  styleUrl: '../shared/gestion.css',
})
export class PagosRegistrados {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  readonly auth = inject(AuthService);
  readonly buscador = new FormControl('', { nonNullable: true });
  readonly filtroEstado = new FormControl<'' | EstadoPago>('', { nonNullable: true });
  readonly desde = new FormControl('', { nonNullable: true });
  readonly hasta = new FormControl('', { nonNullable: true });
  readonly opciones = [
    { valor: '', texto: 'Todos' },
    { valor: 'REGISTRADO', texto: 'Registrado' },
    { valor: 'ANULADO', texto: 'Anulado' },
  ];
  readonly consulta = signal({ q: '', estado: '' as '' | EstadoPago, desde: '', hasta: '' });
  readonly items = signal<Pago[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly listError = signal('');
  readonly filtroError = signal('');
  readonly success = signal('');
  readonly pendingAnular = signal<Pago | null>(null);
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly fecha = fechaCorta;
  readonly fechaHora = fechaHoraCorta;
  readonly pesos = pesos;

  constructor() {
    this.load(0);
  }

  load(offset = this.offset()): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.listError.set('');
    const { q, estado, desde, hasta } = this.consulta();
    this.api
      .listar({ q, estado: estado || undefined, desde, hasta }, offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.load(Math.max(0, Math.floor((data.total - 1) / this.limit) * this.limit));
            return;
          }
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: (error: unknown) => {
          this.loading.set(false);
          this.listError.set(mensajeApi(error));
        },
      });
  }

  buscar(): void {
    if (this.desde.value && this.hasta.value && this.desde.value > this.hasta.value) {
      this.filtroError.set(MENSAJE_FECHAS);
      return;
    }
    this.filtroError.set('');
    this.consulta.set({
      q: this.buscador.value.trim(),
      estado: this.filtroEstado.value,
      desde: this.desde.value,
      hasta: this.hasta.value,
    });
    this.load(0);
  }

  limpiar(): void {
    this.buscador.setValue('');
    this.filtroEstado.setValue('');
    this.desde.setValue('');
    this.hasta.setValue('');
    this.buscar();
  }

  hayFiltro(): boolean {
    const { q, estado, desde, hasta } = this.consulta();
    return !!(q || estado || desde || hasta);
  }

  /** Solo el administrador anula, y solo los pagos que siguen REGISTRADO. */
  puedeAnular(pago: Pago): boolean {
    return this.auth.esAdministrador() && pago.estado === 'REGISTRADO';
  }

  pedirAnulacion(pago: Pago): void {
    if (!this.puedeAnular(pago)) return;
    this.success.set('');
    this.pendingAnular.set(pago);
  }

  cerrarAnulacion(): void {
    this.pendingAnular.set(null);
  }

  anulado(): void {
    this.pendingAnular.set(null);
    this.success.set('Pago anulado.');
    this.load();
  }
}
