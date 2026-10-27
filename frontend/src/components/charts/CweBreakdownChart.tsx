'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { CweBreakdownItem } from '@/lib/types'
import { ChartFrame, LegendItem } from './ChartFrame'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE } from './theme'

/** Horizontal bars per CWE: found at t0 vs fixed by the final version. */
export function CweBreakdownChart({ data, className, limit = 8 }: { data: CweBreakdownItem[]; className?: string; limit?: number }) {
  const reduced = useReducedMotion()
  const rows = [...data].sort((a, b) => b.found - a.found).slice(0, limit)
  return (
    <ChartFrame
      className={className}
      title="CWE breakdown"
      description={`Top ${Math.min(limit, rows.length || limit)} weakness classes: found at t0 versus fixed by the final version.`}
      empty={rows.length === 0}
      heightClass={rows.length > 5 ? 'h-80' : 'h-72'}
      legend={
        <div className="flex flex-wrap gap-4">
          <LegendItem color={CHART_COLORS.found} label="Found" />
          <LegendItem color={CHART_COLORS.fixed} label="Fixed" />
        </div>
      }
      table={{
        columns: ['CWE', 'Name', 'Found', 'Fixed', 'Remaining'],
        rows: rows.map((r) => [r.cwe_id, r.cwe_name ?? '', r.found, r.fixed, r.remaining]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }} barGap={2}>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={CHART_AXIS_TICK} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis type="category" dataKey="cwe_id" width={72} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            labelStyle={CHART_TOOLTIP_LABEL_STYLE}
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            labelFormatter={(label: string) => {
              const row = rows.find((r) => r.cwe_id === label)
              return row?.cwe_name ? `${label} · ${row.cwe_name}` : label
            }}
          />
          <Bar dataKey="found" name="Found" fill={CHART_COLORS.found} radius={[0, 3, 3, 0]} isAnimationActive={!reduced} />
          <Bar dataKey="fixed" name="Fixed" fill={CHART_COLORS.fixed} radius={[0, 3, 3, 0]} isAnimationActive={!reduced} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
