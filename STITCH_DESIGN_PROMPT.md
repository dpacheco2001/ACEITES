# Prompt para Google Stitch — OilMine Analytics

> Pega este prompt completo en Google Stitch. Genera un set cohesivo de 4 pantallas principales + componentes reutilizables para una app SaaS de analítica predictiva en minería.

---

## Product brief

**OilMine Analytics** is an Agent-as-a-Service (AAS) dashboard for predictive maintenance of Caterpillar 794AC mining trucks at the Quellaveco copper mine (Anglo American, Peru). The product monitors oil-analysis samples from 33 truck engines and uses three ML models (state classifier, 12 per-variable regressors, time-to-critical estimator) to warn maintenance engineers before a catastrophic failure.

The target user is a **mining maintenance engineer** — technical, time-pressured, reviewing fleet health from a control room or on a ruggedized laptop at the pit. The design must feel **industrial, serious, data-dense, trustworthy** — closer to Bloomberg Terminal or Palantir Foundry than to a consumer app.

## Brand & visual language

- **Vibe:** heavy industry × high-tech. Dark, cinematic, mission-critical.
- **Primary palette (dark theme only, no light mode):**
  - Background base: `#0b1220` (near-black navy, slight blue tint — like used engine oil)
  - Surface / cards: `#111a2e` with 1px border `#1e293b`
  - Elevated surface: `#0f172a`
  - Text primary: `#e2e8f0`; secondary: `#94a3b8`; muted: `#64748b`
- **Semaphore accent colors (central to the product):**
  - Green (NORMAL): `#22c55e`
  - Yellow / Amber (PRECAUCION): `#f59e0b`
  - Red (CRITICO): `#ef4444`
  - Use these colors with 10–20% opacity backgrounds for badges, rings for emphasis, pure color for icons and chart dots.
- **Brand accent:** amber-gold `#f59e0b` (oil color) for primary CTAs, active nav items, and highlighted metrics.
- **Typography:** Inter for UI, JetBrains Mono for numeric tables and sensor values. Weights 400/600/800. Use all-caps + `tracking-widest` labels for metric titles.
- **Iconography:** Lucide icons, line-weight 1.5. Alert triangle ⚠ for low-confidence indicators.
- **Motion:** subtle only. 150–200ms ease-out on hovers; no flashy animations — this is a monitoring tool.

## Core conceptual pattern — the "confidence flag"

Every prediction the product shows carries a **confidence flag**. When a prediction is low-confidence (short history, or time-to-critical outside 20–100h), the UI shows a ⚠ amber warning icon *next to the value itself* and a banner with the reason. Do NOT hide low-confidence values — show them, but mark them. This honesty is a core product value.

## Global layout

Single-page app with a **persistent left sidebar** (64px collapsed / 224px expanded) and a main content area (max-width 1440px, centered).

**Sidebar items (top to bottom):**
1. Logo "OilMine" + subtitle "Analytics" (amber accent on "Mine")
2. Divider
3. `Flota` (truck icon) — default
4. `Equipo` (wrench icon) — shown when an equipment is selected
5. `Nueva muestra` (plus-circle icon)
6. `Reportes` (download icon)
7. Divider, pushed to bottom
8. Health pill: green dot + "API OK · 3 modelos" OR red dot + "API desconectada"
9. User avatar with role label "Ingeniero de mantenimiento"

**Top bar (inside content area):**
- Breadcrumb on the left (e.g., `Flota / HT012`)
- Last-sync timestamp on the right: "Actualizado hace 3 min · 33 equipos"

---

## Screen 1 — Flota (Fleet dashboard) — DEFAULT

Purpose: at-a-glance view of all 33 trucks, sorted by severity.

**Hero header:**
- H1 `Estado actual de la flota` (3xl, bold, white)
- Subtitle: `Monitoreo en vivo de 33 camiones Caterpillar 794AC · Quellaveco`

**KPI strip (4 equal cards in a row):**
1. `Total equipos` — value `33` (large numeric), neutral slate color
2. `Rojo` — value `8` (large), red color, red 10% background, tiny flame icon
3. `Amarillo` — value `12`, amber color, warning-triangle icon
4. `Verde` — value `13`, green color, check-circle icon

**Filter chips** (horizontal row): `Todos` · `Rojo` · `Amarillo` · `Verde`. The active chip has a colored ring matching its state.

**Equipment grid** — responsive grid (4 columns desktop, 2 tablet, 1 mobile). Each card:
- Top-left: label `EQUIPO` (uppercase, tracking-widest, tiny) + Equipment ID `HT012` (2xl, extra-bold)
- Top-right: a **circular semaphore dot** (18px) — solid red/amber/green, glowing shadow matching color. If the prediction is low-confidence, show a small ⚠ amber icon *immediately left* of the dot.
- Badge row: colored pill with the model-predicted state (`CRITICO` / `PRECAUCION` / `NORMAL`), background at 10% opacity of its color.
- Two metrics in a 2-col grid:
  - `HORAS ACTUALES` → `509.0 h` (bold mono)
  - `HASTA CRÍTICO` → `27.2 h` (bold mono). If the value is unreliable, append a small amber ⚠ after the label.
