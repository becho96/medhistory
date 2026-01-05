import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/authStore'
import { Heart, Loader2 } from 'lucide-react'

export default function GoogleCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')

      if (errorParam) {
        setError('Авторизация через Google была отменена')
        toast.error('Авторизация отменена')
        setTimeout(() => navigate('/login'), 2000)
        return
      }

      if (!code) {
        setError('Не получен код авторизации от Google')
        toast.error('Ошибка авторизации')
        setTimeout(() => navigate('/login'), 2000)
        return
      }

      try {
        // Exchange code for token
        const tokenData = await authService.googleCallback(code, state || undefined)
        
        // Save token
        localStorage.setItem('auth_token', tokenData.access_token)
        
        // Get user info
        const user = await authService.getCurrentUser()
        setAuth(user, tokenData.access_token)
        
        toast.success('Вход через Google выполнен успешно')
        navigate('/')
      } catch (err: any) {
        console.error('Google auth error:', err)
        const message = err.response?.data?.detail || 'Ошибка авторизации через Google'
        setError(message)
        toast.error(message)
        setTimeout(() => navigate('/login'), 3000)
      }
    }

    handleCallback()
  }, [searchParams, navigate, setAuth])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 rounded-full bg-gradient-to-r from-[#4A90E2] to-[#3A7BC8] flex items-center justify-center mb-6">
            <Heart className="h-10 w-10 text-white" />
          </div>
          
          {error ? (
            <>
              <h2 className="text-xl font-bold text-red-600 mb-2">Ошибка авторизации</h2>
              <p className="text-gray-600 text-center">{error}</p>
              <p className="text-sm text-gray-400 mt-4">Перенаправление на страницу входа...</p>
            </>
          ) : (
            <>
              <Loader2 className="h-8 w-8 text-[#4A90E2] animate-spin mb-4" />
              <h2 className="text-xl font-bold text-gray-900 mb-2">Авторизация через Google</h2>
              <p className="text-gray-600">Пожалуйста, подождите...</p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

