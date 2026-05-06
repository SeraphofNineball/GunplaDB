import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, SlidersHorizontal, X } from 'lucide-react'
import { kitsApi } from '../api/client'
import KitCard from '../components/KitCard'
import Pagination from '../components/Pagination'

const GRADES = ['HG', 'HGUC', 'HGCE', 'HGIBO', 'HGBF', 'RG', 'MG', 'PG', 'SD', 'EG', 'RE/100']
const SORT_OPTIONS = [
  { value: 'name', label: 'Name (A–Z)' },
  { value: 'newest', label: 'Recently Added' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'release_date', label: 'Release Date' },
]

export default function HomePage() {
  const [search, setSearch] = useState('')
  const [grade, setGrade] = useState('')
  const [series, setSeries] = useState('')
  const [hasManual, setHasManual] = useState('')
  const [sort, setSort] = useState('name')
  const [page, setPage] = useState(1)
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['kits', { search, grade, series, hasManual, sort, page }],
    queryFn: () => kitsApi.list({
      search: search || undefined,
      grade: grade || undefined,
      series: series || undefined,
      has_manual: hasManual === '' ? undefined : hasManual === 'true',
      sort,
      page,
      page_size: 24,
    }),
    keepPreviousData: true,
  })

  const { data: filters } = useQuery({
    queryKey: ['filters'],
    queryFn: kitsApi.filters,
  })

  const clearFilters = () => {
    setSearch('')
    setGrade('')
    setSeries('')
    setHasManual('')
    setSort('name')
    setPage(1)
  }

  const hasActiveFilters = search || grade || series || hasManual

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search kits, series, franchise…"
            className="w-full bg-gundam-card border border-gundam-border rounded-lg pl-9 pr-4 py-2 text-sm
                       text-white placeholder-gray-500 focus:outline-none focus:border-gundam-red"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={sort}
            onChange={e => { setSort(e.target.value); setPage(1) }}
            className="bg-gundam-card border border-gundam-border rounded-lg px-3 py-2 text-sm text-white
                       focus:outline-none focus:border-gundam-red"
          >
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-colors
              ${showFilters || hasActiveFilters
                ? 'bg-gundam-red border-gundam-red text-white'
                : 'bg-gundam-card border-gundam-border text-gray-300 hover:text-white'}`}
          >
            <SlidersHorizontal size={16} />
            Filters
            {hasActiveFilters && <span className="bg-white text-gundam-red rounded-full w-4 h-4 text-xs flex items-center justify-center font-bold">!</span>}
          </button>
        </div>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="bg-gundam-card border border-gundam-border rounded-xl p-4 mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Grade</label>
            <select
              value={grade}
              onChange={e => { setGrade(e.target.value); setPage(1) }}
              className="w-full bg-gundam-dark border border-gundam-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
            >
              <option value="">All grades</option>
              {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Series</label>
            <select
              value={series}
              onChange={e => { setSeries(e.target.value); setPage(1) }}
              className="w-full bg-gundam-dark border border-gundam-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
            >
              <option value="">All series</option>
              {filters?.series?.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Manual</label>
            <select
              value={hasManual}
              onChange={e => { setHasManual(e.target.value); setPage(1) }}
              className="w-full bg-gundam-dark border border-gundam-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
            >
              <option value="">All kits</option>
              <option value="true">Has manual</option>
              <option value="false">No manual</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <X size={14} /> Clear all
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="bg-gundam-card rounded-xl aspect-square animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-16 text-gray-500">Failed to load kits. Is the backend running?</div>
      ) : data?.total === 0 ? (
        <div className="text-center py-16 text-gray-500">
          No kits found. Try adjusting your filters or{' '}
          <button onClick={clearFilters} className="text-gundam-red hover:underline">clear all filters</button>.
        </div>
      ) : (
        <>
          <div className="text-xs text-gray-500 mb-4">{data?.total?.toLocaleString()} kits</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {data?.items?.map(kit => <KitCard key={kit.id} kit={kit} />)}
          </div>
          <Pagination page={data?.page} pages={data?.pages} onPage={p => { setPage(p); window.scrollTo(0, 0) }} />
        </>
      )}
    </div>
  )
}
