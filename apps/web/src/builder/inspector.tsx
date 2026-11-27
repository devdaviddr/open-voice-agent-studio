import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { CircleAlert, Plus, Trash2 } from 'lucide-react'
import { cn } from 'cn'
import type { VariableDef } from '@/gen/agent-spec'
import { knowledgeQuery } from '@/api/knowledge'
import { StatusBadge } from '@/routes/knowledge-page'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import type { FlowEdge, FlowNode, NodeKind } from './convert'
import { KINDS } from './flow-components'
import { useShallow } from 'zustand/react/shallow'
import { useBuilder } from './store'

type VoiceList = { default: string; voices: string[] }
const voicesQuery = {
  queryKey: ['voices'],
  queryFn: async (): Promise<VoiceList> => {
    const res = await fetch('/api/v1/voices')
    if (!res.ok) throw new Error('Voices unavailable')
    return res.json()
  },
  staleTime: Infinity,
}

function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string
  hint?: string
  htmlFor?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={htmlFor} className="text-muted-foreground text-xs">
        {label}
      </Label>
      {children}
      {hint && <p className="text-muted-foreground text-[11px]">{hint}</p>}
    </div>
  )
}

function VoiceSelect({ value, onChange, id }: { value: string; onChange: (v: string) => void; id?: string }) {
  const { data } = useQuery(voicesQuery)
  const voices = data?.voices ?? [value]
  return (
    <Select value={value} onValueChange={(v) => v && onChange(v as string)}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {voices.map((v) => (
          <SelectItem key={v} value={v}>
            {v}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

const num = (v: number | readonly number[]) => (Array.isArray(v) ? v[0] : (v as number))

/** Attach workspace documents to the agent (MVP FR-15). Attaching enables `search_knowledge`. */
function KnowledgeSection() {
  const { data: sources = [] } = useQuery(knowledgeQuery)
  const attached = useBuilder((s) => s.meta.knowledge)
  const update = useBuilder((s) => s.updateMeta)
  const ids = new Set(attached.map((r) => r.source_id))
  const missing = attached.filter((r) => !sources.some((s) => s.id === r.source_id))
  function toggle(id: string, on: boolean) {
    update((m) => {
      const knowledge = on
        ? [...m.knowledge, { source_id: id }]
        : m.knowledge.filter((r) => r.source_id !== id)
      const hasTool = m.tools.some((t) => t.kind === 'builtin' && t.name === 'search_knowledge')
      const tools =
        on && !hasTool
          ? [...m.tools, { kind: 'builtin' as const, name: 'search_knowledge' as const }]
          : m.tools
      return { ...m, knowledge, tools }
    })
  }
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-muted-foreground mb-1.5 text-xs">Knowledge</legend>
      {sources.length === 0 && (
        <p className="text-muted-foreground text-[11px]">
          No documents yet.{' '}
          <Link to="/knowledge" className="underline underline-offset-2">
            Upload some
          </Link>{' '}
          for the agent to answer from.
        </p>
      )}
      {sources.map((src) => (
        <label key={src.id} className="flex items-center gap-2 text-xs">
          <Checkbox checked={ids.has(src.id)} onCheckedChange={(checked) => toggle(src.id, checked)} />
          <span className="min-w-0 flex-1 truncate">{src.name}</span>
          {src.status !== 'ready' && <StatusBadge source={src} />}
        </label>
      ))}
      {missing.map((r) => (
        <div key={r.source_id} className="text-destructive flex items-center gap-2 text-xs">
          <CircleAlert className="size-3.5 shrink-0" />
          <span className="flex-1">A deleted document is still attached.</span>
          <Button variant="link" size="xs" onClick={() => toggle(r.source_id, false)}>
            Detach
          </Button>
        </div>
      ))}
      {sources.length > 0 && (
        <p className="text-muted-foreground text-[11px]">
          Attached documents are searchable with the search_knowledge tool. Narrow them per step.
        </p>
      )}
    </fieldset>
  )
}

/** Per Agent step: which attached documents to use, and automatic top-k insertion. */
function StepKnowledge({
  value,
  topK,
  onChange,
}: {
  value: { source_id: string }[] | null | undefined
  topK: number
  onChange: (patch: Record<string, unknown>) => void
}) {
  const { data: sources = [] } = useQuery(knowledgeQuery)
  const attached = useBuilder((s) => s.meta.knowledge)
  if (attached.length === 0) return null
  const name = (id: string) => sources.find((s) => s.id === id)?.name ?? 'Deleted document'
  const chosen = value ? new Set(value.map((r) => r.source_id)) : null
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-muted-foreground mb-1.5 text-xs">Knowledge in this step</legend>
      <label className="flex items-center gap-2 text-xs">
        <Checkbox
          checked={chosen === null}
          onCheckedChange={(checked) => onChange({ knowledge: checked ? null : [...attached] })}
        />
        All attached documents
      </label>
      {chosen &&
        attached.map((r) => (
          <label key={r.source_id} className="flex items-center gap-2 pl-5 text-xs">
            <Checkbox
              checked={chosen.has(r.source_id)}
              onCheckedChange={(checked) =>
                onChange({
                  knowledge: checked
                    ? [...(value ?? []), r]
                    : (value ?? []).filter((x) => x.source_id !== r.source_id),
                })
              }
            />
            <span className="truncate">{name(r.source_id)}</span>
          </label>
        ))}
      <Field
        label={topK ? `Insert the top ${topK} passages every turn` : 'Insert passages automatically: off'}
        hint="Adds the best matches for the caller's last message to the prompt, without a tool call."
      >
        <Slider
          min={0}
          max={10}
          step={1}
          value={topK}
          onValueChange={(v) => onChange({ auto_knowledge_top_k: num(v) })}
        />
      </Field>
    </fieldset>
  )
}

function AgentSettingsPanel() {
  const meta = useBuilder((s) => s.meta)
  const update = useBuilder((s) => s.updateMeta)
  const settings = meta.settings
  const set = (patch: Partial<typeof settings>) =>
    update((m) => ({ ...m, settings: { ...m.settings, ...patch } }))
  return (
    <div className="flex flex-col gap-4">
      <Field
        label="Agent prompt"
        htmlFor="agent-prompt"
        hint="Applies to every step. Insert variables with {{name}}."
      >
        <Textarea
          id="agent-prompt"
          rows={7}
          value={settings.prompt}
          onChange={(e) => set({ prompt: e.target.value })}
          className="text-xs leading-relaxed"
        />
      </Field>
      <Field label="First message" htmlFor="first-message">
        <Textarea
          id="first-message"
          rows={2}
          value={settings.first_message}
          onChange={(e) => set({ first_message: e.target.value })}
        />
      </Field>
      <Field label="Model" htmlFor="llm-model" hint="Leave empty to use the workspace default.">
        <Input
          id="llm-model"
          placeholder="Workspace default"
          value={settings.llm.model ?? ''}
          onChange={(e) => set({ llm: { ...settings.llm, model: e.target.value || null } })}
        />
      </Field>
      <Field label={`Temperature: ${settings.llm.temperature.toFixed(1)}`}>
        <Slider
          min={0}
          max={1.5}
          step={0.1}
          value={settings.llm.temperature}
          onValueChange={(v) => set({ llm: { ...settings.llm, temperature: num(v) } })}
        />
      </Field>
      <Field label="Voice" htmlFor="agent-voice">
        <VoiceSelect
          id="agent-voice"
          value={settings.voice.voice_id}
          onChange={(voice_id) => set({ voice: { ...settings.voice, voice_id } })}
        />
      </Field>
      <Field label={`Speech speed: ${settings.voice.speed.toFixed(1)}×`}>
        <Slider
          min={0.5}
          max={2}
          step={0.1}
          value={settings.voice.speed}
          onValueChange={(v) => set({ voice: { ...settings.voice, speed: num(v) } })}
        />
      </Field>
      <Field
        label="History budget (tokens)"
        htmlFor="history-budget"
        hint="Older turns are summarised beyond this."
      >
        <Input
          id="history-budget"
          type="number"
          min={500}
          step={500}
          value={settings.history_token_budget}
          onChange={(e) => set({ history_token_budget: Math.max(500, Number(e.target.value) || 500) })}
        />
      </Field>
      <KnowledgeSection />
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="memory" className="flex flex-col items-start gap-0.5">
          <span>Long-term memory</span>
          <span className="text-muted-foreground text-[11px] font-normal">
            Remember facts about each caller.
          </span>
        </Label>
        <Switch
          id="memory"
          checked={meta.memory.enabled}
          onCheckedChange={(enabled) => update((m) => ({ ...m, memory: { enabled } }))}
        />
      </div>
    </div>
  )
}

const VAR_TYPES: VariableDef['type'][] = ['string', 'number', 'boolean', 'date', 'email', 'enum']

function VariablesPanel() {
  const variables = useBuilder((s) => s.meta.variables)
  const update = useBuilder((s) => s.updateMeta)
  const setVars = (fn: (v: VariableDef[]) => VariableDef[]) =>
    update((m) => ({ ...m, variables: fn(m.variables) }))
  const patch = (i: number, p: Partial<VariableDef>) =>
    setVars((vs) => vs.map((v, j) => (j === i ? { ...v, ...p } : v)))
  return (
    <div className="flex flex-col gap-3">
      <p className="text-muted-foreground text-xs">
        Typed values the agent collects or receives. Use them in prompts as{' '}
        <code className="font-mono">{'{{name}}'}</code>.
      </p>
      {variables.map((v, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-lg border p-2.5">
          <div className="flex gap-2">
            <Input
              aria-label="Variable name"
              className="h-8 font-mono text-xs"
              value={v.name}
              onChange={(e) => patch(i, { name: e.target.value.toLowerCase().replace(/[^a-z0-9_.]/g, '_') })}
            />
            <Select
              value={v.type}
              onValueChange={(t) =>
                t && patch(i, { type: t as VariableDef['type'], enum: t === 'enum' ? (v.enum ?? []) : null })
              }
            >
              <SelectTrigger aria-label="Variable type" className="h-8 w-28 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VAR_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Delete ${v.name}`}
              onClick={() => setVars((vs) => vs.filter((_, j) => j !== i))}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
          {v.type === 'enum' && (
            <Input
              aria-label="Allowed values"
              className="h-8 text-xs"
              placeholder="Allowed values, comma separated"
              value={(v.enum ?? []).join(', ')}
              onChange={(e) =>
                patch(i, {
                  enum: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
            />
          )}
          <Input
            aria-label="Description"
            className="h-8 text-xs"
            placeholder="Description"
            value={v.description}
            onChange={(e) => patch(i, { description: e.target.value })}
          />
        </div>
      ))}
      <Button
        variant="outline"
        size="sm"
        onClick={() =>
          setVars((vs) => [
            ...vs,
            { name: `var_${vs.length + 1}`, type: 'string', enum: null, description: '' },
          ])
        }
      >
        <Plus className="size-3.5" /> Add variable
      </Button>
    </div>
  )
}

function NodeInspector({ node }: { node: FlowNode }) {
  const update = useBuilder((s) => s.updateNodeData)
  const variables = useBuilder((s) => s.meta.variables)
  const agentVoice = useBuilder((s) => s.meta.settings.voice)
  const issues = useBuilder(useShallow((s) => s.issues.filter((i) => i.node_id === node.id)))
  const set = (patch: Record<string, unknown>) => update(node.id, patch)
  const k = KINDS[node.type as NodeKind]
  const d = node.data as { label?: string }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className={cn('grid size-7 place-items-center rounded-md', k.tint)}>
          <k.icon className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
            {k.name}
          </div>
          <div className="truncate text-sm font-medium">{d.label ?? k.name}</div>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Delete node"
          onClick={() => useBuilder.getState().removeNode(node.id)}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
      {issues.map((i) => (
        <div
          key={i.code}
          className="border-destructive/30 bg-destructive/10 text-destructive flex gap-1.5 rounded-md border p-2 text-xs"
        >
          <CircleAlert className="mt-px size-3.5 shrink-0" /> {i.message}
        </div>
      ))}
      {d.label !== undefined && (
        <Field label="Label" htmlFor="node-label">
          <Input id="node-label" value={d.label} onChange={(e) => set({ label: e.target.value })} />
        </Field>
      )}
      {node.type === 'start' && (
        <Field label="First message" htmlFor="start-msg" hint="Leave empty to use the agent’s first message.">
          <Textarea
            id="start-msg"
            rows={3}
            value={node.data.first_message ?? ''}
            onChange={(e) => set({ first_message: e.target.value || null })}
          />
        </Field>
      )}
      {node.type === 'agent_step' && (
        <>
          <Field
            label="Step prompt"
            htmlFor="step-prompt"
            hint="Added to the agent prompt while this step is active."
          >
            <Textarea
              id="step-prompt"
              rows={8}
              className="text-xs leading-relaxed"
              value={node.data.prompt}
              onChange={(e) => set({ prompt: e.target.value })}
            />
          </Field>
          <StepKnowledge value={node.data.knowledge} topK={node.data.auto_knowledge_top_k} onChange={set} />
          <div className="flex items-center justify-between">
            <Label htmlFor="voice-override" className="text-xs">
              Different voice for this step
            </Label>
            <Switch
              id="voice-override"
              checked={!!node.data.overrides?.voice}
              onCheckedChange={(on) =>
                set({
                  overrides: {
                    ...(node.data.overrides ?? { language: null, llm: null }),
                    voice: on ? { ...agentVoice } : null,
                  },
                })
              }
            />
          </div>
          {node.data.overrides?.voice && (
            <VoiceSelect
              value={node.data.overrides.voice.voice_id}
              onChange={(voice_id) =>
                set({
                  overrides: { ...node.data.overrides, voice: { ...node.data.overrides!.voice!, voice_id } },
                })
              }
            />
          )}
          <Field
            label="Model for this step"
            htmlFor="step-model"
            hint="Leave empty to use the agent’s model."
          >
            <Input
              id="step-model"
              placeholder="Agent default"
              value={node.data.overrides?.llm?.model ?? ''}
              onChange={(e) => {
                const model = e.target.value || null
                const base = node.data.overrides ?? { language: null, voice: null, llm: null }
                set({
                  overrides: {
                    ...base,
                    llm: model ? { provider: 'workspace', temperature: 0.6, ...base.llm, model } : null,
                  },
                })
              }}
            />
          </Field>
        </>
      )}
      {node.type === 'extract' && (
        <>
          <Field label="Instructions" htmlFor="extract-instr" hint="How to ask for missing details.">
            <Textarea
              id="extract-instr"
              rows={3}
              value={node.data.instructions}
              onChange={(e) => set({ instructions: e.target.value })}
            />
          </Field>
          <Field label="Variables to fill">
            {variables.length === 0 && (
              <p className="text-muted-foreground text-xs">Declare variables in the Variables tab first.</p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {variables.map((v) => {
                const on = node.data.outputs.includes(v.name)
                return (
                  <button
                    key={v.name}
                    aria-pressed={on}
                    onClick={() =>
                      set({
                        outputs: on
                          ? node.data.outputs.filter((o) => o !== v.name)
                          : [...node.data.outputs, v.name],
                      })
                    }
                    className={cn(
                      'rounded-md border px-2 py-1 font-mono text-[11px]',
                      on
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted',
                    )}
                  >
                    {v.name}
                  </button>
                )
              })}
            </div>
          </Field>
        </>
      )}
      {node.type === 'router' && (
        <p className="text-muted-foreground text-xs">
          Routers do not speak. Their outgoing edges are checked in order: expressions first, then
          model-judged conditions, then <em>else</em>.
        </p>
      )}
      {node.type === 'end' && (
        <>
          <Field label="Goodbye message" htmlFor="end-msg">
            <Textarea
              id="end-msg"
              rows={2}
              value={node.data.message ?? ''}
              onChange={(e) => set({ message: e.target.value || null })}
            />
          </Field>
          <Field label="Outcome tag" htmlFor="end-outcome" hint="Shown on sessions that end here.">
            <Input
              id="end-outcome"
              className="font-mono"
              value={node.data.outcome}
              onChange={(e) => set({ outcome: e.target.value })}
            />
          </Field>
        </>
      )}
      {node.type === 'note' && (
        <Field label="Note" htmlFor="note-text">
          <Textarea
            id="note-text"
            rows={6}
            value={node.data.text}
            onChange={(e) => set({ text: e.target.value })}
          />
        </Field>
      )}
    </div>
  )
}

function EdgeInspector({ edge }: { edge: FlowEdge }) {
  const nodes = useBuilder((s) => s.nodes)
  const update = useBuilder((s) => s.updateEdgeData)
  const issues = useBuilder(useShallow((s) => s.issues.filter((i) => i.edge_id === edge.id)))
  const source = nodes.find((n) => n.id === edge.source)
  const target = nodes.find((n) => n.id === edge.target)
  const name = (n?: FlowNode) =>
    n && 'label' in n.data ? (n.data as { label: string }).label : (n?.type ?? '?')
  const c = edge.data?.condition ?? null
  const conditional = source?.type === 'agent_step' || source?.type === 'router'
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">Edge</div>
          <div className="text-sm font-medium">
            {name(source)} → {name(target)}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Delete edge"
          onClick={() => useBuilder.getState().removeEdge(edge.id)}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
      {issues.map((i) => (
        <div
          key={i.code}
          className="border-destructive/30 bg-destructive/10 text-destructive rounded-md border p-2 text-xs"
        >
          {i.message}
        </div>
      ))}
      {!conditional ? (
        <p className="text-muted-foreground text-xs">
          Always taken once the {source?.type === 'extract' ? 'variables are filled' : 'step finishes'}.
        </p>
      ) : (
        <Tabs
          value={c?.kind ?? 'always'}
          onValueChange={(kind) =>
            update(edge.id, {
              condition:
                kind === 'llm'
                  ? { kind: 'llm', text: c?.kind === 'llm' ? c.text : '' }
                  : kind === 'cel'
                    ? { kind: 'cel', expr: c?.kind === 'cel' ? c.expr : '' }
                    : kind === 'else'
                      ? { kind: 'else' }
                      : null,
            })
          }
        >
          <TabsList className="w-full">
            <TabsTrigger value="llm">Model</TabsTrigger>
            <TabsTrigger value="cel">Expression</TabsTrigger>
            <TabsTrigger value="else">Else</TabsTrigger>
            {source?.type === 'agent_step' && <TabsTrigger value="always">Always</TabsTrigger>}
          </TabsList>
          <TabsContent value="llm" className="pt-3">
            <Field label="Move on when the caller…" htmlFor="edge-llm">
              <Textarea
                id="edge-llm"
                rows={3}
                placeholder="wants to book an appointment"
                value={c?.kind === 'llm' ? c.text : ''}
                onChange={(e) => update(edge.id, { condition: { kind: 'llm', text: e.target.value } })}
              />
            </Field>
          </TabsContent>
          <TabsContent value="cel" className="pt-3">
            <Field
              label="CEL expression over variables"
              htmlFor="edge-cel"
              hint='Example: appointment_type == "emergency"'
            >
              <Input
                id="edge-cel"
                className="font-mono text-xs"
                value={c?.kind === 'cel' ? c.expr : ''}
                onChange={(e) => update(edge.id, { condition: { kind: 'cel', expr: e.target.value } })}
              />
            </Field>
          </TabsContent>
          <TabsContent value="else" className="text-muted-foreground pt-3 text-xs">
            Taken when no other edge from this node fires.
          </TabsContent>
          <TabsContent value="always" className="text-muted-foreground pt-3 text-xs">
            Taken after every reply in this step.
          </TabsContent>
        </Tabs>
      )}
      {conditional && (
        <Field label="Order" htmlFor="edge-order" hint="Lower numbers are checked first.">
          <Input
            id="edge-order"
            type="number"
            min={0}
            className="w-24"
            value={edge.data?.order ?? 0}
            onChange={(e) => update(edge.id, { order: Math.max(0, Number(e.target.value) || 0) })}
          />
        </Field>
      )}
    </div>
  )
}

export function Inspector() {
  const node = useBuilder((s) => {
    const selected = s.nodes.filter((n) => n.selected)
    return selected.length === 1 ? selected[0] : undefined
  })
  const edge = useBuilder((s) => {
    const selected = s.edges.filter((e) => e.selected)
    return selected.length === 1 && !s.nodes.some((n) => n.selected) ? selected[0] : undefined
  })
  if (node) return <NodeInspector key={node.id} node={node} />
  if (edge) return <EdgeInspector key={edge.id} edge={edge} />
  return (
    <Tabs defaultValue="agent">
      <TabsList className="mb-4 w-full">
        <TabsTrigger value="agent">Agent</TabsTrigger>
        <TabsTrigger value="variables">Variables</TabsTrigger>
      </TabsList>
      <TabsContent value="agent">
        <AgentSettingsPanel />
      </TabsContent>
      <TabsContent value="variables">
        <VariablesPanel />
      </TabsContent>
    </Tabs>
  )
}
