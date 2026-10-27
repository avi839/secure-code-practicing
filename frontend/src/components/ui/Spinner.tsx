import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/format'

interface SpinnerProps {
  className?: string
  /** Accessible label; omit when a visible label sits next to the spinner. */
  label?: string
}

export function Spinner({ className, label }: SpinnerProps) {
  return (
    <span className="inline-flex items-center" role={label ? 'status' : undefined}>
      <Loader2 className={cn('h-4 w-4 animate-spin', className)} aria-hidden="true" />
      {label && <span className="sr-only">{label}</span>}
    </span>
  )
}
