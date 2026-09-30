"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes } from "react"
import { cn } from "@/lib/utils"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useUILocale } from "@/components/ui/ds-locale-provider"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

// ── Types ──────────────────────────────────────────────────────────────────

export type PillGroupIntent = "default" | "success" | "warning" | "destructive"
export type PillGroupSize = "sm" | "md" | "lg"

export interface PillGroupItem {
  value: string
  label: string
  /** Numeric count shown as a dimmed suffix next to the label. */
  count?: number
  /** Lucide icon component rendered before the label. */
  icon?: React.ElementType
  /** Disables this individual item without affecting the rest. */
  disabled?: boolean
  /** Active-state color. Defaults to "default" (inverted bg-foreground). */
  intent?: PillGroupIntent
}

export interface PillGroupProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "onChange" | "defaultValue"
> {
  items: PillGroupItem[]
  /**
   * Controlled selected value(s).
   * Pass a `string` for single-select or `string[]` for multi-select.
   * Pass `null` to represent "nothing selected".
   */
  value?: string | string[] | null
  /** Initial selected value(s) for uncontrolled usage. */
  defaultValue?: string | string[] | null
  /** Allow selecting multiple items simultaneously. */
  multiple?: boolean
  onChange?: (value: string | string[] | null) => void
  size?: PillGroupSize
  /**
   * Show counts next to item labels.
   * Auto-enabled when at least one item has a `count` field.
   */
  showCount?: boolean
  loading?: boolean
  disabled?: boolean
  locale?: UILocale
  /** Accessible label for the filter group. Falls back to i18n string. */
  label?: string
  /** Number of skeleton pills shown while loading. Defaults to items.length or 3. */
  skeletonCount?: number
}

export type PillGroupItemVariants = VariantProps<typeof pillGroupItemVariants>

// ── Variants ───────────────────────────────────────────────────────────────

export const pillGroupItemVariants = cva(
  [
    "relative inline-flex shrink-0 items-center gap-1 rounded-full font-medium select-none",
    // Override Button's unconditional transition-colors with a motion-safe version
    "motion-safe:transition-colors motion-safe:duration-150 motion-reduce:transition-none",
    "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:outline-none",
    "disabled:pointer-events-none disabled:opacity-40",
    // Icon sizing — overrides Button's [&_svg]:size-4 per size slot
    "[&_svg]:shrink-0",
  ],
  {
    variants: {
      size: {
        sm: "h-8 min-h-[44px] px-2.5 text-xs [&_svg]:size-3",
        md: "h-8 min-h-[44px] px-3 text-sm [&_svg]:size-3.5",
        lg: "h-9 min-h-[44px] px-4 text-base [&_svg]:size-4",
      },
      active: {
        true: "",
        false: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
      },
      intent: {
        default: "",
        success: "",
        warning: "",
        destructive: "",
      },
    },
    compoundVariants: [
      {
        active: true,
        intent: "default",
        className:
          "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
      },
      {
        active: true,
        intent: "success",
        className:
          "bg-success text-success-foreground shadow-xs hover:bg-success/90",
      },
      {
        active: true,
        intent: "warning",
        className:
          "bg-warning text-warning-foreground shadow-xs hover:bg-warning/90",
      },
      {
        active: true,
        intent: "destructive",
        className:
          "text-destructive-foreground bg-destructive shadow-xs hover:bg-destructive/90",
      },
    ],
    defaultVariants: {
      size: "md",
      active: false,
      intent: "default",
    },
  }
)

export const pillGroupCountVariants = cva("font-normal tabular-nums", {
  variants: {
    active: {
      true: "opacity-60",
      false: "text-muted-foreground",
    },
  },
  defaultVariants: { active: false },
})

// ── Helpers ────────────────────────────────────────────────────────────────

function useScrollFade(ref: React.RefObject<HTMLDivElement | null>) {
  const [canScrollLeft, setCanScrollLeft] = React.useState(false)
  const [canScrollRight, setCanScrollRight] = React.useState(false)

  const check = React.useCallback(() => {
    const el = ref.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 2)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2)
  }, [ref])

  React.useEffect(() => {
    const el = ref.current
    if (!el) return
    check()
    el.addEventListener("scroll", check, { passive: true })
    const ro = new ResizeObserver(check)
    ro.observe(el)
    return () => {
      el.removeEventListener("scroll", check)
      ro.disconnect()
    }
  }, [check, ref])

  return { canScrollLeft, canScrollRight }
}

function itemIsActive(
  value: string,
  selection: string | string[] | null | undefined,
  multiple: boolean
): boolean {
  if (selection == null) return false
  return multiple
    ? Array.isArray(selection) && selection.includes(value)
    : selection === value
}

