'use client'

import { useEffect, useMemo, useState } from 'react'
import { CopyButton } from '@/components/ui/CopyButton'
import { cn } from '@/lib/format'
import { prefersReducedMotion } from '@/lib/useReducedMotion'

// Token colours (syntax palette is only used inside code contexts).
const K = 'text-syntax-violet' // keywords
const F = 'text-syntax-lime' // functions / identifiers
const S = 'text-syntax-pink' // strings
const T = 'text-syntax-green' // literals
const P = 'text-syntax-magenta' // decorators / properties
const D = 'text-cloud' // default

type Segment = [string, string]
type Kind = 'ctx' | 'vuln' | 'fix'
interface Line {
  kind: Kind
  segments: Segment[]
}

const LINES: Line[] = [
  { kind: 'ctx', segments: [['@app', P], ['.route(', D], ['"/users/<username>"', S], [')', D]] },
  { kind: 'ctx', segments: [['def ', K], ['get_user', F], ['(username):', D]] },
  { kind: 'ctx', segments: [['    conn ', D], ['= ', K], ['get_connection', F], ['()', D]] },
  { kind: 'vuln', segments: [['    query ', D], ['= ', K], ['f"SELECT * FROM users WHERE name = \'{username}\'"', S]] },
  { kind: 'vuln', segments: [['    row ', D], ['= ', K], ['conn.', D], ['execute', F], ['(query).', D], ['fetchone', F], ['()', D]] },
  { kind: 'fix', segments: [['    row ', D], ['= ', K], ['conn.', D], ['execute', F], ['(', D]] },
  { kind: 'fix', segments: [['        "SELECT * FROM users WHERE name = ?"', S], [', (username,)', D]] },
  { kind: 'fix', segments: [['    ).', D], ['fetchone', F], ['()', D]] },
  {
    kind: 'ctx',
    segments: [['    return ', K], ['jsonify', F], ['(', D], ['dict', F], ['(row)) ', D], ['if ', K], ['row ', D], ['else ', K], ['(', D], ['""', S], [', ', D], ['404', T], [')', D]],
  },
]

const lineText = (line: Line) => line.segments.map(([text]) => text).join('')
const ORIGINAL = LINES.map((line, i) => ({ line, i })).filter(({ line }) => line.kind !== 'fix')
const FIX = LINES.map((line, i) => ({ line, i })).filter(({ line }) => line.kind === 'fix')

type Phase = 'typing' | 'flag' | 'fixing' | 'done'

const CHAR_MS = 22
const FLAG_MS = 1500
const HOLD_MS = 4200
const EXIT_MS = 220

function renderSegments(segments: Segment[], visible: number) {
  const out: JSX.Element[] = []
  let remaining = visible
  segments.forEach(([text, cls], idx) => {
    if (remaining <= 0) return
    const shown = text.slice(0, remaining)
    remaining -= shown.length
    out.push(
      <span key={idx} className={cls}>
        {shown}
      </span>,
    )
  })
  return out
}

