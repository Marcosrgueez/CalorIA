export function Skeleton({ className = '', ...props }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-gray-200 ${className}`}
      {...props}
    />
  )
}

export function MealCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
      </div>
    </div>
  )
}

export function DietPageSkeleton() {
  return (
    <div className="space-y-4 px-4 pt-4">
      <Skeleton className="h-24 w-full rounded-2xl" />
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <MealCardSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}
