'use client'

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SEVERITY_META, severityMeta } from '@/lib/format'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { SeverityDistributionItem } from '@/lib/types'
import { ChartFrame, LegendItem } from './ChartFrame'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE } from './theme'

/** Findings per severity at t0 vs the final version (grouped bars). */
export function SeverityDistributionChart({ data, className }: { data: SeverityDistributionItem[]; className?: string }) {
  const reduced = useReducedMotion()
  const rows = data.map((d) => ({ ...d, label: severityMeta(d.severity).label }))
  const empty = data.length === 0 || data.every((d) => d.t0 === 0 && d.final === 0)
  return (
    <ChartFrame
      className={className}
      title="Severity distribution"
      description="Findings by severity in the baseline (t0) versus the final version."
      empty={empty}
      legend={
        <div className="flex flex-wrap gap-4">
          <LegendItem color="#fb923c" label="t0 (bar colour = severity)" />
          <LegendItem color={CHART_COLORS.secure} label="Final" />
        </div>
      }
      table={{ columns: ['Severity', 't0', 'Final'], rows: rows.map((r) => [r.label, r.t0, r.final]) }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -18 }} barGap={4}>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={CHART_AXIS_TICK} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis allowDecimals={false} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="t0" name="t0" radius={[3, 3, 0, 0]} isAnimationActive={!reduced}>
            {rows.map((r) => (
              <Cell key={r.severity} fill={SEVERITY_META[r.severity]?.color ?? '#878c99'} fillOpacity={0.85} />
            ))}
          </Bar>
          <Bar dataKey="final" name="Final" fill={CHART_COLORS.secure} radius={[3, 3, 0, 0]} isAnimationActive={!reduced} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
