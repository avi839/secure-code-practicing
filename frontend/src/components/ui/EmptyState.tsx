import type { ReactNode } from 'react'
import { cn } from '@/lib/format'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'relative flex flex-col items-center justify-center overflow-hidden rounded border border-dashed border-hairline px-6 py-12 text-center',
        className,
      )}
    >
      <div className="bg-blueprint pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
      {icon && (
        <div className="relative mb-4 flex h-12 w-12 items-center justify-center rounded border border-hairline bg-ink text-syntax-violet" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3 className="relative text-lg font-medium text-bone">{title}</h3>
      {description && <p className="relative mt-2 max-w-md text-sm text-ash">{description}</p>}
      {action && <div className="relative mt-6">{action}</div>}
    </div>
  )
}
