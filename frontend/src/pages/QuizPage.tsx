import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useCourse } from '../contexts/CourseContext'
import { submitQuiz } from '../api/client'
import type { Quiz, QuizResult } from '../types'
import QuizQuestion from '../components/QuizQuestion'

export default function QuizPage() {
  const { courseId } = useCourse()
  const { chapterId } = useParams<{ chapterId: string }>()
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<QuizResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!courseId || !chapterId) return
    // Fetch chapter content which may include quiz data, or fetch quiz endpoint
    // For now, we use the chapter content endpoint and assume quiz is generated on demand via submit
    setLoading(false)
    // Try to fetch quiz from a dedicated endpoint
    fetch(`/api/courses/${encodeURIComponent(courseId)}/chapters/${encodeURIComponent(chapterId)}/quiz`)
      .then(async (res) => {
        if (!res.ok) throw new Error('加载测验失败')
        return res.json()
      })
      .then((data) => setQuiz(data as Quiz))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [courseId, chapterId])

  const handleSubmit = async () => {
    if (!courseId || !chapterId || !quiz) return
    setSubmitting(true)
    try {
      const res = await submitQuiz(courseId, chapterId, answers)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败')
    } finally {
      setSubmitting(false)
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
