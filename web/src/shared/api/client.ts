import { API_BASE_URL } from '@/shared/config'
import { getInitData } from '@/shared/lib/max'
import { ApiError } from '@/shared/utils'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface RequestOptions extends Omit<RequestInit, 'body' | 'method'> {
  method?: HttpMethod
  body?: unknown
  /** Attach MAX `initData` as `Authorization: tma <initData>` for backend validation. */
  withInitData?: boolean
}

function resolveUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  // Empty base → same-origin (Vite proxy in dev / nginx in docker web).
  return `${API_BASE_URL}${normalized}`
}

async function parseBody(response: Response): Promise<unknown> {
  // FastAPI 204 still sends content-type: application/json with an empty body.
  // Calling response.json() on that throws and looks like a failed request.
  if (response.status === 204 || response.status === 205) {
    return undefined
  }

  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    const text = await response.text()
    if (!text) return undefined
    return JSON.parse(text) as unknown
  }

  const text = await response.text()
  return text || undefined
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, withInitData = false, headers, ...rest } = options

  const requestHeaders = new Headers(headers)

  if (body !== undefined && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  if (withInitData) {
    const initData = getInitData()
    if (initData) {
      requestHeaders.set('Authorization', `tma ${initData}`)
    }
  }

  const response = await fetch(resolveUrl(path), {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...rest,
  })

  const payload = await parseBody(response)

  if (!response.ok) {
    throw new ApiError(
      `Request failed: ${response.status} ${response.statusText}`,
      response.status,
      payload,
    )
  }

  return payload as T
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(path, { ...options, method: 'DELETE' }),
}
