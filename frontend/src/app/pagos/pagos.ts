import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Mensualidades } from './mensualidades';
import { PagosRegistrados } from './pagos-registrados';

type Pestana = 'mensualidades' | 'registrados';

@Component({
  selector: 'app-pagos',
  imports: [Mensualidades, PagosRegistrados, RouterLink],
  templateUrl: './pagos.html',
  styleUrl: '../shared/gestion.css',
})
export class Pagos {
  readonly pestana = signal<Pestana>('mensualidades');
}
