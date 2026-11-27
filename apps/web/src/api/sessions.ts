import { queryOptions } from '@tanstack/react-query'
import type { Issue } from '@/gen/api'
import { ApiError, api, unwrap } from './client'

export type SessionTarget = 'draft' | 'live' | number

export class NotRunnableError extends ApiError {
  readonly issues: Issue[]
  constructor(message: string, issues: Issue[]) {
    super(422, message)
    this.issues = issues
  }
}

export async function startSession(body: {
  agent_id: string
  target: SessionTarget
  end_user_id?: string | null
  variables?: Record<string, unknown>
}) {
  const { data, error, response } = await api.POST('/v1/sessions', { body: { variables: {}, ...body } })
  if (response.status === 422 && error && 'issues' in error) {
    const e = error as { detail: string; issues: Issue[] }
    throw new NotRunnableError(e.detail, e.issues)
  }
  if (!response.ok || !data) {
    const detail = (error as { detail?: string } | undefined)?.detail
    throw new ApiError(
      response.status,
      typeof detail === 'string' ? detail : `Could not start (${response.status})`,
    )
  }
  return data
}

export const sessionsQuery = (agentId?: string) =>
  queryOptions({
    queryKey: ['sessions', agentId ?? 'all'],
    queryFn: () =>
      unwrap(api.GET('/v1/sessions', { params: { query: agentId ? { agent_id: agentId } : {} } })),
  })

export const sessionQuery = (id: string) =>
  queryOptions({
    queryKey: ['sessions', 'detail', id],
    queryFn: () => unwrap(api.GET('/v1/sessions/{session_id}', { params: { path: { session_id: id } } })),
  })
