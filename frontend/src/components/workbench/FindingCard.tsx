'use client'

import { CheckCircle2, ChevronDown, ExternalLink, Wrench } from 'lucide-react'
import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties } from 'react'
import { SeverityBadge, Badge } from '@/components/ui/Badge'
import { cn, cweUrl, severityMeta } from '@/lib/format'
import type { ScanFinding } from '@/lib/types'
import { prefersReducedMotion } from '@/lib/useReducedMotion'

interface FindingCardProps {
  finding: ScanFinding & { status?: string }
  index?: number
  /** Version in which a later round fixed this finding (e.g. "t2"). */
  fixedIn?: string | null
  defaultOpen?: boolean
}

const STATUS_TEXT: Record<string, { label: string; tone: 'neutral' | 'red' | 'amber' }> = {
  open: { label: 'Baseline', tone: 'neutral' },
  unresolved: { label: 'Still present', tone: 'amber' },
  newly_introduced: { label: 'Newly introduced', tone: 'red' },
}

// useLayoutEffect warns during SSR; fall back to useEffect there.
const useIsoLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect

/** Expandable region using the accordion-down / accordion-up keyframes. */
function Accordion({ open, id, labelledBy, children }: { open: boolean; id: string; labelledBy: string; children: React.ReactNode }) {
  const innerRef = useRef<HTMLDivElement>(null)
  const [render, setRender] = useState(open)
  const [closing, setClosing] = useState(false)
  const [height, setHeight] = useState<number | null>(null)

  useIsoLayoutEffect(() => {
    if (open) {
      setRender(true)
      setClosing(false)
    } else if (render) {
      // No animationend fires under reduced motion, so unmount straight away.
      if (prefersReducedMotion()) setRender(false)
      else setClosing(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useIsoLayoutEffect(() => {
    if (render && innerRef.current) setHeight(innerRef.current.scrollHeight)
  }, [render, open])

  if (!render) return null

  const style = { '--accordion-height': height ? `${height}px` : 'auto' } as CSSProperties
  return (
    <div
      id={id}
      role="region"
      aria-labelledby={labelledBy}
      style={style}
      className={cn('overflow-hidden', closing ? 'animate-accordion-up' : 'animate-accordion-down')}
      onAnimationEnd={(event) => {
        if (event.target === event.currentTarget && closing) {
          setRender(false)
          setClosing(false)
        }
      }}
    >
      <div ref={innerRef}>{children}</div>
    </div>
  )
}

export function FindingCard({ finding, index = 0, fixedIn, defaultOpen = false }: FindingCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const uid = useId()
  const meta = severityMeta(finding.severity)
  const link = finding.cwe_url || cweUrl(finding.cwe_id)
  const status = finding.status ? STATUS_TEXT[finding.status] : undefined
  const lines =
    finding.start_line != null
      ? finding.end_line != null && finding.end_line !== finding.start_line
        ? `Lines ${finding.start_line}–${finding.end_line}`
        : `Line ${finding.start_line}`
      : null

  return (
    <article
      className="card-hover animate-enter rounded border border-steel bg-charcoal-850/60"
      style={{ animationDelay: `${Math.min(index, 10) * 70}ms`, borderLeftColor: meta.color, borderLeftWidth: 2 }}
      aria-labelledby={`${uid}-title`}
    >
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          {finding.cwe_id &&
            (link ? (
              <a
                href={link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-full border border-aqua/40 bg-aqua/10 px-2 py-0.5 font-mono text-xs text-[#7bbcf3] hover:border-aqua"
              >
                {finding.cwe_id}
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
                <span className="sr-only">
                  {finding.cwe_name ? `: ${finding.cwe_name}` : ''} on cwe.mitre.org (opens in a new tab)
                </span>
              </a>
            ) : (
              <Badge tone="aqua">{finding.cwe_id}</Badge>
            ))}
          {status && <Badge tone={status.tone}>{status.label}</Badge>}
          {fixedIn && (
            <Badge tone="lime" icon={<CheckCircle2 className="h-3.5 w-3.5" />}>
              Fixed in {fixedIn}
            </Badge>
          )}
          {lines && <span className="ml-auto font-mono text-xs text-fog">{lines}</span>}
        </div>

        <h4 id={`${uid}-title`} className="mt-3 font-sans text-[15px] font-medium tracking-normal text-bone">
          {finding.title}
        </h4>
        {finding.cwe_name && <p className="mt-0.5 text-xs text-fog">{finding.cwe_name}</p>}

        {finding.code_snippet && (
          <pre className="mt-3 overflow-x-auto rounded border border-steel bg-ink px-3 py-2 text-[13px] leading-6 text-cloud">
            <code>{finding.code_snippet}</code>
          </pre>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-fog">
          <span>Detected by</span>
          <Badge tone="violet">{finding.analyzer}</Badge>
          {finding.corroborated_by?.map((a) => (
            <Badge key={a} tone="violet" title="Corroborated by a second analyzer">
              + {a}
            </Badge>
          ))}
          {finding.confidence && <span className="ml-1">· confidence {finding.confidence.toLowerCase()}</span>}
          <button
            type="button"
            id={`${uid}-toggle`}
            aria-expanded={open}
            aria-controls={`${uid}-details`}
            onClick={() => setOpen((o) => !o)}
            className="ml-auto inline-flex items-center gap-1 rounded px-2 py-1 text-sm font-medium text-cloud hover:bg-charcoal-750"
          >
            {open ? 'Hide reasoning' : 'Why & how to fix'}
            <ChevronDown className={cn('h-4 w-4 transition-transform duration-200', open && 'rotate-180')} aria-hidden="true" />
          </button>
        </div>
      </div>

      <Accordion open={open} id={`${uid}-details`} labelledBy={`${uid}-toggle`}>
        <div className="grid gap-4 border-t border-steel px-4 py-4 md:grid-cols-2">
          <section>
            <h5 className="flex items-center gap-1.5 font-sans text-xs font-semibold uppercase tracking-wider text-[#ff8197]">
              <meta.icon className="h-3.5 w-3.5" aria-hidden="true" />
              Why it&apos;s vulnerable
            </h5>
            <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed text-ash">{finding.description}</p>
          </section>
          <section>
            <h5 className="flex items-center gap-1.5 font-sans text-xs font-semibold uppercase tracking-wider text-apple-500">
              <Wrench className="h-3.5 w-3.5" aria-hidden="true" />
              {fixedIn ? `How it was fixed (${fixedIn})` : 'How to fix'}
            </h5>
            <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed text-ash">
              {finding.remediation || 'No specific remediation was provided by the analyzer.'}
            </p>
          </section>
        </div>
      </Accordion>
    </article>
  )
}
