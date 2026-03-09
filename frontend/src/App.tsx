import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import AssessmentPage from './pages/AssessmentPage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import LearningPage from './pages/LearningPage'
import QuizPage from './pages/QuizPage'
import ReviewPage from './pages/ReviewPage'
import ProgressPage from './pages/ProgressPage'
import ExportPage from './pages/ExportPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/assess" element={<AssessmentPage />} />
        <Route path="/graph" element={<KnowledgeGraphPage />} />
        <Route path="/learn/:conceptId" element={<LearningPage />} />
        <Route path="/quiz/:conceptId" element={<QuizPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/export" element={<ExportPage />} />
      </Route>
    </Routes>
  )
}
