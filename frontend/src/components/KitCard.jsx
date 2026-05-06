import { Link } from 'react-router-dom'
import { BookOpen, Star } from 'lucide-react'

const GRADE_COLORS = {
  HG: 'bg-blue-600', HGUC: 'bg-blue-600', HGCE: 'bg-blue-600',
  MG: 'bg-green-600', RG: 'bg-yellow-600', PG: 'bg-purple-600',
  SD: 'bg-pink-600', EG: 'bg-cyan-600',
}

export default function KitCard({ kit }) {
  const gradeColor = GRADE_COLORS[kit.grade] || 'bg-gray-600'
  return (
    <Link
      to={`/kits/${kit.id}`}
      className="group bg-gundam-card border border-gundam-border rounded-xl overflow-hidden
                 hover:border-gundam-red hover:shadow-lg hover:shadow-gundam-red/20 transition-all"
    >
      <div className="relative aspect-square bg-gundam-dark overflow-hidden">
        {kit.thumbnail_url ? (
          <img
            src={kit.thumbnail_url}
            alt={kit.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600">
            <span className="text-4xl">🤖</span>
          </div>
        )}
        {kit.grade && (
          <span className={`absolute top-2 left-2 text-xs font-bold px-2 py-0.5 rounded ${gradeColor}`}>
            {kit.grade}
          </span>
        )}
        {kit.has_manual && (
          <span className="absolute top-2 right-2 bg-gundam-dark/80 rounded p-1" title="Manual available">
            <BookOpen size={12} className="text-green-400" />
          </span>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-semibold text-sm leading-tight line-clamp-2 text-white group-hover:text-gundam-red transition-colors">
          {kit.name}
        </h3>
        <div className="mt-1 flex items-center justify-between text-xs text-gray-400">
          <span className="truncate">{kit.series || kit.franchise || '—'}</span>
          {kit.avg_rating != null && (
            <span className="flex items-center gap-1 shrink-0 ml-2">
              <Star size={10} className="text-yellow-400 fill-yellow-400" />
              {kit.avg_rating.toFixed(1)}
            </span>
          )}
        </div>
        {kit.release_date && (
          <div className="text-xs text-gray-500 mt-0.5">{kit.release_date}</div>
        )}
      </div>
    </Link>
  )
}
