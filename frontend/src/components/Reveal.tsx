'use client'

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { cn } from '@/lib/format'
import { prefersReducedMotion } from '@/lib/useReducedMotion'

interface RevealProps {
  children: ReactNode
  className?: string
  /** Delay in ms (use index * 70 for a stagger). */
  delay?: number
  as?: 'div' | 'section' | 'li'
}

/** Fades a block in (enter keyframe) the first time it scrolls into view. */
export function Reveal({ children, className, delay = 0, as: Tag = 'div' }: RevealProps) {
  const ref = useRef<HTMLElement | null>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.05 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const style: CSSProperties | undefined = delay ? { animationDelay: `${delay}ms` } : undefined

  return (
    <Tag
      ref={(el: HTMLElement | null) => {
        ref.current = el
      }}
      className={cn('reveal', visible && 'reveal-visible', className)}
      style={style}
    >
      {children}
    </Tag>
  )
}