- Footer row (tiny text, slate-500): `Muestras: 178` on the left, date `2024-03-20` on the right. If history is insufficient, show `Muestras: 3 ⚠`.
- **Hover state:** border transitions to amber accent, subtle lift.
- Whole card is clickable → navigates to Screen 2.

**Sort order (descending severity):** red equipment first, then yellow, then green. Within each group, order by `horas_actuales` descending.

---

## Screen 2 — Equipo (Equipment detail)

Purpose: everything about one specific truck. Deep dive.

**Breadcrumb:** `← Flota / HT012`

**Hero row** (full-width card, flex horizontal):
- Left: large 48px semaphore dot with glow
- Center: label `EQUIPO` (tiny uppercase) + `HT012` (4xl extra-bold white) + badge row with state + text `Semáforo: ROJO`
- Right: amber primary button `+ Registrar nueva muestra`

**Confidence banner (conditional, shown only when `advertencias[]` non-empty):**
- Left amber border-l-4, amber 5% background
- Amber ⚠ icon + header "Advertencias de confianza"
- Bulleted list in slate-300:
  - `Historia insuficiente (3 muestras, se recomiendan ≥5). Predicciones con baja confianza.`
  - `Horas hasta crítico fuera del rango confiable del Modelo C (20-100h). Valor: 120.0h — interpretar con cautela.`

**KPI strip (4 cards):**
1. `HORAS ACTUALES` — `509.0 h` — amber accent
2. `HORAS HASTA CRÍTICO` (or `HORAS HASTA CRÍTICO ⚠` if unreliable) — `27.2 h` — red/amber/green matching semaphore
3. `TOTAL MUESTRAS` — `178`
4. `ÚLTIMA MUESTRA` — `2024-03-20`

**Degradation chart** (large card, full width, 320px tall):
- Title `Curva de degradación`
- Subtitle `Eje X: Hora_Producto (horas acumuladas del aceite). ★ = predicción t+1.`
- Top-right: variable selector dropdown (all 12 variables)
- Recharts-style LineChart: blue `#38bdf8` line, dark grid `#1e293b`, dots colored by sample state (green/amber/red), a yellow/gold ★ reference marker at the predicted t+1 position
- Hover tooltip: dark navy with light border, shows (hora, valor, estado)

**"Última muestra — valores actuales" section:**
- H2
- Grid of 12 gauge cards (4-col desktop). Each gauge:
  - Tiny uppercase variable label (`TBN (mg KOH/g)`, `Viscosidad a 100 °C cSt`, etc.)
  - Large numeric value colored by its limit zone (green/amber/red)
  - If variable is `Potasio ppm` or `Cromo ppm` (low R² flagged), show a ⚠ icon in the top-right corner with tooltip "Baja confianza (R² negativo)".

**"Predicciones para la próxima muestra (t+1)" section:**
- Same grid of 12 gauges, but showing predicted values.
- Same low-confidence ⚠ rule applies.

**Historial table** (card with sticky header):
- Title row with count: `Historial completo (178 muestras)`
- Columns: `Fecha` | `Hora_Producto` (mono, right-aligned) | `Estado` (colored badge) | first 6 variable columns
- Scroll container 420px max-height, hover row highlight, zebra stripes NOT used (too visual noise), just hover bg `slate-800/30`.

---

## Screen 3 — Nueva muestra (New sample form)

Purpose: register a fresh oil-analysis result for a specific truck. Writes to the Excel DB and returns an immediate prediction.

**Header:** `Registrar nueva muestra` + subtitle `El sistema predecirá inmediatamente el estado tras guardar.`

**Form card:**
- **Row 1 — Metadata (3 columns):**
  - `Equipo` — dropdown prefilled if coming from Screen 2
  - `Fecha` — date picker (default: today)
  - `Hora del producto (h)` — number input, gt 0, suffix "h"
- **Row 2 — Estado (optional) radio group:** `NORMAL` / `PRECAUCION` / `CRITICO` — each option is a pill with its semaphore color when active.
- **Divider** + section heading `Resultados de laboratorio (12 variables)`
- **Variable grid (3 columns × 4 rows = 12 number inputs):**
  - Each input shows: variable name label, unit, and a tiny inline "range válido: 7.0+" (derived from LIMITES_ALERTA).
  - Input right-aligned mono, amber focus ring.
  - Low-confidence variables (Potasio, Cromo) get a small ⚠ with tooltip.
