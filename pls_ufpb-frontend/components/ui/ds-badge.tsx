"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge as BadgeRoot } from "@/components/ui/badge"
import { UI_I18N, type UILocale } from "@/lib/ui-i18n"
import { useUILocale } from "@/components/ui/ds-locale-provider"
import { Skeleton } from "@/components/ui/skeleton"

// ── Types ──

export interface BadgeProps
  extends
    Omit<React.ComponentProps<"span">, "size" | "color">,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
  removable?: boolean
  icon?: React.ReactNode
  maxCount?: number
  onRemove?: () => void
  count?: number
  loading?: boolean
  locale?: UILocale
  /**
   * Override background via CSS token `--badge-background`.
   * Accepts any CSS color value or `var(--my-token)`.
   * @example background="var(--color-success)"
   */
  background?: string
  /**
   * Override text color via CSS token `--badge-color`.
   * Accepts any CSS color value or `var(--my-token)`.
   */
  color?: string
  /**
   * Override border color via CSS token `--badge-border-color`.
   * Accepts any CSS color value or `var(--my-token)`.
   */
  borderColor?: string
}

// ── Variants ──

export const badgeVariants = cva("flex-nowrap whitespace-nowrap", {
  variants: {
    variant: {
      default: "",
      secondary: "",
      destructive: "",
      outline: "",
      success: "bg-success text-success-foreground [a]:hover:bg-success/80",
      warning: "bg-warning text-warning-foreground [a]:hover:bg-warning/80",
    },
    size: {
      sm: "h-4 px-1.5 text-xs [&>svg]:size-2.5",
      md: "h-5 px-2 text-xs font-medium [&>svg]:size-3",
      lg: "h-6 px-2.5 text-sm font-medium [&>svg]:size-3.5",
    },
  },
  defaultVariants: { variant: "default", size: "md" },
})

export const badgeDotVariants = cva("rounded-full", {
  variants: {
    variant: {
      default: "bg-current",
      secondary: "bg-current",
      destructive: "bg-current",
      outline: "bg-current",
      success: "bg-current",
      warning: "bg-current",
    },
    size: {
      sm: "size-1.5",
      md: "size-2",
      lg: "size-2.5",
    },
  },
  defaultVariants: { variant: "default", size: "md" },
})

// ── Component ──

function Badge({
  variant = "default",
  size = "md",
  dot = false,
  removable = false,
  icon,
  maxCount,
  count,
  onRemove,
  loading = false,
  locale: localeProp,
  className,
  children,
  style,
  background,
  color,
  borderColor,
  ...props
}: BadgeProps) {
  const locale = useUILocale(localeProp)
  const i18n = UI_I18N[locale]

  if (loading) {
    const skeletonSizes = { sm: "h-4 w-14", md: "h-5 w-16", lg: "h-6 w-20" }
    return (
      <Skeleton className={cn("rounded-3xl", skeletonSizes[size ?? "md"])} />
    )
  }

  const showCount = maxCount !== undefined && count !== undefined

  const tokenStyle = {
    ...(background !== undefined && {
      "--badge-background": background,
    }),
    ...(color !== undefined && { "--badge-color": color }),
    ...(borderColor !== undefined && {
      "--badge-border-color": borderColor,
    }),
    ...style,
  } as React.CSSProperties

  return (
    <BadgeRoot
      data-slot="ds-badge"
      style={tokenStyle}
      variant={variant as React.ComponentProps<typeof BadgeRoot>["variant"]}
      className={cn(
        badgeVariants({ variant, size }),
        background && "bg-(--badge-background)",
        color && "text-(--badge-color)",
        borderColor && "border border-(--badge-border-color)",
        className
      )}
      {...props}
    >
      {dot && (
        <span
          data-slot="ds-badge-dot"
          className={badgeDotVariants({ variant, size })}
          aria-hidden="true"
        />
      )}
      {icon && (
        <span
          data-slot="ds-badge-icon"
          aria-hidden="true"
          className={cn(
            "inline-flex shrink-0 items-center justify-center",
            size === "sm"
              ? "[&>svg]:size-2.5"
              : size === "lg"
                ? "[&>svg]:size-3.5"
                : "[&>svg]:size-3"
          )}
        >
          {icon}
        </span>
      )}
      <span data-slot="ds-badge-text" className="truncate">
        {showCount ? (count > 999 ? "99+" : count) : children}
      </span>
      {removable && (
        <button
          type="button"
          data-slot="ds-badge-remove"
          aria-label={i18n.badge.remove}
          onClick={(e) => {
            e.stopPropagation()
            onRemove?.()
          }}
          className="-m-1 ml-0.5 inline-flex size-5 items-center justify-center rounded-full p-1 transition-colors hover:bg-accent"
        >
          <XIcon
            className={cn(
              size === "sm" ? "size-2.5" : size === "lg" ? "size-3.5" : "size-3"
            )}
          />
        </button>
      )}
    </BadgeRoot>
  )
}

export { Badge }
