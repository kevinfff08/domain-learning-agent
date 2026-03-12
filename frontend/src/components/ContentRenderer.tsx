import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import type { ResearchSynthesis, AlgorithmBlock as AlgorithmBlockType, CodeAnalysis as CodeAnalysisType } from '../types'
import EquationBlock from './EquationBlock'
import CodeBlock from './CodeBlock'

interface Props {
  synthesis: ResearchSynthesis
}

type TabKey = 'intuition' | 'mechanism' | 'practice'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'intuition', label: '直觉理解' },
  { key: 'mechanism', label: '机制原理' },
  { key: 'practice', label: '实践应用' },
]

/** Render markdown + LaTeX inline. Used for all text that may contain $..$ or $$..$$. */
function Md({ children, className }: { children: string; className?: string }) {
  return (
    <div className={`prose prose-slate prose-sm max-w-none ${className ?? ''}`}>
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

export default function ContentRenderer({ synthesis }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>('intuition')

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200">
      {/* Tab Header */}
      <div className="flex border-b border-slate-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'intuition' && (
          <IntuitionPanel synthesis={synthesis} />
        )}
        {activeTab === 'mechanism' && (
          <MechanismPanel synthesis={synthesis} />
        )}
        {activeTab === 'practice' && (
          <PracticePanel synthesis={synthesis} />
        )}
      </div>
    </div>
  )
}

function IntuitionPanel({ synthesis }: Props) {
  const { intuition } = synthesis
  return (
    <div className="space-y-6">
      {intuition.analogy && (
        <div className="rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 p-5">
          <h3 className="text-sm font-semibold text-blue-700 mb-2">类比</h3>
          <Md className="text-slate-700">{intuition.analogy}</Md>
        </div>
      )}

      {intuition.key_insight && (
        <div className="rounded-lg bg-green-50 border border-green-300 p-5">
          <h3 className="text-sm font-semibold text-green-700 mb-2">核心洞察</h3>
          <Md className="text-slate-800 font-medium">{intuition.key_insight}</Md>
        </div>
      )}

      {intuition.why_it_matters && (
        <div>
          <h3 className="text-sm font-semibold text-slate-600 mb-2">为什么重要</h3>
          <Md className="text-slate-600">{intuition.why_it_matters}</Md>
        </div>
      )}
    </div>
  )
}

