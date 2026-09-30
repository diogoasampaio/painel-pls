let measureCanvas: HTMLCanvasElement | null = null

function measureTextWidth(text: string, font: string): number {
  if (typeof document === "undefined") return text.length * 7
  measureCanvas ??= document.createElement("canvas")
  const ctx = measureCanvas.getContext("2d")
  if (!ctx) return text.length * 7
  ctx.font = font
  return ctx.measureText(text).width
}

// Recharts' axis <text> has no explicit font-family, so it renders in
// whatever font the host app applies to <body> (e.g. Inter via
// next/font/google) — not the browser's generic "system-ui" fallback,
// which measures noticeably narrower for some glyphs and under-reserves
// axis width. Reading the live computed font keeps the canvas measurement
// and the actual SVG text in the same typeface.
function bodyFontFamily(): string {
  if (typeof document === "undefined") return "system-ui, sans-serif"
  return getComputedStyle(document.body).fontFamily || "system-ui, sans-serif"
}

export function measureAxisWidth(
  values: number[],
  format: (value: number) => string,
  options?: {
    fontSize?: number
    fontFamily?: string
    padding?: number
    min?: number
  }
): number {
  const fontSize = options?.fontSize ?? 12
  const fontFamily = options?.fontFamily ?? bodyFontFamily()
  const padding = options?.padding ?? 32
  const min = options?.min ?? 40

  const finite = values.filter((v) => Number.isFinite(v))
  if (finite.length === 0) return min

  const font = `${fontSize}px ${fontFamily}`
  const widest = [...new Set(finite)].reduce(
    (max, value) => Math.max(max, measureTextWidth(format(value), font)),
    0
  )
  return Math.max(min, Math.ceil(widest) + padding)
}
