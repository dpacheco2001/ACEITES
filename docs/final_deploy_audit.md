# Auditoria final de despliegue

Fecha: 2026-04-30

## Estado

- Produccion: `https://oilmine.site`
- Docker: activo para `postgres`, `api`, `atlas` y `frontend`.
- Postgres: activo con volumen persistente `postgres_data`.
- Postgres interno: `postgres:5432`.
- Postgres en host: publicado solo en `127.0.0.1` con puerto aleatorio de Docker.
- HTTPS: activo con Certbot y renovacion automatica.
- Deploy automatico: workflow GitHub Actions para `main` con runner `oilmine-prod`.

## Cambios validados

- `tenant_key` ya no se pide en el formulario owner; se genera desde el nombre.
- Owner puede crear organizaciones con admin inicial.
- Owner puede transferir ownership a otro correo.
- Owner puede desactivar organizaciones con soft delete (`status=DELETED`).
- No se permite desactivar la organizacion de la sesion actual.
- No se permite que un admin se quite a si mismo el rol `ADMIN`.
- Si una organizacion esta `DELETED`, sus usuarios no pueden usar la sesion.

## Pruebas ejecutadas

- `python3 -m compileall src`
- `npm run build` en `frontend`
- `docker compose build api frontend`
- `docker compose up -d`
- `git diff --check`
- Health local:
  - API healthy
  - Atlas healthy
  - Frontend healthy
  - Postgres healthy
- Health produccion:
  - `https://oilmine.site` responde `200`
  - `https://oilmine.site/api/health` responde ok
  - `https://oilmine.site/atlas-api/health` responde ok
- Smoke con `diegojavier20010@gmail.com`:
  - `/api/me`
  - `/api/org/dataset/status`
  - dataset `veyon`: 3720 filas, 33 equipos
  - create organization owner
  - transfer owner
  - soft delete organization
  - self-demotion admin bloqueada con `403`

## Evidencia Postgres

Consulta en produccion:

```sql
select tenant_key, status from organizations order by id;
```

Resultado observado:

```text
veyon           ACTIVE
auditoria-final DELETED
```

## Notas

- La persistencia SQL usa Postgres mediante `DATABASE_URL`; si falta esa variable el backend falla de forma explicita.
- Las consultas de usuarios, owners y membresias usan `asyncpg` con pool async inicializado en el lifespan de FastAPI.
- El frontend divide chunks por proveedor para evitar bundles monoliticos en Vite.
