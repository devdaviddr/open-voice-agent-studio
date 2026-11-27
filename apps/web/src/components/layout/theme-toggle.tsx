import { Monitor, Moon, Sun } from 'lucide-react'
import { useTheme } from './theme'
import { Button } from '@/components/ui/button'

const order = ['system', 'light', 'dark'] as const
const icons = { system: Monitor, light: Sun, dark: Moon }

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const current = (order as readonly string[]).includes(theme) ? (theme as (typeof order)[number]) : 'system'
  const Icon = icons[current]
  const next = order[(order.indexOf(current) + 1) % order.length]
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={() => setTheme(next)}
      aria-label={`Theme: ${current}. Switch to ${next}`}
    >
      <Icon className="size-4" />
    </Button>
  )
}
