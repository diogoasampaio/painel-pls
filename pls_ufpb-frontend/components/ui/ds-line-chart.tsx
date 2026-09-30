"use client"

import * as React from "react"
import {
  Area,
  AreaChart as RechartsAreaChart,
  Brush,
  CartesianGrid,
  Legend,
  ReferenceLine as RechartsReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cva } from "class-variance-authority"
import { TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useUILocale } from "@/components/ui/ds-locale-provider"
import { formatChartValue, type FormatPreset } from "@/lib/format-utils"
import { measureAxisWidth } from "@/lib/chart-axis-width"

// ── Types ──────────────────────────────────────────────────────────────────

/** "line" = plain strokes; "area" = gradient fill; "area-stacked" = stacked gradient areas */
export type LineChartVariant = "line" | "area" | "area-stacked"
export type LegendPosition = "top" | "bottom" | "left" | "right"

/** When data-point dots are rendered */
export type LineDotVisibility = "none" | "hover" | "always"

/** Line interpolation style */
export type LineCurve = "linear" | "smooth" | "step"

export interface LineChartKey {
  key: string
  label?: string
  /** Defaults to the next --chart-N token */
  color?: string
  /** Render as a dashed stroke — useful for projected or estimated series */
  dashed?: boolean
}

export interface LineChartReferenceLine {
  value: number
  label?: string
  color?: string
  /** @default true */
  dashed?: boolean
}

