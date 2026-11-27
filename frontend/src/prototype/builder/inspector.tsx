// PROTOTYPE — inspector content shared by the builder layout variants. Not production code.
import { Plus, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { agent, type FlowEdge, type FlowNode } from './data'
import { kinds } from './flow'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-muted-foreground text-xs">{label}</Label>
      {children}
    </div>
  )
}

function ChipList({ items, add }: { items?: string[]; add: string }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items?.map((t) => (
        <Badge key={t} variant="secondary" className="font-mono text-[11px]">
          {t}
        </Badge>
      ))}
      <Button variant="ghost" size="xs" className="text-muted-foreground h-5 px-1.5 text-[11px]">
        <Plus className="size-3" /> {add}
      </Button>
    </div>
  )
}

export function Inspector({ node, edge, nodes }: { node?: FlowNode; edge?: FlowEdge; nodes: FlowNode[] }) {
  if (edge) {
    const c = edge.data?.condition
    const from = nodes.find((n) => n.id === edge.source)?.data.label
    const to = nodes.find((n) => n.id === edge.target)?.data.label
    return (
      <div key={edge.id} className="flex flex-col gap-4">
        <div>
          <div className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">Edge</div>
          <div className="text-sm font-medium">
            {from} → {to}
          </div>
        </div>
        <Tabs defaultValue={c?.kind ?? 'else'}>
          <TabsList className="w-full">
            <TabsTrigger value="llm">LLM</TabsTrigger>
            <TabsTrigger value="cel">Expression</TabsTrigger>
            <TabsTrigger value="else">Else</TabsTrigger>
          </TabsList>
          <TabsContent value="llm" className="pt-3">
            <Field label="Fires when the model judges that the caller…">
              <Textarea rows={3} defaultValue={c?.kind === 'llm' ? c.text : ''} placeholder="wants to book an appointment" />
            </Field>
          </TabsContent>
          <TabsContent value="cel" className="pt-3">
            <Field label="CEL expression over session variables">
              <Input className="font-mono" defaultValue={c?.kind === 'cel' ? c.expr : ''} placeholder="slot.available == true" />
            </Field>
          </TabsContent>
          <TabsContent value="else" className="text-muted-foreground pt-3 text-xs">
            Taken when no other edge from this node fires.
          </TabsContent>
        </Tabs>
        <Field label="Order">
          <Input type="number" defaultValue={edge.data?.order ?? 0} className="w-20" />
        </Field>
      </div>
    )
  }

  if (!node) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <div className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">Agent</div>
          <div className="text-sm font-medium">{agent.name}</div>
        </div>
        <Field label="Voice">
          <Input defaultValue={agent.voice} />
        </Field>
        <Field label="LLM">
          <Input defaultValue={agent.llm} />
        </Field>
        <Field label="Speech to text">
          <Input defaultValue={agent.stt} />
        </Field>
        <div className="flex items-center justify-between">
          <Label className="text-xs">Interruptions</Label>
          <Switch defaultChecked />
        </div>
        <div className="flex items-center justify-between">
          <Label className="text-xs">Long-term memory</Label>
          <Switch />
        </div>
        <p className="text-muted-foreground text-xs">Select a node or edge to edit it.</p>
      </div>
    )
  }

  const k = kinds[node.type as keyof typeof kinds]
  const d = node.data
  return (
    <div key={node.id} className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className={`grid size-7 place-items-center rounded-md ${k.tint}`}>
          <k.icon className="size-4" />
        </span>
        <div>
          <div className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">{k.name}</div>
          <div className="text-sm font-medium">{d.label}</div>
        </div>
      </div>
      <Field label="Label">
        <Input defaultValue={d.label} />
      </Field>
      {node.type === 'agent_step' && (
        <>
          <Field label="Step prompt">
            <Textarea rows={6} defaultValue={d.prompt ?? d.summary} className="text-xs leading-relaxed" />
          </Field>
          <p className="text-muted-foreground -mt-2 flex items-center gap-1 text-[11px]">
            <Sparkles className="size-3" /> Use {'{{caller.name}}'} to insert variables
          </p>
          <Field label="Tools">
            <ChipList items={d.tools} add="Tool" />
          </Field>
          <Field label="Knowledge">
            <ChipList items={d.knowledge} add="Source" />
          </Field>
          <div className="flex items-center justify-between">
            <Label className="text-xs">Override voice</Label>
            <Switch defaultChecked={!!d.voice} />
          </div>
        </>
      )}
      {node.type === 'extract' && (
        <Field label="Variables to fill">
          <ChipList items={d.outputs} add="Variable" />
        </Field>
      )}
      {node.type === 'tool_call' && (
        <>
          <Field label="Request">
            <Input className="font-mono text-xs" defaultValue={d.summary} />
          </Field>
          <Field label="Map result">
            <Input className="font-mono text-xs" defaultValue="slot ← $.slots[0]" />
          </Field>
        </>
      )}
      {(node.type === 'start' || node.type === 'end') && (
        <Field label={node.type === 'start' ? 'First message' : 'Outcome'}>
          <Textarea rows={3} defaultValue={d.summary} />
        </Field>
      )}
      {d.issue && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-700 dark:text-amber-300">{d.issue}</div>}
    </div>
  )
}
