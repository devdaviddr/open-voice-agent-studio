import type { QueryClient } from '@tanstack/react-query'
import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from '@tanstack/react-router'
import { agentQuery, agentsQuery, draftQuery } from '@/api/agents'
import { meQuery } from '@/api/auth'
import { llmQuery } from '@/api/llm'
import { sessionQuery, sessionsQuery } from '@/api/sessions'
import { AppShell } from '@/components/layout/app-shell'
import { AuthPage } from './routes/auth-page'
import { BuilderPage } from './builder/builder-page'
import { AgentsPage } from './routes/agents-page'
import { PlaygroundPage, ServicesPage, SettingsPage } from './routes/pages'
import { SessionDetailPage, SessionsPage } from './routes/sessions-page'

type Ctx = { queryClient: QueryClient }

const rootRoute = createRootRouteWithContext<Ctx>()({
  component: Outlet,
  errorComponent: ({ error, reset }) => (
    <main className="grid min-h-svh place-items-center p-6 text-center">
      <div className="flex max-w-md flex-col items-center gap-3">
        <h1 className="text-lg font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground text-sm">
          {error instanceof Error ? error.message : String(error)}
        </p>
        <button className="text-sm underline underline-offset-4" onClick={reset}>
          Try again
        </button>
      </div>
    </main>
  ),
})

type AuthSearch = { redirect?: string }
const validateAuthSearch = (s: Record<string, unknown>): AuthSearch =>
  typeof s.redirect === 'string' && s.redirect.startsWith('/') ? { redirect: s.redirect } : {}

async function redirectIfSignedIn({ context }: { context: Ctx }) {
  if (await context.queryClient.ensureQueryData(meQuery)) throw redirect({ to: '/agents' })
}

const signInRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sign-in',
  validateSearch: validateAuthSearch,
  beforeLoad: redirectIfSignedIn,
  component: function SignIn() {
    return <AuthPage mode="sign-in" redirect={signInRoute.useSearch().redirect} />
  },
})

const signUpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sign-up',
  beforeLoad: redirectIfSignedIn,
  component: () => <AuthPage mode="sign-up" />,
})

/** Everything behind sign-in. */
const authedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authed',
  beforeLoad: async ({ context, location }) => {
    const me = await context.queryClient.ensureQueryData(meQuery)
    if (!me) throw redirect({ to: '/sign-in', search: { redirect: location.href } })
  },
  component: Outlet,
})

/** Pages with the sidebar. The builder is full-screen and sits beside this layout. */
const appRoute = createRoute({ getParentRoute: () => authedRoute, id: 'app', component: AppShell })

const builderRoute = createRoute({
  getParentRoute: () => authedRoute,
  path: '/agents/$agentId',
  loader: ({ context, params }) =>
    Promise.all([
      context.queryClient.ensureQueryData(agentQuery(params.agentId)),
      context.queryClient.ensureQueryData(draftQuery(params.agentId)),
    ]),
  component: function Builder() {
    return <BuilderPage agentId={builderRoute.useParams().agentId} />
  },
})

const indexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/agents' })
  },
})
const agentsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/agents',
  loader: ({ context }) => context.queryClient.ensureQueryData(agentsQuery),
  component: AgentsPage,
})
const sessionsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/sessions',
  loader: ({ context }) => context.queryClient.ensureQueryData(sessionsQuery()),
  component: SessionsPage,
})
const sessionRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/sessions/$sessionId',
  loader: ({ context, params }) => context.queryClient.ensureQueryData(sessionQuery(params.sessionId)),
  component: function Session() {
    return <SessionDetailPage sessionId={sessionRoute.useParams().sessionId} />
  },
})
const playgroundRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/playground/tts',
  component: PlaygroundPage,
})
const servicesRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/services',
  component: ServicesPage,
})
const settingsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/settings',
  loader: ({ context }) => context.queryClient.ensureQueryData(llmQuery),
  component: SettingsPage,
})

const routeTree = rootRoute.addChildren([
  signInRoute,
  signUpRoute,
  authedRoute.addChildren([
    appRoute.addChildren([
      indexRoute,
      agentsRoute,
      sessionsRoute,
      sessionRoute,
      playgroundRoute,
      servicesRoute,
      settingsRoute,
    ]),
    builderRoute,
  ]),
])

export function makeRouter(queryClient: QueryClient) {
  return createRouter({ routeTree, context: { queryClient }, defaultPreload: 'intent' })
}

declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof makeRouter>
  }
}
