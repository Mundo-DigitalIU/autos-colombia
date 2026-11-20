import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MedioPago, Pago } from '../models/pago';
import { TipoVehiculo } from '../models/vehiculo';
import { PagosService } from '../services/pagos.service';
import { mensajeApi } from '../shared/errores';
import { fechaCorta, fechaHora12, numeroPago, pesos } from '../shared/formato';

const TIPOS: Record<TipoVehiculo, string> = {
  MOTO: 'Moto',
  AUTOMOVIL: 'Automóvil',
  CAMIONETA: 'Camioneta',
};
const MEDIOS: Record<MedioPago, string> = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
  TARJETA: 'Tarjeta',
};

@Component({
  selector: 'app-comprobante',
  imports: [RouterLink],
  templateUrl: './comprobante.html',
  styleUrls: ['../shared/gestion.css', './comprobante.css'],
})
export class Comprobante {
  private readonly api = inject(PagosService);
  private readonly destroyRef = inject(DestroyRef);
  readonly pago = signal<Pago | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');
  /** Aviso que deja la pantalla anterior, por ejemplo "Pago registrado." */
  readonly aviso = signal('');
  readonly fecha = fechaCorta;
  /** Solo el comprobante muestra la hora en 12 horas. */
  readonly fechaHora = fechaHora12;
  readonly numero = numeroPago;
  readonly pesos = pesos;
  readonly tipos = TIPOS;
  readonly medios = MEDIOS;

  constructor() {
    const aviso = inject(Router).getCurrentNavigation()?.extras.state?.['aviso'];
    if (typeof aviso === 'string') this.aviso.set(aviso);
    const id = Number(inject(ActivatedRoute).snapshot.paramMap.get('id'));
    if (!Number.isInteger(id) || id < 1) {
      this.loading.set(false);
      this.error.set('Pago no encontrado.');
      return;
    }
    this.api
      .comprobante(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pago) => {
          this.loading.set(false);
          this.pago.set(pago);
        },
        error: (error: unknown) => {
          this.loading.set(false);
          this.error.set(mensajeApi(error));
        },
      });
  }
}
