import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Play, RefreshCw, Clock, CheckCircle, XCircle, Loader,
  Plus, BookOpen, Pause, PauseCircle, Ban, Square, Trash2, RotateCcw,
} from 'lucide-react'
import { scrapeApi } from '../api/client'

const STATUS_ICON = {
  pending:   <Clock size={14} className="text-yellow-400" />,
  running:   <Loader size={14} className="text-blue-400 animate-spin" />,
  paused:    <PauseCircle size={14} className="text-orange-400" />,
  completed: <CheckCircle size={14} className="text-green-400" />,
  failed:    <XCircle size={14} className="text-red-400" />,
  cancelled: <Ban size={14} className="text-gray-500" />,
}

function ActionBtn({ title, onClick, disabled, icon, color = 'text-gray-300' }) {
  return (
    <button
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`p-1 rounded hover:bg-white/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${color}`}
    >
      {icon}
    </button>
  )
}

function JobRow({ job, pendingAction, onCancel, onPause, onResume, onDelete }) {
  const busy = !!pendingAction
  const duration = job.completed_at && job.started_at
    ? Math.round((new Date(job.completed_at) - new Date(job.started_at)) / 1000)
    : null

  return (
    <tr className="border-t border-gundam-border text-sm">
      <td className="py-3 pr-4">
        <span className="flex items-center gap-2">
          {STATUS_ICON[job.status] ?? null}
          <span className="capitalize">{job.status}</span>
        </span>
      </td>
      <td className="py-3 pr-4 text-gray-400 capitalize">{job.job_type.replace('_', ' ')}</td>
      <td className="py-3 pr-4 text-gray-400">
        {job.items_processed}/{job.items_found || '?'}
        {job.items_failed > 0 && <span className="text-red-400 ml-1">({job.items_failed} failed)</span>}
      </td>
      <td className="py-3 pr-4 text-gray-400 text-xs">
        {duration != null ? `${duration}s` : '—'}
      </td>
      <td className="py-3 pr-4 text-gray-500 text-xs">
        {new Date(job.created_at).toLocaleString()}
      </td>
      <td className="py-3 pr-4 text-red-400 text-xs max-w-xs truncate" title={job.error_message ?? ''}>
        {job.error_message ?? ''}
      </td>
      <td className="py-3">
        <div className="flex items-center gap-0.5">
          {job.status === 'running' && (
            <ActionBtn title="Pause" onClick={onPause} disabled={busy} color="text-orange-400" icon={<Pause size={13} />} />
          )}
          {job.status === 'paused' && (
            <ActionBtn title="Resume" onClick={onResume} disabled={busy} color="text-green-400" icon={<Play size={13} />} />
          )}
          {(job.status === 'failed' || job.status === 'cancelled') && job.job_type !== 'fetch_manual' && (
            <ActionBtn title="Retry" onClick={onResume} disabled={busy} color="text-blue-400" icon={<RotateCcw size={13} />} />
          )}
          {['pending', 'running', 'paused'].includes(job.status) && (
            <ActionBtn title="Cancel" onClick={onCancel} disabled={busy} color="text-red-400" icon={<Square size={13} />} />
          )}
          {['completed', 'failed', 'cancelled'].includes(job.status) && (
            <ActionBtn title="Delete" onClick={onDelete} disabled={busy} color="text-gray-500" icon={<Trash2 size={13} />} />
          )}
          {pendingAction && <Loader size={12} className="animate-spin text-gray-400 ml-1" />}
        </div>
      </td>
    </tr>
  )
}

