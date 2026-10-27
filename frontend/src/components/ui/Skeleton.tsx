import { cn } from '@/lib/format'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} aria-hidden="true" />
}

/** A block of skeleton rows with a screen-reader loading message. */
export function SkeletonBlock({ rows = 3, label = 'Loading', className }: { rows?: number; label?: string; className?: string }) {
  return (
    <div className={cn('space-y-3', className)} role="status" aria-live="polite">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className={cn('h-4', i === rows - 1 ? 'w-2/3' : 'w-full')} />
      ))}
    </div>
  )
}
