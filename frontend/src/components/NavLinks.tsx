'use client'

import { BarChart3, FlaskConical, History, Home } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/format'

const LINKS = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/workbench', label: 'Workbench', icon: FlaskConical },
  { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { href: '/history', label: 'History', icon: History },
]

export function NavLinks() {
  const pathname = usePathname()
  return (
    <ul className="flex items-center gap-0.5">
      {LINKS.map(({ href, label, icon: Icon }) => {
        const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
        return (
          <li key={href}>
            <Link
              href={href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'relative inline-flex h-9 items-center gap-2 rounded px-2.5 text-sm transition-colors duration-150 sm:px-3',
                active ? 'font-medium text-bone' : 'text-ash hover:bg-charcoal-750 hover:text-cloud',
              )}
            >
              <Icon className={cn('h-4 w-4', active ? 'text-apple-500' : 'text-fog')} aria-hidden="true" />
              <span className="hidden sm:inline">{label}</span>
              <span className="sr-only sm:hidden">{label}</span>
              {active && <span className="absolute inset-x-2 -bottom-[13px] h-px bg-apple-500" aria-hidden="true" />}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
