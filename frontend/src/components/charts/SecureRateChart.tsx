'use client'

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useReducedMotion } from '@/lib/useReducedMotion'
import type { ReflexionCurvePoint } from '@/lib/types'
import { ChartFrame } from './ChartFrame'
import { CHART_AXIS_TICK, CHART_COLORS, CHART_TOOLTIP_LABEL_STYLE, CHART_TOOLTIP_STYLE } from './theme'

const pct = (v: number) => `${v.toFixed(0)}%`

/** Share of completed evaluations whose version t is secure. */
export function SecureRateChart({ data, className }: { data: ReflexionCurvePoint[]; className?: string }) {
  const reduced = useReducedMotion()
  return (
    <ChartFrame
      className={className}
      title="Secure rate by round"
      description="Percentage of completed evaluations whose code is secure at each version."
      empty={data.length === 0}
      table={{ columns: ['Version', 'Secure rate'], rows: data.map((p) => [p.version, pct(p.secure_rate)]) }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="secure-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.secure} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_COLORS.secure} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="version" tick={CHART_AXIS_TICK} axisLine={{ stroke: CHART_COLORS.grid }} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={pct} tick={CHART_AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={CHART_TOOLTIP_LABEL_STYLE} formatter={(v: number) => [pct(v), 'Secure rate']} />
          <Area
            type="monotone"
            dataKey="secure_rate"
            name="Secure rate"
            stroke={CHART_COLORS.secure}
            strokeWidth={2}
            fill="url(#secure-fill)"
            isAnimationActive={!reduced}
            animationDuration={1100}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