- **Footer:** cancel button (ghost, left) + primary amber button `Guardar y predecir` (right, disabled while submitting, spinner when active).

**After submit:**
- Redirect to Screen 2 for that equipment, with a **toast** top-right: green check icon + "Muestra registrada. Predicción actualizada." (auto-dismiss 4s)
- If backend returns 422 (missing values), show inline red error below the offending inputs.

---

## Screen 4 — Reportes (Reports & export)

Purpose: download data for offline analysis or management reports.

**Header:** `Reportes y exportación` + subtitle `Descarga el historial de un equipo o el resumen completo de la flota.`

**Two stacked cards (each 600px max-width, centered):**

**Card A — Historial por equipo:**
- H2 `Historial por equipo`
- `Equipo` dropdown (33 options)
- Two date inputs in a row: `Desde` / `Hasta` (optional filter). Below them a tiny ghost link `Limpiar filtro de fechas` when either is set.
- Button row: amber primary `Descargar Excel` + ghost `Descargar CSV`.

**Card B — Resumen de flota:**
- H2 `Resumen de flota`
- Descriptive paragraph: `Una fila por equipo con el estado actual: semáforo, horas, horas hasta crítico y flags de confianza.`
- Button row: amber `Descargar Excel` + ghost `Descargar CSV`.

**Success/error strip** (sticky at bottom of content area):
- Green: `✓ Descargado: HT012_historial_2024-01-01_a_2024-03-31.xlsx`
- Red: `⚠ <mensaje de error>`

---

## Reusable components to produce

1. **`<Semaforo estado={...} size={...} />`** — glowing colored circle, sizes 18/24/48px. Ring-halo in the same color at 30% opacity.
2. **`<StatCard title value color />`** — KPI card with uppercase label, giant numeric value, 10% color background.
3. **`<Badge color>TEXT</Badge>`** — pill, 10% bg + full-color text + subtle ring.
4. **`<Gauge variable valor limites bajaConfianza />`** — compact card with variable label, colored numeric, ⚠ slot.
5. **`<ConfidenceBanner advertencias={[]} />`** — amber warning banner with bulleted list.
6. **`<Sidebar />`** — persistent left navigation, collapsible.
7. **`<Breadcrumb />`** — slate text trail, amber hover.

## Grid & spacing

- 8px base unit. Common spacings: 8 / 16 / 24 / 32 / 48.
- Cards: 24px interior padding, 12px border-radius, 1px border `#1e293b`.
- Section vertical rhythm: 32px between major sections on a screen.

## States to cover in the design

- **Loading:** skeleton cards (shimmer slate-800 → slate-700) for KPI strip and equipment grid. Full-page "Cargando estado de la flota..." centered card on cold load.
- **Error:** red-bordered card in the content area: `Error: <mensaje>`, with retry button.
- **Empty:** if the filter shows 0 equipment, gray truck icon + text `No hay equipos con este estado`.
- **Low confidence / insufficient history:** show ⚠ icons but never hide the data.

## Accessibility

- Minimum contrast 4.5:1 on text. The green/amber/red on dark navy meets this.
- Every ⚠ icon has a text-visible tooltip (not just color).
- Focus rings amber `#f59e0b` 2px visible on every interactive element.
- Keyboard navigation fully supported.

## Deliverables expected from Stitch

- 4 main screens as separate frames (Flota, Equipo, Nueva muestra, Reportes).
- A **component library** frame with all reusable pieces listed above.
- Variants for each card showing the three semaphore states.
- At least one screen shown in the "low confidence" variant (Equipo with the amber warning banner visible).
- All text in **Spanish (Latin America)** — this is a Peruvian mining operation.

---

## Example real data to use in mockups (makes it feel real, not Lorem Ipsum)

- Equipment IDs: `HT001`, `HT002`, `HT012`, `HT017`, `HT021`, `HT027`, `HT033`.
- Variable names (exact strings): `TBN (mg KOH/g)`, `Viscosidad a 100 °C cSt`, `Hollin ABS/01 mm`, `Fierro ppm`, `Oxidación ABS/01 mm`, `Sulfatación ABS/01 mm`, `Nitración ABS/01 mm`, `Cobre ppm`, `Potasio ppm`, `Silicio ppm`, `Aluminio ppm`, `Cromo ppm`.
- Sample values for a red truck: Horas 509, HTC 27.2h, TBN 6.8, Viscosidad 12.9, Hollín 38, Fierro 74.
- Sample values for a green truck: Horas 185, HTC 280h, TBN 8.9, Viscosidad 14.7, Hollín 12, Fierro 28.
- Dates between `2024-01-08` and `2024-03-28`.
- Site label: `Quellaveco · Anglo American · Perú`.

Tone: direct, technical, no marketing fluff. This is a tool people use to prevent a $2M engine failure.
