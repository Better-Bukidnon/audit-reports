import { useIndex } from './data';
import { useLang, useT } from './i18n';
import { Link, useRouter } from './router';
import { LANGS } from './strings';
import { THEMES, useTheme } from './theme';
import { cx, ui } from './ui';
import { ERROR_EMAIL } from './components/bits';
import { Home } from './pages/Home';
import { GovernmentPage } from './pages/Government';
import { Compare } from './pages/Compare';
import { About } from './pages/About';
import { DataPage } from './pages/DataPage';
import { NotFound } from './pages/NotFound';

const NAV = [
  { to: '/', key: 'navGovernments' },
  { to: '/compare', key: 'navCompare' },
  { to: '/about', key: 'navAbout' },
  { to: '/data', key: 'navData' },
] as const;

const topLink = 'text-ink-2 no-underline hover:text-accent';

const iconProps = {
  width: 13,
  height: 13,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round',
  'aria-hidden': true,
} as const;

function SunIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.06 1.06M11.54 11.54l1.06 1.06M3.4 12.6l1.06-1.06M11.54 4.46l1.06-1.06" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg {...iconProps}>
      <path d="M14 8.53A6 6 0 1 1 7.47 2 4.67 4.67 0 0 0 14 8.53z" strokeLinejoin="round" />
    </svg>
  );
}

function Page() {
  const { path } = useRouter();
  if (path === '/') return <Home />;
  if (path === '/compare') return <Compare />;
  if (path === '/about') return <About />;
  if (path === '/data') return <DataPage />;
  const m = /^\/([a-z0-9-]+)$/.exec(path);
  if (m) return <GovernmentPage slug={m[1]!} />;
  return <NotFound />;
}

/** The nav item a path belongs to: government pages sit under Governments. */
function section(path: string) {
  if (NAV.some((n) => n.to === path)) return path;
  return /^\/[a-z0-9-]+$/.test(path) ? '/' : null;
}

