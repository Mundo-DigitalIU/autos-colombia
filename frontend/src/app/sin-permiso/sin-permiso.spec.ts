import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { SinPermiso } from './sin-permiso';

describe('Pantalla Sin permiso', () => {
  it('explica que no hay permiso y ofrece volver', async () => {
    await TestBed.configureTestingModule({
      imports: [SinPermiso],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(SinPermiso);
    fixture.detectChanges();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('h1')?.textContent).toContain('Sin permiso');
    expect(raiz.textContent).toContain('No tienes permiso para entrar aquí.');
    expect(raiz.querySelector('a')?.getAttribute('href')).toBe('/entrada');
  });
});
