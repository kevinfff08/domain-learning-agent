import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCourse, fetchCourseSettings, updateCourse } from '../api/client'

export default function NewCoursePage() {
  const navigate = useNavigate()
  const { courseId } = useParams<{ courseId: string }>()
  const isEditMode = Boolean(courseId)
  const [submitting, setSubmitting] = useState(false)
  const [loadingSettings, setLoadingSettings] = useState(false)
  const [settingsLoadFailed, setSettingsLoadFailed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [field, setField] = useState('')
  const [mathLevel, setMathLevel] = useState(2)
  const [programmingLevel, setProgrammingLevel] = useState(2)
  const [domainLevel, setDomainLevel] = useState(1)
  const [learningGoal, setLearningGoal] = useState<
    'understand_concepts' | 'reproduce_papers' | 'improve_methods'
  >('understand_concepts')
  const [availableHours, setAvailableHours] = useState(10)
  const [learningStyle, setLearningStyle] = useState('intuition_first')
  const [courseRequirements, setCourseRequirements] = useState('')

  useEffect(() => {
    if (!courseId) return

    setLoadingSettings(true)
    setSettingsLoadFailed(false)
    setError(null)

    fetchCourseSettings(courseId)
      .then((settings) => {
        setField(settings.field)
        setCourseRequirements(settings.course_requirements)
        setMathLevel(settings.math_level)
        setProgrammingLevel(settings.programming_level)
        setDomainLevel(settings.domain_level)
        setLearningGoal(settings.learning_goal)
        setAvailableHours(settings.available_hours)
        setLearningStyle(settings.learning_style)
      })
      .catch((err) => {
        setSettingsLoadFailed(true)
        setError(
          err instanceof Error
            ? `加载课程设定失败：${err.message}。请先重启后端服务，再进入“修改课程设定”。`
            : '加载课程设定失败。请先重启后端服务，再进入“修改课程设定”。',
        )
      })
      .finally(() => setLoadingSettings(false))
  }, [courseId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!field.trim()) {
      setError('请输入学习领域')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const payload = {
        field: field.trim(),
        course_requirements: courseRequirements.trim(),
        math_level: mathLevel,
        programming_level: programmingLevel,
        domain_level: domainLevel,
        learning_goal: learningGoal,
        available_hours: availableHours,
        learning_style: learningStyle,
      }
      const result = courseId
        ? await updateCourse(courseId, payload)
        : await createCourse(payload)

      navigate(`/courses/${result.course.id}`, {
        state: courseId ? { autoBuildOutline: true } : undefined,
      })
    } catch (err) {
      if (courseId) {
        setError(
          err instanceof Error
            ? `保存失败：${err.message}。如果这是刚加的功能，请先重启后端服务。`
            : '保存失败。请先重启后端服务后重试。',
        )
      } else {
        setError(err instanceof Error ? err.message : '创建失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingSettings) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        加载课程设定中...
      </div>
    )
  }

  if (isEditMode && settingsLoadFailed) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">修改课程设定</h1>
        <div className="mt-8 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error ?? '加载课程设定失败。请先重启后端服务，再进入“修改课程设定”。'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-2">
        {isEditMode ? '修改课程设定' : '创建新课程'}
      </h1>
      <p className="text-sm text-slate-400 mb-8">
        {isEditMode
          ? '修改课程要求和学习设定后，系统会清空旧大纲及其衍生内容，并重新生成教材大纲'
          : '填写你的背景和学习目标，系统将为你生成定制化的学习教材'}
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Field */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            学习领域
          </label>
          <input
            type="text"
            value={field}
            onChange={(e) => setField(e.target.value)}
            placeholder="例如: 图神经网络、强化学习、扩散模型"
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            课程要求（可选）
          </label>
          <textarea
            value={courseRequirements}
            onChange={(e) => setCourseRequirements(e.target.value)}
            rows={4}
            placeholder="例如：整门课偏重图像生成实践，减少纯数学证明，并在后半段加入工程实现与调参经验。"
            className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-slate-400">
            这会先影响大纲设计，再细化为每章可编辑的章节要求。
          </p>
        </div>

        {/* Math Level */}
        <SliderField
          label="数学水平"
          value={mathLevel}
          onChange={setMathLevel}
          descriptions={[
            '基础代数',
            '微积分',
            '线性代数',
            '概率统计',
            '优化理论',
            '高等数学',
          ]}
        />

        {/* Programming Level */}
        <SliderField
          label="编程水平"
          value={programmingLevel}
          onChange={setProgrammingLevel}
          descriptions={[
            '入门',
            '基础 Python',
            'NumPy/Pandas',
            'PyTorch/TF',
            '自定义模型',
            '框架级开发',
          ]}
        />

        {/* Domain Level */}
        <SliderField
          label="领域知识"
          value={domainLevel}
          onChange={setDomainLevel}
          descriptions={[
            '零基础',
            '了解概念',
            '读过论文',
            '做过实验',
            '发表论文',
            '领域专家',
          ]}
        />

        {/* Learning Goal */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            学习目标
          </label>
          <select
            value={learningGoal}
            onChange={(e) =>
              setLearningGoal(e.target.value as typeof learningGoal)
            }
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="understand_concepts">理解概念</option>
            <option value="reproduce_papers">复现论文</option>
            <option value="improve_methods">改进方法</option>
          </select>
        </div>

        {/* Available Hours */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            可用时间 (每周小时数)
          </label>
          <input
            type="number"
            min={1}
            max={80}
            value={availableHours}
            onChange={(e) => setAvailableHours(Number(e.target.value))}
            className="w-32 rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        {/* Learning Style */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            学习风格
          </label>
          <select
            value={learningStyle}
            onChange={(e) => setLearningStyle(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="intuition_first">直觉优先 - 偏好类比和可视化</option>
            <option value="mathematical_first">数学优先 - 偏好公式推导</option>
            <option value="code_first">代码优先 - 偏好实现和实验</option>
            <option value="balanced">均衡 - 三者兼顾</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting
            ? (isEditMode ? '正在保存并重建大纲...' : '创建中...')
            : (isEditMode ? '保存并重新生成大纲' : '创建课程')}
        </button>
      </form>
    </div>
  )
}

function SliderField({
  label,
  value,
  onChange,
  descriptions,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  descriptions: string[]
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label}: <span className="text-blue-600">{value}</span>
        <span className="text-slate-400 ml-2 text-xs">
          ({descriptions[value]})
        </span>
      </label>
      <input
        type="range"
        min={0}
        max={5}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-blue-600"
      />
      <div className="flex justify-between text-xs text-slate-400 mt-1">
        <span>0</span>
        <span>5</span>
      </div>
    </div>
  )
}
