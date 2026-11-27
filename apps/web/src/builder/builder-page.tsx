import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import { Link } from '@tanstack/react-router'
import { useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft, Check, CircleAlert, CloudOff, Loader2, MessageSquare, Redo2, Undo2 } from 'lucide-react'
import { useStore } from 'zustand'
import { agentQuery, draftQuery, DraftConflictError, saveDraft, validateSpec } from '@/api/agents'
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
import { Kbd } from '@/components/ui/kbd'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { flowToSpec, type NodeKind } from './convert'
import { edgeTypes, KINDS, nodeTypes } from './flow-components'
import { Inspector } from './inspector'
import { TestConsole } from './console'
import { PublishButton, VersionsButton } from './versions'
import { contentKey, isValidConnection, redo, undo, useBuilder } from './store'

const PALETTE: NodeKind[] = ['agent_step', 'extract', 'router', 'end', 'note', 'start']
const SAVE_DELAY = 1000
const VALIDATE_DELAY = 400

export function BuilderPage({ agentId }: { agentId: string }) {
  return (
    <ReactFlowProvider>
      <Builder agentId={agentId} />
    </ReactFlowProvider>
  )
}

function Builder({ agentId }: { agentId: string }) {
  const { data: agent } = useSuspenseQuery(agentQuery(agentId))
  const { data: draft } = useSuspenseQuery(draftQuery(agentId))
  const loadedFor = useBuilder((s) => s.agentId)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    useBuilder.getState().load(agentId, draft.revision, draft.spec)
  }, [agentId, draft])

  useAutosave(agentId)
  useLiveValidation(agentId)
  useShortcuts()

  if (loadedFor !== agentId) return null
  return (
    <div className="bg-background flex h-svh flex-col">
      <TopBar
        agentId={agentId}
        name={agent.name}
        liveVersion={agent.live_version}
        testing={testing}
        onToggleTest={() => setTesting((t) => !t)}
      />
      <div className="flex min-h-0 flex-1">
        <Palette />
        <main className="min-w-0 flex-1">
          <Canvas />
        </main>
        {testing ? (
          <aside className="w-[420px] shrink-0 border-l" aria-label="Test console">
            <TestConsole agentId={agentId} onClose={() => setTesting(false)} />
          </aside>
        ) : (
          <aside className="w-80 shrink-0 border-l" aria-label="Inspector">
            <ScrollArea className="h-full">
              <div className="p-4">
                <Inspector />
              </div>
            </ScrollArea>
          </aside>
        )}
      </div>
      <ConflictDialog agentId={agentId} />
    </div>
  )
}

function Canvas() {
  const nodes = useBuilder((s) => s.nodes)
  const edges = useBuilder((s) => s.edges)
  const { onNodesChange, onEdgesChange, onConnect, addNode } = useBuilder.getState()
  const { screenToFlowPosition } = useReactFlow()

  const onDrop = useCallback(
    (e: DragEvent) => {
      const kind = e.dataTransfer.getData('application/ovas-node') as NodeKind
      if (!kind) return
      e.preventDefault()
      addNode(kind, screenToFlowPosition({ x: e.clientX - 120, y: e.clientY - 30 }))
    },
    [addNode, screenToFlowPosition],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      isValidConnection={(c) => isValidConnection(useBuilder.getState().nodes, c)}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
      }}
      onDrop={onDrop}
      deleteKeyCode={['Backspace', 'Delete']}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.2}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap pannable zoomable position="bottom-right" className="!rounded-lg !border" />
    </ReactFlow>
  )
}

