'use client'

import { Activity, Bug, ShieldCheck, TrendingUp } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { ButtonLink } from '@/components/ui/Button'
import { ErrorBanner } from '@/components/ui/ErrorBanner'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatCard } from '@/components/ui/StatCard'
import { getDashboard, errorMessage } from '@/lib/api'
import type { DashboardResponse } from '@/lib/types'

/** Live numbers from GET /api/analytics/dashboard (no hard-coded research figures). */
export function LiveStats() {
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

  if (loading && !data) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" role="status" aria-live="polite">
        <span className="sr-only">Loading live statistics…</span>
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="rounded border border-steel bg-charcoal-850/60 p-5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-4 h-8 w-20" />
          </div>
        ))}
      </div>
    )
  }

  if (error && !data) {
    return <ErrorBanner title="Live statistics are unavailable" message={error} onRetry={() => load()} retrying={loading} />
  }

  if (!data) return null

  const completed = data.completed_evaluations > 0
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Evaluations run" value={data.total_evaluations} icon={<Activity className="h-4 w-4" />} hint={`${data.completed_evaluations} completed`} />
        <StatCard
          label="Findings tracked"
          value={data.total_security_findings}
          icon={<Bug className="h-4 w-4" />}
          hint={`${data.total_code_versions} code versions scanned`}
        />
        <StatCard
          label="Secure after reflexion"
          value={completed ? data.final_secure_rate : null}
          suffix="%"
          tone="lime"
          icon={<ShieldCheck className="h-4 w-4" />}
          hint={completed ? `baseline ${data.baseline_secure_rate.toFixed(0)}%` : 'no completed evaluations yet'}
        />
        <StatCard
          label="Average Repair@T"
          value={completed && data.metrics_flags.repair_defined ? data.average_repair_rate : null}
          suffix="%"
          tone="violet"
          icon={<TrendingUp className="h-4 w-4" />}
          hint={data.metrics_flags.repair_defined ? 'share of insecure t0 versions repaired' : 'needs an insecure baseline'}
        />
      </div>
      {data.total_evaluations === 0 && (
        <p className="text-sm text-ash">
          No evaluations yet. These numbers come from your own runs.{' '}
          <ButtonLink href="/workbench" variant="ghost" size="sm" className="ml-1 text-apple-500">
            Run the first one
          </ButtonLink>
        </p>
      )}
    </div>
  )
}
