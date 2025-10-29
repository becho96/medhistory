import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

// Пример данных гемоглобина за 6 месяцев
const hemoglobinData = [
  { date: 'Янв', value: 110, normal_min: 120, normal_max: 160 },
  { date: 'Фев', value: 115, normal_min: 120, normal_max: 160 },
  { date: 'Мар', value: 122, normal_min: 120, normal_max: 160 },
  { date: 'Апр', value: 128, normal_min: 120, normal_max: 160 },
  { date: 'Май', value: 132, normal_min: 120, normal_max: 160 },
  { date: 'Июн', value: 135, normal_min: 120, normal_max: 160 },
];

const GraphVisualization = () => {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Динамика гемоглобина</h3>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={hemoglobinData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          
          {/* Зона нормы */}
          <defs>
            <linearGradient id="normalZone" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#10B981" stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          
          <XAxis 
            dataKey="date" 
            stroke="#6B7280"
            style={{ fontSize: '14px' }}
          />
          <YAxis 
            stroke="#6B7280"
            style={{ fontSize: '14px' }}
            domain={[100, 170]}
            label={{ value: 'г/л', angle: -90, position: 'insideLeft', style: { fontSize: '14px' } }}
          />
          
          {/* Линии нормы */}
          <ReferenceLine 
            y={120} 
            stroke="#10B981" 
            strokeDasharray="3 3" 
            label={{ value: 'Нижняя норма', position: 'right', fill: '#10B981', fontSize: 12 }}
          />
          <ReferenceLine 
            y={160} 
            stroke="#10B981" 
            strokeDasharray="3 3"
            label={{ value: 'Верхняя норма', position: 'right', fill: '#10B981', fontSize: 12 }}
          />
          
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'white', 
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            formatter={(value: number) => [`${value} г/л`, 'Гемоглобин']}
          />
          
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke="#2563EB" 
            strokeWidth={3}
            dot={{ fill: '#2563EB', r: 6 }}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-600 rounded-full"></div>
          <span className="text-gray-600">Ваш показатель</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-600">Зона нормы</span>
        </div>
      </div>

      <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
        <p className="text-sm text-green-800">
          📈 Показатель вырос с 110 до 135 г/л за период наблюдения
        </p>
      </div>
    </div>
  );
};

export default GraphVisualization;

