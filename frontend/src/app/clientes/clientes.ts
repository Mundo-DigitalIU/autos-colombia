import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormControl,
  ReactiveFormsModule,
  ValidatorFn,
} from '@angular/forms';
import { Cliente } from '../models/cliente';
import { TIPOS_VEHICULO, TipoVehiculo } from '../models/vehiculo';
import { AuthService } from '../services/auth.service';
import { ClientesService } from '../services/clientes.service';
import { mensajeApi } from '../shared/errores';

const noVacio: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };
const anioValido: ValidatorFn = (control) => {
  const valor = Number(control.value);
  return control.value !== null &&
    control.value !== '' &&
    Number.isInteger(valor) &&
    valor >= 1 &&
    valor <= 9999
    ? null
    : { required: true };
};

type CampoCliente = 'nombre' | 'documento' | 'telefono';
type CampoVehiculo = 'placa' | 'tipo' | 'color' | 'marca' | 'modelo';

const MENSAJES: Record<CampoCliente | CampoVehiculo, string> = {
  nombre: 'Escribe el nombre.',
  documento: 'Escribe el documento.',
  telefono: 'Escribe el teléfono.',
  placa: 'Escribe la placa.',
  tipo: 'Selecciona el tipo.',
  color: 'Escribe el color.',
  marca: 'Escribe la marca.',
  modelo: 'Escribe un año entre 1 y 9999.',
};

interface DatosVehiculo {
  id?: number;
  placa?: string;
  tipo?: TipoVehiculo | '';
  color?: string;
  marca?: string;
  modelo?: number | null;
}

function grupoVehiculo(fb: FormBuilder, datos?: DatosVehiculo) {
  return fb.group({
    id: fb.control<number | null>(datos?.id ?? null),
    placa: fb.nonNullable.control(datos?.placa ?? '', noVacio),
    tipo: fb.nonNullable.control<TipoVehiculo | ''>(datos?.tipo ?? '', noVacio),
    color: fb.nonNullable.control(datos?.color ?? '', noVacio),
    marca: fb.nonNullable.control(datos?.marca ?? '', noVacio),
    modelo: fb.control<number | null>(datos?.modelo ?? null, anioValido),
  });
}
type GrupoVehiculo = ReturnType<typeof grupoVehiculo>;

