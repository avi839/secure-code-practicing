'use client'

import { Check, Copy } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/format'

interface CopyButtonProps {
  value: string
  label?: string
  className?: string
}

/** Copy icon -> check icon swap with a small ripple; result is announced politely. */
export function CopyButton({ value, label = 'Copy code', className }: CopyButtonProps) {
  const [state, setState] = useState<'idle' | 'copied' | 'error'>('idle')
  const timer = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => () => clearTimeout(timer.current), [])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setState('copied')
    } catch {
      setState('error')
    }
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setState('idle'), 1600)
  }

  return (
    <button
      type="button"
      onClick={copy}
      className={cn(
        'relative inline-flex h-7 w-7 items-center justify-center rounded text-fog transition-colors duration-150 hover:bg-charcoal-750 hover:text-cloud',
        className,
      )}
      aria-label={label}
    >
      {state === 'copied' && <span className="absolute inset-0 animate-ripple rounded-full bg-apple-500/30" aria-hidden="true" />}
      {state === 'copied' ? (
        <Check className="h-4 w-4 animate-enter text-apple-500" aria-hidden="true" />
      ) : (
        <Copy className="h-4 w-4" aria-hidden="true" />
      )}
      <span className="sr-only" aria-live="polite">
        {state === 'copied' ? 'Copied to clipboard' : state === 'error' ? 'Copy failed' : ''}
      </span>
    </button>
  )
}
