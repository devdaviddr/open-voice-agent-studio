import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, FileText, Loader2, RotateCcw, Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from 'cn'
import {
  KNOWLEDGE_ACCEPT,
  KNOWLEDGE_MAX_BYTES,
  knowledgeQuery,
  useDeleteKnowledge,
  useReindexKnowledge,
  useUploadKnowledge,
  type KnowledgeSource,
} from '@/api/knowledge'
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

const size = (n: number) =>
  n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`

export function StatusBadge({ source }: { source: KnowledgeSource }) {
  if (source.status === 'ready') return <Badge variant="secondary">ready</Badge>
  if (source.status === 'failed') return <Badge variant="destructive">failed</Badge>
  return (
    <Badge variant="outline" className="gap-1">
      <Loader2 className="size-3 animate-spin" /> {source.status}
    </Badge>
  )
}

export function KnowledgePage() {
  const { data: sources = [] } = useQuery(knowledgeQuery)
  const upload = useUploadKnowledge()
  const reindex = useReindexKnowledge()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [deleting, setDeleting] = useState<KnowledgeSource | null>(null)

  function add(files: FileList | null) {
    for (const file of Array.from(files ?? [])) {
      if (file.size > KNOWLEDGE_MAX_BYTES) {
        toast.error(`${file.name} is larger than 20 MB.`)
        continue
      }
      upload.mutate(file, {
        onSuccess: () => toast.success(`Uploaded ${file.name}; indexing…`),
        onError: (e) => toast.error(`${file.name}: ${e.message}`),
      })
    }
  }

  return (
    <>
      <PageHeader
        title="Knowledge"
        description="Documents your agents can answer from. Attach them to an agent in its settings."
      >
        <Button onClick={() => input.current?.click()} disabled={upload.isPending}>
          {upload.isPending ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
          Upload
        </Button>
        <input
          ref={input}
          type="file"
          multiple
          accept={KNOWLEDGE_ACCEPT}
          className="hidden"
          aria-label="Choose files to upload"
          onChange={(e) => {
            add(e.target.files)
            e.target.value = ''
          }}
        />
      </PageHeader>
      <div className="flex flex-col gap-4 px-8 py-6">
        <div
          role="region"
          aria-label="Drop files to upload"
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            add(e.dataTransfer.files)
          }}
          className={cn(
            'text-muted-foreground flex flex-col items-center gap-2 rounded-xl border border-dashed px-6 py-8 text-center text-sm transition-colors',
            dragging && 'border-primary bg-muted/50',
          )}
        >
          <BookOpen className="size-6" />
          <p>
            Drop Markdown, text or PDF files here (up to 20 MB each). They are split into passages and indexed
            on this server; nothing leaves it.
          </p>
        </div>
        {sources.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-muted-foreground text-left text-xs">
                <tr className="border-b">
                  <th className="py-2 font-medium">Document</th>
                  <th className="py-2 font-medium">Status</th>
                  <th className="py-2 text-right font-medium">Passages</th>
                  <th className="py-2 text-right font-medium">Size</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {sources.map((s) => (
                  <tr key={s.id} className="hover:bg-muted/50 align-top">
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <FileText className="text-muted-foreground size-4 shrink-0" />
                        <span className="font-medium">{s.name}</span>
                      </div>
                      {s.error && <p className="text-destructive mt-1 pl-6 text-xs">{s.error}</p>}
                    </td>
                    <td className="py-2">
                      <StatusBadge source={s} />
                    </td>
                    <td className="py-2 text-right tabular-nums">{s.status === 'ready' ? s.chunks : '—'}</td>
                    <td className="text-muted-foreground py-2 text-right tabular-nums">{size(s.bytes)}</td>
                    <td className="py-2 text-right whitespace-nowrap">
                      {s.status === 'failed' && (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Index ${s.name} again`}
                          onClick={() => reindex.mutate(s.id, { onError: (e) => toast.error(e.message) })}
                        >
                          <RotateCcw className="size-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Delete ${s.name}`}
                        onClick={() => setDeleting(s)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <DeleteDialog source={deleting} onClose={() => setDeleting(null)} />
    </>
  )
}

function DeleteDialog({ source, onClose }: { source: KnowledgeSource | null; onClose: () => void }) {
  const del = useDeleteKnowledge()
  return (
    <AlertDialog open={!!source} onOpenChange={(o) => !o && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {source?.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            Agents that use it will show a problem until you detach it. Published versions that use it keep
            it, so it cannot be deleted while one does.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() =>
              source &&
              del.mutate(source.id, {
                onSuccess: () => {
                  toast.success(`Deleted ${source.name}`)
                  onClose()
                },
                onError: (e) => {
                  toast.error(e.message)
                  onClose()
                },
              })
            }
          >
            Delete document
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
