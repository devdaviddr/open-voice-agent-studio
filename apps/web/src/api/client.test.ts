import { describe, expect, it } from 'vitest'
import { ApiError, unwrap } from './client'

const res = (status: number) => new Response(null, { status })

describe('unwrap', () => {
  it('returns data for a successful response', async () => {
    await expect(unwrap(Promise.resolve({ data: { ok: 1 }, response: res(200) }))).resolves.toEqual({ ok: 1 })
  })

  it('throws the API detail message', async () => {
    const p = unwrap(
      Promise.resolve({ error: { detail: 'Email or password is incorrect.' }, response: res(401) }),
    )
    await expect(p).rejects.toEqual(new ApiError(401, 'Email or password is incorrect.'))
  })

  it('names the field for validation errors', async () => {
    const error = {
      detail: [{ loc: ['body', 'password'], msg: 'String should have at least 10 characters' }],
    }
    await expect(unwrap(Promise.resolve({ error, response: res(422) }))).rejects.toThrow(
      'password: String should have at least 10 characters',
    )
  })
})
