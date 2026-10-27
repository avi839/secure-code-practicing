import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/format'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Recessed "Ink Well" surface (code, logs, inset panels). */
  inset?: boolean
  /** Brighten the hairline on hover. */
  interactive?: boolean
  as?: 'div' | 'section' | 'article'
}

export function Card({ inset, interactive, as: Tag = 'div', className, children, ...rest }: CardProps) {
  return (
    <Tag
      className={cn(
        'rounded border',
        inset ? 'border-steel bg-ink' : 'border-steel bg-charcoal-850/60',
        interactive && 'card-hover',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  )
}

interface CardHeaderProps {
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  className?: string
  /** Heading level used for the title. */
  level?: 2 | 3
  id?: string
}

export function CardHeader({ title, description, icon, action, className, level = 2, id }: CardHeaderProps) {
  const Heading = level === 2 ? 'h2' : 'h3'
  return (
    <div className={cn('flex items-start justify-between gap-4 border-b border-steel px-5 py-4', className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 text-syntax-violet" aria-hidden="true">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <Heading id={id} className="text-base font-medium text-bone">
            {title}
          </Heading>
          {description && <p className="mt-0.5 text-sm text-fog">{description}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
