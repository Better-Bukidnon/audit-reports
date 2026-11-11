import { useIndex } from '../data';
import { useT, useTitle, type T } from '../i18n';
import { Link } from '../router';
import { peso } from '../format';
import { cx, ui } from '../ui';
import { ERROR_EMAIL, Loading, LoadError } from '../components/bits';
import { STRINGS, type Key } from '../strings';

/** "csv/sources/coa-aar-2024-files.csv" → the dl_ string that describes it. */
function describe(t: T, path: string): string {
  const m = /coa-aar-(\d{4})-files\.csv$/.exec(path);
  if (m) return t('dl_sources', { year: m[1]! });
  const key = `dl_${path.replace(/^csv\//, '').replace(/\.csv$/, '')}`;
  return key in STRINGS.en ? t(key as Key) : '';
}

/** The figure a correction is to, in words; the raw name if there's no label for it yet. */
function figureLabel(t: T, figure: string): string {
  const key = `corr_${figure}`;
  return key in STRINGS.en ? t(key as Key) : figure;
}

/** Corrected counts are whole numbers; corrected amounts are pesos; empty clears a count. */
function shown(v: string): string {
  if (v === '') return '—';
  return /^\d+$/.test(v) ? v : peso(Number(v));
}

const th = cx(ui.th, ui.left);
const thNum = cx(ui.th, ui.num);
const td = cx(ui.td, ui.left);
const tdNum = cx(ui.td, ui.num);

export function DataPage() {
  const t = useT();
  const { data, error } = useIndex();
  useTitle(t('dataTitle'));

  if (error) return <LoadError />;
  if (!data) return <Loading />;

  const [beforeEmail, afterEmail] = t('dataErrorP', { email: '\u0000' }).split('\u0000');

  return (
    <>
      <div className={ui.pageHead}>
        <h1 className={ui.h1}>{t('dataTitle')}</h1>
        <p className={ui.lede}>{t('dataLede')}</p>
      </div>

      <section className={ui.section} id="downloads" aria-labelledby="downloads-h">
        <h2 className={ui.sectionH} id="downloads-h">
          {t('dataDownloadsH')}
        </h2>
        <div className={ui.tableWrap}>
          <table className={ui.table}>
            <thead>
              <tr>
                <th scope="col" className={th}>
                  {t('colFile')}
                </th>
                <th scope="col" className={th}>
                  {t('colWhat')}
                </th>
                <th scope="col" className={thNum}>
                  {t('colRows')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.downloads.map((d) => (
                <tr key={d.path}>
                  <th scope="row" className={cx(td, 'font-mono text-[12.5px] font-normal')}>
                    <a href={`/data/${d.path}`} download>
                      {d.path.replace(/^csv\//, '')}
                    </a>
                  </th>
                  <td className={td}>{describe(t, d.path)}</td>
                  <td className={tdNum}>{d.rows.toLocaleString('en-PH')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className={cx(ui.sectionNote, 'mt-3')}>{t('dataSourcesP')}</p>
      </section>

      <section className={ui.section} id="corrections" aria-labelledby="corrections-h">
        <h2 className={ui.sectionH} id="corrections-h">
          {t('dataCorrectionsH')}
        </h2>
        <p className={ui.sectionNote}>{t('dataCorrectionsP')}</p>
        <div className={ui.tableWrap}>
          <table className={ui.table}>
            <thead>
              <tr>
                <th scope="col" className={th}>
                  {t('colDate')}
                </th>
                <th scope="col" className={th}>
                  {t('colReport')}
                </th>
                <th scope="col" className={th}>
                  {t('colFigure')}
                </th>
                <th scope="col" className={thNum}>
                  {t('colPrinted')}
                </th>
                <th scope="col" className={thNum}>
                  {t('colShown')}
                </th>
                <th scope="col" className={th}>
                  {t('colWhy')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.corrections.map((c) => (
                <tr key={`${c.year}${c.slug}${c.figure}`}>
                  <td className={cx(td, 'font-mono text-[12.5px] whitespace-nowrap')}>{c.date}</td>
                  <td className={cx(td, 'whitespace-nowrap')}>
                    <Link to={`/${c.slug}?cy=${c.year}`}>
                      {c.name} {t('cy', { year: c.year })}
                    </Link>
                  </td>
                  <td className={cx(td, 'min-w-40')}>{figureLabel(t, c.figure)}</td>
                  <td className={tdNum} lang="en">
                    {c.printed || '—'}
                  </td>
                  <td className={tdNum}>{shown(c.corrected)}</td>
                  <td className={cx(td, 'min-w-80 text-[13px] text-ink-2')} lang="en">
                    {c.note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={ui.section} id="report-error" aria-labelledby="error-h">
        <h2 className={ui.sectionH} id="error-h">
          {t('dataErrorH')}
        </h2>
        <p className={ui.sectionNote}>
          {beforeEmail}
          <a href={`mailto:${ERROR_EMAIL}`}>{ERROR_EMAIL}</a>
          {afterEmail}
        </p>
      </section>
    </>
  );
}
