import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { CeldaEstado, EstadoCelda } from '../models/estancia';
import { TIPOS_VEHICULO, TipoVehiculo } from '../models/vehiculo';
import { CeldasService } from '../services/celdas.service';
import { EstanciasService } from '../services/estancias.service';
import { erroresDeCampo, mensajeApi } from '../shared/errores';

const noVacio: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };

export const AVISO_TIPO_OCUPADA = 'No puedes cambiar el tipo mientras la celda está ocupada.';

@Component({
  selector: 'app-gestion-celdas',
  imports: [ReactiveFormsModule],
  templateUrl: './gestion-celdas.html',
  styleUrl: '../shared/gestion.css',
})
export class GestionCeldas {
  private readonly estados = inject(EstanciasService);
  private readonly celdas = inject(CeldasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly tipos = TIPOS_VEHICULO;
  readonly avisoTipoOcupada = AVISO_TIPO_OCUPADA;
  readonly form = this.fb.group({
    codigo: this.fb.nonNullable.control('', noVacio),
    tipo: this.fb.nonNullable.control<TipoVehiculo | ''>('', noVacio),
  });
  readonly buscador = new FormControl('', { nonNullable: true });
  readonly filtroTipo = new FormControl<TipoVehiculo | ''>('', { nonNullable: true });
  readonly filtroEstado = new FormControl<EstadoCelda | ''>('', { nonNullable: true });
  readonly consulta = signal<{ q: string; tipo: TipoVehiculo | ''; estado: EstadoCelda | '' }>({
    q: '',
    tipo: '',
    estado: '',
  });
  readonly items = signal<CeldaEstado[]>([]);
  readonly total = signal(0);
  readonly disponibles = signal(0);
  readonly ocupadas = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly showForm = signal(false);
  readonly editing = signal<CeldaEstado | null>(null);
  readonly pendingDelete = signal<CeldaEstado | null>(null);
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly success = signal('');
  readonly errorCodigo = signal('');
  readonly errorTipo = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  /** La celda que se edita está ocupada: el tipo queda bloqueado. */
  readonly tipoBloqueado = computed(() => this.editing()?.estado === 'OCUPADA');

  constructor() {
    this.load(0);
  }

  load(offset = this.offset()): void {
    if (this.loading() || this.saving()) return;
    this.loading.set(true);
    this.listError.set('');
    this.estados
      .celdasEstado(offset, this.limit, this.consulta())
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
          this.disponibles.set(data.disponibles);
          this.ocupadas.set(data.ocupadas);
          this.offset.set(offset);
        },
        error: (error: unknown) => {
          this.loading.set(false);
          this.listError.set(mensajeApi(error));
        },
      });
  }

  buscar(): void {
    this.consulta.set({
      q: this.buscador.value.trim(),
      tipo: this.filtroTipo.value,
      estado: this.filtroEstado.value,
    });
    this.load(0);
  }

  limpiarFiltros(): void {
    this.buscador.setValue('');
    this.filtroTipo.setValue('');
    this.filtroEstado.setValue('');
    this.buscar();
  }

  nueva(): void {
    if (this.busy()) return;
    this.abrirFormulario(null);
  }

  editar(celda: CeldaEstado): void {
    if (this.busy()) return;
    this.abrirFormulario(celda);
  }

  private abrirFormulario(celda: CeldaEstado | null): void {
    this.form.reset({ codigo: celda?.codigo ?? '', tipo: (celda?.tipo as TipoVehiculo) ?? '' });
    this.editing.set(celda);
    // Una celda ocupada no puede cambiar de tipo: el campo se bloquea y se explica por qué.
    if (celda?.estado === 'OCUPADA') this.form.controls.tipo.disable();
    else this.form.controls.tipo.enable();
    this.showForm.set(true);
    this.pendingDelete.set(null);
    this.actionError.set('');
    this.success.set('');
    this.errorCodigo.set('');
    this.errorTipo.set('');
  }

  cancelar(): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.pendingDelete.set(null);
    this.actionError.set('');
  }

  guardar(): void {
    if (this.busy()) return;
    const valor = this.form.getRawValue();
    const codigo = valor.codigo.trim();
    this.errorCodigo.set(codigo ? '' : 'Escribe el código de la celda.');
    this.errorTipo.set(valor.tipo ? '' : 'Selecciona el tipo.');
    if (!codigo || !valor.tipo) return;
    const datos = { codigo, tipo: valor.tipo };
    const celda = this.editing();
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    const peticion =
      celda === null ? this.celdas.create(datos) : this.celdas.update(celda.id, datos);
    peticion.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (guardada) => {
        this.saving.set(false);
        this.showForm.set(false);
        this.success.set(
          `Celda ${guardada.codigo} ${celda === null ? 'creada' : 'actualizada'} correctamente.`,
        );
        this.load();
      },
      error: (error: unknown) => {
        this.saving.set(false);
        const campos = erroresDeCampo(error);
        if (campos['codigo']) this.errorCodigo.set(campos['codigo']);
        if (campos['tipo']) this.errorTipo.set(campos['tipo']);
        this.actionError.set(
          mensajeApi(error, 'No se pudo guardar la celda. Revisa los datos e inténtalo otra vez.'),
        );
      },
    });
  }

  confirmarEliminar(celda: CeldaEstado): void {
    if (this.busy()) return;
    this.pendingDelete.set(celda);
    this.showForm.set(false);
    this.actionError.set('');
    this.success.set('');
  }

  eliminar(): void {
    const celda = this.pendingDelete();
    if (!celda || this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.celdas
      .delete(celda.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.pendingDelete.set(null);
          this.success.set(`Celda ${celda.codigo} eliminada correctamente.`);
          this.load();
        },
        error: (error: unknown) => {
          this.saving.set(false);
          this.pendingDelete.set(null);
          // El 409 de "ya tuvo entradas y salidas" se muestra tal cual lo envía la API.
          this.actionError.set(
            mensajeApi(error, 'No se pudo eliminar la celda. Inténtalo otra vez.'),
          );
        },
      });
  }
}
