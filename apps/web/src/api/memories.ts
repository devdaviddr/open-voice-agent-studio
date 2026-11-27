import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { MemoryOut } from '@/gen/api'
import { api, unwrap } from './client'

export type Memory = MemoryOut

export const memoriesQuery = (agentId: string) =>
  queryOptions({
    queryKey: ['memories', agentId],
    queryFn: () =>
      unwrap(api.GET('/v1/agents/{agent_id}/memories', { params: { path: { agent_id: agentId } } })),
  })

/** Memories grouped by end user, in first-seen order. */
export function byCaller(memories: Memory[]): [string, Memory[]][] {
  const groups = new Map<string, Memory[]>()
  for (const m of memories) groups.set(m.end_user_id, [...(groups.get(m.end_user_id) ?? []), m])
  return [...groups]
}

export function useDeleteMemory(agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (memoryId: string) =>
      unwrap(
        api.DELETE('/v1/agents/{agent_id}/memories/{memory_id}', {
          params: { path: { agent_id: agentId, memory_id: memoryId } },
        }),
      ),
    onSettled: () => qc.invalidateQueries({ queryKey: ['memories', agentId] }),
  })
}

export function useForgetCaller(agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (endUserId: string) =>
      unwrap(
        api.DELETE('/v1/agents/{agent_id}/memories', {
          params: { path: { agent_id: agentId }, query: { end_user_id: endUserId } },
        }),
      ),
    onSettled: () => qc.invalidateQueries({ queryKey: ['memories', agentId] }),
  })
}
