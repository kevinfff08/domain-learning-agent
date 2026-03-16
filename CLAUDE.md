# NewLearner

PhD 级 AI 研究领域学习系统，基于教科书/课程架构。系统搜索学术论文，通过 LLM 生成结构化教科书大纲，再为每章生成三层深度内容（直觉理解 → 机制原理 → 实践应用）。

## Tech Stack

- Language: Python 3.14+ (conda: `research_tools`)
- LLM: Anthropic Claude, 支持 api-key 直连和 CLIProxyAPI 代理两种模式
- Backend: FastAPI + Uvicorn, SSE 长连接
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS v4
- Data models: Pydantic v2
- HTTP client: httpx (async)
- CLI: Typer + Rich
- Testing: pytest + respx

## Architecture

```
src/
  models/          Pydantic 数据模型 (Course, Textbook, Chapter, etc.)
  skills/          11 个技能实现 (见下方 Skill Layers)
  apis/            外部 API 客户端 (OpenAlex, arXiv, Semantic Scholar, Tavily)
  api/             FastAPI 后端 (routes/, deps.py, app.py)
  llm/             LLM 交互层 (Anthropic API, raw JSON + auto-continuation)
  storage/         持久化 (JSON file store, course-scoped)
  orchestrator.py  中心工作流协调器
  cli.py           Typer CLI 入口
frontend/          React SPA
  src/
    api/client.ts  API 客户端 (SSE streaming)
    pages/         CoursesPage, NewCoursePage, TextbookPage, ChapterPage
    components/    Layout, ContentRenderer, EquationBlock, CodeBlock
    types/         TypeScript 类型定义
templates/         Jinja2 导出模板
tests/             pytest 测试套件
```

### Skill Layers (11 skills)

- Layer 1 Assessment & Planning: Pre-Assessor, Textbook Planner
- Layer 2 Knowledge Construction: Deep Researcher (3 次专用 LLM 调用), Accuracy Verifier, Resource Curator
- Layer 3 Learning Delivery: Quiz Engine, Adaptive Controller, Spaced Repetition (FSRS), Practice Generator
- Layer 4 Output & Tracking: Progress Tracker, Material Integrator

### Data Flow

```
Assessment → Textbook Outline (paper search + LLM) → Chapter Content (Intuition/Mechanism/Practice) → Quiz & Review
```

### Data Storage (data/, gitignored)

```
data/
  courses.json                              课程注册表
  courses/{course_id}/
    course.json / assessment_profile.json / textbook.json / progress.json
    content/{chapter_id}/
      research_synthesis.json               三层章节内容
      resources.json / verification_report.json
    cards/{chapter_id}/cards.json           FSRS 闪卡
    quizzes/{chapter_id}/quiz.json          章节测验
  cache/                                    共享 API 缓存
```

## Commands

```bash
# Environment
conda activate research_tools
pip install -e ".[dev]"

# Development
uvicorn src.api.app:app --reload                    # Backend (port 8000)
cd frontend && npm run dev                           # Frontend (port 5173)

# CLI
newlearner create <field>      # 创建课程
newlearner outline <course>    # 生成教科书大纲
newlearner generate <course>   # 生成章节内容
newlearner courses             # 列出所有课程
newlearner progress <course>   # 查看学习进度
newlearner review              # 查看待复习闪卡
newlearner export <course>     # 导出学习材料

# Testing
pytest
```

### API Routes

```
GET/POST        /api/courses                             课程 CRUD
GET/DELETE      /api/courses/{id}
GET             /api/courses/{id}/textbook               教科书大纲
GET (SSE)       /api/courses/{id}/textbook/build          构建大纲
GET (SSE)       /api/courses/{id}/textbook/generate       批量生成章节
POST            /api/courses/{id}/textbook/generate/pause 暂停批量生成
GET             /api/courses/{id}/chapters/{ch}           章节内容
GET (SSE)       /api/courses/{id}/chapters/{ch}/stream    生成单章
DELETE          /api/courses/{id}/chapters/{ch}           删除章节内容
POST            /api/courses/{id}/chapters/{ch}/quiz/submit
POST            /api/courses/{id}/chapters/{ch}/socratic  苏格拉底对话
GET             /api/courses/{id}/review/due
POST            /api/courses/{id}/review/{card}
GET             /api/courses/{id}/progress
POST            /api/courses/{id}/export
```

## Conventions

- LLM 调用方式：raw JSON mode + auto-continuation（structured output 已禁用，报错率过高）
- LLM 供应商：Anthropic Claude only，通过 `src/llm/client.py` 统一封装
- 所有 skill 遵循统一模式：input model → process → output model
- 所有数据结构使用 Pydantic v2 models，所有函数需要类型标注
- SSE (Server-Sent Events) 用于长时间运行的操作
- 章节生成支持进度恢复：中间结果逐步保存，失败后重试跳过已完成步骤
- 章节状态流转：pending → generating → ready → in_progress → completed；生成中断则变为 interrupted
- 服务启动时自动将 generating 状态的章节恢复为 interrupted，前端通过 boot-time 轮询检测服务重启
- 日志使用 `src/logging_config.py` 统一配置，模块级 logger
- Frontend 使用 React Router 进行课程级导航
- Markdown 渲染使用 react-markdown + remark-gfm + remark-math + rehype-katex
- 每次更新代码后检查并更新 README、CLAUDE.md、.env.example、pyproject.toml 版本号

## API Keys

Store in `.env` file (gitignored):

| 变量 | 用途 | 必需 |
|------|------|------|
| `ANTHROPIC_API_KEY` | LLM 调用 (api-key 模式) | 是 |
| `LLM_MODE` | `api-key` 或 `setup-token` | 否 (默认 api-key) |
| `LLM_MODEL` | 覆盖默认模型 | 否 |
| `LLM_MAX_TOKENS` | 覆盖最大输出 token | 否 |
| `LLM_MAX_CONTINUATIONS` | 截断时最大续写次数 | 否 (默认 3) |
| `VERIFICATION_ENABLED` | 启用/关闭准确性验证步骤 | 否 (默认 true) |
| `VERIFICATION_MODEL` | 验证步骤使用的模型 (可与生成模型不同) | 否 (默认同 LLM_MODEL) |
| `TAVILY_API_KEY` | Web 搜索 (大纲生成) | 否 |
| `SEMANTIC_SCHOLAR_API_KEY` | 论文搜索增强 | 否 |
| `GITHUB_TOKEN` | GitHub API rate limit | 否 |

## Scope

- 不做通用聊天机器人，只做结构化领域学习
- 不做实时协作或多用户系统
- 不做自动化论文写作
- 数据存储仅使用本地 JSON 文件，不使用数据库

## Important

- Deep Researcher 是最核心最昂贵的 skill，每章 3 次独立 LLM 调用（Mechanism → Intuition + Practice 并行）
- 章节内容生成有进度恢复机制，不要在 orchestrator 中破坏逐步保存逻辑
- LLM structured output (output_config) 已禁用，当前使用 raw JSON + repair + continuation
- 内容质量有最小字符数校验，不达标会自动重试

## Maintaining This File

随着开发推进，将反复出现的纠正和约定追加到对应章节中。
目标：保持此文件在 300 行以内，只包含对所有任务通用的信息。
