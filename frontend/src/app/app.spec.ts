import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('Navegación', () => {
  it('muestra en el menú solo las pantallas de la iteración, en orden', async () => {
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
    ]);
  });
});
