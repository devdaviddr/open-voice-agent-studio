import { memo } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  Handle,
  Position,
  type EdgeProps,
  type NodeProps,
} from '@xyflow/react'
import {
  Braces,
  CircleAlert,
  CircleStop,
  GitBranch,
  MessageSquareText,
  Play,
  Sparkles,
  StickyNote,
  type LucideIcon,
} from 'lucide-react'
import { cn } from 'cn'
import type { FlowEdge, FlowNode, NodeKind } from './convert'
import { useShallow } from 'zustand/react/shallow'
import { useBuilder } from './store'

export const KINDS: Record<NodeKind, { name: string; icon: LucideIcon; tint: string; hint: string }> = {
  start: {
    name: 'Start',
    icon: Play,
    tint: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
    hint: 'First message and initial variables',
  },
  agent_step: {
    name: 'Agent step',
    icon: MessageSquareText,
    tint: 'bg-sky-500/15 text-sky-700 dark:text-sky-400',
    hint: 'A conversation step with its own prompt',
  },
  extract: {
    name: 'Extract',
    icon: Braces,
    tint: 'bg-violet-500/15 text-violet-700 dark:text-violet-400',
    hint: 'Collect variables from the conversation',
  },
  router: {
    name: 'Router',
    icon: GitBranch,
    tint: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
    hint: 'Branch on conditions without speaking',
  },
  end: {
    name: 'End',
    icon: CircleStop,
    tint: 'bg-rose-500/15 text-rose-700 dark:text-rose-400',
    hint: 'Say goodbye and tag the outcome',
  },
  note: {
    name: 'Note',
    icon: StickyNote,
    tint: 'bg-yellow-500/20 text-yellow-800 dark:text-yellow-300',
    hint: 'A comment on the canvas',
  },
}

function Chips({ items, mono }: { items?: string[] | null; mono?: boolean }) {
  if (!items?.length) return null
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((t) => (
        <span
          key={t}
          className={cn(
            'bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px]',
            mono && 'font-mono',
          )}
        >
          {t}
        </span>
      ))}
    </div>
  )
}

function summary(node: FlowNode): { title: string; body?: string; chips?: string[] } {
  switch (node.type) {
    case 'start':
      return { title: 'Start', body: node.data.first_message ?? 'Uses the agent’s first message' }
    case 'agent_step':
      return { title: node.data.label, body: node.data.prompt || 'No step prompt yet' }
    case 'extract':
      return { title: node.data.label, body: node.data.instructions || undefined, chips: node.data.outputs }
    case 'router':
      return { title: node.data.label }
    case 'end':
      return {
        title: node.data.label,
        body: node.data.message ?? undefined,
        chips: [`outcome: ${node.data.outcome}`],
      }
    default:
      return { title: '' }
  }
}

export const FlowNodeView = memo(function FlowNodeView(props: NodeProps<FlowNode>) {
  const { id, type, selected } = props
  const node = props as unknown as FlowNode
  const issues = useBuilder(useShallow((s) => s.issues.filter((i) => i.node_id === id)))
  const k = KINDS[type as NodeKind]
  const Icon = k.icon
  if (type === 'note') {
    return (
      <div
        className={cn(
          'w-56 rounded-lg border border-yellow-500/30 bg-yellow-100/80 p-3 text-xs leading-relaxed whitespace-pre-wrap text-yellow-950 shadow-sm dark:bg-yellow-500/10 dark:text-yellow-100',
          selected && 'ring-2 ring-yellow-500/60',
        )}
      >
        {(node.data as { text: string }).text}
      </div>
    )
  }
  const s = summary({ ...node, type } as FlowNode)
  return (
    <div
      className={cn(
        'bg-card text-card-foreground w-60 rounded-xl border shadow-sm',
        selected && 'ring-ring ring-2',
        issues.length > 0 && 'border-destructive/60',
      )}
    >
      {type !== 'start' && (
        <Handle type="target" position={Position.Left} className="!bg-muted-foreground !size-2.5 !border-0" />
      )}
      <div className="flex items-center gap-2 px-3 pt-3">
        <span className={cn('grid size-6 place-items-center rounded-md', k.tint)}>
          <Icon className="size-3.5" />
        </span>
        <span className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
          {k.name}
        </span>
      </div>
      <div className="space-y-1.5 px-3 pt-1.5 pb-3">
        <div className="text-sm font-medium">{s.title}</div>
        {s.body && <div className="text-muted-foreground line-clamp-2 text-xs">{s.body}</div>}
        <Chips items={s.chips} mono />
      </div>
      {issues.length > 0 && (
        <div className="border-destructive/30 bg-destructive/10 text-destructive flex items-start gap-1.5 rounded-b-xl border-t px-3 py-1.5 text-[11px]">
          <CircleAlert className="mt-px size-3 shrink-0" />
          <span>
            {issues[0].message}
            {issues.length > 1 ? ` (+${issues.length - 1})` : ''}
          </span>
        </div>
      )}
      {type !== 'end' && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-muted-foreground !size-2.5 !border-0"
        />
      )}
    </div>
  )
})

export const ConditionEdge = memo(function ConditionEdge(props: EdgeProps<FlowEdge>) {
  const [path, x, y] = getSmoothStepPath({ ...props, borderRadius: 14 })
  const c = props.data?.condition
  const hasIssue = useBuilder((s) => s.issues.some((i) => i.edge_id === props.id))
  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        markerEnd={props.markerEnd}
        style={{
          stroke: hasIssue
            ? 'var(--destructive)'
            : props.selected
              ? 'var(--ring)'
              : 'var(--muted-foreground)',
          strokeOpacity: props.selected || hasIssue ? 1 : 0.5,
          strokeWidth: props.selected ? 2 : 1.25,
        }}
      />
      {c && (
        <EdgeLabelRenderer>
          <div
            className={cn(
              'nodrag nopan bg-background pointer-events-auto absolute flex max-w-52 cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] shadow-xs',
              props.selected && 'border-ring',
              hasIssue && 'border-destructive text-destructive',
            )}
            style={{ transform: `translate(-50%, -50%) translate(${x}px, ${y}px)` }}
            onClick={() => useBuilder.getState().select({ edges: [props.id] })}
          >
            {props.data?.order ? (
              <span className="text-muted-foreground tabular-nums">{props.data.order}</span>
            ) : null}
            {c.kind === 'llm' && (
              <>
                <Sparkles className="size-3 shrink-0 text-violet-500" />
                <span className="truncate">{c.text}</span>
              </>
            )}
            {c.kind === 'cel' && (
              <span className="truncate font-mono text-sky-700 dark:text-sky-300">{c.expr || '…'}</span>
            )}
            {c.kind === 'else' && <span className="text-muted-foreground italic">else</span>}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
})

export const nodeTypes = Object.fromEntries(Object.keys(KINDS).map((k) => [k, FlowNodeView]))
export const edgeTypes = { condition: ConditionEdge }
