import { Link } from 'react-router-dom';
import {
  Baby, Stethoscope, Sparkles, Shield, HeartPulse,
  CheckCircle2, BarChart3, FileText, Gift, ChevronRight,
} from 'lucide-react';

// Mom-focused landing variant (/deti). Reuses the design language of the
// main Landing page but reframes every message around a child's medical
// records — the first-wave acquisition campaign targets parents of 0–7 y.o.

const valueProps = [
  {
    Icon: FileText,
    title: 'Ничего не теряется',
    text: 'Анализы, УЗИ, заключения и прививочный сертификат собраны в одной истории по каждому ребёнку. Не нужно перерывать папки и галерею в телефоне.',
  },
  {
    Icon: Sparkles,
    title: 'Понятно без врача',
    text: 'Сервис распознаёт документ, объясняет, что значат показатели, и подсвечивает отклонения от нормы. Без медицинского образования — всё ясно.',
  },
  {
    Icon: Stethoscope,
    title: 'История по всем врачам',
    text: 'Педиатр, ЛОР, невролог, ортопед — видно всю картину целиком, а не разрозненные бумажки. Перед приёмом всё под рукой.',
  },
];

const steps = [
  { step: '01', title: 'Сфотографируйте документ', desc: 'Анализ, выписку или прививочный сертификат — прямо с телефона' },
  { step: '02', title: 'Сервис всё распознаёт', desc: 'Определит тип, дату и показатели, разложит по датам' },
  { step: '03', title: 'История ребёнка готова', desc: 'Динамика показателей и история по врачам — всегда под рукой' },
];

const childDocs = [
  { name: 'Общий анализ крови', date: '12.03.2025', Icon: BarChart3 },
  { name: 'УЗИ брюшной полости', date: '04.02.2025', Icon: FileText },
  { name: 'Прививка — АКДС', date: '20.01.2025', Icon: Shield },
];

const LandingMoms = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Hero */}
      <section className="pt-12 sm:pt-16 pb-16 sm:pb-20 px-4 sm:px-10">
        <div className="max-w-[1100px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-10 sm:gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 mb-6">
              <Baby className="w-4 h-4" />
              <span className="text-[12px] font-medium uppercase tracking-wide">Для родителей</span>
            </div>

            <h1 className="text-[34px] sm:text-[46px] md:text-[52px] leading-[1.08] font-semibold text-gray-900 tracking-tight mb-5">
              Вся медкарта ребёнка —{' '}
              <span className="text-emerald-500">в вашем телефоне</span>
            </h1>
            <p className="text-[16px] sm:text-[18px] leading-[1.6] text-gray-500 mb-8">
              Сфотографируйте анализ, выписку или прививочный сертификат — MedHistory
              распознает, разложит по датам и покажет динамику. Перед визитом к врачу
              всё под рукой.
            </p>

            <Link
              to="/register"
              className="inline-block bg-emerald-500 text-white px-8 sm:px-10 py-3.5 sm:py-4 rounded-full text-[15px] sm:text-[16px] font-medium hover:bg-emerald-600 transition-colors"
            >
              Загрузить первый документ — бесплатно
            </Link>

            <div className="flex items-center gap-2 mt-5 text-[14px] text-gray-600">
              <Gift className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>Первым 200 пользователям — Pro-доступ навсегда бесплатно</span>
            </div>
          </div>

          {/* Child medical-history card mock */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 rounded-full bg-amber-50 border-2 border-amber-100 flex items-center justify-center shrink-0">
                <Baby className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-gray-900">Медкарта ребёнка</p>
                <p className="text-[12px] text-gray-500">3 документа · обновлено сегодня</p>
              </div>
            </div>
            <div className="space-y-2.5">
              {childDocs.map(({ name, date, Icon }) => (
                <div key={name} className="flex items-center gap-3 bg-gray-50 rounded-xl px-3 py-2.5 border border-gray-100">
                  <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-gray-800 truncate">{name}</p>
                    <p className="text-[11px] text-gray-400">{date}</p>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="px-4 sm:px-10 py-16 sm:py-24 bg-gray-50">
        <div className="max-w-[1100px] mx-auto">
          <h2 className="text-[28px] sm:text-[40px] font-semibold text-gray-900 tracking-tight text-center mb-3">
            Почему родителям это удобно
          </h2>
          <p className="text-[15px] sm:text-[16px] text-gray-500 max-w-[600px] mx-auto text-center mb-10 sm:mb-14">
            Документы детей копятся быстро — MedHistory держит их в порядке за вас
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {valueProps.map(({ Icon, title, text }) => (
              <div key={title} className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-7">
                <div className="w-11 h-11 bg-emerald-50 rounded-xl flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-emerald-500" />
                </div>
                <h3 className="text-[18px] font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-[14px] sm:text-[15px] text-gray-500 leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-4 sm:px-10 py-16 sm:py-20">
        <div className="max-w-[1100px] mx-auto text-center">
          <h2 className="text-[28px] sm:text-[40px] font-semibold text-gray-900 tracking-tight mb-3">
            Как это работает
          </h2>
          <p className="text-[15px] sm:text-[16px] text-gray-500 max-w-[600px] mx-auto mb-10 sm:mb-12">
            Три шага — и история ребёнка собрана
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {steps.map((item) => (
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

      {/* Trust */}
      <section className="px-4 sm:px-10 pb-16 sm:pb-20">
        <div className="max-w-[1100px] mx-auto">
          <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6 sm:p-8 flex items-start gap-4">
            <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shrink-0 border border-emerald-100">
              <Shield className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h3 className="text-[17px] sm:text-[18px] font-semibold text-gray-900 mb-1">
                Данные ребёнка под защитой
              </h3>
              <p className="text-[14px] sm:text-[15px] text-gray-600 leading-relaxed">
                Документы хранятся на серверах в России, доступ — только у вас.
                Сервис соответствует 152-ФЗ, включая обработку данных о состоянии здоровья.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 sm:px-10 pb-16 sm:pb-20">
        <div className="max-w-[1100px] mx-auto">
          <div className="bg-gray-900 rounded-3xl p-10 sm:p-16 text-center">
            <h2 className="text-[28px] sm:text-[38px] lg:text-[44px] font-semibold text-white leading-[1.1] tracking-tight mb-4 max-w-[720px] mx-auto">
              Соберите медкарту ребёнка за один вечер
            </h2>
            <p className="text-[15px] sm:text-[16px] text-gray-300 mb-8 max-w-[520px] mx-auto">
              Бесплатно. Первым 200 пользователям — Pro-доступ навсегда.
            </p>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 bg-emerald-500 text-white px-7 sm:px-8 py-3 sm:py-3.5 rounded-full text-[15px] font-medium hover:bg-emerald-600 transition-colors"
            >
              Создать аккаунт
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-4 sm:px-10 py-8 sm:py-10 border-t border-gray-100">
        <div className="max-w-[1100px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <HeartPulse className="w-[18px] h-[18px] text-emerald-500" />
            <span className="text-[15px] font-semibold text-gray-900">MedHistory</span>
            <span className="text-[13px] text-gray-400 hidden sm:inline ml-2">— медицинская история семьи</span>
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

export default LandingMoms;
