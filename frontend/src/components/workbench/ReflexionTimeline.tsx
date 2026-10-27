'use client'

import { Loader2, MinusCircle, ShieldAlert, ShieldCheck } from 'lucide-react'
import { Fragment, useRef, type KeyboardEvent } from 'react'
import { cn, isTerminalStatus, plural } from '@/lib/format'
import type { CodeVersion, EvaluationDetail } from '@/lib/types'

type NodeState = 'secure' | 'insecure' | 'active' | 'pending' | 'skipped'

interface TimelineNode {
  version: string
  round: number
  state: NodeState
  data?: CodeVersion
}

export function buildTimeline(evaluation: EvaluationDetail): TimelineNode[] {
  const byVersion = new Map(evaluation.code_versions.map((v) => [v.version, v]))
  const terminal = isTerminalStatus(evaluation.status)
  const existing = evaluation.code_versions.length
  const total = Math.max(evaluation.requested_rounds + 1, existing)
  return Array.from({ length: total }, (_, k) => {
    const version = `t${k}`
    const data = byVersion.get(version)
    let state: NodeState
    if (data) state = data.is_secure ? 'secure' : 'insecure'
    else if (terminal) state = 'skipped'
    else state = k === existing ? 'active' : 'pending'
    return { version, round: k, state, data }
  })
}

const NODE_STYLE: Record<NodeState, string> = {
  secure: 'border-apple-500 bg-apple-500/10 text-apple-500',
  insecure: 'border-mute-red bg-mute-red/10 text-mute-red',
  active: 'border-fog bg-ink text-fog animate-pulse-ring',
  pending: 'border-dashed border-hairline bg-ink text-fog',
  skipped: 'border-charcoal-500 bg-ink text-charcoal-500',
}

const STATE_TEXT: Record<NodeState, string> = {
  secure: 'secure',
  insecure: 'insecure',
  active: 'in progress',
  pending: 'pending',
  skipped: 'skipped',
}

interface ReflexionTimelineProps {
  evaluation: EvaluationDetail
  selected: string | null
  onSelect: (version: string) => void
}

/** Horizontal stepper t0..tN. Nodes are toggle buttons; ArrowLeft/Right/Home/End move between rounds. */
export function ReflexionTimeline({ evaluation, selected, onSelect }: ReflexionTimelineProps) {
  const nodes = buildTimeline(evaluation)
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  const available = nodes.filter((n) => n.data)
  const newest = available[available.length - 1]?.version
  const focusVersion = selected && available.some((n) => n.version === selected) ? selected : newest

  const move = (event: KeyboardEvent<HTMLButtonElement>, version: string) => {
    const index = available.findIndex((n) => n.version === version)
    let next = -1
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = Math.min(available.length - 1, index + 1)
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = Math.max(0, index - 1)
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = available.length - 1
    if (next < 0) return
    event.preventDefault()
    const target = available[next].version
    onSelect(target)
    refs.current[target]?.focus()
  }

  const running = !isTerminalStatus(evaluation.status)

  return (
    <div className="overflow-x-auto pb-2">
      <ol className="flex min-w-max items-start px-1 pt-1" aria-label="Reflexion timeline">
        {nodes.map((node, i) => {
          const isSelected = node.version === selected
          const next = nodes[i + 1]
          const Icon =
            node.state === 'secure' ? ShieldCheck : node.state === 'insecure' ? ShieldAlert : node.state === 'skipped' ? MinusCircle : Loader2
          const count = node.data?.findings_count
          const description = node.data
            ? `${node.version}${node.round === 0 ? ' baseline' : `, round ${node.round}`}: ${STATE_TEXT[node.state]}, ${plural(count ?? 0, 'finding')}`
            : `${node.version}: ${STATE_TEXT[node.state]}${node.state === 'skipped' && evaluation.stopped_early ? ' (stopped early, previous version is clean)' : ''}`

          return (
            <Fragment key={node.version}>
              <li className="flex w-[84px] shrink-0 flex-col items-center">
                <button
                  ref={(el) => {
                    refs.current[node.version] = el
                  }}
                  type="button"
                  disabled={!node.data}
                  aria-pressed={node.data ? isSelected : undefined}
                  aria-current={running && node.version === newest ? 'step' : undefined}
                  aria-label={description}
                  tabIndex={node.data ? (node.version === focusVersion ? 0 : -1) : -1}
                  onClick={() => node.data && onSelect(node.version)}
                  onKeyDown={(e) => move(e, node.version)}
                  className={cn(
                    'group relative flex h-11 w-11 items-center justify-center rounded-full border-2 transition-colors duration-200',
                    NODE_STYLE[node.state],
                    node.data && 'animate-enter cursor-pointer hover:brightness-125',
                    isSelected && 'outline outline-2 outline-offset-[3px] outline-bone/70',
                    !node.data && 'cursor-default',
                  )}
                >
                  <Icon className={cn('h-5 w-5', node.state === 'active' && 'animate-spin', node.state === 'pending' && 'opacity-0')} aria-hidden="true" />
                </button>
                <span className={cn('mt-2 font-mono text-sm', isSelected ? 'text-bone' : 'text-ash')} aria-hidden="true">
                  {node.version}
                </span>
                <span className="text-xs text-fog" aria-hidden="true">
                  {node.data
                    ? plural(count ?? 0, 'finding')
                    : node.state === 'active'
                      ? 'running…'
                      : node.state === 'skipped'
                        ? evaluation.stopped_early
                          ? 'not needed'
                          : 'skipped'
                        : 'pending'}
                </span>
              </li>
              {next && (
                <li aria-hidden="true" className="mt-[21px] w-10 shrink-0 sm:w-14">
                  <span
                    className={cn(
                      'block h-0.5 w-full rounded-full',
                      next.data
                        ? next.data.is_secure
                          ? 'bg-gradient-to-r from-hairline to-apple-500'
                          : 'bg-gradient-to-r from-hairline to-mute-red/80'
                        : next.state === 'active'
                          ? 'moving-line'
                          : 'border-t border-dashed border-hairline bg-transparent',
                    )}
                  />
                </li>
              )}
            </Fragment>
          )
        })}
      </ol>
    </div>
  )
}
