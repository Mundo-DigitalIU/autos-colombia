import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, ReactiveFormsModule, ValidatorFn } from '@angular/forms';
import { Rol } from '../models/auth';
import { Cuenta, CuentaCrear } from '../models/cuenta';
import { CuentasService } from '../services/cuentas.service';
import { erroresDeCampo, mensajeApi } from '../shared/errores';

const noVacio: ValidatorFn = (control) =>
  typeof control.value === 'string' && control.value.trim() ? null : { required: true };
const claveValida: ValidatorFn = (control) => {
  const valor = typeof control.value === 'string' ? control.value : '';
  if (!valor.trim()) return { required: true };
  return valor.length >= 8 ? null : { corta: true };
};

type Campo = 'nombre' | 'telefono' | 'usuario' | 'contrasena' | 'rol';

const CAMPOS: { key: Campo; label: string; tipo: string; falta: string }[] = [
  { key: 'nombre', label: 'Nombre', tipo: 'text', falta: 'Escribe el nombre.' },
  { key: 'telefono', label: 'Teléfono', tipo: 'tel', falta: 'Escribe el teléfono.' },
  { key: 'usuario', label: 'Usuario', tipo: 'text', falta: 'Escribe el usuario.' },
  { key: 'contrasena', label: 'Contraseña', tipo: 'password', falta: 'Escribe la contraseña.' },
];

@Component({
  selector: 'app-cuentas',
  imports: [ReactiveFormsModule],
  templateUrl: './cuentas.html',
  styleUrl: '../shared/gestion.css',
})
export class Cuentas {
  private readonly api = inject(CuentasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly campos = CAMPOS;
  readonly roles: { valor: Rol; texto: string }[] = [
    { valor: 'OPERADOR', texto: 'Operador' },
    { valor: 'ADMINISTRADOR', texto: 'Administrador' },
  ];
  readonly form = this.fb.group({
    nombre: this.fb.nonNullable.control('', noVacio),
    telefono: this.fb.nonNullable.control('', noVacio),
    usuario: this.fb.nonNullable.control('', noVacio),
    contrasena: this.fb.nonNullable.control('', claveValida),
    rol: this.fb.nonNullable.control<Rol>('OPERADOR'),
  });
  readonly buscador = new FormControl('', { nonNullable: true });
  readonly consulta = signal('');
  readonly items = signal<Cuenta[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly busy = computed(() => this.loading() || this.saving());
  readonly showForm = signal(false);
  readonly pendingDelete = signal<Cuenta | null>(null);
  readonly listError = signal('');
  readonly actionError = signal('');
  readonly success = signal('');
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));

  constructor() {
    this.load(0);
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

  nueva(): void {
    if (this.busy()) return;
    this.form.reset({ nombre: '', telefono: '', usuario: '', contrasena: '', rol: 'OPERADOR' });
    this.showForm.set(true);
    this.pendingDelete.set(null);
    this.actionError.set('');
    this.success.set('');
  }

  cancelar(): void {
    if (this.busy()) return;
    this.showForm.set(false);
    this.pendingDelete.set(null);
    this.actionError.set('');
  }

  errorDeCampo(campo: Campo): string {
    const control = this.form.controls[campo];
    if (!control.touched || !control.errors) return '';
    if (control.errors['server']) return String(control.errors['server']);
    if (control.errors['corta']) return 'Mínimo 8 caracteres.';
    return CAMPOS.find((c) => c.key === campo)?.falta ?? 'Revisa este campo.';
  }

  guardar(): void {
    if (this.busy()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.actionError.set('Revisa los campos señalados antes de crear la cuenta.');
      return;
    }
    const valor = this.form.getRawValue();
    const datos: CuentaCrear = {
      nombre: valor.nombre.trim(),
      telefono: valor.telefono.trim(),
      usuario: valor.usuario.trim(),
      contrasena: valor.contrasena,
      rol: valor.rol,
    };
    this.saving.set(true);
    this.actionError.set('');
    this.success.set('');
    this.api
      .create(datos)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cuenta) => {
          this.saving.set(false);
          this.showForm.set(false);
          this.form.reset({
            nombre: '',
            telefono: '',
            usuario: '',
            contrasena: '',
            rol: 'OPERADOR',
          });
          this.success.set(`Cuenta ${cuenta.usuario} creada correctamente.`);
          this.load(0);
        },
        error: (error: unknown) => {
          this.saving.set(false);
          this.actionError.set(
            mensajeApi(error, 'No se pudo crear la cuenta. Revisa los datos e inténtalo otra vez.'),
          );
          for (const [campo, mensaje] of Object.entries(erroresDeCampo(error))) {
            if (Object.hasOwn(this.form.controls, campo)) {
              this.form.controls[campo as Campo].setErrors({ server: mensaje });
              this.form.controls[campo as Campo].markAsTouched();
            }
          }
        },
      });
  }

  confirmarEliminar(cuenta: Cuenta): void {
    if (this.busy()) return;
    this.pendingDelete.set(cuenta);
    this.showForm.set(false);
    this.actionError.set('');
    this.success.set('');
  }

  eliminar(): void {
    const cuenta = this.pendingDelete();
    if (!cuenta || this.busy()) return;
    this.saving.set(true);
    this.actionError.set('');
    this.api
      .delete(cuenta.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.pendingDelete.set(null);
          this.success.set(`Cuenta ${cuenta.usuario} eliminada correctamente.`);
          this.load();
        },
        error: (error: unknown) => {
          this.saving.set(false);
          // El 409 ("No puedes eliminar tu propia cuenta.") se muestra tal cual lo envía la API.
          this.actionError.set(
            mensajeApi(error, 'No se pudo eliminar la cuenta. Inténtalo otra vez.'),
          );
          this.pendingDelete.set(null);
        },
      });
  }

  rolTexto(rol: Rol): string {
    return rol === 'ADMINISTRADOR' ? 'Administrador' : 'Operador';
  }
}
