import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { Bot, Copy, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from 'cn'
import type { AgentSummary } from '@/gen/api'
import { agentsQuery, useCreateAgent, useDeleteAgent, useDuplicateAgent, useRenameAgent } from '@/api/agents'
import { PageHeader } from '@/components/layout/app-shell'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const TEMPLATES = [
  {
    id: 'receptionist',
    name: 'Dental receptionist',
    text: 'Books visits, answers clinic questions, handles emergencies.',
  },
  { id: 'blank', name: 'Blank', text: 'Start, one conversation step, End.' },
] as const

const timeAgo = (iso: string) => {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return new Date(iso).toLocaleDateString()
}

export function AgentsPage() {
  const { data: agents } = useSuspenseQuery(agentsQuery)
  const [creating, setCreating] = useState(false)
  const [renaming, setRenaming] = useState<AgentSummary | null>(null)
  const [deleting, setDeleting] = useState<AgentSummary | null>(null)
  const duplicate = useDuplicateAgent()

  return (
    <>
      <PageHeader title="Agents" description="Voice agents in this workspace.">
        <Button onClick={() => setCreating(true)}>
          <Plus className="size-4" /> New agent
        </Button>
      </PageHeader>
      {agents.length === 0 ? (
        <div className="grid place-items-center px-8 py-24 text-center">
          <div className="flex max-w-sm flex-col items-center gap-3">
            <span className="bg-muted grid size-12 place-items-center rounded-xl">
              <Bot className="text-muted-foreground size-6" />
            </span>
            <h2 className="font-medium">No agents yet</h2>
            <p className="text-muted-foreground text-sm">
              Start from the dental receptionist template to see every kind of step, or from a blank agent.
            </p>
            <Button onClick={() => setCreating(true)}>
              <Plus className="size-4" /> New agent
            </Button>
          </div>
        </div>
      ) : (
        <ul className="divide-y px-8">
          {agents.map((a) => (
            <li key={a.id} className="flex items-center gap-4 py-3">
              <Link
                to="/agents/$agentId"
                params={{ agentId: a.id }}
                className="group flex min-w-0 flex-1 items-center gap-3 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="bg-muted grid size-9 shrink-0 place-items-center rounded-lg">
                  <Bot className="text-muted-foreground size-4" />
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium group-hover:underline">{a.name}</span>
                  <span className="text-muted-foreground block truncate text-xs">
                    {a.node_count} nodes · draft rev {a.draft_revision} · edited {timeAgo(a.updated_at)}
                  </span>
                </span>
              </Link>
              <Badge variant={a.live_version ? 'secondary' : 'outline'} className="font-normal">
                {a.live_version ? `live v${a.live_version}` : 'not published'}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={<Button variant="ghost" size="icon-sm" aria-label={`Actions for ${a.name}`} />}
                >
                  <MoreHorizontal className="size-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setRenaming(a)}>
                    <Pencil className="size-4" /> Rename
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() =>
                      duplicate.mutate(a.id, {
                        onSuccess: (c) => toast.success(`Created ${c.name}`),
                        onError: (e) => toast.error(e.message),
                      })
                    }
                  >
                    <Copy className="size-4" /> Duplicate
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem variant="destructive" onClick={() => setDeleting(a)}>
                    <Trash2 className="size-4" /> Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </li>
          ))}
        </ul>
      )}
      <CreateDialog open={creating} onOpenChange={setCreating} />
      <RenameDialog agent={renaming} onClose={() => setRenaming(null)} />
      <DeleteDialog agent={deleting} onClose={() => setDeleting(null)} />
    </>
  )
}

function CreateDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [name, setName] = useState('')
  const [template, setTemplate] = useState<'receptionist' | 'blank'>('receptionist')
  const create = useCreateAgent()
  const navigate = useNavigate()
  async function submit(e: FormEvent) {
    e.preventDefault()
    const agent = await create.mutateAsync({ name: name.trim(), template, description: '' })
    onOpenChange(false)
    setName('')
    await navigate({ to: '/agents/$agentId', params: { agentId: agent.id } })
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form
          onSubmit={(e) => void submit(e).catch((err: Error) => toast.error(err.message))}
          className="flex flex-col gap-4"
        >
          <DialogHeader>
            <DialogTitle>New agent</DialogTitle>
            <DialogDescription>
              Pick a starting point. You can change everything afterwards.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="agent-name">Name</Label>
            <Input
              id="agent-name"
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Reception"
              autoFocus
            />
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-medium">Start from</legend>
            {TEMPLATES.map((t) => (
              <label
                key={t.id}
                className={cn(
                  'flex cursor-pointer gap-3 rounded-lg border p-3 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
                  template === t.id && 'border-primary bg-muted/50',
                )}
              >
                <input
                  type="radio"
                  name="template"
                  className="sr-only"
                  checked={template === t.id}
                  onChange={() => setTemplate(t.id)}
                />
                <span>
                  <span className="block font-medium">{t.name}</span>
                  <span className="text-muted-foreground block text-xs">{t.text}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending || !name.trim()}>
              Create agent
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RenameDialog({ agent, onClose }: { agent: AgentSummary | null; onClose: () => void }) {
  const rename = useRenameAgent()
  const [name, setName] = useState('')
  return (
    <Dialog open={!!agent} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (!agent) return
            rename.mutate(
              { id: agent.id, name: name.trim() },
              { onSuccess: onClose, onError: (err) => toast.error(err.message) },
            )
          }}
          className="flex flex-col gap-4"
        >
          <DialogHeader>
            <DialogTitle>Rename agent</DialogTitle>
          </DialogHeader>
          <Input
            aria-label="Name"
            required
            maxLength={120}
            defaultValue={agent?.name}
            key={agent?.id}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={rename.isPending || !name.trim()}>
              Rename
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DeleteDialog({ agent, onClose }: { agent: AgentSummary | null; onClose: () => void }) {
  const del = useDeleteAgent()
  return (
    <AlertDialog open={!!agent} onOpenChange={(o) => !o && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {agent?.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            This deletes the agent, its versions and its conversations. It cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() =>
              agent &&
              del.mutate(agent, {
                onSuccess: () => {
                  toast.success(`Deleted ${agent.name}`)
                  onClose()
                },
                onError: (e) => toast.error(e.message),
              })
            }
          >
            Delete agent
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
