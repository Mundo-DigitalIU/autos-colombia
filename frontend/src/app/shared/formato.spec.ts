import {
  fechaCorta,
  fechaHora12,
  fechaHoraCorta,
  hoyBogota,
  numeroPago,
  pesos,
  sumarDias,
} from './formato';

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

  it('fechaHora12 muestra 12 horas con a. m. y p. m. en hora de Bogotá', () => {
    expect(fechaHora12('2026-10-23T10:42:00-05:00')).toBe('23/10/2026 · 10:42 a. m.');
    expect(fechaHora12('2026-09-01T12:00:00-05:00')).toBe('01/09/2026 · 12:00 p. m.');
    expect(fechaHora12('2026-09-01T00:05:00-05:00')).toBe('01/09/2026 · 12:05 a. m.');
    expect(fechaHora12('2026-09-01T15:30:00-05:00')).toBe('01/09/2026 · 03:30 p. m.');
    expect(fechaHora12('2026-09-02T02:05:00+00:00')).toBe('01/09/2026 · 09:05 p. m.');
    expect(fechaHora12(null)).toBe('');
  });

  it('numeroPago rellena con ceros a 6 dígitos', () => {
    expect(numeroPago(184)).toBe('000184');
    expect(numeroPago(7)).toBe('000007');
    expect(numeroPago(1234567)).toBe('1234567');
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
