import { cn } from '@/lib/format'

interface MarqueeProps {
  items: string[]
  label: string
  className?: string
}

/** Infinite horizontal strip. Pauses on hover/focus; static under reduced motion. */
export function Marquee({ items, label, className }: MarqueeProps) {
  return (
    <div
      className={cn('marquee relative overflow-hidden border-y border-steel bg-ink py-4', className)}
      style={{
        maskImage: 'linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)',
        WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)',
      }}
    >
      <p className="sr-only">
        {label}: {items.join(', ')}
      </p>
      <div className="marquee-track flex w-max animate-marquee gap-3" aria-hidden="true">
        {[0, 1].map((copy) => (
          <div key={copy} className="flex gap-3">
            {items.map((item) => (
              <span
                key={`${copy}-${item}`}
                className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-steel bg-canvas px-3.5 py-1.5 font-mono text-[13px] text-ash"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-apple-500/80" />
                {item}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
