import { ArrowRight, BarChart3, FileDiff, GitBranch, Layers, ScrollText, ShieldCheck } from 'lucide-react'
import { HeroCode } from '@/components/landing/HeroCode'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { LiveStats } from '@/components/landing/LiveStats'
import { Marquee } from '@/components/landing/Marquee'
import { Reveal } from '@/components/Reveal'
import { ButtonLink } from '@/components/ui/Button'

const BAND = [
  'Python',
  'JavaScript',
  'Java',
  'C',
  'C++',
  'C#',
  'PHP',
  'Rust',
  'CWE-89 SQL injection',
  'CWE-79 XSS',
  'CWE-78 OS command injection',
  'CWE-798 hard-coded secrets',
  'CWE-22 path traversal',
  'CWE-502 unsafe deserialization',
  'CWE-327 weak crypto',
  'OpenAI',
  'Anthropic',
  'Google Gemini',
  'Offline demo provider',
  'Bandit',
]

const FEATURES = [
  {
    icon: GitBranch,
    title: 'Round-by-round timeline',
    body: 'Watch every reflexion round arrive live: t0 to tN, with findings per version and early stop once the code scans clean.',
  },
  {
    icon: FileDiff,
    title: 'Side-by-side diffs',
    body: 'Each round shows exactly what changed compared with the previous version, next to the reasoning for the change.',
  },
  {
    icon: ScrollText,
    title: 'Findings with reasons',
    body: 'Severity, CWE link, line, snippet, why it is vulnerable and how it was fixed, corroborated across analyzers.',
  },
  {
    icon: BarChart3,
    title: 'Research metrics',
    body: 'Repair@t, Regression@t and NetGain@t relative to t0, with explicit flags when a denominator is zero.',
  },
  {
    icon: Layers,
    title: 'Multi-provider',
    body: 'OpenAI, Anthropic and Gemini over plain HTTPS, with a clearly labelled offline demo fallback when no key is set.',
  },
  {
    icon: ShieldCheck,
    title: 'Safe by default',
    body: 'Keys stay in the backend .env, errors are sanitized, CORS is restricted and every response carries a request ID.',
  },
]

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden" aria-labelledby="hero-title">
        <div className="bg-blueprint pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="glow-orb pointer-events-none absolute -top-40 left-1/2 h-[640px] w-[900px] -translate-x-1/2" aria-hidden="true" />
        <div className="glow-orb-lime pointer-events-none absolute -bottom-40 right-0 h-[420px] w-[520px]" aria-hidden="true" />

        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-24">
          <div className="animate-enter-slow">
            <span className="inline-flex items-center gap-2 rounded-full border border-apple-500/30 bg-apple-500/[0.06] px-3 py-1 text-xs font-medium text-apple-400">
              <span className="led led-live" aria-hidden="true" />
              Reflexion loop · scan → reflect → repair
            </span>
            <h1 id="hero-title" className="mt-6 text-[clamp(2.25rem,5vw,3.75rem)] font-semibold leading-[1.08] tracking-hero">
              Code that finds its flaws
              <br />
              and <span className="text-gradient">repairs itself</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg font-light leading-relaxed text-ash">
              SecureReflex AI generates or ingests code, scans it for CWE-mapped vulnerabilities and runs a reflexion loop that feeds the
              findings back to the model until the code scans clean. Every round is diffed, explained and measured.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/workbench" size="lg" icon={<ArrowRight className="h-4 w-4" />}>
                Open the workbench
              </ButtonLink>
              <ButtonLink href="/dashboard" size="lg" variant="secondary">
                View analytics
              </ButtonLink>
            </div>
            <p className="mt-4 text-sm text-fog">Works offline in demo mode. No API key required to try it.</p>
          </div>
          <div className="animate-enter-slow [animation-delay:150ms]">
            <HeroCode />
          </div>
        </div>
      </section>

      <Marquee items={BAND} label="Supported languages, vulnerability classes and providers" />

      {/* Live stats */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6" aria-labelledby="stats-title">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">Live</p>
          <h2 id="stats-title" className="mt-3 text-3xl tracking-display">
            Your numbers, straight from the API
          </h2>
          <p className="mt-3 max-w-2xl text-ash">
            Aggregated over the evaluations stored in this instance. Nothing here is pre-filled: run an evaluation and the figures move.
          </p>
        </Reveal>
        <Reveal className="mt-8" delay={80}>
          <LiveStats />
        </Reveal>
      </section>

      {/* How it works */}
      <section className="section-fade border-y border-steel" aria-labelledby="how-title">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
          <Reveal>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">How it works</p>
            <h2 id="how-title" className="mt-3 text-3xl tracking-display">
              Four steps per round, up to ten rounds
            </h2>
          </Reveal>
          <Reveal className="mt-10" delay={80}>
            <HowItWorks />
          </Reveal>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6" aria-labelledby="features-title">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">Built for review</p>
          <h2 id="features-title" className="mt-3 text-3xl tracking-display">
            Evidence for every change
          </h2>
        </Reveal>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon
            return (
              <Reveal as="li" key={feature.title} delay={i * 70} className="card-hover rounded border border-steel bg-charcoal-850/60 p-6">
                <span className="flex h-9 w-9 items-center justify-center rounded border border-hairline bg-ink text-syntax-violet" aria-hidden="true">
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <h3 className="mt-4 text-lg">{feature.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ash">{feature.body}</p>
              </Reveal>
            )
          })}
        </ul>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6" aria-labelledby="cta-title">
        <Reveal className="glow-ring edge-glow relative overflow-hidden rounded-lg border border-steel bg-ink px-6 py-12 text-center sm:px-12">
          <div className="glow-orb pointer-events-none absolute inset-0" aria-hidden="true" />
          <h2 id="cta-title" className="relative text-3xl tracking-display">
            Try it on the SQL injection example
          </h2>
          <p className="relative mx-auto mt-3 max-w-xl text-ash">
            Load a curated sample in the workbench, run three reflexion rounds and watch the findings drop to zero.
          </p>
          <div className="relative mt-8 flex justify-center gap-3">
            <ButtonLink href="/workbench" size="lg" icon={<ArrowRight className="h-4 w-4" />}>
              Start a run
            </ButtonLink>
            <ButtonLink href="/history" size="lg" variant="secondary">
              Browse history
            </ButtonLink>
          </div>
        </Reveal>
      </section>
    </>
  )
}
