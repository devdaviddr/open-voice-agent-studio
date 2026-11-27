import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { KnowledgeSourceOut } from '@/gen/api'
import { api, unwrap } from './client'

export type KnowledgeSource = KnowledgeSourceOut

/** Accepted uploads (MVP FR-15); mirrors ovas_api.knowledge.parsing.ACCEPTED. */
export const KNOWLEDGE_ACCEPT = '.md,.markdown,.txt,.pdf'
export const KNOWLEDGE_MAX_BYTES = 20 * 1024 * 1024

const busy = (sources?: KnowledgeSource[]) =>
  !!sources?.some((s) => s.status === 'pending' || s.status === 'indexing')

export const knowledgeQuery = queryOptions({
  queryKey: ['knowledge'],
  queryFn: () => unwrap(api.GET('/v1/knowledge')),
  // Poll while anything is still being indexed.
  refetchInterval: (q) => (busy(q.state.data) ? 1500 : false),
})

/** Upload one document as multipart form data; indexing then runs in the background. */
export function uploadKnowledge(file: File) {
  const form = new FormData()
  form.append('file', file, file.name)
  return unwrap(api.POST('/v1/knowledge', { body: { file: file.name }, bodySerializer: () => form }))
}

export function useUploadKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: uploadKnowledge,
    onSettled: () => qc.invalidateQueries({ queryKey: knowledgeQuery.queryKey }),
  })
}

export function useDeleteKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/v1/knowledge/{source_id}', { params: { path: { source_id: id } } })),
    onSettled: () => qc.invalidateQueries({ queryKey: knowledgeQuery.queryKey }),
  })
}

export function useReindexKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/v1/knowledge/{source_id}/reindex', { params: { path: { source_id: id } } })),
    onSettled: () => qc.invalidateQueries({ queryKey: knowledgeQuery.queryKey }),
  })
}
