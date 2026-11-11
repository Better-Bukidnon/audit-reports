import type { ReactNode } from 'react';
import { cx, ui } from '../ui';

export type Stat = { label: string; value: ReactNode; sub?: string; size?: 'normal' | 'small'; accent?: boolean };

/**
 * The KPI row: four figures between an ink rule and a grey one, in two rows of two
 * below 1024px. Borders depend on the position, so they're worked out here.
 */
export function Stats({ items }: { items: Stat[] }) {
  return (
    <dl className="mb-8 grid grid-cols-2 border-t border-b border-t-ink border-b-rule lg:grid-cols-4">
      {items.map((s, i) => (
        <div
          key={s.label}
          className={cx(
            'min-w-0 border-rule py-3.5 pr-3 md:py-4 md:pr-5',
            i % 2 === 0 ? 'border-r pl-0' : 'pl-3 md:pl-5',
            i < 2 && 'border-b border-b-rule-soft lg:border-b-0',
            i === 0 ? 'lg:pl-0' : 'lg:pl-5',
            i === 1 && 'lg:border-r',
            i === items.length - 1 && 'lg:border-r-0',
          )}
        >
          <dt className={ui.label}>{s.label}</dt>
          <dd
            className={cx(
              'mt-2 font-hero font-bold leading-[1.1] tracking-[-0.02em] tabular-nums wrap-anywhere',
              s.size === 'small' ? 'text-xl md:text-[26px]' : 'text-[26px] md:text-[34px]',
              s.accent && 'text-accent',
            )}
          >
            {s.value}
          </dd>
          {s.sub && <dd className="mt-1 text-[12.5px] text-ink-3">{s.sub}</dd>}
        </div>
      ))}
    </dl>
  );
}
