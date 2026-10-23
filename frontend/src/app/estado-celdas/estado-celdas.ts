import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CeldaEstado } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';

@Component({
  selector: 'app-estado-celdas',
  templateUrl: './estado-celdas.html',
  styleUrl: './estado-celdas.css',
})
export class EstadoCeldas {
  private readonly api = inject(EstanciasService);
  private readonly destroyRef = inject(DestroyRef);
  readonly limit = 100;
  readonly items = signal<CeldaEstado[]>([]);
  readonly total = signal(0);
  readonly disponibles = signal(0);
  readonly ocupadas = signal(0);
  readonly offset = signal(0);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    this.load();
  }

  load(offset = this.offset()): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .celdasEstado(offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.items.set(data.items);
          this.total.set(data.total);
          this.disponibles.set(data.disponibles);
          this.ocupadas.set(data.ocupadas);
          this.offset.set(offset);
        },
        error: () => {
          this.loading.set(false);
          this.error.set(
            'No se pudo consultar el estado de las celdas. Comprueba la conexión y actualiza.',
          );
        },
      });
  }
}
