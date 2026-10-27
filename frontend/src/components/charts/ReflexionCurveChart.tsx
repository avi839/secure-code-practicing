'use client'

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { ReflexionCurvePoint } from '@/lib/types'
import { ChartFrame, LegendItem } from './ChartFrame'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE } from './theme'

const pct = (v: number) => `${v.toFixed(0)}%`

/** Repair@t / Regression@t / NetGain@t per round, aggregated over completed evaluations. */
export function ReflexionCurveChart({ data, className }: { data: ReflexionCurvePoint[]; className?: string }) {
  const reduced = useReducedMotion()
  const rows = data.map((p) => ({ ...p, label: p.version }))
  return (
    <ChartFrame
      className={className}
      title="Reflexion curve"
      description="Repair@t, Regression@t and NetGain@t relative to t0, per round (later rounds carry each run's last label forward)."
      empty={data.length === 0}
      legend={
        <div className="flex flex-wrap gap-4">
          <LegendItem color={CHART_COLORS.repair} label="Repair@t" />
          <LegendItem color={CHART_COLORS.regression} label="Regression@t" />
          <LegendItem color={CHART_COLORS.netGain} label="NetGain@t" />
        </div>
      }
      table={{
        columns: ['Version', 'Repair@t', 'Regression@t', 'NetGain@t'],
        rows: data.map((p) => [
          p.version,
          p.repair_defined ? pct(p.repair_rate) : 'n/a',
          p.regression_defined ? pct(p.regression_rate) : 'n/a',
          pct(p.net_gain),
        ]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={CHART_AXIS_TICK} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis domain={[-100, 100]} ticks={[-100, -50, 0, 50, 100]} tickFormatter={pct} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <ReferenceLine y={0} stroke="#5f6570" />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            labelStyle={CHART_TOOLTIP_LABEL_STYLE}
            formatter={(value: number, name: string) => [pct(value), name]}
            cursor={{ stroke: '#3b3e45' }}
          />
          <Line type="monotone" dataKey="repair_rate" name="Repair@t" stroke={CHART_COLORS.repair} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={!reduced} animationDuration={1100} />
          <Line
            type="monotone"
            dataKey="regression_rate"
            name="Regression@t"
            stroke={CHART_COLORS.regression}
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={!reduced}
            animationDuration={1100}
          />
          <Line
            type="monotone"
            dataKey="net_gain"
            name="NetGain@t"
            stroke={CHART_COLORS.netGain}
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={{ r: 3 }}
            isAnimationActive={!reduced}
            animationDuration={1100}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
