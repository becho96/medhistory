import { Link } from 'react-router-dom';
import {
  FileSearch,
  Users,
  Shield,
  ArrowRight,
  BarChart3,
  Lock,
  FileCheck,
  HeartPulse,
  Bot,
  CheckCircle2,
} from 'lucide-react';
import GraphVisualization from '../components/Landing/GraphVisualization';

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

      {/* Hero */}
      <section className="py-16 sm:py-20 md:py-28 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
              <Bot className="w-4 h-4" />
              AI-ассистент на основе вашей медицинской истории
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-6 leading-tight">
              Ваш личный{' '}
              <span className="text-blue-600">AI-помощник</span>
              <br className="hidden sm:block" />
              {' '}в вопросах здоровья
            </h1>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
              Загружайте медицинские документы — и получайте персональные рекомендации:
              когда пройти чекап, к какому специалисту обратиться.
              Не врач, но умный навигатор в вашей медицинской истории.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
              <Link
                to="/register"
                className="bg-blue-600 text-white px-6 sm:px-8 py-3 sm:py-4 rounded-xl hover:bg-blue-700 transition-all font-semibold text-base sm:text-lg shadow-lg hover:shadow-xl flex items-center justify-center gap-2 group"
              >
                Попробовать бесплатно
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                to="/login"
                className="bg-white text-gray-700 px-6 sm:px-8 py-3 sm:py-4 rounded-xl hover:bg-gray-50 transition-colors font-semibold text-base sm:text-lg border-2 border-gray-200 flex items-center justify-center gap-2"
              >
                Войти
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* AI Assistant Section */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Как AI-ассистент работает с вашими данными
            </h2>
            <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
              Анализирует всю историю целиком и подсказывает следующий шаг — на основе именно вашей динамики
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-10 items-center">
            {/* AI mockup */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-xl overflow-hidden">
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-5 py-4 flex items-center gap-3">
                <div className="w-9 h-9 bg-white/20 rounded-full flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-white text-sm">AI-ассистент MedHistory</p>
                  <p className="text-blue-100 text-xs">Анализирует вашу медицинскую историю</p>
                </div>
              </div>

              <div className="p-5 space-y-3">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wide mb-4">
                  На основе 12 документов за 2023–2024
                </p>

                <div className="flex gap-3 items-start">
                  <span className="text-lg flex-shrink-0">⚡</span>
                  <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      Гемоглобин снижался 3 месяца подряд
                    </p>
                    <p className="text-xs text-amber-700 mt-1">
                      Рекомендуем консультацию терапевта
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 items-start">
                  <span className="text-lg flex-shrink-0">📅</span>
                  <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      Последняя ЭКГ: больше 2 лет назад
                    </p>
                    <p className="text-xs text-blue-700 mt-1">
                      Пора на плановый кардиологический чекап
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 items-start">
                  <span className="text-lg flex-shrink-0">✅</span>
                  <div className="bg-green-50 border border-green-100 rounded-xl px-4 py-3 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      Холестерин стабильно в норме
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      Следующий контроль через 6 месяцев
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 flex items-start gap-2">
                  <span className="text-gray-400 text-xs mt-0.5">⚠️</span>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    AI-ассистент не является врачом и не ставит диагнозов.
                    Он помогает ориентироваться в вашей медицинской истории
                    и не заменяет консультацию специалиста.
                  </p>
                </div>
              </div>
            </div>

            {/* Benefits */}
            <div className="space-y-6">
              <div className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">
                    Видит картину целиком
                  </h3>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    Анализирует не один документ, а всю вашу историю — приёмы, анализы, динамику показателей за годы.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">
                    Напоминает о плановых обследованиях
                  </h3>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    На основе вашей истории подсказывает, когда пора на чекап и чем вызвана такая рекомендация.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">
                    Рекомендует профиль врача
                  </h3>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    Если тренд настораживает — уточняет, к какому специалисту обратиться и почему именно к нему.
                  </p>
                </div>
              </div>

              <Link
                to="/register"
                className="inline-flex items-center gap-2 text-blue-600 font-semibold hover:text-blue-700 transition-colors group mt-2"
              >
                Попробовать бесплатно
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Всё, что нужно для контроля здоровья
            </h2>
            <p className="text-base sm:text-lg text-gray-600">
              AI-рекомендации работают тем точнее, чем полнее ваша медицинская история
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-6 mb-16">
            <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-colors">
              <div className="w-11 h-11 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                <FileSearch className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Умная обработка документов
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Загрузите PDF, фото или скан — тип документа, дата, клиника и параметры определятся автоматически, включая рукописный текст.
              </p>
            </div>

            <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 hover:border-green-200 hover:bg-green-50/30 transition-colors">
              <div className="w-11 h-11 bg-green-100 rounded-xl flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Динамика показателей
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Графики по всем анализам с отметкой нормы — сразу видно тренды по гемоглобину, холестерину, сахару и сотням других параметров.
              </p>
            </div>

            <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/30 transition-colors">
              <div className="w-11 h-11 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Вся семья в одном месте
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Отдельные профили для каждого члена семьи, один аккаунт. Медицинская история детей, родителей и партнёра — всегда под рукой.
              </p>
            </div>

            <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 hover:border-teal-200 hover:bg-teal-50/30 transition-colors">
              <div className="w-11 h-11 bg-teal-100 rounded-xl flex items-center justify-center mb-4">
                <FileCheck className="w-6 h-6 text-teal-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Отчёт для врача за минуту
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Структурированная история по специализации, ключевые анализы и динамика — готовый PDF в один клик перед любым приёмом.
              </p>
            </div>
          </div>

          {/* Graph visualization */}
          <div className="bg-gradient-to-br from-green-50 to-blue-50 rounded-2xl p-6 sm:p-8 border border-gray-200">
            <p className="text-center text-sm font-medium text-gray-500 mb-6">
              Пример: динамика гемоглобина за 6 месяцев
            </p>
            <GraphVisualization />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-4">
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
                Система распознает тип документа, извлечёт данные и построит графики динамики показателей
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold text-purple-600">
                3
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                Получайте AI-рекомендации
              </h3>
              <p className="text-gray-600">
                Управляйте историей, получайте подсказки о чекапах и визитах к специалистам — всё в одном месте
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <Shield className="w-14 h-14 text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ваши данные под надёжной защитой
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="flex gap-4 p-5 bg-gray-50 rounded-xl">
              <Lock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-1 text-sm">Шифрование данных</h3>
                <p className="text-gray-600 text-xs">Все файлы защищены при передаче и хранении</p>
              </div>
            </div>
            <div className="flex gap-4 p-5 bg-gray-50 rounded-xl">
              <CheckCircle2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-1 text-sm">GDPR-compliant</h3>
                <p className="text-gray-600 text-xs">Соответствие стандартам защиты персональных данных</p>
              </div>
            </div>
            <div className="flex gap-4 p-5 bg-gray-50 rounded-xl">
              <Users className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-1 text-sm">Только вы имеете доступ</h3>
                <p className="text-gray-600 text-xs">Никто не видит ваши документы без вашего разрешения</p>
              </div>
            </div>
            <div className="flex gap-4 p-5 bg-gray-50 rounded-xl">
              <Shield className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-1 text-sm">Регулярные аудиты</h3>
                <p className="text-gray-600 text-xs">Мы следим за защитой 24/7</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-blue-700 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-6">
            Узнайте, что AI расскажет о вашей медицинской истории
          </h2>
          <p className="text-lg sm:text-xl text-blue-100 mb-10">
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
