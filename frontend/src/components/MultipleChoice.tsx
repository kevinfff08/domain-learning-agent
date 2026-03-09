interface Props {
  options: string[]
  selected: string | null
  correctAnswer?: string | null
  disabled: boolean
  onChange: (value: string) => void
}

const labels = ['A', 'B', 'C', 'D', 'E', 'F']

export default function MultipleChoice({
  options,
  selected,
  correctAnswer,
  disabled,
  onChange,
}: Props) {
  return (
    <div className="space-y-2">
      {options.map((option, i) => {
        const value = labels[i]
        const isSelected = selected === value
        const isCorrect = correctAnswer === value
        const showResult = disabled && correctAnswer

        let borderClass = 'border-slate-200'
        let bgClass = ''

        if (showResult) {
          if (isCorrect) {
            borderClass = 'border-green-400'
            bgClass = 'bg-green-50'
          } else if (isSelected && !isCorrect) {
            borderClass = 'border-red-400'
            bgClass = 'bg-red-50'
          }
        } else if (isSelected) {
          borderClass = 'border-blue-400'
          bgClass = 'bg-blue-50'
        }

        return (
          <label
            key={value}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${borderClass} ${bgClass} ${
              disabled ? 'cursor-not-allowed opacity-80' : 'hover:bg-slate-50'
            }`}
          >
            <input
              type="radio"
              name="mc-option"
              value={value}
              checked={isSelected}
              disabled={disabled}
              onChange={() => onChange(value)}
              className="mt-0.5 text-blue-600"
            />
            <span className="text-sm text-slate-700">
              <span className="font-medium mr-1">{value}.</span>
              {option}
            </span>
          </label>
        )
      })}
    </div>
  )
}
