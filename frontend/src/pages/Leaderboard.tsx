import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { fetchLeaderboard } from '../data/reportClient'
import {
  TIERS, shortModel, isFullCoverageModel,
  type LeaderboardRow,
} from '../data/reportTypes'

const TIER_LABEL: Record<string, string> = {
  '1': 'T1 closed-book', '2': 'T2 agentic+tools', '3': 'T3 +methodology',
}
const TIER_COLOR: Record<string, string> = { '1': '#94a3b8', '2': '#3b82f6', '3': '#8b5cf6' }

function fmt(x: number | null | undefined) {
  return x == null ? '—' : x.toFixed(3)
}

function LeaderTable({ rows }: { rows: LeaderboardRow[] }) {
  return (
    <table className="score-table">
      <thead>
        <tr>
          <th className="col-name">Model</th>
          {TIERS.map(t => <th key={t} className="col-score">{TIER_LABEL[t]}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map(r => {
          const best = Math.max(...TIERS.map(t => r.tiers[t]?.f1 ?? -1))
          return (
            <tr key={r.model}>
              <td className="cell-name">{shortModel(r.model)}</td>
              {TIERS.map(t => {
                const s = r.tiers[t]
                const isBest = s?.f1 != null && s.f1 === best
                return (
                  <td key={t} className="score-cell" style={isBest ? { fontWeight: 700 } : undefined}>
                    {fmt(s?.f1)}
                    {s?.coverage != null && (
                      <span className="mode-indicator" title="coverage">
                        {' '}{Math.round(s.coverage * 100)}%
                      </span>
                    )}
                  </td>
                )
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default function Leaderboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['leaderboard'], queryFn: fetchLeaderboard })
  if (isLoading) return <div className="loading">Loading leaderboard…</div>
  if (error) return <div className="error">Error: {(error as Error).message}</div>
  if (!data) return null

  const full = data.rows.filter(r => isFullCoverageModel(r.model))
  const opus = data.rows.filter(r => !isFullCoverageModel(r.model))

  const chartData = full.map(r => ({
    model: shortModel(r.model),
    T1: r.tiers['1']?.f1 ?? null,
    T2: r.tiers['2']?.f1 ?? null,
    T3: r.tiers['3']?.f1 ?? null,
  }))

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>All-up F1 Leaderboard</h1>
        <p className="subtitle">
          Mean F1 on each phenotype's <strong>all-patients (comprehensive)</strong> cohort —
          the high-level comparison: <em>does the model find the whole cohort?</em> Rows are the
          three full-coverage (108-phenotype) models.
        </p>
      </div>

      <div className="table-container">
        <LeaderTable rows={full} />
      </div>

      <div style={{ height: 360, marginTop: 24 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="model" />
            <YAxis domain={[0, 1]} />
            <Tooltip formatter={(v: number) => v?.toFixed(3)} />
            <Legend />
            {TIERS.map(t => (
              <Bar key={t} dataKey={`T${t}`} name={TIER_LABEL[t]} fill={TIER_COLOR[t]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {opus.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h2>Opus skill baseline <span className="badge badge-multi">8-phenotype subset</span></h2>
          <p className="subtitle">
            Best off-the-shelf vs our methodology. <code>+fhirskill</code> = closed-book Opus with
            Anthropic's FHIR skill (no tools); plain Opus T1 = frontier one-shot; Opus T2 = our
            agentic stack. (Subset only — not comparable to the 108-phenotype rows above.)
          </p>
          <div className="table-container">
            <LeaderTable rows={opus} />
          </div>
        </div>
      )}

      <div className="table-footer">Generated {data.stamp}</div>
    </div>
  )
}
