import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null

  const range = []
  const delta = 2
  for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) {
    range.push(i)
  }

  const btn = (label, target, disabled = false) => (
    <button
      key={label}
      onClick={() => !disabled && onPage(target)}
      disabled={disabled}
      className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
        ${target === page
          ? 'bg-gundam-red text-white'
          : disabled
            ? 'text-gray-600 cursor-not-allowed'
            : 'text-gray-300 hover:bg-gundam-card hover:text-white'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="flex items-center justify-center gap-1 mt-8">
      {btn(<ChevronLeft size={16} />, page - 1, page === 1)}
      {range[0] > 1 && <>{btn(1, 1)}{range[0] > 2 && <span className="text-gray-500 px-1">…</span>}</>}
      {range.map(p => btn(p, p))}
      {range[range.length - 1] < pages && (
        <>{range[range.length - 1] < pages - 1 && <span className="text-gray-500 px-1">…</span>}{btn(pages, pages)}</>
      )}
      {btn(<ChevronRight size={16} />, page + 1, page === pages)}
    </div>
  )
}
