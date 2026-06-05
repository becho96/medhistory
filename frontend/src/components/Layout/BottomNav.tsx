import { Link, useLocation } from 'react-router-dom'
import { Home, FileText, FlaskConical, User } from 'lucide-react'

const tabs = [
  { name: 'Главная',  href: '/',          icon: Home },
  { name: 'Медкарта', href: '/documents', icon: FileText },
  { name: 'Анализы',  href: '/labs',      icon: FlaskConical },
  { name: 'Профиль', href: '/profile', icon: User, matches: ['/profile', '/settings', '/subscription', '/health-events', '/admin'] },
]

export default function BottomNav() {
  const location = useLocation()

  return (
    <nav
      className="w-full flex-shrink-0 bg-white/95 backdrop-blur-md border-t border-gray-100 lg:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex h-14">
        {tabs.map((tab) => {
          const isActive = tab.href === '/'
            ? location.pathname === tab.href
            : (tab.matches || [tab.href]).some((path) => location.pathname.startsWith(path))
          return (
            <Link
              key={tab.href}
              to={tab.href}
              className={`relative flex-1 flex min-h-16 flex-col items-center justify-center gap-0.5 transition-colors active:opacity-60 ${
                isActive ? 'text-emerald-500' : 'text-gray-400'
              }`}
            >
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-emerald-500 rounded-full" />
              )}
              <tab.icon className="w-5 h-5" strokeWidth={isActive ? 2.5 : 1.75} />
              <span className="text-[10px] font-medium leading-none">{tab.name}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
