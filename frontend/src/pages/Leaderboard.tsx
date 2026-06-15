import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { fetchLeaderboard } from '../data/reportClient'
import {
  TIERS, VARIANTS, shortModel, isCanonicalModel, isSkillSpec,
  type Leaderboard as LB, type LeaderboardRow,
} from '../data/reportTypes'

const TIER_LABEL: Record<string, string> = {
  '1': 'T1 closed-book', '2': 'T2 agentic+tools', '3': 'T3 +methodology',
}
const TIER_COLOR: Record<string, string> = { '1': '#94a3b8', '2': '#3b82f6', '3': '#8b5cf6' }

const fmt = (x: number | null | undefined) => (x == null ? '—' : x.toFixed(3))

// green→red heat color for an F1 in [0,1]
function heat(f1: number | null | undefined): string {
  if (f1 == null) return '#f1f3f5'
  const h = Math.max(0, Math.min(120, f1 * 120)) // 0=red,120=green
  return `hsl(${h} 65% 88%)`
}

function getRow(data: LB, pred: (m: string) => boolean) {
  return data.rows.find(r => pred(r.model))
}

// ---- "What moves the needle?" lever-impact hero (Opus controlled subset) ----
function ImpactHero({ data }: { data: LB }) {
  const plain = getRow(data, m => m === 'copilot:claude-opus-4.7')
  const skill = getRow(data, m => m.includes('opus') && m.includes('fhirskill'))
  if (!plain) return null
  const base = plain.tiers['1']?.f1
  const naive = plain.tiers['1']?.by_prompt?.naive
  const expert = plain.tiers['1']?.by_prompt?.expert
  const levers = [
    { label: 'Better prompt (naive → expert)', delta: (expert != null && naive != null) ? expert - naive : null },
    { label: '+ Anthropic FHIR skill', delta: (skill?.tiers['1']?.f1 != null && base != null) ? skill.tiers['1'].f1! - base : null },
    { label: '+ our agentic tools (T2)', delta: (plain.tiers['2']?.f1 != null && base != null) ? plain.tiers['2'].f1! - base : null },
  ]
  const max = Math.max(0.12, ...levers.map(l => Math.abs(l.delta ?? 0)))
  return (
    <div className="impact-hero">
      <h2>What moves the needle?</h2>
      <p className="subtitle">F1 lift from the same Opus baseline ({fmt(base)}) across all 108
        phenotypes (comprehensive cohort) — isolating each lever. <strong>Only tools matter for a frontier model.</strong></p>
      {levers.map(l => (
        <div key={l.label} className="lever">
          <div className="lever-label">{l.label}</div>
          <div className="lever-track">
            <div className="lever-bar" style={{
              width: `${(Math.abs(l.delta ?? 0) / max) * 100}%`,
              background: (l.delta ?? 0) >= 0.03 ? '#3b82f6' : '#cbd5e1',
            }} />
          </div>
          <div className="lever-val">{l.delta == null ? '—' : (l.delta >= 0 ? '+' : '') + l.delta.toFixed(3)}</div>
        </div>
      ))}
    </div>
  )
}

