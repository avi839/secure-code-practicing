'use client'

import { Terminal } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { cn, formatClock, formatDuration, isTerminalStatus, providerLabel, severitySummary } from '@/lib/format'
import type { EvaluationDetail } from '@/lib/types'

interface LogLine {
  id: string
  time: string
  tone: 'muted' | 'lime' | 'red' | 'default' | 'violet'
  text: string
}

function buildLines(e: EvaluationDetail): LogLine[] {
  const lines: LogLine[] = [
    {
      id: 'created',
      time: formatClock(e.created_at),
      tone: 'muted',
      text: `queued ${e.language} evaluation · ${e.requested_rounds} round${e.requested_rounds === 1 ? '' : 's'} · provider ${providerLabel(e.ai_provider)}${e.is_demo ? ' (demo)' : ''}`,
    },
  ]
  if (e.started_at) lines.push({ id: 'started', time: formatClock(e.started_at), tone: 'default', text: 'run started' })

  for (const v of e.code_versions) {
    const status = v.is_secure ? 'SECURE' : 'INSECURE'
    const head = v.round_number === 0 ? `[${v.version}] baseline ready` : `[${v.version}] reflexion round ${v.round_number} applied`
    lines.push({
      id: `${v.id}-gen`,
      time: formatClock(v.created_at),
      tone: 'default',
      text: `${head}${v.generation_time_seconds != null ? ` in ${formatDuration(v.generation_time_seconds)}` : ''}`,
    })
    if (v.round_number > 0 && v.comparison.fixed.length) {
      lines.push({
        id: `${v.id}-fixed`,
        time: formatClock(v.created_at),
        tone: 'lime',
        text: `  fixed ${v.comparison.fixed.map((f) => f.cwe_id ?? f.rule_id).join(', ')}`,
      })
    }
    if (v.comparison.new.length) {
      lines.push({
        id: `${v.id}-new`,
        time: formatClock(v.created_at),
        tone: 'red',
        text: `  new ${v.comparison.new.map((f) => f.cwe_id ?? f.rule_id).join(', ')}`,
      })
    }
    lines.push({
      id: `${v.id}-scan`,
      time: formatClock(v.created_at),
      tone: v.is_secure ? 'lime' : 'red',
      text: `  scan ${status} · ${v.findings_count} finding${v.findings_count === 1 ? '' : 's'} (${severitySummary(v.severity_counts)})`,
    })
  }

  if (e.status === 'completed') {
    const last = e.metrics[e.metrics.length - 1]
    lines.push({
      id: 'done',
      time: formatClock(e.completed_at),
      tone: 'lime',
      text: `completed in ${formatDuration(e.total_duration_seconds)}${e.stopped_early ? ' · stopped early' : ''}${
        last ? ` · Repair@${last.round} ${last.repair_defined ? `${last.repair_rate.toFixed(0)}%` : 'n/a'} · NetGain@${last.round} ${last.net_gain.toFixed(0)}%` : ''
      }`,
    })
  } else if (e.status === 'failed') {
    lines.push({ id: 'failed', time: formatClock(e.completed_at ?? e.updated_at), tone: 'red', text: `FAILED · ${e.error_message ?? 'see backend logs'}` })
  } else if (e.status === 'cancelled') {
    lines.push({ id: 'cancelled', time: formatClock(e.updated_at), tone: 'muted', text: 'cancelled' })
  }
  return lines
}

const TONE: Record<LogLine['tone'], string> = {
  muted: 'text-fog',
  default: 'text-cloud',
  lime: 'text-apple-500',
  red: 'text-[#ff8197]',
  violet: 'text-syntax-violet',
}

/** Terminal pane that streams round events line by line (role="log" is a polite live region). */
export function RunLog({ evaluation }: { evaluation: EvaluationDetail }) {
  const lines = buildLines(evaluation)
  const scrollRef = useRef<HTMLDivElement>(null)
  const running = !isTerminalStatus(evaluation.status)

  useEffect(() => {
    const node = scrollRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [lines.length])

  return (
    <section aria-labelledby="runlog-title" className="overflow-hidden rounded-lg border border-steel bg-ink">
      <div className="flex items-center justify-between border-b border-steel px-4 py-2">
        <h3 id="runlog-title" className="flex items-center gap-2 font-mono text-xs font-normal tracking-normal text-fog">
          <Terminal className="h-3.5 w-3.5" aria-hidden="true" />
          run log
        </h3>
        {running && (
          <span className="inline-flex items-center gap-1.5 font-mono text-xs text-apple-500">
            <span className="led led-live" aria-hidden="true" />
            live
          </span>
        )}
      </div>
      <div ref={scrollRef} role="log" aria-label="Run log" className="max-h-60 overflow-y-auto px-4 py-3 font-mono text-[13px] leading-6" tabIndex={0}>
        {lines.map((line) => (
          <div key={line.id} className="flex animate-enter gap-3">
            <span className="shrink-0 text-fog">{line.time}</span>
            <span className={cn('whitespace-pre-wrap break-words', TONE[line.tone])}>{line.text}</span>
          </div>
        ))}
        {running && (
          <div className="flex gap-3" aria-hidden="true">
            <span className="shrink-0 text-fog">{'        '}</span>
            <span className="cursor-blink" />
          </div>
        )}
      </div>
    </section>
  )
}
