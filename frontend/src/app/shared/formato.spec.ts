import { fechaCorta, fechaHoraCorta, hoyBogota, pesos, sumarDias } from './formato';

describe('Formato de pagos', () => {
  it('fechaCorta muestra dd/mm/aaaa sin cambiar el día', () => {
    expect(fechaCorta('2026-09-01')).toBe('01/09/2026');
    expect(fechaCorta('2026-12-31')).toBe('31/12/2026');
    expect(fechaCorta(null)).toBe('');
    expect(fechaCorta('basura')).toBe('');
  });

  it('fechaHoraCorta muestra la hora de Bogotá', () => {
    expect(fechaHoraCorta('2026-09-01T12:00:00-05:00')).toBe('01/09/2026 12:00');
    expect(fechaHoraCorta('2026-09-01T17:30:00+00:00')).toBe('01/09/2026 12:30');
    expect(fechaHoraCorta('2026-09-02T02:05:00+00:00')).toBe('01/09/2026 21:05');
    expect(fechaHoraCorta(null)).toBe('');
    expect(fechaHoraCorta('no es fecha')).toBe('');
  });

  it('pesos usa punto como separador de miles', () => {
    expect(pesos(250000)).toBe('$250.000');
    expect(pesos(100000)).toBe('$100.000');
    expect(pesos(1500000)).toBe('$1.500.000');
    expect(pesos(999)).toBe('$999');
    expect(pesos(0)).toBe('$0');
    expect(pesos(null)).toBe('');
  });

  it('hoyBogota usa el día de Bogotá, no el de UTC', () => {
    expect(hoyBogota(new Date('2026-09-02T03:00:00Z'))).toBe('2026-09-01');
    expect(hoyBogota(new Date('2026-09-02T05:00:00Z'))).toBe('2026-09-02');
  });

  it('sumarDias suma días calendario', () => {
    expect(sumarDias('2026-09-01', 30)).toBe('2026-10-01');
    expect(sumarDias('2026-10-01', 30)).toBe('2026-10-31');
    expect(sumarDias('2026-12-20', 30)).toBe('2027-01-19');
  });
});
