import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchAssessment, exportMaterials } from '../api/client'

const formatOptions = [
  {
    id: 'obsidian',
    label: 'Obsidian',
    desc: '导出为 Obsidian Vault 兼容的 Markdown 文件',
  },
  {
    id: 'anki',
    label: 'Anki',
    desc: '导出闪卡为 Anki 卡牌包',
  },
  {
    id: 'html',
    label: 'HTML',
    desc: '导出为独立的 HTML 网页',
  },
  {
    id: 'pdf',
    label: 'PDF',
    desc: '导出为 PDF 文档',
  },
]

export default function ExportPage() {
  const navigate = useNavigate()
  const [field, setField] = useState<string | null>(null)
  const [selectedFormats, setSelectedFormats] = useState<Set<string>>(new Set())
  const [exporting, setExporting] = useState(false)
  const [results, setResults] = useState<Record<string, string> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAssessment().then((a) => {
      if (!a) {
        navigate('/assess')
        return
      }
      setField(a.field)
    })
  }, [navigate])

  const toggleFormat = (id: string) => {
    setSelectedFormats((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleExport = async () => {
    if (!field || selectedFormats.size === 0) return
    setExporting(true)
    setError(null)
    setResults(null)

    try {
      const res = await exportMaterials(field, Array.from(selectedFormats))
      setResults(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-2">导出学习资料</h1>
      <p className="text-sm text-slate-400 mb-8">
        将学习内容导出为多种格式{field && ` - 领域: ${field}`}
      </p>

      {/* Format selection */}
      <div className="space-y-3 mb-8">
        {formatOptions.map((fmt) => (
          <label
            key={fmt.id}
            className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
              selectedFormats.has(fmt.id)
                ? 'border-blue-400 bg-blue-50'
                : 'border-slate-200 bg-white hover:bg-slate-50'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedFormats.has(fmt.id)}
              onChange={() => toggleFormat(fmt.id)}
              className="mt-0.5 text-blue-600 rounded"
            />
            <div>
              <span className="text-sm font-medium text-slate-700">
                {fmt.label}
              </span>
              <p className="text-xs text-slate-400 mt-0.5">{fmt.desc}</p>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={handleExport}
        disabled={exporting || selectedFormats.size === 0}
        className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {exporting ? '导出中...' : '开始导出'}
      </button>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {results && (
        <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-green-700 mb-3">
            导出完成
          </h3>
          <div className="space-y-2">
            {Object.entries(results).map(([format, path]) => (
              <div
                key={format}
                className="flex items-center justify-between bg-white rounded-lg p-3 border border-green-100"
              >
                <div>
                  <span className="text-sm font-medium text-slate-700">
                    {format.toUpperCase()}
                  </span>
                </div>
                <span className="text-xs text-slate-500 font-mono truncate max-w-xs">
                  {path}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
