const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

export type Role = "VIEWER" | "ADMIN"

export type User = {
  id: number
  email: string
  first_name: string
  last_name: string
  role: Role
}

type AuthResponse = { access: string; user: User }

/** Field-level messages from DRF, e.g. { email: ["..."], password: ["..."] } */
export type FieldErrors = Record<string, string[]>

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fieldErrors: FieldErrors = {},
  ) {
    super(message)
  }
}

// The access token lives only in memory: it's gone on reload and is never
// written to localStorage, so injected scripts can't harvest it from storage.
// On reload we get a fresh one via the httpOnly refresh cookie.
let accessToken: string | null = null
let refreshInFlight: Promise<AuthResponse> | null = null

async function toApiError(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null)
  if (body && typeof body === "object") {
    if (typeof body.detail === "string") return new ApiError(res.status, body.detail)
    const { non_field_errors, ...fields } = body as FieldErrors
    const message = non_field_errors?.[0] ?? Object.values(fields)[0]?.[0] ?? "Request failed."
    return new ApiError(res.status, message, fields)
  }
  return new ApiError(res.status, res.status >= 500 ? "Server error. Please try again." : "Request failed.")
}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)

  let res: Response
  try {
    // credentials: "include" so the browser sends/stores the refresh cookie cross-port.
    res = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" })
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the API running?")
  }
  if (!res.ok) throw await toApiError(res)
  return (res.status === 204 ? undefined : await res.json()) as T
}

/** Exchange the refresh cookie for a new access token. Concurrent callers
 *  share one request, because each refresh token is single-use. */
export function refreshSession(): Promise<AuthResponse> {
  refreshInFlight ??= send<AuthResponse>("/auth/refresh", { method: "POST" })
    .then((data) => {
      accessToken = data.access
      return data
    })
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

/** Authenticated request; on 401 refreshes once and retries. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await send<T>(path, init)
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 401) throw err
    await refreshSession() // throws if the session is truly over
    return send<T>(path, init)
  }
}

export async function login(email: string, password: string): Promise<User> {
  const data = await send<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  accessToken = data.access
  return data.user
}

export async function register(email: string, password: string): Promise<User> {
  const data = await send<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  accessToken = data.access
  return data.user
}

export async function logout(): Promise<void> {
  try {
    await send<void>("/auth/logout", { method: "POST" })
  } finally {
    accessToken = null
  }
}
