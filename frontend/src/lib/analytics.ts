// Yandex Metrika integration.
//
// The counter ID comes from the VITE_YM_ID env var, injected at build time as
// a Docker build arg (see docker-compose.prod.yml). It is unset in local dev,
// so analytics stays off there and dev traffic never pollutes the counter.
// Every function no-ops gracefully when the ID is absent.

const YM_ID = import.meta.env.VITE_YM_ID

type YmFn = ((...args: unknown[]) => void) & { a?: unknown[]; l?: number }

declare global {
  interface Window {
    ym?: YmFn
  }
}

let initialized = false

/** Loads the Yandex Metrika tag and initializes the counter. Call once on app start. */
export function initAnalytics(): void {
  if (initialized || !YM_ID || typeof window === 'undefined') return
  initialized = true

  // Standard Metrika loader stub — queues calls until tag.js is ready.
  const stub: YmFn = function (...args: unknown[]) {
    stub.a = stub.a || []
    stub.a.push(args)
  }
  stub.l = Date.now()
  window.ym = window.ym || stub

  const script = document.createElement('script')
  script.async = true
  script.src = 'https://mc.yandex.ru/metrika/tag.js'
  document.head.appendChild(script)

  window.ym(Number(YM_ID), 'init', {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: true,
  })
}

/** Fires a Metrika goal (создаётся в интерфейсе Метрики как «JavaScript-событие»). */
export function trackGoal(goal: string, params?: Record<string, unknown>): void {
  if (!YM_ID || typeof window === 'undefined' || !window.ym) return
  window.ym(Number(YM_ID), 'reachGoal', goal, params)
}

/**
 * Records an SPA pageview. The Metrika 'init' call already counts the first
 * page load, so callers must skip the initial render and only fire this on
 * subsequent client-side route changes.
 */
export function trackPageview(): void {
  if (!YM_ID || typeof window === 'undefined' || !window.ym) return
  window.ym(Number(YM_ID), 'hit', window.location.href)
}
