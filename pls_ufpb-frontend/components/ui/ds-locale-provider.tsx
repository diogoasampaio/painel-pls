"use client"

import * as React from "react"

import type { UILocale } from "@/lib/ui-i18n"

// ── Types ──

export interface UILocaleProviderProps {
  /** Locale herdado por todos os componentes `ds-*` da subárvore. */
  locale: UILocale
  children: React.ReactNode
}

// ── Constants ──

/** Locale usado quando não há provider nem prop `locale`. */
export const DEFAULT_UI_LOCALE: UILocale = "en-US"

const UILocaleContext = React.createContext<UILocale | undefined>(undefined)

// ── Component ──

function UILocaleProvider({ locale, children }: UILocaleProviderProps) {
  return (
    <UILocaleContext.Provider value={locale}>
      {children}
    </UILocaleContext.Provider>
  )
}

/**
 * Resolve o locale efetivo de um componente:
 * prop `locale` > `UILocaleProvider` mais próximo > `DEFAULT_UI_LOCALE`.
 * Chamar no topo do componente, antes de qualquer `return` antecipado.
 */
function useUILocale(override?: UILocale): UILocale {
  const contextLocale = React.useContext(UILocaleContext)
  return override ?? contextLocale ?? DEFAULT_UI_LOCALE
}

/**
 * Variante para componentes em que `locale` é opcional e a ausência dele tem
 * significado próprio (ex.: textos fixos em inglês / formatação `en-US`):
 * prop `locale` > `UILocaleProvider` mais próximo > `undefined`.
 * Sem provider e sem prop o resultado é `undefined`, como antes.
 */
function useOptionalUILocale(override?: UILocale): UILocale | undefined
function useOptionalUILocale(override?: string): string | undefined
function useOptionalUILocale(override?: string): string | undefined {
  const contextLocale = React.useContext(UILocaleContext)
  return override ?? contextLocale
}

export { UILocaleProvider, useUILocale, useOptionalUILocale }
