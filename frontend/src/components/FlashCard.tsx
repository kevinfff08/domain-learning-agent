import { useState } from 'react'
import type { FlashCard as FlashCardType } from '../types'

interface Props {
  card: FlashCardType
  onRate: (rating: number) => void
}

const ratingButtons = [
  { rating: 0, label: '忘记', color: 'bg-red-500 hover:bg-red-600' },
  { rating: 3, label: '困难', color: 'bg-yellow-500 hover:bg-yellow-600' },
  { rating: 4, label: '良好', color: 'bg-blue-500 hover:bg-blue-600' },
  { rating: 5, label: '简单', color: 'bg-green-500 hover:bg-green-600' },
]

export default function FlashCard({ card, onRate }: Props) {
  const [flipped, setFlipped] = useState(false)

  return (
    <div className="max-w-lg mx-auto">
      {/* Card */}
      <div
        className="relative cursor-pointer mb-6"
        style={{ perspective: '1000px' }}
        onClick={() => setFlipped(!flipped)}
      >
        <div
          className="relative w-full transition-transform duration-500"
          style={{
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
            minHeight: '220px',
          }}
        >
          {/* Front */}
          <div
            className="absolute inset-0 rounded-xl bg-white border-2 border-slate-200 shadow-md p-6 flex flex-col items-center justify-center"
            style={{ backfaceVisibility: 'hidden' }}
          >
            <p className="text-xs text-slate-400 mb-3">点击翻转</p>
            <p className="text-center text-slate-800 leading-relaxed whitespace-pre-wrap">
              {card.front}
            </p>
          </div>

          {/* Back */}
          <div
            className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 shadow-md p-6 flex flex-col items-center justify-center"
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
          >
            <p className="text-xs text-blue-400 mb-3">答案</p>
            <p className="text-center text-slate-800 leading-relaxed whitespace-pre-wrap">
              {card.back}
            </p>
          </div>
        </div>
      </div>

      {/* Rating Buttons - only show when flipped */}
      {flipped && (
        <div className="flex justify-center gap-3">
          {ratingButtons.map((btn) => (
            <button
              key={btn.rating}
              onClick={() => {
                onRate(btn.rating)
                setFlipped(false)
              }}
              className={`px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${btn.color}`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
