import EquipoRail from '../components/EquipoRail.jsx'

export default function Equipos() {
  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <EquipoRail />
      <section className="flex-1 p-6 md:p-10">
        <div className="max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight text-on-surface">
            Selecciona un equipo
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-on-surface-variant">
            Usa la lista lateral para buscar una unidad, revisar su estado
            operativo y abrir el detalle predictivo.
          </p>
        </div>
      </section>
    </div>
  )
}