@Component({
  selector: 'app-clientes',
  imports: [ReactiveFormsModule],
  templateUrl: './clientes.html',
  styleUrl: '../shared/gestion.css',
})
export class Clientes {
  readonly auth = inject(AuthService);
  private readonly api = inject(ClientesService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly tipos = TIPOS_VEHICULO;
  readonly camposCliente: { key: CampoCliente; label: string; tipo: string }[] = [
    { key: 'nombre', label: 'Nombre', tipo: 'text' },
    { key: 'documento', label: 'Documento', tipo: 'text' },
    { key: 'telefono', label: 'Teléfono', tipo: 'tel' },
  ];
  readonly form = this.fb.group({
    nombre: this.fb.nonNullable.control('', noVacio),
    documento: this.fb.nonNullable.control('', noVacio),
    telefono: this.fb.nonNullable.control('', noVacio),
    vehiculos: this.fb.array<GrupoVehiculo>([grupoVehiculo(this.fb)]),
  });
  /** Copia reactiva de los bloques de vehículo: la plantilla se redibuja al agregar o quitar. */
  readonly bloques = signal<GrupoVehiculo[]>([]);
  readonly buscador = new FormControl('', { nonNullable: true });
  readonly consulta = signal('');
  readonly items = signal<Cliente[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly showForm = signal(false);
  readonly editing = signal<number | null>(null);
  readonly pendingDelete = signal<Cliente | null>(null);
  readonly pendingVehicle = signal<{ indice: number; id: number; placa: string } | null>(null);
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly success = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    this.sincronizar();
    this.load(0);
  }

  private sincronizar(): void {
    this.bloques.set([...this.vehiculos.controls]);
  }

  get vehiculos(): FormArray<GrupoVehiculo> {
    return this.form.controls.vehiculos;
  }

  vehiculoGrupo(indice: number) {
    return this.vehiculos.at(indice);
  }

  load(offset = this.offset()): void {
    if (this.loading() || this.saving()) return;
    this.loading.set(true);
    this.listError.set('');
    this.api
      .list(this.consulta(), offset, this.limit)
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
    this.consulta.set(this.buscador.value.trim());
    this.load(0);
  }

  limpiarBusqueda(): void {
    this.buscador.setValue('');
    this.buscar();
  }

  private reiniciarFormulario(cliente?: Cliente): void {
    this.vehiculos.clear();
    const vehiculos = cliente?.vehiculos.length ? cliente.vehiculos : [undefined];
    for (const v of vehiculos) this.vehiculos.push(grupoVehiculo(this.fb, v));
    this.form.patchValue({
      nombre: cliente?.nombre ?? '',
      documento: cliente?.documento ?? '',
      telefono: cliente?.telefono ?? '',
    });
    this.form.markAsUntouched();
    this.sincronizar();
  }

  nuevo(): void {
    if (this.busy()) return;
    this.reiniciarFormulario();
    this.editing.set(null);
    this.showForm.set(true);
    this.limpiarAvisos();
  }

  editar(cliente: Cliente): void {
    if (this.busy() || !this.auth.esAdministrador()) return;
    this.loading.set(true);
    this.limpiarAvisos();
    this.api
      .get(cliente.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          this.reiniciarFormulario(data);
          this.editing.set(data.id);
          this.showForm.set(true);
        },
        error: (error: unknown) => {
          this.loading.set(false);
          this.actionError.set(mensajeApi(error));
        },
      });
  }

  private limpiarAvisos(): void {
    this.pendingDelete.set(null);
    this.pendingVehicle.set(null);
    this.actionError.set('');
    this.success.set('');
  }

  agregarVehiculo(): void {
    this.vehiculos.push(grupoVehiculo(this.fb));
    this.sincronizar();
  }

  /** Quita un bloque de vehículo que todavía no se guardó. */
  quitarVehiculo(indice: number): void {
    if (this.vehiculos.length > 1) this.vehiculos.removeAt(indice);
    this.sincronizar();
  }

  esGuardado(indice: number): boolean {
    return this.vehiculoGrupo(indice).controls.id.value !== null;
  }

  cancelar(): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.limpiarAvisos();
  }

  errorCliente(campo: CampoCliente): string {
    const control = this.form.controls[campo];
    return control.touched && control.errors ? MENSAJES[campo] : '';
  }

  errorVehiculo(indice: number, campo: CampoVehiculo): string {
    const control = this.vehiculoGrupo(indice).controls[campo] as AbstractControl;
    return control.touched && control.errors ? MENSAJES[campo] : '';
  }

  guardar(): void {
    if (this.busy()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.actionError.set('Revisa los campos señalados antes de guardar el cliente.');
      return;
    }
    const v = this.form.getRawValue();
    const vehiculos = v.vehiculos.map((x) => ({
      ...(x.id === null ? {} : { id: x.id }),
      placa: x.placa.trim().toUpperCase(),
      tipo: x.tipo as TipoVehiculo,
      color: x.color.trim(),
      marca: x.marca.trim(),
      modelo: Number(x.modelo),
    }));
    const datos = {
      nombre: v.nombre.trim(),
      documento: v.documento.trim(),
      telefono: v.telefono.trim(),
      vehiculos,
    };
    const id = this.editing();
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    const peticion = id === null ? this.api.create(datos) : this.api.update(id, datos);
    peticion.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (cliente) => {
        this.saving.set(false);
        this.showForm.set(false);
        this.success.set(
          `Cliente ${cliente.nombre} ${id === null ? 'registrado' : 'actualizado'} correctamente.`,
        );
        this.load();
      },
      error: (error: unknown) => {
        this.saving.set(false);
        this.actionError.set(
          mensajeApi(
            error,
            'No se pudo guardar el cliente. Revisa los datos e inténtalo otra vez.',
          ),
        );
      },
    });
  }

  confirmarEliminar(cliente: Cliente): void {
    if (this.busy() || !this.auth.esAdministrador()) return;
    this.limpiarAvisos();
    this.pendingDelete.set(cliente);
    this.showForm.set(false);
  }

  eliminar(): void {
    const cliente = this.pendingDelete();
    if (!cliente || this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.api
      .delete(cliente.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.pendingDelete.set(null);
          this.success.set(`Cliente ${cliente.nombre} eliminado correctamente.`);
          this.load();
        },
        error: (error: unknown) => {
          this.saving.set(false);
          // El 409 de "ya tienen entradas y salidas" se muestra tal cual lo envía la API.
          this.actionError.set(
            mensajeApi(error, 'No se pudo eliminar el cliente. Inténtalo otra vez.'),
          );
          this.pendingDelete.set(null);
        },
      });
  }

  confirmarEliminarVehiculo(indice: number): void {
    const id = this.editing();
    const grupo = this.vehiculoGrupo(indice).getRawValue();
    if (this.busy() || id === null || grupo.id === null || !this.auth.esAdministrador()) return;
    this.actionError.set('');
    this.pendingVehicle.set({ indice, id: grupo.id, placa: grupo.placa });
  }

  cancelarEliminarVehiculo(): void {
    if (!this.busy()) this.pendingVehicle.set(null);
  }

  eliminarVehiculo(): void {
    const vehiculo = this.pendingVehicle();
    const clienteId = this.editing();
    if (!vehiculo || clienteId === null || this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.api
      .deleteVehiculo(clienteId, vehiculo.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.pendingVehicle.set(null);
          if (this.vehiculos.length > 1) this.vehiculos.removeAt(vehiculo.indice);
          else
            this.vehiculos
              .at(0)
              .reset({ id: null, placa: '', tipo: '', color: '', marca: '', modelo: null });
          this.sincronizar();
          this.success.set(`Vehículo ${vehiculo.placa} eliminado correctamente.`);
          this.load();
        },
        error: (error: unknown) => {
          this.saving.set(false);
          this.pendingVehicle.set(null);
          this.actionError.set(
            mensajeApi(error, 'No se pudo eliminar el vehículo. Inténtalo otra vez.'),
          );
        },
      });
  }

  placas(cliente: Cliente): string {
    return cliente.vehiculos.map((v) => v.placa).join(', ');
  }
}
