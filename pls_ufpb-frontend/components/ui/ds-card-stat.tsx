import * as React from "react"
import { BarChart2Icon } from "lucide-react"

import { cn } from "@/lib/utils"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useOptionalUILocale } from "@/components/ui/ds-locale-provider"
import { Card, CardAction, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import {
  type FormatPreset,
  type CardStatTrend,
  type CardStatSize,
  applyFormat,
  resolveTrend,
  TREND_ICONS,
  TREND_COLORS,
  cardStatLabelVariants,
  cardStatValueVariants,
  cardStatDescriptionVariants,
  cardStatHeaderIconVariants,
  cardStatTrendIconVariants,
  cardStatContentGapVariants,
} from "@/lib/card-stats-shared"

// ── Component ──

export interface CardStatProps {
  label: string
  value: string | number
  format?: FormatPreset
  decimals?: number
  locale?: string
  currency?: string
  abbreviate?: boolean
  description?: string
  trend?: CardStatTrend | boolean
  icon?: React.ElementType
  size?: CardStatSize
  variant?: "default" | "muted" | "flat"
  valueFormatter?: (value: number | string) => string
  className?: string
  valueClassName?: string
  loading?: boolean
  empty?: boolean
}

const VARIANT_CLASSES = {
  default: "hover:-translate-y-0.5 hover:shadow-lg",
  muted: "bg-muted shadow-none ring-0 hover:bg-accent",
  flat: "bg-background shadow-none ring-0 hover:bg-muted/50",
} as const

export function CardStat({
  label,
  value,
  format,
  decimals,
  locale: localeProp,
  currency,
  abbreviate,
  description,
  trend = false,
  icon: Icon,
  size = "sm",
  variant = "default",
  valueFormatter,
  className,
  valueClassName,
  loading,
  empty,
}: CardStatProps) {
  const locale = useOptionalUILocale(localeProp)
  const variantClass = VARIANT_CLASSES[variant]

  if (loading) {
    return (
      <Card
        size="sm"
        className={cn("transition-all duration-200", variantClass, className)}
        data-slot="card-stat"
      >
        <CardHeader className="flex flex-row items-center justify-between">
          <Skeleton className="h-3 w-24 rounded-md" />
          <Skeleton
            className={cn(cardStatHeaderIconVariants({ size }), "rounded-md")}
          />
        </CardHeader>
        <CardContent
          className={cn("flex flex-col", cardStatContentGapVariants({ size }))}
        >
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-3 w-32 rounded-md" />
        </CardContent>
      </Card>
    )
  }

  if (empty) {
    return (
      <Card
        size="sm"
        className={cn("transition-all duration-200", variantClass, className)}
        data-slot="card-stat"
      >
        <CardHeader className="flex flex-row items-center justify-between">
          <span
            className={cn(
              "truncate text-muted-foreground",
              cardStatLabelVariants({ size })
            )}
          >
            {label}
          </span>
          {Icon && (
            <CardAction className="text-muted-foreground/40">
              <Icon
                className={cardStatHeaderIconVariants({ size })}
                aria-hidden="true"
              />
            </CardAction>
          )}
        </CardHeader>
        <CardContent
          className={cn("flex flex-col", cardStatContentGapVariants({ size }))}
        >
          <p
            className={cn(
              cardStatValueVariants({ size }),
              "text-muted-foreground/25"
            )}
          >
            —
          </p>
          <p
            className={cn(
              "flex items-center gap-1 text-muted-foreground/50",
              cardStatDescriptionVariants({ size })
            )}
          >
            <BarChart2Icon className="size-2.5 shrink-0" aria-hidden />
            {locale
              ? UI_I18N[locale as UILocale].cardStat.nothingToMeasure
              : "Nothing to measure yet"}
          </p>
        </CardContent>
      </Card>
    )
  }

  const displayValue = applyFormat(value, {
    format,
    decimals,
    locale,
    currency,
    abbreviate,
    valueFormatter,
  })

  const trendDir: CardStatTrend | false = resolveTrend(trend)
  const TrendIcon = trendDir ? TREND_ICONS[trendDir] : null

  return (
    <Card
      size="sm"
      className={cn("transition-all duration-200", variantClass, className)}
      data-slot="card-stat"
    >
      <CardHeader className="flex flex-row items-center justify-between">
        <span
          className={cn(
            "truncate text-muted-foreground",
            cardStatLabelVariants({ size })
          )}
        >
          {label}
        </span>
        {Icon && (
          <CardAction className="text-muted-foreground">
            <Icon
              className={cardStatHeaderIconVariants({ size })}
              aria-hidden="true"
            />
          </CardAction>
        )}
      </CardHeader>
      <CardContent
        className={cn("flex flex-col", cardStatContentGapVariants({ size }))}
      >
        <p className={cn(cardStatValueVariants({ size }), valueClassName)}>
          {displayValue}
        </p>
        {description && (
          <p
            className={cn(
              "flex items-center gap-1",
              cardStatDescriptionVariants({ size }),
              trendDir ? TREND_COLORS[trendDir] : "text-muted-foreground"
            )}
          >
            {TrendIcon && (
              <TrendIcon
                className={cn(cardStatTrendIconVariants({ size }))}
                aria-hidden
              />
            )}
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
