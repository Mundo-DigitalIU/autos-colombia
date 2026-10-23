import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('Navegación', () => {
  it('ofrece acceso a la gestión de vehículos', async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('a[href="/gestion/vehiculos"]')
        ?.textContent,
    ).toBe('Vehículos');
  });

  it('ordena el menú con las pantallas de la iteración primero', async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const enlaces = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('nav a'),
    ).map((a) => [a.textContent?.trim(), a.getAttribute('href')]);
    expect(enlaces).toEqual([
      ['Inicio', '/'],
      ['Entrada', '/entrada'],
      ['Salida', '/salida'],
      ['Dentro', '/dentro'],
      ['Historial', '/historial'],
      ['Celdas', '/estado-celdas'],
      ['Vehículos', '/gestion/vehiculos'],
      ['Operadores', '/gestion/operadores'],
      ['Control de acceso', '/control-acceso'],
      ['Gestión de celdas', '/gestion/celdas'],
    ]);
  });
});