function Palette() {
  const hasStart = useBuilder((s) => s.nodes.some((n) => n.type === 'start'))
  const { addNode } = useBuilder.getState()
  const { screenToFlowPosition } = useReactFlow()
  const addAtCentre = (kind: NodeKind) => {
    const pane = document.querySelector('.react-flow')?.getBoundingClientRect()
    const centre = pane
      ? { x: pane.x + pane.width / 2 - 120, y: pane.y + pane.height / 2 - 40 }
      : { x: 400, y: 300 }
    addNode(kind, screenToFlowPosition(centre))
  }
  return (
    <aside className="w-56 shrink-0 border-r" aria-label="Node palette">
      <ScrollArea className="h-full">
        <div className="p-3">
          <div className="text-muted-foreground mb-2 px-1 text-[10px] font-medium tracking-wide uppercase">
            Add a node
          </div>
          {PALETTE.filter((k) => k !== 'start' || !hasStart).map((kind) => {
            const k = KINDS[kind]
            return (
              <button
                key={kind}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('application/ovas-node', kind)
                  e.dataTransfer.effectAllowed = 'move'
                }}
                onClick={() => addAtCentre(kind)}
                className="hover:bg-muted focus-visible:ring-ring flex w-full cursor-grab items-start gap-2.5 rounded-md p-2 text-left outline-none focus-visible:ring-2"
              >
                <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-md ${k.tint}`}>
                  <k.icon className="size-3.5" />
                </span>
                <span>
                  <span className="block text-sm">{k.name}</span>
                  <span className="text-muted-foreground block text-[11px] leading-snug">{k.hint}</span>
                </span>
              </button>
            )
          })}
          <div className="text-muted-foreground mt-6 flex flex-col gap-1.5 px-1 text-[11px]">
            <span className="text-[10px] font-medium tracking-wide uppercase">Shortcuts</span>
            {[
              ['⌘Z / ⇧⌘Z', 'Undo / redo'],
              ['⌘C / ⌘V', 'Copy / paste'],
              ['⌘D', 'Duplicate'],
              ['⌫', 'Delete'],
              ['⇧1', 'Fit view'],
            ].map(([keys, label]) => (
              <span key={label} className="flex items-center justify-between gap-2">
                {label} <Kbd>{keys}</Kbd>
              </span>
            ))}
          </div>
        </div>
      </ScrollArea>
    </aside>
  )
}

function TopBar({
  agentId,
  name,
  liveVersion,
  testing,
  onToggleTest,
}: {
  agentId: string
  name: string
  liveVersion: number | null | undefined
  testing: boolean
  onToggleTest: () => void
}) {
  const revision = useBuilder((s) => s.revision)
  const issues = useBuilder((s) => s.issues)
  const canUndo = useStore(useBuilder.temporal, (s) => s.pastStates.length > 0)
  const canRedo = useStore(useBuilder.temporal, (s) => s.futureStates.length > 0)
  const select = useBuilder((s) => s.select)
  const { fitView } = useReactFlow()
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b px-3">
      <Button
        variant="ghost"
        size="icon-sm"
        nativeButton={false}
        render={<Link to="/agents" aria-label="Back to agents" />}
      >
        <ArrowLeft className="size-4" />
      </Button>
      <span className="text-sm font-medium">{name}</span>
      <Badge variant="outline" className="font-normal">
        Draft · rev {revision}
      </Badge>
      <span className="text-muted-foreground text-xs">
        {liveVersion ? `live is v${liveVersion}` : 'not published'}
      </span>
      <SaveIndicator />
      <div className="ml-auto flex items-center gap-1">
        <Button variant="ghost" size="icon-sm" aria-label="Undo" disabled={!canUndo} onClick={undo}>
          <Undo2 className="size-4" />
        </Button>
        <Button variant="ghost" size="icon-sm" aria-label="Redo" disabled={!canRedo} onClick={redo}>
          <Redo2 className="size-4" />
        </Button>
        {issues.length > 0 ? (
          <Popover>
            <PopoverTrigger
              render={<Button variant="ghost" size="sm" className="text-destructive gap-1.5" />}
            >
              <CircleAlert className="size-4" /> {issues.length}{' '}
              {issues.length === 1 ? 'problem' : 'problems'}
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80 p-1">
              {issues.map((i, n) => (
                <button
                  key={n}
                  className="hover:bg-muted w-full rounded-md p-2 text-left text-xs"
                  onClick={() => {
                    select({ nodes: i.node_id ? [i.node_id] : [], edges: i.edge_id ? [i.edge_id] : [] })
                    const ids = i.node_id ? [{ id: i.node_id }] : []
                    if (ids.length) void fitView({ nodes: ids, duration: 300, maxZoom: 1.2 })
                  }}
                >
                  {i.message}
                </button>
              ))}
            </PopoverContent>
          </Popover>
        ) : (
          <span className="flex items-center gap-1 px-2 text-xs text-emerald-600 dark:text-emerald-400">
            <Check className="size-3.5" /> Valid
          </span>
        )}
        <VersionsButton agentId={agentId} />
        <Button
          variant={testing ? 'secondary' : 'outline'}
          size="sm"
          onClick={onToggleTest}
          aria-pressed={testing}
        >
          <MessageSquare className="size-3.5" /> Test
        </Button>
        <PublishButton agentId={agentId} />
      </div>
    </header>
  )
}

function SaveIndicator() {
  const state = useBuilder((s) => s.saveState)
  const label = {
    saved: 'Saved',
    pending: 'Unsaved changes',
    saving: 'Saving…',
    conflict: 'Not saved: conflict',
    error: 'Not saved: retrying',
  }[state]
  return (
    <span className="text-muted-foreground flex items-center gap-1 text-xs" role="status" aria-live="polite">
      {state === 'saving' && <Loader2 className="size-3 animate-spin" />}
      {(state === 'error' || state === 'conflict') && <CloudOff className="text-destructive size-3" />}
      {label}
    </span>
  )
}

function ConflictDialog({ agentId }: { agentId: string }) {
  const state = useBuilder((s) => s.saveState)
  const conflictRevision = useBuilder((s) => s.conflictRevision)
  const qc = useQueryClient()
  const [busy, setBusy] = useState(false)
  return (
    <AlertDialog open={state === 'conflict'}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>This agent changed somewhere else</AlertDialogTitle>
          <AlertDialogDescription>
            Someone saved this agent (maybe you, in another tab) after you opened it. Reload to get their
            version, or keep yours and overwrite theirs.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel
            disabled={busy}
            onClick={() => void qc.invalidateQueries({ queryKey: draftQuery(agentId).queryKey })}
          >
            Reload their version
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              const s = useBuilder.getState()
              try {
                const saved = await saveDraft(agentId, {
                  revision: conflictRevision ?? s.revision,
                  spec: flowToSpec(s.nodes, s.edges, s.meta),
                })
                s.markSaved(saved.revision)
              } catch {
                s.setSaveState('error')
              } finally {
                setBusy(false)
              }
            }}
          >
            Overwrite with mine
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

/** Save the draft 1 s after the last edit; one save in flight at a time (MVP FR-7). */
function useAutosave(agentId: string) {
  const saved = useRef<string>('')
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    let inFlight = false
    const flush = async () => {
      const s = useBuilder.getState()
      if (s.agentId !== agentId || s.saveState === 'conflict') return
      const key = contentKey(s)
      if (key === saved.current) return s.setSaveState('saved')
      if (inFlight) return schedule()
      inFlight = true
      s.setSaveState('saving')
      try {
        const res = await saveDraft(agentId, {
          revision: s.revision,
          spec: flowToSpec(s.nodes, s.edges, s.meta),
        })
        saved.current = key
        useBuilder.getState().markSaved(res.revision)
        if (contentKey(useBuilder.getState()) !== key) schedule()
      } catch (e) {
        if (e instanceof DraftConflictError) useBuilder.getState().setSaveState('conflict', e.currentRevision)
        else {
          useBuilder.getState().setSaveState('error')
          timer = setTimeout(flush, 5000)
        }
      } finally {
        inFlight = false
      }
    }
    const schedule = () => {
      clearTimeout(timer)
      timer = setTimeout(flush, SAVE_DELAY)
    }
    saved.current = ''
    const unsub = useBuilder.subscribe((s, prev) => {
      if (s.agentId !== agentId) return
      if (s.loadCount !== prev.loadCount) {
        saved.current = contentKey(s)
        return
      }
      if (s.nodes === prev.nodes && s.edges === prev.edges && s.meta === prev.meta) return
      if (contentKey(s) === saved.current) return
      if (s.saveState !== 'conflict') s.setSaveState('pending')
      schedule()
    })
    saved.current = contentKey(useBuilder.getState())
    const beforeUnload = (e: BeforeUnloadEvent) => {
      if (useBuilder.getState().saveState !== 'saved') e.preventDefault()
    }
    window.addEventListener('beforeunload', beforeUnload)
    return () => {
      unsub()
      clearTimeout(timer)
      window.removeEventListener('beforeunload', beforeUnload)
      void flush()
    }
  }, [agentId])
}

/** Ask the API to validate the current graph shortly after each change (MVP FR-8). */
function useLiveValidation(agentId: string) {
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    let controller: AbortController | undefined
    let last = ''
    const run = () => {
      const s = useBuilder.getState()
      const key = contentKey(s)
      if (key === last) return
      last = key
      controller?.abort()
      controller = new AbortController()
      validateSpec(agentId, flowToSpec(s.nodes, s.edges, s.meta), controller.signal)
        .then((issues) => useBuilder.getState().setIssues(issues))
        .catch(() => {})
    }
    const unsub = useBuilder.subscribe((s, prev) => {
      if (s.nodes === prev.nodes && s.edges === prev.edges && s.meta === prev.meta) return
      clearTimeout(timer)
      timer = setTimeout(run, VALIDATE_DELAY)
    })
    timer = setTimeout(run, 50)
    return () => {
      unsub()
      clearTimeout(timer)
      controller?.abort()
    }
  }, [agentId])
}

function useShortcuts() {
  const { fitView } = useReactFlow()
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t.closest('input, textarea, select, [contenteditable="true"], [role="dialog"]')) return
      const mod = e.metaKey || e.ctrlKey
      const s = useBuilder.getState()
      const key = e.key.toLowerCase()
      if (mod && key === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
      } else if (mod && key === 'y') {
        e.preventDefault()
        redo()
      } else if (mod && key === 'c') s.copySelection()
      else if (mod && key === 'v') s.paste()
      else if (mod && key === 'd') {
        e.preventDefault()
        s.duplicateSelection()
      } else if (e.shiftKey && e.code === 'Digit1') void fitView({ duration: 300, padding: 0.15 })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [fitView])
}
