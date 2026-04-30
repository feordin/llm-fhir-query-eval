import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchResult, fetchTestCase } from '../api/client'

export default function EvaluationDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: result, isLoading: resultLoading } = useQuery({
    queryKey: ['result', id],
    queryFn: () => fetchResult(id!),
    enabled: !!id,
  })

  const { data: testCase } = useQuery({
    queryKey: ['test-case', result?.test_case_id],
    queryFn: () => fetchTestCase(result!.test_case_id),
    enabled: !!result?.test_case_id,
  })

  if (resultLoading) return <div className="loading">Loading...</div>
  if (!result) return <div className="error">Evaluation not found</div>

  const exec = result.evaluation_results.execution_match
  const semantic = result.evaluation_results.semantic_match

  return (
    <div className="detail-page">
      <Link to={`/test-cases/${result.test_case_id}`} className="back-link">
        &larr; Back to {testCase?.name || result.test_case_id}
      </Link>

      <div className="detail-header">
        <h1>{testCase?.name || result.test_case_id}</h1>
        <div className="detail-meta">
          <span className="badge">{result.model}</span>
          <span className="badge">{result.mcp_enabled ? 'Agentic (MCP)' : 'Closed Book'}</span>
          <span className={`badge ${result.passed ? 'badge-pass' : 'badge-fail'}`}>
            {result.passed ? 'PASS' : 'FAIL'}
          </span>
        </div>
      </div>

      <div className="eval-grid">
        <section className="detail-section">
          <h2>Score Breakdown</h2>
          <div className="score-breakdown">
            <div className="score-row">
              <span>Overall</span>
              <div className="score-bar-container">
                <div
                  className={`score-bar ${result.passed ? 'bar-pass' : 'bar-fail'}`}
                  style={{ width: `${result.overall_score * 100}%` }}
                />
              </div>
              <strong>{result.overall_score.toFixed(2)}</strong>
            </div>
            <div className="score-row">
              <span>Execution F1</span>
              <div className="score-bar-container">
                <div className="score-bar" style={{ width: `${exec.f1_score * 100}%` }} />
              </div>
              <strong>{exec.f1_score.toFixed(2)}</strong>
            </div>
            <div className="score-row">
              <span>Precision</span>
              <div className="score-bar-container">
                <div className="score-bar" style={{ width: `${exec.precision * 100}%` }} />
              </div>
              <strong>{exec.precision.toFixed(2)}</strong>
            </div>
            <div className="score-row">
              <span>Recall</span>
              <div className="score-bar-container">
                <div className="score-bar" style={{ width: `${exec.recall * 100}%` }} />
              </div>
              <strong>{exec.recall.toFixed(2)}</strong>
            </div>
            <div className="score-row">
              <span>Semantic</span>
              <span className={semantic.passed ? 'score-pass' : 'score-fail'}>
                {semantic.passed ? 'Pass' : 'Fail'}
              </span>
            </div>
            <div className="score-row">
              <span>Resource Type</span>
              <span className={semantic.resource_type_match ? 'score-pass' : 'score-fail'}>
                {semantic.resource_type_match ? 'Match' : 'Mismatch'}
              </span>
            </div>
            <div className="score-row">
              <span>Parameters</span>
              <span className={semantic.parameters_match ? 'score-pass' : 'score-fail'}>
                {semantic.parameters_match ? 'Match' : 'Mismatch'}
              </span>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h2>Query Comparison</h2>
          {testCase && (
            <div className="query-compare">
              <div>
                <h3>Expected</h3>
                <code className="query-display">{testCase.expected_query.url}</code>
              </div>
              <div>
                <h3>Generated</h3>
                <code className="query-display query-generated">
                  {result.generated_query.parsed_query.url}
                </code>
              </div>
              {result.generated_query.additional_queries.length > 0 && (
                <div>
                  <h3>Additional Queries</h3>
                  {result.generated_query.additional_queries.map((q, i) => (
                    <code key={i} className="query-display query-generated">{q.url}</code>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      <section className="detail-section">
        <h2>Raw LLM Response</h2>
        <pre className="raw-response">{result.generated_query.raw_response}</pre>
      </section>

      <section className="detail-section">
        <h2>Execution Details</h2>
        <div className="exec-details">
          <p>
            Expected: <strong>{exec.expected_count}</strong> results
            {' | '}
            Actual: <strong>{exec.actual_count}</strong> results
          </p>
          {exec.expected_ids.length > 0 && exec.actual_ids.length > 0 && (
            <div className="id-comparison">
              <div>
                <h4>Missing IDs ({exec.expected_ids.filter(id => !exec.actual_ids.includes(id)).length})</h4>
                <div className="id-list">
                  {exec.expected_ids.filter(eid => !exec.actual_ids.includes(eid)).map(eid => (
                    <span key={eid} className="id-tag id-missing">{eid}</span>
                  ))}
                </div>
              </div>
              <div>
                <h4>Extra IDs ({exec.actual_ids.filter(id => !exec.expected_ids.includes(id)).length})</h4>
                <div className="id-list">
                  {exec.actual_ids.filter(aid => !exec.expected_ids.includes(aid)).map(aid => (
                    <span key={aid} className="id-tag id-extra">{aid}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {semantic.differences.length > 0 && (
        <section className="detail-section">
          <h2>Semantic Differences</h2>
          <ul className="diff-list">
            {semantic.differences.map((diff, i) => (
              <li key={i}>{diff}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
