const partesFechaHora = new Intl.DateTimeFormat('es-CO', {
  timeZone: 'America/Bogota',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

const partesFecha = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Bogota',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

/** "2026-09-01" → "01/09/2026". Solo reordena el texto: una fecha sin hora no cambia de día por la zona horaria. */
export function fechaCorta(fecha: string | null | undefined): string {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(fecha ?? '');
  return partes ? `${partes[3]}/${partes[2]}/${partes[1]}` : '';
}

/** Instante con zona horaria → "01/09/2026 12:00", siempre en hora de Bogotá. */
export function fechaHoraCorta(instante: string | null | undefined): string {
  if (!instante) return '';
  const fecha = new Date(instante);
  if (Number.isNaN(fecha.getTime())) return '';
  const p = Object.fromEntries(partesFechaHora.formatToParts(fecha).map((x) => [x.type, x.value]));
  return `${p['day']}/${p['month']}/${p['year']} ${p['hour']}:${p['minute']}`;
}

/** 250000 → "$250.000" (separador de miles con punto, sin decimales). */
export function pesos(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '';
  const entero = Math.round(Math.abs(valor)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${valor < 0 ? '-' : ''}$${entero}`;
}

/** Fecha de hoy en Bogotá, como AAAA-MM-DD. */
export function hoyBogota(ahora: Date = new Date()): string {
  return partesFecha.format(ahora);
}

/** Suma días a una fecha AAAA-MM-DD sin pasar por la zona horaria del navegador. */
export function sumarDias(fecha: string, dias: number): string {
  const [a, m, d] = fecha.split('-').map(Number);
  const resultado = new Date(Date.UTC(a, m - 1, d + dias));
  return resultado.toISOString().slice(0, 10);
}
