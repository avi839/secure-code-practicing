'use client'

import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/lib/format'

export interface TabItem {
  id: string
  label: ReactNode
  icon?: ReactNode
  badge?: ReactNode
  content: ReactNode
}

interface TabsProps {
  items: TabItem[]
  value: string
  onChange: (id: string) => void
  label: string
  className?: string
}

/** WAI-ARIA tabs: roving tabindex, ArrowLeft/ArrowRight/Home/End, automatic activation. */
export function Tabs({ items, value, onChange, label, className }: TabsProps) {
  const baseId = useId()
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  const activeIndex = Math.max(
    0,
    items.findIndex((item) => item.id === value),
  )

  const focusTab = (index: number) => {
    const next = (index + items.length) % items.length
    onChange(items[next].id)
    refs.current[next]?.focus()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    switch (event.key) {
      case 'ArrowRight':
        event.preventDefault()
        focusTab(index + 1)
        break
      case 'ArrowLeft':
        event.preventDefault()
        focusTab(index - 1)
        break
      case 'Home':
        event.preventDefault()
        focusTab(0)
        break
      case 'End':
        event.preventDefault()
        focusTab(items.length - 1)
        break
    }
  }

  const active = items[activeIndex]

  return (
    <div className={className}>
      <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-steel">
        {items.map((item, index) => {
          const selected = index === activeIndex
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[index] = el
              }}
              id={`${baseId}-tab-${item.id}`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
              className={cn(
                'relative -mb-px inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors duration-150',
                selected ? 'border-apple-500 text-bone' : 'border-transparent text-fog hover:text-cloud',
              )}
            >
              {item.icon && <span aria-hidden="true">{item.icon}</span>}
              {item.label}
              {item.badge}
            </button>
          )
        })}
      </div>
      {active && (
        <div
          key={active.id}
          id={`${baseId}-panel-${active.id}`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${active.id}`}
          tabIndex={0}
          className="animate-enter pt-4 focus-visible:outline-offset-4"
        >
          {active.content}
        </div>
      )}
    </div>
  )
}
