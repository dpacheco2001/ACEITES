# OilMine Analytics — MVP

Sistema predictivo de mantenimiento para la flota 794AC de Quellaveco.
FastAPI + React + Vite · arquitectura hexagonal · modelos ML ya entrenados.
La persistencia de usuarios, organizaciones y membresías usa Postgres con
`asyncpg`.

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
├── frontend/                     ← React + Vite + Tailwind en :5173
    ├── package.json
    ├── vite.config.js            proxy /api a :8000 y /atlas-api a :8787
    └── src/
        ├── App.jsx  main.jsx  api.js  index.css
        ├── components/           Semaforo, StatCard
        └── pages/                Flota, Equipo, NuevaMuestra, Reportes
└── atlas-service/                ← Vercel AI SDK + tools Atlas en :8787
    └── src/
        ├── prompts/              system prompt y templates
        ├── tools/                backend, slices, Python, artefactos
        └── agent/                compaction de contexto
```

## Arranque

**Linux / Bash**:
```bash
aceites on      # levanta backend + atlas-service + frontend
aceites status  # verifica procesos y endpoints
aceites logs    # sigue logs
aceites off     # baja backend + atlas-service + frontend
```

El helper vive en `scripts/aceites` y se carga desde `scripts/aceites.bashrc`.

**Variables de entorno**:
```bash
cp .env.example .env
# Rellena GOOGLE_CLIENT_ID, JWT_SECRET y GOOGLE_API_KEY.
```

La sesión usa cookie HttpOnly (`oilmine_session` por defecto). El access token
dura 60 minutos salvo que cambies `ACCESS_TOKEN_EXPIRE_MINUTES`.

La organización se resuelve por membresía explícita de correo. Un admin agrega
un email en `/admin/usuarios`; cuando ese usuario entra con Google queda dentro
de la misma organización. Si una organización no tiene dataset cargado, la app
redirige al admin a `/admin/datos` antes de abrir Flota.

Atlas usa `GOOGLE_API_KEY` solo desde `atlas-service`; no se expone al frontend.
Defaults: `ATLAS_PORT=8787`, `ATLAS_MODEL=gemini-3-flash-preview`,
`ATLAS_TOOL_MAX_STEPS=8`, `ATLAS_MAX_SLICE_ROWS=500`.

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
| GET    | `/auth/client-config`             | Client ID público para Google Identity Services  |
| POST   | `/auth/google`                    | valida Google ID token y crea cookie HttpOnly    |
| POST   | `/auth/logout`                    | limpia la cookie de sesión                       |
| GET    | `/me`                             | perfil público de la sesión actual               |
| GET    | `/variables`                      | las 12 variables, baja-confianza, límites alerta |
| GET    | `/equipos`                        | lista de IDs (33 camiones)                       |
| GET    | `/flota/resumen`                  | KPIs + tarjetas de todos los equipos             |
| GET    | `/equipos/{id}/prediccion`        | semáforo + estado + predicciones t+1 + horas     |
| GET    | `/equipos/{id}/historial`         | historial completo, más reciente primero         |
| POST   | `/equipos/{id}/muestras`          | registra muestra y devuelve predicción inmediata |
| GET    | `/equipos/{id}/exportar?formato=` | descarga CSV o XLSX del historial                |
| GET    | `/atlas/model-context`            | algoritmos, reglas, features, confianza          |
| GET    | `/atlas/dashboard-context`        | resultados oficiales del dashboard para Atlas    |
| GET    | `/atlas/equipos/{id}/context`     | predicción, drivers, señales e historial reciente|
| POST   | `/atlas/slices`                   | slice acotado para análisis o gráficos           |
| GET    | `/org/dataset/status`             | estado de dataset y headers requeridos           |
| POST   | `/org/dataset/validate`           | valida Excel/CSV antes de importar               |
| POST   | `/org/dataset/import`             | importa dataset validado para la organización    |
| GET    | `/admin/users`                    | lista usuarios de la organización (ADMIN)        |
| POST   | `/admin/members`                  | agrega membresía por email                       |
| PATCH  | `/admin/users/{id}/role`          | cambia rol ADMIN/CLIENTE (ADMIN)                 |

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
5. **Variables con baja confianza** (`Potasio ppm`, `Cromo ppm`) se marcan con
   advertencia visual en el frontend y en el campo `variables_baja_confianza`
   de la respuesta.

## Documentación técnica

- [Auditoría y propuesta Atlas](docs/auditoria_atlas.md)
- [Pipeline ML actual](docs/pipeline_ml_actual.md)
- [Resultados de pruebas Atlas](docs/atlas_test_results.md)
- [Docker, Postgres y persistencia Atlas](docs/docker_postgres_atlas_persistence.md)
- [Owner, organizaciones e ingesta](docs/owner_org_data_architecture.md)

## Pantallas

1. **`/`** — Dashboard de flota: KPIs por color, filtro por semáforo, grid de
   tarjetas clicables por equipo.
2. **`/equipo/:id`** — Detalle: semáforo grande, curva de degradación por
   variable con marca `P` en la predicción t+1, 12 gauges (actual + t+1), tabla de
   historial paginada.
3. **`/nueva-muestra/:id`** — Formulario con fecha + hora_producto + 12 variables;
   al enviar muestra la predicción inmediata.
4. **`/reportes`** — Exporta el historial de un equipo como Excel o CSV.
