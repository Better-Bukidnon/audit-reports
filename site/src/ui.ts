// Class lists used in more than one place. Tailwind reads this file for class names,
// so keep every class written out in full (no building names from pieces).
//
// Don't add a class that sets something a list below already sets (cx(ui.sectionH, 'mb-0')):
// which one wins depends on Tailwind's stylesheet order, not the order here. Use or add a
// variant instead, like sectionHFlush.

export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(' ');

const labelType = 'font-mono text-[10.5px] font-medium uppercase tracking-[0.14em]';
const sectionHType = 'block font-hero text-[22px] font-bold tracking-[-0.015em]';
const segmentedBtn =
  'border-0 bg-transparent font-mono font-medium tracking-[0.08em] text-ink-3 not-first:border-l not-first:border-rule aria-pressed:bg-ink aria-pressed:text-paper';

export const ui = {
  /** The width container: 1280px, with a 32px gutter (16px on phones). */
  page: 'mx-auto w-full max-w-page px-4 md:px-8',

  /** Mono labels: metadata only, never sentences. */
  label: `${labelType} text-ink-3`,
  labelAccent: `${labelType} text-accent-deep`,
  kicker: 'mb-1.5 block font-mono text-[10.5px] font-medium uppercase tracking-[0.18em] text-accent',
  sub: 'mt-0.5 block font-body text-xs font-normal normal-case tracking-normal text-ink-3',

  pageHead: 'mb-6 max-w-[860px]',
  h1: 'mb-2.5 text-[28px] tracking-[-0.025em] md:text-4xl',
  lede: 'mb-0 text-[17px] leading-[1.55] text-ink-2',

  /** Sections are separated by an ink rule, not cards or shadows. */
  section: 'mt-10 scroll-mt-4 border-t border-ink pt-[18px]',
  sectionH: `${sectionHType} mb-2.5`,
  /** A section heading that sits in a row with other controls. */
  sectionHFlush: sectionHType,
  sectionNote: 'max-w-[760px] text-sm text-ink-3',
  muted: 'text-ink-3',

  btn: 'inline-flex min-h-10 items-center justify-center gap-1.5 border border-ink bg-paper px-3.5 py-2 text-center font-hero text-sm font-semibold text-ink no-underline hover:bg-paper-2 hover:text-ink',

  /** A row of toggle buttons (language, year). */
  segmented: 'inline-flex shrink-0 border border-rule',
  /** The language switcher's buttons. */
  segmentedBtnSmall: `${segmentedBtn} px-2 py-[3px] text-[11px]`,
  /** The light/dark switch's buttons: an icon, as tall as the language buttons beside it. */
  segmentedBtnIcon: `${segmentedBtn} inline-flex items-center justify-center px-[7px]`,
  /** Year pickers' buttons. */
  segmentedBtnLarge: `${segmentedBtn} min-h-9 px-3.5 py-1.5 text-xs`,

  tableWrap: 'overflow-x-auto border-t border-b border-t-ink border-b-rule',
  table: 'w-full border-collapse text-sm [&_tbody_tr:last-child>*]:border-b-0',
  /** Table headings: mono labels on paper-2. thSort has no padding: its button carries it. */
  th: `border-b border-rule bg-paper-2 px-3.5 py-2.5 align-bottom ${labelType} text-ink-3 first:pl-0`,
  thSort: `border-b border-rule bg-paper-2 p-0 align-bottom ${labelType} text-ink-3 aria-[sort]:text-ink`,
  /** Body cells, and row headings (add font-semibold). */
  td: 'border-b border-rule-soft px-3.5 py-3 align-top first:pl-0',
  left: 'text-left',
  num: 'text-right whitespace-nowrap tabular-nums',
  /** Right-aligned heading that may wrap. */
  numWrap: 'text-right tabular-nums',

  /** Small grey links (report an error, page numbers). */
  quietLink: 'text-ink-3 hover:text-accent',
};
