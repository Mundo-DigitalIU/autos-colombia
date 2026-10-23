import { fechaBogota } from './fecha';

describe('fechaBogota', () => {
  it('muestra un instante UTC en hora de Bogotá (UTC-5)', () => {
    expect(fechaBogota('2026-10-23T21:04:21Z')).toContain('4:04:21');
    expect(fechaBogota('2026-10-23T21:04:21Z')).toBe(fechaBogota('2026-10-23T16:04:21-05:00'));
  });
});
