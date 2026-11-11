import type { CSSProperties, ReactNode } from 'react';
import { useT, type T } from '../i18n';
import { isRange, pageRange, peso } from '../format';
import { cx, ui } from '../ui';
import type { Source, Verdict } from '../types';

export const ERROR_EMAIL = 'volunteer@betterbukidnon.org';

/** Sets --c to a verdict's color, for text-(--c), bg-(--c) and border-(--c). */
export const verdictColor = (v: Verdict) => ({ '--c': `var(--color-v-${v})` }) as CSSProperties;

export function VerdictBadge({ verdict, large = false }: { verdict: Verdict; large?: boolean }) {
  const t = useT();
  return (
    <span
      style={verdictColor(verdict)}
      className={cx(
        "inline-flex items-center whitespace-nowrap font-semibold text-(--c) before:shrink-0 before:rounded-full before:bg-(--c) before:content-['']",
        large
          ? 'gap-2.5 font-hero text-xl before:size-3 md:text-[26px]'
          : 'gap-1.5 text-[13px] before:size-2',
      )}
    >
      {t(`verdict_${verdict}`)}
    </span>
  );
}

/** An amount in pesos, or a dash where the report doesn't give it (data rule 4). */
export function Amount({ value }: { value: number | null }) {
  if (value === null) return <Dash />;
  return <>{peso(value)}</>;
}

export function Dash() {
  const t = useT();
  return (
    <span className="text-ink-3" title={t('notGiven')}>
      —<span className="sr-only"> {t('notGiven')}</span>
    </span>
  );
}

/** COA's words, quoted. */
export function Quote({ children }: { children: ReactNode }) {
  const t = useT();
  return (
    <figure className="my-3.5 border-l-2 border-rule py-0.5 pl-4">
      <figcaption className={cx(ui.label, 'mb-1 block')}>{t('coaWords')}</figcaption>
      <blockquote lang="en" className="text-[14.5px] leading-relaxed text-ink-2">
        {children}
      </blockquote>
    </figure>
  );
}

/** A note from the data (in English, as written in the CSVs). */
export function DataNote({ kind, children }: { kind: 'note' | 'corrected'; children: ReactNode }) {
  const t = useT();
  return (
    <p className="text-[13px] text-ink-2">
      <span className={cx(kind === 'corrected' ? ui.labelAccent : ui.label, 'mr-1')}>
        {t(kind === 'corrected' ? 'corrected' : 'note')}
      </span>{' '}
      <span lang="en">{children}</span>
    </p>
  );
}

/** "Part I · Statement of Financial Position · p. 6". The part is left out for the executive summary PDF, which the link already names. */
export function sourceWhere(t: T, s: Source, withPart = true): string {
  const parts = withPart ? [s.part, s.item] : [s.item];
  if (s.pages) parts.push(t(isRange(s.pages) ? 'pageMany' : 'pageOne', { p: pageRange(s.pages) }));
  if (s.pdfPage) parts.push(t('pagePdf', { p: s.pdfPage }));
  return parts.join(' · ');
}

/**
 * Where a figure comes from: a link to COA's page for the file, the part, item and page,
 * and a link to report an error in it.
 */
export function SourceLine({ source, year, name, what }: { source: Source; year: number; name: string; what: string }) {
  const t = useT();
  const fromSummary = source.file === null && /executive summary/i.test(source.part);
  return (
    <p className="mt-2.5 text-[12.5px] text-ink-3 wrap-anywhere">
      <span className={cx(ui.label, 'mr-0.5')}>{t('sourceLabel')}</span>{' '}
      <a href={source.url} target="_blank" rel="noopener" title={t('sourceTitle')}>
        {t(fromSummary ? 'sourceSummary' : 'sourceReport', { year })}&nbsp;↗
      </a>
      <span lang="en">
        {' · '}
        {sourceWhere(t, source, !fromSummary)}
      </span>
      {' · '}
      <ErrorLink name={name} year={year} what={what} />
    </p>
  );
}

export function ErrorLink({ name, year, what }: { name: string; year: number; what: string }) {
  const t = useT();
  const subject = t('reportErrorSubject', { name, year, what });
  const body = `${window.location.href}\n\n`;
  return (
    <a
      className={ui.quietLink}
      href={`mailto:${ERROR_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`}
    >
      {t('reportError')}
    </a>
  );
}

export function Loading() {
  const t = useT();
  return (
    <p className="py-12 text-ink-3" role="status">
      {t('loading')}
    </p>
  );
}

export function LoadError() {
  const t = useT();
  return (
    <p className="py-12 text-v-adverse" role="alert">
      {t('loadError')}
    </p>
  );
}

/** A row of buttons for picking one value, like the language switcher. */
export function Segmented<V extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: V; label: string }[];
  value: V;
  onChange: (v: V) => void;
}) {
  return (
    <div className={ui.segmented} role="group" aria-label={label}>
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          className={ui.segmentedBtnLarge}
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