/** Academic-style algorithm block (Algorithm 1: Name) */
function AlgorithmBlockRenderer({ algorithm }: { algorithm: AlgorithmBlockType }) {
  return (
    <div className="rounded-lg border-2 border-slate-300 bg-slate-50 p-5 my-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-bold text-slate-800">{algorithm.name}</h4>
        {algorithm.source_paper && (
          <span className="text-xs text-slate-400 italic">{algorithm.source_paper}</span>
        )}
      </div>

      {algorithm.inputs?.length > 0 && (
        <div className="mb-2">
          <span className="text-xs font-semibold text-slate-600">Input: </span>
          {algorithm.inputs.map((inp, i) => (
            <span key={i} className="text-xs text-slate-600">
              {i > 0 && ', '}
              <Md className="inline">{inp}</Md>
            </span>
          ))}
        </div>
      )}

      {algorithm.outputs?.length > 0 && (
        <div className="mb-3">
          <span className="text-xs font-semibold text-slate-600">Output: </span>
          {algorithm.outputs.map((out, i) => (
            <span key={i} className="text-xs text-slate-600">
              {i > 0 && ', '}
              <Md className="inline">{out}</Md>
            </span>
          ))}
        </div>
      )}

      <div className="border-t border-slate-300 pt-3 space-y-1">
        {algorithm.steps?.map((step, i) => (
          <div key={i} className="text-sm text-slate-700 font-mono leading-relaxed">
            <Md>{step}</Md>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Code analysis block: code + line annotations + design decisions */
function CodeAnalysisRenderer({ analysis }: { analysis: CodeAnalysisType }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 my-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-bold text-slate-800">{analysis.title}</h4>
        {analysis.source_url && (
          <a
            href={analysis.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:text-blue-600"
          >
            Source
          </a>
        )}
      </div>

      <CodeBlock code={analysis.code} language={analysis.language || 'python'} />

      {analysis.line_annotations?.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold text-slate-600 mb-2">逐行分析</h5>
          <ul className="space-y-1.5">
            {analysis.line_annotations.map((ann, i) => (
              <li key={i} className="text-xs text-slate-600 bg-slate-50 rounded p-2">
                <Md>{ann}</Md>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.key_design_decisions?.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold text-slate-600 mb-2">设计决策</h5>
          <ul className="space-y-1.5">
            {analysis.key_design_decisions.map((dec, i) => (
              <li key={i} className="flex gap-2 text-xs text-slate-600 bg-amber-50 border border-amber-100 rounded p-2">
                <span className="text-amber-500 flex-shrink-0 font-bold">*</span>
                <div className="flex-1"><Md>{dec}</Md></div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function MechanismPanel({ synthesis }: Props) {
  const { mechanism } = synthesis
  return (
    <div className="space-y-6">
      {/* Theoretical Narrative — the main content block */}
      {mechanism.theoretical_narrative && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">理论推导</h3>
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-5">
            <Md>{mechanism.theoretical_narrative}</Md>
          </div>
        </div>
      )}

      {/* Mathematical Framework (legacy / overview) */}
      {mechanism.mathematical_framework && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">数学框架</h3>
          <Md>{mechanism.mathematical_framework}</Md>
        </div>
      )}

      {/* Key Equations — quick reference */}
      {mechanism.key_equations?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">核心公式</h3>
          {mechanism.key_equations.map((eq, i) => (
            <EquationBlock key={i} equation={eq} />
          ))}
        </div>
      )}

      {/* Algorithms — academic style */}
      {mechanism.algorithms?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">算法</h3>
          {mechanism.algorithms.map((alg, i) => (
            <AlgorithmBlockRenderer key={i} algorithm={alg} />
          ))}
        </div>
      )}

      {/* Legacy pseudocode */}
      {mechanism.pseudocode && !mechanism.algorithms?.length && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">伪代码</h3>
          <CodeBlock code={mechanism.pseudocode} language="python" />
        </div>
      )}

      {/* Legacy algorithm steps */}
      {mechanism.algorithm_steps?.length > 0 && !mechanism.algorithms?.length && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">算法步骤</h3>
          <ol className="space-y-2">
            {mechanism.algorithm_steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-700">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold">
                  {i + 1}
                </span>
                <div className="leading-relaxed pt-0.5 flex-1">
                  <Md>{step}</Md>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

function PracticePanel({ synthesis }: Props) {
  const { practice } = synthesis
  return (
    <div className="space-y-6">
      {/* Code Analysis — new primary content */}
      {practice.code_analysis?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">代码分析</h3>
          {practice.code_analysis.map((ca, i) => (
            <CodeAnalysisRenderer key={i} analysis={ca} />
          ))}
        </div>
      )}

      {/* Reference Implementations */}
      {practice.reference_implementations?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">参考实现</h3>
          <div className="grid gap-3">
            {practice.reference_implementations.map((url, i) => (
              <a
                key={i}
                href={url.startsWith('http') ? url.split(' — ')[0] : '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
              >
                <span className="text-sm font-medium text-blue-600 break-all">{url}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Hyperparameters */}
      {practice.key_hyperparameters && Object.keys(practice.key_hyperparameters).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">超参数配置</h3>
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">参数</th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">说明</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(practice.key_hyperparameters).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-mono text-xs text-slate-700">{k}</td>
                    <td className="px-4 py-2 text-slate-600"><Md>{v}</Md></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Common Pitfalls */}
      {practice.common_pitfalls?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">常见陷阱</h3>
          <ul className="space-y-2">
            {practice.common_pitfalls.map((pitfall, i) => (
              <li
                key={i}
                className="flex gap-2 text-sm text-slate-700 bg-red-50 border border-red-100 rounded-lg p-3"
              >
                <span className="text-red-500 flex-shrink-0">!</span>
                <div className="flex-1"><Md>{pitfall}</Md></div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Reproduction Checklist */}
      {practice.reproduction_checklist?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">复现清单</h3>
          <ul className="space-y-1.5">
            {practice.reproduction_checklist.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <input type="checkbox" className="mt-1 rounded border-slate-300" />
                <div className="flex-1"><Md>{item}</Md></div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
