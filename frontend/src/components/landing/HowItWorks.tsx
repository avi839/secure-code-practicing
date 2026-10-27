'use client'

import { Bot, BrainCircuit, ScanSearch, Wrench } from 'lucide-react'
import { Fragment, useEffect, useState } from 'react'
import { cn } from '@/lib/format'
import { useReducedMotion } from '@/lib/useReducedMotion'

const STEPS = [
  {
    icon: Bot,
    tag: 't0',
    title: 'Generate or paste',
    body: 'An AI provider writes code for your task, or you paste your own. This is the baseline version t0.',
  },
  {
    icon: ScanSearch,
    tag: 'scan',
    title: 'Scan',
    body: 'Built-in rules for 8 languages plus Bandit for Python flag CWE-mapped issues with severity, line and reasoning.',
  },
  {
    icon: BrainCircuit,
    tag: 'reflect',
    title: 'Reflect',
    body: 'The findings are fed back to the model with the previous code and an instruction to fix them without new issues.',
  },
  {
    icon: Wrench,
    tag: 't1…tN',
    title: 'Repair & measure',
    body: 'Each repaired version is re-scanned. Repair@t, Regression@t and NetGain@t are computed against t0.',
  },
]

const STEP_MS = 2600

/** Animated 4-step explainer; the active step cycles unless reduced motion is requested. */
export function HowItWorks() {
  const reduced = useReducedMotion()
  const [active, setActive] = useState(0)

  useEffect(() => {
    if (reduced) return
    const timer = setInterval(() => setActive((a) => (a + 1) % STEPS.length), STEP_MS)
    return () => clearInterval(timer)
  }, [reduced])

  return (
    <ol className="grid gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] md:gap-0">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const on = !reduced && active === i
        return (
          <Fragment key={step.title}>
            <li
              className={cn(
                'relative rounded border bg-charcoal-850/60 p-5 transition-colors duration-300',
                on ? 'border-apple-500/60' : 'border-steel',
              )}
              aria-current={on ? 'step' : undefined}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    'flex h-9 w-9 items-center justify-center rounded border transition-colors duration-300',
                    on ? 'border-apple-500/50 bg-apple-500/10 text-apple-500' : 'border-hairline bg-ink text-syntax-violet',
                  )}
                  aria-hidden="true"
                >
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <span className="font-mono text-xs text-fog">
                  <span className="sr-only">Step {i + 1}: </span>
                  {step.tag}
                </span>
              </div>
              <h3 className="mt-4 text-lg font-medium">{step.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ash">{step.body}</p>
            </li>
            {i < STEPS.length - 1 && (
              <li aria-hidden="true" className="flex items-center justify-center md:px-1">
                <span className="moving-line hidden h-px w-8 md:block" style={{ animationDelay: `${i * 400}ms` }} />
                <span className="moving-line-y block h-6 w-px md:hidden" style={{ animationDelay: `${i * 400}ms` }} />
              </li>
            )}
          </Fragment>
        )
      })}
    </ol>
  )
}
