import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AgentSpec } from '@/gen/agent-spec'
import { redo, undo, useBuilder } from './store'

const spec: AgentSpec = {
  schema_version: '1',
  settings: {
    prompt: '',
    first_message: 'Hi',
    language: 'en',
    voice: { provider: 'kokoro', voice_id: 'af_heart', speed: 1 },
    llm: { provider: 'workspace', model: null, temperature: 0.6 },
    stt: { provider: 'whisper', model: 'small.en' },
    turn: { sensitivity: 'medium', interruptions: true },
    limits: { max_session_seconds: 900, idle_timeout_seconds: 30 },
    history_token_budget: 4000,
  },
  graph: {
    nodes: [
      { id: 'start', type: 'start', position: { x: 0, y: 0 }, data: { first_message: null, set: {} } },
      {
        id: 'main',
        type: 'agent_step',
        position: { x: 300, y: 0 },
        data: {
          label: 'Main',
          prompt: '',
          overrides: null,
          tools: null,
          knowledge: null,
          auto_knowledge_top_k: 0,
        },
      },
      {
        id: 'end',
        type: 'end',
        position: { x: 600, y: 0 },
        data: { label: 'End', message: null, outcome: 'done' },
      },
    ],
    edges: [
      { id: 'a', source: 'start', target: 'main', order: 0, condition: null },
      { id: 'b', source: 'main', target: 'end', order: 1, condition: { kind: 'llm', text: 'done' } },
    ],
  },
  tools: [],
  knowledge: [],
  variables: [],
  pronunciation: [],
  memory: { enabled: false },
  recording: { enabled: false },
}

const later = () => vi.advanceTimersByTime(1000)
const s = () => useBuilder.getState()

describe('builder store', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    later()
    s().load('agent', 1, spec)
    later()
  })

  it('undoes and redoes adding a node', () => {
    s().addNode('router', { x: 0, y: 200 })
    expect(s().nodes).toHaveLength(4)
    expect(useBuilder.temporal.getState().pastStates).toHaveLength(1)
    undo()
    expect(s().nodes).toHaveLength(3)
    redo()
    expect(s().nodes).toHaveLength(4)
  })

  it('restores a deleted node together with its edges', () => {
    // MVP AC-9
    s().removeNode('main')
    expect(s().edges).toHaveLength(0)
    undo()
    expect(s().nodes.map((n) => n.id)).toContain('main')
    expect(s().edges).toHaveLength(2)
  })

  it('groups a burst of typing into one undo step', () => {
    for (const label of ['M', 'Ma', 'Mai', 'Main step']) {
      s().updateNodeData('main', { label })
      vi.advanceTimersByTime(100)
    }
    later()
    s().updateNodeData('main', { label: 'Second edit' })
    expect(useBuilder.temporal.getState().pastStates).toHaveLength(2)
    undo()
    expect((s().nodes[1].data as { label: string }).label).toBe('Main step')
    undo()
    expect((s().nodes[1].data as { label: string }).label).toBe('Main')
  })

  it('ignores selection changes in history', () => {
    s().select({ nodes: ['main'] })
    later()
    s().select({ nodes: ['end'] })
    expect(useBuilder.temporal.getState().pastStates).toHaveLength(0)
  })

  it('pastes a copy with new IDs and keeps internal edges', () => {
    // MVP AC-9
    s().select({ nodes: ['main', 'end'] })
    s().copySelection()
    s().paste()
    const ids = s().nodes.map((n) => n.id)
    expect(ids).toHaveLength(5)
    expect(new Set(ids).size).toBe(5)
    const pasted = s().nodes.filter((n) => n.selected)
    expect(pasted).toHaveLength(2)
    const pastedIds = new Set(pasted.map((n) => n.id))
    expect(s().edges.filter((e) => pastedIds.has(e.source) && pastedIds.has(e.target))).toHaveLength(1)
  })

  it('gives router edges an else first, then a model condition', () => {
    s().addNode('router', { x: 0, y: 0 })
    const router = s().nodes.at(-1)!.id
    s().onConnect({ source: router, target: 'end', sourceHandle: null, targetHandle: null })
    s().onConnect({ source: router, target: 'main', sourceHandle: null, targetHandle: null })
    const kinds = s()
      .edges.filter((e) => e.source === router)
      .map((e) => e.data?.condition?.kind)
    expect(kinds).toEqual(['else', 'llm'])
  })

  it('refuses edges out of End or into Start', () => {
    s().onConnect({ source: 'end', target: 'main', sourceHandle: null, targetHandle: null })
    s().onConnect({ source: 'main', target: 'start', sourceHandle: null, targetHandle: null })
    expect(s().edges).toHaveLength(2)
  })
})

describe('builder store after load', () => {
  it('records the very first edit, even right after loading', () => {
    vi.useFakeTimers()
    useBuilder.getState().load('agent', 1, spec)
    useBuilder.getState().addNode('note', { x: 0, y: 0 })
    expect(useBuilder.temporal.getState().pastStates).toHaveLength(1)
  })
})
