import {
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Pago } from '../models/pago';
import { PagosService } from '../services/pagos.service';
import { mensajeApi } from '../shared/errores';
import { fechaCorta, pesos } from '../shared/formato';

export const MENSAJE_MOTIVO = 'Escribe el motivo de la anulación.';

/** Diálogo para anular un pago: resumen, motivo obligatorio y los errores de la API tal cual. */
@Component({
  selector: 'app-anular-pago',
  imports: [ReactiveFormsModule],
  templateUrl: './anular-pago.html',
  styleUrl: '../shared/gestion.css',
})
export class AnularPago {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  readonly pago = input.required<Pago>();
  readonly anulado = output<Pago>();
  readonly cancelado = output<void>();
  readonly motivo = new FormControl('', { nonNullable: true });
  readonly saving = signal(false);
  readonly errorMotivo = signal('');
  readonly actionError = signal('');
  readonly fecha = fechaCorta;
  readonly pesos = pesos;

  constructor() {
    // El diálogo se abre arriba del listado: si la persona había bajado hasta la fila, quedaba fuera
    // de la pantalla y parecía que el botón Anular no hacía nada. Se muestra y se enfoca el motivo.
    const raiz = inject(ElementRef).nativeElement as HTMLElement;
    afterNextRender(() => {
      raiz.querySelector('section')?.scrollIntoView?.({ block: 'center' });
      raiz.querySelector<HTMLTextAreaElement>('#anular-motivo')?.focus({ preventScroll: true });
    });
  }

  anular(): void {
    if (this.saving()) return;
    const motivo = this.motivo.value.trim();
    if (!motivo) {
      this.errorMotivo.set(MENSAJE_MOTIVO);
      return;
    }
    this.errorMotivo.set('');
    this.actionError.set('');
    this.saving.set(true);
    this.api
      .anular(this.pago().id, motivo)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pago) => {
          this.saving.set(false);
          this.anulado.emit(pago);
        },
        error: (error: unknown) => {
          this.saving.set(false);
          // Los 409 ("Solo se puede anular el último pago del vehículo.", etc.) se muestran tal cual.
          this.actionError.set(
            mensajeApi(error, 'No se pudo anular el pago. Inténtalo otra vez.'),
          );
        },
      });
  }

  cancelar(): void {
    if (!this.saving()) this.cancelado.emit();
  }
}
