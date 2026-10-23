import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { EstanciaDentro } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { fechaBogota } from '../shared/fecha';

@Component({
  selector: 'app-dentro',
  templateUrl: './dentro.html',
  styleUrl: './dentro.css',
})
export class Dentro {
  private readonly api = inject(EstanciasService);
  private readonly destroyRef = inject(DestroyRef);
  readonly limit = 20;
  readonly items = signal<EstanciaDentro[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly fecha = fechaBogota;

  constructor() {
    this.load();
  }

  load(offset = this.offset()): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .dentro(offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && !data.items.length && data.total > 0) {
            this.load(Math.floor((data.total - 1) / this.limit) * this.limit);
            return;
          }
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: () => {
          this.loading.set(false);
          this.error.set(
            'No se pudo consultar los vehículos dentro. Comprueba la conexión y actualiza.',
          );
        },
      });
  }
}
