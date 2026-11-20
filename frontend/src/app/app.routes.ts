import { Routes } from '@angular/router';
import { administradorGuard, sesionGuard, visitanteGuard } from './auth/auth.guards';

// Las rutas evitan los prefijos del proxy de desarrollo (/estancias, /celdas, /vehiculos,
// /operadores, /auth, /cuentas, /clientes, /pagos y /health): por eso las pantallas viven en /panel.
export const routes: Routes = [
  {
    path: 'login',
    title: 'Iniciar sesión | Autos Colombia',
    canActivate: [visitanteGuard],
    loadComponent: () => import('./login/login').then((m) => m.Login),
  },
  {
    path: 'sin-permiso',
    title: 'Sin permiso | Autos Colombia',
    canActivate: [sesionGuard],
    loadComponent: () => import('./sin-permiso/sin-permiso').then((m) => m.SinPermiso),
  },
  {
    // Todo lo demás exige sesión.
    path: '',
    canActivate: [sesionGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'entrada' },
      {
        path: 'entrada',
        title: 'Entrada | Autos Colombia',
        loadComponent: () => import('./entrada/entrada').then((m) => m.Entrada),
      },
      {
        path: 'salida',
        title: 'Salida | Autos Colombia',
        loadComponent: () => import('./salida/salida').then((m) => m.Salida),
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
        path: 'estado-celdas',
        title: 'Celdas | Autos Colombia',
        loadComponent: () => import('./estado-celdas/estado-celdas').then((m) => m.EstadoCeldas),
      },
      {
        path: 'inicio',
        title: 'Inicio | Autos Colombia',
        loadComponent: () => import('./home/home').then((m) => m.Home),
      },
      {
        path: 'control-acceso',
        title: 'Control de acceso | Autos Colombia',
        loadComponent: () => import('./control-acceso/control-acceso').then((m) => m.ControlAcceso),
      },
      {
        path: 'panel/clientes',
        title: 'Clientes | Autos Colombia',
        loadComponent: () => import('./clientes/clientes').then((m) => m.Clientes),
      },
      {
        path: 'panel/pagos',
        title: 'Pagos | Autos Colombia',
        loadComponent: () => import('./pagos/pagos').then((m) => m.Pagos),
      },
      {
        path: 'panel/pagos/registrar',
        title: 'Registrar pago | Autos Colombia',
        loadComponent: () => import('./pagos/registrar-pago').then((m) => m.RegistrarPago),
      },
      {
        path: 'panel/pagos/comprobante/:id',
        title: 'Comprobante de pago | Autos Colombia',
        loadComponent: () => import('./pagos/comprobante').then((m) => m.Comprobante),
      },
      {
        path: 'panel/celdas',
        title: 'Gestionar celdas | Autos Colombia',
        canActivate: [administradorGuard],
        loadComponent: () => import('./gestion-celdas/gestion-celdas').then((m) => m.GestionCeldas),
      },
      {
        path: 'panel/cuentas',
        title: 'Cuentas | Autos Colombia',
        canActivate: [administradorGuard],
        loadComponent: () => import('./cuentas/cuentas').then((m) => m.Cuentas),
      },
      // Pantallas de la Iteración 1 (profesor): solo el administrador.
      {
        path: 'gestion/operadores',
        title: 'Operadores | Autos Colombia',
        canActivate: [administradorGuard],
        loadComponent: () => import('./operadores/operadores').then((m) => m.Operadores),
      },
      {
        path: 'gestion/celdas',
        title: 'Celdas | Autos Colombia',
        canActivate: [administradorGuard],
        loadComponent: () => import('./celdas/celdas').then((m) => m.Celdas),
      },
      {
        path: 'gestion/vehiculos',
        title: 'Vehículos | Autos Colombia',
        canActivate: [administradorGuard],
        loadComponent: () => import('./vehiculos/vehiculos').then((m) => m.Vehiculos),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
