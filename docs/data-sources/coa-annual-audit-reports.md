# COA Annual Audit Reports

The main source. COA writes one Annual Audit Report (AAR) per local government per
calendar year and posts it on its website.

- Listing: <https://www.coa.gov.ph/reports/annual-audit-reports/aar-local-government-units/>.
  COA's own menu links to `/audit-audit-reports/aar-local-government-units/` ("audit"
  twice), which redirects there.
- COA describes the collection as AARs for CY 2014 to CY 2025 covering national agencies,
  LGUs and GOCCs, in MS Word, MS Excel or PDF, and **password-protected**
  ([Annual Audit Reports](https://www.coa.gov.ph/reports/annual-audit-reports/)). Reports
  for CY 1998–2013 are in a separate [archive](https://www.coa.gov.ph/reports/aars-archive/).

## Access

**Every coa.gov.ph page sits behind a Cloudflare bot check.** On 2026-11-07, plain
requests got `403` and a "Just a moment..." challenge page for all of these:

- the LGU listing page above
- a single file page (`/wpfd_file/maramag-water-district-bukidnon-annual-audit-report-2022/`)
- the WordPress API (`/wp-json/wp/v2/wpfd_file?search=bukidnon`)
- the old regional pages (`/region1/index.php/reports/annual-audit-reports`)

A real browser passes the check like any visitor, so files are downloaded in a browser. On
2026-11-07 that was Chrome, driven by the Claude in Chrome extension. We don't try to get
around the check with scripts.

The site uses the WP File Download plugin. Once the listing page is open, the plugin
answers the page's own requests for folder and file lists, which saves clicking through
the tree:

| What | Request, sent from the open listing page |
| --- | --- |
| Folders inside a folder | `/wp-admin/admin-ajax.php?juwpfisadmin=false&action=wpfd&task=categories.display&view=categories&id=<folder id>&top=167` |
| Files in a folder | same, with `&task=files.display&view=files&id=<folder id>&rootcat=167` |
| One file, with its download link | same, with `&task=file.display&view=file&id=<file id>&categoryid=<folder id>&rootcat=167` |

Each file comes with its title, type, size in bytes, and upload and change dates.

The site also goes down: later on 2026-11-07 it returned Cloudflare errors 525 (COA's own
server failed the secure connection) and then 522 (COA's server didn't answer).

## Folder layout

Year → region → Provinces, Cities, Municipalities. Cities and Municipalities each have one
folder per province; Provinces holds all five Region X provinces. Confirmed for CY
2022–2025.

| CY | Year folder | Region X | Provinces | Cities / Bukidnon | Municipalities / Bukidnon |
| --- | --- | --- | --- | --- | --- |
| 2025 | `8736` | `8756` | `8809` | `8915` | `8808` |
| 2024 | `8207` | `8298` | `8309` | `8300` | `8305` |
| 2023 | `6264` | `7447` | `7455` | `7496` | `7460` |
| 2022 | `5516` | `5747` | `5904` | `6093` | `5749` |

Other year folders: 2021 `5065`, 2020 `202`, 2019 `203`, 2018 `204`, 2017
`205`, 2016 `206`, 2015 `2279`, 2014 `3429`. All sit under the LGU root folder `167`.

## URL patterns

| Era | Pattern | Example |
| --- | --- | --- |
| Current site, one folder per province per year | `/reports/annual-audit-reports/aar-local-government-units/#167-<folder id>-bukidnon-<timestamp>` | `#167-1401-bukidnon-1615511051` |
| Current site, from the CY 2023 reports on: separate folders for cities and municipalities | `#167-<folder id>-bukidnon-<cities\|municipalities>-region-x-northern-mindanao-<year>[-aar-lgu]` | `#167-8305-bukidnon-municipalities-region-x-northern-mindanao-2024-aar-lgu` |
| Current site, provinces | `#167-<folder id>-provinces-region-x-northern-mindanao-<year>-aar-lgu` | `#167-8309-provinces-region-x-northern-mindanao-2024-aar-lgu` |
| Single file page | `/wpfd_file/<slug>/` | `/wpfd_file/cabanglasan-annual-audit-report-2011/` |
| Old site (no longer used) | `/index.php/local-government-units/<year>/category/<id>-bukidnon?download=<file id>:<name>` | `.../2020/category/8930-bukidnon?download=45491:cabanglasan` |

On the old site, the 2020 cities and municipalities were in different folders (`8989` and
`8930`), both named "bukidnon".

File slugs get a suffix when another province has a town of the same name: Malitbog and San
Fernando are `-2024-2`, Quezon is `-2024-4`. In CY 2025 only San Fernando has one (`-2025-4`).

## Bukidnon folders found so far

CY 2022–2024 are confirmed (see [Folder layout](#folder-layout)). The other years come from
Wikidata citations (see [wikidata.md](wikidata.md)) and haven't been opened yet. The year
is the CY audited. Wikidata dates every report June 30 of the following year, and the
old-site entry titled "2020 Annual Audit Report" carries the date 2021-06-30, so we read CY
as that year minus one. The CY 2024 files confirm this: their titles say 2024 and COA
uploaded them in December 2025.

Folder ids below come from the Cabanglasan and Valencia entries. Libona is cited for
CY 2011–2024 as well; its folders are likely the same as Cabanglasan's.

| CY | Folder | Seen for |
| --- | --- | --- |
| 2011 | single files `cabanglasan-annual-audit-report-2011`, `libona-annual-audit-report-2011` | Cabanglasan, Libona |
| 2012 | `#167-4442`, `#167-4438`; single file `valencia-city-annual-audit-report-2012` | Cabanglasan, Valencia |
| 2013 | `#167-4125`, `#167-4121` | Cabanglasan, Valencia |
| 2014 | `#167-4251`, `#167-4236` | Cabanglasan, Valencia |
| 2015 | `#167-3344`, `#167-3340` | Cabanglasan, Valencia |
| 2016 | `#167-1656`, `#167-1657` | Cabanglasan, Valencia |
| 2017 | `#167-1401`, `#167-1397` | Cabanglasan, Valencia |
| 2018 | `#167-973`, `#167-969` | Cabanglasan, Valencia |
| 2019 | `#167-446`, `#167-442` | Cabanglasan, Valencia |
| 2020 | old site `8930` (municipalities), `8989` (cities) | Cabanglasan, Libona, Valencia |
| 2021 | `#167-5169`, `#167-5191` | Cabanglasan, Valencia |
| 2022 | `#167-5749` municipalities, `#167-6093` cities, `#167-5904` provinces | All 23 (confirmed) |
| 2023 | `#167-7460` municipalities, `#167-7496` cities, `#167-7455` provinces | All 23 (confirmed) |
| 2024 | `#167-8305` municipalities, `#167-8300` cities, `#167-8309` provinces | All 23 (confirmed) |
| 2025 | `#167-8808` municipalities, `#167-8915` cities, `#167-8809` provinces | All 23 (confirmed) |

The two ids per year before 2022 are probably the municipalities' and cities' folders, as
they turned out to be for 2022.

CY 2025 reports: all 23 are posted. COA uploaded them between September and October 2026, and
they were downloaded on 2026-11-08 (below).

## What a report looks like

Checked on 2026-11-07 for all 23 CY 2024 reports. Each government has two files:

| File | Format | Protection |
| --- | --- | --- |
| `<Name> Annual Audit Report 2024` | ZIP, 1.5–36.5 MB | None. The ZIP isn't encrypted. |
| `<Name> Executive Summary 2024` | PDF, 0.14–0.38 MB | Opens without a password. An owner password allows printing and blocks editing, copying and annotating. |

Every ZIP holds the same three files:

| File in the ZIP | What it is | Protection |
| --- | --- | --- |
| `AAR/<Name>2024_Audit_Report.docx` | The full report, in Word | 22 of 23 are locked to "filling in forms", which blocks editing; one has no lock. Neither stops reading: the text comes out in full, 200,000–790,000 characters and 75–176 tables per report. |
| `AAPSI_APMT/<Name>2024_AAPSI.pdf` | Agency Action Plan and Status of Implementation | Same as the executive summary. Not read yet. |
| `AAPSI_APMT/<Name>2024_APMT.pdf` | Action Plan Monitoring Tool | Same. Not read yet. |

So "password-protected" means locked against editing and copying, not against opening.
Standard tools read the Word file's text, so Phase 1 doesn't need hand entry.

### CY 2025

Checked on 2026-11-08 for all 23 governments. The same two files each, as in CY 2024: a ZIP
report (23 in all, 189.9 MB; the largest Impasug-ong's, 42.6 MB) and an executive summary PDF
(10.9 MB in all, with the same owner password). Every ZIP holds the Word report under `AAR/`
and the AAPSI and APMT under `AAPSI_APMT/`, and nothing else: no errata and no Word lock files.
All 23 Word reports are locked against editing only (one lock isn't enforced), and their text
comes out in full: 240,000–1,170,000 characters and 81–177 tables per report. Downloaded one
file every 5 seconds, smallest first; all 46 arrived at COA's listed size in about 21 minutes.

### Earlier years

Checked on 2026-11-07 for all 23 governments in CY 2022 and CY 2023. Every government has
the same two files (ZIP report, PDF executive summary), and every executive summary has the
same protection as in 2024.

| | CY 2023 (ZIPs 78 MB in all) | CY 2022 (ZIPs 22 MB in all) |
| --- | --- | --- |
| Full report | Word file for 22 governments. **Valencia's is a PDF** (`AAR/ValenciaCity2023_Audit_Report.pdf`) that blocks copying. Its text extracts in full (180 pages) with `pypdf` and `cryptography`; see [phase1-data.md](../phase1-data.md#valencia-cy-2023-pdf) | Word file for all 23, at the top of the ZIP (no `AAR/` folder) |
| AAPSI and APMT | Both, for all 23. Baungon's APMT and Don Carlos's AAPSI have no protection. Manolo Fortich adds a prior-year plan, `ManoloFortich2023_AAPSI_PY.pdf` | None |
| Extra files | Errata for Impasug-ong (`AAR/Impasugong2023_Errata.pdf`). Word lock files (`~$...docx`, 162 bytes, empty) in Baungon's, Dangcagan's and Lantapan's ZIPs | Errata for Don Carlos (`DonCarlos2022_Errata.pdf`) |

What each errata sheet corrects is in [phase1-data.md](../phase1-data.md#errata).
Errata change the report they come with, so a figure taken from a report with errata has
to be checked against them.

COA's file names write the cities as "Malaybalay City" and "Valencia City", the province
as plain "Bukidnon", and Impasug-ong as "Impasugong".

### Sections

A text search of the 23 Word files for the items in the [plan](../plan.md#what-we-pull-from-each-report).
Headings vary between reports, so a lower count may mean different wording rather than a
missing section.

| Section | Reports where found |
| --- | --- |
| Independent auditor's report | 23 |
| Part II, observations and recommendations | 23 |
| Part III, status of prior years' recommendations | 23 |
| "Suspensions, disallowances and charges" | 19; a later survey found the balance in all 69 CY 2022–2024 reports, in the executive summary, Part II or Part III ([phase1-data.md](../phase1-data.md#unsettled-disallowances)) |
| Management's comments | 22 |
| Gender and Development | 22 |
| 20% Development Fund | 23 |
| LDRRMF (disaster fund) | 23 |
| Senior citizens | 16 |
| LCPC (children's council) | 6 |
| BIR, GSIS, PhilHealth, Pag-IBIG | 23 each |

### Page numbers

Checked on 2026-11-07 for all 68 Word reports. Each one sets its own page numbers: roman
for the executive summary, then 1 onward from Part I, with COA forcing each later part to
a fixed start page (6 to 26 restarts per report). Each also has a typed table of contents
giving those pages. Maramag CY 2024, for example: Independent Auditor's Report 1–4,
Statement of Financial Position 6, Notes 16–55, Part II 56–108, Part III 111–134.

The page counts Word saved inside the files can't be trusted (some 200-page reports say 1
to 5 pages), and a page inside a long section depends on how the file is laid out on the
reader's machine. So records cite the part and item, plus the page from COA's table of
contents ([plan D7](../plan.md#open-decisions)). A test layout in this machine's Word, to
compare against the tables of contents, was stopped for low memory on 2026-11-07 and
hasn't been redone.

## How we keep the files

- [`scripts/pdf_pages.py`](../../scripts/pdf_pages.py) saves the text of each executive summary PDF,
  page by page, beside it (`<name>.pages.txt`), so a balance COA gives only in the summary can cite
  the PDF's page ([phase1-data.md](../phase1-data.md#executive-summary-pdfs)). It needs `pypdf` and
  `cryptography`, in a throwaway environment.
- [`scripts/import_coa_downloads.py`](../../scripts/import_coa_downloads.py) files each
  download in `raw/<year>/<government>/`, checks its size against COA's listing, unzips it,
  records the protection on every file and saves the Word text beside the report.
- [`scripts/word_list_numbers.ps1`](../../scripts/word_list_numbers.ps1) saves the list
  numbers Word shows in each report beside it (`<report>.word-lists.tsv`), for the check on
  our own count of them ([phase1-data.md](../phase1-data.md#findings)). It needs Word, opens
  each report read-only in its own Word, and reads the numbers without laying out pages.
- `raw/` is git-ignored until [plan D3](../plan.md#open-decisions) is decided.
- `data/sources/coa-aar-<year>-files.csv` lists every file: government, COA file and folder
  ids, slug, size, SHA-256, COA's upload and change dates, download date and protection.
  `coa-aar-<year>-contents.csv` lists the files inside each ZIP.

## Not yet known

- Whether every government has a report for every year. CY 2022–2024 have all 23.
- What the AAPSI and APMT PDFs hold, and whether they cover what
  [lgu-action-plans.md](lgu-action-plans.md) found on Maramag's website. CY 2022 has none.
- Whether the `/wpfd_file/<slug>/` page works for every file. The manifests list it but we
  haven't opened one.
- Whether this machine's Word lays the reports out with the same page breaks as COA's
  table of contents. Needed before findings (Phase 2) cite pages.

## Phase 0 checklist

- [x] Open the CY 2024 municipalities and cities folders and list every file. Done
      2026-11-07: 23 governments, 46 files.
- [x] Download a report and check whether it opens, whether text can be copied, and which
      sections it has. Done for all 23 CY 2024 reports.
- [x] Find the provincial report: Region X → Provinces.
- [x] Repeat for CY 2023 and CY 2022. Done 2026-11-07: all 23 governments both years.
- [x] Update [../auditees.md](../auditees.md) with what's there (CY 2022–2024).
