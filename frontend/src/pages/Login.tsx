import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import { HeartPulse } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const rawNext = searchParams.get('next')
  const next = rawNext && rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '/'

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (data) => {
      localStorage.setItem('auth_token', data.access_token)
      const user = await authService.getCurrentUser()
      setAuth(user, data.access_token)
      toast.success('Вход выполнен успешно')
      navigate(next)
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((e: any) => e.msg).join('; ')
          : 'Ошибка входа'
      toast.error(message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ email, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4">
      <div className="w-full max-w-[400px]">
        <div className="flex items-center justify-center gap-2 mb-10">
          <HeartPulse className="w-6 h-6 text-emerald-500" strokeWidth={2} />
          <span className="text-[20px] font-semibold text-gray-900 tracking-tight">MedHistory</span>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-[28px] font-semibold text-gray-900 tracking-tight mb-2">
            Войти в аккаунт
          </h1>
          <p className="text-[15px] text-gray-500">
            Добро пожаловать обратно
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-[13px] font-medium text-gray-700 mb-1.5">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-[48px] px-4 border border-gray-200 rounded-xl text-[15px] text-gray-900 placeholder:text-gray-400 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-[13px] font-medium text-gray-700 mb-1.5">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-[48px] px-4 border border-gray-200 rounded-xl text-[15px] text-gray-900 placeholder:text-gray-400 outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full h-[48px] bg-emerald-500 text-white rounded-xl text-[15px] font-medium hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-2"
          >
            {loginMutation.isPending ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <p className="text-center mt-8 text-[14px] text-gray-500">
          Нет аккаунта?{' '}
          <Link to="/register" className="font-medium text-emerald-600 hover:text-emerald-700 transition-colors">
            Зарегистрироваться
          </Link>
        </p>
      </div>
    </div>
  )
}
