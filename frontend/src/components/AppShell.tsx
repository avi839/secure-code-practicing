import { ExternalLink, ShieldAlert } from 'lucide-react'
import Link from 'next/link'
import type { ReactNode } from 'react'
import { BackendStatus } from './BackendStatus'
import { Logo } from './Logo'
import { NavLinks } from './NavLinks'

export const PAPER_URL = 'https://arxiv.org/abs/2511.03898'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 border-b border-steel bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <Link href="/" className="rounded" aria-label="SecureReflex AI home">
            <Logo />
          </Link>
          <nav aria-label="Main">
            <NavLinks />
          </nav>
          <BackendStatus />
        </div>
      </header>

      <main id="main" tabIndex={-1} className="flex-1 focus:outline-none">
        {children}
      </main>

      <footer className="border-t border-steel bg-ink">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-sm sm:px-6 md:grid-cols-[1fr_auto]">
          <div className="space-y-2">
            <Logo />
            <p className="max-w-xl text-ash">
              Reflexion-based secure code generation: scan, reflect, repair and measure Repair@t, Regression@t and NetGain@t.
              Method inspired by{' '}
              <a
                href={PAPER_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[#7bbcf3] underline-offset-4 hover:underline"
              >
                arXiv 2511.03898
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
              .
            </p>
          </div>
          <div className="space-y-2 text-ash md:max-w-sm">
            <p className="flex items-start gap-2">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-sev-medium" aria-hidden="true" />
              <span>Automated analysis cannot guarantee complete security. Review every change before shipping it.</span>
            </p>
            <p className="flex items-start gap-2">
              <span className="led mt-1.5 bg-sev-medium" aria-hidden="true" />
              <span>
                This build has <strong className="font-medium text-cloud">no authentication</strong>. Run it locally or behind
                your own access control.
              </span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
