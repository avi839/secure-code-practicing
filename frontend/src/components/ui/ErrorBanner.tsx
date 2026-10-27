import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/format'
import type { FieldError } from '@/lib/types'
import { Button } from './Button'

interface ErrorBannerProps {
  title?: string
  message: string
  fieldErrors?: FieldError[]
  onRetry?: () => void
  retrying?: boolean
  className?: string
}

function fieldName(field: string): string {
  return field.replace(/^body\./, '').replace(/_/g, ' ')
}

export function ErrorBanner({ title = 'Something went wrong', message, fieldErrors, onRetry, retrying, className }: ErrorBannerProps) {
  return (
    <div role="alert" className={cn('animate-enter rounded border border-mute-red/40 bg-mute-red/[0.07] p-4', className)}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-mute-red" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-bone">{title}</p>
          <p className="mt-1 text-sm text-ash">{message}</p>
          {fieldErrors && fieldErrors.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ash">
              {fieldErrors.map((e, i) => (
                <li key={`${e.field}-${i}`}>
                  <span className="font-medium text-cloud">{fieldName(e.field)}</span>: {e.message}
                </li>
              ))}
            </ul>
          )}
        </div>
        {onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry} loading={retrying} icon={<RefreshCw className="h-3.5 w-3.5" />}>
            Retry
          </Button>
        )}
      </div>
    </div>
  )
}
