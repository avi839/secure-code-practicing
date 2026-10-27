'use client'

import { Brain, Bug, CheckCircle2, Code2, FileDiff, PlusCircle, RotateCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Badge, SecureBadge, SeverityBadge } from '@/components/ui/Badge'
import { CopyButton } from '@/components/ui/CopyButton'
import { EmptyState } from '@/components/ui/EmptyState'
import { Tabs } from '@/components/ui/Tabs'
import { cn, formatDuration, formatPercent, formatSignedPercent, languageLabel, severitySummary } from '@/lib/format'
import type { CodeVersion, EvaluationDetail, FindingSummary } from '@/lib/types'
import { CodeEditor } from './CodeEditor'
import { DiffView } from './DiffView'
import { FindingCard } from './FindingCard'

const key = (f: { rule_id: string | null; cwe_id: string | null }) => `${f.rule_id ?? ''}|${f.cwe_id ?? ''}`

/** Version in which each finding of `version` gets fixed by a later round. */
function useFixedIn(evaluation: EvaluationDetail, version: CodeVersion): Map<string, string> {
  return useMemo(() => {
    const result = new Map<string, string>()
    const later = evaluation.code_versions.filter((v) => v.round_number > version.round_number)
    for (const finding of version.findings) {
      const k = key(finding)
      const hit = later.find((v) => v.comparison.fixed.some((f) => key(f) === k))
      if (hit) result.set(k, hit.version)
    }
    return result
  }, [evaluation.code_versions, version])
}

