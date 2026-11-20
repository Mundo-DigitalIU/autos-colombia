import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { EstadoMensualidad, EstadoMensualidadVehiculo } from '../models/pago';
import { PagosService } from '../services/pagos.service';
import { mensajeApi } from '../shared/errores';
import { fechaCorta, pesos } from '../shared/formato';

export const ETIQUETAS_MENSUALIDAD: Record<EstadoMensualidad, { texto: string; clase: string }> = {
  AL_DIA: { texto: 'Al día', clase: 'ok' },
  VENCIDA: { texto: 'Vencida', clase: 'late' },
  SIN_PAGOS: { texto: 'Sin pagos', clase: 'none' },
};

@Component({
  selector: 'app-mensualidades',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './mensualidades.html',
  styleUrl: '../shared/gestion.css',
})
export class Mensualidades {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  readonly buscador = new FormControl('', { nonNullable: true });
  readonly filtroEstado = new FormControl<'' | EstadoMensualidad>('', { nonNullable: true });
  readonly opciones = [
    { valor: '', texto: 'Todos' },
    { valor: 'AL_DIA', texto: ETIQUETAS_MENSUALIDAD.AL_DIA.texto },
    { valor: 'VENCIDA', texto: ETIQUETAS_MENSUALIDAD.VENCIDA.texto },
    { valor: 'SIN_PAGOS', texto: ETIQUETAS_MENSUALIDAD.SIN_PAGOS.texto },
  ];
  readonly consulta = signal({ q: '', estado: '' as '' | EstadoMensualidad });
  readonly items = signal<EstadoMensualidadVehiculo[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly listError = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly fecha = fechaCorta;
  readonly pesos = pesos;
  readonly etiquetas = ETIQUETAS_MENSUALIDAD;

  constructor() {
    this.load(0);
  }

  load(offset = this.offset()): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.listError.set('');
    const { q, estado } = this.consulta();
    this.api
      .estado({ q, estado: estado || undefined }, offset, this.limit)
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
    this.consulta.set({ q: this.buscador.value.trim(), estado: this.filtroEstado.value });
    this.load(0);
  }

  limpiar(): void {
    this.buscador.setValue('');
    this.filtroEstado.setValue('');
    this.buscar();
  }

  hayFiltro(): boolean {
    const { q, estado } = this.consulta();
    return !!q || !!estado;
  }
}
