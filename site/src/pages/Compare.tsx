import { useState } from 'react';
import { useIndex } from '../data';
import { useT, useTitle } from '../i18n';
import { Link, useRouter } from '../router';
import { percent } from '../format';
import { cx, ui } from '../ui';
import { Amount, Dash, Loading, LoadError, Segmented, VerdictBadge } from '../components/bits';
import type { Key } from '../strings';
import type { Index, Verdict } from '../types';

type Row = Index['governments'][number];
type Col = 'name' | 'verdict' | 'findings' | 'recs' | 'recsShare' | 'disallowances' | 'suspensions' | 'mainFund';

// Sorting by verdict groups them in the order COA's standards list them; it isn't a ranking.
const VERDICT_ORDER: Verdict[] = ['unmodified', 'qualified', 'adverse', 'disclaimer'];

const COLS: { col: Col; key: Key; num: boolean; ours?: boolean }[] = [
  { col: 'name', key: 'colGovernment', num: false },
  { col: 'verdict', key: 'colVerdict', num: false },
  { col: 'findings', key: 'colFindings', num: true },
  { col: 'recs', key: 'colRecs', num: true },
  { col: 'recsShare', key: 'colRecsShare', num: true, ours: true },
  { col: 'disallowances', key: 'colDisallowances', num: true },
  { col: 'suspensions', key: 'colSuspensions', num: true },
  { col: 'mainFund', key: 'colMainFund', num: true, ours: true },
];

const isCombined = (fund: string) => fund !== 'General Fund';
const numCell = cx(ui.td, ui.num);

export function Compare() {
  const t = useT();
  const { query, navigate } = useRouter();
  const { data, error } = useIndex();
  const [sort, setSort] = useState<{ col: Col; dir: 1 | -1 }>({ col: 'name', dir: 1 });
  useTitle(t('cmpTitle'));

  if (error) return <LoadError />;
  if (!data) return <Loading />;

  const years = [...data.years].sort((a, b) => b - a);
  const asked = Number(query.get('cy'));
  const year = years.includes(asked) ? asked : years[0]!;
  const setYear = (y: number) =>
    navigate(y === years[0] ? '/compare' : `/compare?cy=${y}`, { replace: true, keepScroll: true });

  const value = (g: Row, col: Col): number | string | null => {
    const y = g.years[year]!;
    switch (col) {
      case 'name':
        return g.name;
      case 'verdict':
        return VERDICT_ORDER.indexOf(y.verdict);
      case 'findings':
        return y.findings;
      case 'recs':
        return y.recsFully;
      case 'recsShare':
        return y.recsTotal ? y.recsFully / y.recsTotal : null;
      case 'disallowances':
        return y.disallowances;
      case 'suspensions':
        return y.suspensions;
      case 'mainFund':
        return y.mainFund?.share ?? null;
    }
  };

  // Missing values always sort last, whichever way the column is sorted.
  const rows = [...data.governments].sort((a, b) => {
    const va = value(a, sort.col);
    const vb = value(b, sort.col);
    if (va === null || vb === null) return va === vb ? a.name.localeCompare(b.name) : va === null ? 1 : -1;
    const c = typeof va === 'string' ? va.localeCompare(vb as string) : va - (vb as number);
    return c * sort.dir || a.name.localeCompare(b.name);
  });

  const toggle = (col: Col) =>
    setSort((s) => (s.col === col ? { col, dir: s.dir === 1 ? -1 : 1 } : { col, dir: col === 'name' ? 1 : -1 }));

  return (
    <>
      <div className={ui.pageHead}>
        <h1 className={ui.h1}>{t('cmpTitle')}</h1>
        <p className={ui.lede}>{t('cmpLede')}</p>
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Segmented
          label={t('yearTabs')}
          options={years.map((y) => ({ value: y, label: t('cy', { year: y }) }))}
          value={year}
          onChange={setYear}
        />
        <Link className={ui.btn} to="/data#downloads">
          {t('cmpDownload')}
        </Link>
      </div>

      <div className={ui.tableWrap}>
        <table className={ui.table}>
          <thead>
            <tr>
              {COLS.map(({ col, key, num, ours }) => (
                <th
                  key={col}
                  scope="col"
                  className={cx(ui.thSort, 'min-w-24', num ? ui.numWrap : ui.left)}
                  aria-sort={sort.col === col ? (sort.dir === 1 ? 'ascending' : 'descending') : undefined}
                >
                  <button
                    type="button"
                    onClick={() => toggle(col)}
                    title={t('sortBy', { col: t(key) })}
                    className={cx(
                      'flex w-full flex-col border-0 bg-transparent py-2.5 uppercase hover:text-ink',
                      col === 'name' ? 'pr-3.5 pl-0' : 'px-3.5',
                      num ? 'items-end text-right' : 'items-start text-left',
                    )}
                  >
                    {t(key)}
                    {ours && <span className={ui.sub}>{t('ourArithmetic')}</span>}
                    <span className="min-h-[1em] text-[9px]" aria-hidden="true">
                      {sort.col === col ? (sort.dir === 1 ? '▲' : '▼') : ''}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((g) => {
              const y = g.years[year]!;
              return (
                <tr key={g.slug}>
                  <th scope="row" className={cx(ui.td, ui.left, 'font-semibold whitespace-nowrap')}>
                    <Link to={year === years[0] ? `/${g.slug}` : `/${g.slug}?cy=${year}`}>{g.name}</Link>
                  </th>
                  <td className={cx(ui.td, ui.left)}>
                    <VerdictBadge verdict={y.verdict} />
                  </td>
                  <td className={numCell}>{y.findings}</td>
                  <td className={numCell}>{t('ofTotal', { n: y.recsFully, total: y.recsTotal })}</td>
                  <td className={numCell}>
                    {y.recsTotal ? percent((100 * y.recsFully) / y.recsTotal) : <Dash />}
                  </td>
                  <td className={numCell}>
                    <Amount value={y.disallowances} />
                  </td>
                  <td className={numCell}>
                    <Amount value={y.suspensions} />
                  </td>
                  <td className={numCell}>
                    {y.mainFund?.share != null ? percent(y.mainFund.share) : <Dash />}
                    {y.mainFund && isCombined(y.mainFund.fund) && '*'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <section className="mt-5 max-w-[820px] text-[13.5px] text-ink-2" aria-labelledby="cmp-notes-h">
        <h2 className={ui.label} id="cmp-notes-h">
          {t('cmpNotes')}
        </h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-[18px]">
          <li>{t('cmpNoteRecs')}</li>
          <li>{t('cmpNoteFund')}</li>
          <li>{t('cmpNoteDash')}</li>
        </ul>
      </section>
    </>
  );
}
