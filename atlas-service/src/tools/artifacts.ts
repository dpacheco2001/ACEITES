import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { env } from '../config/env.js';

export type ArtifactInfo = {
  id: string;
  filename: string;
  path: string;
  url: string;
  kind: 'json' | 'csv' | 'image' | 'text' | 'other';
};

export async function createRunId(): Promise<string> {
  const id = randomUUID();
  await fs.mkdir(runDir(id), { recursive: true });
  return id;
}

export function runDir(runId: string): string {
  return path.join(env.runtimeDir, 'runs', safeName(runId));
}

export function safeName(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 120);
}

export function artifactUrl(runId: string, filename: string): string {
  return `/artifacts/${safeName(runId)}/${safeName(filename)}`;
}

export async function writeArtifact(
  runId: string,
  filename: string,
  content: string,
): Promise<ArtifactInfo> {
  const safe = safeName(filename);
  const fullPath = path.join(runDir(runId), safe);
  await fs.mkdir(path.dirname(fullPath), { recursive: true });
  await fs.writeFile(fullPath, content, 'utf8');
  return artifactInfo(runId, safe, fullPath);
}

export async function listArtifacts(runId: string): Promise<ArtifactInfo[]> {
  try {
    const names = await fs.readdir(runDir(runId));
    return Promise.all(
      names.map((name) => artifactInfo(runId, name, path.join(runDir(runId), name))),
    );
  } catch {
    return [];
  }
}

export async function artifactInfo(
  runId: string,
  filename: string,
  fullPath: string,
): Promise<ArtifactInfo> {
  return {
    id: filename,
    filename,
    path: fullPath,
    url: artifactUrl(runId, filename),
    kind: kindFor(filename),
  };
}

function kindFor(filename: string): ArtifactInfo['kind'] {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.csv')) return 'csv';
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
    return 'image';
  }
  if (lower.endsWith('.txt') || lower.endsWith('.md')) return 'text';
  return 'other';
}
