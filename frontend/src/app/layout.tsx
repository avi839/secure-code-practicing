import type { Metadata, Viewport } from 'next'
import { AppShell } from '@/components/AppShell'
import './globals.css'

// Fonts are self-hosted from /public/fonts via @font-face in globals.css
// (no Google-hosted font loader: builds must work offline, decision D4).

export const metadata: Metadata = {
  title: {
    default: 'SecureReflex AI · Reflexion-based secure code repair',
    template: '%s · SecureReflex AI',
  },
  description:
    'Generate or paste code, scan it for CWE-mapped vulnerabilities and let a reflexion loop repair it round by round, with Repair@t, Regression@t and NetGain@t metrics.',
}

export const viewport: Viewport = {
  themeColor: '#1c1e21',
  colorScheme: 'dark',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preload" href="/fonts/Geist-Variable.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/Satoshi-Medium.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
