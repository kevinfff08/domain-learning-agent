# NewLearner

PhD 级 AI 研究领域自学系统。输入一个研究领域，系统自动搜索学术论文、生成教材大纲、为每章生成深度三层内容（直觉 → 机制 → 实践），并通过测验、间隔重复和自适应控制持续巩固学习。

## 功能特性

- **多课程管理** — 创建、切换、删除不同领域的学习课程
- **智能教材生成** — 多源搜索（Tavily 网络搜索 + OpenAlex/arXiv 论文），LLM 结合论文、教程、博客生成 15-30 章教材大纲
- **课程要求细化** — 创建课程时可提供整门课的补充要求，大纲会为每章生成可编辑的章节级指导
- **三层内容体系** — 每章包含直觉层（深度类比/核心洞察/重要性分析）、机制层（连续数学叙述/严格推导/学术算法块）、实践层（代码分析/逐行注释/设计决策/超参数指南）
- **准确性验证** — 自动交叉验证生成内容的关键声明（可关闭，支持独立模型配置）
- **批量生成控制** — 一键生成全部章节，支持暂停/继续，实时显示每章进度
- **中断恢复** — 服务重启后自动识别中断的章节，支持从断点继续生成
- **服务状态监控** — 前端自动检测后端重启并通知用户
- **自适应学习** — 根据测验表现动态调整内容难度和解释方式
- **间隔重复 (FSRS)** — 基于 FSRS-6 算法的闪卡复习系统
- **多格式导出** — Obsidian 笔记库、Anki 卡组、HTML、PDF

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.14, FastAPI, Pydantic v2, SSE |
| 前端 | React, TypeScript, Vite, Tailwind CSS |
| LLM | Anthropic Claude API / OpenAI API |
| 资料搜索 | Tavily (主, 网络搜索), OpenAlex + arXiv (学术论文 fallback) |
| 间隔重复 | FSRS-6 算法 |

## 快速开始

### 环境准备

```bash
# 创建 conda 环境
conda create -n research_tools python=3.14
conda activate research_tools

# 安装后端
pip install -e ".[dev]"

# 安装前端
cd frontend && npm install
```

### 配置 API Key

在项目根目录创建 `.env` 文件：

```env
ANTHROPIC_API_KEY=sk-ant-...        # 必需
TAVILY_API_KEY=tvly-...              # 推荐，大纲生成时搜索教程/论文
SEMANTIC_SCHOLAR_API_KEY=...         # 可选，提高速率限制
GITHUB_TOKEN=...                     # 可选
```

### LLM 连接模式

**Mode A: API Key（默认）**

Anthropic official API:

```env
LLM_PROVIDER=anthropic
LLM_MODE=api-key
ANTHROPIC_API_KEY=sk-ant-api03-...
```

OpenAI official API:

```env
LLM_PROVIDER=openai
LLM_MODE=api-key
OPENAI_API_KEY=sk-proj-...
LLM_MODEL=gpt-4.1
```

**Mode B: Setup Token（Claude 订阅用户）**

通过 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 代理请求：

```env
LLM_PROVIDER=anthropic   # or openai
LLM_MODE=setup-token
LLM_PROXY_URL=http://localhost:8317
```

### 所有 `.env` 字段

