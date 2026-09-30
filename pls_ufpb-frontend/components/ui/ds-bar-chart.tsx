"use client"

import * as React from "react"
import {
  Bar,
  BarChart as RechartsBarChart,
  Brush,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cva } from "class-variance-authority"
import { BarChart2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useUILocale } from "@/components/ui/ds-locale-provider"
import { formatChartValue, type FormatPreset } from "@/lib/format-utils"
import { measureAxisWidth } from "@/lib/chart-axis-width"

// ── Types ──────────────────────────────────────────────────────────────────

export type BarOrientation = "vertical" | "horizontal"
export type LegendPosition = "top" | "bottom" | "left" | "right"

export interface BarChartKey {
  key: string
  label?: string
  /** Defaults to the next --chart-N token */
  color?: string
}

export interface BarChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: Record<string, string | number>[]
  /** Keys to render as bars — accepts plain strings or { key, label, color } */
  dataKeys: BarChartKey[] | string[]
  /** Object key mapped to the category axis (X on vertical, Y on horizontal) */
  categoryKey: string
  title?: string
  subtitle?: string
  footer?: React.ReactNode
  /** "vertical" = bars point up (default); "horizontal" = bars point right */
  orientation?: BarOrientation
  /** Chart canvas height in px — container width is always 100% */
  height?: number
  showGrid?: boolean
  showLegend?: boolean
  /** @default "bottom" */
  legendPosition?: LegendPosition
  showTooltip?: boolean
  /** Stack all bars into a single column/row */
  stacked?: boolean
  /** Fixed bar thickness in px; recharts auto-sizes when omitted */
  barSize?: number
  /** Round the leading edge of each bar */
  rounded?: boolean
  /** Format the value axis tick labels and tooltip values */
  valueFormatter?: (value: number) => string
  /**
   * Show a range brush below the chart to scroll and zoom the category axis.
   * Works with vertical orientation only. The brush occupies ~30 px of the
   * chart height, so increase `height` accordingly when enabling.
   */
  showBrush?: boolean
  format?: FormatPreset
  decimals?: number
  currency?: string
  abbreviate?: boolean
  /** Show animated skeleton in place of the chart while data loads */
  loading?: boolean
  locale?: UILocale
  /** Label centred on the horizontal (category/value) axis */
  xAxisLabel?: string
  /** Label centred on the vertical (value/category) axis */
  yAxisLabel?: string
}

// ── Constants ──────────────────────────────────────────────────────────────

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
]

const CORNER_RADIUS = 4

const LEGEND_LAYOUT: Record<
  LegendPosition,
  {
    verticalAlign: "top" | "middle" | "bottom"
    align: "left" | "center" | "right"
    layout: "horizontal" | "vertical"
  }
> = {
  top: { verticalAlign: "top", align: "center", layout: "horizontal" },
  bottom: { verticalAlign: "bottom", align: "center", layout: "horizontal" },
  left: { verticalAlign: "middle", align: "left", layout: "vertical" },
  right: { verticalAlign: "middle", align: "right", layout: "vertical" },
}

// ── Skeleton ───────────────────────────────────────────────────────────────

// Vertical orientation skeleton data
const SKELETON_BAR_HEIGHTS = [45, 72, 54, 86, 38, 78, 62, 50]
const SKELETON_YAXIS_WIDTHS = [28, 20, 24, 18]
const SKELETON_XAXIS_WIDTHS = [28, 36, 24, 32, 28, 20, 34, 26]

// Horizontal orientation skeleton data
const SKELETON_H_BAR_WIDTHS = [65, 42, 78, 35, 55, 82, 48]
const SKELETON_H_YAXIS_WIDTHS = [52, 40, 60, 44, 56, 36, 50]
const SKELETON_H_XAXIS_WIDTHS = [24, 20, 28, 18, 24]

interface BarChartSkeletonProps {
  height?: number
  hasTitle?: boolean
  hasSubtitle?: boolean
  hasFooter?: boolean
  orientation?: BarOrientation
  className?: string
}

