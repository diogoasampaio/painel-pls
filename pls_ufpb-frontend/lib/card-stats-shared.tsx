import * as React from "react"
import { cva } from "class-variance-authority"
import { TrendingUpIcon, TrendingDownIcon, MinusIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

// Re-export shared formatting utilities from lib
export type { FormatPreset, FormatOptions } from "@/lib/format-utils"
export { formatValue, formatChartValue, applyFormat } from "@/lib/format-utils"

export type CardStatTrend = "up" | "down" | "neutral"
export type CardStatSize = "sm" | "md" | "lg"

// ── CVA variants ───────────────────────────────────────────────────────────────

export const cardStatLabelVariants = cva("", {
  variants: {
    size: {
      sm: "text-xs font-medium",
      md: "text-sm font-medium",
      lg: "text-base font-medium",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatValueVariants = cva("", {
  variants: {
    size: {
      sm: "text-xl font-semibold tracking-tight tabular-nums",
      md: "text-2xl font-semibold tracking-tight tabular-nums",
      lg: "text-3xl font-semibold tracking-tight tabular-nums",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatDescriptionVariants = cva("", {
  variants: {
    size: {
      sm: "text-xs",
      md: "text-sm",
      lg: "text-base",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatHeaderIconVariants = cva("", {
  variants: {
    size: {
      sm: "size-3.5",
      md: "size-4",
      lg: "size-5",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatTrendIconVariants = cva("shrink-0", {
  variants: {
    size: {
      sm: "size-2.5",
      md: "size-3",
      lg: "size-3.5",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatContentGapVariants = cva("", {
  variants: {
    size: {
      sm: "gap-2",
      md: "gap-3",
      lg: "gap-4",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatBadgePaddingVariants = cva("", {
  variants: {
    size: {
      sm: "px-1.5 py-0.5",
      md: "px-2 py-0.5",
      lg: "px-2.5 py-1",
    },
  },
  defaultVariants: { size: "sm" },
})

export const cardStatBadgeTextVariants = cva("", {
  variants: {
    size: {
      sm: "text-xs font-semibold",
      md: "text-sm font-semibold",
      lg: "text-base font-semibold",
    },
  },
  defaultVariants: { size: "sm" },
})

export const TREND_ICONS: Record<CardStatTrend, React.ElementType> = {
  up: TrendingUpIcon,
  down: TrendingDownIcon,
  neutral: MinusIcon,
}

export const TREND_COLORS: Record<CardStatTrend, string> = {
  up: "text-success",
  down: "text-destructive",
  neutral: "text-muted-foreground",
}

export function resolveTrend(
  trend: CardStatTrend | boolean | undefined
): CardStatTrend | false {
  if (trend === true) return "up"
  if (!trend) return false
  return trend
}

// ── TrendBadge ────────────────────────────────────────────────────────────────

export function TrendBadge({
  trend,
  value,
  size = "sm",
}: {
  trend: CardStatTrend
  value: string
  size?: CardStatSize
}) {
  const Icon = TREND_ICONS[trend]
  return (
    <Badge
      className={cn(
        cardStatBadgePaddingVariants({ size }),
        cardStatBadgeTextVariants({ size }),
        trend === "up" && "bg-success/10 text-success",
        trend === "down" && "bg-destructive/10 text-destructive",
        trend === "neutral" && "bg-muted text-muted-foreground"
      )}
      data-slot="trend-badge"
    >
      <Icon aria-hidden />
      {value}
    </Badge>
  )
}

// ── CardStatEmptySlot ─────────────────────────────────────────────────────────

const emptySlotBoxVariants: Record<string, string> = {
  sm: "size-7 rounded-xl",
  md: "size-9 rounded-2xl",
  lg: "size-11 rounded-3xl",
}

const emptySlotIconVariants: Record<string, string> = {
  sm: "size-3",
  md: "size-4",
  lg: "size-5",
}

export function CardStatEmptySlot({
  icon: Icon,
  message,
  sub,
  inverted = false,
  size = "sm",
}: {
  icon: React.ElementType
  message: string
  sub?: string
  inverted?: boolean
  size?: CardStatSize
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-2 py-5 text-center"
      data-slot="card-stat-empty-slot"
    >
      <div
        className={cn(
          "flex items-center justify-center rounded-2xl",
          emptySlotBoxVariants[size],
          inverted ? "bg-white/15" : "bg-muted/60"
        )}
      >
        <Icon
          className={cn(
            emptySlotIconVariants[size],
            inverted ? "text-white/50" : "text-muted-foreground/50"
          )}
          aria-hidden
        />
      </div>
      <p
        className={cn(
          "text-xs font-medium",
          inverted ? "text-white/80" : "text-muted-foreground"
        )}
      >
        {message}
      </p>
      {sub && (
        <p
          className={cn(
            "text-xs leading-tight",
            inverted ? "text-white/60" : "text-muted-foreground"
          )}
        >
          {sub}
        </p>
      )}
    </div>
  )
}
