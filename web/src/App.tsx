import { useEffect, useState } from 'react'
import { MOCK } from './api'
import { Ask } from './pages/Ask'
import { AttackLab } from './pages/AttackLab'
import { Results } from './pages/Results'

const PAGES = {
  '#/ask': ['Ask', Ask],
  '#/attacks': ['Attack lab', AttackLab],
  '#/results': ['Results', Results],
} as const

type Route = keyof typeof PAGES

const current = (): Route => (location.hash in PAGES ? (location.hash as Route) : '#/ask')

export default function App() {
  const [route, setRoute] = useState<Route>(current)
  useEffect(() => {
    const onHash = () => setRoute(current())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const Page = PAGES[route][1]
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="wordmark" href="#/ask">
            Cheat Sheet Desk
          </a>
          <nav className="tabs" aria-label="Pages">
            {(Object.keys(PAGES) as Route[]).map((r) => (
              <a key={r} href={r} className="tab" aria-current={r === route ? 'page' : undefined}>
                {PAGES[r][0]}
              </a>
            ))}
          </nav>
          {MOCK && <span className="mock-tag" title="Sample data, not from a real run">Sample data</span>}
        </div>
      </header>
      <main>
        <Page />
      </main>
      <footer className="footer">
        An unofficial study project. Answers draw on the{' '}
        <a href="https://github.com/OWASP/CheatSheetSeries" target="_blank" rel="noreferrer">
          OWASP Cheat Sheet Series
        </a>
        , © OWASP Foundation, CC BY-SA 4.0.
      </footer>
    </>
  )
}
