'use client'

import { BookOpen, Play, ScanLine } from 'lucide-react'
import { useEffect, useId, useMemo, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/Button'
import { getSamples, getSettings } from '@/lib/api'
import { ALL_LANGUAGES, cn, languageLabel } from '@/lib/format'
import type { CreateEvaluationRequest, FieldError, Language, ProviderId, ProviderInfo, Sample, ScanRequest, SettingsResponse } from '@/lib/types'
import { CodeEditor } from './CodeEditor'

const MODEL_PATTERN = /^[\w.\-:/]+$/
const FALLBACK_LIMITS = { max_code_chars: 50000, max_task_chars: 5000 }
const FALLBACK_ROUNDS = { min: 1, max: 10, default: 3 }
const FALLBACK_PROVIDERS: ProviderInfo[] = [
  { id: 'demo', label: 'Demo (offline)', configured: true, default_model: 'demo', effective: 'live' },
]

type Mode = 'generate' | 'paste'

interface RunFormProps {
  submitting: 'run' | 'scan' | null
  running: boolean
  serverFieldErrors?: FieldError[]
  onRun: (request: CreateEvaluationRequest) => void
  onScan: (request: ScanRequest) => void
}

function providerOptionLabel(p: ProviderInfo): string {
  if (p.id === 'demo') return p.label
  if (p.effective === 'live') return `${p.label} – live`
  if (p.effective === 'demo-forced') return `${p.label} – demo (DEMO_MODE)`
  return `${p.label} – demo fallback (no key)`
}

export function RunForm({ submitting, running, serverFieldErrors, onRun, onScan }: RunFormProps) {
  const uid = useId()
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [settingsError, setSettingsError] = useState(false)
  const [samples, setSamples] = useState<Sample[]>([])

  const [task, setTask] = useState('')
  const [mode, setMode] = useState<Mode>('generate')
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState<Language>('python')
  const [provider, setProvider] = useState<ProviderId>('demo')
  const [model, setModel] = useState('')
  const [rounds, setRounds] = useState(FALLBACK_ROUNDS.default)
  const [sampleId, setSampleId] = useState('')
  const [touched, setTouched] = useState(false)
  const [loadedNotice, setLoadedNotice] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    getSettings(controller.signal)
      .then((s) => {
        setSettings(s)
        setRounds(s.rounds.default)
        if (s.providers.some((p) => p.id === s.default_ai_provider)) setProvider(s.default_ai_provider as ProviderId)
      })
      .catch((err) => {
        if (!(err instanceof DOMException && err.name === 'AbortError')) setSettingsError(true)
      })
    getSamples(undefined, controller.signal)
      .then(setSamples)
      .catch(() => undefined)
    return () => controller.abort()
  }, [])

  const limits = settings?.limits ?? FALLBACK_LIMITS
  const roundLimits = settings?.rounds ?? FALLBACK_ROUNDS
  const providers = settings?.providers ?? FALLBACK_PROVIDERS
  const languages = settings?.supported_languages ?? ALL_LANGUAGES
  const selectedProvider = providers.find((p) => p.id === provider)

  // Client-side validation mirrors the backend limits.
  const errors = useMemo(() => {
    const e: Record<string, string> = {}
    const trimmed = task.trim()
    if (trimmed.length < 3) e.task = 'Describe the task in at least 3 characters.'
    else if (trimmed.length > limits.max_task_chars) e.task = `Keep the task under ${limits.max_task_chars} characters.`
    if (mode === 'paste' && !code.trim()) e.code = 'Paste the code to start from, or switch to “AI generates t0”.'
    if (code.length > limits.max_code_chars) e.code = `Code is limited to ${limits.max_code_chars.toLocaleString()} characters.`
    if (model && (model.length > 100 || !MODEL_PATTERN.test(model))) e.model = 'Use letters, digits and . - : / _ only (max 100).'
    return e
  }, [task, mode, code, model, limits])

  // Map server-side 422 field errors onto the inputs as well.
  const serverErrors = useMemo(() => {
    const map: Record<string, string> = {}
    for (const fe of serverFieldErrors ?? []) {
      const key = fe.field.replace(/^body\./, '').split('.')[0]
      const target = key === 'ai_model' ? 'model' : key === 'reflexion_rounds' ? 'rounds' : key
      if (!map[target]) map[target] = fe.message
    }
    return map
  }, [serverFieldErrors])

  const err = (name: string) => (touched ? errors[name] : undefined) ?? serverErrors[name]

  const loadSample = (id: string) => {
    setSampleId(id)
    const sample = samples.find((s) => s.id === id)
    if (!sample) return
    setTask(sample.task)
    setLanguage(sample.language)
    setCode(sample.code)
    setMode('paste')
    setLoadedNotice(`Loaded example “${sample.title}” (${languageLabel(sample.language)}).`)
  }

  const submitRun = (event: FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (Object.keys(errors).length) return
    onRun({
      task: task.trim(),
      language,
      ai_provider: provider,
      ai_model: model.trim() || null,
      reflexion_rounds: rounds,
      code: mode === 'paste' ? code : null,
    })
  }

  const scanDisabledReason =
    mode !== 'paste' || !code.trim() ? 'Choose “Paste my code” (or load an example) to scan code without running reflexion.' : null

  const submitScan = () => {
    if (scanDisabledReason) return
    if (code.length > limits.max_code_chars) {
      setTouched(true)
      return
    }
    onScan({ code, language })
  }

  const busy = submitting !== null

  return (
    <form onSubmit={submitRun} noValidate className="space-y-5" aria-describedby={settingsError ? `${uid}-settings` : undefined}>
      {settingsError && (
        <p id={`${uid}-settings`} className="rounded border border-sev-medium/40 bg-sev-medium/10 px-3 py-2 text-sm text-cloud">
          Could not load settings from the backend; using offline defaults.
        </p>
      )}

      {/* Example loader */}
      <div>
        <label htmlFor={`${uid}-sample`} className="field-label">
          <span className="inline-flex items-center gap-1.5">
            <BookOpen className="h-4 w-4 text-syntax-violet" aria-hidden="true" />
            Load example
          </span>
        </label>
        <select id={`${uid}-sample`} className="field" value={sampleId} onChange={(e) => loadSample(e.target.value)} disabled={!samples.length}>
          <option value="">{samples.length ? 'Choose a curated vulnerable sample…' : 'Loading examples…'}</option>
          {ALL_LANGUAGES.filter((lang) => samples.some((s) => s.language === lang)).map((lang) => (
            <optgroup key={lang} label={languageLabel(lang)}>
              {samples
                .filter((s) => s.language === lang)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} ({s.cwes.join(', ')})
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
        <p className="sr-only" aria-live="polite">
          {loadedNotice}
        </p>
      </div>

      {/* Task */}
      <div>
        <label htmlFor={`${uid}-task`} className="field-label">
          Task description
        </label>
        <textarea
          id={`${uid}-task`}
          className="field min-h-[84px] resize-y"
          rows={3}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="e.g. Look up a user by username in SQLite and return it as JSON"
          aria-invalid={!!err('task') || undefined}
          aria-describedby={`${uid}-task-hint`}
          maxLength={limits.max_task_chars + 200}
        />
        <p id={`${uid}-task-hint`} className={cn('field-hint flex justify-between gap-2', err('task') && 'text-[#ff8197]')}>
          <span>{err('task') ?? 'What should the code do? The AI uses this to generate t0 and to guide repairs.'}</span>
          <span className="tabular-nums" aria-hidden="true">
            {task.trim().length}/{limits.max_task_chars}
          </span>
        </p>
      </div>

      {/* Start from */}
      <fieldset>
        <legend className="field-label">Start from</legend>
        <div className="grid grid-cols-2 gap-2">
          {(
            [
              ['generate', 'AI generates t0'],
              ['paste', 'Paste my code'],
            ] as const
          ).map(([value, text]) => (
            <label
              key={value}
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded border px-3 py-2 text-sm transition-colors duration-150 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-apple-500',
                mode === value ? 'border-apple-500/60 bg-apple-500/[0.06] text-bone' : 'border-hairline text-ash hover:border-[#4a4e56]',
              )}
            >
              <input
                type="radio"
                name={`${uid}-mode`}
                value={value}
                checked={mode === value}
                onChange={() => setMode(value)}
                className="h-4 w-4 accent-[#a8ff53]"
              />
              {text}
            </label>
          ))}
        </div>
      </fieldset>

      {mode === 'paste' && (
        <div className="animate-enter">
          <CodeEditor
            id={`${uid}-code`}
            label="Code (t0)"
            value={code}
            onChange={setCode}
            placeholder="Paste the code you want to scan and repair…"
            invalid={!!err('code')}
            describedBy={`${uid}-code-hint`}
            minRows={12}
            maxHeightClass="max-h-[380px]"
          />
          <p id={`${uid}-code-hint`} className={cn('field-hint flex justify-between gap-2', err('code') && 'text-[#ff8197]')}>
            <span>{err('code') ?? 'Used as t0 instead of AI generation. Tab moves focus out of the editor.'}</span>
            <span className="tabular-nums" aria-hidden="true">
              {code.length.toLocaleString()}/{limits.max_code_chars.toLocaleString()}
            </span>
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`${uid}-language`} className="field-label">
            Language
          </label>
          <select id={`${uid}-language`} className="field" value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
            {languages.map((lang) => (
              <option key={lang} value={lang}>
                {languageLabel(lang)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${uid}-provider`} className="field-label">
            AI provider
          </label>
          <select
            id={`${uid}-provider`}
            className="field"
            value={provider}
            onChange={(e) => setProvider(e.target.value as ProviderId)}
            aria-describedby={`${uid}-provider-hint`}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {providerOptionLabel(p)}
              </option>
            ))}
          </select>
          <p id={`${uid}-provider-hint`} className="field-hint">
            {selectedProvider?.id === 'demo'
              ? 'Deterministic offline provider with curated repairs.'
              : selectedProvider?.effective === 'live'
                ? `Calls the live API (default model ${selectedProvider.default_model}).`
                : 'Runs on the demo provider; the result is labelled as demo output.'}
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={`${uid}-model`} className="field-label">
            Model <span className="font-normal text-fog">(optional)</span>
          </label>
          <input
            id={`${uid}-model`}
            className="field font-mono"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={selectedProvider?.default_model ?? 'provider default'}
            maxLength={100}
            autoComplete="off"
            spellCheck={false}
            aria-invalid={!!err('model') || undefined}
            aria-describedby={`${uid}-model-hint`}
          />
          <p id={`${uid}-model-hint`} className={cn('field-hint', err('model') && 'text-[#ff8197]')}>
            {err('model') ?? 'Leave empty to use the provider default.'}
          </p>
        </div>
        <div>
          <label htmlFor={`${uid}-rounds`} className="field-label flex items-center justify-between">
            <span>Reflexion rounds</span>
            <output htmlFor={`${uid}-rounds`} className="rounded border border-hairline bg-ink px-2 font-mono text-sm text-apple-500">
              {rounds}
            </output>
          </label>
          <input
            id={`${uid}-rounds`}
            type="range"
            min={roundLimits.min}
            max={roundLimits.max}
            step={1}
            value={rounds}
            onChange={(e) => setRounds(Number(e.target.value))}
            className="mt-2 w-full"
            aria-valuetext={`${rounds} round${rounds === 1 ? '' : 's'}`}
            aria-describedby={`${uid}-rounds-hint`}
          />
          <p id={`${uid}-rounds-hint`} className={cn('field-hint', serverErrors.rounds && 'text-[#ff8197]')}>
            {serverErrors.rounds ?? `${roundLimits.min}–${roundLimits.max}. Stops early once a version scans clean.`}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-steel pt-5">
        <div className={cn('rounded', running && 'glow-ring')}>
          <Button type="submit" size="lg" loading={submitting === 'run'} disabled={busy} icon={<Play className="h-4 w-4" />}>
            {submitting === 'run' ? 'Starting…' : 'Run reflexion'}
          </Button>
        </div>
        <Button
          variant="secondary"
          size="lg"
          onClick={submitScan}
          loading={submitting === 'scan'}
          disabled={busy || !!scanDisabledReason}
          aria-describedby={scanDisabledReason ? `${uid}-scan-hint` : undefined}
          icon={<ScanLine className="h-4 w-4" />}
        >
          Scan only
        </Button>
        {scanDisabledReason && (
          <p id={`${uid}-scan-hint`} className="w-full text-xs text-fog">
            {scanDisabledReason}
          </p>
        )}
      </div>
    </form>
  )
}
