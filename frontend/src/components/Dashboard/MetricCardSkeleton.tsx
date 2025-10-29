export default function MetricCardSkeleton() {
  return (
    <div className="medical-card animate-pulse">
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-xl bg-gray-200"></div>
        <div className="w-12 h-4 bg-gray-200 rounded"></div>
      </div>
      <div className="space-y-2">
        <div className="h-4 w-24 bg-gray-200 rounded"></div>
        <div className="h-8 w-16 bg-gray-200 rounded"></div>
      </div>
    </div>
  )
}

