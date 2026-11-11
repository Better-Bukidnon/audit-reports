import type { ReactNode } from 'react';
import { useT, useTitle } from '../i18n';
import { cx, ui } from '../ui';
import { VerdictBadge } from '../components/bits';
import type { Key } from '../strings';
import type { Verdict } from '../types';

const VERDICTS: Verdict[] = ['unmodified', 'qualified', 'adverse', 'disclaimer'];

/** COA's answers in its FAQs, at coa.gov.ph/FAQS/<slug>/. */
const FAQ_URL = 'https://www.coa.gov.ph/FAQS/';

type Faq = { slug: string; q: string; text: string };

/** COA's FAQ page defining each verdict. */
const VERDICT_FAQ: Record<Verdict, string> = {
  unmodified: 'what-is-an-unmodified-opinion',
  qualified: 'what-is-a-qualified-opinion',
  adverse: 'what-is-an-adverse-opinion',
  disclaimer: 'what-is-a-disclaimer-of-opinion',
};

// Quoted word for word from COA's FAQs, as read on 2026-11-08. "…" marks words left out.
const FAQ_COA: Faq[] = [
  {
    slug: 'what-is-commission-on-audit-coa',
    q: 'What is Commission on Audit (COA)?',
    text: 'The Commission on Audit is the Supreme Audit Institution of the Philippines. It is the sole External Auditor of the Philippine Government.',
  },
  {
    slug: 'what-is-an-annual-audit-report',
    q: 'What is an Annual Audit Report?',
    text: 'It is a final output of the yearly audit conducted by the auditor assigned to audit the accounts and operations of a government agency and basically consists of the Auditor’s Certificate, the financial statements and the audit observations and recommendations.',
  },
];

const FAQ_VERDICT: Faq[] = [
  {
    slug: 'what-is-the-highest-rating-coa-can-give-to-its-auditee',
    q: 'What is the highest rating COA can give to its auditee?',
    text: '… an audit opinion should not be viewed as a rating, score or grade, with ranking of lowest to highest.',
  },
  {
    slug: 'does-a-coa-unqualified-opinion-vouch-an-agency-free-from-corruption',
    q: 'Does a COA Unqualified Opinion vouch an agency free from corruption?',
    text: 'No. An audit opinion pertains only to the financial audit conducted regularly by COA auditors to ascertain whether an agency’s financial statements are prepared, in all material respects, in accordance with the applicable financial reporting framework.',
  },
  {
    slug: 'what-is-an-unmodified-opinion',
    q: 'What is an unmodified opinion?',
    text: '… an unmodified/unqualified opinion does not necessarily mean that there were no misstatements found during the audit nor there were no uncorrected misstatements as at year-end. … Moreover, this does not entail that the audited agency fully complies with all the laws, rules, and regulations or that the uses of funds on the agency’s programs, projects, and activities are economical, effective, or efficient.',
  },
];

const FAQ_FINDINGS: Faq[] = [
  {
    slug: 'what-happens-after-coas-audit',
    q: 'What happens after COA’s audit?',
    text: 'After COA’s audit, the audited government agency or entity is given a chance to comment on the findings and recommendations. COA then issues a final audit report, which is submitted to the concerned government agency or entity and published in COA’s website.',
  },
];

const FAQ_DIS: Faq[] = [
  {
    slug: 'what-is-a-statement-of-audit-suspensions-disallowances-and-charges-sasdc',
    q: 'What is a Statement of Audit Suspensions, Disallowances and Charges (SASDC)?',
    text: 'It is a written summary of the total balance of audited accounts of the agency at the end of each quarter. It shows the total issued suspensions, disallowances, charges and settlements for the quarter and the running balance of the suspensions, disallowances and charges as of the quarter ended.',
  },
  {
    slug: 'what-is-disallowance',
    q: 'What is disallowance?',
    text: 'According to item 4.27 of COA Circular No. 2009-006, “Disallowance is the disapproval in audit of a transaction, either in whole or in part. The term applies to the audit of disbursements as distinguished from “charge” which applies to the audit of revenues/receipts.”',
  },
  {
    slug: 'what-happens-if-notice-of-suspension-is-not-settled',
    q: 'What happens if Notice of Suspension is not settled?',
    text: 'The NS should be settled within 90 calendar days from date of receipt by the responsible officers; otherwise, the NS will mature into disallowance.',
  },
  {
    slug: 'is-a-notice-of-disallowance-final-and-executory',
    q: 'Is a Notice of Disallowance final and executory?',
    text: 'No. Notice of Disallowance will become final and executory if not appealed within six (6) months from receipt by the accountable officers.',
  },
];

const FAQ_READ: Faq[] = [
  {
    slug: 'how-can-the-public-access-coas-reports',
    q: 'How can the public access COA’s reports?',
    text: 'COA’s reports are available to the public and can be accessed through COA’s website www.coa.gov.ph or by requesting copies from the audit sector concerned.',
  },
];

