// PROTOTYPE — Variant C: build and test side by side (canvas · console/inspect/versions). Not production code.
import { Background, BackgroundVariant, Controls, ReactFlow } from '@xyflow/react'
import { Mic, PhoneOff } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from 'cn'
import { agent, transcript, versions } from './data'
import { edgeTypes, nodeTypes } from './flow'
import { Inspector } from './inspector'
import { useFlow } from './use-flow'

export const name = 'Build + test side by side'

const envs = ['Draft', 'v3 · live', 'v2 · staging']

export function VariantC() {
  const f = useFlow({ active: 'confirm' })
  return (
    <div className="bg-background flex h-svh flex-col">
      <header className="flex h-11 shrink-0 items-center gap-4 border-b px-4">
        <span className="text-sm font-semibold">{agent.name}</span>
        <div className="bg-muted flex rounded-lg p-0.5 text-xs">
          {envs.map((e, i) => (
            <button key={e} className={cn('rounded-md px-2.5 py-1', i === 0 ? 'bg-background shadow-xs' : 'text-muted-foreground')}>
              {e}
            </button>
          ))}
        </div>
        <Button size="sm" className="ml-auto">
          Publish draft
        </Button>
      </header>
      <div className="flex min-h-0 flex-1">
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
            fitViewOptions={{ padding: 0.1 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </main>
        <aside className="flex w-[400px] shrink-0 flex-col border-l">
          <Tabs defaultValue="test" className="flex min-h-0 flex-1 flex-col gap-0">
            <TabsList className="m-3 mb-0 grid grid-cols-3">
              <TabsTrigger value="test">Test</TabsTrigger>
              <TabsTrigger value="inspect">Inspect</TabsTrigger>
              <TabsTrigger value="versions">Versions</TabsTrigger>
            </TabsList>

            <TabsContent value="test" className="flex min-h-0 flex-1 flex-col">
              <div className="text-muted-foreground flex items-center gap-2 px-4 py-2 text-xs">
                <span className="size-2 animate-pulse rounded-full bg-emerald-500" /> Live · draft rev {agent.draftRevision} · 00:42
                <Badge variant="outline" className="ml-auto font-mono font-normal">
                  p50 655 ms
                </Badge>
              </div>
              <ScrollArea className="min-h-0 flex-1">
                <div className="flex flex-col gap-2 px-4 pb-4">
                  {transcript.map((t, i) =>
                    t.who === 'event' ? (
                      <div key={i} className="text-muted-foreground flex items-start gap-2 font-mono text-[11px]">
                        <span className="mt-1.5 size-1 shrink-0 rounded-full bg-current" />
                        <span className="flex-1">{t.text}</span>
                        {t.ms && <span className="tabular-nums">{t.ms}ms</span>}
                      </div>
                    ) : (
                      <div key={i} className={cn('max-w-[85%] rounded-2xl px-3 py-2 text-sm', t.who === 'agent' ? 'bg-muted self-start rounded-bl-sm' : 'bg-primary text-primary-foreground self-end rounded-br-sm')}>
                        {t.text}
                        {t.ms && <div className="text-muted-foreground mt-1 text-[10px] tabular-nums">voice-to-voice {t.ms} ms</div>}
                      </div>
                    ),
                  )}
                </div>
              </ScrollArea>
              <div className="flex items-center justify-center gap-3 border-t p-3">
                <Button size="icon-lg" className="size-12 rounded-full" title="Mute">
                  <Mic className="size-5" />
                </Button>
                <Button size="icon-lg" variant="destructive" className="size-12 rounded-full" title="Hang up">
                  <PhoneOff className="size-5" />
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="inspect" className="min-h-0 flex-1 overflow-auto p-4">
              <Inspector node={f.selectedNode} edge={f.selectedEdge} nodes={f.nodes} />
            </TabsContent>

            <TabsContent value="versions" className="min-h-0 flex-1 overflow-auto p-4">
              <ol className="relative flex flex-col gap-5 border-l pl-4">
                {versions.map((v) => (
                  <li key={v.n}>
                    <span className="bg-background absolute -left-[5px] mt-1.5 size-2.5 rounded-full border-2" />
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">v{v.n}</span>
                      {v.env.map((e) => (
                        <Badge key={e} variant={e === 'live' ? 'default' : 'secondary'} className="text-[10px]">
                          {e}
                        </Badge>
                      ))}
                      <span className="text-muted-foreground ml-auto text-xs">{v.when}</span>
                    </div>
                    <div className="text-muted-foreground text-xs">{v.message}</div>
                    <div className="mt-1.5 flex gap-1">
                      <Button variant="outline" size="xs">
                        Diff
                      </Button>
                      <Button variant="ghost" size="xs">
                        Make live
                      </Button>
                    </div>
                  </li>
                ))}
              </ol>
            </TabsContent>
          </Tabs>
        </aside>
      </div>
    </div>
  )
}
