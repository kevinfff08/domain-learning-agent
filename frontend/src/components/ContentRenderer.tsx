import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import type { ResearchSynthesis } from '../types'
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
      {/* Analogy Card */}
      <div className="rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 p-5">
        <h3 className="text-sm font-semibold text-blue-700 mb-2">类比</h3>
        <p className="text-slate-700 leading-relaxed">{intuition.analogy}</p>
      </div>

      {/* Visual Description */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 p-5">
        <h3 className="text-sm font-semibold text-amber-700 mb-2">
          可视化描述
        </h3>
        <p className="text-slate-700 leading-relaxed">
          {intuition.visual_description}
        </p>
      </div>

      {/* Key Insight */}
      <div className="rounded-lg bg-green-50 border border-green-300 p-5">
        <h3 className="text-sm font-semibold text-green-700 mb-2">
          核心洞察
        </h3>
        <p className="text-slate-800 font-medium leading-relaxed">
          {intuition.key_insight}
        </p>
      </div>

      {/* ELI5 */}
      {intuition.eli5 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-600 mb-2">
            简单解释
          </h3>
          <p className="text-slate-600 leading-relaxed">{intuition.eli5}</p>
        </div>
      )}

      {/* Mental Model */}
      {intuition.mental_model && (
        <div>
          <h3 className="text-sm font-semibold text-slate-600 mb-2">
            思维模型
          </h3>
          <p className="text-slate-600 leading-relaxed">
            {intuition.mental_model}
          </p>
        </div>
      )}
    </div>
  )
}

function MechanismPanel({ synthesis }: Props) {
  const { mechanism } = synthesis
  return (
    <div className="space-y-6">
      {/* Math Framework */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">
          数学框架
        </h3>
        <div className="prose prose-slate max-w-none prose-sm">
          <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
            {mechanism.math_framework}
          </ReactMarkdown>
        </div>
      </div>

      {/* Equations */}
      {mechanism.equations.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            核心公式
          </h3>
          {mechanism.equations.map((eq, i) => (
            <EquationBlock key={i} equation={eq} />
          ))}
        </div>
      )}

      {/* Pseudocode */}
      {mechanism.pseudocode && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">伪代码</h3>
          <CodeBlock code={mechanism.pseudocode} language="python" />
        </div>
      )}

      {/* Algorithm Steps */}
      {mechanism.algorithm_steps.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            算法步骤
          </h3>
          <ol className="space-y-2">
            {mechanism.algorithm_steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-700">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold">
                  {i + 1}
                </span>
                <span className="leading-relaxed pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Complexity Analysis */}
      {mechanism.complexity_analysis && (
        <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-2">
            复杂度分析
          </h3>
          <p className="text-sm text-slate-600">
            {mechanism.complexity_analysis}
          </p>
        </div>
      )}
    </div>
  )
}

function PracticePanel({ synthesis }: Props) {
  const { practice } = synthesis
  return (
    <div className="space-y-6">
      {/* Reference Implementations */}
      {practice.reference_implementations.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            参考实现
          </h3>
          <div className="grid gap-3">
            {practice.reference_implementations.map((res, i) => (
              <a
                key={i}
                href={res.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-blue-600">
                    {res.title}
                  </span>
                  <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    {res.type}
                  </span>
                </div>
                {res.description && (
                  <p className="text-xs text-slate-500 mt-1">
                    {res.description}
                  </p>
                )}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Hyperparameters Table */}
      {Object.keys(practice.hyperparameters).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            超参数配置
          </h3>
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">
                    参数
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">
                    推荐值
                  </th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(practice.hyperparameters).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-mono text-xs text-slate-700">
                      {k}
                    </td>
                    <td className="px-4 py-2 text-slate-600">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Common Pitfalls */}
      {practice.common_pitfalls.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            常见陷阱
          </h3>
          <ul className="space-y-2">
            {practice.common_pitfalls.map((pitfall, i) => (
              <li
                key={i}
                className="flex gap-2 text-sm text-slate-700 bg-red-50 border border-red-100 rounded-lg p-3"
              >
                <span className="text-red-500 flex-shrink-0">!</span>
                <span>{pitfall}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Reproduction Checklist */}
      {practice.reproduction_checklist.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            复现清单
          </h3>
          <ul className="space-y-1.5">
            {practice.reproduction_checklist.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="mt-1 rounded border-slate-300"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
