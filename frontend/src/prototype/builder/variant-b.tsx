// PROTOTYPE — Variant B: canvas-first, everything floats over a full-bleed canvas. Not production code.
import { Background, BackgroundVariant, Panel, ReactFlow } from '@xyflow/react'
import { Command, History, Play, TriangleAlert, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { agent, type NodeKind } from './data'
import { edgeTypes, kinds, nodeTypes } from './flow'
import { Inspector } from './inspector'
import { useFlow } from './use-flow'

export const name = 'Canvas-first, floating'

const floating = 'bg-background/85 rounded-xl border shadow-lg backdrop-blur'

export function VariantB() {
  const f = useFlow({ selected: 'collect' })
  const showInspector = f.selectedNode || f.selectedEdge
  return (
    <div className="bg-muted/40 h-svh">
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
        fitViewOptions={{ padding: 0.18 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Lines} gap={32} className="opacity-40" />

        <Panel position="top-left" className={`${floating} flex items-center gap-3 px-3 py-2`}>
          <span className="bg-primary text-primary-foreground grid size-7 place-items-center rounded-lg text-xs font-semibold">BS</span>
          <div className="leading-tight">
            <div className="text-sm font-medium">{agent.name}</div>
            <div className="text-muted-foreground text-[11px]">
              Draft rev {agent.draftRevision} · live v{agent.live}
            </div>
          </div>
          <Button variant="ghost" size="icon-sm" title="Versions">
            <History className="size-4" />
          </Button>
        </Panel>

        <Panel position="top-right" className={`${floating} flex items-center gap-1 p-1.5`}>
          {f.issues > 0 && (
            <Button variant="ghost" size="sm" className="gap-1.5 text-amber-600 dark:text-amber-400">
              <TriangleAlert className="size-4" /> {f.issues}
            </Button>
          )}
          <Button variant="ghost" size="sm" className="gap-1.5">
            <Play className="size-3.5" /> Talk to it
          </Button>
          <Button size="sm" className="rounded-lg">
            Publish
          </Button>
        </Panel>

        <Panel position="center-left" className={`${floating} flex flex-col gap-0.5 p-1.5`}>
          {(Object.keys(kinds) as NodeKind[]).map((k) => {
            const m = kinds[k]
            return (
              <button key={k} title={`${m.name}: ${m.hint}`} onClick={() => f.addNode(k)} className="hover:bg-muted grid size-9 place-items-center rounded-lg">
                <span className={`grid size-6 place-items-center rounded-md ${m.tint}`}>
                  <m.icon className="size-3.5" />
                </span>
              </button>
            )
          })}
        </Panel>

        <Panel position="bottom-left" className={`${floating} text-muted-foreground flex items-center gap-2 px-3 py-1.5 text-xs`}>
          <Command className="size-3.5" /> K to add a node · drag from a handle to connect
        </Panel>

        {showInspector && (
          <Panel position="top-right" className={`${floating} !top-16 w-80 p-4`}>
            <Button variant="ghost" size="icon-xs" className="absolute top-2 right-2" title="Close">
              <X className="size-3.5" />
            </Button>
            <Inspector node={f.selectedNode} edge={f.selectedEdge} nodes={f.nodes} />
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}
