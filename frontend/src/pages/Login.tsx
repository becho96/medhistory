import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import { HeartPulse } from 'lucide-react'

const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
)

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (data) => {
      localStorage.setItem('auth_token', data.access_token)
      const user = await authService.getCurrentUser()
      setAuth(user, data.access_token)
      toast.success('Вход выполнен успешно')
      navigate('/')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Ошибка входа')
    },
  })

  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true)
    try {
      const { auth_url, state } = await authService.getGoogleAuthUrl()
      sessionStorage.setItem('google_oauth_state', state)
      window.location.href = auth_url
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка подключения к Google')
      setIsGoogleLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ email, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-10">
          <HeartPulse className="w-6 h-6 text-emerald-500" strokeWidth={2} />
          <span className="text-[20px] font-semibold text-gray-900 tracking-tight">MedHistory</span>
        </div>

        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-[28px] font-semibold text-gray-900 tracking-tight mb-2">
            Войти в аккаунт
          </h1>
          <p className="text-[15px] text-gray-500">
            Добро пожаловать обратно
          </p>
        </div>

        {/* Google Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isGoogleLoading}
          className="w-full flex items-center justify-center gap-3 h-[48px] border border-gray-200 rounded-xl text-[15px] font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mb-6"
        >
          <GoogleIcon />
          {isGoogleLoading ? 'Подключение...' : 'Войти через Google'}
        </button>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-100" />
          </div>
          <div className="relative flex justify-center">
            <span className="px-4 bg-white text-[13px] text-gray-400">или</span>
          </div>
        </div>

        {/* Form */}
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

        {/* Footer link */}
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
