import { useIndex, useGovernment } from '../data';
import { useT, useTitle, type T } from '../i18n';
import { useRouter } from '../router';
import { count, fileSize, isRange, pageRange, percent, peso } from '../format';
import { cx, ui } from '../ui';
import {
  Amount,
  DataNote,
  ErrorLink,
  Loading,
  LoadError,
  Quote,
  Segmented,
  SourceLine,
  VerdictBadge,
  sourceWhere,
} from '../components/bits';
import { Place } from '../components/Place';
import { Stats } from '../components/Stats';
import { NotFound } from './NotFound';
import { FIGURE_KEYS, type Fund, type Government, type Source, type YearRecord } from '../types';

const isCombined = (fund: string) => fund !== 'General Fund' && fund !== 'Special Education Fund';

/** The General Fund, or COA's combined statement where it gives the funds together. */
const mainFund = (y: YearRecord) =>
  y.budget.find((b) => b.fund === 'General Fund') ?? y.budget.find((b) => isCombined(b.fund)) ?? null;

// Table cells
const colHead = cx(ui.th, ui.num);
const rowHead = cx(ui.td, ui.left, 'font-semibold');
const numCell = cx(ui.td, ui.num);
const blank = cx(ui.th, ui.left);

const block = 'mt-7 max-w-[900px] border-t border-rule pt-4';
const blockH = 'mb-3 flex items-baseline gap-2.5 text-lg';

export function GovernmentPage({ slug }: { slug: string }) {
  const t = useT();
  const { query, navigate } = useRouter();
  const { data: index, error: indexError } = useIndex();
  const known = index?.governments.some((g) => g.slug === slug) ?? false;
  const { data: gov, error } = useGovernment(known ? slug : null);
  useTitle(gov?.name ?? null);

  if (indexError || error) return <LoadError />;
  if (!index) return <Loading />;
  if (!known) return <NotFound />;
  if (!gov) return <Loading />;

  const years = [...index.years].sort((a, b) => a - b);
  const latest = years[years.length - 1]!;
  const asked = Number(query.get('cy'));
  const year = years.includes(asked) ? asked : latest;
  const setYear = (y: number) =>
    navigate(y === latest ? `/${slug}` : `/${slug}?cy=${y}`, { replace: true, keepScroll: true });
  const now = gov.years[latest]!;

  return (
    <>
      <div className={ui.pageHead}>
        <p className={ui.kicker}>
          <Place gov={gov} />
        </p>
        <h1 className={ui.h1}>{gov.name}</h1>
        <p className={ui.lede}>{t('govLede', { name: gov.name, from: years[0]!, to: latest })}</p>
      </div>

      <Reports gov={gov} years={years} />

      <h2 className={cx(ui.label, 'mt-7 block pb-2')}>{t('govGlance', { year: latest })}</h2>
      <Stats
        items={[
          { label: t('statVerdict'), value: <VerdictBadge verdict={now.verdict.verdict} large /> },
          { label: t('statFindingsGov'), value: now.findings.count },
          { label: t('statRecs'), value: t('ofTotal', { n: now.priorRecs.fully, total: now.priorRecs.total }) },
          { label: t('statDisallowances'), value: <Amount value={now.disallowances.disallowances} />, size: 'small' },
        ]}
      />

      <YearsSideBySide gov={gov} years={years} />
      <Statements gov={gov} years={years} />

      <section className={ui.section} id="detail" aria-labelledby="detail-h">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
          <h2 className={ui.sectionHFlush} id="detail-h">
            {t('govDetail')}
          </h2>
          <Segmented
            label={t('yearTabs')}
            options={[...years].reverse().map((y) => ({ value: y, label: t('cy', { year: y }) }))}
            value={year}
            onChange={setYear}
          />
        </div>
        <YearDetail gov={gov} y={gov.years[year]!} />
      </section>
    </>
  );
}

