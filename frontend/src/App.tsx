import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TestCaseDetail from './pages/TestCaseDetail'
import EvaluationDetail from './pages/EvaluationDetail'
import TestCases from './pages/TestCases'
import Evaluate from './pages/Evaluate'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <Link to="/" style={{ color: 'white', textDecoration: 'none' }}>
            <h1>FHIR Query Evaluation</h1>
          </Link>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/test-cases">Test Cases</Link>
            <Link to="/evaluate">Evaluate</Link>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/test-cases" element={<TestCases />} />
            <Route path="/test-cases/:id" element={<TestCaseDetail />} />
            <Route path="/evaluations/:id" element={<EvaluationDetail />} />
            <Route path="/evaluate" element={<Evaluate />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
