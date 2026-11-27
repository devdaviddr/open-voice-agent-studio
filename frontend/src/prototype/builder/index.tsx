// PROTOTYPE — three builder layouts on /prototype/builder, switch with ?variant=A|B|C or the ← → keys.
// Throwaway: lives on branch prototype/builder and is never merged.
import '@xyflow/react/dist/style.css'
import { useEffect, useState } from 'react'
import { ReactFlowProvider } from '@xyflow/react'
import { ChevronLeft, ChevronRight, Moon, Sun } from 'lucide-react'
import * as A from './variant-a'
import * as B from './variant-b'
import * as C from './variant-c'

const variants = { A, B, C } as const
type Key = keyof typeof variants
const keys = Object.keys(variants) as Key[]

function readVariant(): Key {
  const v = new URLSearchParams(location.search).get('variant')?.toUpperCase()
  return keys.includes(v as Key) ? (v as Key) : 'A'
}

export function BuilderPrototype() {
  const [key, setKey] = useState<Key>(readVariant)
  const go = (step: number) => {
    const next = keys[(keys.indexOf(key) + step + keys.length) % keys.length]
    history.replaceState(null, '', `?variant=${next}`)
    setKey(next)
  }
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t.closest('input, textarea, [contenteditable]')) return
      if (e.key === 'ArrowLeft') go(-1)
      if (e.key === 'ArrowRight') go(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
  const V = variants[key]
  const Comp = { A: A.VariantA, B: B.VariantB, C: C.VariantC }[key]
  return (
    <>
      <ReactFlowProvider key={key}>
        <Comp />
      </ReactFlowProvider>
      {import.meta.env.DEV && (
        <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1 rounded-full bg-zinc-900 px-2 py-1.5 text-xs text-white shadow-2xl ring-1 ring-white/10">
          <button onClick={() => go(-1)} className="rounded-full p-1 hover:bg-white/10" title="Previous (←)">
            <ChevronLeft className="size-4" />
          </button>
          <span className="min-w-44 text-center">
            <b>{key}</b> · {V.name}
          </span>
          <button onClick={() => go(1)} className="rounded-full p-1 hover:bg-white/10" title="Next (→)">
            <ChevronRight className="size-4" />
          </button>
          <span className="mx-1 h-4 w-px bg-white/20" />
          <button onClick={() => document.documentElement.classList.toggle('dark')} className="rounded-full p-1 hover:bg-white/10" title="Toggle theme">
            <Sun className="size-4 dark:hidden" />
            <Moon className="hidden size-4 dark:block" />
          </button>
        </div>
      )}
    </>
  )
}