function nextSelection(
  value: string,
  selection: string | string[] | null | undefined,
  multiple: boolean
): string | string[] | null {
  if (multiple) {
    const cur = Array.isArray(selection) ? selection : []
    return cur.includes(value)
      ? cur.filter((v) => v !== value)
      : [...cur, value]
  }
  return selection === value ? null : value
}

// ── Component ──────────────────────────────────────────────────────────────

export const PillGroup = React.forwardRef<HTMLDivElement, PillGroupProps>(
  (
    {
      items,
      value: controlledValue,
      defaultValue = null,
      multiple = false,
      onChange,
      size = "md",
      showCount,
      loading = false,
      disabled = false,
      locale: localeProp,
      label,
      skeletonCount,
      className,
      ...props
    },
    ref
  ) => {
    const locale = useUILocale(localeProp)
    const t = UI_I18N[locale].pillGroup
    const scrollRef = React.useRef<HTMLDivElement>(null)
    const { canScrollLeft, canScrollRight } = useScrollFade(scrollRef)

    const isControlled = controlledValue !== undefined
    const [internalValue, setInternalValue] = React.useState<
      string | string[] | null
    >(defaultValue ?? null)

    const selection = isControlled ? controlledValue : internalValue

    const handleSelect = React.useCallback(
      (itemValue: string, itemDisabled?: boolean) => {
        if (disabled || itemDisabled) return
        const next = nextSelection(itemValue, selection, multiple)
        if (!isControlled) setInternalValue(next)
        onChange?.(next)
      },
      [selection, multiple, disabled, isControlled, onChange]
    )

    const hasAnyCount = items.some((it) => it.count !== undefined)
    const shouldShowCount = showCount ?? hasAnyCount

    const trackPadding = size === "sm" ? "p-0.5" : "p-1"
    const pillHeight =
      size === "sm"
        ? "h-8 min-h-[44px]"
        : size === "lg"
          ? "h-9 min-h-[44px]"
          : "h-8 min-h-[44px]"
    const skeletonWidths = ["w-12", "w-24", "w-20", "w-16", "w-28", "w-14"]

    if (loading) {
      const n = skeletonCount ?? (items.length > 0 ? items.length : 3)
      return (
        <div
          ref={ref}
          data-slot="pill-group"
          className={cn(
            "inline-flex items-center gap-0.5 rounded-full border bg-muted/30",
            trackPadding,
            className
          )}
          {...props}
        >
          {Array.from({ length: n }).map((_, i) => (
            <Skeleton
              key={i}
              className={cn(
                "rounded-full",
                pillHeight,
                skeletonWidths[i % skeletonWidths.length]
              )}
            />
          ))}
        </div>
      )
    }

    return (
      <div
        ref={ref}
        data-slot="pill-group"
        className={cn(
          "relative inline-flex max-w-full overflow-hidden rounded-full border bg-muted/30",
          trackPadding,
          disabled && "pointer-events-none opacity-50",
          className
        )}
        {...props}
      >
        {/* Left scroll-fade — appears when items overflow left */}
        {canScrollLeft && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-linear-to-r from-background/80 to-transparent"
          />
        )}

        {/* Scrollable track — hides native scrollbar cross-browser */}
        <div
          ref={scrollRef}
          className="scrollbar-none overflow-x-auto [&::-webkit-scrollbar]:hidden"
        >
          <div
            role={multiple ? "group" : "radiogroup"}
            aria-label={label ?? t.filterLabel}
            aria-disabled={disabled || undefined}
            className="flex items-center gap-0.5"
          >
            {items.map((item) => {
              const active = itemIsActive(item.value, selection, multiple)
              const Icon = item.icon
              const intent = item.intent ?? "default"

              return (
                <Button
                  key={item.value}
                  variant="ghost"
                  role={multiple ? "checkbox" : "radio"}
                  aria-checked={active}
                  disabled={disabled || item.disabled}
                  onClick={() => handleSelect(item.value, item.disabled)}
                  className={cn(
                    pillGroupItemVariants({ size, active, intent })
                  )}
                  data-slot="pill-group-item"
                  data-active={active || undefined}
                  data-value={item.value}
                >
                  {Icon && <Icon aria-hidden="true" />}
                  <span className="truncate">{item.label}</span>
                  {shouldShowCount && item.count !== undefined && (
                    <span
                      className={cn(pillGroupCountVariants({ active }))}
                      aria-hidden="true"
                    >
                      {item.count.toLocaleString(locale)}
                    </span>
                  )}
                </Button>
              )
            })}
          </div>
        </div>

        {/* Right scroll-fade — appears when items overflow right */}
        {canScrollRight && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-linear-to-l from-background/80 to-transparent"
          />
        )}
      </div>
    )
  }
)

PillGroup.displayName = "PillGroup"
