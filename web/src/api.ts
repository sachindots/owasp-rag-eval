import { ATTACKS, RUNS, sampleAnswer, sampleAttackResult } from './fixtures'
import type { Answer, AttackItem, AttackResult, Defenses, Run } from './types'

// shortcut: serves fixtures while the backend is being built; replace each body with a fetch to
// the FastAPI routes once they exist, then delete fixtures.ts and the MOCK flag.
export const MOCK = true

const delay = <T>(value: T, ms = 900): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms))

export async function ask(question: string, _defenses: Defenses): Promise<Answer> {
  const started = performance.now()
  const answer = await delay(sampleAnswer(question), 1100)
  return { ...answer, latency_ms: performance.now() - started }
}

export async function listAttacks(): Promise<AttackItem[]> {
  return delay(ATTACKS, 150)
}

export async function runAttack(item: AttackItem, defenses: Defenses): Promise<AttackResult> {
  return delay(sampleAttackResult(item, defenses), 1300)
}

export async function listRuns(): Promise<Run[]> {
  return delay(RUNS, 150)
}
