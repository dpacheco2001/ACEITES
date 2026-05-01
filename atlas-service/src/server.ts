import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import type { IncomingMessage, ServerResponse } from 'node:http';
import type { UIMessage } from 'ai';
import { stepCountIs, streamText } from 'ai';
import { compactMessages } from './agent/compaction.js';
import { env } from './config/env.js';
import { atlasModel, googleProviderOptions } from './config/providers.js';
import { ATLAS_SYSTEM_PROMPT } from './prompts/system.js';
import { createRunId, runDir, safeName } from './tools/artifacts.js';
import { createAtlasTools } from './tools/index.js';

const server = http.createServer(async (req, res) => {
  try {
    applyCors(res);
    if (req.method === 'OPTIONS') return sendJson(res, 204, {});
    if (req.method === 'GET' && req.url === '/health') return health(res);
    if (req.method === 'POST' && req.url === '/chat') return chat(req, res);
    if ((req.method === 'GET' || req.method === 'HEAD') && req.url?.startsWith('/artifacts/')) {
      return artifact(req, res);
    }
    return sendJson(res, 404, { error: 'Not found' });
  } catch (error) {
    return sendJson(res, 500, {
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

server.listen(env.port, '0.0.0.0', () => {
  console.log(`[atlas] listening on http://127.0.0.1:${env.port}`);
});

async function chat(req: IncomingMessage, res: ServerResponse) {
  const body = await readJson<{ messages?: UIMessage[] }>(req);
  const runId = await createRunId();
  const result = streamText({
    model: atlasModel(),
    system: ATLAS_SYSTEM_PROMPT,
    messages: compactMessages(body.messages || []),
    tools: createAtlasTools(req.headers.cookie, runId),
    stopWhen: stepCountIs(env.toolMaxSteps),
    providerOptions: googleProviderOptions,
  });
  const response = result.toUIMessageStreamResponse({
    messageMetadata: () => ({ runId }),
  });
  await writeWebResponse(res, response);
}

function health(res: ServerResponse) {
  return sendJson(res, 200, {
    status: 'ok',
    model: env.model,
    google_api_key_present: Boolean(env.googleApiKey),
    backend_url: env.backendUrl,
    runtime_dir: env.runtimeDir,
  });
}

function artifact(req: IncomingMessage, res: ServerResponse) {
  const parts = new URL(req.url || '/', 'http://atlas.local').pathname.split('/');
  const runId = safeName(parts[2] || '');
  const filename = safeName(parts.slice(3).join('/') || '');
  const fullPath = path.join(runDir(runId), filename);
  if (!filename || !fs.existsSync(fullPath)) {
    return sendJson(res, 404, { error: 'Artifact not found' });
  }
  res.writeHead(200, { 'Content-Type': contentType(filename) });
  if (req.method === 'HEAD') return res.end();
  fs.createReadStream(fullPath).pipe(res);
}

async function readJson<T>(req: IncomingMessage): Promise<T> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? (JSON.parse(raw) as T) : ({} as T);
}

async function writeWebResponse(res: ServerResponse, response: Response) {
  res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
  if (!response.body) return res.end();
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    res.write(Buffer.from(value));
  }
  res.end();
}

function sendJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(status === 204 ? undefined : JSON.stringify(body));
}

function applyCors(res: ServerResponse) {
  res.setHeader('Access-Control-Allow-Origin', 'http://127.0.0.1:5173');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
}

function contentType(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.csv')) return 'text/csv; charset=utf-8';
  if (lower.endsWith('.json')) return 'application/json; charset=utf-8';
  return 'application/octet-stream';
}
