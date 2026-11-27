import { create } from 'zustand'
import { temporal } from 'zundo'
import {
  addEdge,
  type Connection,
  type EdgeChangeset,
  type NodeChangeset,
  type XYPosition,
} from '@xyflow/react'
import type { Issue } from '@/gen/api'
import type { AgentSpec } from '@/gen/agent-spec'
import {
  flowToSpec,
  newId,
  specToFlow,
  type FlowEdge,
  type FlowNode,
  type Meta,
  type NodeKind,
} from './convert'

export type SaveState = 'saved' | 'pending' | 'saving' | 'conflict' | 'error'

type Content = { nodes: FlowNode[]; edges: FlowEdge[]; meta: Meta }

type State = Content & {
  agentId: string
  revision: number
  /** Increments on every load so subscribers can tell a reload from an edit. */
  loadCount: number
  issues: Issue[]
  /** Node the test console's session is in; highlighted on the canvas. */
  activeNodeId: string | null
  saveState: SaveState
  conflictRevision: number | null
  clipboard: { nodes: FlowNode[]; edges: FlowEdge[] } | null
  load: (agentId: string, revision: number, spec: AgentSpec) => void
  onNodesChange: (changes: NodeChangeset<FlowNode>) => void
  onEdgesChange: (changes: EdgeChangeset<FlowEdge>) => void
  removeNode: (id: string) => void
  removeEdge: (id: string) => void
  onConnect: (c: Connection) => void
  addNode: (kind: NodeKind, position: XYPosition) => void
  updateNodeData: (id: string, patch: Record<string, unknown>) => void
  updateEdgeData: (id: string, patch: Partial<NonNullable<FlowEdge['data']>>) => void
  updateMeta: (fn: (meta: Meta) => Meta) => void
  select: (ids: { nodes?: string[]; edges?: string[] }) => void
  copySelection: () => void
  paste: () => void
  duplicateSelection: () => void
  setIssues: (issues: Issue[]) => void
  setActiveNode: (id: string | null) => void
  setSaveState: (s: SaveState, conflictRevision?: number | null) => void
  markSaved: (revision: number) => void
}

/** Time of the last content edit, for grouping undo steps. load() resets it. */
let lastEdit = 0

export const DEFAULT_DATA: { [K in NodeKind]: Extract<FlowNode, { type: K }>['data'] } = {
  start: { first_message: null, set: {} },
  agent_step: {
    label: 'New step',
    prompt: '',
    overrides: null,
    tools: null,
    knowledge: null,
    auto_knowledge_top_k: 0,
  },
  extract: { label: 'Extract details', instructions: '', outputs: [] },
  router: { label: 'Router' },
  end: { label: 'End', message: null, outcome: 'completed' },
  note: { text: 'Note' },
} as never

const CONNECTABLE_FROM: NodeKind[] = ['start', 'agent_step', 'extract', 'router']

export function isValidConnection(nodes: FlowNode[], c: { source: string; target: string }): boolean {
  const source = nodes.find((n) => n.id === c.source)
  const target = nodes.find((n) => n.id === c.target)
  if (!source || !target || source.id === target.id) return false
  return (
    CONNECTABLE_FROM.includes(source.type as NodeKind) && target.type !== 'start' && target.type !== 'note'
  )
}

/** Strip view-only fields so undo history and autosave only see real edits. */
export function content(s: Content): Content {
  return {
    nodes: s.nodes.map(({ id, type, position, data }) => ({ id, type, position, data }) as FlowNode),
    edges: s.edges.map(
      ({ id, source, target, type, data }) => ({ id, source, target, type, data }) as FlowEdge,
    ),
    meta: s.meta,
  }
}

export const contentKey = (s: Content) => JSON.stringify(flowToSpec(s.nodes, s.edges, s.meta))

