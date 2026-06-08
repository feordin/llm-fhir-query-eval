import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import PhenotypeMatrix from './pages/PhenotypeMatrix'
import PhenotypeDetail from './pages/PhenotypeDetail'
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
            <NavLink to="/">Leaderboard</NavLink>
            <NavLink to="/phenotypes">Phenotypes</NavLink>
            <NavLink to="/live">Live tooling</NavLink>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            {/* Static report */}
            <Route path="/" element={<Leaderboard />} />
            <Route path="/phenotypes" element={<PhenotypeMatrix />} />
            <Route path="/phenotypes/:id" element={<PhenotypeDetail />} />
            {/* Live tooling (backend API) */}
            <Route path="/live" element={<Dashboard />} />
            <Route path="/live/test-cases" element={<TestCases />} />
            <Route path="/live/test-cases/:id" element={<TestCaseDetail />} />
            <Route path="/live/evaluations/:id" element={<EvaluationDetail />} />
            <Route path="/live/evaluate" element={<Evaluate />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
