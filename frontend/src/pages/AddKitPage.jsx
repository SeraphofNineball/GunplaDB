import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, Save } from 'lucide-react'
import { kitsApi } from '../api/client'

function Field({ label, name, value, onChange, type = 'text', required = false }) {
  return (
    <div>
      <label className="text-xs text-gray-400 block mb-1">{label}{required && ' *'}</label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        className="w-full bg-gundam-dark border border-gundam-border rounded-lg px-3 py-2 text-sm text-white
                   placeholder-gray-600 focus:outline-none focus:border-gundam-red"
      />
    </div>
  )
}

export default function AddKitPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '', franchise: '', series: '', grade: '',
    scale: '', release_date: '', brand: '', description: '',
  })

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const create = useMutation({
    mutationFn: () => kitsApi.create(form),
    onSuccess: (kit) => navigate(`/kits/${kit.id}`),
  })

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft size={16} /> Back
      </Link>

      <h1 className="text-2xl font-bold mb-6">Add Kit Manually</h1>

      <form onSubmit={e => { e.preventDefault(); create.mutate() }} className="space-y-4">
        <Field label="Kit Name" name="name" value={form.name} onChange={handleChange} required />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Franchise" name="franchise" value={form.franchise} onChange={handleChange} />
          <Field label="Series" name="series" value={form.series} onChange={handleChange} />
          <Field label="Grade (HG, MG, RG…)" name="grade" value={form.grade} onChange={handleChange} />
          <Field label="Scale (1/144, 1/100…)" name="scale" value={form.scale} onChange={handleChange} />
          <Field label="Brand" name="brand" value={form.brand} onChange={handleChange} />
          <Field label="Release Date" name="release_date" value={form.release_date} onChange={handleChange} />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            rows={3}
            className="w-full bg-gundam-dark border border-gundam-border rounded-lg px-3 py-2 text-sm text-white
                       placeholder-gray-600 focus:outline-none focus:border-gundam-red resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={create.isPending}
          className="flex items-center gap-2 px-6 py-2.5 bg-gundam-red hover:bg-red-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
        >
          <Save size={16} />
          {create.isPending ? 'Saving…' : 'Save Kit'}
        </button>

        {create.isError && (
          <div className="text-red-400 text-sm">{create.error?.response?.data?.detail || 'Failed to create kit.'}</div>
        )}
      </form>
    </div>
  )
}
