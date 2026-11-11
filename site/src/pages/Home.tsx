import { useState } from 'react';
import { useIndex } from '../data';
import { useT, useTitle } from '../i18n';
import { Link } from '../router';
import { count } from '../format';
import { cx, ui } from '../ui';
import { Loading, LoadError, VerdictBadge, verdictColor } from '../components/bits';
import { Place } from '../components/Place';
import { Stats } from '../components/Stats';
import type { GovernmentMeta } from '../types';

const GROUPS: GovernmentMeta['type'][] = ['Province', 'City', 'Municipality'];

/** "Impasugong", "impasug ong" and "Impasug-ong" all match. */
const fold = (s: string) => s.toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');

export function Home() {
  const t = useT();
  const { data, error } = useIndex();
  const [q, setQ] = useState('');
  useTitle(null);

  if (error) return <LoadError />;
  if (!data) return <Loading />;

  const latest = Math.max(...data.years);
  const from = Math.min(...data.years);
  const govs = data.governments;
  const findings = govs.reduce((n, g) => n + g.years[latest]!.findings, 0);
  const qualified = govs.filter((g) => g.years[latest]!.verdict === 'qualified').length;
  const shown = q.trim() ? govs.filter((g) => fold(g.name).includes(fold(q))) : govs;

  return (
    <>
      <div className={ui.pageHead}>
        <p className={ui.lede}>{t('homeLede')}</p>
      </div>

      <Stats
        items={[
          { label: t('statGovernments'), value: govs.length },
          { label: t('statReports'), value: govs.length * data.years.length, sub: t('statReportsSub', { from, to: latest }) },
          { label: t('statFindings', { year: latest }), value: count(findings), sub: t('statFindingsSub', { n: govs.length }) },
          { label: t('statQualified', { year: latest }), value: t('ofTotal', { n: qualified, total: govs.length }), accent: true },
        ]}
      />

      <section className={ui.section} aria-labelledby="find-h">
        <div className="flex flex-wrap items-baseline gap-x-[18px] gap-y-2">
          <label htmlFor="find" id="find-h" className={ui.sectionHFlush}>
            {t('findTown')}
          </label>
          <input
            id="find"
            type="search"
            autoComplete="off"
            placeholder={t('findTownPh')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="min-h-10 max-w-[420px] flex-[1_1_260px] rounded-none border border-ink bg-paper px-3 py-[7px] text-[15px] focus-visible:border-accent focus-visible:outline-offset-0"
          />
        </div>
        <p className="mt-3 text-[13.5px] text-ink-3">
          {t('homeLegend', { year: latest })} {t('homeVerdictNote')}{' '}
          <Link to="/about#verdict">{t('whatVerdictsMean')}</Link>
        </p>

        {shown.length === 0 && (
          <p className="mt-6 border-t border-rule py-8 text-ink-3">{t('noMatch', { q: q.trim() })}</p>
        )}

        {GROUPS.map((type) => {
          const list = shown.filter((g) => g.type === type);
          if (!list.length) return null;
          return (
            <div key={type} className="mt-7">
              <h2 className={cx(ui.label, 'mb-2.5 block')}>{t(`group_${type}`)}</h2>
              <ul className="grid grid-cols-1 gap-x-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {list.map((g) => {
                  const y = g.years[latest]!;
                  return (
                    <li key={g.slug} className="min-w-0 border-t-[3px] border-(--c)" style={verdictColor(y.verdict)}>
                      <Link
                        to={`/${g.slug}`}
                        className="group flex h-full flex-col gap-1.5 border-b border-rule-soft pt-3 pb-[18px] text-ink no-underline hover:bg-paper-2 hover:text-ink"
                      >
                        <span className="font-hero text-[19px] leading-tight font-bold tracking-[-0.015em] group-hover:text-accent">
                          {g.name}
                        </span>
                        <span className="text-xs text-ink-3">
                          <Place gov={g} />
                        </span>
                        <span className="flex items-center gap-2">
                          <span className={ui.label}>{t('cy', { year: latest })}</span>
                          <VerdictBadge verdict={y.verdict} />
                        </span>
                        <span className="text-[13px] text-ink-2">
                          {t('cardFindings', { n: y.findings })} · {t('cardRecs', { fully: y.recsFully, total: y.recsTotal })}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </section>
    </>
  );
}
