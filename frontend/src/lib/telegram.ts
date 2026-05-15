/** Minimal typings and helpers for the Telegram WebApp (Mini App) SDK. */

interface TelegramWebApp {
  /** Signed launch payload — empty when not launched from Telegram. */
  initData: string
  ready: () => void
  expand: () => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null
}

/** True when the app runs inside Telegram with signed initData available. */
export function isTelegramMiniApp(): boolean {
  const webApp = getTelegramWebApp()
  return Boolean(webApp && webApp.initData)
}
