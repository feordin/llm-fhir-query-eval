// Fetch the static report JSON (emitted by scripts/build_frontend_data.py).
// Served from frontend/public/data/ at /data/* by Vite.
import type {
  Leaderboard, PhenotypeMatrix, PhenotypeDetail, ReportMeta,
} from './reportTypes'

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchLeaderboard = () => getJSON<Leaderboard>('/data/leaderboard.json')
export const fetchPhenotypeMatrix = () => getJSON<PhenotypeMatrix>('/data/phenotypes.json')
export const fetchReportMeta = () => getJSON<ReportMeta>('/data/meta.json')
export const fetchPhenotypeDetail = (phenotype: string) =>
  getJSON<PhenotypeDetail>(`/data/phenotypes/${phenotype}.json`)
