# Plan

## Why

The other Better Bukidnon trackers show what money is planned (Budget), what DPWH builds
(Infrastructure) and what officials declare they own (SALN). None shows what COA found
when it checked how the money was handled. COA publishes an Annual Audit Report (AAR) for
every local government each year, but as long PDFs on a site that is hard to browse. This
site pulls the same items out of every report and lays them side by side.

## Who it's for

- Residents who want to know how their town or city did in its latest audit.
- Journalists and researchers comparing governments or tracking one over several years.
- Local officials and Sanggunian members following up on COA recommendations.

## What we pull from each report

| Item | Where it is in the AAR | What it tells people |
| --- | --- | --- |
| COA's verdict on the books | Independent auditor's report: unmodified, qualified, adverse, or disclaimer | Whether the financial statements can be relied on |
| Headline money figures | Financial highlights: appropriations, obligations, assets, liabilities, income | Size of the operation |
| Findings | Part II: title, amount involved, COA's recommendation, management's reply | What COA flagged that year |
| Past recommendations | Part III: each one fully, partly or not implemented | Whether problems get fixed or keep coming back |
| Unsettled disallowances | Status of suspensions, disallowances and charges | Spending COA ruled improper that hasn't been paid back |
| Required set-asides | Compliance sections: 5% Gender and Development, 20% Development Fund, 5% disaster fund (LDRRMF), 1% senior citizens and PWDs, 1% children's council (LCPC) | Whether money the law requires was set aside and used |
| Unremitted contributions | Compliance sections: BIR, GSIS, PhilHealth, Pag-IBIG | Whether employee deductions were paid in |

