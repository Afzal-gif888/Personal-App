/**
 * HTTP client for the FastAPI backend (`/api/v1`).
 *
 * - Adds the bearer access token, and on a 401 refreshes it once with the refresh token.
 * - Turns the backend's `{error: {code, message, details}}` envelope into an `ApiError`.
 * - In development Vite proxies `/api` to the backend, so the base URL is empty by default;
 *   set `VITE_API_URL` to call a backend on another origin.
 */

const BASE_URL = `${(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')}/api/v1`;

const TOKEN_KEYS = {
  ACCESS: 'agentos_access_token',
  REFRESH: 'agentos_refresh_token',
};

export interface Tokens {
  accessToken: string;
  refreshToken: string;
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export const tokenStore = {
  get access() {
    return read(TOKEN_KEYS.ACCESS);
  },
  get refresh() {
    return read(TOKEN_KEYS.REFRESH);
  },
  set(tokens: Tokens) {
    try {
      localStorage.setItem(TOKEN_KEYS.ACCESS, tokens.accessToken);
      localStorage.setItem(TOKEN_KEYS.REFRESH, tokens.refreshToken);
    } catch {
      // storage unavailable: the session lasts until the page is reloaded
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEYS.ACCESS);
      localStorage.removeItem(TOKEN_KEYS.REFRESH);
    } catch {
      // ignore
    }
  },
};

/** Called when the session can't be refreshed; the auth store signs the user out. */
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** A user-facing message for any thrown error. */
export function errorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (err instanceof ApiError) {
    // Validation errors carry per-field details; the first one is usually the most useful.
    if (Array.isArray(err.details) && err.details.length > 0) {
      const first = err.details[0] as { field?: string; message?: string };
      if (first?.message) return first.field ? `${first.field}: ${first.message}` : first.message;
    }
    return err.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

type Query = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  query?: Query;
  body?: unknown;
  /** Skip the bearer token and 401 handling (login, register, refresh). */
  anonymous?: boolean;
  /** Set on the single retry after a token refresh. */
  retried?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const url = `${BASE_URL}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json();
    const e = data?.error;
    if (e?.message) return new ApiError(res.status, e.code ?? 'ERROR', e.message, e.details);
  } catch {
    // not JSON
  }
  return new ApiError(res.status, 'HTTP_ERROR', `Request failed (${res.status})`);
}

// One refresh at a time: concurrent 401s all wait for the same attempt.
let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refreshToken = tokenStore.refresh;
  if (!refreshToken) return false;
  refreshing ??= (async () => {
    try {
      const res = await fetch(buildUrl('/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      if (!res.ok) return false;
      tokenStore.set(await res.json());
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function send(method: string, path: string, opts: RequestOptions = {}): Promise<Response> {
  const isForm = opts.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (opts.body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  if (!opts.anonymous && tokenStore.access) headers.Authorization = `Bearer ${tokenStore.access}`;

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body: opts.body === undefined ? undefined : isForm ? (opts.body as FormData) : JSON.stringify(opts.body),
    });
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', "Can't reach the server. Check that the backend is running.");
  }

  if (res.status === 401 && !opts.anonymous) {
    if (!opts.retried && (await refreshTokens())) return send(method, path, { ...opts, retried: true });
    tokenStore.clear();
    onUnauthorized();
  }
  return res;
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, opts);
  if (!res.ok) {
    throw await parseError(res);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

const MAX_PAGE_SIZE = 100;
const MAX_PAGES = 20;

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown, opts: Omit<RequestOptions, 'body'> = {}) =>
    request<T>('POST', path, { ...opts, body: body ?? {} }),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, { body }),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, { body }),
  delete: (path: string) => request<void>('DELETE', path),
  upload: <T>(path: string, form: FormData) => request<T>('POST', path, { body: form }),

  /** Every item of a paginated list endpoint (capped at MAX_PAGES pages). */
  async getAll<T>(path: string, query: Query = {}): Promise<T[]> {
    const items: T[] = [];
    for (let page = 1; page <= MAX_PAGES; page++) {
      const res = await request<Page<T>>('GET', path, { query: { ...query, page, page_size: MAX_PAGE_SIZE } });
      items.push(...res.items);
      if (items.length >= res.total || res.items.length === 0) break;
    }
    return items;
  },

  /** An authenticated file download, as a Blob. */
  async blob(path: string): Promise<Blob> {
    const res = await send('GET', path);
    if (!res.ok) throw await parseError(res);
    return res.blob();
  },
};
