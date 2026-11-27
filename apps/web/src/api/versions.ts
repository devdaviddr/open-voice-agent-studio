import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Issue } from '@/gen/api'
import type { AgentSpec } from '@/gen/agent-spec'
import { ApiError, api, unwrap } from './client'
import { agentQuery, draftQuery } from './agents'

const path = (agentId: string) => ({ params: { path: { agent_id: agentId } } })

export const versionsQuery = (agentId: string) =>
  queryOptions({
    queryKey: ['agents', agentId, 'versions'],
    queryFn: () => unwrap(api.GET('/v1/agents/{agent_id}/versions', path(agentId))),
  })

export const versionQuery = (agentId: string, number: number) =>
  queryOptions({
    queryKey: ['agents', agentId, 'versions', number],
    queryFn: async () => {
      const v = await unwrap(
        api.GET('/v1/agents/{agent_id}/versions/{number}', {
          params: { path: { agent_id: agentId, number } },
        }),
      )
      return { ...v, spec: v.spec as AgentSpec }
    },
    staleTime: Infinity, // versions never change
  })

/** `revision` is the saved draft revision, so the diff refreshes after each save. */
export const diffQuery = (agentId: string, from: string, to = 'draft', revision = 0) =>
  queryOptions({
    queryKey: ['agents', agentId, 'diff', from, to, revision],
    queryFn: () =>
      unwrap(
        api.GET('/v1/agents/{agent_id}/diff', {
          params: { path: { agent_id: agentId }, query: { from, to } },
        }),
      ),
    staleTime: 0,
  })

export class PublishRejectedError extends ApiError {
  readonly issues: Issue[]
  constructor(message: string, issues: Issue[]) {
    super(422, message)
    this.issues = issues
  }
}

export function usePublish(agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (message: string) => {
      const { data, error, response } = await api.POST('/v1/agents/{agent_id}/versions', {
        ...path(agentId),
        body: { message },
      })
      if (response.status === 422 && error && 'issues' in error) {
        const e = error as { detail: string; issues: Issue[] }
        throw new PublishRejectedError(e.detail, e.issues)
      }
      if (!response.ok || !data) throw new ApiError(response.status, `Publishing failed (${response.status})`)
      return data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: versionsQuery(agentId).queryKey })
      void qc.invalidateQueries({ queryKey: agentQuery(agentId).queryKey, exact: true })
      void qc.invalidateQueries({ queryKey: ['agents'], exact: true })
    },
  })
}

export function useSetLive(agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (version: number) =>
      unwrap(api.PUT('/v1/agents/{agent_id}/live', { ...path(agentId), body: { version } })),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: versionsQuery(agentId).queryKey })
      void qc.invalidateQueries({ queryKey: agentQuery(agentId).queryKey, exact: true })
    },
  })
}

export function useRestore(agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (number: number) =>
      unwrap(
        api.POST('/v1/agents/{agent_id}/versions/{number}/restore', {
          params: { path: { agent_id: agentId, number } },
        }),
      ),
    // The builder reloads when the draft query gets new data.
    onSuccess: (draft) =>
      qc.setQueryData(draftQuery(agentId).queryKey, {
        revision: draft.revision,
        spec: draft.spec as AgentSpec,
      }),
  })
}