export const useBuilder = create<State>()(
  temporal(
    (set, get) => ({
      agentId: '',
      revision: 0,
      loadCount: 0,
      nodes: [],
      edges: [],
      meta: {} as Meta,
      issues: [],
      activeNodeId: null,
      saveState: 'saved',
      conflictRevision: null,
      clipboard: null,

      load: (agentId, revision, spec) => {
        const flow = specToFlow(spec)
        set({
          agentId,
          revision,
          ...flow,
          issues: [],
          saveState: 'saved',
          conflictRevision: null,
          loadCount: get().loadCount + 1,
        })
        useBuilder.temporal.getState().clear()
        lastEdit = 0
      },

      onNodesChange: (changes) => set({ nodes: changes.applyTo(get().nodes) }),
      onEdgesChange: (changes) => set({ edges: changes.applyTo(get().edges) }),
      removeNode: (id) =>
        set({
          nodes: get().nodes.filter((n) => n.id !== id),
          edges: get().edges.filter((e) => e.source !== id && e.target !== id),
        }),
      removeEdge: (id) => set({ edges: get().edges.filter((e) => e.id !== id) }),

      onConnect: (c) => {
        const { nodes, edges } = get()
        if (!c.source || !c.target || !isValidConnection(nodes, c)) return
        const source = nodes.find((n) => n.id === c.source)!
        const siblings = edges.filter((e) => e.source === c.source)
        const order = Math.max(0, ...siblings.map((e) => e.data?.order ?? 0)) + 1
        let condition: NonNullable<FlowEdge['data']>['condition'] = null
        if (source.type === 'router') {
          condition = siblings.some((e) => e.data?.condition?.kind === 'else')
            ? { kind: 'llm', text: 'describe when to take this path' }
            : { kind: 'else' }
        } else if (source.type === 'agent_step') {
          condition = { kind: 'llm', text: 'the caller is ready to move on' }
        }
        set({
          edges: addEdge(
            { ...c, id: newId('e'), type: 'condition', data: { condition, order } } as FlowEdge,
            edges,
          ),
        })
      },

      addNode: (kind, position) => {
        const id = newId(kind.replace('_', '-'))
        const node = {
          id,
          type: kind,
          position,
          data: structuredClone(DEFAULT_DATA[kind]),
          selected: true,
        } as FlowNode
        set({
          nodes: [...get().nodes.map((n) => ({ ...n, selected: false })), node],
          edges: get().edges.map((e) => ({ ...e, selected: false })),
        })
      },

      updateNodeData: (id, patch) =>
        set({
          nodes: get().nodes.map((n) =>
            n.id === id ? ({ ...n, data: { ...n.data, ...patch } } as FlowNode) : n,
          ),
        }),

      updateEdgeData: (id, patch) =>
        set({
          edges: get().edges.map((e) =>
            e.id === id ? { ...e, data: { condition: null, order: 0, ...e.data, ...patch } } : e,
          ),
        }),

      updateMeta: (fn) => set({ meta: fn(get().meta) }),

      select: ({ nodes = [], edges = [] }) =>
        set({
          nodes: get().nodes.map((n) => ({ ...n, selected: nodes.includes(n.id) })),
          edges: get().edges.map((e) => ({ ...e, selected: edges.includes(e.id) })),
        }),

      copySelection: () => {
        const nodes = get().nodes.filter((n) => n.selected && n.type !== 'start')
        const ids = new Set(nodes.map((n) => n.id))
        const edges = get().edges.filter((e) => ids.has(e.source) && ids.has(e.target))
        if (nodes.length) set({ clipboard: structuredClone(content({ nodes, edges, meta: get().meta })) })
      },

      paste: () => {
        const clip = get().clipboard
        if (!clip) return
        const idMap = new Map(clip.nodes.map((n) => [n.id, newId(n.type!.replace('_', '-'))]))
        const nodes = clip.nodes.map(
          (n) =>
            ({
              ...structuredClone(n),
              id: idMap.get(n.id)!,
              position: { x: n.position.x + 40, y: n.position.y + 40 },
              selected: true,
            }) as FlowNode,
        )
        const edges = clip.edges.map((e) => ({
          ...structuredClone(e),
          id: newId('e'),
          source: idMap.get(e.source)!,
          target: idMap.get(e.target)!,
        }))
        set({
          nodes: [...get().nodes.map((n) => ({ ...n, selected: false })), ...nodes],
          edges: [...get().edges.map((e) => ({ ...e, selected: false })), ...edges],
          clipboard: { nodes: nodes.map((n) => ({ ...n, selected: false })), edges },
        })
      },

      duplicateSelection: () => {
        const clipboard = get().clipboard
        get().copySelection()
        get().paste()
        set({ clipboard })
      },

      setIssues: (issues) => set({ issues }),
      setActiveNode: (activeNodeId) => set({ activeNodeId }),
      setSaveState: (saveState, conflictRevision = null) => set({ saveState, conflictRevision }),
      markSaved: (revision) => set({ revision, saveState: 'saved', conflictRevision: null }),
    }),
    {
      partialize: (s) => content(s),
      equality: (a, b) => JSON.stringify(a) === JSON.stringify(b),
      limit: 200,
      // One undo step per burst of edits (typing, dragging): record only after 600 ms of quiet.
      handleSet: (handleSet) => {
        return (...args: Parameters<typeof handleSet>) => {
          // Selection and measuring also call set; only real edits count towards the window.
          if (JSON.stringify(args[0]) === JSON.stringify(content(useBuilder.getState()))) return
          const now = Date.now()
          if (now - lastEdit > 600) handleSet(...args)
          lastEdit = now
        }
      },
    },
  ),
)

export const undo = () => useBuilder.temporal.getState().undo()
export const redo = () => useBuilder.temporal.getState().redo()

// Development aid: inspect the builder from the browser console (and end-to-end tests).
if (import.meta.env.DEV)
  (window as unknown as { __ovasBuilder: typeof useBuilder }).__ovasBuilder = useBuilder
