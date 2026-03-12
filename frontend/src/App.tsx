import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import CourseLayout from './components/CourseLayout'
import CoursesPage from './pages/CoursesPage'
import NewCoursePage from './pages/NewCoursePage'
import TextbookPage from './pages/TextbookPage'
import ChapterPage from './pages/ChapterPage'
import QuizPage from './pages/QuizPage'
import ReviewPage from './pages/ReviewPage'
import ProgressPage from './pages/ProgressPage'
import ExportPage from './pages/ExportPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<CoursesPage />} />
        <Route path="/courses/new" element={<NewCoursePage />} />
      </Route>
      <Route path="/courses/:courseId" element={<CourseLayout />}>
        <Route index element={<TextbookPage />} />
        <Route path="chapters/:chapterId" element={<ChapterPage />} />
        <Route path="quiz/:chapterId" element={<QuizPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="export" element={<ExportPage />} />
      </Route>
    </Routes>
  )
}
