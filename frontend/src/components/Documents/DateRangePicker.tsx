interface DateRangePickerProps {
  label: string
  fromValue: string
  toValue: string
  onFromChange: (value: string) => void
  onToChange: (value: string) => void
}

export default function DateRangePicker({
  label,
  fromValue,
  toValue,
  onFromChange,
  onToChange
}: DateRangePickerProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={fromValue}
          onChange={(e) => onFromChange(e.target.value)}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
        />
        <span className="text-gray-500 text-sm flex-shrink-0">—</span>
        <input
          type="date"
          value={toValue}
          onChange={(e) => onToChange(e.target.value)}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
        />
      </div>
    </div>
  )
}

