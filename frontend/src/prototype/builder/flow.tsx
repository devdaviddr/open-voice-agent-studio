// PROTOTYPE — node and edge renderers shared by the builder layout variants. Not production code.
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
  ArrowRightLeft,
  Braces,
  CircleStop,
  GitBranch,
  MessageSquareText,
  Play,
  Sparkles,
  StickyNote,
  TriangleAlert,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { cn } from 'cn'
import type { FlowEdge, FlowNode, NodeKind } from './data'

export const kinds: Record<NodeKind, { name: string; icon: LucideIcon; tint: string; hint: string }> = {
  start: { name: 'Start', icon: Play, tint: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400', hint: 'First message and initial variables' },
  agent_step: { name: 'Agent step', icon: MessageSquareText, tint: 'bg-sky-500/15 text-sky-600 dark:text-sky-400', hint: 'A conversation step with its own prompt and tools' },
  extract: { name: 'Extract', icon: Braces, tint: 'bg-violet-500/15 text-violet-600 dark:text-violet-400', hint: 'Fill typed variables from the conversation' },
  router: { name: 'Router', icon: GitBranch, tint: 'bg-amber-500/15 text-amber-600 dark:text-amber-400', hint: 'Branch on conditions without speaking' },
  tool_call: { name: 'Tool call', icon: Wrench, tint: 'bg-orange-500/15 text-orange-600 dark:text-orange-400', hint: 'Call a tool deterministically' },
  handoff: { name: 'Handoff', icon: ArrowRightLeft, tint: 'bg-fuchsia-500/15 text-fuchsia-600 dark:text-fuchsia-400', hint: 'Pass the caller to another agent' },
  end: { name: 'End', icon: CircleStop, tint: 'bg-rose-500/15 text-rose-600 dark:text-rose-400', hint: 'Say goodbye and tag the outcome' },
  note: { name: 'Note', icon: StickyNote, tint: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300', hint: 'A comment on the canvas' },
}

function Chips({ items, mono }: { items?: string[]; mono?: boolean }) {
  if (!items?.length) return null
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((t) => (
        <span key={t} className={cn('bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px]', mono && 'font-mono')}>
          {t}
        </span>
      ))}
    </div>
  )
}

export function FlowNodeView({ data, type, selected }: NodeProps<FlowNode>) {
  const k = kinds[type as NodeKind]
  const Icon = k.icon
  if (type === 'note') {
    return (
      <div className={cn('w-56 rounded-lg border border-yellow-500/30 bg-yellow-100/70 p-3 text-xs leading-relaxed text-yellow-950 shadow-sm dark:bg-yellow-500/10 dark:text-yellow-100', selected && 'ring-2 ring-yellow-500/60')}>
        <StickyNote className="mb-1 size-3.5 opacity-60" />
        {data.label}
      </div>
    )
  }
  return (
    <div
      className={cn(
        'bg-card text-card-foreground w-60 rounded-xl border shadow-sm transition-shadow',
        selected && 'ring-ring ring-2',
        data.active && 'shadow-[0_0_0_3px] shadow-emerald-500/50',
      )}
    >
      {type !== 'start' && <Handle type="target" position={Position.Left} className="!bg-muted-foreground !size-2 !border-0" />}
      <div className="flex items-center gap-2 px-3 pt-3">
        <span className={cn('grid size-6 place-items-center rounded-md', k.tint)}>
          <Icon className="size-3.5" />
        </span>
        <span className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">{k.name}</span>
        {data.active && <span className="ml-auto size-2 animate-pulse rounded-full bg-emerald-500" />}
      </div>
      <div className="space-y-1.5 px-3 pt-1.5 pb-3">
        <div className={cn('text-sm font-medium', type === 'tool_call' && 'font-mono text-[13px]')}>{data.label}</div>
        {data.summary && <div className="text-muted-foreground line-clamp-2 text-xs">{data.summary}</div>}
        <Chips items={data.tools} mono />
        <Chips items={data.knowledge} />
        <Chips items={data.outputs} mono />
      </div>
      {data.issue && (
        <div className="flex items-center gap-1.5 border-t border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] text-amber-700 dark:text-amber-300">
          <TriangleAlert className="size-3" /> {data.issue}
        </div>
      )}
      {type !== 'end' && <Handle type="source" position={Position.Right} className="!bg-muted-foreground !size-2 !border-0" />}
    </div>
  )
}

export function ConditionEdge(props: EdgeProps<FlowEdge>) {
  const [path, x, y] = getSmoothStepPath({ ...props, borderRadius: 14 })
  const c = props.data?.condition
  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        markerEnd={props.markerEnd}
        style={{ stroke: props.selected ? 'var(--ring)' : 'var(--muted-foreground)', strokeOpacity: props.selected ? 1 : 0.45, strokeWidth: props.selected ? 2 : 1.25 }}
      />
      {c && (
        <EdgeLabelRenderer>
          <div
            className={cn(
              'nodrag nopan bg-background pointer-events-auto absolute flex max-w-48 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] shadow-xs',
              props.selected && 'border-ring',
            )}
            style={{ transform: `translate(-50%, -50%) translate(${x}px, ${y}px)` }}
          >
            {props.data?.order ? <span className="text-muted-foreground tabular-nums">{props.data.order}</span> : null}
            {c.kind === 'llm' && (
              <>
                <Sparkles className="size-3 shrink-0 text-violet-500" />
                <span className="truncate">{c.text}</span>
              </>
            )}
            {c.kind === 'cel' && <span className="truncate font-mono text-sky-700 dark:text-sky-300">{c.expr}</span>}
            {c.kind === 'else' && <span className="text-muted-foreground italic">else</span>}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

export const nodeTypes = Object.fromEntries(Object.keys(kinds).map((k) => [k, FlowNodeView]))
export const edgeTypes = { condition: ConditionEdge }
