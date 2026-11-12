import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-sin-permiso',
  imports: [RouterLink],
  template: `
    <section class="management" aria-labelledby="sin-permiso-title">
      <header class="heading">
        <div>
          <span class="eyebrow">ACCESO RESTRINGIDO</span>
          <h1 id="sin-permiso-title">Sin permiso</h1>
          <p>No tienes permiso para entrar aquí.</p>
        </div>
      </header>
      <section class="panel">
        <p>Esta pantalla es solo para administradores. Si la necesitas, pídele acceso a uno.</p>
        <div class="actions">
          <a class="button-link" routerLink="/entrada">Volver a Entrada</a>
        </div>
      </section>
    </section>
  `,
  styleUrl: '../shared/gestion.css',
})
export class SinPermiso {}
