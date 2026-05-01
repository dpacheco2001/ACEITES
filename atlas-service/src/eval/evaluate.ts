import fs from 'node:fs/promises';
import path from 'node:path';
import { generateText, stepCountIs } from 'ai';
import { compactMessages } from '../agent/compaction.js';
import { env, requireGoogleKey } from '../config/env.js';
import { atlasModel, googleProviderOptions } from '../config/providers.js';
import { ATLAS_SYSTEM_PROMPT } from '../prompts/system.js';
import { createRunId } from '../tools/artifacts.js';
import { createAtlasTools } from '../tools/index.js';

const prompts = [
  'Explicame el dashboard actual.',
  'Dame las muestras/equipos criticos y por que.',
  'Que fue con HT017, por que esta critico.',
  'Explicame que significa horas hasta critico.',
  'Grafica Fierro ppm y TBN para HT017.',
  'Haz un analisis exploratorio solo si los resultados existentes no bastan.',
];

const offlineFixture = `
Fixture runtime verificado: 33 equipos, 3720 muestras, estado PRECAUCION/CRITICO/NORMAL.
Pipeline: XGBoost clasifica estado, 12 LightGBM predicen t+1, otro LightGBM estima horas hasta critico.
Semaforo ROJO si estado CRITICO, horas actuales >=400 o horas hasta critico <=50.
Semaforo AMARILLO si PRECAUCION, horas actuales >=300 o horas hasta critico <=150.
Variables baja confianza: Potasio ppm y Cromo ppm.
No hay artefacto runtime SHAP ni PCA.
`.trim();

async function main() {
  const started = new Date();
  const cookie = process.env.ATLAS_TEST_COOKIE;
  const useTools = Boolean(cookie);
  const results = [];
  requireGoogleKey();

  for (const prompt of prompts) {
    const runId = await createRunId();
    const message = useTools
      ? prompt
      : `${offlineFixture}\n\nCon base estricta en el fixture anterior: ${prompt}`;
    const result = await generateText({
      model: atlasModel(),
      system: ATLAS_SYSTEM_PROMPT,
      messages: compactMessages([
        {
          id: `eval-${Date.now()}`,
          role: 'user',
          parts: [{ type: 'text', text: message }],
        },
      ]),
      tools: useTools ? createAtlasTools(cookie, runId) : undefined,
      stopWhen: stepCountIs(env.toolMaxSteps),
      providerOptions: googleProviderOptions,
    });
    const anyResult = result as unknown as {
      text: string;
      steps?: Array<{ toolCalls?: Array<{ toolName?: string }> }>;
    };
    results.push({
      prompt,
      text: anyResult.text,
      tools: (anyResult.steps || [])
        .flatMap((step) => step.toolCalls || [])
        .map((call) => call.toolName || 'unknown'),
    });
  }

  const md = buildMarkdown(started, useTools, results);
  const output = path.join(env.rootDir, 'docs', 'atlas_test_results.md');
  await fs.mkdir(path.dirname(output), { recursive: true });
  await fs.writeFile(output, md, 'utf8');
  console.log(output);
}

function buildMarkdown(
  started: Date,
  useTools: boolean,
  results: Array<{ prompt: string; text: string; tools: string[] }>,
): string {
  const lines = [
    '# Atlas prompt test results',
    '',
    `Fecha: ${started.toISOString()}`,
    `Modelo: ${env.model}`,
    `Backend tools: ${useTools ? 'live con ATLAS_TEST_COOKIE' : 'fixture offline'}`,
    '',
    '## Criterios',
    '',
    '- No inventar SHAP/PCA como evidencia runtime.',
    '- Explicar XGBoost, LightGBM, t+1, horas a critico y semaforo.',
    '- Usar resultados oficiales antes de slices.',
    '- Usar Python solo para graficos/calculos faltantes.',
    '- Reportar fallas de tools sin reintentos infinitos.',
    '',
    '## Resultados',
    '',
  ];

  for (const item of results) {
    lines.push(`### ${item.prompt}`, '');
    lines.push(`Tools usadas: ${item.tools.length ? item.tools.join(', ') : 'ninguna'}`, '');
    lines.push(item.text.trim(), '');
  }

  lines.push('## Ajustes aplicados', '');
  lines.push('- Prompt del sistema reforzado como results-first.');
  lines.push('- SHAP/PCA quedan bloqueados como evidencia runtime si no existe artefacto.');
  lines.push('- Python queda explicitamente como ultimo recurso.');
  lines.push('');
  return lines.join('\n');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
