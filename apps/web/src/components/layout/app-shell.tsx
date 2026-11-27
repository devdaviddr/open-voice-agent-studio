import { Link, Outlet, useNavigate } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { Activity, AudioLines, Bot, LogOut, Settings, Volume2 } from 'lucide-react'
import { meQuery, useSignOut } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from './theme-toggle'

const nav = [
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/playground/tts', label: 'Voice playground', icon: Volume2 },
  { to: '/services', label: 'Services', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

export function AppShell() {
  const { data: me } = useSuspenseQuery(meQuery)
  const signOut = useSignOut()
  const navigate = useNavigate()
  return (
    <div className="flex min-h-svh">
      <aside className="bg-sidebar text-sidebar-foreground flex w-56 shrink-0 flex-col border-r">
        <div className="flex h-12 items-center gap-2 px-4 text-sm font-semibold">
          <AudioLines className="size-4" /> Voice Agent Studio
        </div>
        <nav className="flex flex-col gap-0.5 px-2 py-2" aria-label="Main">
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="hover:bg-sidebar-accent text-muted-foreground flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm"
              activeProps={{ className: 'bg-sidebar-accent text-sidebar-accent-foreground font-medium' }}
            >
              <Icon className="size-4" /> {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-2 border-t p-3">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{me?.display_name || me?.email}</div>
            <div className="text-muted-foreground truncate text-xs">
              {me?.workspace_name} · {me?.role}
            </div>
          </div>
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Sign out"
            onClick={() => signOut.mutate(undefined, { onSuccess: () => void navigate({ to: '/sign-in' }) })}
          >
            <LogOut className="size-4" />
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: React.ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b px-8 py-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>
      {children}
    </header>
  )
}
