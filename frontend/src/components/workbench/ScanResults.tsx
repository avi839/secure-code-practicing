'use client'

import { CheckCircle2, ScanLine, X } from 'lucide-react'
import { SecureBadge, SeverityBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { SEVERITIES, languageLabel } from '@/lib/format'
import type { Language, ScanResponse } from '@/lib/types'
import { FindingCard } from './FindingCard'

interface ScanResultsProps {
  result: ScanResponse
  language: Language
  onClose: () => void
}

/** "Scan only" output: findings without a reflexion timeline. */
export function ScanResults({ result, language, onClose }: ScanResultsProps) {
  return (
    <section aria-labelledby="scan-title" className="animate-enter space-y-4">
      <div className="rounded-lg border border-steel bg-charcoal-850/60">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-steel px-5 py-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 font-mono text-xs text-fog">
                <ScanLine className="h-3.5 w-3.5" aria-hidden="true" />
                scan only · {languageLabel(language)}
              </span>
              <SecureBadge secure={result.is_secure} />
            </div>
            <h2 id="scan-title" className="mt-2 font-sans text-lg font-medium tracking-normal">
              {result.findings.length === 0 ? 'No findings' : `${result.findings.length} finding${result.findings.length === 1 ? '' : 's'}`}
            </h2>
            <p className="mt-1 text-xs text-fog">Analyzers: {result.analyzers_run.join(', ') || 'none'}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} icon={<X className="h-3.5 w-3.5" />}>
            Clear
          </Button>
        </div>
        <ul className="flex flex-wrap gap-2 px-5 py-3" aria-label="Findings by severity">
          {SEVERITIES.map((s) => (
            <li key={s} className="inline-flex items-center gap-1.5 text-sm text-ash">
              <SeverityBadge severity={s} />
              <span className="tabular-nums">{result.severity_counts[s] ?? 0}</span>
            </li>
          ))}
        </ul>
        {result.errors.length > 0 && (
          <div className="border-t border-steel px-5 py-3 text-sm text-sev-medium" role="alert">
            {result.errors.map((e, i) => (
              <p key={i}>{e}</p>
            ))}
          </div>
        )}
      </div>

      {result.findings.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-6 w-6 text-apple-500" />}
          title="The code scans clean"
          description="No rule matched. Automated analysis cannot guarantee complete security; review the code as well."
        />
      ) : (
        <div className="space-y-3">
          {result.findings.map((f, i) => (
            <FindingCard key={`${f.rule_id}-${f.start_line}-${i}`} finding={f} index={i} defaultOpen={i === 0} />
          ))}
        </div>
      )}
    </section>
  )
}
