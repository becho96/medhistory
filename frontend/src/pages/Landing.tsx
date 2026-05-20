import { Link } from 'react-router-dom';
import {
  FileSearch, BarChart3, FileCheck,
  HeartPulse, Sparkles, Users,
  Shield, ChevronRight, FileText, ImageIcon, Zap, UserRound, User2, Baby, CheckCircle2,
  X,
} from 'lucide-react';
import GraphVisualization from '../components/Landing/GraphVisualization';

const familyMembers = [
  { name: 'Мама', docs: 23, initial: 'М', bg: 'bg-rose-50', text: 'text-rose-500', border: 'border-rose-100', Icon: UserRound },
  { name: 'Папа', docs: 15, initial: 'П', bg: 'bg-blue-50', text: 'text-blue-500', border: 'border-blue-100', Icon: User2 },
  { name: 'Ребёнок', docs: 8, initial: 'Р', bg: 'bg-amber-50', text: 'text-amber-500', border: 'border-amber-100', Icon: Baby },
];

const Landing = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Hero */}
      <section className="pt-12 sm:pt-16 pb-16 sm:pb-20 px-4 sm:px-10">
        <div className="max-w-[1400px] mx-auto text-center">


          <h1 className="text-[38px] sm:text-[52px] md:text-[64px] leading-[1.05] font-semibold text-gray-900 tracking-tight max-w-[1088px] mx-auto mb-5 sm:mb-6">
            Умное управление{' '}
            <span className="text-emerald-500">медицинской историей</span>
          </h1>
          <p className="text-[16px] sm:text-[18px] leading-[1.6] text-gray-500 max-w-[680px] mx-auto mb-8 sm:mb-10">
            Загружайте документы, отслеживайте динамику показателей и обсуждайте их с AI-ассистентом
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

        </div>
      </section>

      {/* Vertical Features */}
      <section className="px-4 sm:px-10 pb-16 sm:pb-24 bg-gray-50">
        <div className="max-w-[1100px] mx-auto pt-16 sm:pt-24 space-y-20 sm:space-y-32">

          {/* Feature 1 — Smart document processing */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <FileSearch className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">Документы</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Умная обработка медицинских документов
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Загрузите PDF, фото или скан — тип документа, дата и параметры определятся автоматически. Результаты анализов попадают в общую структурированную историю.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 space-y-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-2 flex-1">
                  {[
                    { Icon: FileText, label: 'PDF', bg: 'bg-red-50', color: 'text-red-400' },
                    { Icon: ImageIcon, label: 'Фото', bg: 'bg-blue-50', color: 'text-blue-400' },
                    { Icon: FileSearch, label: 'Скан', bg: 'bg-purple-50', color: 'text-purple-400' },
                  ].map(({ Icon, label, bg, color }) => (
                    <div key={label} className={`flex flex-col items-center gap-1 flex-1 rounded-xl p-2.5 ${bg}`}>
                      <Icon className={`w-4 h-4 ${color}`} />
                      <span className="text-[10px] text-gray-500 font-medium">{label}</span>
                    </div>
                  ))}
                </div>
                <ChevronRight className="w-4 h-4 text-gray-300 shrink-0" />
                <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center shrink-0 shadow-sm shadow-emerald-200">
                  <Zap className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="bg-gray-50 rounded-xl p-3 border border-gray-100">
                <div className="flex items-center gap-2 mb-2.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span className="text-[11px] font-medium text-gray-700">Анализ крови.pdf — распознан</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {[
                    { label: 'Тип', value: 'Общий АК' },
                    { label: 'Дата', value: '12.03.2024' },
                    { label: 'Гемоглобин', value: '135 г/л' },
                    { label: 'Показателей', value: '18' },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-white rounded-lg px-2.5 py-1.5 border border-gray-100">
                      <p className="text-[9px] text-gray-400 uppercase tracking-wide leading-none mb-0.5">{label}</p>
                      <p className="text-[11px] font-medium text-gray-800">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Feature 2 — AI assistants with full context (NEW) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div className="lg:order-2">
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <Sparkles className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">AI с контекстом</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Подключите ChatGPT, Claude или другого AI к полной медицинской истории
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed mb-4">
                Обычно в ChatGPT приходится загружать один документ — и ассистент видит только его. MedHistory отдаёт AI всю структурированную историю: анализы за годы, визиты, диагнозы, динамику показателей.
              </p>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Любой вопрос про здоровье получает ответ с учётом полного контекста, а не одного листочка.
              </p>
            </div>
            <div className="lg:order-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-white rounded-2xl border border-gray-200 p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center">
                    <FileText className="w-3.5 h-3.5 text-gray-400" />
                  </div>
                  <span className="text-[12px] font-medium text-gray-500">ChatGPT без MedHistory</span>
                </div>
                <p className="text-[12px] text-gray-400 leading-relaxed mb-4">AI видит ровно то, что вы прислали в чат</p>
                <div className="space-y-2 mt-auto">
                  <div className="flex items-center gap-2 text-[12px] text-gray-700 bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-100">
                    <CheckCircle2 className="w-3 h-3 text-gray-400 shrink-0" />
                    <span className="truncate">Анализ от 12.03</span>
                  </div>
                  {['Прошлые результаты', 'Визиты к врачам', 'Динамика за годы'].map((label) => (
                    <div key={label} className="flex items-center gap-2 text-[12px] text-gray-400 px-2.5 py-1.5">
                      <X className="w-3 h-3 text-gray-300 shrink-0" />
                      <span className="truncate">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white rounded-2xl border-2 border-emerald-200 p-5 flex flex-col shadow-sm shadow-emerald-100">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500 flex items-center justify-center">
                    <Sparkles className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-[12px] font-semibold text-gray-900">AI + MedHistory</span>
                </div>
                <p className="text-[12px] text-gray-500 leading-relaxed mb-4">AI видит всю вашу медисторию целиком</p>
                <div className="space-y-2 mt-auto">
                  {[
                    { label: '47 документов', value: '5 лет' },
                    { label: '156 показателей', value: 'тренды' },
                    { label: '12 визитов', value: 'история' },
                    { label: 'Диагнозы', value: 'хроники' },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex items-center justify-between gap-2 text-[12px] bg-emerald-50 rounded-lg px-2.5 py-1.5 border border-emerald-100">
                      <div className="flex items-center gap-2 min-w-0">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                        <span className="text-gray-700 font-medium truncate">{label}</span>
                      </div>
                      <span className="text-[10px] text-emerald-600 shrink-0">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Feature 3 — Indicator dynamics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <BarChart3 className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">Динамика</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Видеть тренды показателей за любой период
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Графики по всем анализам с зоной нормы — изменения и отклонения видны сразу, без перелистывания PDF и сравнения цифр вручную.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8">
              <GraphVisualization />
            </div>
          </div>

          {/* Feature 4 — Family profiles */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div className="lg:order-2">
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <Users className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">Семья</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Профили членов семьи в одном аккаунте
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Ведите медицинскую историю детей, родителей и близких отдельными профилями — со своими документами, анализами и динамикой.
              </p>
            </div>
            <div className="lg:order-1 bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 space-y-2.5">
              {familyMembers.map(({ name, docs, bg, text, border, Icon }) => (
                <div key={name} className={`flex items-center gap-3 rounded-xl p-3 border ${border} ${bg}`}>
                  <div className={`w-10 h-10 rounded-full ${bg} border-2 ${border} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-5 h-5 ${text}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-gray-900">{name}</p>
                    <p className="text-[11px] text-gray-500">{docs} документов</p>
                  </div>
                  <div className={`text-[11px] font-medium ${text} px-2 py-0.5 rounded-full bg-white border ${border}`}>
                    {docs}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Feature 5 — Doctor report */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <FileCheck className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">Отчёт</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Отчёт для врача за одну минуту
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Структурированная история, ключевые анализы и динамика — готовый PDF перед любым приёмом, без сборки документов вручную.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8 space-y-3">
              {['Анализ крови — 12.03.2024', 'ЭКГ — 15.01.2024', 'УЗИ — 08.11.2023'].map((item) => (
                <div key={item} className="flex items-center gap-3 bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-100">
                  <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center shrink-0">
                    <FileCheck className="w-4 h-4 text-emerald-500" />
                  </div>
                  <p className="text-[13px] text-gray-700">{item}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Feature 6 — Security */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
            <div className="lg:order-2">
              <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-4">
                <Shield className="w-4 h-4" />
                <span className="text-[12px] font-medium uppercase tracking-wide">Безопасность</span>
              </div>
              <h3 className="text-[26px] sm:text-[34px] font-semibold text-gray-900 tracking-tight leading-[1.15] mb-4">
                Данные под защитой
              </h3>
              <p className="text-[16px] sm:text-[17px] text-gray-500 leading-relaxed">
                Шифрование, соответствие 152-ФЗ, хранение данных на серверах в РФ. Доступ — только у вас.
              </p>
            </div>
            <div className="lg:order-1 bg-white rounded-2xl border border-gray-200 p-8 sm:p-10 flex items-center justify-center">
              <div className="w-20 h-20 bg-emerald-50 rounded-2xl flex items-center justify-center">
                <Shield className="w-10 h-10 text-emerald-500" />
              </div>
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
              { text: 'Загружаю PDF, фото и сканы — всё автоматически распознаётся и складывается в единую медкарту. Больше не ищу анализы по почте и старым папкам.', name: 'Анна М.', role: 'Пользователь', bg: 'bg-emerald-50', text_color: 'text-emerald-600', border: 'border-emerald-100' },
              { text: 'Веду истории всей семьи в одном аккаунте. Перед приёмом за минуту получаю PDF-отчёт с динамикой — не приходится таскать пачку документов.', name: 'Дмитрий К.', role: 'Пользователь', bg: 'bg-blue-50', text_color: 'text-blue-600', border: 'border-blue-100' },
              { text: 'Подключила ChatGPT к своей истории через MedHistory. Теперь спрашиваю про здоровье, и он отвечает с учётом всех моих анализов за годы, а не одного документа.', name: 'Елена С.', role: 'Пользователь', bg: 'bg-amber-50', text_color: 'text-amber-600', border: 'border-amber-100' },
            ].map((review) => (
              <div key={review.name} className="bg-white rounded-2xl border border-gray-200 p-6 text-left">
                <p className="text-[15px] text-gray-600 leading-relaxed mb-6">"{review.text}"</p>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border ${review.bg} ${review.border}`}>
                    <span className={`text-[14px] font-semibold ${review.text_color}`}>{review.name.charAt(0)}</span>
                  </div>
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
              { step: '03', title: 'Структурированная медкарта', desc: 'Графики динамики, отчёты для врача и подключение к AI-ассистентам' },
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
          <div className="bg-gray-900 rounded-3xl p-10 sm:p-16 text-center">
            <h2 className="text-[30px] sm:text-[40px] lg:text-[48px] font-semibold text-white leading-[1.1] tracking-tight mb-8 max-w-[820px] mx-auto">
              Начните управлять медицинской историей уже сегодня
            </h2>
            <div className="flex gap-3 justify-center">
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
        </div>
      </section>

      {/* Footer */}
      <footer className="px-4 sm:px-10 py-8 sm:py-10 border-t border-gray-100">
        <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <HeartPulse className="w-[18px] h-[18px] text-emerald-500" />
            <span className="text-[15px] font-semibold text-gray-900">MedHistory</span>
            <span className="text-[13px] text-gray-400 hidden sm:inline ml-2">— персональная медицинская история</span>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
            <Link to="/legal/privacy" className="text-[13px] text-gray-500 hover:text-gray-900 transition-colors">Политика</Link>
            <Link to="/legal/terms" className="text-[13px] text-gray-500 hover:text-gray-900 transition-colors">Соглашение</Link>
            <Link to="/login" className="text-[13px] text-gray-500 hover:text-gray-900 transition-colors">Войти</Link>
            <Link to="/register" className="text-[13px] text-gray-500 hover:text-gray-900 transition-colors">Регистрация</Link>
            <span className="text-[13px] text-gray-400">&copy; {new Date().getFullYear()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
