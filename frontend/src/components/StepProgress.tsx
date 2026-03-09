interface Props {
  currentStep: number
  completedSteps: number[]
}

const steps = [
  { num: 1, label: '深度研究' },
  { num: 2, label: '准确性验证' },
  { num: 3, label: '资源整理' },
  { num: 4, label: '测验生成' },
  { num: 5, label: '练习生成' },
]

export default function StepProgress({ currentStep, completedSteps }: Props) {
  return (
    <div className="flex items-center justify-between max-w-2xl mx-auto py-4">
      {steps.map((step, i) => {
        const isCompleted = completedSteps.includes(step.num)
        const isCurrent = currentStep === step.num
        const isLast = i === steps.length - 1

        return (
          <div key={step.num} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : isCurrent
                    ? 'bg-blue-500 text-white ring-4 ring-blue-100'
                    : 'bg-slate-200 text-slate-500'
                }`}
              >
                {isCompleted ? '✓' : step.num}
              </div>
              <span
                className={`text-xs mt-1.5 whitespace-nowrap ${
                  isCurrent
                    ? 'text-blue-600 font-medium'
                    : isCompleted
                    ? 'text-green-600'
                    : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={`flex-1 h-0.5 mx-2 mt-[-1rem] ${
                  isCompleted ? 'bg-green-400' : 'bg-slate-200'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
