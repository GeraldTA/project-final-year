export const API_BASE_URL: string = (import.meta as any).env?.VITE_API_BASE_URL
  ? String((import.meta as any).env.VITE_API_BASE_URL).replace(/\/$/, '')
  : '';

export function apiUrl(path: string): string {
  if (!path) return API_BASE_URL;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(input), init);
}
