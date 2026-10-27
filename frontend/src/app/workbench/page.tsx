'use client'

import { FlaskConical, GitBranch, Plus } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useCallback, useEffect, useState } from 'react'
import { Card, CardHeader } from '@/components/ui/Card'
import { Button, ButtonLink } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorBanner } from '@/components/ui/ErrorBanner'
import { Skeleton, SkeletonBlock } from '@/components/ui/Skeleton'
import { EvaluationSummary } from '@/components/workbench/EvaluationSummary'
import { ReflexionTimeline } from '@/components/workbench/ReflexionTimeline'
import { RoundPanel } from '@/components/workbench/RoundPanel'
import { RunForm } from '@/components/workbench/RunForm'
import { RunLog } from '@/components/workbench/RunLog'
import { ScanResults } from '@/components/workbench/ScanResults'
import { ApiError, cancelEvaluation, createEvaluation, errorMessage, scanCode } from '@/lib/api'
import { STATUS_LABELS, isTerminalStatus } from '@/lib/format'
import { useEvaluationPolling } from '@/lib/usePolling'
import type { CreateEvaluationRequest, EvaluationDetail, Language, ScanRequest, ScanResponse } from '@/lib/types'

export default function WorkbenchPage() {
  return (
    <Suspense fallback={<WorkbenchSkeleton />}>
      <Workbench />
    </Suspense>
  )
}

function WorkbenchSkeleton() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <Skeleton className="h-8 w-48" />
      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        <SkeletonBlock rows={8} label="Loading workbench" />
        <Skeleton className="h-80 w-full" />
      </div>
    </div>
  )
}

