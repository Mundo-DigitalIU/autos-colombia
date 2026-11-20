import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, debounceTime, distinctUntilChanged, map, of, switchMap, tap } from 'rxjs';
import { EstadoMensualidadVehiculo, MEDIOS_PAGO, MedioPago } from '../models/pago';
import { PagosService } from '../services/pagos.service';
import { erroresDeCampo, mensajeApi } from '../shared/errores';
import { fechaCorta, hoyBogota, pesos, sumarDias } from '../shared/formato';

const noVacio: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };

type Campo = 'placa' | 'medio_pago';

const FALTA: Record<Campo, string> = {
  placa: 'Escribe la placa.',
  medio_pago: 'Selecciona el medio de pago.',
};

const DIAS_VIGENCIA = 30;

@Component({
  selector: 'app-registrar-pago',
  imports: [ReactiveFormsModule],
  templateUrl: './registrar-pago.html',
  styleUrl: '../shared/gestion.css',
})
export class RegistrarPago {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  readonly medios = MEDIOS_PAGO;
  readonly form = this.fb.group({
    placa: this.fb.nonNullable.control('', noVacio),
    medio_pago: this.fb.nonNullable.control<'' | MedioPago>('', noVacio),
  });
  readonly saving = signal(false);
  readonly actionError = signal('');
  /** Datos del vehículo escrito, tomados de /pagos/estado; null si no hay coincidencia. */
  readonly vehiculo = signal<EstadoMensualidadVehiculo | null>(null);
  readonly buscandoPlaca = signal(false);
  readonly sinVehiculo = signal(false);
  /** Vigencia que quedaría. Es solo una ayuda: la que vale es la que calcula el servidor. */
  readonly vigencia = computed(() => {
    const vehiculo = this.vehiculo();
    if (!vehiculo) return null;
    const desde = vehiculo.vigencia_hasta ?? hoyBogota();
    return { desde, hasta: sumarDias(desde, DIAS_VIGENCIA) };
  });
  readonly fecha = fechaCorta;
  readonly pesos = pesos;

  constructor() {
    this.form.controls.placa.valueChanges
      .pipe(
        map((valor) => valor.trim().toUpperCase()),
        distinctUntilChanged(),
        tap(() => {
          this.vehiculo.set(null);
          this.sinVehiculo.set(false);
        }),
        debounceTime(300),
        switchMap((placa) => {
          if (!placa) return of(null);
          this.buscandoPlaca.set(true);
          return this.api.estado({ q: placa }, 0, 10).pipe(
            map((pagina) => pagina.items.find((item) => item.placa === placa) ?? null),
            catchError(() => of(null)),
            tap((encontrado) => {
              this.buscandoPlaca.set(false);
              this.sinVehiculo.set(!encontrado);
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((encontrado) => this.vehiculo.set(encontrado));

    // Desde "Mensualidades", el botón de cada fila abre esta pantalla con la placa escrita.
    const placa = inject(ActivatedRoute).snapshot.queryParamMap.get('placa');
    if (placa?.trim()) this.form.controls.placa.setValue(placa.trim().toUpperCase());
  }

  errorDeCampo(campo: Campo): string {
    const control = this.form.controls[campo];
    if (!control.touched || !control.errors) return '';
    if (control.errors['server']) return String(control.errors['server']);
    return FALTA[campo];
  }

  guardar(): void {
    if (this.saving()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.actionError.set('Revisa los campos señalados antes de guardar el pago.');
      return;
    }
    const valor = this.form.getRawValue();
    this.saving.set(true);
    this.actionError.set('');
    this.api
      .registrar({ placa: valor.placa.trim().toUpperCase(), medio_pago: valor.medio_pago as MedioPago })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pago) => {
          this.saving.set(false);
          void this.router.navigate(['/panel/pagos/comprobante', pago.id], {
            state: { aviso: 'Pago registrado.' },
          });
        },
        error: (error: unknown) => {
          this.saving.set(false);
          // Los errores de la API (404, 409) se muestran tal cual, sin códigos técnicos.
          this.actionError.set(
            mensajeApi(error, 'No se pudo registrar el pago. Inténtalo otra vez.'),
          );
          for (const [campo, mensaje] of Object.entries(erroresDeCampo(error))) {
            if (campo === 'placa' || campo === 'medio_pago') {
              this.form.controls[campo].setErrors({ server: mensaje });
              this.form.controls[campo].markAsTouched();
            }
          }
        },
      });
  }

  cancelar(): void {
    if (!this.saving()) void this.router.navigateByUrl('/panel/pagos');
  }
}
