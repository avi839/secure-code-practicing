import { CheckCircle2, CircleDashed, Loader2, MinusCircle, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { STATUS_LABELS, cn, severityMeta } from '@/lib/format'
import type { EvaluationStatus } from '@/lib/types'

export type BadgeTone = 'neutral' | 'lime' | 'red' | 'amber' | 'aqua' | 'violet'

const TONES: Record<BadgeTone, string> = {
  neutral: 'border-hairline bg-charcoal-750 text-ash',
  lime: 'border-apple-500/40 bg-apple-500/10 text-apple-400',
  red: 'border-mute-red/40 bg-mute-red/10 text-[#ff8197]',
  amber: 'border-sev-medium/40 bg-sev-medium/10 text-sev-medium',
  aqua: 'border-aqua/40 bg-aqua/10 text-[#7bbcf3]',
  violet: 'border-syntax-violet/40 bg-syntax-violet/10 text-syntax-violet',
}

interface BadgeProps {
  tone?: BadgeTone
  icon?: ReactNode
  className?: string
  children: ReactNode
  title?: string
}

export function Badge({ tone = 'neutral', icon, className, children, title }: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  )
}

export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  const meta = severityMeta(severity)
  const Icon = meta.icon
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide',
        meta.badge,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {meta.label}
    </span>
  )
}

const STATUS_TONE: Record<EvaluationStatus, BadgeTone> = {
  pending: 'neutral',
  running: 'lime',
  completed: 'aqua',
  failed: 'red',
  cancelled: 'neutral',
}

export function StatusBadge({ status }: { status: EvaluationStatus }) {
  const icon =
    status === 'running' ? (
      <span className="led led-live" />
    ) : status === 'pending' ? (
      <CircleDashed className="h-3.5 w-3.5" />
    ) : status === 'completed' ? (
      <CheckCircle2 className="h-3.5 w-3.5" />
    ) : status === 'failed' ? (
      <XCircle className="h-3.5 w-3.5" />
    ) : (
      <MinusCircle className="h-3.5 w-3.5" />
    )
  return (
    <Badge tone={STATUS_TONE[status] ?? 'neutral'} icon={icon}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  )
}

export function SecureBadge({ secure, pending }: { secure: boolean | null | undefined; pending?: boolean }) {
  if (pending) {
    return (
      <Badge tone="neutral" icon={<Loader2 className="h-3.5 w-3.5 animate-spin" />}>
        Scanning
      </Badge>
    )
  }
  if (secure === null || secure === undefined) return <Badge tone="neutral">Unknown</Badge>
  return secure ? (
    <Badge tone="lime" icon={<ShieldCheck className="h-3.5 w-3.5" />}>
      Secure
    </Badge>
  ) : (
    <Badge tone="red" icon={<ShieldAlert className="h-3.5 w-3.5" />}>
      Insecure
    </Badge>
  )
}
