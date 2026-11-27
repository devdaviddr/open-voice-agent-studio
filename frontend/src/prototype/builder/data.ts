// PROTOTYPE — throwaway mock data for the builder layout prototype. Not production code.
import type { Edge, Node } from '@xyflow/react'

export type NodeKind =
  | 'start'
  | 'agent_step'
  | 'extract'
  | 'router'
  | 'tool_call'
  | 'handoff'
  | 'end'
  | 'note'

export type Condition = { kind: 'llm'; text: string } | { kind: 'cel'; expr: string } | { kind: 'else' }

export type FlowNodeData = {
  label: string
  summary?: string
  prompt?: string
  tools?: string[]
  knowledge?: string[]
  outputs?: string[]
  voice?: string
  issue?: string
  active?: boolean
}

export type FlowNode = Node<FlowNodeData, NodeKind>
export type FlowEdge = Edge<{ condition?: Condition; order?: number }, 'condition'>

export const agent = {
  name: 'Bright Smile reception',
  description: 'Books dental appointments and answers clinic questions',
  draftRevision: 14,
  live: 3,
  voice: 'af_heart',
  llm: 'qwen3:4b (Ollama)',
  stt: 'whisper small.en',
}

export const versions = [
  { n: 3, message: 'Offer alternatives when the slot is taken', author: 'devdaviddr', when: '2 days ago', env: ['live'] },
  { n: 2, message: 'Add billing handoff', author: 'devdaviddr', when: '5 days ago', env: ['staging'] },
  { n: 1, message: 'First version', author: 'devdaviddr', when: '1 week ago', env: [] },
]

const p = (x: number, y: number) => ({ x, y })

export const initialNodes: FlowNode[] = [
  { id: 'start', type: 'start', position: p(0, 220), data: { label: 'Start', summary: '"Hi, Bright Smile Dental, this is Ava. How can I help?"' } },
  {
    id: 'triage', type: 'agent_step', position: p(280, 200),
    data: {
      label: 'Triage', summary: 'Work out what the caller needs',
      prompt: 'You are Ava, the receptionist at Bright Smile Dental. Find out whether the caller wants to book, has a question, or has a billing issue. Keep replies under two sentences.',
      tools: ['end_session'], voice: 'af_heart',
    },
  },
  {
    id: 'collect', type: 'extract', position: p(620, 40),
    data: { label: 'Collect details', summary: 'Name, phone, preferred day', outputs: ['caller.name', 'caller.phone', 'preferred_date'] },
  },
  {
    id: 'availability', type: 'tool_call', position: p(940, 40),
    data: { label: 'check_availability', summary: 'GET /slots?date={{preferred_date}}', tools: ['clinic_api'], issue: 'Secret CLINIC_API_KEY is not set' },
  },
  { id: 'slot', type: 'router', position: p(1250, 60), data: { label: 'Slot free?' } },
  {
    id: 'confirm', type: 'agent_step', position: p(1540, -60),
    data: { label: 'Confirm booking', summary: 'Read back the booking and confirm', tools: ['book_slot', 'send_sms'], voice: 'af_heart' },
  },
  {
    id: 'alternatives', type: 'agent_step', position: p(1540, 170),
    data: { label: 'Offer alternatives', summary: 'Suggest the next 3 free slots', tools: ['check_availability'] },
  },
  { id: 'booked', type: 'end', position: p(1880, -40), data: { label: 'Booked', summary: 'outcome: booked' } },
  {
    id: 'faq', type: 'agent_step', position: p(620, 330),
    data: { label: 'Clinic FAQ', summary: 'Hours, prices, location', knowledge: ['clinic-handbook.pdf', 'price-list.md'], tools: ['search_knowledge'] },
  },
  { id: 'answered', type: 'end', position: p(940, 350), data: { label: 'Answered', summary: 'outcome: faq' } },
  { id: 'billing', type: 'handoff', position: p(620, 520), data: { label: 'Billing agent', summary: 'live · passes caller.*' } },
  {
    id: 'note', type: 'note', position: p(260, 440),
    data: { label: 'Prices must come from the knowledge base, never from the model. Review price-list.md monthly.' },
  },
]

const e = (id: string, source: string, target: string, condition?: Condition, order = 0): FlowEdge => ({
  id, source, target, type: 'condition', data: { condition, order },
})

export const initialEdges: FlowEdge[] = [
  e('e1', 'start', 'triage'),
  e('e2', 'triage', 'collect', { kind: 'llm', text: 'wants to book or move an appointment' }, 1),
  e('e3', 'triage', 'faq', { kind: 'llm', text: 'asks about hours, prices or location' }, 2),
  e('e4', 'triage', 'billing', { kind: 'llm', text: 'has a billing or insurance question' }, 3),
  e('e5', 'collect', 'availability'),
  e('e6', 'availability', 'slot'),
  e('e7', 'slot', 'confirm', { kind: 'cel', expr: 'slot.available == true' }, 1),
  e('e8', 'slot', 'alternatives', { kind: 'else' }, 2),
  e('e9', 'confirm', 'booked', { kind: 'llm', text: 'caller confirmed' }, 1),
  e('e10', 'alternatives', 'collect', { kind: 'llm', text: 'caller picked a new day' }, 1),
  e('e11', 'faq', 'answered', { kind: 'else' }, 1),
]

export const transcript = [
  { who: 'agent', node: 'start', text: 'Hi, Bright Smile Dental, this is Ava. How can I help?', ms: null },
  { who: 'user', node: 'triage', text: "Hi, I'd like to book a cleaning next Tuesday.", ms: null },
  { who: 'event', node: 'triage', text: 'edge → Collect details (LLM: wants to book…)', ms: 212 },
  { who: 'agent', node: 'collect', text: 'Sure! Can I get your name and a phone number?', ms: 640 },
  { who: 'user', node: 'collect', text: "It's Ana Lopez, 0412 555 019.", ms: null },
  { who: 'event', node: 'collect', text: 'set caller.name = "Ana Lopez", caller.phone, preferred_date = 2026-12-01', ms: 180 },
  { who: 'event', node: 'availability', text: 'tool check_availability → 200 OK (3 slots)', ms: 96 },
  { who: 'agent', node: 'confirm', text: 'I have 9:30 or 2:15 on Tuesday. Which works better?', ms: 710 },
] as const
