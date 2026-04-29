export default function Semaforo({ estado = 'VERDE', size = 14, pulse = true }) {
  const color =
    estado === 'ROJO' ? 'bg-rojo' :
    estado === 'AMARILLO' ? 'bg-amarillo' : 'bg-verde'
  const glow =
    estado === 'ROJO' ? 'shadow-[0_0_24px_rgba(239,68,68,0.7)]' :
    estado === 'AMARILLO' ? 'shadow-[0_0_20px_rgba(245,158,11,0.6)]' :
    'shadow-[0_0_20px_rgba(34,197,94,0.55)]'
  return (
    <div
      className={`rounded-full ${color} ${glow} ${pulse ? 'animate-pulse' : ''}`}
      style={{ width: size, height: size }}
      aria-label={`Semáforo ${estado}`}
    />
  )
}
