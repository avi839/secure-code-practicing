'use client'

import { Activity, ArrowRight, BarChart3, RefreshCw, ShieldCheck, ShieldHalf, TrendingDown, TrendingUp, Sigma } from 'lucide-react'
import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { CweBreakdownChart } from '@/components/charts/CweBreakdownChart'
import { LanguageChart } from '@/components/charts/LanguageChart'
import { ReflexionCurveChart } from '@/components/charts/ReflexionCurveChart'
import { SecureRateChart } from '@/components/charts/SecureRateChart'
import { SeverityDistributionChart } from '@/components/charts/SeverityDistributionChart'
import { Reveal } from '@/components/Reveal'
import { SecureBadge, StatusBadge } from '@/components/ui/Badge'
import { Button, ButtonLink } from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorBanner } from '@/components/ui/ErrorBanner'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatCard } from '@/components/ui/StatCard'
import { errorMessage, getDashboard } from '@/lib/api'
import { languageLabel, providerLabel, relativeTime, truncate } from '@/lib/format'
import type { DashboardResponse } from '@/lib/types'

function DashboardSkeleton() {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <span className="sr-only">Loading dashboard…</span>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="rounded border border-steel bg-charcoal-850/60 p-5">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="mt-4 h-8 w-16" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-80 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      setData(await getDashboard(signal))
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  const completed = (data?.completed_evaluations ?? 0) > 0
  const flags = data?.metrics_flags
  const lastRound = data?.reflexion_curve[data.reflexion_curve.length - 1]?.round
  const T = lastRound !== undefined ? String(lastRound) : 'T'

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">Analytics</p>
          <h1 className="mt-2 text-3xl tracking-display">Dashboard</h1>
          <p className="mt-2 max-w-2xl text-ash">Aggregated over every evaluation stored in this instance. Metrics are relative to t0.</p>
        </div>
        <Button variant="secondary" onClick={() => load()} loading={loading && !!data} icon={<RefreshCw className="h-4 w-4" />}>
          Refresh
        </Button>
      </div>

      <div className="mt-8 space-y-6">
        {error && <ErrorBanner title="Could not load analytics" message={error} onRetry={() => load()} retrying={loading} />}

        {!data && loading && <DashboardSkeleton />}

        {data && data.total_evaluations === 0 && (
          <EmptyState
            icon={<BarChart3 className="h-6 w-6" />}
            title="No evaluations yet"
            description="Run your first evaluation in the workbench. Charts and KPIs fill in as soon as it completes."
            action={
              <ButtonLink href="/workbench" icon={<ArrowRight className="h-4 w-4" />}>
                Open the workbench
              </ButtonLink>
            }
          />
        )}

        {data && data.total_evaluations > 0 && (
          <>
            <section aria-label="Key metrics" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              <StatCard
                label="Evaluations"
                value={data.total_evaluations}
                icon={<Activity className="h-4 w-4" />}
                hint={`${data.completed_evaluations} completed · ${data.total_code_versions} versions`}
              />
              <StatCard
                label="Baseline secure"
                value={completed ? data.baseline_secure_rate : null}
                suffix="%"
                icon={<ShieldHalf className="h-4 w-4" />}
                hint="secure at t0"
              />
              <StatCard
                label="Final secure"
                value={completed ? data.final_secure_rate : null}
                suffix="%"
                tone="lime"
                icon={<ShieldCheck className="h-4 w-4" />}
                hint="secure after reflexion"
              />
              <StatCard
                label={`Repair@${T}`}
                value={completed && flags?.repair_defined ? data.average_repair_rate : null}
                suffix="%"
                tone="lime"
                icon={<TrendingUp className="h-4 w-4" />}
                hint={flags?.repair_defined ? 'insecure t0 → secure' : 'n/a: no insecure baseline'}
              />
              <StatCard
                label={`Regression@${T}`}
                value={completed && flags?.regression_defined ? data.average_regression_rate : null}
                suffix="%"
                tone="red"
                icon={<TrendingDown className="h-4 w-4" />}
                hint={flags?.regression_defined ? 'secure t0 → insecure' : 'n/a: no secure baseline'}
              />
              <StatCard
                label={`NetGain@${T}`}
                value={completed ? data.average_net_gain : null}
                suffix="%"
                signed
                tone="violet"
                icon={<Sigma className="h-4 w-4" />}
                hint="repaired minus regressed"
              />
            </section>

            <div className="grid gap-4 lg:grid-cols-2">
              <Reveal>
                <ReflexionCurveChart data={data.reflexion_curve} className="h-full" />
              </Reveal>
              <Reveal delay={70}>
                <SecureRateChart data={data.reflexion_curve} className="h-full" />
              </Reveal>
              <Reveal>
                <SeverityDistributionChart data={data.severity_distribution} className="h-full" />
              </Reveal>
              <Reveal delay={70}>
                <CweBreakdownChart data={data.cwe_breakdown} className="h-full" />
              </Reveal>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
              <Reveal>
                <LanguageChart data={data.evaluations_by_language} className="h-full" />
              </Reveal>
              <Reveal delay={70}>
                <Card className="h-full">
                  <CardHeader
                    title="Recent evaluations"
                    description="Open one to replay its rounds in the workbench."
                    action={
                      <ButtonLink href="/history" variant="ghost" size="sm" icon={<ArrowRight className="h-3.5 w-3.5" />}>
                        All history
                      </ButtonLink>
                    }
                  />
                  {data.recent_evaluations.length === 0 ? (
                    <p className="px-5 py-6 text-sm text-fog">No evaluations yet.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <caption className="sr-only">Most recent evaluations</caption>
                        <thead className="border-b border-steel text-xs text-fog">
                          <tr>
                            <th scope="col" className="px-5 py-2.5 font-medium">
                              Task
                            </th>
                            <th scope="col" className="px-3 py-2.5 font-medium">
                              Language
                            </th>
                            <th scope="col" className="px-3 py-2.5 font-medium">
                              Status
                            </th>
                            <th scope="col" className="px-3 py-2.5 font-medium">
                              Findings
                            </th>
                            <th scope="col" className="px-3 py-2.5 font-medium">
                              Result
                            </th>
                            <th scope="col" className="px-5 py-2.5 text-right font-medium">
                              Created
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-steel">
                          {data.recent_evaluations.map((e) => (
                            <tr key={e.id} className="transition-colors duration-150 hover:bg-charcoal-750/60">
                              <td className="max-w-[280px] px-5 py-3">
                                <Link href={`/workbench?id=${encodeURIComponent(e.id)}`} className="text-cloud underline-offset-4 hover:text-bone hover:underline">
                                  {truncate(e.task, 70)}
                                </Link>
                                <span className="block text-xs text-fog">{providerLabel(e.ai_provider)}</span>
                              </td>
                              <td className="px-3 py-3 text-ash">{languageLabel(e.language)}</td>
                              <td className="px-3 py-3">
                                <StatusBadge status={e.status} />
                              </td>
                              <td className="px-3 py-3 font-mono text-ash">
                                {e.total_findings_t0} → {e.total_findings_final}
                              </td>
                              <td className="px-3 py-3">
                                <SecureBadge secure={e.final_secure} />
                              </td>
                              <td className="whitespace-nowrap px-5 py-3 text-right text-fog">{relativeTime(e.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </Reveal>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