Parts II and III are confirmed by Maramag's CY 2023 action plan
([data-sources/lgu-action-plans.md](data-sources/lgu-action-plans.md)). A text search of
all 23 CY 2024 reports found every item in the table, though some headings vary between
reports ([data-sources/coa-annual-audit-reports.md](data-sources/coa-annual-audit-reports.md#sections)).

## What people see

### Home

A grid or map of the 23 governments, each colored by its latest verdict, and a search box
("Find your town").

### Government page (one per city, town and the province)

Example with made-up numbers:

```
Sample Town, Bukidnon                         Source: COA reports ↗
─────────────────────────────────────────────────────────────────
COA's verdict   2020      2021      2022      2023      2024
                Qualified Qualified Adverse   Qualified Unmodified

2024 at a glance
  Findings ............................ 14
  Past recommendations fixed .......... 9 of 21
  Disallowances not yet settled ....... ₱3.2M
  Gender and Development budget used .. 61% of the 5% set aside

Not fixed for 2+ years
  ▸ Cash advances not liquidated (₱1.8M)        since 2021   p. 47
  ▸ Equipment records don't match the count     since 2020   p. 52

All 2024 findings  [Cash] [Property] [Procurement] [Required funds] ...
  ▸ Disaster fund only 40% used ........ ₱6.1M   p. 33
    COA said: "..." · Recommendation: "..." · Management replied: "..."
```

### Compare

One table of all 23 governments for a chosen year: verdict, number of findings, share of
past recommendations fixed, unsettled disallowances. Sortable, with no "best" or "worst"
labels.

### About COA audits

What COA does, what each verdict means, what a finding is and isn't, and how to read an
AAR yourself.

### What people can check

- Every figure and quote links to the report it came from and says where in it: the part and item, and the page where COA's table of contents gives one ([D7](#open-decisions)).
- All data downloads as CSV.
- "Report an error" on every record, and a public changelog of corrections.

## What we leave out

- Scores, grades or rankings of our own. We show COA's verdict and nothing else.
- Names of individual employees. COA writes "the Municipal Treasurer", and so do we.
- Our own wording of findings. Findings, recommendations and management replies are quoted.

## Phases

| Phase | Scope | Source |
| --- | --- | --- |
| 0. Check | Open a real Bukidnon AAR; confirm sections, file protection, and coverage per government ([D1](#open-decisions)). Done for CY 2022–2025 | COA site, in a browser |
| 1. Verdicts | Verdict, headline figures, number of findings, past recommendations fixed, unsettled disallowances, report link. 23 governments × CY 2022–2025. **Verdicts, five figures, past recommendations fixed and the number of findings done for all 69 reports on 2026-11-07, unsettled disallowances and appropriations and obligations on 2026-11-08; all of it for the 23 CY 2025 reports on 2026-11-08** ([phase1-data.md](phase1-data.md)) | AAR Word files (text extracts cleanly); one PDF (Valencia CY 2023); errata where COA issued them; executive summary PDFs, for disallowances given only there |
| 2. Findings | Each finding with category, amount, quotes and page number | AAR Part II and III, the action plans (AAPSI, APMT) in each report's ZIP from CY 2023 |
| 3. Backfill | Earlier years (reports go back to about 2012) | COA site, in a browser |

Phase 2 is a lot of reading. It suits volunteers, through the same kind of form proposed
for the SALN tracker ([Better-Bukidnon/saln#5](https://github.com/Better-Bukidnon/saln/issues/5)).

## Open decisions

| # | Question | Notes |
| --- | --- | --- |
| D1 | Do the Bukidnon AARs contain everything in the table above, and can their text be copied? | **Resolved 2026-11-07: yes.** All 69 CY 2022–2024 reports open without a password. 68 are Word files locked against editing only, and their text extracts in full; Valencia's CY 2023 report is a copy-blocked PDF, not yet extracted. A text search of the CY 2024 reports found every item in the table. |
| D2 | How many years in Phase 1? | CY 2022–2025 (92 reports). CY 2022–2024 downloaded 2026-11-07, CY 2025 on 2026-11-08, after COA posted all 23 in September–October 2026. |
| D3 | Can we host copies of the reports, or only link to COA? | Links break when COA reorganizes its site (it already has once, see the old `index.php` URLs), and the site goes down at times. A mirror protects against that but raises the question of redistributing protected files. For now the files stay on the maintainer's machine, out of git; `data/sources/` records each file's SHA-256 so others can fetch and check the same files. |
| D4 | Stack and repo | **Frontend decided 2026-11-07: React with TypeScript, styled like the Infrastructure tracker** (`../bukidnon-infra-projects`, infra.betterbukidnon.org). That site is plain HTML, so we copy its look, not its code: its masthead, subnav, KPI row and footer layout, Figtree, Inter and JetBrains Mono type roles, tokens in `assets/css/infra-projects.css`, every string in English, Filipino and Cebuano, and its own accent color. Its `.claude/skills/design-system` skill has the rules. **Styling decided 2026-11-08: Tailwind CSS**, with the Infrastructure tracker's tokens as Tailwind theme values (`site/src/index.css`) instead of its `ip-` prefixed classes. The site was started on 2026-11-08 in `site/` ([site/README.md](../site/README.md)). Proposed repo: `Better-Bukidnon/audit-reports`, `develop` for integration and `main` for production. Work is on a local `develop` branch, not yet on GitHub. |
| D5 | Do we use the Wikidata figures? | Useful to cross-check, but every figure shown must come from the report ([data-rules.md](data-rules.md)). |
| D6 | Where is the Province of Bukidnon's own report? | **Resolved 2026-11-07:** Region X → Provinces, in its own folder next to Cities and Municipalities. |
| D7 | What page number does a figure cite? | **Decided 2026-11-07: part and item, plus COA's own page where its table of contents gives one.** Each Word report sets its own page numbers (roman for the executive summary, then 1 onward, with every part forced to a fixed start page) and has a typed table of contents listing them, for example Maramag CY 2024: auditor's report pp. 1–4, Part II pp. 56–108. Section start pages don't move, but a page inside a long section depends on how Word lays the file out, so findings get a page only once a test shows our Word lays out the files as COA's did. Every Phase 1 item sits at a section COA's table of contents lists. PDFs (executive summaries, Valencia CY 2023, errata) cite their real page. See [data rule 1](data-rules.md). |

## Risks

| Risk | Mitigation |
| --- | --- |
| COA's Cloudflare check blocks automated downloads | Download in a browser; `scripts/import_coa_downloads.py` checks each file against COA's listing |
| COA's site is down when we need it (Cloudflare errors 525 and 522 on 2026-11-07) | Keep our own copies (D3) and the manifests in `data/sources/` |
| Text can't be copied from the files | Resolved by D1: the Word files' text extracts. Still spot-check extracted figures against the report |
| Readers take a finding as proof of wrongdoing | Explainer page, a note on every finding, quotes only |
| A government disputes a finding | Show management's reply next to every finding, as COA does |
| Records drift from the source | Every record stores the report URL, part, item and page ([D7](#open-decisions)); spot checks before each release |
