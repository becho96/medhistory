import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea } from 'recharts';

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
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[14px] font-medium text-gray-900">Динамика гемоглобина</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full" />
            <span className="text-[12px] text-gray-500">Ваш показатель</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-3 w-8 rounded-sm bg-emerald-100 border border-emerald-300 border-dashed" />
            <span className="text-[12px] text-gray-500">Норма</span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={hemoglobinData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />

          <XAxis
            dataKey="date"
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
            domain={[100, 170]}
            tickLine={false}
            axisLine={false}
          />

          <ReferenceArea y1={120} y2={160} fill="#d1fae5" fillOpacity={0.35} />
          <ReferenceLine y={120} stroke="#6ee7b7" strokeDasharray="4 4" label={{ value: 'норма', position: 'insideBottomLeft', fontSize: 10, fill: '#6ee7b7' }} />
          <ReferenceLine y={160} stroke="#6ee7b7" strokeDasharray="4 4" />

          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '13px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
            }}
            formatter={(value: number) => [`${value} г/л`, 'Гемоглобин']}
          />

          <Line
            type="monotone"
            dataKey="value"
            stroke="#10b981"
            strokeWidth={2.5}
            dot={{ fill: '#10b981', r: 4, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: '#10b981' }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-3 bg-emerald-50 rounded-lg px-3 py-2">
        <p className="text-[13px] text-emerald-700">
          Показатель вырос с 110 до 135 г/л за период наблюдения
        </p>
      </div>
    </div>
  );
};

export default GraphVisualization;
