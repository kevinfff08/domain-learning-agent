import katex from 'katex'
import 'katex/dist/katex.min.css'
import type { Equation } from '../types'

interface Props {
  equation: Equation
}

export default function EquationBlock({ equation }: Props) {
  let html = ''
  try {
    html = katex.renderToString(equation.latex, {
      throwOnError: false,
      displayMode: true,
    })
  } catch {
    html = `<code>${equation.latex}</code>`
  }

  return (
    <div className="my-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-slate-700">
          {equation.name}
        </h4>
        {equation.source_paper && (
          <span className="text-xs text-slate-400 italic">
            {equation.source_paper}
          </span>
        )}
      </div>

      <div
        className="overflow-x-auto py-3 text-center"
        dangerouslySetInnerHTML={{ __html: html }}
      />

      <p className="text-sm text-slate-600 mt-2 leading-relaxed">
        {equation.explanation}
      </p>
    </div>
  )
}
