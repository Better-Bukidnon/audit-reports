# Scripts

These scripts turn COA's report files into the CSVs in [`data/`](../data/), and the website
is built from those CSVs. Each script says at its top what it reads and writes. This page
says which to run, in what order, and what a good run looks like.

```
COA's site --(browser)--> your Downloads folder, plus a listing of the files
    |
import_coa_downloads.py --> raw/<year>/<government>/           the files, unzipped (not in git)
    |                       data/sources/coa-aar-<year>-*.csv   what was downloaded, with SHA-256
    |
    |-- pdf_pages.py ----------> <name>.pages.txt beside each PDF in raw/
    |-- word_list_numbers.ps1 --> <report>.word-lists.tsv beside each Word report in raw/
    |
extract_phase1.py --> data/phase1/*.csv
    |
site: npm run build --> site/public/data/, then site/dist/
```

## Which steps to run

| You changed | Run |
| --- | --- |
| `extract_phase1.py`, or a CSV kept by hand (`corrections.csv`, `errata.csv`, `appendix-notes.csv`, `pdf-reports.csv`) | [Step 5](#5-pull-the-data), then [step 6](#6-build-the-site) |
| Only the site's code | [Step 6](#6-build-the-site) |
| Nothing, but there's no `raw/` (a fresh clone) | Every step. The manifests say [which files to get](#getting-the-same-files-again) |
| A new year of reports came out | Every step, for that year. See [A new year](#a-new-year) |

## What each needs

| Step | Needs | Takes |
| --- | --- | --- |
| `import_coa_downloads.py` | Python 3, standard library only. 7-Zip at `C:\Program Files\7-Zip\7z.exe`, but only for a ZIP Python can't unpack (Deflate64) | 6 seconds to recheck a year; longer when it unzips |
| `pdf_pages.py` | `pypdf` and `cryptography`, in a throwaway environment ([step 3](#3-save-the-pdfs-text)) | About a minute for 93 PDFs |
| `word_list_numbers.ps1` | Windows with Microsoft Word | About 10 seconds and 300 MB per report |
| `extract_phase1.py` | Python 3, standard library only | 2½ to 3½ minutes for 92 reports |
| The site | Node 24 (`site/.node-version`) | |

All of it ran on Windows 11 with Python 3.14 in November 2026.

Run Python with `-I`. It keeps Python from importing code from the current folder or from
`PYTHONPATH`, so nothing in `raw/` can run. The scripts find the repository from their own
path, so they work from any folder; the commands below run from the repository root.

## 1. Download the reports

coa.gov.ph sits behind a Cloudflare bot check that turns scripts away, so the reports are
downloaded in a browser, like any visitor. [docs/data-sources/coa-annual-audit-reports.md](../docs/data-sources/coa-annual-audit-reports.md)
has each year's folder ids and the requests that list a folder's files without clicking
through the tree.

For a year you need, in one folder:

- **Each government's two files**, 46 in all: the report (`<Name> Annual Audit Report <year>`,
  a ZIP) and the executive summary (`<Name> Executive Summary <year>`, a PDF).
- **The names Chrome gives them**: the title with hyphens for spaces, such as
  `Baungon-Annual-Audit-Report-2025.zip`. COA writes the cities as `Malaybalay-City` and
  `Valencia-City`, the province as plain `Bukidnon`, and Impasug-ong as `Impasugong`.
- **A listing**: a tab-separated file with this header row and one row per file, as COA's
  folder listing gives them:

  ```
  category_id	file_id	slug	ext	size	created	modified
  ```

Download slowly. One file every 5 seconds worked for CY 2025; COA's site has gone down after
a fast burst.

### Getting the same files again

`data/sources/coa-aar-<year>-files.csv` lists every file we downloaded, with the listing's
columns under other names, and `coa_file_page` gives each file's page on COA's site. To get
the same files again, write the listing from it (PowerShell):

```powershell
Import-Csv data\sources\coa-aar-2024-files.csv |
  Select-Object @{n='category_id';e={$_.coa_category_id}}, @{n='file_id';e={$_.coa_file_id}},
    @{n='slug';e={$_.coa_slug}}, ext, @{n='size';e={$_.bytes}},
    @{n='created';e={$_.coa_uploaded}}, @{n='modified';e={$_.coa_modified}} |
  Export-Csv $env:TEMP\listing-2024.tsv -Delimiter "`t" -NoTypeInformation -Encoding UTF8
```

If COA has replaced a file since, step 2's size check will say so, or the new SHA-256 will
show in `git diff data/sources`.

## 2. File the downloads

```
python -I scripts/import_coa_downloads.py 2024 <listing.tsv> <Downloads folder>
```

For each row of the listing it finds the download, checks its size against COA's, moves it to
`raw/<year>/<government>/` and unzips the report into `extracted/` beside it. It records each
file's protection, saves each Word report's text beside it as `.txt` (for searching by hand;
the extractor reads the Word file itself), and writes `data/sources/coa-aar-<year>-files.csv`
and `coa-aar-<year>-contents.csv`.

A good run prints `filed 46 of 46 files; ... files inside ZIPs` and nothing more. Otherwise
each `PROBLEM:` line names a file, and the script exits with 1:

| The problem | What to do |
| --- | --- |
| `size ... != COA ...; left in Downloads` | The download was cut short. Delete it, download that file again and rerun |
| `not downloaded` | The file isn't in the folder under the name the script expects |
| `copied; Downloads copy is in use, delete it later` | Filed. Some program had the download open, so delete the Downloads copy yourself |
| `differs from the copy already in ...` | COA's file isn't the one filed before. Find out why before replacing it |

Rerunning it is safe: files already filed are checked again, not filed twice. To recheck a
year without new downloads, pass any folder as the Downloads folder. It does rewrite the
manifests with today's date in their `downloaded` column; if that is all
`git diff data/sources` shows, undo it with `git checkout data/sources`.

## 3. Save the PDFs' text

The executive summary PDFs carry an owner password (AES), so `pypdf` needs `cryptography` to
read them. Neither is a dependency of the repository, so install them in a throwaway
environment outside it (PowerShell):

```powershell
python -m venv $env:TEMP\coa-pdf
& $env:TEMP\coa-pdf\Scripts\python.exe -m pip install pypdf cryptography
& $env:TEMP\coa-pdf\Scripts\python.exe -I scripts\pdf_pages.py
```

It writes `<name>.pages.txt` beside every executive summary PDF in `raw/`, and beside Valencia
CY 2023's report, the one report that is a PDF: each page's text after a line
`=== PDF page N ===`. It redoes every PDF each run and ends with the count, 93 for CY
2022–2025.

Don't skip it. The extractor cites the PDF page for each disallowance balance COA gives only
in the executive summary, and checks Valencia CY 2023's figures, read by hand, against the
pages they cite. Without these files those checks fail and the pages come out empty.

## 4. Save Word's list numbers (optional)

Most of COA's finding numbers are Word list numbers: Word works them out when it shows the
file, so they aren't in the file's text. The extractor counts them the way Word does. This
script asks Word itself, so the extractor can check its count.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\word_list_numbers.ps1
```

It writes `<report>.word-lists.tsv` beside each Word report and skips reports that already
have one (`-Force` redoes them). Each report opens read-only, with macros off, in its own
hidden Word. That Word is stopped when the report is done, whatever happened, or after 5
minutes (`-TimeoutSec`). The run stops if less than 4 GB of memory is free. It prints a line
for each report it opens (`ok`, `FAILED` or `TIMEOUT`) and, last, how many Word processes are
running, your own included.

Skip it and the data doesn't change: the check "findings: numbers match Word's" reads `n/a`
for a report without the file.

## 5. Pull the data

```
python -I scripts/extract_phase1.py
```

It reads every Word report in `raw/<year>/<government>/extracted/`, and the files steps 3 and
4 saved, and rewrites the CSVs in `data/phase1/`. What each CSV holds, and how each item is
found and checked, is in [docs/phase1-data.md](../docs/phase1-data.md).

Four CSVs in `data/phase1/` are kept by hand. The script reads them and never writes them:

| File | Holds |
| --- | --- |
| `corrections.csv` | Figures COA printed wrong, where the same report shows the right one |
| `errata.csv` | What COA's errata sheets correct |
| `appendix-notes.csv` | A note for each fund where a budget appendix and the statement disagree |
| `pdf-reports.csv` | Valencia CY 2023, read by hand from its PDF |

If a row in one of them no longer fits what the script reads in the report, it stops with
`correction no longer matches the report`, `errata no longer matches the report` or
`appendix note no longer matches the report`. Either the reading changed or the report did;
find out which before touching the row.

For CY 2022–2025 a good run prints this, then one line per failed check:

```
92 verdicts: {'qualified': 91, 'disclaimer': 1}
460 figures, 92 past-recommendation rows, 1298 findings in 92 reports, 92 disallowance rows (404 table rows), 177 appropriation rows (3538 table rows), 3375 checks, 95 failed
  FAIL 2022 cabanglasan: past recommendations: our count of the Part III status column agrees - ...
```

The 95 `FAIL` lines are expected. Each is about COA's own report: two places in it that
disagree, or a figure it doesn't give. The Checks part of each section of
docs/phase1-data.md says how we read them. The script records them in `checks.csv` and
changes nothing. A `FAIL` the docs don't explain is new: read it.

Then compare with what's committed:

```powershell
git diff --stat data/phase1
(git diff data/phase1 | Select-String '^-[0-9]').Count
```

No difference means the run gave the same data. After changing the script, the second line
counts the rows it changed or dropped (every row starts with its year); it should be 0 unless
you meant to change them.

## 6. Build the site

```
cd site
npm install
npm run build
```

`npm run build` and `npm run dev` first run `site/scripts/build-data.mjs`, which reads the CSVs
and writes `site/public/data/`. It stops with an error if a report lacks something the site
shows. See [site/README.md](../site/README.md).

## A new year

1. Find the year's folder ids on COA's site and add them to the
   [folder table](../docs/data-sources/coa-annual-audit-reports.md#folder-layout).
2. Run steps 1 to 4 for that year. If COA names a government in a way the importer doesn't
   know, it stops with a `KeyError`: add the name to `LGUS` at the top of
   `import_coa_downloads.py`.
3. Run step 5. Each year's reports change a little: CY 2025 brought seven changes the script
   didn't read yet ([CY 2025](../docs/phase1-data.md#cy-2025)). Read the new year's `FAIL`
   lines, fix the script, and run it again until each `FAIL` left is a disagreement in COA's
   report, with the check above that no earlier year's row changed.
4. Write up the year in [docs/phase1-data.md](../docs/phase1-data.md), as for CY 2025.
5. The site takes its years from the data, so step 6 is all it needs.

## Rules

- `raw/` stays out of git ([plan D3](../docs/plan.md#open-decisions)). The manifests in
  `data/sources/` record each file and its SHA-256, so anyone can get and check the same files.
- Nothing from the downloads is run: the scripts read the files as data, Word opens them with
  macros off, and Python runs with `-I`.
- No script corrects COA. A figure is corrected only through `corrections.csv`, with its date,
  source and note ([data rules 4 and 12](../docs/data-rules.md)).
- Standard library only, except `pdf_pages.py`.
- Word is heavy. Run it through `word_list_numbers.ps1`, one report at a time, and don't save
  reports as text through Word: that stalled for over 8 minutes.
