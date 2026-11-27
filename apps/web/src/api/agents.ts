import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { AgentCreate, AgentSummary, Issue } from '@/gen/api'
import type { AgentSpec } from '@/gen/agent-spec'
import { ApiError, api, unwrap } from './client'

export const agentsQuery = queryOptions({
  queryKey: ['agents'],
  queryFn: () => unwrap(api.GET('/v1/agents')),
})

export const agentQuery = (id: string) =>
  queryOptions({
    queryKey: ['agents', id],
    queryFn: () => unwrap(api.GET('/v1/agents/{agent_id}', { params: { path: { agent_id: id } } })),
  })

export type Draft = { revision: number; spec: AgentSpec }

export const draftQuery = (id: string) =>
  queryOptions({
    queryKey: ['agents', id, 'draft'],
    queryFn: async (): Promise<Draft> =>
      (await unwrap(api.GET('/v1/agents/{agent_id}/draft', { params: { path: { agent_id: id } } }))) as Draft,
    staleTime: Infinity, // the builder owns the draft once loaded
  })

export class DraftConflictError extends Error {
  readonly currentRevision: number
  constructor(currentRevision: number) {
    super('This agent was saved somewhere else since you opened it.')
    this.currentRevision = currentRevision
  }
}

export async function saveDraft(id: string, draft: Draft): Promise<Draft> {
  const { data, error, response } = await api.PUT('/v1/agents/{agent_id}/draft', {
    params: { path: { agent_id: id } },
    body: draft,
  })
  if (response.status === 409)
    throw new DraftConflictError((error as { current_revision: number }).current_revision)
  if (!response.ok) throw new ApiError(response.status, `Saving failed (${response.status})`)
  return data as Draft
}

export async function validateSpec(id: string, spec: AgentSpec, signal?: AbortSignal): Promise<Issue[]> {
  const res = await unwrap(
    api.POST('/v1/agents/{agent_id}/validate', { params: { path: { agent_id: id } }, body: spec, signal }),
  )
  return res.issues
}

function useInvalidateAgents() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['agents'] })
}

export function useCreateAgent() {
  const invalidate = useInvalidateAgents()
  return useMutation({
    mutationFn: (body: AgentCreate) => unwrap(api.POST('/v1/agents', { body })),
    onSuccess: invalidate,
  })
}

export function useRenameAgent() {
  const invalidate = useInvalidateAgents()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      unwrap(api.PATCH('/v1/agents/{agent_id}', { params: { path: { agent_id: id } }, body: { name } })),
    onSuccess: invalidate,
  })
}

export function useDuplicateAgent() {
  const invalidate = useInvalidateAgents()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/v1/agents/{agent_id}/duplicate', { params: { path: { agent_id: id } } })),
    onSuccess: invalidate,
  })
}

export function useDeleteAgent() {
  const invalidate = useInvalidateAgents()
  return useMutation({
    mutationFn: (agent: AgentSummary) =>
      unwrap(api.DELETE('/v1/agents/{agent_id}', { params: { path: { agent_id: agent.id } } })),
    onSuccess: invalidate,
  })
}
