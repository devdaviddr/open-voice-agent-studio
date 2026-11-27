import type { Edge as RFEdge, Node as RFNode } from '@xyflow/react'
import type {
  AgentSpec,
  AgentStepNode,
  Edge,
  EndNode,
  ExtractNode,
  NoteNode,
  RouterNode,
  StartNode,
} from '@/gen/agent-spec'

export type SpecNode = StartNode | AgentStepNode | ExtractNode | RouterNode | EndNode | NoteNode
export type NodeKind = SpecNode['type']
type FlowNodeOf<K extends NodeKind> = RFNode<
  Extract<SpecNode, { type: K }>['data'] & Record<string, unknown>,
  K
>
/** A canvas node; `type` discriminates `data` exactly like the spec's node union. */
export type FlowNode = { [K in NodeKind]: FlowNodeOf<K> }[NodeKind]
export type FlowEdge = RFEdge<
  { condition: Edge['condition']; order: number } & Record<string, unknown>,
  'condition'
>
/** Everything in the spec except the graph. */
export type Meta = Omit<AgentSpec, 'graph'>

export function specToFlow(spec: AgentSpec): { nodes: FlowNode[]; edges: FlowEdge[]; meta: Meta } {
  const { graph, ...meta } = spec
  const nodes = graph.nodes
    .filter((n): n is SpecNode => n.type !== 'tool_call' && n.type !== 'handoff')
    .map((n) => ({ id: n.id, type: n.type, position: n.position, data: n.data }) as FlowNode)
  const edges = graph.edges.map((e): FlowEdge => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'condition',
    data: { condition: e.condition, order: e.order },
  }))
  return { nodes, edges, meta }
}

export function flowToSpec(nodes: FlowNode[], edges: FlowEdge[], meta: Meta): AgentSpec {
  return {
    ...meta,
    graph: {
      nodes: nodes.map(
        (n) =>
          ({
            id: n.id,
            type: n.type,
            position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
            data: n.data,
          }) as SpecNode,
      ),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        order: e.data?.order ?? 0,
        condition: e.data?.condition ?? null,
      })),
    },
  }
}

export function newId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}`
}
