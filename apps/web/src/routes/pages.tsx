import { useSuspenseQuery, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useState } from 'react'
import { meQuery } from '@/api/auth'
import { llmQuery, useTestLlm, useUpdateLlm } from '@/api/llm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { healthQuery, settingsQuery, useUpdateSettings } from '@/api/workspace'
import { PageHeader } from '@/components/layout/app-shell'
import { SpeakCard } from '@/components/speak-card'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

const SERVICE_LABELS: Record<string, string> = {
  api: 'API',
  db: 'Database',
  runtime: 'Runtime',
  tts: 'Text to speech',
}

export function ServicesPage() {
  const { data, error } = useQuery(healthQuery)
  return (
    <>
      <PageHeader
        title="Services"
        description="Health of each part of the stack. Refreshes every 15 seconds."
      />
      <div className="max-w-2xl p-8">
        <Card>
          <CardContent className="divide-y">
            {error && (
              <p className="text-destructive py-3 text-sm">The API is not reachable: {error.message}</p>
            )}
            {data &&
              Object.entries(data).map(([name, s]) => (
                <div key={name} className="flex items-center justify-between py-3">
                  <span className="text-sm font-medium">{SERVICE_LABELS[name] ?? name}</span>
                  <Badge variant={s.status === 'ok' ? 'secondary' : 'destructive'}>
                    {s.status}
                    {s.version ? ` · ${s.version}` : ''}
                  </Badge>
                </div>
              ))}
          </CardContent>
        </Card>
      </div>
    </>
  )
}

function LlmCard({ isOwner }: { isOwner: boolean }) {
  const { data: llm } = useSuspenseQuery(llmQuery)
  const update = useUpdateLlm()
  const test = useTestLlm()
  const [baseUrl, setBaseUrl] = useState(llm.base_url)
  const [model, setModel] = useState(llm.default_model)
  const [effort, setEffort] = useState(llm.reasoning_effort ?? 'off')
  const [apiKey, setApiKey] = useState('')
  const save = () =>
    update.mutate(
      {
        base_url: baseUrl.trim(),
        default_model: model.trim(),
        reasoning_effort: effort === 'off' ? null : effort,
        api_key: apiKey ? apiKey : null,
      },
      {
        onSuccess: () => {
          setApiKey('')
          toast.success('LLM settings saved')
        },
        onError: (e) => toast.error(e.message),
      },
    )
  return (
    <Card>
      <CardHeader>
        <CardTitle>Language model</CardTitle>
        <CardDescription>
          Any OpenAI-compatible endpoint: Ollama, vLLM, llama.cpp or a cloud provider.
          {!llm.configured && ' Using the server default until you save.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="llm-url">Endpoint URL</Label>
          <Input
            id="llm-url"
            disabled={!isOwner}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://host.docker.internal:11434/v1"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="llm-model">Default model</Label>
            <Input
              id="llm-model"
              disabled={!isOwner}
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="llm-effort">Reasoning effort</Label>
            <Select value={effort} onValueChange={(v) => v && setEffort(v as string)} disabled={!isOwner}>
              <SelectTrigger id="llm-effort" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">none (fastest; turns thinking off)</SelectItem>
                <SelectItem value="low">low</SelectItem>
                <SelectItem value="medium">medium</SelectItem>
                <SelectItem value="high">high</SelectItem>
                <SelectItem value="off">not sent</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="llm-key">API key</Label>
          <Input
            id="llm-key"
            type="password"
            autoComplete="off"
            disabled={!isOwner}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={llm.api_key.set ? 'Saved. Type to replace it.' : 'Not needed for local models'}
          />
          <p className="text-muted-foreground text-xs">Stored encrypted. It is never shown again.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={!isOwner || update.isPending} onClick={save}>
            Save
          </Button>
          <Button variant="outline" disabled={test.isPending} onClick={() => test.mutate()}>
            {test.isPending ? 'Testing…' : 'Test connection'}
          </Button>
          {test.data && (
            <span
              className={
                test.data.ok ? 'text-sm text-emerald-600 dark:text-emerald-400' : 'text-destructive text-sm'
              }
            >
              {test.data.ok
                ? `Connected. ${test.data.models?.length ?? 0} models available.`
                : test.data.error}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function PlaygroundPage() {
  return (
    <>
      <PageHeader title="Voice playground" description="Try the Kokoro voices that agents speak with." />
      <div className="max-w-2xl p-8">
        <SpeakCard />
      </div>
    </>
  )
}

export function SettingsPage() {
  const { data: me } = useSuspenseQuery(meQuery)
  const { data: settings } = useSuspenseQuery(settingsQuery)
  const update = useUpdateSettings()
  const isOwner = me?.role === 'owner'
  return (
    <>
      <PageHeader title="Settings" description={settings.name} />
      <div className="flex max-w-2xl flex-col gap-6 p-8">
        <Card>
          <CardHeader>
            <CardTitle>Sign-up</CardTitle>
            <CardDescription>
              {isOwner
                ? 'Control who can create an account on this install.'
                : 'Only the workspace owner can change this.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-4">
            <Label htmlFor="open-signup" className="flex flex-col items-start gap-1">
              <span>Allow new sign-ups</span>
              <span className="text-muted-foreground text-xs font-normal">
                New accounts join this workspace as members.
              </span>
            </Label>
            <Switch
              id="open-signup"
              checked={settings.open_signup}
              disabled={!isOwner || update.isPending}
              onCheckedChange={(open_signup) =>
                update.mutate(
                  { open_signup },
                  {
                    onSuccess: () => toast.success(open_signup ? 'Sign-up opened' : 'Sign-up closed'),
                    onError: (e) => toast.error(e.message),
                  },
                )
              }
            />
          </CardContent>
        </Card>
        <LlmCard isOwner={isOwner} />
      </div>
    </>
  )
}
