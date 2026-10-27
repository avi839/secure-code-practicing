'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/format'
import { prefersReducedMotion } from '@/lib/useReducedMotion'

interface StatCardProps {
  label: string
  /** null renders "n/a" (e.g. metric undefined because of a zero denominator). */
  value: number | null
  suffix?: string
  decimals?: number
  signed?: boolean
  hint?: ReactNode
  icon?: ReactNode
  tone?: 'default' | 'lime' | 'red' | 'violet'
  className?: string
}

const TONE: Record<NonNullable<StatCardProps['tone']>, string> = {
  default: 'text-bone',
  lime: 'text-apple-500',
  red: 'text-[#ff8197]',
  violet: 'text-syntax-violet',
}

/** Animates 0 -> value with requestAnimationFrame; jumps straight to the value under reduced motion. */
function useCountUp(target: number | null, duration = 900): number | null {
  const [display, setDisplay] = useState<number | null>(target === null ? null : 0)
  const fromRef = useRef(0)

  useEffect(() => {
    if (target === null) {
      setDisplay(null)
      return
    }
    if (prefersReducedMotion()) {
      setDisplay(target)
      fromRef.current = target
      return
    }
    const from = fromRef.current
    const start = performance.now()
    let frame = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(from + (target - from) * eased)
      if (t < 1) frame = requestAnimationFrame(step)
      else fromRef.current = target
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, duration])

  return display
}

export function StatCard({ label, value, suffix = '', decimals = 0, signed, hint, icon, tone = 'default', className }: StatCardProps) {
  const display = useCountUp(value)
  const text =
    display === null
      ? 'n/a'
      : `${signed && (value ?? 0) > 0 ? '+' : ''}${display.toFixed(decimals)}${suffix}`
  const finalText =
    value === null ? 'not available' : `${signed && value > 0 ? '+' : ''}${value.toFixed(decimals)}${suffix}`

  return (
    <div className={cn('card-hover rounded border border-steel bg-charcoal-850/60 p-5', className)}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-ash">{label}</p>
        {icon && (
          <span className="text-fog" aria-hidden="true">
            {icon}
          </span>
        )}
      </div>
      <p className={cn('mt-3 font-display text-3xl font-medium tabular-nums tracking-display', value === null ? 'text-fog' : TONE[tone])}>
        <span aria-hidden="true">{text}</span>
        <span className="sr-only">{finalText}</span>
      </p>
      {hint && <p className="mt-1.5 text-xs text-fog">{hint}</p>}
    </div>
  )
}
