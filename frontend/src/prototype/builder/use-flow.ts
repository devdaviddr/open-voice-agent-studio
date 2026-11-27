// PROTOTYPE — in-memory canvas state shared by the variants. Not production code.
import { addEdge, MarkerType, useEdgesState, useNodesState, type Connection } from '@xyflow/react'
import { initialEdges, initialNodes, type FlowEdge, type FlowNode, type NodeKind } from './data'
import { kinds } from './flow'

export function useFlow(opts: { selected?: string; active?: string } = {}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(
    initialNodes.map((n) => ({ ...n, selected: n.id === opts.selected, data: { ...n.data, active: n.id === opts.active } })),
  )
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>(
    initialEdges.map((e) => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 } })),
  )
  const selectedNode = nodes.find((n) => n.selected)
  const selectedEdge = edges.find((e) => e.selected)
  const issues = nodes.filter((n) => n.data.issue).length

  const onConnect = (c: Connection) =>
    setEdges((es) => addEdge({ ...c, type: 'condition', data: { condition: { kind: 'llm', text: 'describe when to move on' } } }, es))

  const addNode = (kind: NodeKind) =>
    setNodes((ns) => [
      ...ns.map((n) => ({ ...n, selected: false })),
      { id: `${kind}-${ns.length}`, type: kind, position: { x: 300 + ns.length * 8, y: 650 }, selected: true, data: { label: `New ${kinds[kind].name.toLowerCase()}` } },
    ])

  return { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, selectedNode, selectedEdge, issues }
}
