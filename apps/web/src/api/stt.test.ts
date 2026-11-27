import { afterEach, describe, expect, it, vi } from 'vitest'
import { SttError, transcribe } from './stt'

afterEach(() => vi.unstubAllGlobals())

const clip = new Blob(['RIFF'], { type: 'audio/webm;codecs=opus' })

describe('transcribe', () => {
  it('posts the raw clip with its type and the agent language', async () => {
    // MVP AC-21
    const fetch = vi.fn(async () => Response.json({ text: 'hello', language: 'en', duration_ms: 800 }))
    vi.stubGlobal('fetch', fetch)
    expect((await transcribe(clip, 'en')).text).toBe('hello')
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v1/stt?language=en')
    expect(init.headers).toEqual({ 'content-type': 'audio/webm;codecs=opus' })
    expect(init.body).toBe(clip)
  })

  it('surfaces the API message when the provider is down', async () => {
    // MVP AC-21
    vi.stubGlobal('fetch', async () =>
      Response.json({ detail: 'The speech-to-text service is not reachable.' }, { status: 502 }),
    )
    await expect(transcribe(clip)).rejects.toThrow(
      new SttError('The speech-to-text service is not reachable.'),
    )
  })

  it('reports a network failure readably', async () => {
    vi.stubGlobal('fetch', async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(transcribe(clip)).rejects.toBeInstanceOf(SttError)
  })
})
