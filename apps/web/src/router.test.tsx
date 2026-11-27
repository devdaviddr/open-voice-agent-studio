import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { ThemeProvider } from '@/components/layout/theme'
import { makeRouter } from './router'

function renderAt(path: string, me: object | null) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      me ? Response.json(me) : Response.json({ detail: 'Sign in to continue.' }, { status: 401 }),
    ),
  )
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = makeRouter(queryClient)
  router.update({ ...router.options, history: createMemoryHistory({ initialEntries: [path] }) })
  render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>,
  )
  return router
}

const me = {
  id: '1',
  email: 'ana@example.com',
  display_name: 'Ana',
  role: 'owner',
  workspace_id: 'w',
  workspace_name: 'My workspace',
}

describe('auth routing', () => {
  it('sends signed-out visitors to sign-in and remembers where they were going', async () => {
    const router = renderAt('/settings', null)
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
    expect(router.state.location.search).toEqual({ redirect: '/settings' })
  })

  it('shows the app shell to signed-in users', async () => {
    renderAt('/agents', me)
    expect(await screen.findByRole('heading', { name: 'Agents', exact: true })).toBeInTheDocument()
    expect(screen.getByText('Ana')).toBeInTheDocument()
  })

  it('redirects signed-in users away from sign-in', async () => {
    const router = renderAt('/sign-in', me)
    expect(await screen.findByRole('heading', { name: 'Agents', exact: true })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/agents')
  })
})
