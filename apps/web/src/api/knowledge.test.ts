// @vitest-environment node
// Node's own File, FormData and Request, as in a browser (jsdom's File is not accepted by them).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => vi.stubGlobal('window', { location: { origin: 'http://studio.test' } }))
afterEach(() => vi.unstubAllGlobals())

describe('uploadKnowledge', () => {
  it('posts the file as multipart form data', async () => {
    // MVP AC-14
    const seen: Request[] = []
    vi.stubGlobal('fetch', async (req: Request) => {
      seen.push(req)
      return Response.json({ id: '1', name: 'handbook.md', status: 'pending' }, { status: 201 })
    })
    const { uploadKnowledge } = await import('./knowledge')
    const file = new File(['# Prices'], 'handbook.md', { type: 'text/markdown' })
    expect((await uploadKnowledge(file)).name).toBe('handbook.md')
    const req = seen[0]
    expect(req.method).toBe('POST')
    expect(new URL(req.url).pathname).toBe('/api/v1/knowledge')
    expect(req.headers.get('content-type')).toMatch(/^multipart\/form-data; boundary=/)
    const sent = (await req.formData()).get('file') as File
    expect(sent.name).toBe('handbook.md')
    expect(await sent.text()).toBe('# Prices')
  })

  it('surfaces the API message on failure', async () => {
    vi.stubGlobal('fetch', async () =>
      Response.json({ detail: 'Files must be 20 MB or smaller.' }, { status: 413 }),
    )
    const { uploadKnowledge } = await import('./knowledge')
    await expect(uploadKnowledge(new File(['x'], 'big.pdf'))).rejects.toThrow('20 MB')
  })
})
