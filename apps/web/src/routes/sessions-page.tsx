import { useSuspenseQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { MessagesSquare } from 'lucide-react'
import { cn } from 'cn'
import { sessionQuery, sessionsQuery } from '@/api/sessions'
import { PageHeader } from '@/components/layout/app-shell'
import { Badge } from '@/components/ui/badge'

const when = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const duration = (a: string, b?: string | null) => {
  if (!b) return 'open'
  const s = Math.round((new Date(b).getTime() - new Date(a).getTime()) / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}

export function SessionsPage() {
  const { data: sessions } = useSuspenseQuery(sessionsQuery())
  return (
    <>
      <PageHeader
        title="Sessions"
        description="Every conversation, with the version it ran and what happened."
      />
      {sessions.length === 0 ? (
        <div className="grid place-items-center px-8 py-24 text-center">
          <div className="flex max-w-sm flex-col items-center gap-3">
            <span className="bg-muted grid size-12 place-items-center rounded-xl">
              <MessagesSquare className="text-muted-foreground size-6" />
            </span>
            <h2 className="font-medium">No conversations yet</h2>
            <p className="text-muted-foreground text-sm">
              Open an agent and press Test to have the first one.
            </p>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto px-8 py-4">
          <table className="w-full text-sm">
            <thead className="text-muted-foreground text-left text-xs">
              <tr className="border-b">
                <th className="py-2 font-medium">Started</th>
                <th className="py-2 font-medium">Agent</th>
                <th className="py-2 font-medium">Ran</th>
                <th className="py-2 font-medium">Caller</th>
                <th className="py-2 text-right font-medium">Turns</th>
                <th className="py-2 text-right font-medium">Length</th>
                <th className="py-2 pl-4 font-medium">Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sessions.map((s) => (
                <tr key={s.id} className="hover:bg-muted/50">
                  <td className="py-2">
                    <Link
                      to="/sessions/$sessionId"
                      params={{ sessionId: s.id }}
                      className="underline-offset-2 hover:underline"
                    >
                      {when(s.started_at)}
                    </Link>
                  </td>
                  <td className="py-2">{s.agent_name}</td>
                  <td className="text-muted-foreground py-2">
                    {s.version_number ? `v${s.version_number}` : `draft rev ${s.draft_revision}`}
                  </td>
                  <td className="text-muted-foreground py-2 font-mono text-xs">{s.end_user_id ?? '—'}</td>
                  <td className="py-2 text-right tabular-nums">{s.turns}</td>
                  <td className="py-2 text-right tabular-nums">{duration(s.started_at, s.ended_at)}</td>
                  <td className="py-2 pl-4">
                    <Badge variant="outline" className="font-mono font-normal">
                      {s.outcome ?? 'open'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export function SessionDetailPage({ sessionId }: { sessionId: string }) {
  const { data: s } = useSuspenseQuery(sessionQuery(sessionId))
  const latencies = s.events
    .filter((e) => e.type === 'assistant_message' && e.payload.llm)
    .map((e) => (e.payload.llm as { total_ms: number }).total_ms)
    .sort((a, b) => a - b)
  const p50 = latencies.length ? latencies[Math.floor(latencies.length / 2)] : null
  return (
    <>
      <PageHeader
        title={s.agent_name}
        description={`${when(s.started_at)} · ${s.version_number ? `v${s.version_number}` : `draft rev ${s.draft_revision}`} · ${s.turns} turns${p50 ? ` · reply p50 ${p50} ms` : ''}`}
      >
        <Badge variant="outline" className="font-mono">
          {s.outcome ?? 'open'}
        </Badge>
      </PageHeader>
      <div className="grid gap-8 px-8 py-6 lg:grid-cols-[1fr_320px]">
        <ol className="flex flex-col gap-2">
          {s.events.map((e) => {
            const p = e.payload as Record<string, unknown>
            if (e.type === 'assistant_message' || e.type === 'user_message') {
              const agent = e.type === 'assistant_message'
              return (
                <li
                  key={e.seq}
                  className={cn(
                    'max-w-[75%] rounded-2xl px-3 py-2 text-sm',
                    agent ? 'bg-muted self-start' : 'bg-primary text-primary-foreground self-end',
                  )}
                >
                  {String(p.text)}
                  {agent && p.llm ? (
                    <div className="text-muted-foreground mt-1 text-[10px]">
                      {(p.llm as { total_ms: number }).total_ms} ms
                    </div>
                  ) : null}
                </li>
              )
            }
            return (
              <li key={e.seq} className="text-muted-foreground font-mono text-[11px]">
                {e.type} {JSON.stringify(p)}
              </li>
            )
          })}
        </ol>
        <aside className="flex flex-col gap-3">
          <h2 className="text-sm font-medium">Variables at the end</h2>
          <pre className="bg-muted/50 overflow-x-auto rounded-lg p-3 font-mono text-xs">
            {JSON.stringify(s.variables, null, 2)}
          </pre>
          <dl className="text-muted-foreground grid grid-cols-2 gap-1 text-xs">
            <dt>Caller ID</dt>
            <dd className="font-mono">{s.end_user_id ?? '—'}</dd>
            <dt>Channel</dt>
            <dd>{s.channel}</dd>
            <dt>Length</dt>
            <dd>{duration(s.started_at, s.ended_at)}</dd>
          </dl>
        </aside>
      </div>
    </>
  )
}