export default function AdminPage() {
  const qc = useQueryClient()
  const [maxKits, setMaxKits] = useState('')
  const [bandaiId, setBandaiId] = useState('')
  const [kitId, setKitId] = useState('')
  const [pendingAction, setPendingAction] = useState(null) // { id, type }

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['scrape-jobs'],
    queryFn: () => scrapeApi.listJobs(50),
    refetchInterval: 5000,
  })

  const invalidate = () => qc.invalidateQueries(['scrape-jobs'])
  const trackAction = (id, type) => setPendingAction({ id, type })
  const clearAction = () => { setPendingAction(null); invalidate() }

  const startFull = useMutation({
    mutationFn: () => scrapeApi.startFull(maxKits ? parseInt(maxKits) : undefined),
    onSuccess: invalidate,
  })
  const startUpdate = useMutation({
    mutationFn: scrapeApi.startUpdate,
    onSuccess: invalidate,
  })
  const fetchManual = useMutation({
    mutationFn: () => scrapeApi.fetchManual(parseInt(kitId), parseInt(bandaiId)),
    onSuccess: () => { invalidate(); setBandaiId(''); setKitId('') },
  })
  const cancelJob = useMutation({
    mutationFn: (id) => { trackAction(id, 'cancel'); return scrapeApi.cancelJob(id) },
    onSettled: clearAction,
  })
  const pauseJob = useMutation({
    mutationFn: (id) => { trackAction(id, 'pause'); return scrapeApi.pauseJob(id) },
    onSettled: clearAction,
  })
  const resumeJob = useMutation({
    mutationFn: (id) => { trackAction(id, 'resume'); return scrapeApi.resumeJob(id) },
    onSettled: clearAction,
  })
  const deleteJob = useMutation({
    mutationFn: (id) => { trackAction(id, 'delete'); return scrapeApi.deleteJob(id) },
    onSettled: clearAction,
  })

  const activeJobs = jobs?.filter(j => ['pending', 'running', 'paused'].includes(j.status)).length ?? 0

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <Link
          to="/kits/new"
          className="flex items-center gap-2 px-4 py-2 bg-gundam-red hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus size={16} /> Add Kit
        </Link>
      </div>

      {/* Scrape actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-gundam-card border border-gundam-border rounded-xl p-5">
          <h2 className="font-semibold mb-1 flex items-center gap-2"><Play size={16} className="text-gundam-red" /> Full Scrape</h2>
          <p className="text-xs text-gray-400 mb-4">Scrape all Gunpla kits from GunplaCentral (takes a long time).</p>
          <input
            type="number"
            placeholder="Max kit ID (optional)"
            value={maxKits}
            onChange={e => setMaxKits(e.target.value)}
            className="w-full bg-gundam-dark border border-gundam-border rounded px-3 py-1.5 text-sm text-white mb-3 focus:outline-none focus:border-gundam-red"
          />
          <button
            onClick={() => startFull.mutate()}
            disabled={startFull.isPending || activeJobs > 0}
            className="w-full py-2 bg-gundam-red hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {startFull.isPending ? 'Starting…' : 'Start Full Scrape'}
          </button>
        </div>

        <div className="bg-gundam-card border border-gundam-border rounded-xl p-5">
          <h2 className="font-semibold mb-1 flex items-center gap-2"><RefreshCw size={16} className="text-blue-400" /> Update</h2>
          <p className="text-xs text-gray-400 mb-4">Fetch only kits added since the last scrape.</p>
          <button
            onClick={() => startUpdate.mutate()}
            disabled={startUpdate.isPending || activeJobs > 0}
            className="w-full py-2 bg-blue-700 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 mt-auto"
          >
            {startUpdate.isPending ? 'Starting…' : 'Check for New Kits'}
          </button>
        </div>

        <div className="bg-gundam-card border border-gundam-border rounded-xl p-5">
          <h2 className="font-semibold mb-1 flex items-center gap-2"><BookOpen size={16} className="text-green-400" /> Fetch Manual</h2>
          <p className="text-xs text-gray-400 mb-3">Pull a manual from Bandai Hobby by ID.</p>
          <input
            type="number"
            placeholder="Kit DB ID"
            value={kitId}
            onChange={e => setKitId(e.target.value)}
            className="w-full bg-gundam-dark border border-gundam-border rounded px-3 py-1.5 text-sm text-white mb-2 focus:outline-none focus:border-gundam-red"
          />
          <input
            type="number"
            placeholder="Bandai manual ID (e.g. 3038)"
            value={bandaiId}
            onChange={e => setBandaiId(e.target.value)}
            className="w-full bg-gundam-dark border border-gundam-border rounded px-3 py-1.5 text-sm text-white mb-3 focus:outline-none focus:border-gundam-red"
          />
          <button
            onClick={() => fetchManual.mutate()}
            disabled={fetchManual.isPending || !bandaiId || !kitId}
            className="w-full py-2 bg-green-700 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {fetchManual.isPending ? 'Fetching…' : 'Fetch Manual'}
          </button>
        </div>
      </div>

      {/* Job log */}
      <div className="bg-gundam-card border border-gundam-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Job Log</h2>
          {activeJobs > 0 && (
            <span className="text-xs text-blue-400 flex items-center gap-1">
              <Loader size={12} className="animate-spin" /> {activeJobs} active
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="text-gray-500 text-sm">Loading…</div>
        ) : !jobs?.length ? (
          <div className="text-gray-500 text-sm">No jobs yet. Run a scrape to get started.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500">
                  <th className="text-left pb-2 pr-4">Status</th>
                  <th className="text-left pb-2 pr-4">Type</th>
                  <th className="text-left pb-2 pr-4">Progress</th>
                  <th className="text-left pb-2 pr-4">Duration</th>
                  <th className="text-left pb-2 pr-4">Started</th>
                  <th className="text-left pb-2 pr-4">Error</th>
                  <th className="text-left pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => (
                  <JobRow
                    key={job.id}
                    job={job}
                    pendingAction={pendingAction?.id === job.id ? pendingAction.type : null}
                    onCancel={() => cancelJob.mutate(job.id)}
                    onPause={() => pauseJob.mutate(job.id)}
                    onResume={() => resumeJob.mutate(job.id)}
                    onDelete={() => deleteJob.mutate(job.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
