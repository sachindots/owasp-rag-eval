import { useEffect, useState } from 'react'
import { MOCK, listRuns } from '../api'
import { defenseNames, duration, pct } from '../format'
import type { AttackRun, GoldenRun, Run } from '../types'

export function Results() {
  const [runs, setRuns] = useState<Run[]>([])
  useEffect(() => {
    listRuns().then(setRuns)
  }, [])

  const golden = runs.filter((r): r is GoldenRun => r.suite === 'golden')
  const attacks = runs.filter((r): r is AttackRun => r.suite === 'attacks')

  return (
    <div className="page">
      <section className="ask-head">
        <h1>Evaluation register</h1>
        <p className="muted">
          Every number here is read from a results file a real run produced, on the held-out test
          split.
        </p>
        {MOCK && (
          <p className="notice notice-warn">
            These are placeholder numbers to show the layout. No run has produced them.
          </p>
        )}
      </section>

      <section className="table-block">
        <h2>Answer quality</h2>
        <p className="muted small">
          Golden set: answerable and unanswerable questions, graded by an LLM judge checked against
          human labels.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Defenses</th>
                <th>Model</th>
                <th className="num">n</th>
                <th className="num">Recall@5</th>
                <th className="num">MRR</th>
                <th className="num">Answer acc.</th>
                <th className="num">Refusal acc.</th>
                <th className="num">p95</th>
                <th>Results file</th>
              </tr>
            </thead>
            <tbody>
              {golden.map((r) => (
                <tr key={r.results}>
                  <td>{defenseNames(r.defenses)}</td>
                  <td><code>{r.model}</code></td>
                  <td className="num">{r.n}</td>
                  <td className="num">{pct(r.recall_at_5)}</td>
                  <td className="num">{r.mrr?.toFixed(2) ?? '—'}</td>
                  <td className="num">{pct(r.answer_accuracy)}</td>
                  <td className="num">{pct(r.refusal_accuracy)}</td>
                  <td className="num">{duration(r.p95_latency_ms)}</td>
                  <td><code className="muted">{r.results}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="table-block">
        <h2>Attack resistance</h2>
        <p className="muted small">
          Share of attacks that got what they wanted. Lower is better.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Defenses</th>
                <th className="num">n</th>
                <th className="bar-col">Attack success</th>
                <th className="num">Jailbreak</th>
                <th className="num">Indirect</th>
                <th className="num">Leak</th>
                <th className="num">Tool misuse</th>
                <th className="num">p95</th>
                <th>Results file</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((r) => (
                <tr key={r.results}>
                  <td>{defenseNames(r.defenses)}</td>
                  <td className="num">{r.n}</td>
                  <td className="bar-col">
                    <span className="bar">
                      <span style={{ width: pct(r.attack_success_rate) }} />
                    </span>
                    <span className="num">{pct(r.attack_success_rate)}</span>
                  </td>
                  <td className="num">{pct(r.by_category.direct_jailbreak)}</td>
                  <td className="num">{pct(r.by_category.indirect_injection)}</td>
                  <td className="num">{pct(r.by_category.prompt_leak)}</td>
                  <td className="num">{pct(r.by_category.tool_misuse)}</td>
                  <td className="num">{duration(r.p95_latency_ms)}</td>
                  <td><code className="muted">{r.results}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
