import { Link } from 'react-router-dom';
import {
  FileSearch, BarChart3, FileCheck,
  HeartPulse, Bot, CheckCircle2, AlertTriangle, Calendar,
  Shield, ChevronRight,
} from 'lucide-react';
import GraphVisualization from '../components/Landing/GraphVisualization';

const Landing = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-10 flex justify-between items-center h-[52px]">
          <Link to="/" className="flex items-center gap-2">
            <HeartPulse className="w-[18px] h-[18px] text-emerald-500" strokeWidth={2} />
            <span className="text-[16px] font-semibold text-gray-900 tracking-tight">MedHistory</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {['Возможности', 'Тарифы', 'Блог'].map((item) => (
              <a key={item} href="#" className="px-4 py-2 text-[15px] text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">
                {item}
              </a>
            ))}
          </nav>
          <Link
            to="/register"
            className="bg-gray-900 text-white px-4 sm:px-6 py-2 sm:py-2.5 rounded-full text-[13px] sm:text-[14px] font-medium hover:bg-gray-800 transition-colors"
          >
            Начать бесплатно
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-12 sm:pt-16 pb-16 sm:pb-20 px-4 sm:px-10">
        <div className="max-w-[1400px] mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 border border-gray-200 rounded-full px-1 py-1 mb-6 sm:mb-8">
            <span className="bg-emerald-400 text-white text-[11px] sm:text-[12px] font-medium px-2.5 py-0.5 rounded-full">Новое</span>
            <span className="text-[13px] sm:text-[14px] text-gray-600 pr-2 flex items-center gap-1">
              AI-ассистент на основе вашей истории
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </span>
          </div>

          <h1 className="text-[38px] sm:text-[52px] md:text-[64px] leading-[1.05] font-semibold text-gray-900 tracking-tight max-w-[1088px] mx-auto mb-5 sm:mb-6">
            Умное управление{' '}
            <span className="text-emerald-500">медицинской историей</span>
          </h1>
          <p className="text-[16px] sm:text-[18px] leading-[1.6] text-gray-500 max-w-[680px] mx-auto mb-8 sm:mb-10">
            Загружайте документы, отслеживайте динамику показателей и получайте персональные AI-рекомендации — всё в одном месте.
          </p>

          {/* CTA Button */}
          <div className="mb-7 sm:mb-8">
            <Link
              to="/register"
              className="inline-block bg-emerald-500 text-white px-8 sm:px-10 py-3.5 sm:py-4 rounded-full text-[15px] sm:text-[16px] font-medium hover:bg-emerald-600 transition-colors"
            >
              Попробовать
            </Link>
          </div>

          {/* Social proof */}
          <div className="flex items-center justify-center gap-3">
            <div className="flex -space-x-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="w-8 h-8 rounded-full bg-gray-200 border-2 border-white" />
              ))}
            </div>
            <p className="text-[14px] text-gray-500">
              Более 1,200 пользователей
            </p>
          </div>
        </div>
      </section>

      {/* Dashboard Mockup */}
      <section className="px-4 sm:px-10 pb-16 sm:pb-20">
        <div className="max-w-[1400px] mx-auto">
          <div className="bg-gray-50 rounded-2xl border border-gray-200 p-4 sm:p-6 overflow-hidden">
            {/* Stats row */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-3 sm:mb-4">
              <div className="bg-white rounded-xl border border-gray-100 p-3 sm:p-5">
                <p className="text-[11px] sm:text-[14px] text-gray-500 mb-1 sm:mb-2 leading-tight">Документы загружены</p>
                <p className="text-[24px] sm:text-[36px] font-semibold text-gray-900 tracking-tight">47</p>
                <span className="text-[10px] sm:text-[12px] text-emerald-500 font-medium">+12 за месяц</span>
              </div>
              <div className="bg-white rounded-xl border border-gray-100 p-3 sm:p-5">
                <p className="text-[11px] sm:text-[14px] text-gray-500 mb-1 sm:mb-2 leading-tight">Показателей отслеживается</p>
                <p className="text-[24px] sm:text-[36px] font-semibold text-gray-900 tracking-tight">128</p>
                <span className="text-[10px] sm:text-[12px] text-emerald-500 font-medium">+18.2%</span>
              </div>
              <div className="bg-white rounded-xl border border-gray-100 p-3 sm:p-5">
                <p className="text-[11px] sm:text-[14px] text-gray-500 mb-1 sm:mb-2 leading-tight">AI-рекомендаций</p>
                <p className="text-[24px] sm:text-[36px] font-semibold text-gray-900 tracking-tight">15</p>
                <span className="text-[10px] sm:text-[12px] text-emerald-500 font-medium">3 новых</span>
              </div>
            </div>

            {/* Chart + sidebar */}
            <div className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-3 sm:gap-4">
              <div className="bg-white rounded-xl border border-gray-100 p-4 sm:p-5">
                <GraphVisualization />
              </div>
              <div className="bg-white rounded-xl border border-gray-100 p-4 sm:p-5 space-y-3 sm:space-y-4">
                <p className="text-[14px] font-medium text-gray-900">AI-рекомендации</p>

                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 bg-amber-50 rounded-md flex items-center justify-center shrink-0 mt-0.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-gray-900">Гемоглобин снижался</p>
                    <p className="text-[12px] text-gray-500 mt-0.5">Консультация терапевта</p>
                  </div>
                </div>

                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 bg-blue-50 rounded-md flex items-center justify-center shrink-0 mt-0.5">
                    <Calendar className="w-3.5 h-3.5 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-gray-900">ЭКГ: &gt;2 лет назад</p>
                    <p className="text-[12px] text-gray-500 mt-0.5">Плановый чекап</p>
                  </div>
                </div>

                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 bg-emerald-50 rounded-md flex items-center justify-center shrink-0 mt-0.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-gray-900">Холестерин в норме</p>
                    <p className="text-[12px] text-gray-500 mt-0.5">Контроль через 6 мес.</p>
                  </div>
                </div>

                <div className="border-t border-gray-100 pt-3">
                  <p className="text-[11px] text-gray-400 leading-relaxed">
                    AI не является врачом. Помогает ориентироваться в медицинской истории.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bento Grid Features */}
      <section className="px-4 sm:px-10 pb-16 sm:pb-20 bg-gray-50">
        <div className="max-w-[1400px] mx-auto pt-16 sm:pt-20">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
            {/* Left card */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 flex flex-col">
              <div className="flex items-center gap-2 mb-3">
                <FileSearch className="w-5 h-5 text-emerald-500" />
                <h3 className="text-[16px] font-semibold text-gray-900">Умная обработка</h3>
              </div>
              <p className="text-[15px] text-gray-500 leading-relaxed mb-6">
                Загрузите PDF, фото или скан — тип документа, дата и параметры определятся автоматически.
              </p>
              <div className="mt-auto bg-gray-50 rounded-xl p-4 border border-gray-100">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center">
                    <Bot className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-[12px] font-medium text-gray-900">Анализ крови.pdf</p>
                    <p className="text-[11px] text-emerald-500">Распознан автоматически</p>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div className="bg-emerald-400 h-1.5 rounded-full w-3/4" />
                </div>
              </div>
            </div>

            {/* Center card */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 flex flex-col">
              <div className="text-center mb-6">
                <h3 className="text-[22px] sm:text-[28px] font-semibold text-gray-900 tracking-tight mb-2">
                  Управляйте расходами на здоровье как команда
                </h3>
                <p className="text-[15px] text-gray-500 leading-relaxed">
                  Ведите медицинскую историю всей семьи в одном месте с отдельными профилями.
                </p>
              </div>
              <div className="mt-auto bg-gray-50 rounded-xl p-5 border border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[13px] font-medium text-gray-900">Семейные профили</p>
                  <div className="flex -space-x-1.5">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="w-7 h-7 rounded-full bg-gray-200 border-2 border-white" />
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  {['Мама — 23 документа', 'Папа — 15 документов', 'Ребёнок — 8 документов'].map((item) => (
                    <div key={item} className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
                      <p className="text-[13px] text-gray-700">{item}</p>
                      <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right card */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 flex flex-col sm:col-span-2 lg:col-span-1">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-5 h-5 text-emerald-500" />
                <h3 className="text-[16px] font-semibold text-gray-900">Динамика показателей</h3>
              </div>
              <p className="text-[15px] text-gray-500 leading-relaxed mb-6">
                Графики по всем анализам с зоной нормы — сразу видно тренды за любой период.
              </p>
              <div className="mt-auto flex justify-center">
                <div className="flex -space-x-1.5">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div key={i} className="w-10 h-10 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center">
                      <BarChart3 className="w-4 h-4 text-gray-400" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom left - wide */}
            <div className="col-span-1 sm:col-span-2 bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 flex flex-col sm:flex-row gap-6 sm:gap-8">
              <div className="flex-1">
                <h3 className="text-[22px] sm:text-[28px] font-semibold text-gray-900 tracking-tight mb-3">
                  Отчёт для врача за одну минуту
                </h3>
                <p className="text-[15px] text-gray-500 leading-relaxed mb-6">
                  Структурированная история, ключевые анализы и динамика — готовый PDF перед любым приёмом.
                </p>
                <div className="flex gap-3">
                  <Link to="/register" className="bg-emerald-500 text-white px-5 py-2.5 rounded-full text-[14px] font-medium hover:bg-emerald-600 transition-colors">
                    Попробовать
                  </Link>
                  <Link to="/login" className="border border-gray-200 text-gray-700 px-5 py-2.5 rounded-full text-[14px] font-medium hover:bg-gray-50 transition-colors">
                    Подробнее
                  </Link>
                </div>
              </div>
              <div className="w-full sm:w-[300px] bg-gray-50 rounded-xl border border-gray-100 p-4 space-y-3">
                {['Анализ крови — 12.03.2024', 'ЭКГ — 15.01.2024', 'УЗИ — 08.11.2023'].map((item) => (
                  <div key={item} className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center shrink-0">
                      <FileCheck className="w-4 h-4 text-emerald-500" />
                    </div>
                    <p className="text-[13px] text-gray-700">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom right */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 flex flex-col items-center justify-center text-center">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center mb-4">
                <Shield className="w-6 h-6 text-emerald-500" />
              </div>
              <h3 className="text-[16px] font-semibold text-gray-900 mb-2">Данные под защитой</h3>
              <p className="text-[14px] text-gray-500 leading-relaxed">
                Шифрование, GDPR, доступ только у вас. Регулярные аудиты безопасности 24/7.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="px-4 sm:px-10 py-16 sm:py-20">
        <div className="max-w-[1400px] mx-auto text-center">
          <h2 className="text-[28px] sm:text-[40px] font-semibold text-gray-900 tracking-tight mb-3">
            Что говорят пользователи
          </h2>
          <p className="text-[15px] sm:text-[16px] text-gray-500 max-w-[600px] mx-auto mb-10 sm:mb-12">
            Тысячи людей уже управляют медицинской историей с MedHistory
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
            {[
              { text: 'Наконец-то все анализы в одном месте. AI-подсказки реально помогают не забывать про чекапы.', name: 'Анна М.', role: 'Пользователь' },
              { text: 'Веду историю всей семьи — детей, родителей. Отчёт для врача формируется за секунды, врачи в восторге.', name: 'Дмитрий К.', role: 'Пользователь' },
              { text: 'Загрузил старые анализы — система сразу показала тренды. Увидел снижение гемоглобина за 3 месяца.', name: 'Елена С.', role: 'Пользователь' },
            ].map((review) => (
              <div key={review.name} className="bg-white rounded-2xl border border-gray-200 p-6 text-left">
                <p className="text-[15px] text-gray-600 leading-relaxed mb-6">"{review.text}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gray-100" />
                  <div>
                    <p className="text-[14px] font-medium text-gray-900">{review.name}</p>
                    <p className="text-[12px] text-gray-500">{review.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-4 sm:px-10 py-16 sm:py-20 bg-gray-50">
        <div className="max-w-[1400px] mx-auto text-center">
          <h2 className="text-[28px] sm:text-[40px] font-semibold text-gray-900 tracking-tight mb-3">
            Как это работает
          </h2>
          <p className="text-[15px] sm:text-[16px] text-gray-500 max-w-[600px] mx-auto mb-10 sm:mb-12">
            Три простых шага до полного контроля за здоровьем
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 sm:gap-8">
            {[
              { step: '01', title: 'Загрузите документы', desc: 'PDF, фото, скан или сделайте фото прямо в приложении' },
              { step: '02', title: 'Автоматическая обработка', desc: 'Система распознает тип, извлечёт данные и построит графики' },
              { step: '03', title: 'AI-рекомендации', desc: 'Подсказки о чекапах, визитах к специалистам и динамике' },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-12 h-12 bg-emerald-500 text-white rounded-full flex items-center justify-center mx-auto mb-5 text-[16px] font-semibold">
                  {item.step}
                </div>
                <h3 className="text-[17px] sm:text-[18px] font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-[14px] sm:text-[15px] text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 sm:px-10 py-16 sm:py-20">
        <div className="max-w-[1400px] mx-auto">
          <div className="bg-gray-900 rounded-3xl p-8 sm:p-16 flex flex-col lg:flex-row items-center gap-8 sm:gap-16">
            <div className="flex-1 text-center lg:text-left">
              <h2 className="text-[30px] sm:text-[40px] lg:text-[48px] font-semibold text-white leading-[1.1] tracking-tight mb-6">
                Начните управлять медицинской историей уже сегодня
              </h2>
              <div className="flex gap-3 justify-center lg:justify-start">
                <Link
                  to="/register"
                  className="bg-emerald-500 text-white px-6 sm:px-7 py-3 sm:py-3.5 rounded-full text-[14px] sm:text-[15px] font-medium hover:bg-emerald-600 transition-colors"
                >
                  Создать аккаунт
                </Link>
                <Link
                  to="/login"
                  className="border border-gray-600 text-white px-6 sm:px-7 py-3 sm:py-3.5 rounded-full text-[14px] sm:text-[15px] font-medium hover:bg-gray-800 transition-colors"
                >
                  Войти
                </Link>
              </div>
            </div>
            <div className="hidden lg:flex w-[400px] h-[300px] bg-gray-800 rounded-2xl overflow-hidden items-center justify-center">
              <Bot className="w-16 h-16 text-gray-600" />
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-4 sm:px-10 py-10 sm:py-12 border-t border-gray-100">
        <div className="max-w-[1400px] mx-auto">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 sm:gap-8 mb-10 sm:mb-12">
            <div className="col-span-2 sm:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <HeartPulse className="w-[18px] h-[18px] text-emerald-500" />
                <span className="text-[16px] font-semibold text-gray-900">MedHistory</span>
              </div>
              <p className="text-[14px] text-gray-500 leading-relaxed">
                Персональная система управления медицинской историей
              </p>
            </div>
            {[
              { title: 'Продукт', links: ['Возможности', 'Тарифы', 'Обновления'] },
              { title: 'Ресурсы', links: ['Документация', 'Блог', 'FAQ'] },
              { title: 'Компания', links: ['О нас', 'Контакты', 'Конфиденциальность'] },
            ].map((col) => (
              <div key={col.title}>
                <p className="text-[14px] font-semibold text-gray-900 mb-4">{col.title}</p>
                <div className="space-y-3">
                  {col.links.map((link) => (
                    <a key={link} href="#" className="block text-[14px] text-gray-500 hover:text-gray-900 transition-colors">
                      {link}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-100 pt-6 text-center">
            <p className="text-[13px] text-gray-400">&copy; 2024 MedHistory. Все права защищены.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
