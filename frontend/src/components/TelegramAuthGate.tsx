import { useEffect, useState, type ReactNode } from 'react'
import { getTelegramWebApp, isTelegramMiniApp } from '../lib/telegram'
import { authenticateWithTelegram } from '../services/telegramAuth'
import { useAuthStore } from '../stores/authStore'

interface TelegramAuthGateProps {
  children: ReactNode
}

/**
 * When the app runs inside a Telegram Mini App, exchanges the signed initData
 * for a session before rendering — so the user lands straight in the
 * authorized zone, as if logged into the mobile app. Outside Telegram (and on
 * failure) it renders children immediately, falling back to the login screen.
 */
export function TelegramAuthGate({ children }: TelegramAuthGateProps) {
  const [ready, setReady] = useState(() => !isTelegramMiniApp())

  useEffect(() => {
    const webApp = getTelegramWebApp()
    if (webApp) {
      webApp.ready()
      webApp.expand()
    }

    const alreadyAuthed = useAuthStore.getState().isAuthenticated
    if (!webApp || !webApp.initData || alreadyAuthed) {
      setReady(true)
      return
    }

    authenticateWithTelegram(webApp.initData)
      .catch(() => undefined) // degrade gracefully to the login screen
      .finally(() => setReady(true))
  }, [])

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-gray-500">
        Авторизация…
      </div>
    )
  }

  return <>{children}</>
}
