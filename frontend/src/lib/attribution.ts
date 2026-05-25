// First-touch marketing attribution.
//
// Captures utm_* parameters (and the referrer) the first time a visitor
// lands on the site, and persists them so they can be attached to the
// eventual signup — no matter how many pages the visitor browses first.

const STORAGE_KEY = 'mh_attribution'
const UTM_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_content',
  'utm_term',
] as const

export type Attribution = Record<string, string>

/**
 * Records first-touch attribution. Idempotent: once stored, never overwritten,
 * so the original acquisition channel is preserved across return visits.
 */
export function captureAttribution(): void {
  if (typeof window === 'undefined') return
  if (localStorage.getItem(STORAGE_KEY)) return

  const params = new URLSearchParams(window.location.search)
  const utm = UTM_KEYS.reduce<Attribution>((acc, key) => {
    const value = params.get(key)
    return value ? { ...acc, [key]: value.slice(0, 200) } : acc
  }, {})

  const referrer = (document.referrer || '').slice(0, 500)
  if (Object.keys(utm).length === 0 && !referrer) return

  const attribution: Attribution = {
    ...utm,
    ...(referrer ? { referrer } : {}),
    landing_at: new Date().toISOString(),
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(attribution))
}

/** Returns the stored first-touch attribution, or null if none was captured. */
export function getAttribution(): Attribution | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Attribution) : null
  } catch {
    return null
  }
}

/**
 * Normalized acquisition channel label, mirroring the backend's signup_source
 * logic (auth.py): utm_source → that value, else a referrer → 'referral',
 * else 'direct'. Used to break Metrika goals down by channel.
 */
export function getSourceLabel(): string {
  const attribution = getAttribution()
  if (attribution?.utm_source) return attribution.utm_source
  if (attribution?.referrer) return 'referral'
  return 'direct'
}