function Reports({ gov, years }: { gov: Government; years: number[] }) {
  const t = useT();
  return (
    <div className="flex flex-wrap items-baseline gap-x-[18px] gap-y-2 border-y border-rule py-2.5 text-[13.5px]">
      <span className={ui.label}>{t('govReports')}</span>
      <ul className="flex flex-wrap gap-x-6 gap-y-1">
        {[...years].reverse().map((y) => {
          const r = gov.years[y]!;
          return (
            <li key={y}>
              <span className="font-mono text-xs font-medium text-ink-2">{t('cy', { year: y })}</span>{' '}
              <a href={r.report.url} target="_blank" rel="noopener">
                {t('govReport')}{' '}
                <span className="text-xs text-ink-3">
                  ({r.report.format.toUpperCase()}, {fileSize(r.report.bytes)})
                </span>
                &nbsp;↗
              </a>
              {r.summary && (
                <>
                  {' · '}
                  <a href={r.summary.url} target="_blank" rel="noopener">
                    {t('govSummary')} <span className="text-xs text-ink-3">(PDF)</span>&nbsp;↗
                  </a>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function YearHeads({ years }: { years: number[] }) {
  const t = useT();
  return (
    <thead>
      <tr>
        <td className={blank} />
        {years.map((y) => (
          <th key={y} scope="col" className={colHead}>
            {t('cy', { year: y })}
          </th>
        ))}
      </tr>
    </thead>
  );
}

function YearsSideBySide({ gov, years }: { gov: Government; years: number[] }) {
  const t = useT();
  const at = (y: number) => gov.years[y]!;
  const anyCombined = years.some((y) => {
    const f = mainFund(at(y));
    return f !== null && isCombined(f.fund);
  });
  const row = (label: React.ReactNode, cell: (y: number) => React.ReactNode) => (
    <tr>
      <th scope="row" className={cx(rowHead, 'min-w-[150px] md:w-[34%]')}>
        {label}
      </th>
      {years.map((y) => (
        <td key={y} className={numCell}>
          {cell(y)}
        </td>
      ))}
    </tr>
  );

  return (
    <section className={ui.section} aria-labelledby="years-h">
      <h2 className={ui.sectionH} id="years-h">
        {t('govYears', { n: years.length })}
      </h2>
      <p className={ui.sectionNote}>{t('govYearsNote')}</p>
      <div className={ui.tableWrap}>
        <table className={ui.table}>
          <YearHeads years={years} />
          <tbody>
            {row(t('rowVerdict'), (y) => (
              <VerdictBadge verdict={at(y).verdict.verdict} />
            ))}
            {row(t('rowFindings'), (y) => count(at(y).findings.count))}
            {row(t('rowRecs'), (y) => t('ofTotal', { n: at(y).priorRecs.fully, total: at(y).priorRecs.total }))}
            {row(t('rowDisallowances'), (y) => (
              <Amount value={at(y).disallowances.disallowances} />
            ))}
            {row(t('rowSuspensions'), (y) => (
              <Amount value={at(y).disallowances.suspensions} />
            ))}
            {row(
              <>
                {t('rowMainFund')} <span className={ui.sub}>{t('ourArithmetic')}</span>
              </>,
              (y) => {
                const f = mainFund(at(y));
                return (
                  <>
                    {f?.share != null ? percent(f.share) : '—'}
                    {f && isCombined(f.fund) && <span title={t('combinedFunds')}>*</span>}
                  </>
                );
              },
            )}
          </tbody>
        </table>
      </div>
      {anyCombined && <p className="mt-2 text-[12.5px] text-ink-3">* {t('combinedFunds')}</p>}
    </section>
  );
}

function Statements({ gov, years }: { gov: Government; years: number[] }) {
  const t = useT();
  const corrections = years.flatMap((y) =>
    FIGURE_KEYS.flatMap((k) => {
      const f = gov.years[y]!.figures[k];
      return f.correction ? [{ y, k, note: f.correction }] : [];
    }),
  );

  return (
    <section className={ui.section} aria-labelledby="statements-h">
      <h2 className={ui.sectionH} id="statements-h">
        {t('govStatements')}
      </h2>
      <p className={ui.sectionNote}>{t('govStatementsNote')}</p>
      <div className={ui.tableWrap}>
        <table className={ui.table}>
          <YearHeads years={years} />
          <tbody>
            {FIGURE_KEYS.map((k) => (
              <tr key={k}>
                <th scope="row" className={cx(rowHead, 'min-w-[150px] md:w-[34%]')}>
                  {t(`fig_${k}`)}
                </th>
                {years.map((y) => {
                  const f = gov.years[y]!.figures[k];
                  return (
                    <td key={y} className={numCell}>
                      {peso(f.value)}
                      {f.correction && <span title={t('corrected')}> †</span>}
                      <PageLink t={t} source={f.source} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {corrections.map((c) => (
        <DataNote key={`${c.y}${c.k}`} kind="corrected">
          † {t('cy', { year: c.y })}, {t(`fig_${c.k}`)}: {c.note}
        </DataNote>
      ))}
    </section>
  );
}

/** A small link under a figure in a table: the page it comes from, linked to COA's file. */
function PageLink({ t, source }: { t: T; source: Source }) {
  const page = source.pages
    ? t(isRange(source.pages) ? 'pageMany' : 'pageOne', { p: pageRange(source.pages) })
    : source.pdfPage
      ? t('pagePdf', { p: source.pdfPage })
      : source.item;
  return (
    <a
      className="mt-0.5 block text-[11.5px] text-ink-3 no-underline hover:text-accent hover:underline"
      href={source.url}
      target="_blank"
      rel="noopener"
      title={sourceWhere(t, source)}
    >
      {page}&nbsp;↗
    </a>
  );
}

function YearDetail({ gov, y }: { gov: Government; y: YearRecord }) {
  const t = useT();
  const year = y.year;
  const name = gov.name;
  const recs = y.priorRecs;
  const statuses = (
    [
      ['recs_partially', recs.partially],
      ['recs_notImplemented', recs.notImplemented],
      ['recs_forImplementation', recs.forImplementation],
      ['recs_closed', recs.closed],
      ['recs_reiterated', recs.reiterated],
    ] as const
  ).filter(([, n]) => n !== null);

  return (
    <div>
      <section className={block} aria-labelledby="d-verdict">
        <h3 id="d-verdict" className={blockH}>
          {t('secVerdict')}
        </h3>
        <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <VerdictBadge verdict={y.verdict.verdict} /> {t(`verdictExplain_${y.verdict.verdict}`)}
        </p>
        <Quote>{y.verdict.quote}</Quote>
        <SourceLine source={y.verdict.source} year={year} name={name} what={t('secVerdict')} />
      </section>

      <section className={block} aria-labelledby="d-findings">
        <h3 id="d-findings" className={blockH}>
          {t('secFindings')} <span className="font-mono text-[13px] font-medium text-ink-3">{y.findings.count}</span>
        </h3>
        <p className="border-l-[3px] border-accent bg-accent-soft px-3.5 py-3 text-sm text-ink-2">
          {t('findingsNotProof')}
        </p>
        <p>{t('findingsCount', { n: y.findings.count })}</p>
        {y.findings.countNote && <DataNote kind="note">{y.findings.countNote}</DataNote>}
        {y.findings.numberedAfter && (
          <p className={ui.muted}>{t('findingsNumberedAfter', { numbers: pageRange(y.findings.numberedAfter) })}</p>
        )}
        <SourceLine source={y.findings.source} year={year} name={name} what={t('secFindings')} />
        <ol className="mt-4">
          {y.findings.items.map((f) => (
            <li key={f.number} className="border-t border-rule-soft py-3.5">
              <p className="mb-1.5 text-[12.5px] text-ink-3">
                <span className={ui.label}>{t('findingNo', { n: f.number })}</span>
                {f.source.pdfPage && (
                  <>
                    {' · '}
                    <a href={f.source.url} target="_blank" rel="noopener">
                      {t('pagePdf', { p: f.source.pdfPage })}&nbsp;↗
                    </a>
                  </>
                )}
                {' · '}
                <ErrorLink name={name} year={year} what={t('findingNo', { n: f.number })} />
              </p>
              <blockquote lang="en" className="text-[14.5px] leading-relaxed text-ink-2">
                {f.text}
              </blockquote>
            </li>
          ))}
        </ol>
      </section>

      <section className={block} aria-labelledby="d-recs">
        <h3 id="d-recs" className={blockH}>
          {t('secRecs')}
        </h3>
        <p className="font-hero text-2xl font-bold tracking-[-0.015em]">
          {t('recsHeadline', { fully: recs.fully, total: recs.total })}
        </p>
        {statuses.length > 0 && (
          <dl className="mb-3.5 max-w-[420px] border-t border-rule-soft">
            {statuses.map(([k, n]) => (
              <div key={k} className="flex justify-between gap-4 border-b border-rule-soft py-2">
                <dt>{t(k)}</dt>
                <dd className={ui.num}>{n}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className={ui.muted}>{t('recsHow')}</p>
        {recs.statedIn === 'Part III table, Total row' && <p className={ui.muted}>{t('recsFromTable')}</p>}
        {recs.statedIn === 'Part III status column, our count' && <p className={ui.muted}>{t('recsOurCount')}</p>}
        {recs.correction && <DataNote kind="corrected">{recs.correction}</DataNote>}
        {recs.quote && <Quote>{recs.quote}</Quote>}
        <SourceLine source={recs.source} year={year} name={name} what={t('secRecs')} />
      </section>

      <section className={block} aria-labelledby="d-dis">
        <h3 id="d-dis" className={blockH}>
          {t('secDisallowances')}
        </h3>
        <p>{t('disIntro', { year })}</p>
        <dl className="mb-3.5 border-t border-rule-soft">
          {(['disallowances', 'suspensions', 'charges'] as const).map((k) => (
            <div key={k} className="flex justify-between gap-4 border-b border-rule-soft py-2">
              <dt className="font-semibold">
                {t(`dis_${k}`)}
                <span className={ui.sub}>{t(`disHelp_${k}`)}</span>
              </dt>
              <dd className={cx(ui.num, 'text-base font-semibold')}>
                <Amount value={y.disallowances[k]} />
              </dd>
            </div>
          ))}
        </dl>
        {y.disallowances.note && <DataNote kind="note">{y.disallowances.note}</DataNote>}
        {y.disallowances.quote && <Quote>{y.disallowances.quote}</Quote>}
        <SourceLine source={y.disallowances.source} year={year} name={name} what={t('secDisallowances')} />
      </section>

      <section className={block} aria-labelledby="d-budget">
        <h3 id="d-budget" className={blockH}>
          {t('secBudget')}
        </h3>
        <p>{t('budgetIntro')}</p>
        <Budget funds={y.budget} />
        <p className={cx(ui.muted, 'mt-3')}>{t('budgetShareNote')}</p>
        {y.budget.map((f) => (
          <div key={f.fund}>
            {f.correction && (
              <DataNote kind="corrected">
                {f.fund}: {f.correction}
              </DataNote>
            )}
            {f.note && (
              <DataNote kind="note">
                {f.fund}: {f.note}
              </DataNote>
            )}
          </div>
        ))}
        {distinctSources(y.budget).map((s) => (
          <SourceLine key={`${s.item}${s.pages}${s.pdfPage}`} source={s} year={year} name={name} what={t('secBudget')} />
        ))}
      </section>
    </div>
  );
}

function Budget({ funds }: { funds: Fund[] }) {
  const t = useT();
  return (
    <div className={ui.tableWrap}>
      <table className={ui.table}>
        <thead>
          <tr>
            <th scope="col" className={cx(ui.th, ui.left)}>
              {t('colFund')}
            </th>
            <th scope="col" className={colHead}>
              {t('colFinal')}
            </th>
            <th scope="col" className={colHead}>
              {t('colObligations')}
            </th>
            <th scope="col" className={colHead}>
              {t('colShare')} <span className={ui.sub}>{t('ourArithmetic')}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {funds.map((f) => (
            <tr key={f.fund}>
              <th scope="row" lang="en" className={rowHead}>
                {f.fund}
              </th>
              <td className={numCell}>{peso(f.final)}</td>
              <td className={numCell}>
                {peso(f.obligations)}
                {f.correction && <span title={t('corrected')}> †</span>}
              </td>
              <td className={numCell}>
                {f.share !== null ? percent(f.share) : <span className="text-xs text-ink-3">{t('noShare')}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function distinctSources(funds: Fund[]): Source[] {
  const seen = new Map<string, Source>();
  for (const f of funds) {
    const s = f.source;
    seen.set(`${s.url}|${s.item}|${s.pages}|${s.pdfPage}`, s);
  }
  return [...seen.values()];
}
