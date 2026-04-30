import axios from 'axios'
import type { DashboardData, EvaluationResult, TestCase } from '../types'

const api = axios.create({
  baseURL: '/api',
})

// Test Cases
export async function fetchTestCases(): Promise<TestCase[]> {
  const { data } = await api.get<TestCase[]>('/test-cases')
  return data
}

export async function fetchTestCase(id: string): Promise<TestCase> {
  const { data } = await api.get<TestCase>(`/test-cases/${id}`)
  return data
}

// Results
export async function fetchResults(params?: {
  test_case_id?: string
  model?: string
  mcp_enabled?: boolean
  passed?: boolean
}): Promise<EvaluationResult[]> {
  const { data } = await api.get<EvaluationResult[]>('/results', { params })
  return data
}

export async function fetchResult(evaluationId: string): Promise<EvaluationResult> {
  const { data } = await api.get<EvaluationResult>(`/results/${evaluationId}`)
  return data
}

// Dashboard
export async function fetchDashboard(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>('/results/dashboard')
  return data
}
