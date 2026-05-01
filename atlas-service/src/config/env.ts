import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

const serviceDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const rootDir = path.resolve(serviceDir, '..');

dotenv.config({ path: path.join(rootDir, '.env') });
dotenv.config({ path: path.join(serviceDir, '.env') });

function intEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number.parseInt(raw, 10);
  return Number.isFinite(value) ? value : fallback;
}

export const env = {
  rootDir,
  serviceDir,
  port: intEnv('ATLAS_PORT', 8787),
  backendUrl: process.env.ATLAS_BACKEND_URL || 'http://127.0.0.1:8000',
  model: process.env.ATLAS_MODEL || 'gemini-3-flash-preview',
  toolMaxSteps: intEnv('ATLAS_TOOL_MAX_STEPS', 8),
  maxSliceRows: intEnv('ATLAS_MAX_SLICE_ROWS', 500),
  pythonTimeoutMs: intEnv('ATLAS_PYTHON_TIMEOUT_MS', 20000),
  googleApiKey: process.env.GOOGLE_API_KEY || process.env.GOOGLE_GENERATIVE_AI_API_KEY || '',
  runtimeDir: process.env.ATLAS_RUNTIME_DIR || path.join(rootDir, '.runtime', 'atlas'),
  pythonBin:
    process.env.ATLAS_PYTHON ||
    path.join(rootDir, '.venv-linux', 'bin', 'python'),
};

export function requireGoogleKey(): void {
  if (!env.googleApiKey) {
    throw new Error('GOOGLE_API_KEY is required for Atlas service');
  }
}
