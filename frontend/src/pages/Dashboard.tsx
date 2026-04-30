import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDashboard } from '../api/client'
import type { DashboardTestCase, DashboardModelResult } from '../types'

type StatusFilter = 'all' | 'pass' | 'fail' | 'not_tested'

function ScoreCell({ result }: { result?: DashboardModelResult }) {
  if (!result) {
    return <td className="score-cell score-none">&mdash;</td>
  }
  const cls = result.passed ? 'score-pass' : 'score-fail'
  return (
    <td className={`score-cell ${cls}`}>
      <Link to={`/evaluations/${result.evaluation_id}`} className="score-link">
        <span className="score-dot">{result.passed ? '\u25CF' : '\u25CB'}</span>
        {' '}
        {result.score.toFixed(2)}
        {result.mcp_enabled && <span className="mode-indicator" title="Agentic (MCP)">A</span>}
      </Link>
    </td>
  )
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  })

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredTestCases = useMemo(() => {
    if (!data) return []

    return data.test_cases.filter((tc: DashboardTestCase) => {
      // Search
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        if (!tc.name.toLowerCase().includes(q)
          && !tc.id.toLowerCase().includes(q)
          && !tc.tags.some(t => t.toLowerCase().includes(q))) {
          return false
        }
      }

      // Status
      if (statusFilter !== 'all') {
        const hasResults = Object.keys(tc.results).length > 0
        if (statusFilter === 'not_tested') return !hasResults
        if (statusFilter === 'pass') return hasResults && Object.values(tc.results).some(r => r.passed)
        if (statusFilter === 'fail') return hasResults && !Object.values(tc.results).every(r => r.passed)
      }

      return true
    })
  }, [data, searchQuery, statusFilter])

  if (isLoading) return <div className="loading">Loading dashboard...</div>
  if (error) return <div className="error">Error loading dashboard: {(error as Error).message}</div>
  if (!data) return null

  const { models, summary } = data

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Evaluation Dashboard</h1>
        <div className="summary-bar">
          <span className="summary-stat">
            <strong>{summary.total_test_cases}</strong> phenotypes
          </span>
          <span className="summary-stat">
            <strong>{summary.total_evaluations}</strong> evaluations
          </span>
          <span className="summary-stat">
            <strong>{summary.evaluated_test_cases}</strong> tested
          </span>
          <span className={`summary-stat ${summary.pass_rate > 0.5 ? 'stat-good' : 'stat-warn'}`}>
            <strong>{(summary.pass_rate * 100).toFixed(0)}%</strong> pass rate
          </span>
          <span className="summary-stat">
            <strong>{summary.passed}</strong> pass / <strong>{summary.failed}</strong> fail
          </span>
        </div>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Search phenotypes..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="filter-search"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as StatusFilter)}>
          <option value="all">All Statuses</option>
          <option value="pass">Passed</option>
          <option value="fail">Failed</option>
          <option value="not_tested">Not Tested</option>
        </select>
      </div>

      <div className="table-container">
        <table className="score-table">
          <thead>
            <tr>
              <th className="col-name">Phenotype</th>
              {models.map(model => (
                <th key={model} className="col-score">{model}</th>
              ))}
              <th className="col-score">Best</th>
            </tr>
          </thead>
          <tbody>
            {filteredTestCases.map(tc => (
              <tr key={tc.id}>
                <td className="cell-name">
                  <Link to={`/test-cases/${tc.id}`}>{tc.name}</Link>
                  {tc.multi_query && <span className="badge badge-multi">multi</span>}
                </td>
                {models.map(model => (
                  <ScoreCell key={model} result={tc.results[model]} />
                ))}
                <td className="score-cell score-best">
                  {tc.best_score !== null ? tc.best_score.toFixed(2) : '\u2014'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        Showing {filteredTestCases.length} of {data.test_cases.length} phenotypes
      </div>
    </div>
  )
}
