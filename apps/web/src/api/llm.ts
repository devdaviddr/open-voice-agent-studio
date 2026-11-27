import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { LlmConfigUpdate } from '@/gen/api'
import { api, unwrap } from './client'

export const llmQuery = queryOptions({
  queryKey: ['settings', 'llm'],
  queryFn: () => unwrap(api.GET('/v1/settings/llm')),
})

export function useUpdateLlm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LlmConfigUpdate) => unwrap(api.PUT('/v1/settings/llm', { body })),
    onSuccess: (data) => qc.setQueryData(llmQuery.queryKey, data),
  })
}

export function useTestLlm() {
  return useMutation({ mutationFn: () => unwrap(api.POST('/v1/settings/llm/test')) })
}
