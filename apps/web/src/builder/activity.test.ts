import { describe, expect, it } from 'vitest'
import { IDLE, nextActivity, type ActivityEvent } from './activity'

const run = (events: ActivityEvent[]) => events.reduce(nextActivity, IDLE)

describe('canvas activity', () => {
  it('follows a turn: thinking, speaking, waiting', () => {
    // MVP AC-22
    let a = run([{ type: 'node_enter', node_id: 'n1' }])
    expect(a).toMatchObject({ nodeId: 'n1', phase: 'thinking', visitedNodes: ['n1'] })
    a = nextActivity(a, { type: 'token' })
    expect(a.phase).toBe('speaking')
    a = nextActivity(a, { type: 'assistant_message' })
    expect(a.phase).toBe('waiting')
    a = nextActivity(a, { type: 'local:user_sent' })
    expect(a.phase).toBe('thinking')
  })

  it('animates a fired edge and keeps the path visited', () => {
    // MVP AC-22
    const a = run([
      { type: 'node_enter', node_id: 'start' },
      { type: 'edge', edge_id: 'e1' },
      { type: 'node_enter', node_id: 'n2' },
      { type: 'edge', edge_id: 'e2' },
      { type: 'edge', edge_id: 'e2' },
    ])
    expect(a.firing).toEqual({ edgeId: 'e2', seq: 3 })
    expect(a.visitedEdges).toEqual(['e1', 'e2'])
    expect(a.visitedNodes).toEqual(['start', 'n2'])
  })

  it('shows tool use, then speaking again', () => {
    // MVP AC-22
    const a = run([{ type: 'node_enter', node_id: 'n1' }, { type: 'knowledge' }])
    expect(a.phase).toBe('tool')
    expect(nextActivity(a, { type: 'token' }).phase).toBe('speaking')
  })

  it('listens while recording and speaks while reading aloud', () => {
    let a = run([{ type: 'node_enter', node_id: 'n1' }, { type: 'assistant_message' }])
    a = nextActivity(a, { type: 'local:listening', on: true })
    expect(a.phase).toBe('listening')
    a = nextActivity(a, { type: 'local:listening', on: false })
    expect(a.phase).toBe('waiting')
    a = nextActivity(a, { type: 'local:audio', playing: true })
    expect(a.phase).toBe('speaking')
    a = nextActivity(a, { type: 'local:audio', playing: false })
    expect(a.phase).toBe('waiting')
  })

  it('a late audio end does not override a newer phase', () => {
    let a = run([{ type: 'node_enter', node_id: 'n1' }, { type: 'local:user_sent' }])
    a = nextActivity(a, { type: 'local:audio', playing: false })
    expect(a.phase).toBe('thinking')
  })

  it('ending or resetting clears everything', () => {
    // MVP AC-22
    const busy = run([
      { type: 'node_enter', node_id: 'n1' },
      { type: 'edge', edge_id: 'e1' },
    ])
    expect(nextActivity(busy, { type: 'ended' })).toEqual(IDLE)
    expect(nextActivity(busy, { type: 'local:reset' })).toEqual(IDLE)
  })
})