function Block({ id, h, children }: { id: string; h: Key; children: ReactNode }) {
  const t = useT();
  return (
    <section
      id={id}
      aria-labelledby={`${id}-h`}
      className="mt-9 max-w-[760px] scroll-mt-4 border-t border-ink pt-4 [&_p]:text-[15.5px] [&_p]:leading-[1.65] [&_p]:text-ink-2"
    >
      <h2 className={ui.sectionH} id={`${id}-h`}>
        {t(h)}
      </h2>
      {children}
    </section>
  );
}

/** A term and what it means, one per row. */
function Terms({ items }: { items: { term: ReactNode; text: ReactNode }[] }) {
  return (
    <dl className="mt-1 mb-4 border-t border-rule-soft">
      {items.map((it, i) => (
        <div key={i} className="grid grid-cols-1 gap-1 border-b border-rule-soft py-2.5 md:grid-cols-[160px_minmax(0,1fr)] md:gap-4">
          <dt className="font-semibold">{it.term}</dt>
          <dd className="text-ink-2">{it.text}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * COA's answers from its FAQs, quoted in English with a link to each.
 * No <p> inside: Block styles every <p> as body text.
 */
function CoaFaq({ items }: { items: Faq[] }) {
  const t = useT();
  return (
    <figure className="my-4 border-l-2 border-rule py-0.5 pl-4">
      <figcaption className={cx(ui.label, 'mb-1.5 block')}>{t('aboutFaqCaption')}</figcaption>
      {items.map((f) => (
        <div key={f.slug} lang="en" className="mb-3 last:mb-0">
          <blockquote cite={FAQ_URL + f.slug + '/'} className="text-[14.5px] leading-relaxed text-ink-2">
            {f.text}
          </blockquote>
          <div className="mt-1 text-[12.5px] wrap-anywhere">
            <a className={ui.quietLink} href={FAQ_URL + f.slug + '/'} target="_blank" rel="noopener">
              {f.q}&nbsp;↗
            </a>
          </div>
        </div>
      ))}
    </figure>
  );
}

export function About() {
  const t = useT();
  useTitle(t('aboutTitle'));
  return (
    <article>
      <div className={ui.pageHead}>
        <h1 className={ui.h1}>{t('aboutTitle')}</h1>
        <p className={ui.lede}>{t('aboutLede')}</p>
      </div>

      <Block id="coa" h="aboutCoaH">
        <p>{t('aboutCoaP')}</p>
        <CoaFaq items={FAQ_COA} />
      </Block>

      <Block id="verdict" h="aboutVerdictH">
        <p>{t('aboutVerdictP1')}</p>
        <Terms
          items={VERDICTS.map((v) => ({
            term: <VerdictBadge verdict={v} />,
            text: (
              <>
                {t(`verdictExplain_${v}`)}{' '}
                <a
                  className={cx(ui.quietLink, 'text-[13px] whitespace-nowrap')}
                  href={FAQ_URL + VERDICT_FAQ[v] + '/'}
                  target="_blank"
                  rel="noopener"
                >
                  {t('aboutFaqDef')}&nbsp;↗
                </a>
              </>
            ),
          }))}
        />
        <p>{t('aboutVerdictP2')}</p>
        <CoaFaq items={FAQ_VERDICT} />
      </Block>

      <Block id="findings" h="aboutFindingsH">
        <p>{t('aboutFindingsP1')}</p>
        <CoaFaq items={FAQ_FINDINGS} />
        <p>{t('aboutFindingsP2')}</p>
        <p>{t('aboutFindingsP3')}</p>
      </Block>

      <Block id="recommendations" h="aboutRecsH">
        <p>{t('aboutRecsP')}</p>
      </Block>

      <Block id="disallowances" h="aboutDisH">
        <p>{t('aboutDisP1')}</p>
        <Terms
          items={(['suspensions', 'disallowances', 'charges'] as const).map((k) => ({
            term: t(`dis_${k}`),
            text: t(`disHelp_${k}`),
          }))}
        />
        <p>{t('aboutDisP2')}</p>
        <CoaFaq items={FAQ_DIS} />
      </Block>

      <Block id="budget" h="aboutBudgetH">
        <p>{t('aboutBudgetP1')}</p>
        <p>{t('aboutBudgetP2')}</p>
      </Block>

      <Block id="sources" h="aboutSourcesH">
        <p>{t('aboutSourcesP1')}</p>
        <p>{t('aboutSourcesP2')}</p>
      </Block>

      <Block id="left-out" h="aboutLeaveOutH">
        <p>{t('aboutLeaveOutP')}</p>
      </Block>

      <Block id="read" h="aboutReadH">
        <p>{t('aboutReadP1')}</p>
        <p>{t('aboutReadP2')}</p>
        <CoaFaq items={FAQ_READ} />
        <a
          className={cx(ui.btn, 'mt-1')}
          href="https://www.coa.gov.ph/reports/annual-audit-reports/aar-local-government-units/"
          target="_blank"
          rel="noopener"
        >
          coa.gov.ph ↗
        </a>
      </Block>

      <Block id="languages" h="aboutLangH">
        <p>{t('aboutLangP')}</p>
      </Block>
    </article>
  );
}
