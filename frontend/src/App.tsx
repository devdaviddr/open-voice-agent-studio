import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type ServiceStatus = { status: string; version?: string }
type Health = { agent: ServiceStatus; audio: ServiceStatus }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function check() {
    setError(null)
    try {
      const res = await fetch('/api/health')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setHealth(await res.json())
    } catch (e) {
      setHealth(null)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    check()
  }, [])

  return (
    <main className="mx-auto flex min-h-svh max-w-2xl flex-col gap-6 p-8">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Open Voice Agent Studio</h1>
        <p className="text-muted-foreground">Build, run and test voice agents.</p>
      </header>
      <Card>
        <CardHeader>
          <CardTitle>Services</CardTitle>
          <CardDescription>Agent (Python) and audio (Rust) health.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {error && <p className="text-destructive text-sm">Agent unreachable: {error}</p>}
          {health &&
            (Object.entries(health) as [string, ServiceStatus][]).map(([name, s]) => (
              <div key={name} className="flex items-center justify-between">
                <span className="font-medium capitalize">{name}</span>
                <Badge variant={s.status === 'ok' ? 'default' : 'destructive'}>
                  {s.status}
                  {s.version ? ` · ${s.version}` : ''}
                </Badge>
              </div>
            ))}
          <Button variant="outline" className="self-start" onClick={check}>
            Refresh
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
