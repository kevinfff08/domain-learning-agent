import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchQuiz, submitQuiz, exportQuiz } from '../api/client'
import type { Quiz, QuizResult } from '../types'
import QuizQuestion from '../components/QuizQuestion'

export default function QuizPage() {
  const { conceptId } = useParams<{ conceptId: string }>()
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<QuizResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!conceptId) return
    fetchQuiz(conceptId)
      .then(setQuiz)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [conceptId])

  const handleSubmit = async () => {
    if (!conceptId || !quiz) return
    setSubmitting(true)
    try {
      const res = await submitQuiz(conceptId, answers)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleExport = async () => {
    if (!conceptId) return
    try {
      await exportQuiz(conceptId)
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

  if (error && !quiz) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  if (!quiz) return null

  const submitted = result !== null

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            知识测验: {quiz.concept_name}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            共 {quiz.questions.length} 题 | 及格分:
            {quiz.passing_score}%
            {quiz.time_limit_minutes &&
              ` | 限时 ${quiz.time_limit_minutes} 分钟`}
          </p>
        </div>
        <button
          onClick={handleExport}
          className="text-sm bg-slate-100 text-slate-600 px-4 py-2 rounded-lg hover:bg-slate-200 transition-colors"
        >
          下载测验
        </button>
      </div>

      {/* Result overlay */}
      {result && <ResultPanel result={result} />}

      {/* Questions */}
      <div className="space-y-4">
        {quiz.questions.map((q, i) => {
          const qResult = result?.question_results.find(
            (r) => r.question_id === q.id
          )
          return (
            <div key={q.id}>
              <p className="text-xs text-slate-400 mb-1">
                第 {i + 1} 题
              </p>
              <QuizQuestion
                question={q}
                answer={answers[q.id] ?? null}
                correctAnswer={submitted ? q.correct_answer ?? null : null}
                disabled={submitted}
                onChange={(val) =>
                  setAnswers((prev) => ({ ...prev, [q.id]: val }))
                }
              />
              {qResult && (
                <div
                  className={`mt-2 rounded-lg p-3 text-sm ${
                    qResult.correct
                      ? 'bg-green-50 border border-green-200 text-green-700'
                      : 'bg-red-50 border border-red-200 text-red-700'
                  }`}
                >
                  <span className="font-medium">
                    {qResult.correct ? '正确' : '错误'}
                  </span>
                  {' - '}
                  {qResult.feedback}
                  <span className="text-xs ml-2">
                    (+{qResult.points_earned} 分)
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Submit button */}
      {!submitted && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleSubmit}
            disabled={submitting || Object.keys(answers).length === 0}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? '提交中...' : '提交答案'}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  )
}

function ResultPanel({ result }: { result: QuizResult }) {
  const pct = Math.round(
    (result.score / Math.max(result.total_points, 1)) * 100
  )

  return (
    <div
      className={`mb-6 rounded-xl p-6 border-2 ${
        result.passed
          ? 'bg-green-50 border-green-300'
          : 'bg-red-50 border-red-300'
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <h2
            className={`text-xl font-bold ${
              result.passed ? 'text-green-700' : 'text-red-700'
            }`}
          >
            {result.passed ? '通过!' : '未通过'}
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            得分: {result.score} / {result.total_points} ({pct}%)
          </p>
        </div>
        <div
          className={`text-4xl font-bold ${
            result.passed ? 'text-green-500' : 'text-red-500'
          }`}
        >
          {pct}%
        </div>
      </div>

      {result.adaptive_message && (
        <div className="mt-4 bg-white/60 rounded-lg p-3">
          <p className="text-sm font-medium text-slate-700 mb-1">学习建议</p>
          <p className="text-sm text-slate-600">{result.adaptive_message}</p>
        </div>
      )}
    </div>
  )
}
