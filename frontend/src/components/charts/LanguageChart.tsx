'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { languageLabel } from '@/lib/format'
import { useReducedMotion } from '@/lib/useReducedMotion'
import { ChartFrame, LegendItem } from './ChartFrame'
import { CHART_TOOLTIP_STYLE, SERIES_PALETTE } from './theme'

/** Evaluations per language (donut). */
export function LanguageChart({ data, className }: { data: Record<string, number>; className?: string }) {
  const reduced = useReducedMotion()
  const rows = Object.entries(data)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([language, count], i) => ({ language, name: languageLabel(language), count, color: SERIES_PALETTE[i % SERIES_PALETTE.length] }))
  const total = rows.reduce((sum, r) => sum + r.count, 0)

  return (
    <ChartFrame
      className={className}
      title="Languages"
      description="Evaluations per programming language."
      empty={rows.length === 0}
      legend={
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {rows.map((r) => (
            <LegendItem key={r.language} color={r.color} label={`${r.name} · ${r.count}`} />
          ))}
        </div>
      }
      table={{
        columns: ['Language', 'Evaluations', 'Share'],
        rows: rows.map((r) => [r.name, r.count, `${total ? Math.round((r.count / total) * 100) : 0}%`]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} itemStyle={{ color: '#e5e7eb' }} />
          <Pie
            data={rows}
            dataKey="count"
            nameKey="name"
            innerRadius="58%"
            outerRadius="85%"
            paddingAngle={2}
            stroke="#1c1e21"
            strokeWidth={2}
            isAnimationActive={!reduced}
          >
            {rows.map((r) => (
              <Cell key={r.language} fill={r.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
