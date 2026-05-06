import { useState } from 'react'
import { ExternalLink, BookOpen } from 'lucide-react'

export default function ManualViewer({ manual }) {
  const [open, setOpen] = useState(false)

  if (!manual?.url) return null

  return (
    <div className="mt-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <BookOpen size={18} className="text-green-400" />
        Instruction Manual
      </h2>

      <div className="bg-gundam-card border border-gundam-border rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm text-gray-400">
            {manual.page_count ? `${manual.page_count} pages` : 'PDF Manual'}
            {manual.bandai_manual_id && (
              <span className="ml-2 text-gray-500">· Bandai ID #{manual.bandai_manual_id}</span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setOpen(!open)}
              className="text-xs px-3 py-1.5 bg-gundam-border hover:bg-gundam-blue text-white rounded transition-colors"
            >
              {open ? 'Hide' : 'View'} Manual
            </button>
            <a
              href={manual.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs px-3 py-1.5 bg-gundam-red hover:bg-red-700 text-white rounded transition-colors flex items-center gap-1"
            >
              <ExternalLink size={12} />
              Download
            </a>
          </div>
        </div>

        {open && (
          <div className="border border-gundam-border rounded-lg overflow-hidden" style={{ height: '75vh' }}>
            <iframe
              src={`${manual.url}#toolbar=1`}
              className="w-full h-full"
              title="Instruction Manual"
            />
          </div>
        )}
      </div>
    </div>
  )
}
