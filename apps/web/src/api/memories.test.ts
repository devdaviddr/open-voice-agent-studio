import { describe, expect, it } from 'vitest'
import { byCaller, type Memory } from './memories'

const m = (id: string, end_user_id: string, fact: string): Memory => ({
  id,
  end_user_id,
  fact,
  session_id: null,
  created_at: '2026-11-28T00:00:00Z',
})

describe('byCaller', () => {
  it('groups memories by end user in first-seen order', () => {
    // MVP AC-15
    const groups = byCaller([
      m('1', 'ana', 'Dog Rex'),
      m('2', 'bob', 'Likes jazz'),
      m('3', 'ana', 'Mornings'),
    ])
    expect(groups.map(([who, facts]) => [who, facts.map((f) => f.fact)])).toEqual([
      ['ana', ['Dog Rex', 'Mornings']],
      ['bob', ['Likes jazz']],
    ])
  })
})