function Workbench() {
  const router = useRouter()
  const params = useSearchParams()
  const id = params.get('id')

  const [created, setCreated] = useState<EvaluationDetail | null>(null)
  const [submitting, setSubmitting] = useState<'run' | 'scan' | null>(null)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const [scan, setScan] = useState<{ result: ScanResponse; language: Language } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [follow, setFollow] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')

  const { data, error, loading, refresh } = useEvaluationPolling(id, created)

  // New evaluation -> follow the newest round again.
  useEffect(() => {
    setSelected(null)
    setFollow(true)
    setCancelError(null)
  }, [id])

  const versionCount = data?.code_versions.length ?? 0
  const newest = data?.code_versions[versionCount - 1]?.version ?? null

  // Auto-select the newest version as rounds arrive (unless the user picked an older one).
  useEffect(() => {
    if (!data || !newest) return
    const exists = selected && data.code_versions.some((v) => v.version === selected)
    if (follow || !exists) setSelected(newest)
  }, [data, newest, follow, selected])

  // Screen-reader announcements for status / round progress.
  useEffect(() => {
    if (!data) return
    const total = data.requested_rounds + 1
    const status = STATUS_LABELS[data.status] ?? data.status
    if (isTerminalStatus(data.status)) {
      setAnnouncement(
        data.status === 'completed'
          ? `Evaluation completed. ${data.total_findings_t0} findings at t0, ${data.total_findings_final} in the final version.`
          : `Evaluation ${status.toLowerCase()}.`,
      )
    } else {
      setAnnouncement(`Evaluation ${status.toLowerCase()}. ${versionCount} of up to ${total} versions ready.`)
    }
  }, [data, versionCount])

  const onRun = useCallback(
    async (request: CreateEvaluationRequest) => {
      setSubmitting('run')
      setSubmitError(null)
      setScan(null)
      try {
        const evaluation = await createEvaluation(request)
        setCreated(evaluation)
        router.replace(`/workbench?id=${encodeURIComponent(evaluation.id)}`, { scroll: false })
      } catch (err) {
        setSubmitError(err instanceof ApiError ? err : new ApiError(0, errorMessage(err)))
      } finally {
        setSubmitting(null)
      }
    },
    [router],
  )

  const onScan = useCallback(
    async (request: ScanRequest) => {
      setSubmitting('scan')
      setSubmitError(null)
      try {
        const result = await scanCode(request)
        setScan({ result, language: request.language })
        setAnnouncement(`Scan finished: ${result.findings.length} findings, ${result.is_secure ? 'secure' : 'insecure'}.`)
        if (id) router.replace('/workbench', { scroll: false })
      } catch (err) {
        setSubmitError(err instanceof ApiError ? err : new ApiError(0, errorMessage(err)))
      } finally {
        setSubmitting(null)
      }
    },
    [id, router],
  )

  const onCancel = useCallback(async () => {
    if (!id) return
    setCancelling(true)
    setCancelError(null)
    try {
      await cancelEvaluation(id, 'Cancelled from the workbench')
      refresh()
    } catch (err) {
      setCancelError(errorMessage(err))
    } finally {
      setCancelling(false)
    }
  }, [id, refresh])

  const running = !!data && !isTerminalStatus(data.status)
  const selectedVersion = data?.code_versions.find((v) => v.version === selected) ?? null

  let results: React.ReactNode
  if (scan) {
    results = <ScanResults result={scan.result} language={scan.language} onClose={() => setScan(null)} />
  } else if (id && !data && loading) {
    results = (
      <div className="space-y-4">
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-28 w-full" />
        <SkeletonBlock rows={4} label="Loading evaluation" />
      </div>
    )
  } else if (id && !data && error) {
    results = (
      <ErrorBanner
        title={error.status === 404 ? 'Evaluation not found' : 'Could not load the evaluation'}
        message={error.status === 404 ? 'It may have been deleted. Start a new run or pick one from the history.' : error.message}
        onRetry={error.status === 404 ? undefined : refresh}
      />
    )
  } else if (data) {
    results = (
      <div className="space-y-5">
        <EvaluationSummary evaluation={data} onCancel={onCancel} cancelling={cancelling} />
        {cancelError && <ErrorBanner title="Could not cancel" message={cancelError} />}
        {error && <ErrorBanner title="Connection problem" message={`${error.message} Retrying…`} />}
        <Card>
          <CardHeader
            icon={<GitBranch className="h-4 w-4" />}
            title="Reflexion timeline"
            description={running ? 'Rounds appear as they are committed. Use arrow keys to move between versions.' : 'Select a version to inspect it. Arrow keys move between versions.'}
          />
          <div className="px-5 pb-2 pt-5">
            <ReflexionTimeline
              evaluation={data}
              selected={selected}
              onSelect={(v) => {
                setSelected(v)
                setFollow(v === newest)
              }}
            />
          </div>
          <div className="border-t border-steel px-5 py-5">
            {selectedVersion ? (
              <RoundPanel key={selectedVersion.id} evaluation={data} version={selectedVersion} />
            ) : (
              <SkeletonBlock rows={4} label="Waiting for the first version" />
            )}
          </div>
        </Card>
        <RunLog evaluation={data} />
      </div>
    )
  } else {
    results = (
      <EmptyState
        icon={<FlaskConical className="h-6 w-6" />}
        title="No run yet"
        description="Describe a task or load an example, pick the number of reflexion rounds and press Run reflexion. Results stream in round by round."
      />
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">Workbench</p>
          <h1 className="mt-2 text-3xl tracking-display">Scan, reflect, repair</h1>
          <p className="mt-2 max-w-2xl text-ash">
            Generate code with an AI provider or paste your own, then let the reflexion loop repair it while every round is scanned and measured.
          </p>
        </div>
        {(id || scan) && (
          <Button
            variant="secondary"
            icon={<Plus className="h-4 w-4" />}
            onClick={() => {
              setScan(null)
              setCreated(null)
              setSubmitError(null)
              router.replace('/workbench', { scroll: false })
            }}
          >
            New run
          </Button>
        )}
      </div>

      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
        <Card className="lg:sticky lg:top-20">
          <CardHeader title="Configure a run" description="All fields are sent to the backend through the /api proxy." />
          <div className="p-5">
            <RunForm submitting={submitting} running={running} serverFieldErrors={submitError?.fieldErrors} onRun={onRun} onScan={onScan} />
          </div>
        </Card>

        <div className="min-w-0 space-y-5">
          {submitError && (
            <ErrorBanner
              title={submitError.status === 422 ? 'Please fix the highlighted fields' : 'The request failed'}
              message={submitError.message}
              fieldErrors={submitError.fieldErrors}
            />
          )}
          {results}
          {data && !running && (
            <p className="text-sm text-fog">
              Want the bigger picture?{' '}
              <ButtonLink href="/dashboard" variant="ghost" size="sm" className="text-apple-500">
                Open the dashboard
              </ButtonLink>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
