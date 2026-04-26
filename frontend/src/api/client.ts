import { useAuthStore } from "../store/auth";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";
console.log("[api] BASE =", BASE);

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Tests inject a spy via setAuthRedirect; production uses window.location.assign.
type RedirectFn = (target: string) => void;
let redirectFn: RedirectFn | null = null;

export function setAuthRedirect(fn: RedirectFn | null): void {
  redirectFn = fn;
}

function defaultRedirect(target: string): void {
  if (typeof window !== "undefined") window.location.assign(target);
}

function handle401(path: string): void {
  // /auth/* routes own their own UX (AuthPage shows the form on /auth/me 401),
  // so we must not pre-empt them — and redirecting from /auth itself would loop.
  if (path.startsWith("/auth/")) return;
  if (typeof window !== "undefined" && window.location.pathname === "/auth") return;
  useAuthStore.getState().setUser(null);
  (redirectFn ?? defaultRedirect)("/auth");
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
    if (resp.status === 401) handle401(path);
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
