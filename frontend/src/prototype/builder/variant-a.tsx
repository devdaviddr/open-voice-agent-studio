// PROTOTYPE — Variant A: classic three-pane editor (palette · canvas · inspector). Not production code.
import { Background, BackgroundVariant, Controls, MiniMap, ReactFlow } from '@xyflow/react'
import { ChevronDown, CircleCheck, Play, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { agent, type NodeKind } from './data'
import { edgeTypes, kinds, nodeTypes } from './flow'
import { Inspector } from './inspector'
import { useFlow } from './use-flow'

export const name = 'Three-pane editor'

export function VariantA() {
  const f = useFlow({ selected: 'triage' })
  return (
    <div className="bg-background flex h-svh flex-col">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b px-4">
        <span className="text-muted-foreground text-sm">Agents /</span>
        <span className="text-sm font-medium">{agent.name}</span>
        <Badge variant="outline" className="font-normal">
          Draft · rev {agent.draftRevision}
        </Badge>
        <Button variant="ghost" size="sm" className="text-muted-foreground gap-1">
          live is v{agent.live} <ChevronDown className="size-3.5" />
        </Button>
        <div className="ml-auto flex items-center gap-2">
          {f.issues ? (
            <Button variant="ghost" size="sm" className="gap-1.5 text-amber-600 dark:text-amber-400">
              <TriangleAlert className="size-4" /> {f.issues} issue
            </Button>
          ) : (
            <span className="flex items-center gap-1.5 text-sm text-emerald-600">
              <CircleCheck className="size-4" /> Valid
            </span>
          )}
          <Button variant="outline" size="sm" className="gap-1.5">
            <Play className="size-3.5" /> Test
          </Button>
          <Button size="sm">Publish v{agent.live + 1}</Button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="w-56 shrink-0 border-r">
          <ScrollArea className="h-full">
            <div className="p-3">
              <div className="text-muted-foreground mb-2 px-1 text-[10px] font-medium tracking-wide uppercase">Nodes</div>
              {(Object.keys(kinds) as NodeKind[]).map((k) => {
                const m = kinds[k]
                return (
                  <button key={k} onClick={() => f.addNode(k)} className="hover:bg-muted flex w-full items-start gap-2.5 rounded-md p-2 text-left">
                    <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-md ${m.tint}`}>
                      <m.icon className="size-3.5" />
                    </span>
                    <span>
                      <span className="block text-sm">{m.name}</span>
                      <span className="text-muted-foreground block text-[11px] leading-snug">{m.hint}</span>
                    </span>
                  </button>
                )
              })}
              <Separator className="my-3" />
              <div className="text-muted-foreground mb-2 px-1 text-[10px] font-medium tracking-wide uppercase">Variables</div>
              {['caller.name', 'caller.phone', 'preferred_date', 'slot'].map((v) => (
                <div key={v} className="text-muted-foreground px-2 py-1 font-mono text-xs">
                  {v}
                </div>
              ))}
            </div>
          </ScrollArea>
        </aside>
        <main className="min-w-0 flex-1">
          <ReactFlow
            nodes={f.nodes}
            edges={f.edges}
            onNodesChange={f.onNodesChange}
            onEdgesChange={f.onEdgesChange}
            onConnect={f.onConnect}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
        minZoom={0.2}
            fitViewOptions={{ padding: 0.12 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
            <Controls showInteractive={false} position="bottom-left" />
            <MiniMap pannable zoomable position="bottom-right" className="!rounded-lg !border" />
          </ReactFlow>
        </main>
        <aside className="w-80 shrink-0 border-l">
          <ScrollArea className="h-full">
            <div className="p-4">
              <Inspector node={f.selectedNode} edge={f.selectedEdge} nodes={f.nodes} />
            </div>
          </ScrollArea>
        </aside>
      </div>
    </div>
  )
}