// ---- 2D prompt × tier heatmap per model ------------------------------------
function Heatmap({ rows }: { rows: LeaderboardRow[] }) {
  return (
    <div className="grid-row">
      {rows.map(r => (
        <div key={r.model} className="grid-card">
          <div className="grid-model">{shortModel(r.model)}</div>
          <table className="mini-grid">
            <thead><tr><th></th>{TIERS.map(t => <th key={t}>T{t}</th>)}</tr></thead>
            <tbody>
              {VARIANTS.map(v => (
                <tr key={v}>
                  <td className="grid-rowlabel">{v}</td>
                  {TIERS.map(t => {
                    const f1 = r.tiers[t]?.by_prompt?.[v]
                    return <td key={t} className="mini-cell" style={{ background: heat(f1) }}>
                      {f1 == null ? '—' : f1.toFixed(2)}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

function LeaderTable({ rows }: { rows: LeaderboardRow[] }) {
  return (
    <table className="score-table">
      <thead>
        <tr><th className="col-name">Model</th>{TIERS.map(t => <th key={t} className="col-score">{TIER_LABEL[t]}</th>)}</tr>
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
                    {s?.coverage != null && <span className="mode-indicator" title="coverage"> {Math.round(s.coverage * 100)}%</span>}
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

// ---- Best achievable per model (best tier × prompt, all test cases) --------
const TIER_SHORT: Record<number, string> = { 1: 'T1 closed-book', 2: 'T2 tools', 3: 'T3 +methodology' }
function BestAchievable({ rows }: { rows: LeaderboardRow[] }) {
  const withBest = rows.filter(r => r.best).sort((a, b) => b.best!.f1 - a.best!.f1)
  if (!withBest.length) return null
  const max = Math.max(...withBest.map(r => r.best!.f1))
  return (
    <div style={{ marginTop: 32 }}>
      <h2>Best achievable per model
        <span className="badge badge-multi"> best tier × prompt · all 388 test cases</span></h2>
      <p className="subtitle">Each model's <strong>ceiling</strong> — its single best tier+prompt
        combination, averaged over all 108 phenotypes (Slide 14 was the prompt-<em>average</em>; this is
        the best cell). Frontier models peak at <strong>tools + an expert prompt</strong> (~0.90); the small
        open model needs the full stack (methodology + expert) to approach them.</p>
      <div className="table-container">
        <table className="score-table">
          <thead><tr>
            <th className="col-name">Model</th><th className="col-score">Best config</th>
            <th className="col-score">Best F1</th><th></th>
          </tr></thead>
          <tbody>
            {withBest.map(r => (
              <tr key={r.model}>
                <td className="cell-name">{shortModel(r.model)}</td>
                <td className="score-cell">{TIER_SHORT[r.best!.tier]} · {r.best!.variant}</td>
                <td className="score-cell" style={{ fontWeight: 700 }}>{r.best!.f1.toFixed(3)}</td>
                <td className="score-cell" style={{ width: '38%' }}>
                  <div className="lever-track">
                    <div className="lever-bar" style={{ width: `${(r.best!.f1 / max) * 100}%`, background: '#3b82f6' }} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---- Off-the-shelf skill vs our agentic stack (Opus, by prompt) ------------
function SkillBaseline({ data }: { data: LB }) {
  const plain = getRow(data, m => m === 'copilot:claude-opus-4.7')
  const skill = getRow(data, m => isSkillSpec(m) && m.includes('opus'))
  if (!plain || !skill) return null
  const rows = [
    { label: 'Opus closed-book (no skill)', t: plain.tiers['1'] },
    { label: 'Opus + Anthropic FHIR skill (closed-book, no tools)', t: skill.tiers['1'] },
    { label: 'Opus + our agentic tools (T2)', t: plain.tiers['2'] },
  ]
  return (
    <div style={{ marginTop: 32 }}>
      <h2>Off-the-shelf skill vs our agentic stack
        <span className="badge badge-multi"> Opus · comprehensive cohort · full 108</span></h2>
      <p className="subtitle"><code>+fhirskill</code> = closed-book Opus + Anthropic's published
        FHIR-developer skill (prepended text, no tools). The skill barely helps a model that already
        knows FHIR — and helps least on the expert prompt; the win is the agentic <strong>tools</strong>.</p>
      <div className="table-container">
        <table className="score-table">
          <thead><tr><th className="col-name">Configuration</th>
            {VARIANTS.map(v => <th key={v} className="col-score">{v}</th>)}
            <th className="col-score">overall</th></tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.label}>
                <td className="cell-name">{r.label}</td>
                {VARIANTS.map(v => (
                  <td key={v} className="score-cell" style={{ background: heat(r.t?.by_prompt?.[v]) }}>
                    {fmt(r.t?.by_prompt?.[v])}</td>
                ))}
                <td className="score-cell" style={{ fontWeight: 700 }}>{fmt(r.t?.f1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Leaderboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['leaderboard'], queryFn: fetchLeaderboard })
  if (isLoading) return <div className="loading">Loading leaderboard…</div>
  if (error) return <div className="error">Error: {(error as Error).message}</div>
  if (!data) return null

  const full = data.rows.filter(r => isCanonicalModel(r.model))
  const chartData = full.map(r => ({
    model: shortModel(r.model),
    T1: r.tiers['1']?.f1 ?? null, T2: r.tiers['2']?.f1 ?? null, T3: r.tiers['3']?.f1 ?? null,
  }))

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>FHIR Cohort-Finding: Model Comparison</h1>
        <p className="subtitle">All-up F1 on each phenotype's <strong>all-patients</strong> cohort —
          <em>does the model find the whole cohort?</em></p>
      </div>

      <ImpactHero data={data} />

      <h2 style={{ marginTop: 28 }}>Prompt × tier, per model</h2>
      <p className="subtitle">Rows = prompt sophistication, columns = capability tier. Watch the rows
        <strong> converge</strong> as you move right: tools make the prompt matter less. For qwen the
        gradient runs both ways — a weak model needs both.</p>
      <Heatmap rows={full} />

      <h2 style={{ marginTop: 28 }}>All-up leaderboard (full 108 phenotypes)</h2>
      <div className="table-container"><LeaderTable rows={full} /></div>

      <div style={{ height: 340, marginTop: 16 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="model" /><YAxis domain={[0, 1]} />
            <Tooltip formatter={(v: number) => v?.toFixed(3)} /><Legend />
            {TIERS.map(t => <Bar key={t} dataKey={`T${t}`} name={TIER_LABEL[t]} fill={TIER_COLOR[t]} />)}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <BestAchievable rows={full} />

      <SkillBaseline data={data} />

      <div className="table-footer">Generated {data.stamp}</div>
    </div>
  )
}
