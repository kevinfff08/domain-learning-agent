// Course
export interface CourseEntry {
  id: string
  title: string
  description: string
  status: 'created' | 'outline_ready' | 'generating' | 'active' | 'completed'
  created_at: string
  updated_at: string
  last_accessed: string | null
  total_chapters: number
  completed_chapters: number
}

// Textbook & Chapters
export interface Chapter {
  id: string
  chapter_number: number
  title: string
  description: string
  difficulty: number
  estimated_hours: number
  status: 'pending' | 'generating' | 'interrupted' | 'ready' | 'in_progress' | 'completed'
  mastery: number
  has_content: boolean
  quiz_score: number | null
  tags: string[]
  key_topics: string[]
}

export interface Textbook {
  course_id: string
  field: string
  title: string
  chapters: Chapter[]
  survey_papers: PaperReference[]
  total_estimated_hours: number
  created_at: string
  updated_at: string
}

export interface PaperReference {
  arxiv_id: string
  doi: string
  title: string
  authors: string[]
  year: number
  venue: string
  citation_count: number
  role: string
}

// Assessment - request shape (what we POST)
export interface AssessmentRequest {
  field: string
  math_level: number
  programming_level: number
  domain_level: number
  learning_goal: 'understand_concepts' | 'reproduce_papers' | 'improve_methods'
  available_hours: number
  learning_style: string
}

// Assessment - response shape (what the API returns)
export interface AssessmentProfile {
  target_field: string
  learning_goal: string
  available_hours_per_week: number
  learning_style: string
  math_foundations: Record<string, unknown>
  programming: Record<string, unknown>
  domain_knowledge: Record<string, number>
  calibration_confidence: number
  created_at?: string
  updated_at?: string
}

// Research Synthesis - Three Layer Content
// Must match backend: src/models/content.py

export interface Equation {
  name: string
  latex: string
  explanation: string
  derivation_steps?: string[]
  source_paper?: string
  source_equation_ref?: string
}

export interface IntuitionLayer {
  analogy: string
  why_it_matters: string
  key_insight: string
  estimated_reading_minutes?: number
}

export interface AlgorithmBlock {
  name: string
  inputs: string[]
  outputs: string[]
  steps: string[]
  source_paper?: string
}

export interface MechanismLayer {
  theoretical_narrative: string
  mathematical_framework: string
  key_equations: Equation[]
  algorithms: AlgorithmBlock[]
  pseudocode: string
  algorithm_steps: string[]
  connections?: { target_concept_id: string; relationship: string }[]
  estimated_reading_minutes?: number
}

export interface Resource {
  url: string
  title: string
  resource_type: string
  source?: string
  quality_score?: number
  difficulty: string
  description?: string
  arxiv_id?: string
  citation_count?: number
  github_stars?: number
  language?: string
  framework?: string
}

export interface CodeAnalysis {
  title: string
  language: string
  source_url?: string
  code: string
  line_annotations: string[]
  key_design_decisions: string[]
}

export interface PracticeLayer {
  code_analysis: CodeAnalysis[]
  reference_implementations: string[]
  key_hyperparameters: Record<string, string>
  common_pitfalls: string[]
  reproduction_checklist: string[]
  estimated_reading_minutes?: number
}

export interface ResearchSynthesis {
  concept_id: string
  title: string
  intuition: IntuitionLayer
  mechanism: MechanismLayer
  practice: PracticeLayer
  sources?: { title: string; url?: string; source_type?: string; role?: string }[]
  generated_at?: string
  verified?: boolean
}

// Verification — matches backend: src/models/verification.py
export interface VerificationCheck {
  check_type: string
  claim: string
  source_paper: string
  result: 'verified' | 'warning' | 'error' | 'unverifiable'
  details: string
  confidence: number
}

export interface VerificationReport {
  id: string
  concept_id: string
  checks: VerificationCheck[]
  hallucination_risk_score: number
  flagged_items: string[]
  overall_status: string
  verified_at?: string
}

// Quiz
export interface Question {
  id: string
  question_type: 'multiple_choice' | 'derivation' | 'code' | 'concept_comparison'
  question_text: string
  options?: string[]
  correct_answer?: string
  difficulty: number
  explanation?: string
  points: number
}

export interface Quiz {
  concept_id: string
  concept_name: string
  questions: Question[]
  time_limit_minutes?: number
  passing_score: number
}

export interface QuestionResult {
  question_id: string
  correct: boolean
  user_answer: string
  feedback: string
  points_earned: number
}

export interface QuizResult {
  concept_id: string
  score: number
  total_points: number
  passed: boolean
  question_results: QuestionResult[]
  adaptive_message?: string
  completed_at?: string
}

// Spaced Repetition
export interface SM2State {
  easiness_factor: number
  interval: number
  repetitions: number
  next_review: string
}

export interface FlashCard {
  id: string
  concept_id: string
  front: string
  back: string
  card_type: string
  sm2_state: SM2State
  created_at?: string
}

// Progress
export interface ConceptProgress {
  concept_id: string
  concept_name: string
  status: 'pending' | 'in_progress' | 'completed'
  mastery_level: number
  quiz_scores: number[]
  time_spent_minutes: number
  last_studied?: string
}

export interface LearnerProgress {
  field: string
  total_concepts: number
  completed_concepts: number
  completion_rate: number
  concept_progress: ConceptProgress[]
  weekly_report?: string
  streak_days: number
}

// Resources — matches backend: src/models/resources.py
export interface ResourceCollection {
  concept_id: string
  papers: Resource[]
  blogs: Resource[]
  videos: Resource[]
  code: Resource[]
  courses: Resource[]
  curated_at?: string
}

export interface ExportResponse {
  items: Record<string, string>
  errors: Record<string, string>
}

// SSE Events
export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}
