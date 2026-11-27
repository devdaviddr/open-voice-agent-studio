import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { CircleStop, Loader2, Mic, Play, RotateCcw, Send, Square, Volume2, VolumeX, X } from 'lucide-react'
import { cn } from 'cn'
import { NotRunnableError, startSession, type SessionTarget } from '@/api/sessions'
import { SttError, transcribe as speechToText } from '@/api/stt'
import { versionsQuery } from '@/api/versions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useBuilder } from './store'
import type { ActivityEvent } from './activity'

/** Push-to-talk clips stop on their own after this long (MVP FR-23). */
const MAX_CLIP_MS = 60_000

const track = (e: ActivityEvent) => useBuilder.getState().track(e)

type Voice = { voice_id: string; speed: number }
type Item =
  | { kind: 'agent'; text: string; nodeId?: string; ms?: number; streaming?: boolean }
  | { kind: 'user'; text: string; voice?: boolean }
  | { kind: 'event'; text: string; tone?: 'info' | 'warn' | 'error' }

type Status = 'idle' | 'connecting' | 'live' | 'ended'

const label = (id: string) => {
  const n = useBuilder.getState().nodes.find((x) => x.id === id)
  return n && 'label' in n.data ? (n.data as { label: string }).label : (n?.type ?? id)
}

function describe(e: Record<string, unknown>): Item | null {
  switch (e.type) {
    case 'node_enter':
      return { kind: 'event', text: `→ ${label(String(e.node_id))}` }
    case 'edge': {
      const c = e.condition as { kind: string; text?: string; expr?: string } | null
      const why = !c ? 'always' : c.kind === 'llm' ? `“${c.text}”` : c.kind === 'cel' ? c.expr : 'else'
      return { kind: 'event', text: `edge fired: ${why}` }
    }
    case 'variable_set':
      return { kind: 'event', text: `set ${e.name} = ${JSON.stringify(e.value)}` }
    case 'variable_rejected':
      return {
        kind: 'event',
        tone: 'warn',
        text: `rejected ${e.name} = ${JSON.stringify(e.value)} (${e.reason})`,
      }
    case 'tool_call':
      return { kind: 'event', text: `tool ${e.name}(${JSON.stringify(e.arguments)})` }
    case 'knowledge':
      return { kind: 'event', text: `knowledge “${e.query}”: ${(e.results as unknown[]).length} results` }
    case 'memory':
      return { kind: 'event', text: `memory recalled ${(e.recalled as unknown[]).length} facts` }
    case 'summary':
      return { kind: 'event', text: `summarised ${e.dropped_messages} older messages` }
    case 'error':
      return { kind: 'event', tone: 'error', text: String(e.message) }
    default:
      return null
  }
}

