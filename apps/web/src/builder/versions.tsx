import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Background, BackgroundVariant, ReactFlow, ReactFlowProvider } from '@xyflow/react'
import { Eye, GitCompare, History, RotateCcw, Rocket } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from 'cn'
import type { Change, VersionSummary } from '@/gen/api'
import {
  diffQuery,
  PublishRejectedError,
  usePublish,
  useRestore,
  useSetLive,
  versionQuery,
  versionsQuery,
} from '@/api/versions'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { specToFlow } from './convert'
import { edgeTypes, nodeTypes, ReadOnlyCanvas } from './flow-components'
import { useBuilder } from './store'

const when = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export function PublishButton({ agentId }: { agentId: string }) {
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const issues = useBuilder((s) => s.issues.length)
  const saveState = useBuilder((s) => s.saveState)
  const publish = usePublish(agentId)
  const blocked = issues > 0 || saveState === 'conflict'

  async function submit(e: FormEvent) {
    e.preventDefault()
    try {
      const v = await publish.mutateAsync(message.trim())
      toast.success(`Published v${v.number}. It is now live.`)
      setOpen(false)
      setMessage('')
    } catch (err) {
      toast.error(
        err instanceof PublishRejectedError
          ? `${err.message} (${err.issues.length} problems)`
          : (err as Error).message,
      )
    }
  }

  return (
    <>
      <Button
        size="sm"
        disabled={blocked}
        onClick={() => setOpen(true)}
        title={blocked ? 'Fix the problems before publishing' : undefined}
      >
        <Rocket className="size-3.5" /> Publish
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
            <DialogHeader>
              <DialogTitle>Publish a new version</DialogTitle>
              <DialogDescription>
                The current draft is frozen as the next version and goes live. You can keep editing the draft
                afterwards.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-2">
              <Label htmlFor="publish-message">What changed?</Label>
              <Input
                id="publish-message"
                required
                maxLength={500}
                placeholder="Offer alternatives when the slot is taken"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={publish.isPending || !message.trim() || saveState !== 'saved'}>
                {saveState !== 'saved' ? 'Saving draft…' : 'Publish and go live'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function VersionsButton({ agentId }: { agentId: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <History className="size-4" /> Versions
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-[420px] gap-0 sm:max-w-[420px]">
          <SheetHeader className="border-b">
            <SheetTitle>Versions</SheetTitle>
            <SheetDescription>
              Published versions are frozen. New conversations use the live one.
            </SheetDescription>
          </SheetHeader>
          <ScrollArea className="min-h-0 flex-1">
            <VersionList agentId={agentId} />
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </>
  )
}

function VersionList({ agentId }: { agentId: string }) {
  const { data: versions, isLoading } = useQuery(versionsQuery(agentId))
  const setLive = useSetLive(agentId)
  const restore = useRestore(agentId)
  const [diffFrom, setDiffFrom] = useState<number | null>(null)
  const [viewing, setViewing] = useState<number | null>(null)
  const [restoring, setRestoring] = useState<VersionSummary | null>(null)

  if (isLoading) return <p className="text-muted-foreground p-4 text-sm">Loading…</p>
  if (!versions?.length)
    return (
      <p className="text-muted-foreground p-4 text-sm">
        Nothing published yet. Publish the draft to create v1.
      </p>
    )

  return (
    <>
      <ol className="flex flex-col p-4">
        {versions.map((v, i) => (
          <li key={v.number} className="relative flex gap-3 pb-6">
            {i < versions.length - 1 && (
              <span className="bg-border absolute top-4 left-[5px] h-full w-px" aria-hidden />
            )}
            <span
              className={cn(
                'mt-1.5 size-[11px] shrink-0 rounded-full border-2',
                v.is_live ? 'border-primary bg-primary' : 'bg-background',
              )}
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">v{v.number}</span>
                {v.is_live && <Badge className="text-[10px]">live</Badge>}
                <span className="text-muted-foreground ml-auto text-xs">{when(v.created_at)}</span>
              </div>
              <p className="text-sm">{v.message}</p>
              <p className="text-muted-foreground text-xs">{v.author}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Button variant="outline" size="xs" onClick={() => setDiffFrom(v.number)}>
                  <GitCompare className="size-3" /> Compare with draft
                </Button>
                <Button variant="ghost" size="xs" onClick={() => setViewing(v.number)}>
                  <Eye className="size-3" /> View
                </Button>
                <Button variant="ghost" size="xs" onClick={() => setRestoring(v)}>
                  <RotateCcw className="size-3" /> Restore
                </Button>
                {!v.is_live && (
                  <Button
                    variant="ghost"
                    size="xs"
                    disabled={setLive.isPending}
                    onClick={() =>
                      setLive.mutate(v.number, {
                        onSuccess: () => toast.success(`v${v.number} is now live`),
                        onError: (e) => toast.error(e.message),
                      })
                    }
                  >
                    Make live
                  </Button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
      {diffFrom !== null && (
        <DiffDialog agentId={agentId} from={diffFrom} onClose={() => setDiffFrom(null)} />
      )}
      {viewing !== null && (
        <VersionView agentId={agentId} number={viewing} onClose={() => setViewing(null)} />
      )}
      <AlertDialog open={!!restoring} onOpenChange={(o) => !o && setRestoring(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore v{restoring?.number} into the draft?</AlertDialogTitle>
            <AlertDialogDescription>
              The draft is replaced with v{restoring?.number}. Published versions and the live version do not
              change. You can undo this by restoring another version.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                restoring &&
                restore.mutate(restoring.number, {
                  onSuccess: () => toast.success(`Draft restored from v${restoring.number}`),
                  onError: (e) => toast.error(e.message),
                  onSettled: () => setRestoring(null),
                })
              }
            >
              Restore
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

const CHANGE_STYLE: Record<Change['change'], string> = {
  added: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
  removed: 'bg-rose-500/15 text-rose-700 dark:text-rose-400',
  changed: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
}

const show = (v: unknown) =>
  v === null || v === undefined ? '—' : typeof v === 'string' ? v : JSON.stringify(v)

function DiffDialog({ agentId, from, onClose }: { agentId: string; from: number; onClose: () => void }) {
  const revision = useBuilder((s) => s.revision)
  const saved = useBuilder((s) => s.saveState === 'saved')
  // Compare against what is on the server only once local edits are saved.
  const { data, isLoading, error } = useQuery({
    ...diffQuery(agentId, String(from), 'draft', revision),
    enabled: saved,
  })
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[85svh] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>v{from} → draft</DialogTitle>
          <DialogDescription>
            What the draft changes compared with v{from}. Moving nodes around is not counted.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60svh]">
          {(isLoading || !saved) && (
            <p className="text-muted-foreground text-sm">
              {saved ? 'Comparing…' : 'Saving the draft first…'}
            </p>
          )}
          {error && <p className="text-destructive text-sm">{error.message}</p>}
          {data && data.changes.length === 0 && (
            <p className="text-muted-foreground text-sm">No differences.</p>
          )}
          <ul className="flex flex-col gap-3 pr-3">
            {data?.changes.map((c) => (
              <li key={`${c.kind}-${c.id}`} className="rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-[10px] font-medium uppercase',
                      CHANGE_STYLE[c.change],
                    )}
                  >
                    {c.change}
                  </span>
                  <span className="text-muted-foreground text-xs">{c.kind}</span>
                  <span className="text-sm font-medium">{c.label}</span>
                </div>
                {c.fields && c.fields.length > 0 && (
                  <dl className="mt-2 flex flex-col gap-2 text-xs">
                    {c.fields.map((f) => (
                      <div key={f.path}>
                        <dt className="text-muted-foreground font-mono">{f.path}</dt>
                        {f.lines ? (
                          <pre className="bg-muted/50 mt-1 overflow-x-auto rounded p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                            {f.lines.map((l, i) => (
                              <div
                                key={i}
                                className={cn(
                                  l.startsWith('+ ') &&
                                    'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300',
                                  l.startsWith('- ') &&
                                    'bg-rose-500/15 text-rose-800 line-through dark:text-rose-300',
                                )}
                              >
                                {l}
                              </div>
                            ))}
                          </pre>
                        ) : (
                          <dd className="font-mono">
                            <span className="text-rose-700 line-through dark:text-rose-400">
                              {show(f.before)}
                            </span>
                            {' → '}
                            <span className="text-emerald-700 dark:text-emerald-400">{show(f.after)}</span>
                          </dd>
                        )}
                      </div>
                    ))}
                  </dl>
                )}
              </li>
            ))}
          </ul>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}

function VersionView({ agentId, number, onClose }: { agentId: string; number: number; onClose: () => void }) {
  const { data } = useQuery(versionQuery(agentId, number))
  const flow = data ? specToFlow(data.spec) : null
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="h-[80svh] max-w-[min(1200px,95vw)] grid-rows-[auto_1fr] sm:max-w-[min(1200px,95vw)]">
        <DialogHeader>
          <DialogTitle>v{number} (read-only)</DialogTitle>
          <DialogDescription>{data?.message}</DialogDescription>
        </DialogHeader>
        <div className="min-h-0 rounded-lg border">
          {flow && (
            <ReadOnlyCanvas.Provider value>
              <ReactFlowProvider>
                <ReactFlow
                  nodes={flow.nodes}
                  edges={flow.edges}
                  nodeTypes={nodeTypes}
                  edgeTypes={edgeTypes}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  elementsSelectable={false}
                  fitView
                  minZoom={0.2}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
                </ReactFlow>
              </ReactFlowProvider>
            </ReadOnlyCanvas.Provider>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
