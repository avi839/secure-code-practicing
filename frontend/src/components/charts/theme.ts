import type { CSSProperties } from 'react'

// Chart palette from the design reference: Repair = lime, Regression = Mute Red,
// NetGain = Event Violet, gridlines charcoal-700, axes Fog, tooltip on Ink Well.
export const CHART_COLORS = {
  repair: '#a8ff53',
  regression: '#f43f5e',
  netGain: '#7655fd',
  netGainText: '#9c9af2',
  secure: '#a8ff53',
  baseline: '#878c99',
  grid: '#272a2e',
  axis: '#878c99',
  fixed: '#a8ff53',
  found: '#f43f5e',
  remaining: '#fb923c',
}

export const SERIES_PALETTE = ['#a8ff53', '#9c9af2', '#479dec', '#fbbf24', '#e888f8', '#fb923c', '#afec73', '#f43f5e']

export const CHART_AXIS_TICK = { fill: '#878c99', fontSize: 12, fontFamily: 'Geist, system-ui, sans-serif' }

export const CHART_TOOLTIP_STYLE: CSSProperties = {
  background: '#121317',
  border: '1px solid #3b3e45',
  borderRadius: 4,
  color: '#e5e7eb',
  fontSize: 12,
  fontFamily: 'Geist, system-ui, sans-serif',
  boxShadow: 'none',
}

export const CHART_TOOLTIP_LABEL_STYLE: CSSProperties = { color: '#d7d9dd', fontWeight: 500, marginBottom: 4 }

export const CHART_LEGEND_STYLE: CSSProperties = { fontSize: 12, color: '#b5b8c0', paddingTop: 8 }
