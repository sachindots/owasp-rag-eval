// Mirrors src/owasp_rag/schemas.py. Change both together.

export type Chunk = {
  id: string
  doc: string
  heading: string
  text: string
  trusted: boolean
}

export type Defenses = {
  spotlight: boolean
  classifier: boolean
  tool_confirmation: boolean
}

export type ToolStatus = 'executed' | 'blocked' | 'pending_confirmation'

export type ToolCall = {
  name: string
  arguments: Record<string, unknown>
  status: ToolStatus
}

// One row per retrieved chunk: where it ranked in each search and what the classifier made of it.
// Planted attack chunks have no search ranks.
export type RetrievalHit = {
  id: string
  dense_rank: number | null
  keyword_rank: number | null
  rrf_score: number | null
  injection_score: number | null
  dropped: boolean
}

export type Answer = {
  text: string
  refused: boolean
  citations: string[]
  retrieved: Chunk[]
  retrieval: RetrievalHit[]
  tool_calls: ToolCall[]
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
}

export type AttackCategory = 'direct_jailbreak' | 'indirect_injection' | 'prompt_leak' | 'tool_misuse'

export type SuccessCriterion =
  | { kind: 'tool_executed'; tool: string }
  | { kind: 'canary_leaked' }
  | { kind: 'output_contains'; text: string }

export type AttackItem = {
  id: string
  category: AttackCategory
  question: string
  injected_document: string | null
  success_if: SuccessCriterion
}

export type AttackResult = {
  item_id: string
  category: AttackCategory
  answer: Answer
  succeeded: boolean
}

// The summary dicts that `python -m owasp_rag.evals` prints, one per results file.
type RunBase = {
  results: string
  model: string
  defenses: Defenses
  n: number
  p50_latency_ms: number
  p95_latency_ms: number
  cost_per_1k_queries_usd: number
}

export type GoldenRun = RunBase & {
  suite: 'golden'
  recall_at_5: number | null
  mrr: number | null
  answer_accuracy: number | null
  refusal_accuracy: number | null
}

export type AttackRun = RunBase & {
  suite: 'attacks'
  attack_success_rate: number | null
  by_category: Partial<Record<AttackCategory, number | null>>
}

export type Run = GoldenRun | AttackRun
