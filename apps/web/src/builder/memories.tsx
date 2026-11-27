import { useQuery } from '@tanstack/react-query'
import { Brain, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { byCaller, memoriesQuery, useDeleteMemory, useForgetCaller } from '@/api/memories'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useBuilder } from './store'

/** What the agent remembers about each test caller, with delete (MVP FR-16). */
export function MemoriesSheet() {
  const agentId = useBuilder((s) => s.agentId)
  const { data: memories = [] } = useQuery({ ...memoriesQuery(agentId), enabled: !!agentId })
  const del = useDeleteMemory(agentId)
  const forget = useForgetCaller(agentId)
  const groups = byCaller(memories)
  const fail = (e: Error) => toast.error(e.message)
  return (
    <Sheet>
      <SheetTrigger render={<Button variant="outline" size="sm" className="w-full" />}>
        <Brain className="size-3.5" /> Memories ({memories.length})
      </SheetTrigger>
      <SheetContent side="right" className="w-96">
        <SheetHeader>
          <SheetTitle>Memories</SheetTitle>
          <SheetDescription>
            Facts saved after each conversation with a test caller ID. New sessions for the same caller start
            with the latest five.
          </SheetDescription>
        </SheetHeader>
        <ScrollArea className="min-h-0 flex-1 px-4 pb-4">
          {groups.length === 0 && (
            <p className="text-muted-foreground text-sm">
              Nothing yet. Turn memory on, set a test caller ID in the Test panel, chat, then end the session.
            </p>
          )}
          <div className="flex flex-col gap-5">
            {groups.map(([caller, facts]) => (
              <section key={caller} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">{caller}</h3>
                  <Button
                    variant="link"
                    size="xs"
                    onClick={() =>
                      forget.mutate(caller, {
                        onSuccess: () => toast.success(`Forgot everything about ${caller}`),
                        onError: fail,
                      })
                    }
                  >
                    Forget {caller}
                  </Button>
                </div>
                <ul className="flex flex-col gap-1">
                  {facts.map((f) => (
                    <li
                      key={f.id}
                      className="bg-muted flex items-start gap-2 rounded-md px-2.5 py-1.5 text-xs"
                    >
                      <span className="flex-1 leading-relaxed">{f.fact}</span>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        aria-label={`Delete memory: ${f.fact}`}
                        onClick={() => del.mutate(f.id, { onError: fail })}
                      >
                        <Trash2 className="size-3" />
                      </Button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
