import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchTestCase, fetchResults } from '../api/client'

export default function TestCaseDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: testCase, isLoading: tcLoading } = useQuery({
    queryKey: ['test-case', id],
    queryFn: () => fetchTestCase(id!),
    enabled: !!id,
  })

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['results', { test_case_id: id }],
    queryFn: () => fetchResults({ test_case_id: id }),
    enabled: !!id,
  })

  if (tcLoading || resultsLoading) return <div className="loading">Loading...</div>
  if (!testCase) return <div className="error">Test case not found</div>

  return (
    <div className="detail-page">
      <Link to="/" className="back-link">&larr; Back to Dashboard</Link>

      <div className="detail-header">
        <h1>{testCase.name}</h1>
        <div className="detail-meta">
          <span className={`badge badge-${testCase.metadata.complexity}`}>
            {testCase.metadata.complexity}
          </span>
          <span className="badge">{testCase.source}</span>
          <span className="badge">{testCase.expected_query.resource_type}</span>
        </div>
      </div>

      <section className="detail-section">
        <h2>Prompt</h2>
        <div className="prompt-box">{testCase.prompt}</div>
      </section>

      <section className="detail-section">
        <h2>Expected Query</h2>
        <code className="query-display">{testCase.expected_query.url}</code>
        {testCase.metadata.required_codes.length > 0 && (
          <div className="codes-list">
            <h3>Required Codes</h3>
            {testCase.metadata.required_codes.map((code, i) => (
              <span key={i} className="code-tag">
                {code.system.split('/').pop()}|{code.code} ({code.display})
              </span>
            ))}
          </div>
        )}
        {testCase.metadata.algorithm_path && (
          <p className="algorithm-path">Algorithm path: {testCase.metadata.algorithm_path}</p>
        )}
      </section>

      <section className="detail-section">
        <h2>Evaluation Results</h2>
        {results && results.length > 0 ? (
          <table className="score-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Mode</th>
                <th>Score</th>
                <th>Exec F1</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>Semantic</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {results.map(r => (
                <tr key={r.evaluation_id}>
                  <td>
                    <Link to={`/evaluations/${r.evaluation_id}`}>{r.model}</Link>
                  </td>
                  <td>{r.mcp_enabled ? 'Agentic' : 'Closed'}</td>
                  <td className={r.passed ? 'score-pass' : 'score-fail'}>
                    {r.overall_score.toFixed(2)}
                  </td>
                  <td>{r.evaluation_results.execution_match.f1_score.toFixed(2)}</td>
                  <td>{r.evaluation_results.execution_match.precision.toFixed(2)}</td>
                  <td>{r.evaluation_results.execution_match.recall.toFixed(2)}</td>
                  <td>{r.evaluation_results.semantic_match.passed ? 'Pass' : 'Fail'}</td>
                  <td>
                    <span className={`badge ${r.passed ? 'badge-pass' : 'badge-fail'}`}>
                      {r.passed ? 'PASS' : 'FAIL'}
                    </span>
                  </td>
                  <td>{new Date(r.timestamp).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No evaluations yet for this test case.</p>
        )}
      </section>
    </div>
  )
}
