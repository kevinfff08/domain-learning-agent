import type { Question } from '../types'
import MultipleChoice from './MultipleChoice'

interface Props {
  question: Question
  answer: string | null
  correctAnswer?: string | null
  disabled: boolean
  onChange: (value: string) => void
}

export default function QuizQuestion({
  question,
  answer,
  correctAnswer,
  disabled,
  onChange,
}: Props) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
          {questionTypeLabel(question.question_type)}
        </span>
        <span className="text-xs text-slate-400">
          {question.points} 分
        </span>
      </div>

      <p className="text-sm text-slate-800 mb-4 leading-relaxed whitespace-pre-wrap">
        {question.question_text}
      </p>

      {question.question_type === 'multiple_choice' && question.options && (
        <MultipleChoice
          options={question.options}
          selected={answer}
          correctAnswer={correctAnswer}
          disabled={disabled}
          onChange={onChange}
        />
      )}

      {question.question_type === 'derivation' && (
        <textarea
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="请写出推导过程..."
          className="w-full h-32 rounded-lg border border-slate-200 p-3 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-50"
        />
      )}

      {question.question_type === 'code' && (
        <textarea
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="请编写代码..."
          className="w-full h-40 rounded-lg border border-slate-200 p-3 text-sm font-mono resize-y bg-slate-900 text-green-300 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-60"
        />
      )}

      {question.question_type === 'concept_comparison' && (
        <textarea
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="请比较这些概念..."
          className="w-full h-32 rounded-lg border border-slate-200 p-3 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-50"
        />
      )}

      {/* Show explanation after submission */}
      {disabled && question.explanation && (
        <div className="mt-4 rounded-lg bg-blue-50 border border-blue-200 p-3">
          <p className="text-xs font-semibold text-blue-700 mb-1">解析</p>
          <p className="text-sm text-slate-700">{question.explanation}</p>
        </div>
      )}
    </div>
  )
}

function questionTypeLabel(type: string): string {
  switch (type) {
    case 'multiple_choice':
      return '选择题'
    case 'derivation':
      return '推导题'
    case 'code':
      return '编程题'
    case 'concept_comparison':
      return '概念比较'
    default:
      return type
  }
}
