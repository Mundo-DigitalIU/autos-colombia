import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { FiltrosHistorial, MovimientoHistorial } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { fechaBogota } from '../shared/fecha';

@Component({
  selector: 'app-historial',
  imports: [ReactiveFormsModule],
  templateUrl: './historial.html',
  styleUrl: './historial.css',
})
export class Historial {
  private readonly api = inject(EstanciasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly limit = 20;
  readonly form = this.fb.nonNullable.group({ placa: '', desde: '', hasta: '' });
  readonly items = signal<MovimientoHistorial[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly filtros = signal<FiltrosHistorial>({});
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly fecha = fechaBogota;

  constructor() {
    this.cargar(0);
  }

  buscar(): void {
    if (this.loading()) return;
    const { placa, desde, hasta } = this.form.getRawValue();
    if (desde && hasta && desde > hasta) {
      this.error.set('La fecha "Desde" no puede ser posterior a la fecha "Hasta".');
      return;
    }
    const filtros: FiltrosHistorial = { placa: placa.trim().toUpperCase(), desde, hasta };
    this.form.controls.placa.setValue(filtros.placa!);
    this.filtros.set(filtros);
    this.cargar(0);
  }

  cargar(offset: number): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .historial(this.filtros(), offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: (error: HttpErrorResponse) => {
          this.loading.set(false);
          this.error.set(this.mensaje(error));
        },
      });
  }

  private mensaje(error: HttpErrorResponse): string {
    if (error.status === 422 && typeof error.error?.detail === 'string') return error.error.detail;
    if (error.status === 422) return 'Revisa los filtros: la placa o las fechas no son válidas.';
    return 'No se pudo consultar el historial. Comprueba la conexión y vuelve a intentarlo.';
  }
}
