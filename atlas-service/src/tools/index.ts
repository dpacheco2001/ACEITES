import { tool } from 'ai';
import { z } from 'zod/v4';
import { env } from '../config/env.js';
import { createBackendClient } from './backend-client.js';
import { artifactInfo, listArtifacts, runDir, safeName, writeArtifact } from './artifacts.js';
import { runPython } from './python-runner.js';
import path from 'node:path';

export function createAtlasTools(cookieHeader: string | undefined, runId: string) {
  const backend = createBackendClient(cookieHeader);

  return {
    getModelContext: tool({
      description:
        'Obtiene algoritmos, reglas de semaforo, variables, confianza e importancia proxy. Usar antes de explicar metricas o el pipeline.',
      inputSchema: z.object({}),
      execute: async () => safe(() => backend.get('/atlas/model-context')),
    }),

    getDashboardResults: tool({
      description:
        'Obtiene resultados oficiales del dashboard de flota. Primera opcion para explicar estado global, criticos y resumen.',
      inputSchema: z.object({}),
      execute: async () => safe(() => backend.get('/atlas/dashboard-context')),
    }),

    getEquipmentResults: tool({
      description:
        'Obtiene prediccion oficial, drivers, variables y ultimas muestras de un equipo especifico.',
      inputSchema: z.object({
        equipoId: z.string().min(1).describe('ID de equipo, por ejemplo HT017'),
      }),
      execute: async ({ equipoId }) =>
        safe(() => backend.get(`/atlas/equipos/${encodeURIComponent(equipoId)}/context`)),
    }),

    createDatasetSlice: tool({
      description:
        'Crea un slice acotado JSON/CSV para revisar evidencia historica. No pedir todo el dataset.',
      inputSchema: z.object({
        equipoId: z.string().optional(),
        variables: z.array(z.string()).optional(),
        fechaDesde: z.string().optional(),
        fechaHasta: z.string().optional(),
        maxRows: z.number().int().min(1).max(1000).optional(),
      }),
      execute: async (input) =>
        safe(async () => {
          const payload = {
            equipo_id: input.equipoId,
            variables: input.variables,
            fecha_desde: input.fechaDesde,
            fecha_hasta: input.fechaHasta,
            max_rows: Math.min(input.maxRows || env.maxSliceRows, env.maxSliceRows),
          };
          const slice = await backend.post<{
            rows: Record<string, unknown>[];
            row_count_total: number;
            row_count_returned: number;
            truncated: boolean;
            variables: string[];
          }>('/atlas/slices', payload);
          const stamp = Date.now();
          const json = await writeArtifact(
            runId,
            `slice-${stamp}.json`,
            JSON.stringify(slice, null, 2),
          );
          const csv = await writeArtifact(runId, `slice-${stamp}.csv`, rowsToCsv(slice.rows));
          return {
            ok: true,
            row_count_total: slice.row_count_total,
            row_count_returned: slice.row_count_returned,
            truncated: slice.truncated,
            variables: slice.variables,
            artifacts: [json, csv],
            preview: slice.rows.slice(0, 8),
          };
        }),
    }),

    runPythonAnalysis: tool({
      description:
        'Ejecuta Python con pandas/matplotlib sobre los artefactos del run. Ultimo recurso para calculos o graficos.',
      inputSchema: z.object({
        reason: z.string().min(1),
        code: z.string().min(1).describe('Codigo Python. Guardar graficos como PNG en el cwd.'),
      }),
      execute: async ({ code, reason }) =>
        safe(async () => ({
          reason,
          ...(await runPython(runId, code)),
        })),
    }),

    showImage: tool({
      description:
        'Muestra en el chat una imagen PNG/JPG ya generada en el run, por ejemplo chart.png.',
      inputSchema: z.object({
        filename: z.string().min(1),
        caption: z.string().optional(),
      }),
      execute: async ({ filename, caption }) =>
        safe(async () => {
          const safeFile = safeName(filename);
          const info = await artifactInfo(runId, safeFile, path.join(runDir(runId), safeFile));
          return { ok: true, type: 'image', caption, image: info };
        }),
    }),

    listRunArtifacts: tool({
      description: 'Lista artefactos disponibles del run actual.',
      inputSchema: z.object({}),
      execute: async () => safe(() => listArtifacts(runId)),
    }),
  };
}

async function safe<T>(fn: () => Promise<T>): Promise<T | { ok: false; error: string }> {
  try {
    return await fn();
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

function rowsToCsv(rows: Record<string, unknown>[]): string {
  if (!rows.length) return '';
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map((header) => csvCell(row[header])).join(','));
  }
  return `${lines.join('\n')}\n`;
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const text = String(value).replace(/"/g, '""');
  return /[",\n]/.test(text) ? `"${text}"` : text;
}
