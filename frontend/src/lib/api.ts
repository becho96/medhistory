import axios from 'axios'

// Для production (через nginx reverse proxy) используем относительный путь
// Для development используем прямой URL к backend
const API_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'production' ? '' : 'http://localhost:8000')

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  paramsSerializer: {
    serialize: (params) => {
      // Сериализация параметров для FastAPI
      // Массивы должны быть в формате: ?key=value1&key=value2
      const searchParams = new URLSearchParams()
      
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null) {
          return
        }
        
        if (Array.isArray(value)) {
          // Для массивов добавляем каждый элемент отдельно
          value.forEach((item) => {
            if (item !== undefined && item !== null) {
              searchParams.append(key, String(item))
            }
          })
        } else {
          searchParams.append(key, String(value))
        }
      })
      
      return searchParams.toString()
    }
  }
})

// Функция для получения активного профиля из localStorage
const getActiveProfileId = (): string | null => {
  try {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      const parsed = JSON.parse(authStorage)
      return parsed?.state?.activeProfileId || null
    }
  } catch {
    return null
  }
  return null
}

// Request interceptor to add auth token and profile ID
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Добавляем X-Profile-Id если выбран не свой профиль
    const activeProfileId = getActiveProfileId()
    if (activeProfileId) {
      // Получаем ID текущего пользователя
      try {
        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const parsed = JSON.parse(authStorage)
          const userId = parsed?.state?.user?.id
          // Только добавляем header если это не свой профиль
          if (userId && activeProfileId !== userId) {
            config.headers['X-Profile-Id'] = activeProfileId
          }
        }
      } catch {
        // Ignore parsing errors
      }
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

