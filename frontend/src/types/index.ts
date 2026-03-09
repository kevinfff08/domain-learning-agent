// Assessment
export interface AssessmentProfile {
  field: string
  math_level: number
  programming_level: number
  domain_level: number
  learning_goal: 'understand_concepts' | 'reproduce_papers' | 'improve_methods'
  available_hours: number
  learning_style: string
  created_at?: string
}

// Knowledge Graph
export interface ConceptNode {
  id: string
  name: string
  description: string
  difficulty: number
  status: 'pending' | 'in_progress' | 'completed'
  mastery_level: number
  prerequisites: string[]
  category?: string
}

export interface GraphEdge {
  source: string
  target: string
  relationship: string
  weight: number
}

export interface KnowledgeGraph {
  field: string
  nodes: ConceptNode[]
  edges: GraphEdge[]
  created_at?: string
}

// Research Synthesis - Three Layer Content
export interface Equation {
  name: string
  latex: string
  explanation: string
  source_paper?: string
}

export interface IntuitionLayer {
  analogy: string
  visual_description: string
  key_insight: string
  eli5: string
  mental_model: string
}

export interface MechanismLayer {
  math_framework: string
  equations: Equation[]
  pseudocode: string
  algorithm_steps: string[]
  complexity_analysis?: string
}

export interface Resource {
  title: string
  url: string
  type: string
  difficulty: string
  description?: string
}

export interface PracticeLayer {
  reference_implementations: Resource[]
  hyperparameters: Record<string, string>
  common_pitfalls: string[]
  reproduction_checklist: string[]
  exercises?: string[]
}

export interface ResearchSynthesis {
  concept_id: string
  concept_name: string
  intuition: IntuitionLayer
  mechanism: MechanismLayer
  practice: PracticeLayer
  generated_at?: string
}

// Verification
export interface VerificationCheck {
  claim: string
  source: string
  status: 'verified' | 'unverified' | 'disputed'
  confidence: number
  notes?: string
}

export interface VerificationReport {
  concept_id: string
  checks: VerificationCheck[]
  overall_confidence: number
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

// Resources
export interface ResourceCollection {
  concept_id: string
  resources: Resource[]
  curated_at?: string
}

// SSE Events
export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}
