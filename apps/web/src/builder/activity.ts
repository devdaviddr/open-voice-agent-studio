/**
 * What the agent is doing on the canvas during a console session (MVP FR-24, DD-7).
 * Derived from runtime events plus the console's own actions; the runtime protocol is unchanged.
 */

export type Phase = 'waiting' | 'listening' | 'thinking' | 'speaking' | 'tool'

export type Activity = {
  nodeId: string | null
  phase: Phase | null
  /** Edge that just fired; animates until `clearFiring` runs. `seq` restarts the animation. */
  firing: { edgeId: string; seq: number } | null
  visitedNodes: string[]
  visitedEdges: string[]
}

export const IDLE: Activity = { nodeId: null, phase: null, firing: null, visitedNodes: [], visitedEdges: [] }

/** Runtime events (`type` from the WebSocket) and console-local ones (`local:*`). */
export type ActivityEvent =
  | { type: 'node_enter'; node_id: string }
  | { type: 'edge'; edge_id: string }
  | { type: 'token' }
  | { type: 'assistant_message' }
  | { type: 'tool_call' | 'knowledge' | 'memory' }
  | { type: 'ended' }
  | { type: 'local:user_sent' }
  | { type: 'local:listening'; on: boolean }
  | { type: 'local:audio'; playing: boolean }
  | { type: 'local:reset' }

const add = (xs: string[], x: string) => (xs.includes(x) ? xs : [...xs, x])

export function nextActivity(a: Activity, e: ActivityEvent): Activity {
  switch (e.type) {
    case 'node_enter':
      return { ...a, nodeId: e.node_id, phase: 'thinking', visitedNodes: add(a.visitedNodes, e.node_id) }
    case 'edge':
      return {
        ...a,
        firing: { edgeId: e.edge_id, seq: (a.firing?.seq ?? 0) + 1 },
        visitedEdges: add(a.visitedEdges, e.edge_id),
      }
    case 'token':
      return a.phase === 'speaking' ? a : { ...a, phase: 'speaking' }
    case 'assistant_message':
      return { ...a, phase: 'waiting' }
    case 'tool_call':
    case 'knowledge':
    case 'memory':
      return { ...a, phase: 'tool' }
    case 'local:user_sent':
      return { ...a, phase: 'thinking' }
    case 'local:listening':
      if (e.on) return { ...a, phase: 'listening' }
      return a.phase === 'listening' ? { ...a, phase: 'waiting' } : a
    case 'local:audio':
      // Read-aloud: the node keeps "speaking" while its reply plays, unless it has moved on.
      if (e.playing) return a.phase === 'waiting' ? { ...a, phase: 'speaking' } : a
      return a.phase === 'speaking' ? { ...a, phase: 'waiting' } : a
    case 'ended':
    case 'local:reset':
      return IDLE
  }
}
