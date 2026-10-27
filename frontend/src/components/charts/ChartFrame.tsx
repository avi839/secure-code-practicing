import type { ReactNode } from 'react'
import { cn } from '@/lib/format'

export interface ChartTable {
  columns: string[]
  rows: (string | number)[][]
}

interface ChartFrameProps {
  title: string
  description?: string
  /** Visually hidden data table so the chart content is available to screen readers. */
  table: ChartTable
  heightClass?: string
  empty?: boolean
  emptyText?: string
  legend?: ReactNode
  className?: string
  children: ReactNode
}

/** Accessible chart wrapper: <figure> + <figcaption>, fixed-height plot area, sr-only data table. */
export function ChartFrame({
  title,
  description,
  table,
  heightClass = 'h-72',
  empty,
  emptyText = 'No data yet. Complete an evaluation to populate this chart.',
  legend,
  className,
  children,
}: ChartFrameProps) {
  return (
    <figure className={cn('card-hover flex flex-col rounded border border-steel bg-charcoal-850/60 p-5', className)}>
      <figcaption>
        <span className="block font-display text-base font-medium tracking-display text-bone">{title}</span>
        {description && <span className="mt-1 block text-sm text-fog">{description}</span>}
      </figcaption>
      {legend && <div className="mt-3">{legend}</div>}
      <div className={cn('mt-4 w-full', heightClass)} aria-hidden="true">
        {empty ? (
          <div className="flex h-full items-center justify-center rounded border border-dashed border-hairline text-center text-sm text-fog">
            {emptyText}
          </div>
        ) : (
          children
        )}
      </div>
      {empty ? (
        <p className="sr-only">{emptyText}</p>
      ) : (
        <table className="sr-only">
          <caption>{title}</caption>
          <thead>
            <tr>
              {table.columns.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) =>
                  j === 0 ? (
                    <th key={j} scope="row">
                      {cell}
                    </th>
                  ) : (
                    <td key={j}>{cell}</td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </figure>
  )
}

export function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ash">
      <span
        className="inline-block h-0.5 w-4 rounded-full"
        style={dashed ? { backgroundImage: `linear-gradient(90deg, ${color} 50%, transparent 50%)`, backgroundSize: '6px 2px' } : { background: color }}
        aria-hidden="true"
      />
      {label}
    </span>
  )
}
