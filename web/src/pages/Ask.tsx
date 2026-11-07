import { useState, type FormEvent } from 'react'
import { ask } from '../api'
import { CitedText, DefenseToggles, Pill, RetrievalDrawer, SourceCard } from '../components'
import { NO_DEFENSES, defenseNames, duration } from '../format'
import { EXAMPLE_QUESTIONS } from '../fixtures'
import type { Answer, Defenses } from '../types'

export function Ask() {
  const [question, setQuestion] = useState('')
  const [defenses, setDefenses] = useState<Defenses>(NO_DEFENSES)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [asked, setAsked] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<string | null>(null)
  const [inspecting, setInspecting] = useState(false)

  async function submit(q: string) {
    const text = q.trim()
    if (!text || loading) return
    setQuestion(text)
    setLoading(true)
    setError(null)
    try {
      setAnswer(await ask(text, defenses))
      setAsked(text)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The request failed.')
    } finally {
      setLoading(false)
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit(question)
  }

  const sources = answer
    ? answer.citations
        .map((id) => answer.retrieved.find((c) => c.id === id))
        .filter((c) => c !== undefined)
    : []

  return (
    <div className="page">
      <section className="ask-head">
        <h1>Ask the cheat sheets</h1>
        <p className="muted">
          Answers come only from the OWASP Cheat Sheet Series, with every claim linked to the passage
          it came from.
        </p>
        <form className="ask-form" onSubmit={onSubmit}>
          <input
            className="ask-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="How should I store user passwords?"
            maxLength={2000}
            aria-label="Question"
            autoFocus
          />
          <button className="btn btn-primary" type="submit" disabled={loading || !question.trim()}>
            {loading ? 'Searching…' : 'Ask'}
          </button>
        </form>
        <div className="ask-options">
          <DefenseToggles value={defenses} onChange={setDefenses} />
          <div className="examples">
            <span className="label">Try</span>
            {EXAMPLE_QUESTIONS.map((q) => (
              <button key={q} type="button" className="link" onClick={() => submit(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      </section>

      {error && <div className="notice notice-danger">{error}</div>}

      {loading && (
        <section className="result" aria-busy="true">
          <div className="skeleton">
            <span style={{ width: '92%' }} />
            <span style={{ width: '86%' }} />
            <span style={{ width: '64%' }} />
          </div>
        </section>
      )}

      {!loading && answer && (
        <section className="result">
          <div className="result-main">
            <p className="label">Answer</p>
            <p className="question">{asked}</p>
            {answer.refused ? (
              <div className="refusal">
                <p className="refusal-title">Not covered by the cheat sheets</p>
                <p>{answer.text}</p>
              </div>
            ) : (
              <CitedText
                text={answer.text}
                citations={answer.citations}
                active={active}
                onActivate={setActive}
              />
            )}
            <div className="meta">
              <span>{duration(answer.latency_ms)}</span>
              <span>
                {answer.prompt_tokens.toLocaleString()} in · {answer.completion_tokens} out tokens
              </span>
              <span>{defenseNames(defenses)}</span>
              <button type="button" className="link" onClick={() => setInspecting(true)}>
                Inspect retrieval ({answer.retrieved.length})
              </button>
            </div>
            {answer.tool_calls.length > 0 && (
              <div className="tool-list">
                {answer.tool_calls.map((t, i) => (
                  <div key={i} className="tool">
                    <code>{t.name}</code>
                    <code className="muted">{JSON.stringify(t.arguments)}</code>
                    <Pill tone={t.status === 'executed' ? 'danger' : 'warn'}>
                      {t.status.replace('_', ' ')}
                    </Pill>
                  </div>
                ))}
              </div>
            )}
          </div>
          <aside className="result-side" aria-label="Sources">
            <p className="label">Sources</p>
            {sources.length ? (
              sources.map((c, i) => (
                <SourceCard key={c.id} n={i + 1} chunk={c} active={active === c.id} />
              ))
            ) : (
              <p className="muted small">
                Nothing cited. The closest passages are in the retrieval view.
              </p>
            )}
          </aside>
        </section>
      )}

      {!loading && !answer && !error && (
        <section className="empty">
          <p className="muted">
            137 cheat sheets, split along their headings and searched two ways at once: by meaning
            and by keyword.
          </p>
        </section>
      )}

      {inspecting && answer && (
        <RetrievalDrawer answer={answer} onClose={() => setInspecting(false)} />
      )}
    </div>
  )
}
