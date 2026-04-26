const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";
console.log("[api] BASE =", BASE);

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let reqCounter = 0;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const id = ++reqCounter;
  const method = init?.method ?? "GET";
  const t0 = performance.now();
  console.log(`[api #${id}] → ${method} ${BASE}${path}`, init?.body ?? "");
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (e) {
    console.error(`[api #${id}] ✗ network ${method} ${path}`, e);
    throw e;
  }
  const dt = (performance.now() - t0).toFixed(1);
  console.log(`[api #${id}] ← ${resp.status} ${method} ${path} in ${dt}ms`);
  if (!resp.ok) {
    let message = resp.statusText;
    try {
      const body = await resp.json();
      message = body.detail ?? message;
      console.warn(`[api #${id}] error body`, body);
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, message);
  }
  if (resp.status === 204) return undefined as T;
  const json = (await resp.json()) as T;
  console.log(`[api #${id}] body`, json);
  return json;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
  upload: async <T>(path: string, file: File): Promise<T> => {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch(`${BASE}${path}`, {
      method: "POST",
      credentials: "include",
      body: fd,
    });
    if (!resp.ok) throw new ApiError(resp.status, resp.statusText);
    return (await resp.json()) as T;
  },
};