export function App() {
  const t = useT();
  const { lang, setLang } = useLang();
  const { theme, setTheme } = useTheme();
  const { path } = useRouter();
  const { data: index } = useIndex();
  const from = index ? Math.min(...index.years) : 2022;
  const to = index ? Math.max(...index.years) : 2024;
  const active = section(path);

  return (
    <>
      <a
        href="#main-content"
        className="absolute -top-12 left-2 z-[2000] bg-ink px-3.5 py-2 text-paper focus:top-2 focus:text-paper"
      >
        {t('skip')}
      </a>

      <header className="bg-paper">
        <div className="border-b border-rule-soft font-hero text-xs font-semibold">
          <div className={cx(ui.page, 'flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 py-1.5')}>
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1 md:gap-x-[18px]">
              <a className={topLink} href="https://betterbukidnon.org/" target="_blank" rel="noopener">
                Better Bukidnon <span aria-hidden="true">↗</span>
              </a>
              <a className={topLink} href="https://budget.betterbukidnon.org/" target="_blank" rel="noopener">
                {t('topBudget')} <span aria-hidden="true">↗</span>
              </a>
              <a className={topLink} href="https://infra.betterbukidnon.org/" target="_blank" rel="noopener">
                {t('topInfra')} <span aria-hidden="true">↗</span>
              </a>
            </span>
            <span className="flex items-stretch gap-2">
              <span className={ui.segmented} role="group" aria-label={t('themeLabel')}>
                {THEMES.map((th) => (
                  <button
                    key={th}
                    type="button"
                    className={ui.segmentedBtnIcon}
                    aria-pressed={th === theme}
                    aria-label={t(`theme_${th}`)}
                    title={t(`theme_${th}`)}
                    onClick={() => setTheme(th)}
                  >
                    {th === 'light' ? <SunIcon /> : <MoonIcon />}
                  </button>
                ))}
              </span>
              <span className={ui.segmented} role="group" aria-label={t('langLabel')}>
                {LANGS.map((l) => (
                  <button
                    key={l}
                    type="button"
                    lang={l}
                    className={ui.segmentedBtnSmall}
                    aria-pressed={l === lang}
                    onClick={() => setLang(l)}
                  >
                    {l.toUpperCase()}
                  </button>
                ))}
              </span>
            </span>
          </div>
        </div>

        <div
          className={cx(
            ui.page,
            'flex flex-col items-start gap-3 pt-[22px] pb-5 md:flex-row md:items-center md:justify-between md:gap-6',
          )}
        >
          <Link to="/" className="min-w-0 text-ink no-underline hover:text-ink">
            <span className={ui.kicker}>{t('kicker')}</span>
            <span className="block font-hero text-2xl leading-[1.05] font-bold tracking-[-0.025em] md:text-[28px]">
              {t('title')}
            </span>
          </Link>
          <a
            className="flex shrink-0 flex-row flex-wrap items-baseline gap-1.5 text-ink no-underline hover:text-accent md:flex-col md:items-end md:gap-0"
            href="https://www.coa.gov.ph/reports/annual-audit-reports/aar-local-government-units/"
            target="_blank"
            rel="noopener"
          >
            <span className={ui.label}>{t('reportsFrom')}</span>
            <span className="font-hero text-[15px] leading-[1.15] font-bold tracking-[-0.02em] md:text-[22px]">
              {t('coaName')}
            </span>
            <span className="text-xs text-ink-3">
              {t('coaSub')}, CY {from}–{to}
            </span>
          </a>
        </div>

        <nav className="bg-band" aria-label={t('navLabel')}>
          <div className={cx(ui.page, 'flex gap-7 overflow-x-auto [scrollbar-width:none]')}>
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                aria-current={active === n.to ? 'page' : undefined}
                className="inline-flex min-h-[46px] items-center border-b-[3px] border-transparent font-hero text-[15px] font-semibold whitespace-nowrap text-white/80 no-underline hover:text-white focus-visible:-outline-offset-2 focus-visible:outline-white aria-[current=page]:border-white aria-[current=page]:text-white"
              >
                {t(n.key)}
              </Link>
            ))}
          </div>
        </nav>
      </header>

      <main id="main-content" className="flex-1 pt-8 pb-[72px] focus:outline-none" tabIndex={-1}>
        <div className={ui.page}>
          <Page />
        </div>
      </main>

      <footer className="mt-auto border-t border-ink bg-paper-2">
        <div className={cx(ui.page, 'pt-7 pb-10')}>
          <p className="mb-5 font-mono text-[11px] tracking-[0.12em] text-ink-3 uppercase">
            {t('footSource', { from, to })}
            {index?.dataAsOf ? ` · ${t('footAsOf', { date: index.dataAsOf })}` : ''}
          </p>
          <ul className="grid grid-cols-1 gap-4 text-[13.5px] md:grid-cols-2 lg:grid-cols-4">
            <li className="flex min-w-0 flex-col gap-1 wrap-anywhere">
              <span className={ui.label}>{t('footSite')}</span>
              <span>
                {t('footRunBy')}{' '}
                <a href="https://betterbukidnon.org/" target="_blank" rel="noopener">
                  Better Bukidnon ↗
                </a>
              </span>
            </li>
            <li className="flex min-w-0 flex-col gap-1 wrap-anywhere">
              <span className={ui.label}>{t('footAlso')}</span>
              <a href="https://budget.betterbukidnon.org/" target="_blank" rel="noopener">
                budget.betterbukidnon.org ↗
              </a>
              <a href="https://infra.betterbukidnon.org/" target="_blank" rel="noopener">
                infra.betterbukidnon.org ↗
              </a>
            </li>
            <li className="flex min-w-0 flex-col gap-1 wrap-anywhere">
              <span className={ui.label}>{t('footReports')}</span>
              <a href="https://www.coa.gov.ph/reports/annual-audit-reports/" target="_blank" rel="noopener">
                coa.gov.ph ↗
              </a>
            </li>
            <li className="flex min-w-0 flex-col gap-1 wrap-anywhere">
              <span className={ui.label}>{t('footHelp')}</span>
              <a href={`mailto:${ERROR_EMAIL}`}>{ERROR_EMAIL}</a>
            </li>
          </ul>
          <p className="mt-6 mb-0 text-[12.5px] text-ink-3">{t('footDisclaimer')}</p>
        </div>
      </footer>
    </>
  );
}
