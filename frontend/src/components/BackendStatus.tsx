'use client'

import { useEffect, useState } from 'react'
import { getHealth } from '@/lib/api'
import { cn } from '@/lib/format'
import type { HealthResponse } from '@/lib/types'

type State = { kind: 'checking' } | { kind: 'online'; health: HealthResponse } | { kind: 'degraded'; health: HealthResponse } | { kind: 'offline' }

const HEALTH_INTERVAL_MS = 30_000

/** Polls /api/health every 30 s and shows a status pill (LED + text, never colour only). */
export function BackendStatus({ className }: { className?: string }) {
  const [state, setState] = useState<State>({ kind: 'checking' })

  useEffect(() => {
    let cancelled = false
    let controller: AbortController | undefined

    const check = async () => {
      controller?.abort()
      controller = new AbortController()
      try {
        const health = await getHealth(controller.signal)
        if (cancelled) return
        setState(health.status === 'healthy' ? { kind: 'online', health } : { kind: 'degraded', health })
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === 'AbortError')) return
        setState({ kind: 'offline' })
      }
    }

    check()
    const timer = setInterval(check, HEALTH_INTERVAL_MS)
    const onVisible = () => document.visibilityState === 'visible' && check()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      clearInterval(timer)
      controller?.abort()
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  const demo = (state.kind === 'online' || state.kind === 'degraded') && state.health.demo_mode

  const { label, led, tone, title } =
    state.kind === 'online'
      ? {
          label: 'Backend online',
          led: 'led-live',
          tone: 'border-apple-500/30 text-cloud',
          title: `API v${state.health.version} · database ${state.health.components.database.type} · Bandit ${state.health.components.security_scanners.bandit}`,
        }
      : state.kind === 'degraded'
        ? {
            label: 'Backend degraded',
            led: 'bg-sev-medium',
            tone: 'border-sev-medium/40 text-cloud',
            title: state.health.components.database.message ?? 'A backend component is unhealthy.',
          }
        : state.kind === 'offline'
          ? {
              label: 'Backend offline',
              led: 'bg-mute-red',
              tone: 'border-mute-red/40 text-cloud',
              title: 'The API did not respond. Start the backend (START.bat) and check BACKEND_URL.',
            }
          : { label: 'Checking backend', led: 'bg-fog animate-pulse-ring', tone: 'border-hairline text-ash', title: 'Contacting the API…' }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span
        role="status"
        aria-live="polite"
        title={title}
        className={cn('inline-flex items-center gap-2 rounded-full border bg-ink px-3 py-1 text-xs font-medium', tone)}
      >
        <span className={cn('led', led)} aria-hidden="true" />
        <span className="sr-only md:not-sr-only">{label}</span>
      </span>
      {demo && (
        <span
          className="hidden rounded-full border border-syntax-violet/40 bg-syntax-violet/10 px-2.5 py-1 text-xs font-medium text-syntax-violet sm:inline-flex"
          title="DEMO_MODE is enabled: the deterministic demo provider is used instead of live models."
        >
          Demo mode
        </span>
      )}
    </div>
  )
}
