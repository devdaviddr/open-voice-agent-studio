import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Me, SignIn, SignUp } from '@/gen/api'
import { ApiError, api, unwrap } from './client'

export const meQuery = queryOptions({
  queryKey: ['me'],
  queryFn: async (): Promise<Me | null> => {
    try {
      return await unwrap(api.GET('/v1/me'))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return null
      throw e
    }
  },
  staleTime: 60_000,
})

export function useSignIn() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SignIn) => unwrap(api.POST('/v1/auth/login', { body })),
    onSuccess: (me) => qc.setQueryData(meQuery.queryKey, me),
  })
}

export function useSignUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SignUp) => unwrap(api.POST('/v1/auth/signup', { body })),
    onSuccess: (me) => qc.setQueryData(meQuery.queryKey, me),
  })
}

export function useSignOut() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/v1/auth/logout')),
    onSuccess: () => {
      qc.clear()
      qc.setQueryData(meQuery.queryKey, null)
    },
  })
}
