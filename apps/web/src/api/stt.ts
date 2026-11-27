import type { components } from '@/gen/api'

type Transcript = components['schemas']['Transcript']

/** A speech-to-text failure with a message fit to show the builder. */
export class SttError extends Error {}

/**
 * Push-to-talk (MVP FR-23): send a recorded clip to Whisper through the API.
 * The body is the raw clip, so this bypasses the JSON client.
 */
export async function transcribe(clip: Blob, language?: string | null): Promise<Transcript> {
  const query = language ? `?language=${encodeURIComponent(language)}` : ''
  let res: Response
  try {
    res = await fetch(`/api/v1/stt${query}`, {
      method: 'POST',
      headers: { 'content-type': clip.type || 'audio/webm' },
      body: clip,
    })
  } catch {
    throw new SttError('The speech-to-text service is not reachable. Type instead.')
  }
  const body = (await res.json().catch(() => ({}))) as Partial<Transcript> & { detail?: unknown }
  if (!res.ok)
    throw new SttError(
      typeof body.detail === 'string' ? body.detail : `Speech-to-text failed (${res.status}).`,
    )
  return body as Transcript
}
