import createClient from 'openapi-fetch'
import type { paths } from '@/gen/api'

/** Typed client for the OVAS API. Vite (and the production proxy) route /api to the API service. */
export const api = createClient<paths>({
  baseUrl: new URL('/api', window.location.origin).href,
  credentials: 'same-origin',
  fetch: (request) => globalThis.fetch(request),
})

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response }

/** Return data or throw an ApiError carrying the API's `detail` message. */
export async function unwrap<T>(promise: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await promise
  if (response.ok) return data as T
  throw new ApiError(response.status, detailOf(error) ?? `Request failed (${response.status})`)
}

function detailOf(error: unknown): string | undefined {
  if (!error || typeof error !== 'object' || !('detail' in error)) return undefined
  const detail = (error as { detail: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) {
    const field = detail[0].loc?.at(-1)
    return field ? `${field}: ${detail[0].msg}` : detail[0].msg
  }
  return undefined
}
