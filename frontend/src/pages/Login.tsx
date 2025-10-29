import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import { Heart, Mail, Lock } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (data) => {
      // Сначала сохраняем токен в localStorage
      localStorage.setItem('auth_token', data.access_token)
      
      // Теперь запрос будет с правильным заголовком Authorization
      const user = await authService.getCurrentUser()
      setAuth(user, data.access_token)
      toast.success('Вход выполнен успешно')
      navigate('/')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Ошибка входа')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loginMutation.mutate({ email, password })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50 p-3 sm:p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl sm:rounded-2xl shadow-2xl overflow-hidden">
          {/* Header Section */}
          <div className="bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] px-6 sm:px-8 py-8 sm:py-10 text-white">
            <div className="flex justify-center mb-3 sm:mb-4">
              <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Heart className="h-8 w-8 sm:h-10 sm:w-10 text-white" />
              </div>
            </div>
            <h2 className="text-center text-2xl sm:text-3xl font-bold mb-1 sm:mb-2">
              MedHistory
            </h2>
            <p className="text-center text-sm sm:text-base text-blue-100">
              Персональная медицинская история
            </p>
          </div>
          
          {/* Form Section */}
          <div className="p-6 sm:p-8">
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-5">
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
                      className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2] text-gray-900"
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
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4A90E2] focus:border-[#4A90E2] text-gray-900"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={loginMutation.isPending}
                className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] hover:from-[#3A7BC8] hover:to-[#2A6BA8] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#4A90E2] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-200/50"
              >
                {loginMutation.isPending ? '⏳ Вход...' : '🚀 Войти'}
              </button>

              <div className="text-center pt-4 border-t border-gray-100">
                <Link
                  to="/register"
                  className="font-semibold text-[#4A90E2] hover:text-[#3A7BC8] transition-colors"
                >
                  Нет аккаунта? Зарегистрироваться →
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

