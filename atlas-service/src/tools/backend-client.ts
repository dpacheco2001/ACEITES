import { env } from '../config/env.js';

export type BackendClient = {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body: unknown): Promise<T>;
};

export function createBackendClient(cookieHeader: string | undefined): BackendClient {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    if (cookieHeader) headers.set('Cookie', cookieHeader);
    if (init.body) headers.set('Content-Type', 'application/json');

    const response = await fetch(`${env.backendUrl}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new Error(`Backend ${response.status} on ${path}: ${detail.slice(0, 500)}`);
    }
    return response.json() as Promise<T>;
  }

  return {
    get: (path) => request(path),
    post: (path, body) =>
      request(path, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  };
}