export function TestConsole({ agentId, onClose }: { agentId: string; onClose: () => void }) {
  const { data: versions } = useQuery(versionsQuery(agentId))
  const saveState = useBuilder((s) => s.saveState)
  const issues = useBuilder((s) => s.issues.length)
  const [target, setTarget] = useState<string>('draft')
  const [endUser, setEndUser] = useState('')
  const [readAloud, setReadAloud] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [items, setItems] = useState<Item[]>([])
  const [text, setText] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [mic, setMic] = useState<'idle' | 'recording' | 'transcribing'>('idle')
  const [clipMs, setClipMs] = useState(0)
  const recorder = useRef<{
    mr: MediaRecorder
    stream: MediaStream
    timer: number
    cancelled: boolean
  } | null>(null)
  const language = useBuilder((s) => s.meta.settings?.language)
  const ws = useRef<WebSocket | null>(null)
  const audio = useRef<{ queue: Promise<void>; current: HTMLAudioElement | null }>({
    queue: Promise.resolve(),
    current: null,
  })
  const readAloudRef = useRef(readAloud)
  readAloudRef.current = readAloud
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [items])
  useEffect(() => {
    return () => stop()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function speak(text: string, voice: Voice) {
    audio.current.queue = audio.current.queue.then(async () => {
      if (!readAloudRef.current) return
      const res = await fetch('/api/v1/tts', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, voice: voice.voice_id, speed: voice.speed }),
      })
      if (!res.ok) return
      const url = URL.createObjectURL(await res.blob())
      const el = new Audio(url)
      audio.current.current = el
      track({ type: 'local:audio', playing: true })
      await el.play().catch(() => {})
      await new Promise<void>((done) => {
        el.onended = () => done()
        el.onpause = () => done()
      })
      track({ type: 'local:audio', playing: false })
      URL.revokeObjectURL(url)
    })
  }

  function onEvent(e: Record<string, unknown>) {
    switch (e.type) {
      case 'node_enter':
        track({ type: 'node_enter', node_id: String(e.node_id) })
        break
      case 'edge':
        track({ type: 'edge', edge_id: String(e.edge_id) })
        break
      case 'token':
      case 'assistant_message':
      case 'tool_call':
      case 'knowledge':
      case 'memory':
      case 'ended':
        track({ type: e.type })
        break
    }
    if (e.type === 'token') {
      setItems((xs) => {
        const last = xs.at(-1)
        if (last?.kind === 'agent' && last.streaming)
          return [...xs.slice(0, -1), { ...last, text: last.text + String(e.text) }]
        return [...xs, { kind: 'agent', text: String(e.text), streaming: true }]
      })
      return
    }
    if (e.type === 'assistant_message') {
      const llm = e.llm as { total_ms: number } | null
      const item: Item = { kind: 'agent', text: String(e.text), nodeId: String(e.node_id), ms: llm?.total_ms }
      setItems((xs) =>
        xs.at(-1)?.kind === 'agent' && (xs.at(-1) as { streaming?: boolean }).streaming
          ? [...xs.slice(0, -1), item]
          : [...xs, item],
      )
      speak(String(e.text), e.voice as Voice)
      return
    }
    if (e.type === 'ended') {
      setItems((xs) => [...xs, { kind: 'event', text: `Session ended (${e.outcome ?? 'ended'})` }])
      setStatus('ended')
      return
    }
    const item = describe(e)
    if (item) setItems((xs) => [...xs, item])
  }

  async function start() {
    stop()
    setItems([])
    setStatus('connecting')
    try {
      const t: SessionTarget = target === 'draft' || target === 'live' ? target : Number(target)
      const s = await startSession({ agent_id: agentId, target: t, end_user_id: endUser.trim() || null })
      setSessionId(s.session_id)
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const socket = new WebSocket(`${proto}://${location.host}${s.stream_url}`)
      ws.current = socket
      socket.onopen = () => setStatus('live')
      socket.onmessage = (m) => onEvent(JSON.parse(m.data as string))
      socket.onclose = (ev) => {
        setStatus('ended')
        stopRecording(true)
        track({ type: 'local:reset' })
        if (ev.code >= 4000)
          setItems((xs) => [...xs, { kind: 'event', tone: 'error', text: ev.reason || 'Connection refused' }])
      }
    } catch (e) {
      setStatus('idle')
      const message =
        e instanceof NotRunnableError ? `${e.message} (${e.issues.length} problems)` : (e as Error).message
      setItems([{ kind: 'event', tone: 'error', text: message }])
    }
  }

  function stop() {
    if (ws.current && ws.current.readyState === WebSocket.OPEN)
      ws.current.send(JSON.stringify({ type: 'end' }))
    ws.current?.close()
    ws.current = null
    audio.current.current?.pause()
    audio.current.queue = Promise.resolve()
    stopRecording(true)
    track({ type: 'local:reset' })
  }

  function sendText(t: string, voice = false) {
    if (!t || !ws.current || ws.current.readyState !== WebSocket.OPEN) return false
    audio.current.current?.pause()
    ws.current.send(JSON.stringify({ type: 'user_message', text: t }))
    setItems((xs) => [...xs, { kind: 'user', text: t, voice }])
    track({ type: 'local:user_sent' })
    return true
  }

  function send(e: FormEvent) {
    e.preventDefault()
    if (sendText(text.trim())) setText('')
  }

  const fail = (text: string, tone: 'warn' | 'error' = 'error') =>
    setItems((xs) => [...xs, { kind: 'event', tone, text }])

  // Push-to-talk (MVP FR-23): record a clip, transcribe it with Whisper, send it as the caller.
  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      fail('This browser cannot record audio. Type instead.')
      return
    }
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      fail('Microphone access was blocked. Allow it for this site and try again, or type instead.')
      return
    }
    const mr = new MediaRecorder(stream)
    const chunks: Blob[] = []
    const started = Date.now()
    const timer = window.setInterval(() => {
      const ms = Date.now() - started
      setClipMs(ms)
      if (ms >= MAX_CLIP_MS) stopRecording()
    }, 200)
    const rec = { mr, stream, timer, cancelled: false }
    recorder.current = rec
    mr.ondataavailable = (ev) => ev.data.size && chunks.push(ev.data)
    mr.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      track({ type: 'local:listening', on: false })
      if (!rec.cancelled) void transcribe(new Blob(chunks, { type: mr.mimeType || 'audio/webm' }))
      else setMic('idle')
    }
    mr.start()
    setClipMs(0)
    setMic('recording')
    track({ type: 'local:listening', on: true })
  }

  function stopRecording(cancel = false) {
    const rec = recorder.current
    if (!rec) return
    recorder.current = null
    window.clearInterval(rec.timer)
    rec.cancelled = cancel
    if (rec.mr.state !== 'inactive') rec.mr.stop()
    else rec.stream.getTracks().forEach((t) => t.stop())
    if (cancel) setMic('idle')
  }

  async function transcribe(clip: Blob) {
    setMic('transcribing')
    try {
      if (!clip.size) return fail('Nothing was recorded. Try again.', 'warn')
      const heard = (await speechToText(clip, language)).text.trim()
      if (!heard) return fail('Didn’t catch that. Try again, a little closer to the mic.', 'warn')
      if (!sendText(heard, true)) fail('The session ended before the recording was sent.', 'warn')
    } catch (e) {
      fail(e instanceof SttError ? e.message : 'Speech-to-text failed. Type instead.')
    } finally {
      setMic('idle')
    }
  }

  const draftNotReady = target === 'draft' && (saveState !== 'saved' || issues > 0)
  const busy =
    items.at(-1)?.kind === 'user' ||
    (items.at(-1)?.kind === 'agent' && (items.at(-1) as { streaming?: boolean }).streaming)

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <span className="text-sm font-medium">Test</span>
        <Badge variant={status === 'live' ? 'default' : 'outline'} className="font-normal">
          {status === 'live' && <span className="mr-1 size-1.5 animate-pulse rounded-full bg-emerald-400" />}
          {status}
        </Badge>
        <Button
          variant="ghost"
          size="icon-sm"
          className="ml-auto"
          aria-label={readAloud ? 'Stop reading aloud' : 'Read replies aloud'}
          onClick={() => setReadAloud((r) => !r)}
        >
          {readAloud ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Close test console"
          onClick={() => {
            stop()
            onClose()
          }}
        >
          <X className="size-4" />
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-2 border-b px-4 py-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="console-target" className="text-muted-foreground text-xs">
            Run
          </Label>
          <Select value={target} onValueChange={(v) => v && setTarget(v as string)}>
            <SelectTrigger id="console-target" className="h-8 w-full text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="draft">Draft</SelectItem>
              {versions?.map((v) => (
                <SelectItem key={v.number} value={String(v.number)}>
                  v{v.number}
                  {v.is_live ? ' (live)' : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="console-user" className="text-muted-foreground text-xs">
            Test caller ID
          </Label>
          <Input
            id="console-user"
            className="h-8 text-xs"
            placeholder="optional, e.g. ana"
            value={endUser}
            onChange={(e) => setEndUser(e.target.value)}
          />
        </div>
        <div className="col-span-2 flex gap-2">
          {status === 'live' || status === 'connecting' ? (
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={() => {
                stop()
                setStatus('ended')
              }}
            >
              <CircleStop className="size-3.5" /> End session
            </Button>
          ) : (
            <Button
              size="sm"
              className="flex-1"
              disabled={draftNotReady}
              onClick={() => void start()}
              title={draftNotReady ? 'Save and fix the draft first' : undefined}
            >
              {status === 'ended' ? <RotateCcw className="size-3.5" /> : <Play className="size-3.5" />}
              {status === 'ended' ? 'New session' : 'Start session'}
            </Button>
          )}
        </div>
        {draftNotReady && status === 'idle' && (
          <p className="text-muted-foreground col-span-2 text-xs">
            {issues > 0 ? 'Fix the problems in the draft to test it.' : 'Saving the draft…'}
          </p>
        )}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-2 p-4" aria-live="polite">
          {items.length === 0 && status === 'idle' && (
            <p className="text-muted-foreground text-sm">
              Start a session, then type or press the mic to talk as the caller. The canvas shows what the
              agent is doing.
            </p>
          )}
          {items.map((item, i) =>
            item.kind === 'event' ? (
              <p
                key={i}
                className={cn(
                  'font-mono text-[11px]',
                  item.tone === 'error'
                    ? 'text-destructive'
                    : item.tone === 'warn'
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-muted-foreground',
                )}
              >
                {item.text}
              </p>
            ) : (
              <div
                key={i}
                className={cn(
                  'max-w-[88%] rounded-2xl px-3 py-2 text-sm',
                  item.kind === 'agent'
                    ? 'bg-muted self-start rounded-bl-sm'
                    : 'bg-primary text-primary-foreground self-end rounded-br-sm',
                )}
              >
                {item.kind === 'user' && item.voice && (
                  <Mic className="mr-1 inline size-3 align-[-1px] opacity-70" aria-label="Spoken" />
                )}
                {item.text}
                {item.kind === 'agent' && item.ms !== undefined && (
                  <div className="text-muted-foreground mt-1 text-[10px] tabular-nums">{item.ms} ms</div>
                )}
              </div>
            ),
          )}
          {busy && status === 'live' && <p className="text-muted-foreground text-xs">Agent is thinking…</p>}
          <div ref={bottom} />
        </div>
      </ScrollArea>
      <form onSubmit={send} className="flex gap-2 border-t p-3">
        <Button
          type="button"
          size="icon"
          variant={mic === 'recording' ? 'destructive' : 'outline'}
          aria-label={mic === 'recording' ? 'Stop and send recording' : 'Talk as the caller'}
          aria-pressed={mic === 'recording'}
          title={mic === 'recording' ? 'Stop and send' : 'Push to talk'}
          disabled={status !== 'live' || mic === 'transcribing'}
          onClick={() => (mic === 'recording' ? stopRecording() : void startRecording())}
        >
          {mic === 'recording' ? (
            <Square className="size-3.5 fill-current" />
          ) : mic === 'transcribing' ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Mic className="size-4" />
          )}
        </Button>
        {mic === 'idle' ? (
          <Input
            aria-label="Message as the caller"
            placeholder={status === 'live' ? 'Type or press the mic…' : 'Start a session first'}
            disabled={status !== 'live'}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        ) : (
          <div
            className="border-input text-muted-foreground flex h-9 flex-1 items-center gap-2 rounded-md border px-3 text-sm"
            role="status"
          >
            {mic === 'recording' ? (
              <>
                <span className="size-2 animate-pulse rounded-full bg-rose-500" aria-hidden />
                Listening… {Math.floor(clipMs / 1000)}s
                <Button
                  type="button"
                  variant="link"
                  size="xs"
                  className="ml-auto"
                  onClick={() => stopRecording(true)}
                >
                  Cancel
                </Button>
              </>
            ) : (
              'Transcribing…'
            )}
          </div>
        )}
        <Button type="submit" size="icon" aria-label="Send" disabled={status !== 'live' || !text.trim()}>
          <Send className="size-4" />
        </Button>
      </form>
      {sessionId && (
        <p className="text-muted-foreground border-t px-4 py-2 text-[11px]">
          Saved to{' '}
          <Link to="/sessions/$sessionId" params={{ sessionId }} className="underline underline-offset-2">
            Sessions
          </Link>
        </p>
      )}
    </div>
  )
}
