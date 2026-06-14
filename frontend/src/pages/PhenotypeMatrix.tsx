import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchPhenotypeMatrix } from '../data/reportClient'
import { shortModel, isCanonicalModel, type PhenotypeRow } from '../data/reportTypes'

const TIER_LABEL: Record<string, string> = { '1': 'T1 closed-book', '2': 'T2 +tools', '3': 'T3 +methodology' }

function scoreClass(f1: number | null): string {
  if (f1 == null) return 'score-none'
  if (f1 >= 0.9) return 'score-pass'
  if (f1 >= 0.6) return 'score-mid'
  return 'score-fail'
}

export default function PhenotypeMatrix() {
  const { data, isLoading, error } = useQuery({ queryKey: ['phenotypes'], queryFn: fetchPhenotypeMatrix })
  const [tier, setTier] = useState('2')
  const [q, setQ] = useState('')

  const models = useMemo(() => (data?.models ?? []).filter(isCanonicalModel), [data])
  const rows = useMemo(() => {
    if (!data) return []
    return data.phenotypes.filter((p: PhenotypeRow) => !q || p.phenotype.includes(q.toLowerCase()))
  }, [data, q])

  if (isLoading) return <div className="loading">Loading phenotypes…</div>
  if (error) return <div className="error">Error: {(error as Error).message}</div>
  if (!data) return null

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Phenotype Matrix</h1>
        <p className="subtitle">
          Comprehensive-cohort F1 per phenotype × model, averaged over the three prompts.
          Click a phenotype for the full prompt × tier grids and cell detail.
        </p>
      </div>

      <div className="filters">
        <input className="filter-search" placeholder="Search phenotypes…"
               value={q} onChange={e => setQ(e.target.value)} />
        <select value={tier} onChange={e => setTier(e.target.value)}>
          {['1', '2', '3'].map(t => <option key={t} value={t}>{TIER_LABEL[t]}</option>)}
        </select>
      </div>

      <div className="table-container">
        <table className="score-table">
          <thead>
            <tr>
              <th className="col-name">Phenotype</th>
              {models.map(m => <th key={m} className="col-score">{shortModel(m)}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map(p => (
              <tr key={p.phenotype}>
                <td className="cell-name">
                  <Link to={`/phenotypes/${p.phenotype}`}>{p.phenotype}</Link>
                </td>
                {models.map(m => {
                  const f1 = p.scores[m]?.[tier] ?? null
                  return (
                    <td key={m} className={`score-cell ${scoreClass(f1)}`}>
                      {f1 == null ? '—' : f1.toFixed(2)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-footer">{rows.length} of {data.phenotypes.length} phenotypes · {TIER_LABEL[tier]}</div>
    </div>
  )
}
