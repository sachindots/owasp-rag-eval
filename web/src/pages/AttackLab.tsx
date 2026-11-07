import { useEffect, useState } from 'react'
import { listAttacks, runAttack } from '../api'
import { CitedText, DefenseToggles, Pill, RetrievalDrawer, Stamp } from '../components'
import { NO_DEFENSES, defenseNames } from '../format'
import type { AttackCategory, AttackItem, AttackResult, Defenses, SuccessCriterion } from '../types'

const CATEGORY: Record<AttackCategory, string> = {
  direct_jailbreak: 'Direct jailbreak',
  indirect_injection: 'Indirect injection',
  prompt_leak: 'Prompt leak',
  tool_misuse: 'Tool misuse',
}

function criterion(c: SuccessCriterion): string {
  switch (c.kind) {
    case 'tool_executed':
      return `${c.tool} is executed`
    case 'canary_leaked':
      return 'the system prompt canary appears in the answer'
    case 'output_contains':
      return `the answer contains "${c.text}"`
  }
}

type Pair = { baseline: AttackResult; defended: AttackResult }

export function AttackLab() {
  const [attacks, setAttacks] = useState<AttackItem[]>([])
  const [selected, setSelected] = useState<AttackItem | null>(null)
  const [defenses, setDefenses] = useState<Defenses>({
    spotlight: true,
    classifier: true,
    tool_confirmation: true,
  })
  const [pair, setPair] = useState<Pair | null>(null)
  const [running, setRunning] = useState(false)
  const [inspect, setInspect] = useState<AttackResult | null>(null)

  useEffect(() => {
    listAttacks().then((items) => {
      setAttacks(items)
      setSelected(items[0] ?? null)
    })
  }, [])

  function choose(item: AttackItem) {
    setSelected(item)
    setPair(null)
  }

  async function run() {
    if (!selected) return
    setRunning(true)
    const [baseline, defended] = await Promise.all([
      runAttack(selected, NO_DEFENSES),
      runAttack(selected, defenses),
    ])
    setPair({ baseline, defended })
    setRunning(false)
  }

  const groups = (Object.keys(CATEGORY) as AttackCategory[])
    .map((cat) => [cat, attacks.filter((a) => a.category === cat)] as const)
    .filter(([, items]) => items.length)

  return (
    <div className="page lab">
      <nav className="lab-list" aria-label="Attacks">
        <p className="label">Case files · {attacks.length}</p>
        {groups.map(([cat, items]) => (
          <div key={cat} className="lab-group">
            <p className="lab-group-title">{CATEGORY[cat]}</p>
            {items.map((a) => (
              <button
                key={a.id}
                type="button"
                className={`lab-item${selected?.id === a.id ? ' is-active' : ''}`}
                aria-current={selected?.id === a.id}
                onClick={() => choose(a)}
              >
                <code>{a.id}</code>
                <span>{a.question}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>

      {selected && (
        <div className="lab-main">
          <header className="lab-head">
            <div>
              <p className="label">
                File <code>{selected.id}</code> · {CATEGORY[selected.category]}
              </p>
              <h1>{selected.question}</h1>
            </div>
          </header>

          {selected.injected_document && (
            <div className="planted">
              <p className="label">Exhibit · planted document · untrusted</p>
              <pre>{selected.injected_document}</pre>
            </div>
          )}
          <p className="criterion">
            <span className="label">Succeeds if</span> {criterion(selected.success_if)}
          </p>

          <div className="lab-controls">
            <DefenseToggles value={defenses} onChange={setDefenses} />
            <button className="btn btn-primary" type="button" onClick={run} disabled={running}>
              {running ? 'Running…' : 'Run both'}
            </button>
          </div>

          {pair && (
            <div className="compare">
              {(
                [
                  ['No defenses', pair.baseline],
                  [defenseNames(defenses), pair.defended],
                ] as const
              ).map(([title, r]) => (
                <section key={title} className={`outcome ${r.succeeded ? 'is-bad' : 'is-good'}`}>
                  <header>
                    <h2>{title}</h2>
                    <Stamp tone={r.succeeded ? 'danger' : 'ok'}>
                      {r.succeeded ? 'Compromised' : 'Blocked'}
                    </Stamp>
                  </header>
                  <dl>
                    <dt>Tool calls</dt>
                    <dd>
                      {r.answer.tool_calls.length
                        ? r.answer.tool_calls.map((t, i) => (
                            <div key={i} className="tool">
                              <code>{t.name}</code>
                              <code className="muted">{JSON.stringify(t.arguments)}</code>
                              <Pill tone={t.status === 'executed' ? 'danger' : 'warn'}>
                                {t.status.replace('_', ' ')}
                              </Pill>
                            </div>
                          ))
                        : 'None'}
                    </dd>
                    {r.answer.retrieval
                      .filter((h) => h.id.startsWith('injected#'))
                      .map((h) => (
                        <div key={h.id}>
                          <dt>Planted chunk</dt>
                          <dd>
                            {h.dropped ? (
                              <>
                                <span className="redact-bar" aria-hidden="true" />
                                Redacted by the classifier at {h.injection_score?.toFixed(2)}, never
                                reached the prompt
                              </>
                            ) : (
                              'Reached the prompt'
                            )}
                          </dd>
                        </div>
                      ))}
                    <dt>Answer</dt>
                    <dd className="outcome-answer">
                      <CitedText
                        text={r.answer.text}
                        citations={r.answer.citations}
                        active={null}
                        onActivate={() => {}}
                      />
                    </dd>
                  </dl>
                  <button type="button" className="link" onClick={() => setInspect(r)}>
                    Inspect retrieval ({r.answer.retrieved.length})
                  </button>
                </section>
              ))}
            </div>
          )}
        </div>
      )}

      {inspect && <RetrievalDrawer answer={inspect.answer} onClose={() => setInspect(null)} />}
    </div>
  )
}
