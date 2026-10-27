'use client'

import dynamic from 'next/dynamic'
import { Columns2, Rows2 } from 'lucide-react'
import { useState } from 'react'
import { CopyButton } from '@/components/ui/CopyButton'
import { cn } from '@/lib/format'

interface DiffViewProps {
  oldCode: string
  newCode: string
  oldTitle: string
  newTitle: string
  /** Unified diff from the backend, shown while the viewer bundle loads. */
  unifiedDiff?: string | null
}

function UnifiedFallback({ diff }: { diff?: string | null }) {
  if (!diff) {
    return (
      <div className="rounded border border-steel bg-ink p-4" role="status">
        <div className="skeleton h-4 w-1/2" />
        <div className="skeleton mt-3 h-4 w-3/4" />
        <span className="sr-only">Loading diff viewer…</span>
      </div>
    )
  }
  return (
    <pre className="max-h-[520px] overflow-auto rounded border border-steel bg-ink p-3 text-[13px] leading-6" aria-label="Unified diff">
      <code>
        {diff.split('\n').map((line, i) => (
          <span
            key={i}
            className={cn(
              'block whitespace-pre',
              line.startsWith('+') && !line.startsWith('+++') && 'bg-apple-500/10 text-apple-300',
              line.startsWith('-') && !line.startsWith('---') && 'bg-mute-red/10 text-[#ff9aac]',
              line.startsWith('@@') && 'text-syntax-violet',
              !/^[+\-@]/.test(line) && 'text-ash',
            )}
          >
            {line || ' '}
          </span>
        ))}
      </code>
    </pre>
  )
}

// react-diff-viewer-continued touches window/emotion at import time: client only.
const ReactDiffViewer = dynamic(() => import('react-diff-viewer-continued'), {
  ssr: false,
  loading: () => <UnifiedFallback />,
})

const DIFF_STYLES = {
  variables: {
    dark: {
      diffViewerBackground: '#121317',
      diffViewerColor: '#d7d9dd',
      diffViewerTitleBackground: '#15171a',
      diffViewerTitleColor: '#d7d9dd',
      diffViewerTitleBorderColor: '#272a2e',
      addedBackground: 'rgba(168, 255, 83, 0.08)',
      addedColor: '#e5e7eb',
      removedBackground: 'rgba(244, 63, 94, 0.10)',
      removedColor: '#e5e7eb',
      changedBackground: 'rgba(251, 191, 36, 0.08)',
      wordAddedBackground: 'rgba(168, 255, 83, 0.25)',
      wordRemovedBackground: 'rgba(244, 63, 94, 0.30)',
      addedGutterBackground: 'rgba(168, 255, 83, 0.12)',
      removedGutterBackground: 'rgba(244, 63, 94, 0.15)',
      gutterBackground: '#0d0e12',
      gutterBackgroundDark: '#0d0e12',
      highlightBackground: 'rgba(118, 85, 253, 0.15)',
      highlightGutterBackground: 'rgba(118, 85, 253, 0.25)',
      codeFoldGutterBackground: '#15171a',
      codeFoldBackground: '#15171a',
      emptyLineBackground: '#121317',
      gutterColor: '#878c99',
      addedGutterColor: '#bfff81',
      removedGutterColor: '#ff9aac',
      codeFoldContentColor: '#b5b8c0',
    },
  },
  contentText: { fontFamily: '"Geist Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', fontSize: '13px', lineHeight: '22px' },
  lineNumber: { fontFamily: '"Geist Mono", ui-monospace, monospace', fontSize: '12px' },
  titleBlock: { fontFamily: '"Geist Mono", ui-monospace, monospace', fontSize: '12px', padding: '8px 12px' },
}

/** Side-by-side (or unified) diff between two code versions. */
export function DiffView({ oldCode, newCode, oldTitle, newTitle, unifiedDiff }: DiffViewProps) {
  const [split, setSplit] = useState(true)

  if (oldCode === newCode) {
    return <p className="rounded border border-steel bg-ink px-4 py-3 text-sm text-ash">No changes: this round returned the same code as {oldTitle}.</p>
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div role="group" aria-label="Diff layout" className="inline-flex rounded border border-hairline p-0.5">
          {[
            { value: true, label: 'Split', icon: Columns2 },
            { value: false, label: 'Unified', icon: Rows2 },
          ].map(({ value, label, icon: Icon }) => (
            <button
              key={label}
              type="button"
              aria-pressed={split === value}
              onClick={() => setSplit(value)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-xs font-medium transition-colors duration-150',
                split === value ? 'bg-charcoal-750 text-bone' : 'text-fog hover:text-cloud',
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
        {unifiedDiff && <CopyButton value={unifiedDiff} label="Copy unified diff" />}
      </div>
      <div className="max-h-[560px] overflow-auto rounded border border-steel" aria-label={`Changes from ${oldTitle} to ${newTitle}`} role="region">
        <ReactDiffViewer
          oldValue={oldCode}
          newValue={newCode}
          splitView={split}
          useDarkTheme
          leftTitle={oldTitle}
          rightTitle={newTitle}
          styles={DIFF_STYLES}
          extraLinesSurroundingDiff={3}
        />
      </div>
    </div>
  )
}
