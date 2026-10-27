'use client'

import { useMemo, useRef, type ReactNode } from 'react'
import { SEVERITIES, cn, severityMeta } from '@/lib/format'
import type { Severity } from '@/lib/types'

export interface LineMarker {
  line: number
  severity: string
  title: string
}

interface CodeEditorProps {
  id: string
  label: ReactNode
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  placeholder?: string
  /** Finding markers rendered in the gutter (aria-hidden; findings are listed elsewhere). */
  highlightLines?: LineMarker[]
  describedBy?: string
  invalid?: boolean
  maxLength?: number
  minRows?: number
  maxHeightClass?: string
  hideLabel?: boolean
  toolbar?: ReactNode
}

/**
 * Accessible code editor: a labelled native <textarea> (no keyboard traps, works with
 * screen readers) with a scroll-synced, aria-hidden line-number gutter.
 */
export function CodeEditor({
  id,
  label,
  value,
  onChange,
  readOnly,
  placeholder,
  highlightLines,
  describedBy,
  invalid,
  maxLength,
  minRows = 14,
  maxHeightClass = 'max-h-[460px]',
  hideLabel,
  toolbar,
}: CodeEditorProps) {
  const gutterRef = useRef<HTMLDivElement>(null)
  const lineCount = Math.max(minRows, value.split('\n').length)

  const markers = useMemo(() => {
    // Keep the most severe marker per line.
    const map = new Map<number, LineMarker>()
    for (const marker of highlightLines ?? []) {
      const existing = map.get(marker.line)
      if (!existing || SEVERITIES.indexOf(marker.severity as Severity) < SEVERITIES.indexOf(existing.severity as Severity)) {
        map.set(marker.line, marker)
      }
    }
    return map
  }, [highlightLines])

  return (
    <div>
      <div className={cn('mb-1.5 flex items-center justify-between gap-2', hideLabel && 'sr-only')}>
        <label htmlFor={id} className="text-sm font-medium text-cloud">
          {label}
        </label>
        {toolbar}
      </div>
      <div
        className={cn(
          'relative overflow-hidden rounded border bg-ink transition-colors duration-150',
          'focus-within:border-apple-500 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-apple-500',
          invalid ? 'border-mute-red' : 'border-hairline',
        )}
      >
        <div
          ref={gutterRef}
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-0 w-14 select-none overflow-hidden border-r border-steel bg-charcoal-950 py-3 text-right font-mono text-code text-fog"
        >
          {Array.from({ length: lineCount }, (_, i) => {
            const marker = markers.get(i + 1)
            const meta = marker ? severityMeta(marker.severity) : null
            return (
              <div key={i} className={cn('flex items-center justify-end gap-1.5 pl-2 pr-3', meta && meta.text)} title={marker?.title}>
                {meta && <span className={cn('h-1.5 w-1.5 rounded-full', meta.bar)} />}
                {i + 1}
              </div>
            )
          })}
        </div>
        <textarea
          id={id}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          onScroll={(e) => {
            if (gutterRef.current) gutterRef.current.scrollTop = e.currentTarget.scrollTop
          }}
          readOnly={readOnly}
          placeholder={placeholder}
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          wrap="off"
          rows={minRows}
          maxLength={maxLength}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          className={cn(
            'block w-full resize-y overflow-auto whitespace-pre bg-transparent py-3 pl-[4.25rem] pr-3 font-mono text-code text-bone outline-none placeholder:text-fog',
            'focus-visible:outline-none',
            maxHeightClass,
            readOnly && 'resize-none text-cloud',
          )}
        />
      </div>
    </div>
  )
}
