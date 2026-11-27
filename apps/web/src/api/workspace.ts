import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { WorkspaceSettingsPatch } from '@/gen/api'
import { api, unwrap } from './client'

export const healthQuery = queryOptions({
  queryKey: ['health'],
  queryFn: async (): Promise<Record<string, { status: string; version?: string }>> => {
    const res = await fetch('/api/health')
    if (!res.ok) throw new Error(`Health check failed (${res.status})`)
    return res.json()
  },
  refetchInterval: 15_000,
})

export const settingsQuery = queryOptions({
  queryKey: ['settings'],
  queryFn: () => unwrap(api.GET('/v1/settings')),
})

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: WorkspaceSettingsPatch) => unwrap(api.PATCH('/v1/settings', { body })),
    onSuccess: (data) => qc.setQueryData(settingsQuery.queryKey, data),
  })
}