function BarChartSkeleton({
  height = 280,
  hasTitle = false,
  hasSubtitle = false,
  hasFooter = false,
  orientation = "vertical",
  className,
}: BarChartSkeletonProps) {
  return (
    <div
      className={cn("flex w-full flex-col", className)}
      data-slot="bar-chart-skeleton"
    >
      {(hasTitle || hasSubtitle) && (
        <div className="flex flex-col gap-1.5 px-1 pb-4">
          {hasTitle && (
            <Skeleton
              className="h-3.5 w-44 rounded-md"
              style={{ animationDelay: "0s" }}
            />
          )}
          {hasSubtitle && (
            <Skeleton
              className="mt-0.5 h-2.5 w-28 rounded-md"
              style={{ animationDelay: "0.1s" }}
            />
          )}
        </div>
      )}

      {orientation === "horizontal" ? (
        <div className="relative overflow-hidden" style={{ height }}>
          {/* Faint vertical grid lines */}
          <div className="pointer-events-none absolute top-2 right-1 bottom-8 left-[92px] flex flex-row justify-around">
            {SKELETON_H_XAXIS_WIDTHS.map((_, i) => (
              <Skeleton
                key={i}
                className="h-full w-px opacity-70"
                style={{ animationDelay: `${0.6 + i * 0.15}s` }}
              />
            ))}
          </div>

          {/* Y-axis category labels */}
          <div className="absolute top-2 bottom-8 left-0 flex w-22 flex-col items-end justify-around pr-2">
            {SKELETON_H_YAXIS_WIDTHS.map((w, i) => (
              <Skeleton
                key={i}
                className="h-2.5 rounded-sm"
                style={{ width: w, animationDelay: `${0.5 + i * 0.1}s` }}
              />
            ))}
          </div>

          {/* Horizontal bars — cascade top to bottom */}
          <div className="absolute top-2 right-1 bottom-8 left-[92px] flex flex-col justify-around gap-2 py-1">
            {SKELETON_H_BAR_WIDTHS.map((pct, i) => (
              <Skeleton
                key={i}
                className="flex-1 rounded-r-sm"
                style={{
                  width: `${pct}%`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>

          {/* X-axis value tick labels */}
          <div className="absolute right-1 bottom-0 left-[92px] flex h-7 items-center justify-around">
            {SKELETON_H_XAXIS_WIDTHS.map((w, i) => (
              <Skeleton
                key={i}
                className="h-2.5 rounded-sm"
                style={{ width: w, animationDelay: `${0.05 + i * 0.1}s` }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="relative overflow-hidden" style={{ height }}>
          {/* Faint horizontal grid lines */}
          <div className="pointer-events-none absolute top-2 right-1 bottom-8 left-11 flex flex-col justify-around">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton
                key={i}
                className="h-px w-full opacity-70"
                style={{ animationDelay: `${0.6 + i * 0.15}s` }}
              />
            ))}
          </div>

          {/* Y-axis tick labels */}
          <div className="absolute top-2 bottom-8 left-0 flex w-9 flex-col items-end justify-between pr-1">
            {SKELETON_YAXIS_WIDTHS.map((w, i) => (
              <Skeleton
                key={i}
                className="h-2.5 rounded-sm"
                style={{ width: w, animationDelay: `${0.5 + i * 0.12}s` }}
              />
            ))}
          </div>

          {/* Bars — wave cascade from left to right */}
          <div className="absolute top-2 right-1 bottom-8 left-11 flex items-end gap-2 px-1">
            {SKELETON_BAR_HEIGHTS.map((pct, i) => (
              <Skeleton
                key={i}
                className="flex-1 rounded-t-sm"
                style={{
                  height: `${pct}%`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>

          {/* X-axis tick labels */}
          <div className="absolute right-1 bottom-0 left-11 flex h-7 items-center justify-around">
            {SKELETON_XAXIS_WIDTHS.map((w, i) => (
              <Skeleton
                key={i}
                className="h-2.5 rounded-sm"
                style={{ width: w, animationDelay: `${0.05 + i * 0.1}s` }}
              />
            ))}
          </div>
        </div>
      )}

      {hasFooter && (
        <div className="mt-4 flex items-center gap-2 border-t border-border px-1 pt-3">
          <Skeleton
            className="h-3.5 w-3.5 shrink-0 rounded-full"
            style={{ animationDelay: "0.7s" }}
          />
          <Skeleton
            className="h-2.5 w-36 rounded-md"
            style={{ animationDelay: "0.8s" }}
          />
          <Skeleton
            className="ml-auto h-2.5 w-20 rounded-md"
            style={{ animationDelay: "0.9s" }}
          />
        </div>
      )}
    </div>
  )
}

// ── Variants ───────────────────────────────────────────────────────────────

const chartWrapperVariants = cva("flex w-full flex-col")

const chartHeaderVariants = cva("flex flex-col px-1 pb-4")

const chartTitleVariants = cva(
  "text-sm leading-tight font-semibold text-foreground"
)

const chartSubtitleVariants = cva("mt-0.5 text-xs text-muted-foreground")

const chartFooterVariants = cva(
  "mt-4 flex items-center gap-2 border-t border-border px-1 pt-3 text-xs text-muted-foreground"
)

// ── Custom Tooltip ─────────────────────────────────────────────────────────

interface TooltipPayloadEntry {
  name: string
  value: number
  fill: string
}

function ChartTooltip({
  active,
  payload,
  label,
  fmt,
}: {
  active?: boolean
  payload?: TooltipPayloadEntry[]
  label?: string
  fmt: (v: number) => string
}) {
  if (!active || !payload?.length) return null

  return (
    <div className="min-w-32 rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="mb-1.5 text-xs font-semibold text-foreground">{label}</p>
      <div className="flex flex-col gap-1">
        {payload.map((entry) => (
          <div key={entry.name} className="flex items-center gap-2">
            <span
              className="inline-block size-2 shrink-0 rounded-sm"
              style={{ backgroundColor: entry.fill }}
            />
            <span className="text-xs text-muted-foreground">{entry.name}</span>
            <span className="ml-auto pl-6 text-xs font-semibold text-foreground tabular-nums">
              {fmt(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Custom Legend ──────────────────────────────────────────────────────────

interface LegendPayloadEntry {
  value: string
  color: string
}

function ChartLegend({
  payload,
  hiddenSeries,
  onToggle,
  vertical = false,
}: {
  payload?: LegendPayloadEntry[]
  hiddenSeries?: Set<string>
  onToggle?: (name: string) => void
  vertical?: boolean
}) {
  if (!payload?.length) return null

  return (
    <div
      className={cn(
        "flex gap-y-1",
        vertical
          ? "flex-col px-2 py-1"
          : "flex-wrap items-center justify-center gap-x-4 pt-3"
      )}
    >
      {payload.map((entry, i) => {
        const hidden = hiddenSeries?.has(entry.value)
        return (
          <div
            key={entry.value ?? i}
            role="button"
            tabIndex={0}
            aria-pressed={hidden}
            aria-label={entry.value}
            onClick={() => onToggle?.(entry.value)}
            onKeyDown={(e) =>
              (e.key === "Enter" || e.key === " ") && onToggle?.(entry.value)
            }
            className={cn(
              "flex cursor-pointer items-center gap-1.5 rounded px-1 py-0.5 select-none",
              "transition-opacity focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none",
              hidden ? "opacity-40" : "hover:opacity-70"
            )}
          >
            <span
              className="inline-block size-2 shrink-0 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-muted-foreground">{entry.value}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

function normalizeKeys(raw: BarChartKey[] | string[]): BarChartKey[] {
  return raw.map((k, i) => {
    const color = CHART_COLORS[i % CHART_COLORS.length]
    if (typeof k === "string") return { key: k, label: k, color }
    return { label: k.key, ...k, color: k.color ?? color }
  })
}

// Custom traveller handle for recharts Brush — styled with semantic tokens
function BrushHandle(props: {
  x?: number
  y?: number
  width?: number
  height?: number
}): React.ReactElement {
  const { x = 0, y = 0, width = 8, height = 30 } = props
  const midY = y + height / 2
  return (
    <g>
      <rect
        x={x}
        y={y + 5}
        width={width}
        height={height - 10}
        rx={3}
        fill="var(--card)"
        stroke="var(--border)"
        strokeWidth={1.5}
      />
      <line
        x1={x + 2}
        y1={midY - 3}
        x2={x + width - 2}
        y2={midY - 3}
        stroke="var(--muted-foreground)"
        strokeWidth={1}
        opacity={0.5}
      />
      <line
        x1={x + 2}
        y1={midY + 3}
        x2={x + width - 2}
        y2={midY + 3}
        stroke="var(--muted-foreground)"
        strokeWidth={1}
        opacity={0.5}
      />
    </g>
  )
}

function barRadius(
  orientation: BarOrientation,
  index: number,
  total: number,
  stacked: boolean,
  rounded: boolean
): number | [number, number, number, number] {
  if (!rounded) return 0
  // For stacked charts only the last bar in the stack gets rounded corners
  if (stacked && index < total - 1) return 0
  const r = CORNER_RADIUS
  return orientation === "vertical"
    ? [r, r, 0, 0] // top-left, top-right, bottom-right, bottom-left
    : [0, r, r, 0] // leading edge is the right side
}

// ── BarChart ───────────────────────────────────────────────────────────────

export function BarChart({
  data,
  dataKeys,
  categoryKey,
  title,
  subtitle,
  footer,
  orientation = "vertical",
  height = 280,
  showGrid = true,
  showLegend = false,
  legendPosition = "bottom",
  showTooltip = true,
  stacked = false,
  barSize,
  rounded = true,
  valueFormatter,
  format,
  decimals,
  currency,
  abbreviate,
  showBrush = false,
  loading = false,
  locale: localeProp,
  xAxisLabel,
  yAxisLabel,
  className,
  ...props
}: BarChartProps) {
  const locale = useUILocale(localeProp)
  // Hooks must be called unconditionally before any early returns
  const fmt = React.useCallback(
    (v: number) =>
      formatChartValue(v, {
        format,
        decimals,
        locale,
        currency,
        abbreviate,
        valueFormatter,
      }),
    [valueFormatter, format, decimals, locale, currency, abbreviate]
  )

  const [hiddenSeries, setHiddenSeries] = React.useState<Set<string>>(new Set())
  const toggleSeries = React.useCallback((name: string) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  // Stable identity across renders — an inline arrow function here would give Recharts'
  // Legend a new `content` type every render, forcing it to unmount/remount the legend
  // subtree instead of reconciling it (and dropping click events along the way).
  const renderLegendContent = React.useCallback(
    (props: { payload?: unknown }) => (
      <ChartLegend
        payload={props.payload as LegendPayloadEntry[]}
        hiddenSeries={hiddenSeries}
        onToggle={toggleSeries}
        vertical={legendPosition === "left" || legendPosition === "right"}
      />
    ),
    [hiddenSeries, toggleSeries, legendPosition]
  )

  if (loading) {
    return (
      <BarChartSkeleton
        height={height}
        hasTitle={!!title}
        hasSubtitle={!!subtitle}
        hasFooter={!!footer}
        orientation={orientation}
        className={className}
      />
    )
  }

  if (data.length === 0) {
    return (
      <div
        className={cn(chartWrapperVariants(), className)}
        data-slot="bar-chart"
        {...props}
      >
        {(title || subtitle) && (
          <div className={chartHeaderVariants()} data-slot="bar-chart-header">
            {title && <p className={chartTitleVariants()}>{title}</p>}
            {subtitle && <p className={chartSubtitleVariants()}>{subtitle}</p>}
          </div>
        )}
        <div
          className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border text-muted-foreground"
          data-slot="bar-chart-empty"
          style={{ height }}
        >
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <BarChart2 className="size-5" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">
              {UI_I18N[locale].emptyState.noData}
            </p>
            <p className="mt-0.5 text-xs">
              {UI_I18N[locale].emptyState.dataWillAppear}
            </p>
          </div>
        </div>
        {footer && (
          <div className={chartFooterVariants()} data-slot="bar-chart-footer">
            {footer}
          </div>
        )}
      </div>
    )
  }

  const keys = normalizeKeys(dataKeys)
  const stackId = stacked ? "stack" : undefined

  // recharts layout axis convention is inverted relative to user mental model
  const rechartsLayout =
    orientation === "horizontal" ? "vertical" : "horizontal"

  const axisStyle = {
    fontSize: "12px",
    fill: "var(--muted-foreground)",
  }

  const axisLabelStyle = {
    fontSize: "11px",
    fill: "var(--muted-foreground)",
  }

  // Expand chart margins when axis labels are present to avoid clipping
  const marginBottom = xAxisLabel ? 28 : 4
  const marginLeft = yAxisLabel ? 8 : 4
  // Sized from the actual formatted tick values (not a fixed guess) so
  // abbreviated currency ("R$ 800,0 mi") never wraps or clips — see
  // lib/chart-axis-width.ts. Only feeds the vertical-orientation value axis;
  // horizontal orientation uses a fixed width for its category axis instead.
  const yAxisValues = [
    0,
    ...data.flatMap((d) => keys.map((k) => Number(d[k.key]))),
  ]
  const yAxisWidth = measureAxisWidth(yAxisValues, fmt, {
    padding: yAxisLabel ? 52 : 32,
  })
  const yAxisLabelOffset = yAxisLabel ? 0 : 10

  return (
    <div
      className={cn(chartWrapperVariants(), className)}
      data-slot="bar-chart"
      {...props}
    >
      {(title || subtitle) && (
        <div className={chartHeaderVariants()} data-slot="bar-chart-header">
          {title && <p className={chartTitleVariants()}>{title}</p>}
          {subtitle && <p className={chartSubtitleVariants()}>{subtitle}</p>}
        </div>
      )}

      <ResponsiveContainer
        width="100%"
        height={height}
        data-slot="bar-chart-chart"
      >
        <RechartsBarChart
          data={data}
          layout={rechartsLayout}
          margin={{ top: 4, right: 4, bottom: marginBottom, left: marginLeft }}
          barCategoryGap="30%"
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              horizontal={orientation === "vertical"}
              vertical={orientation === "horizontal"}
            />
          )}

          {orientation === "vertical" ? (
            <>
              <XAxis
                dataKey={categoryKey}
                tick={axisStyle}
                axisLine={false}
                tickLine={false}
                dy={6}
                label={
                  xAxisLabel
                    ? {
                        value: xAxisLabel,
                        position: "insideBottom",
                        offset: -16,
                        style: axisLabelStyle,
                      }
                    : undefined
                }
              />
              <YAxis
                tick={axisStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={fmt}
                width={yAxisWidth}
                label={
                  yAxisLabel
                    ? {
                        value: yAxisLabel,
                        angle: -90,
                        position: "insideLeft",
                        offset: yAxisLabelOffset,
                        style: { ...axisLabelStyle, textAnchor: "middle" },
                      }
                    : undefined
                }
              />
            </>
          ) : (
            <>
              <YAxis
                dataKey={categoryKey}
                type="category"
                tick={axisStyle}
                axisLine={false}
                tickLine={false}
                width={90}
                label={
                  yAxisLabel
                    ? {
                        value: yAxisLabel,
                        angle: -90,
                        position: "insideLeft",
                        offset: yAxisLabelOffset,
                        style: { ...axisLabelStyle, textAnchor: "middle" },
                      }
                    : undefined
                }
              />
              <XAxis
                type="number"
                tick={axisStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={fmt}
                label={
                  xAxisLabel
                    ? {
                        value: xAxisLabel,
                        position: "insideBottom",
                        offset: -16,
                        style: axisLabelStyle,
                      }
                    : undefined
                }
              />
            </>
          )}

          {showTooltip && (
            <Tooltip
              content={<ChartTooltip fmt={fmt} />}
              cursor={{
                fill: "var(--muted)",
                opacity: 0.4,
                radius: 4,
              }}
            />
          )}

          {showLegend && (
            <Legend
              {...LEGEND_LAYOUT[legendPosition]}
              content={renderLegendContent}
            />
          )}

          {keys.map((k, i) => (
            <Bar
              key={k.key}
              dataKey={k.key}
              name={k.label ?? k.key}
              fill={k.color}
              stackId={stackId}
              barSize={barSize}
              radius={barRadius(
                orientation,
                i,
                keys.length,
                stacked,
                rounded ?? true
              )}
              hide={hiddenSeries.has(k.label ?? k.key)}
            />
          ))}

          {showBrush && orientation === "vertical" && (
            <Brush
              dataKey={categoryKey}
              height={30}
              stroke="var(--border)"
              fill="var(--card)"
              travellerWidth={8}
              traveller={(<BrushHandle />) as React.ReactElement<SVGElement>}
              tickFormatter={(v) => (typeof v === "string" ? v : String(v))}
            />
          )}
        </RechartsBarChart>
      </ResponsiveContainer>

      {footer && (
        <div className={chartFooterVariants()} data-slot="bar-chart-footer">
          {footer}
        </div>
      )}
    </div>
  )
}
