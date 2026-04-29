export default function StatCard({ title, value, subtitle, color = 'accent' }) {
  const palette = {
    accent: 'from-oil-accent/10 to-transparent text-oil-accent ring-oil-accent/30',
    verde: 'from-verde/10 to-transparent text-verde ring-verde/30',
    amarillo: 'from-amarillo/10 to-transparent text-amarillo ring-amarillo/30',
    rojo: 'from-rojo/10 to-transparent text-rojo ring-rojo/30',
    slate: 'from-slate-600/10 to-transparent text-slate-200 ring-slate-600/40',
  }[color]
  return (
    <div className={`card relative overflow-hidden`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${palette} opacity-70`} />
      <div className="relative p-5">
        <div className="text-xs uppercase tracking-widest text-slate-400 font-semibold">{title}</div>
        <div className={`mt-2 text-4xl font-extrabold`}>{value}</div>
        {subtitle && <div className="mt-1 text-xs text-slate-400">{subtitle}</div>}
      </div>
    </div>
  )
}
