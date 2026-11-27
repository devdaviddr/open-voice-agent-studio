import { useSuspenseQuery, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { meQuery } from '@/api/auth'
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
      </div>
    </>
  )
}
