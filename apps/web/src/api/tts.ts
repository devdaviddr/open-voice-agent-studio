/** Read-aloud (MVP FR-19): synthesise speech with Kokoro through the API. */
export async function synthesize(text: string, voice: { voice_id: string; speed: number }): Promise<Blob> {
  const res = await fetch('/api/v1/tts', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text, voice: voice.voice_id, speed: voice.speed }),
  })
  if (!res.ok) throw new Error(`Text-to-speech failed (${res.status})`)
  return res.blob()
}
