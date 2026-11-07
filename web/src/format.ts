import type { Defenses } from './types'

export const NO_DEFENSES: Defenses = { spotlight: false, classifier: false, tool_confirmation: false }

export const DEFENSE_LABELS: Record<keyof Defenses, [string, string]> = {
  spotlight: ['Spotlighting', 'Marks retrieved text so the model treats it as data, not instructions'],
  classifier: ['Injection classifier', 'Drops chunks and questions that Prompt Guard 2 flags'],
  tool_confirmation: ['Tool confirmation', 'Side-effect tools wait for a person to confirm'],
}

export function docTitle(doc: string): string {
  if (doc === 'injected') return 'Planted document'
  return doc.replace(/_Cheat_Sheet$/, '').replaceAll('_', ' ')
}

export function headingTail(heading: string): string {
  return heading.split(' > ').slice(1).join(' › ')
}

export function sourceUrl(doc: string): string {
  return `https://cheatsheetseries.owasp.org/cheatsheets/${doc}.html`
}

// Cheat sheet markdown shown as plain prose: keep link text and emphasis content, drop the syntax.
export function plain(markdown: string): string {
  return markdown
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^- /gm, '• ')
}

export const pct = (x: number | null | undefined) => (x == null ? '—' : `${Math.round(x * 100)}%`)

export const duration = (ms: number) => (ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`)

export function defenseNames(d: Defenses): string {
  const on = (Object.keys(DEFENSE_LABELS) as (keyof Defenses)[]).filter((k) => d[k])
  if (on.length === 3) return 'All defenses'
  return on.length ? on.map((k) => DEFENSE_LABELS[k][0]).join(' + ') : 'No defenses'
}
