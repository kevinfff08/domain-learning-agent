import { useEffect, useRef } from 'react'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.min.css'

interface Props {
  code: string
  language?: string
}

export default function CodeBlock({ code, language = 'python' }: Props) {
  const codeRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (codeRef.current) {
      hljs.highlightElement(codeRef.current)
    }
  }, [code, language])

  return (
    <div className="my-4 rounded-lg overflow-hidden">
      <div className="bg-slate-800 px-4 py-1.5 flex items-center justify-between">
        <span className="text-xs text-slate-400 font-mono">{language}</span>
        <button
          className="text-xs text-slate-400 hover:text-white transition-colors"
          onClick={() => navigator.clipboard.writeText(code)}
        >
          复制
        </button>
      </div>
      <pre className="!m-0 !rounded-t-none">
        <code
          ref={codeRef}
          className={`language-${language} !bg-slate-900 text-sm`}
        >
          {code}
        </code>
      </pre>
    </div>
  )
}
