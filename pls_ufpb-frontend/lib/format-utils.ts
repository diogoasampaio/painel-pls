import { ABBREV_SCALES } from "@/lib/ui-i18n"

// ── Types ──

export type FormatPreset = "currency" | "percent" | "integer" | "float"

export interface FormatOptions {
  format?: FormatPreset
  decimals?: number
  locale?: string
  currency?: string
  abbreviate?: boolean
  valueFormatter?: (value: number | string) => string
}

// ── Internal helpers ──

function resolveAbbrevLocale(
  locale: string
): "pt-BR" | "en-US" | "es-ES" | "fr-FR" {
  if (locale.startsWith("pt")) return "pt-BR"
  if (locale.startsWith("es")) return "es-ES"
  if (locale.startsWith("fr")) return "fr-FR"
  return "en-US"
}

function abbreviateNum(
  value: number,
  locale: string
): { value: number; suffix: string } {
  const abs = Math.abs(value)
  const scales = ABBREV_SCALES[resolveAbbrevLocale(locale)]
  for (const { threshold, divisor, suffix } of scales) {
    if (abs >= threshold) {
      return { value: value / divisor, suffix }
    }
  }
  return { value, suffix: "" }
}

// ── formatValue ──

export function formatValue(
  value: string | number,
  format?: FormatPreset,
  opts?: {
    decimals?: number
    locale?: string
    currency?: string
    abbreviate?: boolean
  }
): string {
  if (!format || typeof value === "string") return String(value)
  const num = Number(value)
  const locale = opts?.locale ?? "en-US"
  const currency = opts?.currency ?? "USD"
  const abbreviate = opts?.abbreviate ?? false

  let fmtValue = num
  let suffix = ""
  if (abbreviate) {
    const ab = abbreviateNum(num, locale)
    fmtValue = ab.value
    suffix = ab.suffix
  }

  const decimals = opts?.decimals ?? (abbreviate ? 1 : undefined)

  let formatted: string
  switch (format) {
    case "currency":
      formatted = new Intl.NumberFormat(locale, {
        style: "currency",
        currency,
        minimumFractionDigits: decimals ?? 2,
        maximumFractionDigits: decimals ?? 2,
      }).format(fmtValue)
      break
    case "percent":
      // `value` is a ratio (0-1) per the FormatPreset contract — Intl's
      // style: "percent" multiplies by 100 and applies the locale-correct symbol/spacing.
      formatted = new Intl.NumberFormat(locale, {
        style: "percent",
        minimumFractionDigits: decimals ?? 1,
        maximumFractionDigits: decimals ?? 1,
      }).format(fmtValue)
      break
    case "integer":
      formatted = new Intl.NumberFormat(locale, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(fmtValue)
      break
    case "float":
      formatted = new Intl.NumberFormat(locale, {
        minimumFractionDigits: decimals ?? 2,
        maximumFractionDigits: decimals ?? 2,
      }).format(fmtValue)
      break
    default:
      formatted = String(fmtValue)
  }

  return suffix ? formatted + suffix : formatted
}

// ── formatChartValue (chart wrapper) ──

export function formatChartValue(
  value: number,
  opts?: {
    format?: FormatPreset
    decimals?: number
    locale?: string
    currency?: string
    abbreviate?: boolean
    valueFormatter?: (value: number) => string
  }
): string {
  const locale = opts?.locale ?? "en-US"
  if (opts?.valueFormatter) return opts.valueFormatter(value)
  if (!opts?.format) return value.toLocaleString(locale)
  return formatValue(value, opts.format, {
    decimals: opts.decimals,
    locale,
    currency: opts.currency,
    abbreviate: opts.abbreviate,
  })
}

// ── applyFormat (card-stat convenience wrapper) ──

export function applyFormat(
  value: number | string,
  opts: FormatOptions
): string {
  return opts.valueFormatter
    ? opts.valueFormatter(value)
    : formatValue(value, opts.format, {
        decimals: opts.decimals,
        locale: opts.locale,
        currency: opts.currency,
        abbreviate: opts.abbreviate,
      })
}
