import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchPhenotypeDetail } from '../data/reportClient'
import { TIERS, VARIANTS, shortModel, type CellDetail } from '../data/reportTypes'

const TIER_LABEL: Record<string, string> = { '1': 'T1', '2': 'T2', '3': 'T3' }

function cellClass(f1: number | null | undefined): string {
  if (f1 == null) return 'score-none'
  if (f1 >= 0.9) return 'score-pass'
  if (f1 >= 0.6) return 'score-mid'
  return 'score-fail'
}

function CellModal({ cell, label, onClose }: { cell: CellDetail; label: string; onClose: () => void }) {
  const rm = cell.run_metadata
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{label}</h3>
          <button onClick={onClose}>×</button>
        </div>
        {cell.error ? (
          <p className="error">Error: {cell.error}</p>
        ) : (
          <>
            <div className="metric-row">
              <span>P <strong>{cell.precision?.toFixed(3)}</strong></span>
              <span>R <strong>{cell.recall?.toFixed(3)}</strong></span>
              <span>F1 <strong>{cell.f1?.toFixed(3)}</strong></span>
              <span>expected <strong>{cell.expected_count}</strong></span>
              <span>found <strong>{cell.actual_count}</strong></span>
              <span>{cell.elapsed_sec}s</span>
              {rm?.tool_calls_count != null && <span>{rm.tool_calls_count} tool calls</span>}
              {rm?.output_tokens != null && <span>{rm.output_tokens} tok</span>}
            </div>
            <h4>Prompt</h4>
            <pre className="detail-block">{cell.prompt_text}</pre>
            <h4>Generated query</h4>
            <pre className="detail-block">{cell.primary_query_url}
              {cell.additional_query_urls?.map(u => '\n' + u).join('')}</pre>
            <h4>Raw response</h4>
            <pre className="detail-block detail-scroll">{cell.raw_response}</pre>
          </>
        )}
      </div>
    </div>
  )
}

export default function PhenotypeDetail() {
  const { id = '' } = useParams()
  const { data, isLoading, error } = useQuery({
    queryKey: ['phenotype', id], queryFn: () => fetchPhenotypeDetail(id),
  })
  const [modal, setModal] = useState<{ cell: CellDetail; label: string } | null>(null)

  if (isLoading) return <div className="loading">Loading {id}…</div>
  if (error) return <div className="error">Error: {(error as Error).message}</div>
  if (!data) return null

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <Link to="/phenotypes">← Phenotype matrix</Link>
        <h1>{data.phenotype}</h1>
        <p className="subtitle">All-patients case: <code>{data.canonical_tc}</code>. Each grid is
          prompt × tier (F1) per model — click a cell for the query, raw response, counts, and effort.</p>
      </div>

      {data.cases.map(tc => (
        <div key={tc.test_case} style={{ marginBottom: 28 }}>
          <h3><code>{tc.test_case}</code></h3>
          <div className="grid-row">
            {Object.entries(tc.grids).map(([model, grid]) => (
              <div key={model} className="grid-card">
                <div className="grid-model">{shortModel(model)}</div>
                <table className="mini-grid">
                  <thead>
                    <tr><th></th>{TIERS.map(t => <th key={t}>{TIER_LABEL[t]}</th>)}</tr>
                  </thead>
                  <tbody>
                    {VARIANTS.map(v => (
                      <tr key={v}>
                        <td className="grid-rowlabel">{v}</td>
                        {TIERS.map(t => {
                          const cell = grid[`${t}-${v}`]
                          return (
                            <td key={t}
                                className={`mini-cell ${cellClass(cell?.f1)}`}
                                onClick={() => cell && setModal({ cell, label: `${shortModel(model)} · T${t} · ${v}` })}
                                style={{ cursor: cell ? 'pointer' : 'default' }}>
                              {cell?.f1 == null ? '—' : cell.f1.toFixed(2)}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>
      ))}

      {modal && <CellModal cell={modal.cell} label={modal.label} onClose={() => setModal(null)} />}
    </div>
  )
}
