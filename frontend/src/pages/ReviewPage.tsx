import { useEffect, useState } from 'react'
import { fetchDueCards, reviewCard, exportAnki, fetchAssessment } from '../api/client'
import type { FlashCard as FlashCardType } from '../types'
import FlashCard from '../components/FlashCard'

export default function ReviewPage() {
  const [cards, setCards] = useState<FlashCardType[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [field, setField] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const assessment = await fetchAssessment()
        if (assessment) setField(assessment.target_field)

        const due = await fetchDueCards()
        setCards(due)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleRate = async (rating: number) => {
    const card = cards[currentIndex]
    if (!card) return

    try {
      await reviewCard(card.id, rating)
      setCurrentIndex((prev) => prev + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交评分失败')
    }
  }

  const handleExportAnki = async () => {
    if (!field) return
    try {
      await exportAnki(field)
    } catch (err) {
      setError(err instanceof Error ? err.message : '导出失败')
    }
  }

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

  const allDone = currentIndex >= cards.length

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">间隔复习</h1>
          <p className="text-sm text-slate-400 mt-1">
            基于 SM-2 算法的智能复习系统
          </p>
        </div>
        {field && (
          <button
            onClick={handleExportAnki}
            className="text-sm bg-slate-100 text-slate-600 px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors"
          >
            导出 Anki
          </button>
        )}
      </div>

      {cards.length === 0 || allDone ? (
        <div className="text-center pt-16">
          <p className="text-4xl mb-4">🎉</p>
          <h2 className="text-xl font-bold text-slate-700 mb-2">
            {cards.length === 0 ? '没有待复习的卡片' : '全部复习完成!'}
          </h2>
          <p className="text-sm text-slate-400">
            {cards.length === 0
              ? '当前没有到期的闪卡，学习新概念后会自动生成'
              : `本次共复习了 ${cards.length} 张卡片`}
          </p>
        </div>
      ) : (
        <div>
          {/* Counter */}
          <div className="text-center mb-6">
            <span className="text-sm text-slate-400">
              卡片 {currentIndex + 1} / {cards.length}
            </span>
            <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all"
                style={{
                  width: `${((currentIndex + 1) / cards.length) * 100}%`,
                }}
              />
            </div>
          </div>

          <FlashCard card={cards[currentIndex]} onRate={handleRate} />
        </div>
      )}
    </div>
  )
}
