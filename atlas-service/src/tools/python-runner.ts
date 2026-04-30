import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { env } from '../config/env.js';
import { artifactInfo, listArtifacts, runDir, safeName } from './artifacts.js';

export type PythonRunResult = {
  ok: boolean;
  stdout: string;
  stderr: string;
  exitCode: number | null;
  artifacts: Awaited<ReturnType<typeof listArtifacts>>;
};

export async function runPython(
  runId: string,
  code: string,
  timeoutMs = env.pythonTimeoutMs,
): Promise<PythonRunResult> {
  const dir = runDir(runId);
  await fs.mkdir(dir, { recursive: true });
  const before = new Set((await listArtifacts(runId)).map((item) => item.filename));
  const script = path.join(dir, `analysis-${Date.now()}.py`);
  await fs.writeFile(script, buildScript(code), 'utf8');

  const python = await resolvePython();
  const child = spawn(python, [script], {
    cwd: dir,
    env: {
      PATH: process.env.PATH || '',
      MPLBACKEND: 'Agg',
      PYTHONNOUSERSITE: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => {
    stdout += chunk.toString();
  });
  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });

  const exitCode = await new Promise<number | null>((resolve) => {
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      stderr += `\nTimeout after ${timeoutMs}ms`;
    }, timeoutMs);
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });

  const artifacts = (await listArtifacts(runId)).filter((item) => !before.has(item.filename));
  await fs.writeFile(
    path.join(dir, safeName(`python-${Date.now()}-result.json`)),
    JSON.stringify({ stdout, stderr, exitCode }, null, 2),
    'utf8',
  );
  return {
    ok: exitCode === 0,
    stdout: stdout.slice(-4000),
    stderr: stderr.slice(-4000),
    exitCode,
    artifacts: await Promise.all(
      artifacts.map((item) => artifactInfo(runId, item.filename, item.path)),
    ),
  };
}

async function resolvePython(): Promise<string> {
  try {
    await fs.access(env.pythonBin);
    return env.pythonBin;
  } catch {
    return 'python3';
  }
}

function buildScript(code: string): string {
  return [
    'import os',
    'os.environ.setdefault("MPLBACKEND", "Agg")',
    'import matplotlib',
    'matplotlib.use("Agg")',
    code,
    '',
  ].join('\n');
}