| 变量 | 必需 | 说明 |
|------|------|------|
| `LLM_MODE` | 否 | `api-key`（默认）或 `setup-token` |
| `ANTHROPIC_API_KEY` | api-key 模式 | 从 [console.anthropic.com](https://console.anthropic.com) 获取 |
| `LLM_PROXY_URL` | 否 | setup-token 模式的代理地址（默认 `http://localhost:8317`） |
| `TAVILY_API_KEY` | 否 | 网络搜索（教程/博客/论文），从 [tavily.com](https://tavily.com) 获取，免费 1000 次/月 |
| `SEMANTIC_SCHOLAR_API_KEY` | 否 | 提高论文搜索速率限制 |
| `GITHUB_TOKEN` | 否 | 仓库质量指标 |
| `LLM_MODEL` | 否 | 覆盖默认模型（默认 `claude-sonnet-4-20250514`） |
| `LLM_MAX_TOKENS` | 否 | 覆盖最大输出 token 数（默认按模型：Opus 32000, Sonnet 16000） |
| `LLM_MAX_CONTINUATIONS` | 否 | 输出截断时最大自动续写次数（默认 `3`） |
| `VERIFICATION_ENABLED` | 否 | 启用/关闭准确性验证步骤（默认 `true`，设为 `false` 跳过） |
| `VERIFICATION_MODEL` | 否 | 验证步骤使用的模型（默认同 `LLM_MODEL`，可设为更便宜的模型） |
| `API_HOST` | 否 | 后端地址（默认 `127.0.0.1`） |
| `API_PORT` | 否 | 后端端口（默认 `8000`） |

### 启动服务

**一键启动：**

```bash
# Windows
start.bat

# Linux / macOS
./start.sh
```

**手动启动：**

```bash
# 终端 1: 后端
conda activate research_tools
python -m src.api.app

# 终端 2: 前端
cd frontend
npm run dev
```

打开 http://localhost:5173 访问 Web 界面。

创建课程时可以额外填写“课程要求”。系统会先把这段整门课要求用于大纲设计，再为每章生成 `chapter_guidance`；你也可以在大纲页手动修改每章要求，后续重新生成该章时会按新的章节要求生效。
如果当前大纲不满意，可以从教材页返回课程设定页，修改课程要求、学习目标、背景等级等参数；保存后系统会清空旧大纲及其衍生章节内容，并自动重新生成大纲。

## Web 界面功能

- 课程列表与管理（创建/切换/删除）
- 教材大纲预览与编号章节导航
- 实时内容生成进度（SSE 流式传输 + 5 步进度指示器）
- 批量生成控制（暂停/继续，每章实时状态更新）
- 中断章节恢复（服务重启后自动标记，一键继续生成）
- 服务重启通知横幅
- 三层内容渲染（KaTeX 数学公式 + 语法高亮代码）
- 章节测验与即时反馈
- 闪卡复习（3D 翻转动画 + FSRS 调度）
- 学习进度仪表盘
- 多格式导出（Obsidian、Anki、HTML、PDF）

## CLI 命令

```bash
# 创建课程（含学习者评估）
newlearner create "Diffusion Models" --math-level 4 --programming-level 4

# 生成教材大纲
newlearner outline diffusion_models

# 生成章节内容
newlearner generate diffusion_models                    # 全部章节
newlearner generate diffusion_models --chapter ch01     # 单章

# 查看课程列表
newlearner courses

# 查看学习进度
newlearner progress diffusion_models

# 复习闪卡
newlearner review

# 导出材料
newlearner export diffusion_models --formats obsidian,anki,html,pdf

# 系统状态
newlearner status
```

## 系统架构

```
用户评估 → 教材大纲生成 → 章节内容生成 → 测验与复习
   │              │              │              │
Pre-Assessor  Textbook      5-step         Quiz Engine
              Planner       Pipeline       Spaced Rep (FSRS)
                │                          Adaptive Controller
          Tavily (教程/博客)
          + OpenAlex/arXiv (论文)
          + LLM 生成大纲
```

### 11 个 Skill（4 层）

| 层 | Skill | 职责 |
|---|---|---|
| 1 评估与规划 | Pre-Assessor | 学习者背景多维诊断 |
| | Textbook Planner | 多源搜索（Tavily + 论文）+ LLM 生成教材大纲 |
| 2 知识构建与验证 | Deep Researcher | 三层内容生成（3 次专用 LLM 调用：机制→直觉+实践并行） |
| | Accuracy Verifier | 关键声明交叉验证 |
| | Resource Curator | 补充资源推荐（论文/代码/教程） |
| 3 学习交付与适应 | Quiz Engine | 章节测验生成与评分 |
| | Adaptive Controller | 自适应难度调整 |
| | Spaced Repetition | FSRS-6 闪卡复习调度 |
| | Practice Generator | 练习题与编程挑战 |
| 4 输出与追踪 | Progress Tracker | 学习进度追踪与报告 |
| | Material Integrator | Obsidian/Anki/HTML/PDF 导出 |

### 章节内容生成管道（5 步）

```
Chapter → Deep Researcher → Accuracy Verifier → Resource Curator → Quiz Engine → Practice Generator
            │                    │                   │                 │              │
         三层内容           声明验证            资源推荐          章节测验        练习题
```

支持**一键批量生成全部章节**和**按需逐章生成**两种模式。

### 完整学习流程

```
用户: "我要学 Diffusion Models"
        |
        v
[Pre-Assessor] → assessment_profile.json（数学/编程/领域水平）
        |
        v
[Textbook Planner] → textbook.json（搜索教程/博客/论文 + LLM 生成 15-30 章大纲）
        |
        v
=== 章节循环 ===
        |
[Deep Researcher] → 三层 PhD 级内容
[Accuracy Verifier] → 验证关键声明
[Resource Curator] → 补充资源
[Quiz Engine] → 章节测验
        |
        |-- 分数 >= 70% → 通过，生成闪卡 + 练习题 → 下一章
        |-- 分数 < 70%  → Adaptive Controller 介入
        |                  L1: 换种方式解释
        |                  L2: 苏格拉底式对话
=== 循环结束 ===
        |
        v
[Progress Tracker] → 进度报告
[Spaced Repetition] → FSRS 闪卡复习
[Material Integrator] → Obsidian / Anki / PDF 导出
```

## 项目结构

```
NewLearner/
├── pyproject.toml             # 项目配置与依赖
├── .env.example               # 环境变量模板
├── start.bat / start.sh       # 一键启动脚本
├── CLAUDE.md                  # Claude Code 项目指令
│
├── frontend/                  # React Web 前端
│   ├── package.json
│   ├── vite.config.ts         # Vite 配置（/api 代理至后端）
│   └── src/
│       ├── App.tsx            # 路由
│       ├── api/client.ts      # REST + SSE API 客户端
│       ├── contexts/          # React Context
│       │   └── CourseContext.tsx
│       ├── pages/             # 页面组件
│       │   ├── CoursesPage.tsx       # 课程列表（首页）
│       │   ├── NewCoursePage.tsx      # 创建课程
│       │   ├── TextbookPage.tsx       # 教材大纲
│       │   ├── ChapterPage.tsx        # 章节阅读
│       │   ├── QuizPage.tsx
│       │   ├── ReviewPage.tsx
│       │   ├── ProgressPage.tsx
│       │   └── ExportPage.tsx
│       ├── components/        # 可复用组件
│       │   ├── Layout.tsx
│       │   ├── Sidebar.tsx
│       │   ├── CourseLayout.tsx
│       │   ├── ContentRenderer.tsx    # 三层内容 + KaTeX
│       │   ├── FlashCard.tsx
│       │   └── ...
│       └── types/index.ts     # TypeScript 类型定义
│
├── skills/                    # Claude Code SKILL.md 文件
│   ├── pre-assessor/
│   ├── textbook-planner/
│   ├── deep-researcher/
│   └── ...
│
├── src/
│   ├── cli.py                 # Typer CLI 入口
│   ├── orchestrator.py        # 工作流引擎（编排 11 个 skill）
│   ├── logging_config.py      # 日志配置
│   │
│   ├── api/                   # FastAPI 后端
│   │   ├── app.py             # 应用配置、CORS、路由注册
│   │   ├── deps.py            # 依赖注入
│   │   └── routes/
│   │       ├── courses.py     # 课程 CRUD
│   │       ├── textbook.py    # 教材/章节/测验/复习/进度/导出
│   │       ├── assessment.py  # 评估
│   │       ├── quiz.py        # 测验（legacy）
│   │       ├── review.py      # 复习（legacy）
│   │       ├── progress.py    # 进度（legacy）
│   │       └── export.py      # 导出（legacy）
│   │
│   ├── models/                # Pydantic v2 数据模型
│   │   ├── course.py          # Course, CourseStatus
│   │   ├── textbook.py        # Textbook, Chapter, ChapterStatus, PaperReference
│   │   ├── assessment.py      # AssessmentProfile
│   │   ├── content.py         # ResearchSynthesis（三层内容）
│   │   ├── quiz.py            # Quiz, QuizResult
│   │   ├── cards.py           # FlashCard, FSRSState
│   │   ├── progress.py        # LearnerProgress
│   │   ├── resources.py       # ResourceCollection
│   │   └── verification.py    # VerificationReport
│   │
│   ├── skills/                # 11 个 Skill 实现
│   │   ├── pre_assessor.py
│   │   ├── textbook_planner.py    # 论文搜索 + LLM 大纲生成
│   │   ├── deep_researcher.py
│   │   ├── accuracy_verifier.py
│   │   ├── resource_curator.py
│   │   ├── quiz_engine.py
│   │   ├── adaptive_controller.py
│   │   ├── spaced_repetition.py   # FSRS-6 算法
│   │   ├── practice_generator.py
│   │   ├── progress_tracker.py
│   │   └── material_integrator.py
│   │
│   ├── apis/                  # 学术 API 客户端
│   │   ├── base.py            # RateLimiter, ResponseCache, BaseAPIClient
│   │   ├── tavily_client.py    # Tavily（主要搜索：教程/博客/论文）
│   │   ├── open_alex.py       # OpenAlex（学术论文 fallback）
│   │   ├── arxiv_client.py    # arXiv（学术论文 fallback）
│   │   ├── semantic_scholar.py
│   │   ├── crossref.py
│   │   ├── papers_with_code.py
│   │   └── github_client.py
│   │
│   ├── llm/                   # LLM 交互层
│   │   └── client.py          # Anthropic API / CLIProxyAPI
│   │
│   └── storage/               # 持久化
│       └── local_store.py     # 课程作用域 JSON 文件存储
│
├── templates/                 # Jinja2 导出模板
├── data/                      # 运行时数据（gitignored）
├── logs/                      # 日志文件（gitignored）
└── tests/                     # pytest 测试套件
```

## 数据存储

```
data/
  courses.json                              # 课程注册表
  courses/{course_id}/
    course.json                             # 课程元数据
    assessment_profile.json                 # 学习者画像
    textbook.json                           # 教材大纲（章节列表）
    progress.json                           # 学习进度
    content/{chapter_id}/
      research_synthesis.json               # 三层章节内容
      resources.json                        # 资源推荐
      verification_report.json              # 验证报告
    cards/{chapter_id}/cards.json           # FSRS 闪卡
    quizzes/{chapter_id}/quiz.json          # 章节测验
  cache/                                    # 共享 API 缓存
```

## 数据模型

所有 Skill 通过 Pydantic v2 模型通信：

| 模型 | 文件 | 说明 |
|------|------|------|
| `Course` | `course.py` | 课程元数据与状态 |
| `Textbook` / `Chapter` | `textbook.py` | 教材大纲与章节定义 |
| `AssessmentProfile` | `assessment.py` | 学习者多维画像 |
| `ResearchSynthesis` | `content.py` | 三层内容（直觉/机制/实践）+ AlgorithmBlock + CodeAnalysis |
| `Quiz` / `QuizResult` | `quiz.py` | 测验题目与评分结果 |
| `FlashCard` / `FSRSState` | `cards.py` | FSRS 闪卡与复习状态 |
| `LearnerProgress` | `progress.py` | 章节与整体进度指标 |
| `ResourceCollection` | `resources.py` | 论文/博客/视频/代码/教程 |
| `VerificationReport` | `verification.py` | 准确性验证报告 |

## API 接口

```
GET/POST        /api/courses                           课程 CRUD
GET/DELETE      /api/courses/{id}
GET             /api/courses/{id}/textbook              教材大纲
GET (SSE)       /api/courses/{id}/textbook/build        生成大纲（流式）
GET (SSE)       /api/courses/{id}/textbook/generate     批量生成章节（流式）
POST            /api/courses/{id}/textbook/generate/pause  暂停批量生成
GET             /api/courses/{id}/chapters/{ch}          章节内容
GET (SSE)       /api/courses/{id}/chapters/{ch}/stream   生成单章（流式）
POST            /api/courses/{id}/chapters/{ch}/quiz/submit  提交测验
GET             /api/courses/{id}/review/due             待复习闪卡
POST            /api/courses/{id}/review/{card}          复习闪卡
GET             /api/courses/{id}/progress               学习进度
POST            /api/courses/{id}/export                 导出材料
GET             /api/status                              系统状态
GET             /api/boot-time                           服务启动时间（重启检测）
```

## API 集成

| API | 用途 | 相关 Skill |
|-----|------|-----------|
| Tavily | 网络搜索（教程/博客/论文，主要） | Textbook Planner |
| OpenAlex | 学术论文搜索（fallback）、引用数据 | Textbook Planner, Deep Researcher |
| arXiv | 学术论文搜索（fallback）、PDF | Textbook Planner, Deep Researcher |
| Semantic Scholar | 论文元数据、引用网络 | Deep Researcher, Accuracy Verifier |
| CrossRef | DOI 验证、引用校验 | Accuracy Verifier |
| Papers With Code | 论文→代码映射 | Resource Curator, Practice Generator |
| GitHub | 仓库质量指标 | Resource Curator |
| Anthropic Claude | LLM 推理与内容生成 | 所有 Skill |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 带覆盖率
pytest --cov=src

# 仅集成测试
pytest -m integration

# 跳过集成测试
pytest -m "not integration"
```

## License

MIT
