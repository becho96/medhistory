import { Heart, Activity, Pill, TestTube, Stethoscope } from 'lucide-react';

const timelineData = [
  {
    id: 1,
    date: '15 Янв 2024',
    type: 'Анализ крови',
    specialty: 'Гематология',
    icon: TestTube,
    color: 'bg-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  {
    id: 2,
    date: '03 Фев 2024',
    type: 'Прием врача',
    specialty: 'Кардиолог',
    icon: Heart,
    color: 'bg-pink-500',
    bgColor: 'bg-pink-50',
    borderColor: 'border-pink-200',
  },
  {
    id: 3,
    date: '20 Мар 2024',
    type: 'УЗИ',
    specialty: 'Исследование',
    icon: Activity,
    color: 'bg-purple-500',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  {
    id: 4,
    date: '12 Апр 2024',
    type: 'Анализ крови',
    specialty: 'Гематология',
    icon: TestTube,
    color: 'bg-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  {
    id: 5,
    date: '28 Май 2024',
    type: 'Назначения',
    specialty: 'Терапевт',
    icon: Pill,
    color: 'bg-blue-500',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  {
    id: 6,
    date: '15 Июн 2024',
    type: 'Прием врача',
    specialty: 'Гастроэнтеролог',
    icon: Stethoscope,
    color: 'bg-green-500',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
];

const TimelineVisualization = () => {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Интерактивный таймлайн</h3>
        <p className="text-sm text-gray-500 mt-1">
          Все документы в хронологическом порядке
        </p>
      </div>

      {/* Фильтры */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors">
          Анализы
        </button>
        <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors">
          Приемы врачей
        </button>
        <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors">
          Исследования
        </button>
        <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm hover:bg-gray-200 transition-colors">
          Функциональная диагностика
        </button>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Horizontal line */}
        <div className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-blue-200 via-purple-200 to-green-200 top-1/2 transform -translate-y-1/2"></div>

        {/* Timeline items */}
        <div className="relative grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {timelineData.map((item, index) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                className="relative group cursor-pointer"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Connector dot */}
                <div className="flex justify-center mb-3">
                  <div className={`w-4 h-4 rounded-full ${item.color} border-4 border-white shadow-md group-hover:scale-125 transition-transform duration-200`}></div>
                </div>

                {/* Card */}
                <div className={`${item.bgColor} border-2 ${item.borderColor} rounded-lg p-3 hover:shadow-lg transition-all duration-200 hover:-translate-y-1`}>
                  <div className="flex items-center justify-center mb-2">
                    <div className={`${item.color} w-10 h-10 rounded-full flex items-center justify-center`}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                  </div>
                  
                  <p className="text-xs font-semibold text-gray-900 text-center mb-1">
                    {item.type}
                  </p>
                  <p className="text-xs text-gray-600 text-center mb-1">
                    {item.specialty}
                  </p>
                  <p className="text-xs text-gray-500 text-center font-medium">
                    {item.date}
                  </p>
                </div>

                {/* Hover tooltip */}
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                  <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
                    Нажмите для просмотра
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Controls */}
      <div className="mt-6 flex justify-center gap-3">
        <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium">
          ← Назад
        </button>
        <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium">
          2024
        </button>
        <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium">
          Вперед →
        </button>
      </div>
    </div>
  );
};

export default TimelineVisualization;

