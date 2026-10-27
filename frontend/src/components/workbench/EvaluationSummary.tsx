'use client'

import { Ban, Clock, FlaskConical } from 'lucide-react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SecureBadge, StatusBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ErrorBanner } from '@/components/ui/ErrorBanner'
import { SEVERITIES, SEVERITY_META, cn, formatDuration, formatPercent, formatSignedPercent, isTerminalStatus, languageLabel, providerLabel, relativeTime } from '@/lib/format'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { EvaluationDetail } from '@/lib/types'
import { CHART_TOOLTIP_STYLE, CHART_AXIS_TICK } from '@/components/charts/theme'

interface EvaluationSummaryProps {
  evaluation: EvaluationDetail
  onCancel?: () => void
  cancelling?: boolean
}

function Metric({ label, value, tone, hint }: { label: string; value: string; tone?: string; hint?: string }) {
  return (
    <div className="rounded border border-steel bg-ink px-4 py-3">
      <dt className="text-xs text-fog">{label}</dt>
      <dd className={cn('mt-1 font-display text-2xl font-medium tabular-nums tracking-display', tone ?? 'text-bone')}>{value}</dd>
      {hint && <dd className="mt-0.5 text-xs text-fog">{hint}</dd>}
    </div>
  )
}

/** Run header: status, provider, demo banner, findings t0 -> final, Repair/Regression/NetGain and severity per round. */
export function EvaluationSummary({ evaluation, onCancel, cancelling }: EvaluationSummaryProps) {
  const reduced = useReducedMotion()
  const terminal = isTerminalStatus(evaluation.status)
  const last = evaluation.metrics[evaluation.metrics.length - 1]
  const versions = evaluation.code_versions
  const finalVersion = versions[versions.length - 1]
  const t0 = versions[0]
  const findingsT0 = terminal ? evaluation.total_findings_t0 : (t0?.findings_count ?? 0)
  const findingsFinal = terminal ? evaluation.total_findings_final : (finalVersion?.findings_count ?? 0)
  const requested = typeof evaluation.ai_config.requested_provider === 'string' ? evaluation.ai_config.requested_provider : null
  const fallbackReason = typeof evaluation.ai_config.fallback_reason === 'string' ? evaluation.ai_config.fallback_reason : null
  const chartData = versions.map((v) => ({ version: v.version, ...v.severity_counts }))

  return (
    <section
      aria-labelledby="run-title"
      className={cn('relative rounded-lg border border-steel bg-charcoal-850/60', !terminal && 'glow-ring')}
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-steel px-5 py-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={evaluation.status} />
            <SecureBadge secure={terminal ? evaluation.final_secure : finalVersion?.is_secure} pending={!terminal && !finalVersion} />
            <span className="font-mono text-xs text-fog">
              {languageLabel(evaluation.language)} · {providerLabel(evaluation.ai_provider)} · {evaluation.ai_model}
            </span>
          </div>
          <h2 id="run-title" className="mt-2 line-clamp-2 font-sans text-lg font-medium tracking-normal text-bone">
            {evaluation.task}
          </h2>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fog">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              started {relativeTime(evaluation.started_at ?? evaluation.created_at)}
            </span>
            <span>
              {evaluation.completed_rounds}/{evaluation.requested_rounds} rounds
              {evaluation.stopped_early ? ' · stopped early (clean)' : ''}
            </span>
            {terminal && <span>duration {formatDuration(evaluation.total_duration_seconds)}</span>}
          </p>
        </div>
        {!terminal && onCancel && (
          <Button variant="secondary" size="sm" onClick={onCancel} loading={cancelling} icon={<Ban className="h-3.5 w-3.5" />}>
            Cancel run
          </Button>
        )}
      </div>

      <div className="space-y-4 p-5">
        {evaluation.is_demo && (
          <div className="flex items-start gap-3 rounded border border-syntax-violet/40 bg-syntax-violet/[0.07] px-4 py-3 text-sm">
            <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-syntax-violet" aria-hidden="true" />
            <p className="text-ash">
              <span className="font-medium text-cloud">Demo provider output.</span>{' '}
              {requested && requested !== 'demo'
                ? `You requested ${providerLabel(requested)}, but the run used the offline demo provider${fallbackReason ? ` because ${fallbackReason}` : ''}.`
                : 'Code and repairs come from the deterministic offline provider, not a live model.'}
            </p>
          </div>
        )}

        {evaluation.status === 'failed' && (
          <ErrorBanner title="The evaluation failed" message={evaluation.error_message || 'The run stopped with an error. Check the backend logs.'} />
        )}
        {evaluation.status === 'cancelled' && (
          <p className="rounded border border-hairline bg-ink px-4 py-3 text-sm text-ash">
            This run was cancelled{evaluation.error_message ? `: ${evaluation.error_message}` : '.'}
          </p>
        )}

        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric
            label="Findings t0 → final"
            value={`${findingsT0} → ${findingsFinal}`}
            tone={findingsFinal < findingsT0 ? 'text-apple-500' : findingsFinal > findingsT0 ? 'text-[#ff8197]' : 'text-bone'}
            hint={terminal ? `${evaluation.findings_fixed} fixed · ${evaluation.findings_new} new` : 'updating live'}
          />
          <Metric
            label={`Repair@${last?.round ?? 'T'}`}
            value={last ? (last.repair_defined ? formatPercent(last.repair_rate) : 'n/a') : '…'}
            tone="text-apple-500"
            hint={last && !last.repair_defined ? 't0 was already secure' : undefined}
          />
          <Metric
            label={`Regression@${last?.round ?? 'T'}`}
            value={last ? (last.regression_defined ? formatPercent(last.regression_rate) : 'n/a') : '…'}
            tone="text-[#ff8197]"
            hint={last && !last.regression_defined ? 't0 was insecure' : undefined}
          />
          <Metric label={`NetGain@${last?.round ?? 'T'}`} value={last ? formatSignedPercent(last.net_gain) : '…'} tone="text-syntax-violet" />
        </dl>
        {!last && terminal && evaluation.status === 'completed' && (
          <p className="text-xs text-fog">No reflexion round was needed: t0 already scanned clean, so no metrics were computed.</p>
        )}
        {!terminal && <p className="text-xs text-fog">Metrics are computed when the run completes.</p>}

        {chartData.length > 0 && (
          <figure className="rounded border border-steel bg-ink p-4">
            <figcaption className="text-xs text-fog">Findings by severity per version</figcaption>
            <div className="mt-2 h-36" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
                  <XAxis dataKey="version" tick={CHART_AXIS_TICK} axisLine={{ stroke: '#272a2e' }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  {SEVERITIES.map((s) => (
                    <Bar key={s} dataKey={s} name={SEVERITY_META[s].label} stackId="sev" fill={SEVERITY_META[s].color} isAnimationActive={!reduced} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
            <table className="sr-only">
              <caption>Findings by severity per version</caption>
              <thead>
                <tr>
                  <th scope="col">Version</th>
                  {SEVERITIES.map((s) => (
                    <th key={s} scope="col">
                      {SEVERITY_META[s].label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chartData.map((row) => (
                  <tr key={row.version}>
                    <th scope="row">{row.version}</th>
                    {SEVERITIES.map((s) => (
                      <td key={s}>{row[s]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </figure>
        )}
      </div>
    </section>
  )
}
