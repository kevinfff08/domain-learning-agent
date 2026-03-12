import katex from 'katex'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import type { Equation } from '../types'

interface Props {
  equation: Equation
}

/** Strip surrounding $$ or $ delimiters that LLMs often include. */
function stripDelimiters(raw: string): string {
  let s = raw.trim()
  if (s.startsWith('$$') && s.endsWith('$$')) return s.slice(2, -2).trim()
  if (s.startsWith('$') && s.endsWith('$')) return s.slice(1, -1).trim()
  return s
}

export default function EquationBlock({ equation }: Props) {
  const latex = stripDelimiters(equation.latex)
  let html = ''
  try {
    html = katex.renderToString(latex, {
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

      {equation.explanation && (
        <div className="text-sm text-slate-600 mt-2 leading-relaxed prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {equation.explanation}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}