function ComparisonList({ title, items, tone, icon }: { title: string; items: FindingSummary[]; tone: 'lime' | 'red' | 'amber'; icon: React.ReactNode }) {
  return (
    <div className="rounded border border-steel bg-ink p-4">
      <h4 className="flex items-center gap-2 font-sans text-sm font-medium tracking-normal text-cloud">
        <span aria-hidden="true">{icon}</span>
        {title}
        <Badge tone={tone}>{items.length}</Badge>
      </h4>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-fog">None</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((f, i) => (
            <li key={`${key(f)}-${i}`} className="flex flex-wrap items-center gap-2 text-sm text-ash">
              {f.severity && <SeverityBadge severity={f.severity} />}
              {f.cwe_id && <span className="font-mono text-xs text-[#7bbcf3]">{f.cwe_id}</span>}
              <span>{f.title ?? f.rule_id}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

interface RoundPanelProps {
  evaluation: EvaluationDetail
  version: CodeVersion
}

/** Details of one code version: Findings | Diff | Code | Reasoning. */
export function RoundPanel({ evaluation, version }: RoundPanelProps) {
  const [tab, setTab] = useState('findings')
  const fixedIn = useFixedIn(evaluation, version)
  const previous = evaluation.code_versions.find((v) => v.round_number === version.round_number - 1)
  const metric = evaluation.metrics.find((m) => m.version === version.version)
  const markers = version.findings
    .filter((f) => f.start_line != null)
    .map((f) => ({ line: f.start_line as number, severity: f.severity, title: `${f.severity} ${f.cwe_id ?? ''} ${f.title}` }))

  const findingsTab = version.findings.length ? (
    <div className="space-y-3">
      {version.findings.map((finding, i) => (
        <FindingCard key={finding.id} finding={finding} index={i} fixedIn={fixedIn.get(key(finding))} defaultOpen={i === 0} />
      ))}
    </div>
  ) : (
    <EmptyState
      icon={<CheckCircle2 className="h-6 w-6 text-apple-500" />}
      title={`${version.version} scans clean`}
      description={
        version.scan_error
          ? `The scan reported an error: ${version.scan_error}`
          : 'No findings at MEDIUM or above, and no LOW findings either. Automated analysis cannot guarantee complete security.'
      }
    />
  )

  const diffTab = previous ? (
    <DiffView oldCode={previous.code} newCode={version.code} oldTitle={previous.version} newTitle={version.version} unifiedDiff={version.diff} />
  ) : (
    <EmptyState
      icon={<FileDiff className="h-6 w-6" />}
      title="Baseline version"
      description="t0 is the starting point, so there is no previous version to diff against. Select a later round to see what changed."
    />
  )

  const codeTab = (
    <CodeEditor
      id={`code-${version.id}`}
      label={`${version.version} source (${languageLabel(evaluation.language)}, read-only)`}
      value={version.code}
      readOnly
      highlightLines={markers}
      minRows={Math.min(24, Math.max(10, version.code.split('\n').length))}
      maxHeightClass="max-h-[560px]"
      toolbar={<CopyButton value={version.code} label={`Copy ${version.version} code`} />}
    />
  )

  const reasoningTab = (
    <div className="space-y-4">
      <div className="rounded border border-steel bg-ink p-4">
        <h4 className="flex items-center gap-2 font-sans text-sm font-medium tracking-normal text-cloud">
          <Brain className="h-4 w-4 text-syntax-violet" aria-hidden="true" />
          {version.round_number === 0 ? 'How t0 was produced' : `What changed in round ${version.round_number}`}
        </h4>
        <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ash">
          {version.explanation || (version.round_number === 0 ? 'Baseline code for the task.' : 'No explanation was recorded for this round.')}
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-fog">Scan result</dt>
            <dd className="mt-1">
              <SecureBadge secure={version.is_secure} />
            </dd>
          </div>
          <div>
            <dt className="text-xs text-fog">Findings</dt>
            <dd className="mt-1 text-cloud">{severitySummary(version.severity_counts)}</dd>
          </div>
          <div>
            <dt className="text-xs text-fog">Generation time</dt>
            <dd className="mt-1 font-mono text-cloud">{formatDuration(version.generation_time_seconds)}</dd>
          </div>
          <div>
            <dt className="text-xs text-fog">Tokens</dt>
            <dd className="mt-1 font-mono text-cloud">{version.tokens_used ?? 'n/a'}</dd>
          </div>
        </dl>
      </div>

      {version.round_number > 0 && (
        <div className="grid gap-3 md:grid-cols-3">
          <ComparisonList title={`Fixed vs ${previous?.version ?? 'previous'}`} items={version.comparison.fixed} tone="lime" icon={<CheckCircle2 className="h-4 w-4 text-apple-500" />} />
          <ComparisonList title="Newly introduced" items={version.comparison.new} tone="red" icon={<PlusCircle className="h-4 w-4 text-mute-red" />} />
          <ComparisonList title="Still present" items={version.comparison.unresolved} tone="amber" icon={<RotateCw className="h-4 w-4 text-sev-medium" />} />
        </div>
      )}

      {metric && (
        <div className="rounded border border-steel bg-ink p-4">
          <h4 className="font-sans text-sm font-medium tracking-normal text-cloud">Metrics for {metric.version} relative to t0</h4>
          <dl className="mt-3 grid grid-cols-3 gap-3">
            <div>
              <dt className="text-xs text-fog">Repair@{metric.round}</dt>
              <dd className={cn('mt-1 font-display text-2xl', metric.repair_defined ? 'text-apple-500' : 'text-fog')}>
                {metric.repair_defined ? formatPercent(metric.repair_rate) : 'n/a'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-fog">Regression@{metric.round}</dt>
              <dd className={cn('mt-1 font-display text-2xl', metric.regression_defined ? 'text-[#ff8197]' : 'text-fog')}>
                {metric.regression_defined ? formatPercent(metric.regression_rate) : 'n/a'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-fog">NetGain@{metric.round}</dt>
              <dd className="mt-1 font-display text-2xl text-syntax-violet">{formatSignedPercent(metric.net_gain)}</dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-fog">
            “n/a” means the denominator is zero: Repair needs an insecure t0, Regression needs a secure t0.
          </p>
        </div>
      )}
    </div>
  )

  return (
    <Tabs
      label={`Details for ${version.version}`}
      value={tab}
      onChange={setTab}
      items={[
        {
          id: 'findings',
          label: 'Findings',
          icon: <Bug className="h-4 w-4" />,
          badge: <Badge tone={version.findings.length ? 'red' : 'lime'}>{version.findings.length}</Badge>,
          content: findingsTab,
        },
        { id: 'diff', label: 'Diff', icon: <FileDiff className="h-4 w-4" />, content: diffTab },
        { id: 'code', label: 'Code', icon: <Code2 className="h-4 w-4" />, content: codeTab },
        { id: 'reasoning', label: 'Reasoning', icon: <Brain className="h-4 w-4" />, content: reasoningTab },
      ]}
    />
  )
}
