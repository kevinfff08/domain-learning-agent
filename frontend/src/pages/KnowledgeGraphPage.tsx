import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchAssessment, fetchGraph, buildGraph } from '../api/client'
import KnowledgeGraphView from '../components/KnowledgeGraph'
import type { KnowledgeGraph, ConceptNode, SSEEvent } from '../types'

export default function KnowledgeGraphPage() {
  const navigate = useNavigate()
  const [field, setField] = useState<string | null>(null)
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
  const [selectedNode, setSelectedNode] = useState<ConceptNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)
  const [buildLog, setBuildLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  // Load assessment and graph
  useEffect(() => {
    async function load() {
      try {
        const assessment = await fetchAssessment()
        if (!assessment) {
          navigate('/assess')
          return
        }
        setField(assessment.field)

        const g = await fetchGraph(assessment.field)
        setGraph(g)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [navigate])

  const handleBuild = useCallback(() => {
    if (!field) return
    setBuilding(true)
    setBuildLog([])

    buildGraph(
      field,
      (event: SSEEvent) => {
        const msg = (event.data.message as string) ?? JSON.stringify(event.data)
        setBuildLog((prev) => [...prev, `[${event.event}] ${msg}`])
      },
      () => {
        setBuilding(false)
        // Reload graph
        fetchGraph(field).then((g) => setGraph(g))
      },
      (err) => {
        setBuilding(false)
        setError(err.message)
      }
    )
  }, [field])

  const handleNodeClick = useCallback(
    (conceptId: string) => {
      const node = graph?.nodes.find((n) => n.id === conceptId)
      setSelectedNode(node ?? null)
    },
    [graph]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  // No graph yet
  if (!graph) {
    return (
      <div className="max-w-lg mx-auto pt-16 text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">知识图谱</h1>
        <p className="text-sm text-slate-400 mb-6">
          领域: {field}
        </p>
        <p className="text-slate-500 mb-6">
          尚未构建知识图谱，点击下方按钮开始构建
        </p>

        <button
          onClick={handleBuild}
          disabled={building}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {building ? '构建中...' : '构建知识图谱'}
        </button>

        {buildLog.length > 0 && (
          <div className="mt-6 text-left bg-slate-900 rounded-lg p-4 max-h-64 overflow-y-auto">
            {buildLog.map((line, i) => (
              <p key={i} className="text-xs text-green-400 font-mono">
                {line}
              </p>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-3rem)]  flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">知识图谱</h1>
          <p className="text-sm text-slate-400">
            {field} - {graph.nodes.length} 个概念
          </p>
        </div>
        <button
          onClick={handleBuild}
          disabled={building}
          className="text-sm bg-slate-100 text-slate-600 px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
        >
          {building ? '重建中...' : '重新构建'}
        </button>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Graph */}
        <div className="flex-1">
          <KnowledgeGraphView
            nodes={graph.nodes}
            edges={graph.edges}
            onNodeClick={handleNodeClick}
          />
        </div>

        {/* Detail panel */}
        <div className="w-72 flex-shrink-0 bg-white rounded-lg border border-slate-200 p-4 overflow-y-auto">
          {selectedNode ? (
            <div>
              <h3 className="font-semibold text-slate-800 mb-2">
                {selectedNode.name}
              </h3>
              <p className="text-sm text-slate-500 mb-3">
                {selectedNode.description}
              </p>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">难度</span>
                  <span className="text-slate-600">
                    {selectedNode.difficulty}/5
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">状态</span>
                  <StatusBadge status={selectedNode.status} />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">掌握度</span>
                  <span className="text-slate-600">
                    {Math.round(selectedNode.mastery_level * 100)}%
                  </span>
                </div>
              </div>

              {selectedNode.prerequisites.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-slate-400 mb-1">前置知识</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedNode.prerequisites.map((p) => (
                      <span
                        key={p}
                        className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={() => navigate(`/learn/${selectedNode.id}`)}
                className="mt-4 w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                开始学习
              </button>
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center pt-8">
              点击节点查看详情
            </p>
          )}
        </div>
      </div>

      {/* Learning Path */}
      <div className="mt-4 bg-white rounded-lg border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">学习路径</h3>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {graph.nodes.map((node, i) => (
            <div key={node.id} className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => {
                  setSelectedNode(node)
                }}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  node.status === 'completed'
                    ? 'bg-green-50 border-green-300 text-green-700'
                    : node.status === 'in_progress'
                    ? 'bg-yellow-50 border-yellow-300 text-yellow-700'
                    : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                {node.name}
              </button>
              {i < graph.nodes.length - 1 && (
                <span className="text-slate-300 text-xs">→</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-slate-100 text-slate-500',
    in_progress: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-green-100 text-green-700',
  }
  const labels: Record<string, string> = {
    pending: '待学习',
    in_progress: '学习中',
    completed: '已完成',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[status] ?? ''}`}>
      {labels[status] ?? status}
    </span>
  )
}