export interface LineChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: Record<string, string | number>[]
  /** Keys to plot — accepts plain strings or { key, label, color, dashed } objects */
  dataKeys: LineChartKey[] | string[]
  /** Object key mapped to the category (X) axis */
  categoryKey: string
  title?: string
  subtitle?: string
  footer?: React.ReactNode
  variant?: LineChartVariant
  curve?: LineCurve
  /** When to show data-point dots */
  dots?: LineDotVisibility
  height?: number
  showGrid?: boolean
  showLegend?: boolean
  /** @default "bottom" */
  legendPosition?: LegendPosition
  showTooltip?: boolean
  /** Bridge over null / undefined values instead of breaking the line */
  connectNulls?: boolean
  /** Horizontal threshold lines — targets, SLA limits, averages, etc. */
  referenceLines?: LineChartReferenceLine[]
  /** Format value-axis tick labels and tooltip values */
  valueFormatter?: (value: number) => string
  /**
   * Show a range brush below the chart to scroll and zoom the category axis.
   * The brush occupies ~30 px of the chart height, so increase `height`
   * accordingly when enabling.
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

const CURVE_TYPE = {
  linear: "linear",
  smooth: "monotone",
  step: "step",
} as const

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

const SKELETON_YAXIS_WIDTHS = [28, 20, 24, 18]
const SKELETON_XAXIS_WIDTHS = [28, 36, 24, 32, 28, 20, 34, 26]
const SKELETON_LINE_DOTS = [
  [0, 65],
  [13, 40],
  [26, 52],
  [39, 20],
  [52, 35],
  [65, 10],
  [78, 28],
  [91, 15],
]

interface LineChartSkeletonProps {
  height?: number
  hasTitle?: boolean
  hasSubtitle?: boolean
  hasFooter?: boolean
  className?: string
}

function LineChartSkeleton({
  height = 280,
  hasTitle = false,
  hasSubtitle = false,
  hasFooter = false,
  className,
}: LineChartSkeletonProps) {
  const polylinePoints = SKELETON_LINE_DOTS.map(([x, y]) => `${x},${y}`).join(
    " "
  )
  const areaPath = `M 0,65 L 13,40 L 26,52 L 39,20 L 52,35 L 65,10 L 78,28 L 91,15 L 91,100 L 0,100 Z`

  return (
    <div
      className={cn("flex w-full flex-col", className)}
      data-slot="line-chart-skeleton"
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

      <div className="relative overflow-hidden" style={{ height }}>
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

        {/* Chart area with SVG line */}
        <div className="absolute top-2 right-1 bottom-8 left-11">
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            className="h-full w-full"
          >
            {/* Horizontal grid lines */}
            {[25, 50, 75].map((y, i) => (
              <line
                key={y}
                x1="0"
                y1={y}
                x2="100"
                y2={y}
                stroke="var(--muted)"
                strokeWidth="0.8"
                style={{ animationDelay: `${0.6 + i * 0.15}s` }}
              />
            ))}
            {/* Area fill */}
            <path d={areaPath} fill="var(--muted)" fillOpacity={0.15} />
            {/* Line */}
            <polyline
              points={polylinePoints}
              fill="none"
              stroke="var(--muted)"
              strokeWidth="2"
              className="motion-safe:animate-pulse"
            />
            {/* Dots */}
            {SKELETON_LINE_DOTS.map(([x, y], i) => (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="2.5"
                fill="var(--muted)"
                className="motion-safe:animate-pulse"
                style={{ animationDelay: `${i * 0.09}s` }}
              />
            ))}
          </svg>
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
  stroke: string
  color: string
  strokeDasharray?: string
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
    <div className="min-w-36 rounded-lg border border-border bg-card px-3 py-2 shadow-md">
      <p className="mb-1.5 text-xs font-semibold text-foreground">{label}</p>
      <div className="flex flex-col gap-1">
        {payload.map((entry) => {
          const color = entry.stroke ?? entry.color
          const isDashed = !!entry.strokeDasharray
          return (
            <div key={entry.name} className="flex items-center gap-2">
              {/* Line swatch — solid or dashed to mirror the series style */}
              <svg width="16" height="8" className="shrink-0">
                <line
                  x1="0"
                  y1="4"
                  x2="16"
                  y2="4"
                  stroke={color}
                  strokeWidth="2"
                  strokeDasharray={isDashed ? "4 2" : undefined}
                  strokeLinecap="round"
                />
              </svg>
              <span className="text-xs text-muted-foreground">
                {entry.name}
              </span>
              <span className="ml-auto pl-4 text-xs font-semibold text-foreground tabular-nums">
                {fmt(entry.value)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Custom Legend ──────────────────────────────────────────────────────────

interface LegendPayloadEntry {
  value: string
  color: string
  payload?: { strokeDasharray?: string }
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
          : "flex-wrap items-center justify-center gap-x-5 pt-3"
      )}
    >
      {payload.map((entry, i) => {
        const isDashed = !!entry.payload?.strokeDasharray
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
            <svg width="16" height="8" className="shrink-0">
              <line
                x1="0"
                y1="4"
                x2="16"
                y2="4"
                stroke={entry.color}
                strokeWidth="2"
                strokeDasharray={isDashed ? "4 2" : undefined}
                strokeLinecap="round"
              />
            </svg>
            <span className="text-xs text-muted-foreground">{entry.value}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Reference Line Label ───────────────────────────────────────────────────

function ReferenceLineLabel({
  viewBox,
  label,
  color,
}: {
  viewBox?: { x?: number; width?: number; y?: number }
  label: string
  color: string
}) {
  const x = (viewBox?.x ?? 0) + (viewBox?.width ?? 0)
  const y = viewBox?.y ?? 0
  const padding = 6
  const estimatedWidth = label.length * 6 + padding * 2

  return (
    <g>
      <rect
        x={x - estimatedWidth - 4}
        y={y - 10}
        width={estimatedWidth}
        height={16}
        rx={4}
        fill={color}
        fillOpacity={0.12}
      />
      <text
        x={x - estimatedWidth / 2 - 4}
        y={y + 3}
        textAnchor="middle"
        fontSize={10}
        fontWeight={600}
        fill={color}
      >
        {label}
      </text>
    </g>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

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

function normalizeKeys(
  raw: LineChartKey[] | string[]
): Required<LineChartKey>[] {
  return raw.map((k, i) => {
    const color = CHART_COLORS[i % CHART_COLORS.length]
    if (typeof k === "string") return { key: k, label: k, color, dashed: false }
    return { label: k.key, dashed: false, ...k, color: k.color ?? color }
  })
}

// ── LineChart ──────────────────────────────────────────────────────────────

export function LineChart({
  data,
  dataKeys,
  categoryKey,
  title,
  subtitle,
  footer,
  variant = "line",
  curve = "smooth",
  dots = "hover",
  height = 280,
  showGrid = true,
  showLegend = false,
  legendPosition = "bottom",
  showTooltip = true,
  connectNulls = false,
  referenceLines,
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
}: LineChartProps) {
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

  // useId produces strings like ":r0:" — strip non-alphanumeric for safe SVG IDs
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, "")
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
      <LineChartSkeleton
        height={height}
        hasTitle={!!title}
        hasSubtitle={!!subtitle}
        hasFooter={!!footer}
        className={className}
      />
    )
  }

  if (data.length === 0) {
    return (
      <div
        className={cn(chartWrapperVariants(), className)}
        data-slot="line-chart"
        {...props}
      >
        {(title || subtitle) && (
          <div className={chartHeaderVariants()} data-slot="line-chart-header">
            {title && <p className={chartTitleVariants()}>{title}</p>}
            {subtitle && <p className={chartSubtitleVariants()}>{subtitle}</p>}
          </div>
        )}
        <div
          className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border text-muted-foreground"
          data-slot="line-chart-empty"
          style={{ height }}
        >
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <TrendingUp className="size-5" />
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
          <div className={chartFooterVariants()} data-slot="line-chart-footer">
            {footer}
          </div>
        )}
      </div>
    )
  }

  const keys = normalizeKeys(dataKeys)
  const isArea = variant !== "line"
  const curveType = CURVE_TYPE[curve]
  const axisStyle = { fontSize: "12px", fill: "var(--muted-foreground)" }

  const axisLabelStyle = {
    fontSize: "11px",
    fill: "var(--muted-foreground)",
  }

  // Expand chart margins when axis labels are present to avoid clipping
  const marginBottom = xAxisLabel ? 28 : 4
  const marginLeft = yAxisLabel ? 8 : 4
  // Sized from the actual formatted tick values (not a fixed guess) so
  // abbreviated currency ("R$ 800,0 mi") never wraps or clips — see
  // lib/chart-axis-width.ts.
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
      data-slot="line-chart"
      {...props}
    >
      {(title || subtitle) && (
        <div className={chartHeaderVariants()} data-slot="line-chart-header">
          {title && <p className={chartTitleVariants()}>{title}</p>}
          {subtitle && <p className={chartSubtitleVariants()}>{subtitle}</p>}
        </div>
      )}

      <ResponsiveContainer
        width="100%"
        height={height}
        data-slot="line-chart-chart"
      >
        <RechartsAreaChart
          data={data}
          margin={{ top: 12, right: 4, bottom: marginBottom, left: marginLeft }}
        >
          {/* Gradient fills — only injected when variant is area or area-stacked */}
          {isArea && (
            <defs>
              {keys.map((k) => (
                <linearGradient
                  key={k.key}
                  id={`${uid}-${k.key}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={k.color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={k.color} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
          )}

          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              vertical={false}
            />
          )}

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

          {showTooltip && (
            <Tooltip
              content={<ChartTooltip fmt={fmt} />}
              cursor={{
                stroke: "var(--border)",
                strokeWidth: 1,
                strokeDasharray: "4 3",
              }}
            />
          )}

          {showLegend && (
            <Legend
              {...LEGEND_LAYOUT[legendPosition]}
              content={renderLegendContent}
            />
          )}

          {referenceLines?.map((ref, i) => (
            <RechartsReferenceLine
              key={i}
              y={ref.value}
              stroke={ref.color ?? "var(--muted-foreground)"}
              strokeDasharray={ref.dashed !== false ? "4 3" : undefined}
              strokeWidth={1.5}
              label={
                ref.label
                  ? (labelProps: {
                      viewBox?: { x?: number; width?: number; y?: number }
                    }) => (
                      <ReferenceLineLabel
                        key={`ref-label-${i}`}
                        viewBox={labelProps.viewBox}
                        label={ref.label!}
                        color={ref.color ?? "var(--muted-foreground)"}
                      />
                    )
                  : undefined
              }
            />
          ))}

          {keys.map((k) => (
            <Area
              key={k.key}
              type={curveType}
              dataKey={k.key}
              name={k.label}
              stroke={k.color}
              strokeWidth={2}
              strokeDasharray={k.dashed ? "6 3" : undefined}
              fill={isArea ? `url(#${uid}-${k.key})` : "none"}
              stackId={variant === "area-stacked" ? "stack" : undefined}
              connectNulls={connectNulls}
              hide={hiddenSeries.has(k.label)}
              dot={
                dots === "always"
                  ? {
                      r: 3,
                      fill: k.color,
                      stroke: "var(--card)",
                      strokeWidth: 2,
                    }
                  : false
              }
              activeDot={
                dots === "none"
                  ? false
                  : {
                      r: 4,
                      fill: k.color,
                      stroke: "var(--card)",
                      strokeWidth: 2,
                    }
              }
            />
          ))}

          {showBrush && (
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
        </RechartsAreaChart>
      </ResponsiveContainer>

      {footer && (
        <div className={chartFooterVariants()} data-slot="line-chart-footer">
          {footer}
        </div>
      )}
    </div>
  )
}
