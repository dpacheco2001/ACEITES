# OilMine Analytics — MVP

Sistema predictivo de mantenimiento para la flota 794AC de Quellaveco.
FastAPI + React + Vite · arquitectura hexagonal · modelos ML ya entrenados.

## Estructura

```
ACEITES_MINERIA/
├── DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx   (datos — sin tocar)
├── models/                                                       (3 modelos + feat_cols.json)
├── run_api.py                    ← arranca FastAPI en :8000
├── requirements.txt
├── src/                          ← backend Python
│   ├── domain/                   entidades, value objects, SemaforoService
│   ├── application/              ports (ABCs) + casos de uso
│   ├── infrastructure/           Excel repo, ModeloLoader, feature_builder, predictor
│   └── interfaces/api/           FastAPI (main, routers, schemas, deps)
└── frontend/                     ← React + Vite + Tailwind en :5173
    ├── package.json
    ├── vite.config.js            proxy /api → :8000
    └── src/
        ├── App.jsx  main.jsx  api.js  index.css
        ├── components/           Semaforo, StatCard
        └── pages/                Flota, Equipo, NuevaMuestra, Reportes
```

## Arranque

**Backend** (una vez):
```powershell
pip install -r requirements.txt
python run_api.py
# abre http://localhost:8000/docs
```

**Frontend** (otra terminal):
```powershell
cd frontend
npm install
npm run dev
# abre http://localhost:5173
```

## Endpoints REST

| Método | Ruta                              | Qué hace                                         |
|--------|-----------------------------------|--------------------------------------------------|
| GET    | `/health`                         | ping + flag de modelos cargados                  |
| GET    | `/variables`                      | las 12 variables, baja-confianza, límites alerta |
| GET    | `/equipos`                        | lista de IDs (33 camiones)                       |
| GET    | `/flota/resumen`                  | KPIs + tarjetas de todos los equipos             |
| GET    | `/equipos/{id}/prediccion`        | semáforo + estado + predicciones t+1 + horas     |
| GET    | `/equipos/{id}/historial`         | historial completo, más reciente primero         |
| POST   | `/equipos/{id}/muestras`          | registra muestra y devuelve predicción inmediata |
| GET    | `/equipos/{id}/exportar?formato=` | descarga CSV o XLSX del historial                |

## Reglas de negocio fijas (Sección 5 de la guía)

- **ROJO**: estado=CRITICO ∪ horas≥400 ∪ horas_hasta_critico≤50
- **AMARILLO**: estado=PRECAUCION ∪ horas≥300 ∪ horas_hasta_critico≤150
- **VERDE**: resto

## Notas técnicas

1. **Feature-engineering idéntico al entrenamiento** (`src/infrastructure/feature_builder.py`):
   truncations `var[:18]` y `var[:15]`, rolling sobre `shift(1)` (anti-leakage),
   delta/lag/rollmean/rollstd/trend por cada una de las 12 variables, y 5 features
   globales — total 173, alineados al `models/feat_cols.json`.
2. **Carga de modelos** perezosa y cacheada (`ModeloLoader` singleton),
   precargados en el `lifespan` de FastAPI para eliminar latencia en la 1ª petición.
3. **Excel como BD** con `threading.Lock` en `ExcelManager` para evitar
   corrupción bajo escrituras concurrentes.
4. **Orden cronológico**: el repositorio ordena por `(Fecha, Hora_Producto)` — así una
   muestra recién registrada siempre es la "última" aunque inicie un nuevo ciclo
   de aceite con `Hora_Producto` bajo.
5. **Variables con baja confianza** (`Potasio ppm`, `Cromo ppm`) se marcan con ⚠️
   en el frontend y en el campo `variables_baja_confianza` de la respuesta.

## Pantallas

1. **`/`** — Dashboard de flota: KPIs por color, filtro por semáforo, grid de
   tarjetas clicables por equipo.
2. **`/equipo/:id`** — Detalle: semáforo grande, curva de degradación por
   variable con ★ en la predicción t+1, 12 gauges (actual + t+1), tabla de
   historial paginada.
3. **`/nueva-muestra/:id`** — Formulario con fecha + hora_producto + 12 variables;
   al enviar muestra la predicción inmediata.
4. **`/reportes`** — Exporta el historial de un equipo como Excel o CSV.
