import type { Envelope } from "@/types/api";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

function url(path: string, params?: Params) {
  const u = new URL(API_BASE.replace(/\/$/, "") + path);
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== null && v !== "") u.searchParams.set(k, String(v));
  }
  return u.toString();
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(input, init);
  } catch {
    throw new ApiError(
      "The Kisan Cold Link API is not reachable. Start the backend with ./dev.sh.",
      "network",
      0,
    );
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON */
  }
  if (!res.ok) {
    const err = (body as { error?: { code: string; message: string; details?: Record<string, unknown> } })?.error;
    throw new ApiError(err?.message ?? `Request failed (${res.status})`, err?.code ?? "http_error", res.status, err?.details);
  }
  return body as T;
}

export const api = {
  get<T>(path: string, params?: Params, headers?: HeadersInit) {
    return request<Envelope<T>>(url(path, params), { headers });
  },
  getRaw<T>(path: string, params?: Params) {
    return request<T>(url(path, params));
  },
  post<T>(path: string, body: unknown) {
    return request<Envelope<T>>(url(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  put<T>(path: string, body: unknown, headers?: HeadersInit) {
    return request<Envelope<T>>(url(path), {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
    });
  },
};
