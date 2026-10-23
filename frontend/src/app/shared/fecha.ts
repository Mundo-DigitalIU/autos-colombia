const formato = new Intl.DateTimeFormat('es-CO', {
  timeZone: 'America/Bogota',
  dateStyle: 'medium',
  timeStyle: 'medium',
});

/** Muestra una fecha de la API (UTC) en la zona horaria America/Bogota. */
export const fechaBogota = (value: string): string => formato.format(new Date(value));
