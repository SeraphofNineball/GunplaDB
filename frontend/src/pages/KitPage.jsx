import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Upload, Trash2, Star, ExternalLink, BookOpen } from 'lucide-react'
import { kitsApi, manualsApi } from '../api/client'
import ManualViewer from '../components/ManualViewer'

const GRADE_COLORS = {
  HG: 'bg-blue-600', HGUC: 'bg-blue-600', HGCE: 'bg-blue-600',
  MG: 'bg-green-600', RG: 'bg-yellow-600', PG: 'bg-purple-600',
  SD: 'bg-pink-600', EG: 'bg-cyan-600',
}

function Stat({ label, value }) {
  if (!value) return null
  return (
    <div className="bg-gundam-dark rounded-lg p-3">
      <div className="text-xs text-gray-400 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  )
}

export default function KitPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [activeImg, setActiveImg] = useState(0)

  const { data: kit, isLoading, isError } = useQuery({
    queryKey: ['kit', id],
    queryFn: () => kitsApi.get(id),
  })

  const uploadManual = useMutation({
    mutationFn: (file) => manualsApi.upload(id, file),
    onSuccess: () => qc.invalidateQueries(['kit', id]),
  })

  const deleteManual = useMutation({
    mutationFn: () => manualsApi.delete(id),
    onSuccess: () => qc.invalidateQueries(['kit', id]),
  })

  const deleteKit = useMutation({
    mutationFn: () => kitsApi.delete(id),
    onSuccess: () => navigate('/'),
  })

  const uploadImage = useMutation({
    mutationFn: (file) => kitsApi.uploadImage(id, file),
    onSuccess: () => qc.invalidateQueries(['kit', id]),
  })

  if (isLoading) return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gundam-card rounded w-1/3" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="aspect-square bg-gundam-card rounded-xl" />
          <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 bg-gundam-card rounded" />)}</div>
        </div>
      </div>
    </div>
  )

  if (isError || !kit) return (
    <div className="text-center py-16 text-gray-500">Kit not found.</div>
  )

  const gradeColor = GRADE_COLORS[kit.grade] || 'bg-gray-600'
  const currentImg = kit.images?.[activeImg]

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft size={16} /> Back to all kits
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left: images */}
        <div>
          <div className="aspect-square bg-gundam-card rounded-xl overflow-hidden border border-gundam-border">
            {currentImg ? (
              <img src={currentImg.url} alt={kit.name} className="w-full h-full object-contain p-4" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-6xl">🤖</div>
            )}
          </div>

          {/* Thumbnails */}
          {kit.images.length > 1 && (
            <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
              {kit.images.map((img, i) => (
                <button
                  key={img.id}
                  onClick={() => setActiveImg(i)}
                  className={`w-16 h-16 shrink-0 rounded-lg overflow-hidden border-2 transition-colors
                    ${i === activeImg ? 'border-gundam-red' : 'border-gundam-border hover:border-gray-400'}`}
                >
                  <img src={img.url} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}

          {/* Upload image */}
          <label className="mt-3 flex items-center gap-2 text-xs text-gray-400 hover:text-white cursor-pointer transition-colors">
            <Upload size={14} />
            Add image
            <input type="file" accept="image/*" className="hidden" onChange={e => {
              if (e.target.files?.[0]) uploadImage.mutate(e.target.files[0])
            }} />
          </label>
        </div>

        {/* Right: info */}
        <div>
          <div className="flex items-start gap-3 mb-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white leading-tight">{kit.name}</h1>
              {kit.franchise && <p className="text-gray-400 text-sm mt-1">{kit.franchise}</p>}
            </div>
            {kit.grade && (
              <span className={`text-sm font-bold px-3 py-1 rounded-full shrink-0 ${gradeColor}`}>{kit.grade}</span>
            )}
          </div>

          {kit.avg_rating != null && (
            <div className="flex items-center gap-2 mb-4">
              <div className="flex items-center gap-1">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-4 h-1.5 rounded-full ${i < Math.round(kit.avg_rating) ? 'bg-yellow-400' : 'bg-gray-600'}`}
                  />
                ))}
              </div>
              <span className="text-sm text-yellow-400 font-semibold">{kit.avg_rating.toFixed(1)}/10</span>
              {kit.total_owners && <span className="text-xs text-gray-500">({kit.total_owners.toLocaleString()} owners)</span>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 mb-4">
            <Stat label="Series" value={kit.series} />
            <Stat label="Scale" value={kit.scale} />
            <Stat label="Brand" value={kit.brand} />
            <Stat label="Release" value={kit.release_date} />
          </div>

          {kit.description && (
            <p className="text-sm text-gray-300 leading-relaxed mb-4">{kit.description}</p>
          )}

          <div className="flex gap-2 flex-wrap">
            {kit.source_url && (
              <a
                href={kit.source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-xs px-3 py-1.5 border border-gundam-border rounded-lg text-gray-400 hover:text-white hover:border-gray-400 transition-colors"
              >
                <ExternalLink size={12} /> GunplaCentral
              </a>
            )}

            {/* Upload manual */}
            <label className="flex items-center gap-1 text-xs px-3 py-1.5 border border-gundam-border rounded-lg text-gray-400 hover:text-white hover:border-gray-400 transition-colors cursor-pointer">
              <Upload size={12} /> Upload Manual (PDF)
              <input type="file" accept=".pdf" className="hidden" onChange={e => {
                if (e.target.files?.[0]) uploadManual.mutate(e.target.files[0])
              }} />
            </label>

            {kit.manual && (
              <button
                onClick={() => { if (confirm('Remove manual?')) deleteManual.mutate() }}
                className="flex items-center gap-1 text-xs px-3 py-1.5 border border-red-800 rounded-lg text-red-400 hover:text-red-300 transition-colors"
              >
                <Trash2 size={12} /> Remove Manual
              </button>
            )}

            {kit.manually_added && (
              <button
                onClick={() => { if (confirm(`Delete "${kit.name}"?`)) deleteKit.mutate() }}
                className="flex items-center gap-1 text-xs px-3 py-1.5 border border-red-800 rounded-lg text-red-400 hover:text-red-300 transition-colors ml-auto"
              >
                <Trash2 size={12} /> Delete Kit
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Manual viewer */}
      <ManualViewer manual={kit.manual} />
    </div>
  )
}