/** Hero code pane: types a vulnerable Flask handler, flags CWE-89, then types the parameterized fix. */
export function HeroCode() {
  const [phase, setPhase] = useState<Phase>('typing')
  const [typed, setTyped] = useState(0)
  const [typedFix, setTypedFix] = useState(0)
  const [leaving, setLeaving] = useState(false)

  const offsets = useMemo(() => {
    const build = (items: { line: Line; i: number }[]) => {
      const map = new Map<number, number>()
      let acc = 0
      items.forEach(({ line, i }) => {
        map.set(i, acc)
        acc += lineText(line).length
      })
      return { map, total: acc }
    }
    return { original: build(ORIGINAL), fix: build(FIX) }
  }, [])

  useEffect(() => {
    if (prefersReducedMotion()) {
      setTyped(offsets.original.total)
      setTypedFix(offsets.fix.total)
      setPhase('done')
      return
    }
    let timer: ReturnType<typeof setTimeout>
    let current: Phase = 'typing'
    let a = 0
    let b = 0

    const run = () => {
      if (current === 'typing') {
        a = Math.min(offsets.original.total, a + 2)
        setTyped(a)
        if (a >= offsets.original.total) {
          current = 'flag'
          setPhase('flag')
          timer = setTimeout(() => {
            current = 'fixing'
            setPhase('fixing')
            run()
          }, FLAG_MS)
          return
        }
        timer = setTimeout(run, CHAR_MS)
      } else if (current === 'fixing') {
        b = Math.min(offsets.fix.total, b + 2)
        setTypedFix(b)
        if (b >= offsets.fix.total) {
          current = 'done'
          setPhase('done')
          timer = setTimeout(() => {
            // Fade the pane out (exit keyframe) before the loop restarts.
            setLeaving(true)
            timer = setTimeout(() => {
              a = 0
              b = 0
              current = 'typing'
              setTyped(0)
              setTypedFix(0)
              setPhase('typing')
              setLeaving(false)
              run()
            }, EXIT_MS)
          }, HOLD_MS)
          return
        }
        timer = setTimeout(run, CHAR_MS)
      }
    }
    timer = setTimeout(run, 400)
    return () => clearTimeout(timer)
  }, [offsets])

  const flagged = phase !== 'typing'
  const showFix = phase === 'fixing' || phase === 'done'

  // Index of the line that currently carries the cursor.
  let cursorLine = -1
  if (phase === 'typing') {
    for (const { line, i } of ORIGINAL) {
      const start = offsets.original.map.get(i) ?? 0
      if (typed < start + lineText(line).length || i === ORIGINAL[ORIGINAL.length - 1].i) {
        cursorLine = i
        break
      }
    }
  } else if (phase === 'fixing') {
    for (const { line, i } of FIX) {
      const start = offsets.fix.map.get(i) ?? 0
      if (typedFix < start + lineText(line).length || i === FIX[FIX.length - 1].i) {
        cursorLine = i
        break
      }
    }
  }

  const fullCode = LINES.filter((l) => l.kind !== 'vuln').map(lineText).join('\n')
  let lineNo = 0

  return (
    <figure className="relative overflow-hidden rounded-lg border border-hairline bg-ink">
      <figcaption className="sr-only">
        Example repair: a Flask handler builds an SQL query with an f-string (CWE-89, SQL injection). The reflexion round replaces it with a
        parameterized query and the re-scan reports zero findings.
      </figcaption>
      <div className="flex items-center justify-between border-b border-steel px-4 py-2.5">
        <div className="flex items-center gap-2" aria-hidden="true">
          <span className="h-2.5 w-2.5 rounded-full bg-charcoal-600" />
          <span className="h-2.5 w-2.5 rounded-full bg-charcoal-600" />
          <span className="h-2.5 w-2.5 rounded-full bg-charcoal-600" />
          <span className="ml-3 font-mono text-xs text-fog">app.py</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-fog" aria-hidden="true">
            {showFix ? 't1' : 't0'}
          </span>
          <CopyButton value={fullCode} label="Copy repaired example code" />
        </div>
      </div>

      <pre className={cn('min-h-[240px] overflow-x-auto py-3 text-code', leaving && 'animate-exit')} aria-hidden="true">
        <code className="block min-w-max">
          {LINES.map((line, i) => {
            const isFix = line.kind === 'fix'
            if (isFix && !showFix) return null
            const text = lineText(line)
            const visible = isFix
              ? Math.max(0, Math.min(text.length, typedFix - (offsets.fix.map.get(i) ?? 0)))
              : Math.max(0, Math.min(text.length, typed - (offsets.original.map.get(i) ?? 0)))
            if (visible === 0 && cursorLine !== i) return null
            const removed = line.kind === 'vuln' && flagged
            lineNo += line.kind === 'vuln' && showFix ? 0 : 1
            return (
              <div
                key={i}
                className={cn(
                  'flex px-4 transition-colors duration-300',
                  removed && 'bg-mute-red/10',
                  isFix && 'bg-apple-500/[0.08] animate-enter',
                )}
              >
                <span className="w-7 shrink-0 select-none text-right text-charcoal-500">{removed && showFix ? '' : lineNo}</span>
                <span className={cn('w-5 shrink-0 select-none text-center', removed ? 'text-mute-red' : isFix ? 'text-apple-500' : 'text-transparent')}>
                  {removed ? '-' : isFix ? '+' : ' '}
                </span>
                <span className={cn('whitespace-pre', removed && showFix && 'line-through decoration-mute-red/60 opacity-70')}>
                  {renderSegments(line.segments, visible)}
                  {cursorLine === i && <span className="cursor-blink ml-px" />}
                </span>
              </div>
            )
          })}
        </code>
      </pre>

      <div className="border-t border-steel px-4 py-3 font-mono text-[13px] leading-6" aria-hidden="true">
        <p className="text-fog">
          <span className="text-apple-500">$</span> securereflex scan app.py --rounds 3
        </p>
        {flagged && (
          <p className="animate-enter text-[#ff8197]">
            ✗ t0 CWE-89 SQL injection <span className="text-fog">(line 4)</span> · critical
          </p>
        )}
        {phase === 'done' && (
          <p className="animate-enter text-apple-500">
            ✓ t1 re-scan: 0 findings · secure <span className="text-fog">· stopped early</span>
          </p>
        )}
      </div>
    </figure>
  )
}
