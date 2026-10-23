import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'control-acceso',
    title: 'Control de acceso | Autos Colombia',
    loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
  },
  {
    path: 'gestion/operadores',
    title: 'Operadores | Autos Colombia',
    loadComponent: () => import('./operadores/operadores').then((m) => m.Operadores),
  },
  {
    path: 'gestion/celdas',
    title: 'Celdas | Autos Colombia',
    loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
  },
  { path: '', pathMatch: 'full', loadComponent: () => import('./home/home').then((m) => m.Home) },
  {
    path: 'gestion/vehiculos',
    title: 'Vehículos | Autos Colombia',
    loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
  },

  {
    path: 'estado-celdas',
    title: 'Celdas | Autos Colombia',
    loadComponent: () => import('./estado-celdas/estado-celdas').then((m) => m.EstadoCeldas),
  },
  {
    path: 'dentro',
    title: 'Dentro | Autos Colombia',
    loadComponent: () => import('./dentro/dentro').then((m) => m.Dentro),
  },
  {
    path: 'historial',
    title: 'Historial | Autos Colombia',
    loadComponent: () => import('./historial/historial').then((m) => m.Historial),
  },
  {
    path: 'entrada',
    title: 'Entrada | Autos Colombia',
    loadComponent: () => import('./entrada/entrada').then((m) => m.Entrada),
  },
  { path: '**', redirectTo: '' },
];
