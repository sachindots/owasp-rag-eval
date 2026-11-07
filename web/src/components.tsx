import { useEffect, type ReactNode } from 'react'
import { DEFENSE_LABELS, docTitle, headingTail, plain, sourceUrl } from './format'
import type { Answer, Chunk, Defenses } from './types'

export function DefenseToggles({
  value,
  onChange,
}: {
  value: Defenses
  onChange: (d: Defenses) => void
}) {
  return (
    <fieldset className="defenses">
      <legend>Defenses</legend>
      {(Object.keys(DEFENSE_LABELS) as (keyof Defenses)[]).map((key) => (
        <label key={key} className="toggle" title={DEFENSE_LABELS[key][1]}>
          <input
            type="checkbox"
            checked={value[key]}
            onChange={(e) => onChange({ ...value, [key]: e.target.checked })}
          />
          <span>{DEFENSE_LABELS[key][0]}</span>
        </label>
      ))}
    </fieldset>
  )
}

type Tone = 'ok' | 'danger' | 'warn' | 'neutral'

export function Stamp({ tone, children }: { tone: 'ok' | 'danger' | 'neutral'; children: ReactNode }) {
  return <span className={`stamp stamp-${tone}`}>{children}</span>
}

export function Pill({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

const CITE = /\[([^[\]]+#\d+)\]/g

export function CitedText({
  text,
  citations,
  active,
  onActivate,
}: {
  text: string
  citations: string[]
  active: string | null
  onActivate: (id: string | null) => void
}) {
  return (
    <div className="prose">
      {text.split(/\n{2,}/).map((para, i) => (
        <p key={i}>
          {para.split(CITE).map((part, j) => {
            // Markers sit flush against the word they cite, like footnotes.
            if (j % 2 === 0) return part.replace(/\s+$/, '')
            const n = citations.indexOf(part) + 1
            if (n === 0) return null
            return (
              <button
                key={j}
                type="button"
                className={`cite${active === part ? ' is-active' : ''}`}
                onMouseEnter={() => onActivate(part)}
                onMouseLeave={() => onActivate(null)}
                onFocus={() => onActivate(part)}
                onBlur={() => onActivate(null)}
                onClick={() => document.getElementById(`src-${n}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })}
                aria-label={`Source ${n}`}
              >
                {n}
              </button>
            )
          })}
        </p>
      ))}
    </div>
  )
}

export function SourceCard({ n, chunk, active }: { n: number; chunk: Chunk; active: boolean }) {
  const tail = headingTail(chunk.heading)
  return (
    <article id={`src-${n}`} className={`source${active ? ' is-active' : ''}`}>
      <header>
        <span className="source-n">EX.{String(n).padStart(2, '0')}</span>
        <div className="source-title">
          <a href={sourceUrl(chunk.doc)} target="_blank" rel="noreferrer">
            {docTitle(chunk.doc)}
          </a>
          {tail && <span className="source-path">{tail}</span>}
        </div>
      </header>
      <p className="source-text">{plain(chunk.text)}</p>
      <code className="source-id">{chunk.id}</code>
    </article>
  )
}

export function RetrievalDrawer({ answer, onClose }: { answer: Answer; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const hits = new Map(answer.retrieval.map((h) => [h.id, h]))
  const rank = (r: number | null) => (r == null ? '—' : r)

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="drawer-head">
          <div>
            <h2 id="drawer-title">Retrieval log</h2>
            <p className="muted">
              Dense and keyword results fused with reciprocal rank fusion (k = 60). Lower rank is better.
            </p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">
            Close
          </button>
        </header>
        <div className="hits" role="table" aria-label="Retrieved chunks">
          <div className="hit hit-head" role="row">
            <span role="columnheader">#</span>
            <span role="columnheader">Chunk</span>
            <span role="columnheader">Dense</span>
            <span role="columnheader">Keyword</span>
            <span role="columnheader">RRF</span>
          </div>
          {answer.retrieved.map((c, i) => {
            const h = hits.get(c.id)
            const cited = answer.citations.includes(c.id)
            return (
              <div key={c.id} className={`hit${h?.dropped ? ' is-dropped' : ''}`} role="row">
                <span className="num" role="cell">
                  {i + 1}
                </span>
                <span className="hit-chunk" role="cell">
                  <span className="hit-title">
                    <span className={h?.dropped ? 'redact' : undefined}>{docTitle(c.doc)}</span>
                    {cited && <Pill>cited</Pill>}
                    {!c.trusted && <Pill tone="warn">untrusted</Pill>}
                    {h?.dropped && <Pill tone="danger">redacted · {h.injection_score?.toFixed(2)}</Pill>}
                  </span>
                  <span className="source-path">{headingTail(c.heading) || '—'}</span>
                  <code className="source-id">{c.id}</code>
                </span>
                <span className="num" role="cell" data-label="Dense">
                  {rank(h?.dense_rank ?? null)}
                </span>
                <span className="num" role="cell" data-label="Keyword">
                  {rank(h?.keyword_rank ?? null)}
                </span>
                <span className="num" role="cell" data-label="RRF">
                  {h?.rrf_score == null ? '—' : h.rrf_score.toFixed(4)}
                </span>
              </div>
            )
          })}
        </div>
      </aside>
    </div>
  )
}
