import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { AudioLines } from 'lucide-react'
import { useSignIn, useSignUp } from '@/api/auth'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function AuthPage({ mode, redirect }: { mode: 'sign-in' | 'sign-up'; redirect?: string }) {
  const signIn = useSignIn()
  const signUp = useSignUp()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const isSignUp = mode === 'sign-up'
  const mutation = isSignUp ? signUp : signIn

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (isSignUp) await signUp.mutateAsync({ email, password, display_name: name })
    else await signIn.mutateAsync({ email, password })
    await navigate({ to: redirect ?? '/agents' })
  }

  return (
    <main className="bg-muted/40 grid min-h-svh place-items-center p-4">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex items-center justify-center gap-2 text-sm font-semibold">
          <AudioLines className="size-5" /> Open Voice Agent Studio
        </div>
        <Card>
          <CardHeader>
            <CardTitle>{isSignUp ? 'Create your account' : 'Sign in'}</CardTitle>
            <CardDescription>
              {isSignUp
                ? 'The first account on this install becomes the workspace owner.'
                : 'Use the email and password you signed up with.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={(e) => void submit(e).catch(() => {})} className="flex flex-col gap-4">
              {isSignUp && (
                <div className="flex flex-col gap-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                  />
                </div>
              )}
              <div className="flex flex-col gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={isSignUp ? 10 : undefined}
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {isSignUp && <p className="text-muted-foreground text-xs">At least 10 characters.</p>}
              </div>
              {mutation.error && (
                <Alert variant="destructive">
                  <AlertDescription>{mutation.error.message}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="text-muted-foreground text-center text-sm">
          {isSignUp ? 'Already have an account? ' : 'New here? '}
          <Link
            to={isSignUp ? '/sign-in' : '/sign-up'}
            className="text-foreground underline underline-offset-4"
          >
            {isSignUp ? 'Sign in' : 'Create an account'}
          </Link>
        </p>
      </div>
    </main>
  )
}
