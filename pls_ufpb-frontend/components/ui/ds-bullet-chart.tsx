"use client"

import * as React from "react"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useUILocale } from "@/components/ui/ds-locale-provider"
import { formatChartValue, type FormatPreset } from "@/lib/format-utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

// ── Types ──────────────────────────────────────────────────────────────────

export type BulletChartSize = "sm" | "md" | "lg"

export interface BulletChartProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Metric label */
  label: string
  /** The current measured value */
  value: number
  /** The target/goal value — rendered as a vertical tick */
  target?: number
  /**
   * Qualitative range thresholds [poor, ok, good].
   * Rendered as background bands from low to high risk.
   * If omitted, no range bands are shown.
   */
  ranges?: [number, number, number]
  /** Axis maximum — defaults to max(value, target, ranges[-1]) * 1.1 */
  max?: number
  size?: BulletChartSize
  valueFormatter?: (v: number) => string
  format?: FormatPreset
  decimals?: number
  currency?: string
  abbreviate?: boolean
  loading?: boolean
  locale?: UILocale
}

// ── Variants ───────────────────────────────────────────────────────────────

export const bulletChartContainerVariants = cva("w-full", {
  variants: {
    size: {
      sm: "gap-1",
      md: "gap-1.5",
      lg: "gap-2",
    },
  },
  defaultVariants: { size: "md" },
})

export const bulletChartLabelVariants = cva(
  "shrink-0 truncate font-medium text-muted-foreground",
  {
    variants: {
      size: {
        sm: "w-24 text-xs",
        md: "w-28 text-sm",
        lg: "w-32 text-base",
      },
    },
    defaultVariants: { size: "md" },
  }
)

export const bulletChartValueVariants = cva(
  "shrink-0 text-right font-semibold text-foreground tabular-nums",
  {
    variants: {
      size: {
        sm: "w-12 text-xs",
        md: "w-14 text-sm",
        lg: "w-16 text-base",
      },
    },
    defaultVariants: { size: "md" },
  }
)

export const bulletChartTrackVariants = cva(
  "relative flex-1 overflow-hidden rounded-sm bg-muted",
  {
    variants: {
      size: {
        sm: "h-2",
        md: "h-3",
        lg: "h-4",
      },
    },
    defaultVariants: { size: "md" },
  }
)

// ── Skeleton dims ─────────────────────────────────────────────────────────

const skeletonDims: Record<
  BulletChartSize,
  { label: string; value: string; track: string }
> = {
  sm: { label: "h-3 w-20", value: "h-3 w-10", track: "h-2" },
  md: { label: "h-4 w-24", value: "h-4 w-12", track: "h-3" },
  lg: { label: "h-5 w-28", value: "h-5 w-14", track: "h-4" },
}

// ── Risk range colors (4 bands from worst to best) ────────────────────────

const RANGE_COLORS = [
  "bg-risk-1", // lowest threshold → worst performance
  "bg-risk-2",
  "bg-risk-3",
  "bg-risk-4", // upper area → best performance
]

// ── BulletChart ────────────────────────────────────────────────────────────

