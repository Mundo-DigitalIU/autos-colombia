import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { mensajeApi } from '../shared/errores';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: '../shared/gestion.css',
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly form = this.fb.nonNullable.group({ usuario: '', contrasena: '' });
  readonly aviso = signal(this.auth.consumirAviso());
  readonly saving = signal(false);
  readonly errorUsuario = signal('');
  readonly errorContrasena = signal('');
  readonly error = signal('');

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.errorUsuario.set('');
      this.errorContrasena.set('');
      this.error.set('');
    });
  }

  entrar(): void {
    if (this.saving()) return;
    const usuario = this.form.controls.usuario.value.trim();
    const contrasena = this.form.controls.contrasena.value;
    this.errorUsuario.set(usuario ? '' : 'Escribe tu usuario.');
    this.errorContrasena.set(contrasena.trim() ? '' : 'Escribe tu contraseña.');
    if (!usuario || !contrasena.trim()) return;
    this.saving.set(true);
    this.aviso.set('');
    this.error.set('');
    this.auth
      .login({ usuario, contrasena })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          void this.router.navigateByUrl('/entrada');
        },
        error: (error: unknown) => {
          this.saving.set(false);
          this.form.controls.contrasena.setValue('', { emitEvent: false });
          this.error.set(mensajeApi(error));
        },
      });
  }
}
