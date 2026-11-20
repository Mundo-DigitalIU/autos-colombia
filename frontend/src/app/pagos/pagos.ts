import { Component, signal } from '@angular/core';

type Pestana = 'mensualidades' | 'registrados';

@Component({
  selector: 'app-pagos',
  templateUrl: './pagos.html',
  styleUrl: '../shared/gestion.css',
})
export class Pagos {
  readonly pestana = signal<Pestana>('mensualidades');
}
