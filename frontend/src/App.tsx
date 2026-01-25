import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import TestCases from './pages/TestCases'
import Evaluate from './pages/Evaluate'
import Results from './pages/Results'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <h1>FHIR Query Evaluation</h1>
          <div className="nav-links">
            <a href="/">Home</a>
            <a href="/test-cases">Test Cases</a>
            <a href="/evaluate">Evaluate</a>
            <a href="/results">Results</a>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/test-cases" element={<TestCases />} />
            <Route path="/evaluate" element={<Evaluate />} />
            <Route path="/results" element={<Results />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
