# Bukidnon Audit Reports

What the Commission on Audit (COA) found when it audited the Province of Bukidnon, its
2 cities and its 20 municipalities: COA's verdict on each government's books, the findings,
and whether past recommendations were acted on. Every figure links to the COA report it came
from and says where in it.

A [Better Bukidnon](https://betterbukidnon.org) site at `audit.betterbukidnon.org`, alongside
the [Budget](https://budget.betterbukidnon.org), [SALN](https://saln.betterbukidnon.org) and
[Infrastructure](https://infra.betterbukidnon.org) trackers.

## Why

The other trackers show what money is planned, what DPWH builds and what officials declare
they own. None shows what COA found when it checked how the money was handled. COA publishes
an Annual Audit Report for every local government each year, but as long reports on a site
that is hard to browse. This project pulls the same items out of every report and lays them
side by side, government by government and year by year.

It is for residents who want to know how their town or city did in its audit, journalists
and researchers comparing governments or following one over several years, and local
officials and Sanggunian members following up on COA's recommendations.

## What it shows

For each government and each year audited:

- **COA's verdict on the books**: unmodified, qualified, adverse or disclaimer, with COA's
  opinion quoted.
- **Headline figures** from the audited statements: total assets, liabilities, equity,
  revenue, and the surplus or deficit.
- **Budget and obligations**: each fund's final budget and how much of it was obligated.
- **Findings**: how many observations COA made, each with its own recommendation.
- **Past recommendations**: how many from earlier audits were fully implemented.
- **Unsettled disallowances**: suspensions, disallowances and charges still unsettled at the
  end of the year.

## Rules

- The COA report is the source. Every figure and quote links to it and says where in it.
- COA's words are quoted, not paraphrased.
- Years sit side by side; amounts from different years are never added together.
- A finding is not proof of wrongdoing, and the site says so wherever findings appear.
- No scores, grades or rankings of our own, and no individual names.
- Nothing changes silently: every correction goes in a public changelog with its reason.

The full list is in [docs/data-rules.md](docs/data-rules.md).

## In this repository

| Folder | Holds |
| --- | --- |
| [`docs/`](docs/README.md) | The plan, where the data comes from, the data rules, and how each item is taken from the reports and checked |
| [`data/`](data/) | The data as CSV, with each figure's source: the record the site is built from |
| [`scripts/`](scripts/README.md) | The scripts that file the downloaded reports and pull the data out of them, and how to run them again |
| [`site/`](site/README.md) | The website (React, TypeScript and Tailwind CSS): how to run it, build it and deploy it |

Start with [docs/](docs/README.md).

## License

Two licenses, the same two as Better Bukidnon:

| License | Applies to |
| --- | --- |
| MIT | The code: `scripts/` and the website's source in `site/` |
| CC BY 4.0 | Everything else: the data, the docs, and the text and translations the website shows |

COA's reports, and COA's words quoted from them, are COA's and under neither license. See
[LICENSE](LICENSE).
