import { cn } from '@/lib/format'

/** SecureReflex glyph: a shield outline with a reflexion loop arrow (original artwork). */
export function LogoGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn('h-6 w-6', className)} aria-hidden="true" focusable="false">
      <path
        d="M12 2.5 4 5.5v6.2c0 4.7 3.3 8.6 8 9.8 4.7-1.2 8-5.1 8-9.8V5.5l-8-3Z"
        fill="none"
        stroke="#a8ff53"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M15.6 10.2a3.8 3.8 0 1 0-.9 4.3" fill="none" stroke="#a8ff53" strokeWidth="1.6" strokeLinecap="round" />
      <path d="m15.9 7.6-.2 2.8-2.7-.4" fill="none" stroke="#a8ff53" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <LogoGlyph />
      <span className="font-display text-[17px] font-medium tracking-display text-bone">
        SecureReflex <span className="text-apple-500">AI</span>
      </span>
    </span>
  )
}
