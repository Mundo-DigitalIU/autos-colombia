import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { catchError, map, of, switchMap } from 'rxjs';
import { CeldasService } from '../services/celdas.service';
import { EstanciasService } from '../services/estancias.service';
import { OperadoresService } from '../services/operadores.service';
import { fechaBogota } from '../shared/fecha';

interface SalidaRegistrada {
  placa: string;
  celda: string | null;
  salida: string;
}

@Component({
  selector: 'app-salida',
  imports: [ReactiveFormsModule],
  templateUrl: './salida.html',
  styleUrl: './salida.css',
})
export class Salida {
  private readonly api = inject(EstanciasService);
  private readonly celdas = inject(CeldasService);
  private readonly operadores = inject(OperadoresService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly form = this.fb.nonNullable.group({ placa: '' });
  readonly operadorId = signal<number | null>(null);
  readonly cargandoOperador = signal(false);
  readonly errorOperador = signal('');
  readonly saving = signal(false);
  readonly errorPlaca = signal('');
  readonly error = signal('');
  readonly resultado = signal<SalidaRegistrada | null>(null);
  readonly bloqueado = computed(
    () => this.saving() || this.cargandoOperador() || this.operadorId() === null,
  );
  readonly fecha = fechaBogota;

  constructor() {
    this.form.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.errorPlaca.set('');
        this.error.set('');
        this.resultado.set(null);
      });
    this.cargarOperador();
  }

  cargarOperador(): void {
    if (this.cargandoOperador()) return;
    this.cargandoOperador.set(true);
    this.errorOperador.set('');
    this.operadores
      .list(0, 1)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.cargandoOperador.set(false);
          const primero = data.items.at(0);
          this.operadorId.set(primero?.id ?? null);
          if (!primero)
            this.errorOperador.set(
              'No hay operadores registrados. No se puede registrar la salida.',
            );
        },
        error: () => {
          this.cargandoOperador.set(false);
          this.operadorId.set(null);
          this.errorOperador.set(
            'No se pudo cargar el operador. No se puede registrar la salida hasta reintentar.',
          );
        },
      });
  }

  registrar(): void {
    if (this.bloqueado()) return;
    const placa = this.form.controls.placa.value.trim().toUpperCase();
    if (!placa) {
      this.errorPlaca.set('Escribe la placa del vehículo.');
      return;
    }
    this.form.controls.placa.setValue(placa, { emitEvent: false });
    this.saving.set(true);
    this.error.set('');
    this.resultado.set(null);
    this.api
      .salida({ placa, operador_id: this.operadorId()! })
      .pipe(
        switchMap((estancia) =>
          this.celdas.get(estancia.celda_id).pipe(
            // La salida ya quedó registrada: si falla la consulta, solo falta mostrar la celda.
            map((celda) => celda.codigo),
            catchError(() => of(null)),
            map((celda): SalidaRegistrada => ({ placa, celda, salida: estancia.salida! })),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (resultado) => {
          this.saving.set(false);
          this.resultado.set(resultado);
          this.form.controls.placa.setValue('', { emitEvent: false });
        },
        error: (error: HttpErrorResponse) => {
          this.saving.set(false);
          this.error.set(this.mensaje(error));
        },
      });
  }

  private mensaje(error: HttpErrorResponse): string {
    if ([404, 409].includes(error.status) && typeof error.error?.detail === 'string')
      return error.error.detail;
    if (error.status === 422) return 'Revisa la placa: no es válida.';
    return 'No se pudo conectar con el servicio. Revisa la pantalla Dentro antes de reintentar: la salida podría haberse registrado.';
  }
}
