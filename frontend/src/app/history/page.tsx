'use client'

import { ArrowRight, ChevronLeft, ChevronRight, ExternalLink, History as HistoryIcon, RefreshCw, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { useCallback, useEffect, useId, useState } from 'react'
import { Badge, SecureBadge, StatusBadge } from '@/components/ui/Badge'
import { Button, ButtonLink } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorBanner } from '@/components/ui/ErrorBanner'
import { Skeleton } from '@/components/ui/Skeleton'
import { deleteEvaluation, errorMessage, listEvaluations } from '@/lib/api'
import { ALL_LANGUAGES, STATUS_LABELS, formatDateTime, formatDuration, languageLabel, providerLabel, relativeTime, truncate } from '@/lib/format'
import type { EvaluationList, EvaluationStatus, EvaluationSummary, Language } from '@/lib/types'

const PAGE_SIZE = 10
const STATUSES = Object.keys(STATUS_LABELS) as EvaluationStatus[]

export default function HistoryPage() {
  const uid = useId()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<EvaluationStatus | ''>('')
  const [language, setLanguage] = useState<Language | ''>('')
  const [data, setData] = useState<EvaluationList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [pendingDelete, setPendingDelete] = useState<EvaluationSummary | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true)
      setError(null)
      try {
        const result = await listEvaluations({ page, page_size: PAGE_SIZE, status: status || undefined, language: language || undefined }, signal)
        setData(result)
        setAnnouncement(`${result.total} evaluation${result.total === 1 ? '' : 's'} found. Page ${result.page}.`)
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    },
    [page, status, language],
  )

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteEvaluation(pendingDelete.id)
      setAnnouncement(`Deleted “${truncate(pendingDelete.task, 60)}”.`)
      setPendingDelete(null)
      // Step back a page if the last row of this page was removed.
      if (data && data.items.length === 1 && page > 1) setPage(page - 1)
      else load()
    } catch (err) {
      setDeleteError(errorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-apple-500">Runs</p>
          <h1 className="mt-2 text-3xl tracking-display">History</h1>
          <p className="mt-2 max-w-2xl text-ash">Every evaluation stored in this instance, newest first.</p>
        </div>
        <ButtonLink href="/workbench" icon={<ArrowRight className="h-4 w-4" />}>
          New run
        </ButtonLink>
      </div>

      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>

      <Card className="mt-8">
        <div className="flex flex-wrap items-end gap-4 border-b border-steel px-5 py-4">
          <div>
            <label htmlFor={`${uid}-status`} className="field-label">
              Status
            </label>
            <select
              id={`${uid}-status`}
              className="field w-44"
              value={status}
              onChange={(e) => {
                setPage(1)
                setStatus(e.target.value as EvaluationStatus | '')
              }}
            >
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor={`${uid}-language`} className="field-label">
              Language
            </label>
            <select
              id={`${uid}-language`}
              className="field w-44"
              value={language}
              onChange={(e) => {
                setPage(1)
                setLanguage(e.target.value as Language | '')
              }}
            >
              <option value="">All languages</option>
              {ALL_LANGUAGES.map((l) => (
                <option key={l} value={l}>
                  {languageLabel(l)}
                </option>
              ))}
            </select>
          </div>
          <Button variant="secondary" className="ml-auto" onClick={() => load()} loading={loading && !!data} icon={<RefreshCw className="h-4 w-4" />}>
            Refresh
          </Button>
        </div>

        {error && (
          <div className="p-5">
            <ErrorBanner title="Could not load history" message={error} onRetry={() => load()} retrying={loading} />
          </div>
        )}
        {deleteError && (
          <div className="px-5 pt-5">
            <ErrorBanner title="Delete failed" message={deleteError} />
          </div>
        )}

        {!data && loading && (
          <div className="divide-y divide-steel" role="status" aria-live="polite">
            <span className="sr-only">Loading history…</span>
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4">
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        )}

        {data && data.items.length === 0 && (
          <div className="p-5">
            <EmptyState
              icon={<HistoryIcon className="h-6 w-6" />}
              title={status || language ? 'No evaluations match these filters' : 'No evaluations yet'}
              description={status || language ? 'Clear the filters to see every run.' : 'Runs you start in the workbench are listed here.'}
              action={
                status || language ? (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setStatus('')
                      setLanguage('')
                      setPage(1)
                    }}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <ButtonLink href="/workbench">Open the workbench</ButtonLink>
                )
              }
            />
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">
                Evaluations, page {data.page} of {totalPages}
              </caption>
              <thead className="border-b border-steel text-xs text-fog">
                <tr>
                  <th scope="col" className="px-5 py-2.5 font-medium">
                    Task
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Language
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Provider
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Status
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Rounds
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Findings t0 → final
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Result
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Created
                  </th>
                  <th scope="col" className="px-5 py-2.5 text-right font-medium">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className={loading ? 'divide-y divide-steel opacity-60 transition-opacity' : 'divide-y divide-steel transition-opacity'}>
                {data.items.map((e, i) => (
                  <tr key={e.id} className="animate-enter transition-colors duration-150 hover:bg-charcoal-750/60" style={{ animationDelay: `${i * 40}ms` }}>
                    <td className="max-w-[320px] px-5 py-3">
                      <Link href={`/workbench?id=${encodeURIComponent(e.id)}`} className="text-cloud underline-offset-4 hover:text-bone hover:underline">
                        {truncate(e.task, 80)}
                      </Link>
                      <span className="block font-mono text-xs text-fog">{e.ai_model}</span>
                    </td>
                    <td className="px-3 py-3 text-ash">{languageLabel(e.language)}</td>
                    <td className="px-3 py-3">
                      <span className="flex items-center gap-1.5 text-ash">
                        {providerLabel(e.ai_provider)}
                        {e.is_demo && <Badge tone="violet">demo</Badge>}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge status={e.status} />
                    </td>
                    <td className="px-3 py-3 font-mono text-ash">
                      {e.completed_rounds}/{e.requested_rounds}
                    </td>
                    <td className="px-3 py-3 font-mono text-ash">
                      {e.total_findings_t0} → {e.total_findings_final}
                      {e.findings_new > 0 && <span className="ml-1 text-[#ff8197]">(+{e.findings_new} new)</span>}
                    </td>
                    <td className="px-3 py-3">
                      <SecureBadge secure={e.final_secure} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-fog">
                      <time dateTime={e.created_at} title={formatDateTime(e.created_at)}>
                        {relativeTime(e.created_at)}
                      </time>
                      {e.total_duration_seconds != null && <span className="block text-xs">{formatDuration(e.total_duration_seconds)}</span>}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3 text-right">
                      <div className="inline-flex gap-1">
                        <ButtonLink href={`/workbench?id=${encodeURIComponent(e.id)}`} variant="ghost" size="sm" icon={<ExternalLink className="h-3.5 w-3.5" />}>
                          Open<span className="sr-only">: {truncate(e.task, 40)}</span>
                        </ButtonLink>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[#ff8197] hover:bg-mute-red/10"
                          icon={<Trash2 className="h-3.5 w-3.5" />}
                          onClick={() => {
                            setDeleteError(null)
                            setPendingDelete(e)
                          }}
                        >
                          Delete<span className="sr-only">: {truncate(e.task, 40)}</span>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > 0 && (
          <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-steel px-5 py-3 text-sm text-ash">
            <span>
              {(data.page - 1) * data.page_size + 1}–{Math.min(data.total, data.page * data.page_size)} of {data.total}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)} icon={<ChevronLeft className="h-4 w-4" />}>
                Previous
              </Button>
              <span className="font-mono text-xs" aria-current="page">
                {page}/{totalPages}
              </span>
              <Button variant="secondary" size="sm" disabled={page >= totalPages || loading} onClick={() => setPage(page + 1)}>
                Next
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </nav>
        )}
      </Card>

      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete this evaluation?"
        description={
          pendingDelete && (
            <>
              <p>
                “{truncate(pendingDelete.task, 120)}” and all of its code versions, findings and metrics will be removed. This cannot be undone.
              </p>
            </>
          )
        }
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