export function BulletChart({
  label,
  value,
  target,
  ranges,
  max: maxProp,
  size = "md",
  valueFormatter,
  format,
  decimals = 0,
  currency = "USD",
  abbreviate = false,
  loading = false,
  locale: localeProp,
  className,
  ...props
}: BulletChartProps) {
  const locale = useUILocale(localeProp)
  const formatValue = React.useCallback(
    (v: number) => {
      if (valueFormatter) return valueFormatter(v)
      return formatChartValue(v, {
        format,
        decimals,
        locale,
        currency,
        abbreviate,
      })
    },
    [valueFormatter, format, decimals, locale, currency, abbreviate]
  )

  // ── Loading ─────────────────────────────────────────────────────────────

  if (loading) {
    const d = skeletonDims[size]
    return (
      <div
        className={cn("flex items-center gap-2", className)}
        aria-hidden="true"
        {...props}
      >
        <Skeleton className={d.label} />
        <Skeleton className={cn("flex-1 rounded-sm", d.track)} />
        <Skeleton className={d.value} />
      </div>
    )
  }

  // ── Compute ──────────────────────────────────────────────────────────────

  const maxCandidate = Math.max(
    value,
    target ?? 0,
    ranges ? (ranges[2] ?? 0) : 0
  )
  const axisMax = (maxProp ?? maxCandidate * 1.15) || 1
  const valuePct = Math.min(100, (value / axisMax) * 100)
  const targetPct =
    target !== undefined ? Math.min(100, (target / axisMax) * 100) : null

  // ── Range bands ──────────────────────────────────────────────────────────

  const rangeBands = ranges
    ? [
        { from: 0, to: ranges[0]!, colorClass: RANGE_COLORS[0]! },
        { from: ranges[0]!, to: ranges[1]!, colorClass: RANGE_COLORS[1]! },
        { from: ranges[1]!, to: ranges[2]!, colorClass: RANGE_COLORS[2]! },
        { from: ranges[2]!, to: axisMax, colorClass: RANGE_COLORS[3]! },
      ]
    : []

  const targetLabel =
    target !== undefined
      ? `${label}: ${formatValue(value)} / Target: ${formatValue(target)}`
      : `${label}: ${formatValue(value)}`

  return (
    <TooltipProvider delayDuration={100}>
      <div
        className={cn(
          "flex items-center gap-2",
          bulletChartContainerVariants({ size }),
          className
        )}
        role="meter"
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={Math.round(axisMax)}
        aria-label={targetLabel}
        {...props}
      >
        {/* Label */}
        <span className={bulletChartLabelVariants({ size })}>{label}</span>

        {/* Track */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn(bulletChartTrackVariants({ size }))}>
              {/* Range bands */}
              {rangeBands.map((band, i) => {
                const leftPct = (band.from / axisMax) * 100
                const widthPct = ((band.to - band.from) / axisMax) * 100
                return (
                  <div
                    key={i}
                    className={cn(
                      "absolute inset-y-0",
                      band.colorClass,
                      "opacity-40"
                    )}
                    style={{
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                    }}
                  />
                )
              })}

              {/* Value bar */}
              <div
                className="absolute inset-y-0 left-0 rounded-sm bg-primary transition-all duration-500"
                style={{ width: `${valuePct}%` }}
              />

              {/* Target marker */}
              {targetPct !== null && (
                <div
                  className="absolute -inset-y-0.5 w-0.5 rounded-full bg-foreground"
                  style={{ left: `${targetPct}%` }}
                  aria-hidden="true"
                />
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="flex flex-col gap-0.5 text-xs">
              <span className="font-medium">{label}</span>
              <span>
                {UI_I18N[locale].riskLevelBar?.value ?? "Value"}:{" "}
                <span className="font-semibold tabular-nums">
                  {formatValue(value)}
                </span>
              </span>
              {target !== undefined && (
                <span>
                  Target:{" "}
                  <span className="font-semibold tabular-nums">
                    {formatValue(target)}
                  </span>
                </span>
              )}
            </div>
          </TooltipContent>
        </Tooltip>

        {/* Value */}
        <span className={bulletChartValueVariants({ size })}>
          {formatValue(value)}
        </span>
      </div>
    </TooltipProvider>
  )
}

// ── BulletChartGroup ───────────────────────────────────────────────────────

export interface BulletChartGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  items: BulletChartProps[]
  size?: BulletChartSize
  loading?: boolean
}

export function BulletChartGroup({
  items,
  size = "md",
  loading = false,
  className,
  ...props
}: BulletChartGroupProps) {
  return (
    <div className={cn("flex flex-col gap-3", className)} {...props}>
      {items.map((item, i) => (
        <BulletChart key={i} {...item} size={size} loading={loading} />
      ))}
    </div>
  )
}
