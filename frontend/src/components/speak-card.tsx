import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Textarea } from '@/components/ui/textarea'

type VoiceList = { default: string; voices: string[] }

export function SpeakCard() {
  const [voices, setVoices] = useState<string[]>([])
  const [voice, setVoice] = useState('af_heart')
  const [speed, setSpeed] = useState(1)
  const [text, setText] = useState('Hello! I am a voice agent built with Open Voice Agent Studio.')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    fetch('/api/voices')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: VoiceList) => {
        setVoices(data.voices)
        setVoice(data.default)
      })
      .catch((e) => setError(`Could not load voices: ${e.message}`))
  }, [])

  useEffect(() => {
    if (audioUrl) audioRef.current?.play()
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  async function speak() {
    setBusy(true)
    setError(null)
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text, voice, speed }),
      })
      if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`)
      setAudioUrl(URL.createObjectURL(await res.blob()))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Text to speech</CardTitle>
        <CardDescription>Kokoro-82M, running locally in the tts service.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="tts-text">Text</Label>
          <Textarea
            id="tts-text"
            rows={4}
            maxLength={5000}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label>Voice</Label>
            <Select value={voice} onValueChange={(v) => v && setVoice(v)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {voices.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label>Speed: {speed.toFixed(1)}×</Label>
            <Slider
              min={0.5}
              max={2}
              step={0.1}
              value={speed}
              onValueChange={(v) => setSpeed(Array.isArray(v) ? v[0] : v)}
            />
          </div>
        </div>
        {error && <p className="text-destructive text-sm">{error}</p>}
        <div className="flex items-center gap-3">
          <Button onClick={speak} disabled={busy || !text.trim() || voices.length === 0}>
            {busy ? 'Generating…' : 'Speak'}
          </Button>
          {audioUrl && <audio ref={audioRef} src={audioUrl} controls className="h-9" />}
        </div>
      </CardContent>
    </Card>
  )
}
