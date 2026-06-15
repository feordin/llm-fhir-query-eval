// Types for the static results-report JSON emitted by scripts/build_frontend_data.py

export interface TierStat {
  f1: number | null
  coverage: number | null
  by_prompt: Record<string, number | null>
}

export interface BestCombo {
  tier: number
  variant: string
  f1: number
}

export interface LeaderboardRow {
  model: string
  tiers: Record<string, TierStat> // "1" | "2" | "3"
  best?: BestCombo | null // best (tier, variant) over ALL test cases
}

export interface Leaderboard {
  models: string[]
  tiers: number[]
  rows: LeaderboardRow[]
  stamp: string
}

export interface PhenotypeRow {
  phenotype: string
  canonical_tc: string
  scores: Record<string, Record<string, number | null>> // model -> tier -> f1
}

export interface PhenotypeMatrix {
  phenotypes: PhenotypeRow[]
  models: string[]
}

export interface CellDetail {
  precision?: number
  recall?: number
  f1?: number | null
  passed?: boolean
  expected_count?: number
  actual_count?: number
  elapsed_sec?: number
  queries_generated?: number
  primary_query_url?: string
  additional_query_urls?: string[]
  raw_response?: string
  prompt_text?: string
  error?: string | null
  run_metadata?: {
    output_tokens?: number
    tool_calls_count?: number
    stop_reason?: string
    fallback_used?: boolean
  }
}

export interface TestCaseDetail {
  test_case: string
  grids: Record<string, Record<string, CellDetail>> // model -> "tier-variant" -> cell
}

export interface PhenotypeDetail {
  phenotype: string
  canonical_tc: string
  cases: TestCaseDetail[]
}

export interface ReportMeta {
  since: string
  stamp: string
  models: string[]
  excluded: string[]
  tier_labels: Record<string, string>
  prompt_labels: Record<string, string>
}

export const TIERS = ['1', '2', '3'] as const
export const VARIANTS = ['naive', 'broad', 'expert'] as const

// Short display label for a provider:model spec.
export function shortModel(spec: string): string {
  return spec.replace(/^copilot:/, '').replace(/^openai-compat:/, '')
}

// Canonical models (the main leaderboard) vs suffix-tagged baselines like
// '+fhirskill'. All four canonical models are now full-108 coverage.
export function isCanonicalModel(spec: string): boolean {
  return !spec.includes('+')
}
export function isSkillSpec(spec: string): boolean {
  return spec.includes('fhirskill')
}
