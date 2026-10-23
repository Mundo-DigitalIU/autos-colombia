import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { catchError, of, switchMap } from 'rxjs';
import { Estancia } from '../models/estancia';
import { EstanciasService } from '../services/estancias.service';
import { OperadoresService } from '../services/operadores.service';
import { fechaBogota } from '../shared/fecha';

interface EntradaRegistrada {
  placa: string;
  celda: string | null;
  entrada: string;
}

@Component({
  selector: 'app-entrada',
  imports: [ReactiveFormsModule],
  templateUrl: './entrada.html',
  styleUrl: './entrada.css',
})
export class Entrada {
  private readonly api = inject(EstanciasService);
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
  readonly resultado = signal<EntradaRegistrada | null>(null);
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
              'No hay operadores registrados. No se puede registrar la entrada.',
            );
        },
        error: () => {
          this.cargandoOperador.set(false);
          this.operadorId.set(null);
          this.errorOperador.set(
            'No se pudo cargar el operador. No se puede registrar la entrada hasta reintentar.',
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
      .entrada({ placa, operador_id: this.operadorId()! })
      .pipe(
        switchMap((estancia: Estancia) =>
          this.api.consultar(placa).pipe(
            // La entrada ya quedó registrada: si falla la consulta, solo falta mostrar la celda.
            catchError(() => of(null)),
            switchMap((estado) =>
              of<EntradaRegistrada>({
                placa,
                celda: estado?.estancia?.celda.codigo ?? null,
                entrada: estancia.entrada,
              }),
            ),
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
    return 'No se pudo conectar con el servicio. Revisa la pantalla Dentro antes de reintentar: la entrada podría haberse registrado.';
  }
}
