// Mapea semáforo del dominio → tokens MD3 que usa el diseño visual.
// ROJO / AMARILLO / VERDE son conceptos del backend;
// "error" / "tertiary" / "surface-tint" son los roles MD3 que el usuario eligió.

export const SEMAFORO_THEME = {
  ROJO: {
    label: 'Crítico',
    dot: 'bg-error',
    dotGlow: 'shadow-[0_0_8px_rgba(186,26,26,0.6)]',
    iconBg: 'bg-error-container',
    iconFg: 'text-error',
    chipBg: 'bg-error-container/60',
    chipFg: 'text-on-error-container',
    kpiBg: 'bg-error-container',
    kpiFg: 'text-on-error-container',
    barra: 'bg-error',
    label_fg: 'text-error',
  },
  AMARILLO: {
    label: 'Precaución',
    dot: 'bg-tertiary-container',
    dotGlow: 'shadow-[0_0_8px_rgba(222,194,154,0.7)]',
    iconBg: 'bg-tertiary-container',
    iconFg: 'text-tertiary-fixed',
    chipBg: 'bg-tertiary-fixed',
    chipFg: 'text-tertiary-container',
    kpiBg: 'bg-tertiary-container',
    kpiFg: 'text-on-tertiary-container',
    barra: 'bg-tertiary-fixed-dim',
    label_fg: 'text-on-tertiary-container',
  },
  VERDE: {
    label: 'Óptimo',
    dot: 'bg-surface-tint',
    dotGlow: '',
    iconBg: 'bg-surface-container',
    iconFg: 'text-surface-tint',
    chipBg: 'bg-surface-container-high',
    chipFg: 'text-on-surface',
    kpiBg: 'bg-surface-container-lowest',
    kpiFg: 'text-on-surface',
    barra: 'bg-surface-tint',
    label_fg: 'text-surface-tint',
  },
}

export function temaSemaforo(sem) {
  return SEMAFORO_THEME[sem] || SEMAFORO_THEME.VERDE
}

// Formatea horas con formato 18,452.3 (en-US) como en el diseño
export function fmtHoras(n) {
  if (n == null || isNaN(n)) return '—'
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

// "Horas actuales" es Hora_Producto (horas del aceite) — entero o .1
export function fmtHorasAceite(n) {
  if (n == null || isNaN(n)) return '—'
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: 1 })
}

// Tiempo relativo del tipo "2M AGO"
export function relativeAgo(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const delta = Date.now() - d.getTime()
  const min = Math.floor(delta / 60000)
  if (min < 1) return 'JUST NOW'
  if (min < 60) return `${min}M AGO`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}H AGO`
  const dd = Math.floor(hr / 24)
  if (dd < 30) return `${dd}D AGO`
  return d.toISOString().slice(0, 10)
}
