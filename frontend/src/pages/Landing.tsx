import { Link } from 'react-router-dom';
import { 
  FileSearch, 
  Users, 
  Shield,
  CheckCircle2,
  ArrowRight,
  BarChart3,
  Clock3,
  Lock,
  Zap,
  FileCheck,
  HeartPulse,
  FileText
} from 'lucide-react';
import GraphVisualization from '../components/Landing/GraphVisualization';
import TimelineVisualization from '../components/Landing/TimelineVisualization';

const Landing = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Navigation */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <HeartPulse className="w-8 h-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">MedHistory</span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Войти
              </Link>
              <Link
                to="/register"
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm hover:shadow-md"
              >
                Регистрация
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-12 sm:py-16 md:py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-4 sm:mb-6 leading-tight">
              Вся медицинская история{' '}
              <span className="text-blue-600">вашей семьи</span>
              <br className="hidden sm:block" />
              <span className="sm:hidden"> </span>в одном месте
            </h1>
            
            <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-8 sm:mb-10 max-w-3xl mx-auto leading-relaxed">
              Загружайте документы, получайте интерпретацию анализов 
              и контролируйте показатели здоровья на интерактивных графиках. 
              MedHistory систематизирует ваши медицинские данные автоматически.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
              <Link
                to="/register"
                className="bg-blue-600 text-white px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl hover:bg-blue-700 transition-all font-semibold text-base sm:text-lg shadow-lg hover:shadow-xl flex items-center justify-center gap-2 group"
              >
                Попробовать бесплатно
                <ArrowRight className="w-4 h-4 sm:w-5 sm:h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                to="/login"
                className="bg-white text-gray-700 px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl hover:bg-gray-50 transition-colors font-semibold text-base sm:text-lg border-2 border-gray-200 flex items-center justify-center gap-2"
              >
                Войти
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-12 sm:py-16 md:py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-3 sm:mb-4">
              MedHistory автоматизирует всё, что делали вручную
            </h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-600">
              Просто загрузите документы
            </p>
          </div>

          {/* Feature 1: Document Analysis */}
          <div className="mb-12 sm:mb-16 md:mb-20">
            <div className="grid md:grid-cols-2 gap-8 sm:gap-12 items-center">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3 sm:mb-4">
                  Проанализируем ваши документы за вас
                </h3>
                <p className="text-base sm:text-lg text-gray-600 mb-4 sm:mb-6">
                  Просто загрузите результат анализа, приема врача или другой медицинский документ — 
                  сервис автоматически:
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      Определит тип документа (анализ крови, УЗИ, прием врача)
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      Определит дату, клинику и другие параметры
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      Классифицирует по специализации
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      Распознает даже рукописный текст
                    </span>
                  </li>
                </ul>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-2xl p-8 border border-gray-200">
                <div className="bg-white rounded-xl p-6 shadow-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">Анализ крови</p>
                      <p className="text-sm text-gray-500">Загружен только что</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-600">Тип документа:</span>
                      <span className="font-medium text-gray-900">Общий анализ крови</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-600">Дата:</span>
                      <span className="font-medium text-gray-900">15 января 2024</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-600">Специализация:</span>
                      <span className="font-medium text-gray-900">Гематология</span>
                    </div>
                    <div className="flex justify-between py-2">
                      <span className="text-gray-600">Учреждение:</span>
                      <span className="font-medium text-gray-900">Клиника "Здоровье"</span>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-green-600 text-sm font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    Обработано
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 2: Graphs */}
          <div className="mb-20">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="order-2 md:order-1">
                <GraphVisualization />
              </div>
              <div className="order-1 md:order-2">
                <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <BarChart3 className="w-4 h-4" />
                  Визуализация данных
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">
                  Следите за динамикой, а не просто за цифрами
                </h3>
                <p className="text-lg text-gray-600 mb-6">
                  Система автоматически строит графики по всем анализам:
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Гемоглобин, холестерин, сахар</strong> — вся динамика на одном экране
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Сравнение с нормой</strong> — цветовые индикаторы покажут отклонения
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Тренды</strong> — растут или падают показатели?
                    </span>
                  </li>
                </ul>
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-800">
                    💡 <strong>Пример:</strong> "Гемоглобин вырос со 110 до 135 г/л — 
                    вы увидите всю динамику наглядно на одном графике"
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 3: Timeline */}
          <div className="mb-20">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 bg-purple-50 text-purple-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                <Clock3 className="w-4 h-4" />
                Интерактивная навигация
              </div>
              <h3 className="text-3xl font-bold text-gray-900 mb-4">
                Вся история болезни перед глазами
              </h3>
              <p className="text-lg text-gray-600 max-w-3xl mx-auto">
                Навигация по медицинским документам стала простой
              </p>
            </div>
            <TimelineVisualization />
            <div className="grid md:grid-cols-4 gap-4 mt-8">
              <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-900">Хронологический порядок</p>
                <p className="text-xs text-gray-600 mt-1">От первого до последнего</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-900">Цветовое кодирование</p>
                <p className="text-xs text-gray-600 mt-1">Каждая специализация имеет свой цвет</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-900">Умные фильтры</p>
                <p className="text-xs text-gray-600 mt-1">Найдите нужный документ за секунды</p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-900">Быстрый поиск</p>
                <p className="text-xs text-gray-600 mt-1">Мгновенный доступ к истории</p>
              </div>
            </div>
          </div>

          {/* Feature 4: Interpretation */}
          <div className="mb-20">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <FileSearch className="w-4 h-4" />
                  Понятные объяснения
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">
                  Понятное объяснение вместо медицинского жаргона
                </h3>
                <p className="text-lg text-gray-600 mb-6">
                  Не знаете, что означают латинские аббревиатуры в анализе крови?
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Простым языком</strong> — что показывает каждый параметр
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Оценка отклонений</strong> — норма, повышен или понижен
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Рекомендации</strong> — на что обратить внимание врача
                    </span>
                  </li>
                </ul>
                <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-sm text-yellow-800">
                    ⚠️ <strong>Важно:</strong> Это не заменяет консультацию специалиста, 
                    но помогает быть информированным пациентом
                  </p>
                </div>
              </div>
              <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-2xl p-8 border border-gray-200">
                <div className="bg-white rounded-xl p-6 shadow-lg">
                  <h4 className="font-semibold text-gray-900 mb-4">Интерпретация анализа крови</h4>
                  <div className="space-y-4">
                    <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Гемоглобин: 145 г/л</p>
                        <p className="text-xs text-gray-600 mt-1">✅ В норме. Показатель отвечает за перенос кислорода в крови.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Холестерин: 6.2 ммоль/л</p>
                        <p className="text-xs text-gray-600 mt-1">⚠️ Немного повышен. Рекомендуется скорректировать диету и увеличить физическую активность.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">Глюкоза: 5.1 ммоль/л</p>
                        <p className="text-xs text-gray-600 mt-1">✅ В норме. Уровень сахара в крови находится в допустимых пределах.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 5: Family Management */}
          <div className="mb-20">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="order-2 md:order-1">
                <div className="bg-gradient-to-br from-pink-50 to-purple-50 rounded-2xl p-8 border border-gray-200">
                  <div className="bg-white rounded-xl p-6 shadow-lg">
                    <h4 className="font-semibold text-gray-900 mb-4">Члены семьи</h4>
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                          И
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">Иван Петров</p>
                          <p className="text-sm text-gray-600">48 документов</p>
                        </div>
                        <CheckCircle2 className="w-5 h-5 text-blue-600" />
                      </div>
                      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="w-12 h-12 bg-pink-500 rounded-full flex items-center justify-center text-white font-semibold">
                          М
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">Мария Петрова</p>
                          <p className="text-sm text-gray-600">35 документов</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center text-white font-semibold">
                          А
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">Анна Петрова</p>
                          <p className="text-sm text-gray-600">22 документа</p>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                      <p className="text-sm text-green-800">
                        <CheckCircle2 className="w-4 h-4 inline mr-1" />
                        Система автоматически определила 3 члена семьи
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="order-1 md:order-2">
                <div className="inline-flex items-center gap-2 bg-pink-50 text-pink-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <Users className="w-4 h-4" />
                  Семейное здоровье
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">
                  Управляйте здоровьем всей семьи
                </h3>
                <p className="text-lg text-gray-600 mb-6">
                  Один аккаунт для всех медицинских документов семьи
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Автоматическое распознавание</strong> — система определит, чей это документ
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Отдельные профили</strong> — мама, папа, дети
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Единый доступ</strong> — не нужно переключаться между аккаунтами
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Feature 6: Doctor Reports */}
          <div>
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <div className="inline-flex items-center gap-2 bg-teal-50 text-teal-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <FileCheck className="w-4 h-4" />
                  Экономия времени
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">
                  Отчеты для врачей за минуту
                </h3>
                <p className="text-lg text-gray-600 mb-6">
                  Идете к новому врачу? Создайте полный отчет за 1 клик
                </p>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Хронология обращений</strong> по выбранной специализации
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Ключевые анализы</strong> и их динамика
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>Назначенное лечение</strong> и результаты
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">
                      <strong>PDF формат</strong> — распечатайте или отправьте врачу заранее
                    </span>
                  </li>
                </ul>
                <div className="mt-6 p-4 bg-teal-50 rounded-lg border border-teal-200">
                  <p className="text-sm text-teal-800">
                    <Zap className="w-4 h-4 inline mr-1" />
                    Вместо 15 минут рассказа — 2 минуты на просмотр структурированной истории
                  </p>
                </div>
              </div>
              <div className="bg-gradient-to-br from-teal-50 to-blue-50 rounded-2xl p-8 border border-gray-200">
                <div className="bg-white rounded-xl p-6 shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-semibold text-gray-900">Отчет для кардиолога</h4>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">Готов</span>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="font-medium text-gray-900 mb-1">📋 Период</p>
                      <p className="text-gray-600">Январь 2023 - Июнь 2024</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="font-medium text-gray-900 mb-1">🏥 Обращений</p>
                      <p className="text-gray-600">12 приемов, 8 анализов, 3 ЭКГ</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="font-medium text-gray-900 mb-1">📊 Ключевые показатели</p>
                      <p className="text-gray-600">Холестерин, давление, пульс</p>
                    </div>
                  </div>
                  <button className="w-full mt-4 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium">
                    Скачать PDF
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              3 простых шага до полного контроля
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold text-blue-600">
                1
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Загрузите документы
              </h3>
              <p className="text-gray-600">
                Перетащите файлы (PDF, фото, скан) или сделайте фото документа прямо в приложении
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold text-green-600">
                2
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                MedHistory обработает автоматически
              </h3>
              <p className="text-gray-600">
                Система распознает тип документа, извлечет данные, построит графики.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold text-purple-600">
                3
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Управляйте историей
              </h3>
              <p className="text-gray-600">
                Просматривайте таймлайн, анализируйте динамику, генерируйте отчеты — всё под рукой
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Target Audience */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              MedHistory создан для тех, кто ценит своё время и здоровье
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">🏃‍♀️</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Активные пациенты
              </h3>
              <p className="text-gray-600">
                Регулярно проходите обследования? Хотите отслеживать динамику показателей 
                и эффективность лечения? MedHistory — ваш личный медицинский ассистент.
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">👨‍👩‍👧</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Заботливые родители
              </h3>
              <p className="text-gray-600">
                Управляйте медицинскими данными всей семьи из одного места. 
                Никогда больше не потеряете карту прививок или справку для школы.
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="text-4xl mb-4">🏥</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Пациенты с хроническими заболеваниями
              </h3>
              <p className="text-gray-600">
                Диабет, гипертония, аллергии — контролируйте состояние, видьте тренды, 
                делитесь полной историей с врачами мгновенно.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <Shield className="w-16 h-16 text-blue-600 mx-auto mb-4" />
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ваши данные под надежной защитой
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="flex gap-4 p-6 bg-gray-50 rounded-xl">
              <Lock className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Шифрование данных</h3>
                <p className="text-gray-600 text-sm">
                  Все файлы защищены при передаче и хранении
                </p>
              </div>
            </div>

            <div className="flex gap-4 p-6 bg-gray-50 rounded-xl">
              <CheckCircle2 className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">GDPR-compliant</h3>
                <p className="text-gray-600 text-sm">
                  Соответствие стандартам защиты персональных данных
                </p>
              </div>
            </div>

            <div className="flex gap-4 p-6 bg-gray-50 rounded-xl">
              <Users className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Только вы имеете доступ</h3>
                <p className="text-gray-600 text-sm">
                  Никто не видит ваши документы без вашего разрешения
                </p>
              </div>
            </div>

            <div className="flex gap-4 p-6 bg-gray-50 rounded-xl">
              <Shield className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Регулярные аудиты</h3>
                <p className="text-gray-600 text-sm">
                  Мы следим за защитой 24/7
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-blue-700 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-bold mb-6">
            Начните систематизировать здоровье уже сегодня
          </h2>
          <p className="text-xl text-blue-100 mb-10">
            Регистрация занимает 30 секунд. Первые 50 документов — бесплатно.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <Link
              to="/register"
              className="bg-white text-blue-600 px-8 py-4 rounded-xl hover:bg-gray-50 transition-all font-semibold text-lg shadow-lg hover:shadow-xl flex items-center justify-center gap-2 group"
            >
              Создать аккаунт бесплатно
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>

          <p className="text-blue-100 text-sm">
            Не требуется кредитная карта • Работает на всех устройствах • Поддержка 24/7
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center mb-4">
                <HeartPulse className="w-6 h-6 text-blue-500" />
                <span className="ml-2 text-lg font-bold text-white">MedHistory</span>
              </div>
              <p className="text-sm text-gray-400">
                Персональная система управления медицинской историей
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-3">Продукт</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">Возможности</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Тарифы</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Обновления</a></li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-3">Ресурсы</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">Документация</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Блог</a></li>
                <li><a href="#" className="hover:text-white transition-colors">FAQ</a></li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-3">Компания</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">О нас</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Контакты</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Политика конфиденциальности</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-8 text-center text-sm text-gray-400">
            <p>&copy; 2024 MedHistory. Все права защищены.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;

