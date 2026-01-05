import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { Heart, Mail, Lock, User } from 'lucide-react'

// Google Icon component
const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
    />
  </svg>
)

export default function Register() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  const registerMutation = useMutation({
    mutationFn: authService.register,
    onSuccess: () => {
      toast.success('Регистрация успешна! Теперь войдите в систему.')
      navigate('/login')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Ошибка регистрации')
    },
  })

  const handleGoogleSignup = async () => {
    setIsGoogleLoading(true)
    try {
      const { auth_url, state } = await authService.getGoogleAuthUrl()
      // Save state for CSRF verification
      sessionStorage.setItem('google_oauth_state', state)
      // Redirect to Google
      window.location.href = auth_url
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка подключения к Google')
      setIsGoogleLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    registerMutation.mutate({ email, password, full_name: fullName })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-purple-50 to-pink-50 p-3 sm:p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl sm:rounded-2xl shadow-2xl overflow-hidden">
          {/* Header Section */}
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 sm:px-8 py-8 sm:py-10 text-white">
            <div className="flex justify-center mb-3 sm:mb-4">
              <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Heart className="h-8 w-8 sm:h-10 sm:w-10 text-white" />
              </div>
            </div>
            <h2 className="text-center text-2xl sm:text-3xl font-bold mb-1 sm:mb-2">
              Регистрация
            </h2>
            <p className="text-center text-sm sm:text-base text-purple-100">
              Создайте свой аккаунт MedHistory
            </p>
          </div>
          
          {/* Form Section */}
          <div className="p-6 sm:p-8">
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-5">
                <div>
                  <label htmlFor="fullName" className="block text-sm font-semibold text-gray-700 mb-2">
                    Полное имя
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="fullName"
                      name="fullName"
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 text-gray-900"
                      placeholder="Иван Иванов"
                    />
                  </div>
                </div>
                
                <div>
                  <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
                    Email
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 text-gray-900"
                      placeholder="your@email.com"
                    />
                  </div>
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                    Пароль
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="new-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-purple-600 text-gray-900"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={registerMutation.isPending}
                className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-purple-200/50"
              >
                {registerMutation.isPending ? '⏳ Регистрация...' : '✨ Зарегистрироваться'}
              </button>

              {/* Divider */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500">или</span>
                </div>
              </div>

              {/* Google Signup Button */}
              <button
                type="button"
                onClick={handleGoogleSignup}
                disabled={isGoogleLoading}
                className="w-full flex items-center justify-center gap-3 py-3 px-4 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <GoogleIcon />
                {isGoogleLoading ? 'Подключение...' : 'Зарегистрироваться через Google'}
              </button>

              <div className="text-center pt-4 border-t border-gray-100">
                <Link
                  to="/login"
                  className="font-semibold text-purple-600 hover:text-purple-700 transition-colors"
                >
                  ← Уже есть аккаунт? Войти
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

