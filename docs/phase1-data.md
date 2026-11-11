# Phase 1 data

COA's verdict, five headline figures, the count of past recommendations fixed, the number
of findings, the unsettled disallowances, and appropriations and obligations, for each of the
92 CY 2022–2025 reports. Pulled on 2026-11-07 and 2026-11-08 (CY 2025 on 2026-11-08, see
[CY 2025](#cy-2025)) by
[`scripts/extract_phase1.py`](../scripts/extract_phase1.py) from the files in `raw/` (see
[data-sources/coa-annual-audit-reports.md](data-sources/coa-annual-audit-reports.md)).

```
python -I scripts/extract_phase1.py
```

The disallowances also need the text of COA's executive summary PDFs, and Valencia CY 2023's
appropriations the text of its report PDF, saved once beside each PDF by
[`scripts/pdf_pages.py`](../scripts/pdf_pages.py) in a throwaway environment with `pypdf` and
`cryptography` ([below](#executive-summary-pdfs)).

## Files

| File | One row per | Columns |
| --- | --- | --- |
| [`data/phase1/verdicts.csv`](../data/phase1/verdicts.csv) | report | year, government, `verdict`, `opinion_quote` (COA's opinion paragraph, word for word), source |
| [`data/phase1/figures.csv`](../data/phase1/figures.csv) | report and figure | year, government, `figure`, `label_as_printed`, `amount_as_printed`, `amount` (the number we show), `correction_note` (empty unless corrected), source |
| [`data/phase1/prior-recommendations.csv`](../data/phase1/prior-recommendations.csv) | report | year, government, `total` and `fully_implemented` (the numbers we show), the other statuses COA gives, `total_as_printed`, `fully_implemented_as_printed`, `stated_in`, `quote` (COA's sentence, word for word), `correction_note`, source ([below](#past-recommendations)) |
| [`data/phase1/findings.csv`](../data/phase1/findings.csv) | finding | year, government, `number` (COA's), `numbered` (`Word list`, `typed`, or `PDF`), `observation` (the finding's opening paragraph, word for word), source ([below](#findings)) |
| [`data/phase1/finding-counts.csv`](../data/phase1/finding-counts.csv) | report | year, government, `findings` (the number we show), `numbers_as_printed`, `count_note` (empty unless COA's numbers don't run 1 to N), `numbered_after_findings` (numbers COA goes on to print on paragraphs with no recommendation), source |
| [`data/phase1/disallowances.csv`](../data/phase1/disallowances.csv) | report | year, government, `disallowances`, `suspensions`, `charges` (the numbers we show, unsettled at December 31; empty where the report doesn't give one), each as printed, COA's `total_as_printed`, `funds` (filled only where COA gives the funds separately with no total), `note`, `quote` (COA's words under the heading, word for word), source ([below](#unsettled-disallowances)) |
| [`data/phase1/disallowance-tables.csv`](../data/phase1/disallowance-tables.csv) | row of COA's table | year, government, `fund` (`all` unless COA splits by fund), `notice` (suspension, disallowance, charge or total), `label_as_printed`, `beginning`, `issued`, `settled`, `ending` as printed, `other_columns` (columns only some reports have), source. Only the table we cite; none where COA gives the balance in words |
| [`data/phase1/appropriations.csv`](../data/phase1/appropriations.csv) | report and fund | year, government, `fund` (General Fund, Special Education Fund, or COA's combined statement), `fund_as_printed`, `final_appropriations` and `obligations` (the numbers we show: the final budget for the current year and its obligations), `share_obligated` (our arithmetic), `current_from` (COA's row, COA's total, or our sum of its rows), then COA's current, continuing and total rows as printed (label, original, final, obligations), `note`, `correction_note` (empty unless corrected), source ([below](#appropriations-and-obligations)) |
| [`data/phase1/appropriation-tables.csv`](../data/phase1/appropriation-tables.csv) | row of COA's statement | year, government, `fund`, `section` (current or continuing), `row` (`line`, or COA's `current`, `continuing` or `total` row), `label_as_printed`, `original`, `final`, `diff_original_final`, `actual`, `diff_final_actual` as printed (a blank cell is left blank), `read` (how the amounts were placed in their columns), source. The appropriations only, not the revenue |
| [`data/phase1/checks.csv`](../data/phase1/checks.csv) | check | year, government, check, pass, FAIL or n/a (the check can't be run on that report), detail |
| [`data/phase1/pdf-reports.csv`](../data/phase1/pdf-reports.csv) | record | Valencia CY 2023, read by hand from the PDF (below), its findings, disallowances and appropriations included. The script merges it in |
| [`data/phase1/corrections.csv`](../data/phase1/corrections.csv) | correction | date, report, figure, what COA printed, the figure we show, where the correction comes from, and the note shown with it ([below](#corrections)). The script applies it |
| [`data/phase1/appendix-notes.csv`](../data/phase1/appendix-notes.csv) | note | date, report, fund, the appendix and the obligations it gives, and the note shown on the site where we keep the statement's figure (every appendix difference but Kitaotao CY 2024's, which is corrected; [below](#appropriations-and-obligations)). The script checks and applies it |
| [`data/phase1/errata.csv`](../data/phase1/errata.csv) | errata entry | date, report, errata file, where, what COA printed, what it should read ([below](#errata)). The script applies it |

The source columns on every row: `report_url` (COA's page for the ZIP), `file_in_zip`,
`file_sha256`, `part`, `item`, `toc_pages` (the page COA's own table of contents gives,
[plan D7](plan.md#open-decisions)) and, for PDFs only, `pdf_page`. Where a disallowance
balance comes from the executive summary, the source is COA's separate Executive Summary
PDF: `report_url` is COA's page for that PDF, `file_in_zip` is empty, `file_sha256` is the
PDF's and `pdf_page` its page.

## What we take, and from where

| Item | Where | How it's found |
| --- | --- | --- |
| Verdict | Part I, Independent Auditor's Report | The "Basis for … Opinion" heading: *Qualified*, *Adverse*, *Disclaimer of*, or none for an unmodified opinion. Some reports write "Bases for" or "Bases of" |
| Opinion quote | Same | The paragraph that starts "In our opinion" (or, for a disclaimer, "Because of the significance") |
| `total_assets`, `total_liabilities`, `net_assets_equity` | Part I, Statement of Financial Position | Current-year column of the total rows |
| `total_revenue`, `surplus_deficit` | Part I, Statement of Financial Performance | Current-year column of "Total Revenue" and "Surplus (Deficit) for the period" |
| Past recommendations fixed | Part III, Status of Implementation of Prior Years' Audit Recommendations | COA's sentence "Out of the N prior years' audit recommendations, M were fully implemented …", or the Total row of Part III's table by year of report ([below](#past-recommendations)) |
| Number of findings | Part II, Observations and Recommendations | Each numbered observation that has its own recommendation ([below](#findings)) |
| Unsettled disallowances | Part II or III where the report has it there, else the executive summary | COA's table (or sentence) of suspensions, disallowances and charges unsettled at December 31 ([below](#unsettled-disallowances)) |
| Appropriations and obligations | Part I, Statement of Comparison of Budget and Actual Amounts | Each fund's final budget for the current year and the actual amounts (obligations) beside it ([below](#appropriations-and-obligations)) |

The figures come from the audited statements, not the executive summary's "Financial
Highlights", for two reasons. The statements have pages in COA's table of contents; the
summary doesn't. And the summary's labels don't always mean the same thing: Baungon's
CY 2024 summary shows "Revenue" of 252,075,733.87, the statement's total revenue plus
transfers received, where the statement's "Total Revenue" is 238,349,115.37. The summary is
still used, as a check.

Amounts are kept as printed, including COA's typos ("629,837,996.7" in Damulog's CY 2024
statement), with the parsed number beside them ([data rule 4](data-rules.md)).

## Results

| | CY 2022 | CY 2023 | CY 2024 | CY 2025 |
| --- | --- | --- | --- | --- |
| Qualified | 23 | 22 | 23 | 23 |
| Disclaimer | | 1 (Kitaotao) | | |
| Adverse, unmodified | none | none | none | none |

In every report, the verdict in the auditor's report agrees with what the transmittal
letters and executive summary say COA rendered.

## Checks

Each report is checked three ways: the verdict and opinion paragraph are found; total
assets equal total liabilities plus equity; and each figure matches the executive
summary's highlights, at the precision the summary prints (the province's CY 2024
summary rounds to whole pesos). A summary "Surplus" that equals the statement's surplus
*from current operation* is accepted and noted (Baungon and Malitbog CY 2022, Kadingilan
all three years, Libona CY 2023).

Ten of these checks fail, and each is a difference inside COA's own report. The checks
run on the figures as printed, so they keep failing after a correction; a separate check
confirms the corrected statement balances. Only the Malitbog figure is corrected:

| Report | What differs | Reading |
| --- | --- | --- |
| Malitbog CY 2022 | The statement prints total liabilities as 817,000,032.58, the same figure as equity. Its own current-liabilities subtotal and the summary give 82,959,327.76, which balances the statement | Typo in the audited statement. Corrected (below) |
| Kalilangan CY 2022, CY 2023 | Summary assets and liabilities are 13,350,024.16 (2022) and 15,422,641.10 (2023) higher than the statement | The summary took its figures from the combined by-fund statement in the appendix, before inter-fund amounts were eliminated. The consolidated statement is the audited figure |
| Kibawe CY 2024 | Summary assets 1,045,571,335.84; statement 1,045,472,535.84 | The summary figure appears nowhere else in the report: a typo |
| Cabanglasan CY 2023 | Summary surplus (4,591,509.10); statement (4,951,509.10) | Digits swapped in the summary |
| Kalilangan CY 2024 | Summary surplus 7,153,752.15; statement 7,153,572.15 | Digits swapped in the summary |
| Province CY 2025 | Summary liabilities 2,869,987,707; statement 2,869,987,707.64 | The summary prints whole pesos and drops the centavos instead of rounding them. Not corrected: the statement is the figure we show |

## Past recommendations

Part III of each report lists the recommendations COA made in earlier years and whether
each was acted on. COA sums this up in one sentence, at the head of Part III and usually
again in the executive summary: "Out of the twenty-three (23) prior years' audit
recommendations, seventeen (17) were fully implemented and six (6) audit recommendations
are for implementation" (Maramag CY 2024). The site shows that as **17 of 23 fully
implemented**: `fully_implemented` of `total`, both COA's numbers.

`stated_in` says where each count comes from. Every one is from Part III, which has a page
in COA's table of contents:

| Source | Reports |
| --- | --- |
| COA's sentence in Part III, quoted in `quote` | 88, including Valencia CY 2023, read by hand from the PDF (PDF p. 118, COA p. 102) |
| The Total row of Part III's table by year of report | Province CY 2022 and CY 2024. Neither sums up in a sentence; the executive summary takes each earlier report in turn |
| Our count of Part III's status column | Province CY 2023 and CY 2025, which have neither a sentence nor a table total. In CY 2023 COA numbers each status in the table, from "Fully Implemented1" to "Fully Implemented83" and "Not Implemented1" to "Not Implemented20", and the executive summary's figures by year of report add up to the same 83 of 103 (39 + 42 + 1 + 1 of 44 + 56 + 1 + 2) |

Quezon CY 2022's table of contents gives Part III as pages "116-113". It is kept as
printed.

### What the numbers mean

- **`total` is the number COA says it evaluated, and what goes into it varies**, so a total
  in one report isn't like-for-like with another. Some reports count every earlier
  recommendation still open. Others leave out those repeated in this year's Part II ("Of
  the Ninety-Nine (99) remaining prior years' audit recommendations, excluding the One (1)
  reiterated recommendation", Lantapan CY 2024). Where COA writes "only N were evaluated",
  N is the total (Lantapan CY 2022 and CY 2023, San Fernando all three years, Cabanglasan
  CY 2023).
- **The statuses changed in CY 2023.** CY 2022 reports use fully, partially and not
  implemented. Most later reports use "fully implemented" and "for implementation"; some
  keep "not implemented". Don Carlos (all three years), Kitaotao (CY 2023 and CY 2024) and
  Lantapan (CY 2024) write plain "implemented", counted as fully implemented.
- **Closed.** Impasug-ong, Libona and Manolo Fortich (CY 2023 and CY 2024) also count
  recommendations as "closed", for example because this year's report takes them up again
  as a new finding. COA keeps those in the total and in its own compliance rate
  (Impasug-ong CY 2023: 31 of 66, "computed at 47 percent").
- **CY 2025 counts observations, then recommendations.** Most CY 2025 reports write "Out of
  the 36 prior years' audit observations with 217 number of recommendations, 146 have been
  fully implemented and 71 are for implementation" (Dangcagan). The statuses count
  recommendations, so `total` is the recommendations (217), not the observations. Variants:
  "26 prior year's audit recommendations with 75 Audit Recommendations (ARs), 43 ARs have
  been…" (Baungon), "fifty-six (56) or 84 percent were fully implemented" (Maramag). Don
  Carlos spells "fourty four (44)", read as 44.
- **`reiterated` is filled only where COA counts reiterated recommendations in the total
  without another status:** Kitaotao CY 2024 (19 implemented + 13 for implementation + 1
  reiterated = 33) and the province CY 2024 (69 fully implemented + 20 not implemented = 89;
  its table splits "Not Implemented" into two columns, 10 "Reiterated in Part II" and 10 "Not
  implemented", which are `reiterated` and `not_implemented`). Elsewhere a reiterated count is part of another status or
  outside the total, and is left in the quote.

### Checks

| Check | Compares | n/a when |
| --- | --- | --- |
| Words match numerals | Each count's words and figure, "seventeen (17)" | The count comes from a table |
| Statuses add up to the total | The statuses COA gives, against its total | |
| Executive summary agrees with Part III | Total and fully implemented | The summary has no total: Baungon, Don Carlos, Kibawe, Kitaotao, Malitbog and Talakag CY 2024, and the province, whose summary goes year by year |
| Executive summary words match numerals | As above, in the summary's sentence | Same |
| Part III table agrees | The Total row of the table by year of report, where there is one | No such table, or it is the source |
| Our count of the Part III status column agrees | Fully implemented only: the column also holds notes and notices that make the other counts unreliable | The count is the source (province CY 2023), or the table sits inside another table, which the script doesn't read (San Fernando CY 2023) |

Nineteen of these checks fail. Sixteen are differences inside COA's report; the other three
are our count of the status column, which undercounts in CY 2025 (last row):

| Report | What differs | Reading |
| --- | --- | --- |
| Malitbog CY 2022 | The total is "thirty-one (30)" in Part III and the summary. Part III's rows mark 12 fully implemented, 16 partially and 2 not; the sentence says 11, 17 and 2 | The sentence's statuses add up to 30 and the table lists 30: corrected to 30 (below). The 11 fully implemented is COA's stated figure; the rows don't settle it |
| Manolo Fortich CY 2022 | The total is "twenty (26)" in both places, and the sentence's statuses add up to 24 (16 fully, 8 partially) | Part III's table lists 26, including 2 not implemented that the sentence leaves out. Corrected to 26 |
| Kibawe CY 2024 | "thirteen (10)" fully implemented | 10 + 11 for implementation = 21, the total, and Part III's table shows 10. Corrected to 10 |
| San Fernando CY 2024 | "fifty-five (56)" fully implemented and "fifty-eight (57)" not implemented, in both places | Either pair adds up to 113. Part III's table numbers each status, ending at Implemented56 and Not Implemented57. Corrected to 56 and 57 |
| Kibawe CY 2023 | Summary 12 of 19; Part III 13 of 19 | The summary's 12 + 6 is 18. Part III's sentence and table say 13, which we show |
| Cabanglasan CY 2022 | Part III's rows mark 15 fully implemented and 6 partially; its sentence and its table by year say 14 and 7 | We show COA's stated 14 |
| Kitaotao CY 2023 | Part III's rows mark 9 implemented; COA says 10 | One row's status column reads only "Reply for For audit evaluation and/or action." |
| Maramag CY 2024 | Part III's rows mark 16 fully implemented; COA says 17 | Observation 14's status is blank |
| Manolo Fortich CY 2025 | Part III's sentence: 17 fully implemented, 32 unimplemented and 19 closed, of 68. Part III's table by year of report and the executive summary: 32 of 61 | The table's rows each add up (CY 2024: 44 = 26 + 12 + 6), its earlier years add to the 17 that the CY 2024 report left unimplemented, and the executive summary agrees with it (32 fully implemented, 29 unimplemented, of 61). The sentence uses CY 2024's wording with the table's 32 and 17 swapped, and its 68 and 19 closed are nowhere else in the report. Corrected to 32 of 61 ([corrections](#corrections)), decided 2026-11-08 |
| Damulog, Don Carlos, Kitaotao CY 2025 | Our count of the status column: 63, 13 and 15 fully implemented; COA's sentence: 62, 44 and 61 | Not COA's: these reports put the status of each of an observation's recommendations in one cell ("Implemented Implemented Implemented Implemented"), and our count reads one per paragraph. The sentence is the figure we show |

## Findings

Part II of each report sets out what COA found, one numbered observation at a time, each
followed by COA's recommendation and usually management's comment. Decided 2026-11-07: the
site shows how many there are, and **14 findings** means 14 numbered observations in Part II,
each with its own recommendation ([data rule 6](data-rules.md)). We count them rather than
take the last number COA prints, because that number often goes past the last finding (below).

`findings.csv` has one row per finding: COA's number, and the finding's opening paragraph,
which states it, word for word ("Advance payments aggregating to ₱ 3,114,889.50 were made to
suppliers for the procurement of "goods" despite …", Maramag CY 2024, observation 6). A
number typed into the text is left out of the quote. `finding-counts.csv` has the count per
report.

| | CY 2022 | CY 2023 | CY 2024 | CY 2025 |
| --- | --- | --- | --- | --- |
| Findings, all 23 reports | 307 | 349 | 332 | 310 |
| Fewest | 7 (Cabanglasan) | 7 (Kalilangan) | 7 (Libona) | 7 (Libona) |
| Most | 22 (province) | 26 (province) | 26 (San Fernando) | 25 (Lantapan, San Fernando) |

### How Part II numbers its findings

Surveyed in all 69 reports on 2026-11-07, before the rule was decided.

- **The numbers run 1, 2, 3 … straight through Part II**, across its sections: financial audit
  and compliance audit (most CY 2022 reports), "Other Areas" (CY 2023), "Other Financial
  Related Issues" (CY 2024), COVID-19 transactions, and topic headings such as "Cash
  Advances" (Malaybalay, Sumilao). No report starts again at 1.
- **A finding with several parts is one finding.** The parts are lettered or numbered inside
  it: a and b, A to G (province CY 2024, observation 7), I to IV, 1.1 and 1.2.
- **Most numbers are Word list numbers**, which aren't in the file's text: Word works them out
  when it shows the file. 54 Word reports use only list numbers, 1 only typed numbers, and 13
  both. Of the 968 findings in Word reports, 849 have list numbers and 119 typed ones.
- **25 reports go on numbering after the last finding** (15 in CY 2022–2024, 10 in CY 2025), on paragraphs or headings with no
  recommendation: notes that taxes and GSIS, PhilHealth and Pag-IBIG contributions were
  remitted, on GAD, the Special Education Fund, the 20% development fund and the disaster
  fund, and the status of disallowances. In Malaybalay CY 2022 the headings themselves are
  numbered, "19. Special Education Fund (SEF)" to "24. Status of Audit Suspensions,
  Disallowances and Charges"; also Lantapan CY 2024 and Sumilao CY 2023. These aren't
  findings. `numbered_after_findings` keeps COA's numbers, so a reader holding the report can
  see why our count is lower:

  | Report | Findings | COA goes on to number |
  | --- | --- | --- |
  | Province CY 2022, 2023, 2024 | 22, 26, 16 | 23–29, 27–33, 17–26 |
  | Malaybalay CY 2022, 2023, 2024 | 18, 17, 18 | 19–24, 18–23, 19–21 |
  | Sumilao CY 2023, 2024 | 12, 14 | 13–15, 15–18 |
  | Valencia CY 2023, 2024 | 20, 22 | 21–24, 23–32 |
  | Cabanglasan CY 2024 | 8 | 9–24 |
  | Impasug-ong CY 2024 | 19 | 20–34 |
  | Lantapan CY 2024 | 18 | 19–22 |
  | Manolo Fortich CY 2024 | 15 | 16–32 |
  | San Fernando CY 2024 | 26 | 27–38 |
  | CY 2025: province, Cabanglasan, Impasug-ong, Lantapan | 18, 9, 12, 25 | 19–30, 10–20, 13–29, 26–36 |
  | CY 2025: Libona, Malaybalay, Manolo Fortich | 7, 15, 8 | 8–21, 16–26, 9–26 |
  | CY 2025: San Fernando, Sumilao, Valencia | 25, 12, 19 | 26–37, 13–18, 20–27 |

- **No unnumbered section has a recommendation**, so counting numbered observations only
  leaves out no finding.
- **Don Carlos CY 2023 skips 5.** A quoted list inside observation 4 (the copies of a bank
  statement) ends with an automatically numbered "5. Quintuplicate - Provincial/City/Municipal
  Accountant", and the next observation carries on that list as "6. The Real Property Tax
  (RPT) and Special Education Tax (SET) Receivable …". So the report has 10 findings numbered
  1–4 and 6–11, and `count_note` says so. Its executive summary numbers the same finding 5.
  Nothing is corrected: COA prints no count.

### How the script finds them

1. Part II runs from its heading to Part III's.
2. A paragraph outside a table, at least 60 characters long and opening with a whole number
   (a Word list number, or typed), may be an observation.
3. The findings are the longest run of these numbered 1, 2, 3 … with a recommendation
   between each pair: a "Recommendation(s)" heading, or a paragraph beginning "We recommend
   …" or "It is recommended …". A list inside one observation never has one between its
   items. A repeated, skipped or restarted number is allowed at a cost, so COA's slips show in
   the checks.
4. The last finding needs a recommendation of its own before Part II ends; a numbered note
   after it has none.

The script works out Word's list numbers itself, from the file's numbering definitions, the
way Word does. On 2026-11-07 they were checked against Word with
[`scripts/word_list_numbers.ps1`](../scripts/word_list_numbers.ps1), which opens each report
in Word and saves the number Word shows on every list paragraph beside the report in `raw/`
(`<report>.word-lists.tsv`). All 849 list-numbered findings match. On 2026-11-08 the same was
done for the 23 CY 2025 reports, and all 247 list-numbered findings match (63 more are typed).
Quezon CY 2025's observation 4 sits on a list level formatted "none" whose text is "%1.", the
counter of the level above: Word shows "4.", and the script takes the number as Word builds it,
whatever the level's own format (before that fix it read 1–3, 5–11). Of all 18,937 list numbers
in the 68 Word reports, 18,918 match; the 19 that don't are in lists inside findings
(lettered recommendations, quoted circulars, "4.1" where Word shows "5.1"), and none is a
finding's number.

### Checks

| Check | Compares | n/a when |
| --- | --- | --- |
| Findings found | At least one numbered observation with a recommendation | |
| COA's numbers run 1 to N | The numbers on the findings found | |
| Part II's pages in the table of contents | | |
| Numbers match Word's | Each list number the script works out on a finding, against the one Word shows | Word's numbers aren't saved for the report, every number is typed, or the report is a PDF |

One fails, Don Carlos CY 2023, above.

`toc_pages` is Part II's range in COA's table of contents: from the first page it gives under
Part II to the last, or to the page before Part III where it gives only start pages
(Malaybalay CY 2022 lists Financial Audit 61, Compliance Audit 110, Other Matters 183 and
Part III 185, so 61–184). A finding gets its own page in Phase 2 ([plan D7](plan.md#open-decisions)).

### What the count means

- **It is COA's unit.** One finding can hold several issues (parts A to G), and how COA splits
  what it found into observations differs between audit teams and years.
- **The action plans don't give the same count.** Each government's Agency Action Plan
  (AAPSI, CY 2023 and 2024) lists the current year's findings too, but they range from 3 to 74
  pages and their text doesn't come out in a form we can count for most of them. Maramag's
  CY 2024 plan lists 15, one of them (the Local School Board's reporting on the Special
  Education Fund) found nowhere in the report. The count comes from the report.

## Unsettled disallowances

COA keeps a running record of the notices it issues to each government, the Statement of
Audit Suspensions, Disallowances and Charges (SASDC), and every report gives the balance
still unsettled at December 31:

- **Notice of suspension (NS):** COA holds a payment until missing documents or explanations
  come in. It is lifted when they do, or becomes a disallowance.
- **Notice of disallowance (ND):** COA rules the spending improper, and the persons liable must
  pay it back.
- **Notice of charge (NC):** COA finds that money due to the government wasn't collected, or
  was under-collected. No report has an unsettled charge.

Decided 2026-11-08:

1. **The site shows the disallowances**, as "Disallowances not yet settled". Suspensions and
   charges get their own lines and are never added in: a suspension isn't a ruling, and the
   province's ₱136,808,527.29 total is ₱135,736,327.29 of suspensions. COA's total stays in
   the CSV as printed.
2. **Where a report gives the balance only in its executive summary**, the source is COA's
   separate Executive Summary PDF and its page ([plan D7](plan.md#open-decisions) already
   gives PDFs their real page), checked against the copy inside the Word report.
3. **Where a report gives no balance**, the site shows a dash and COA's words. Neither the
   government's receivable nor the next report's opening balance stands in for it.

`disallowances.csv` has one row per report: the three balances we show, COA's words under the
heading in `quote`, and a `note` where something needs saying. `disallowance-tables.csv` has
COA's table row by row, for the report's cited table only.

### How the reports show them

Surveyed in all 69 reports on 2026-11-08, before the rules were decided.

| Taken from | CY 2022 | CY 2023 | CY 2024 | CY 2025 |
| --- | --- | --- | --- | --- |
| Executive summary (the body of the report doesn't have it) | 21 | 11, including Valencia's PDF report | 6 | 5, including Pangantucan's (below) |
| Part II (most also in the summary) | 2 | 12 | 2 | 18 |
| Part III, section B | | | 15 | |

CY 2024 moved it into Part III, and most CY 2024 summaries dropped it. CY 2025 has it in Part
II again.

Pangantucan's CY 2025 Part II rounds the balances to millions ("0.333 million"); its executive
summary gives them in pesos and centavos (332,940.58). Since rule 4 keeps amounts as printed to
the centavo, a section whose year-end balances can't all be read exactly comes after one whose
can, and Pangantucan's figures come from the executive summary (PDF p. 5). The headings vary:
"Summary of NS, ND, NC Issued During the Year", "Status of Audit Suspensions, Disallowances and
Charges", "Summary of Notice of Suspension, Notice of Disallowance and Notice of Charge",
"Notice of Suspensions, Disallowances, and Charges". Only four tables of contents list the
section itself (Don Carlos, Kadingilan, Kibawe and Maramag, all CY 2024); elsewhere
`toc_pages` is the pages of the part it sits in.

- **Most reports** print one row per notice and a total, with columns for the balance at the
  start of the year, issued, settled, and the balance at December 31. The settled column may
  be "Settlement", "NSSDC" (notices of settlement) or "Settle-ments ND/NS/NC". Sumilao adds
  "Matured to ND"; San Fernando CY 2022 adds "Error in Previous AAR" and "Adjusted Beginning
  Balance". Manolo Fortich, Sumilao and Impasug-ong CY 2023 have no charge row, so `charges`
  is empty for them.
- **Notices across, balances down, one table per fund:** Damulog, Valencia, and Pangantucan
  CY 2023 and 2024.
- **Each fund, then all funds:** Baungon CY 2023–24, Talakag CY 2023–24, Malitbog CY 2024. We
  take the all-funds rows.
- **The year-end balance only:** Kibawe (all three years), Maramag CY 2024, Dangcagan CY 2023
  (in Part II; its summary has the full table). `beginning`, `issued` and `settled` are empty
  because the table has no such columns.
- **In words:** Maramag CY 2022–23 ("has an outstanding Notice of Suspensions and
  Disallowances in the amount of P11,439,050.25 and P7,674,912.61 as of December 31, 2022,
  respectively"), Quezon CY 2022–24, Kalilangan CY 2024 ("stood at P0.00").
- **No balance:** Kalilangan CY 2022 and 2023 and Pangantucan CY 2022 say only that nothing was
  issued during the year, then give the receivable on the government's books (below).

### How the script finds them

1. A heading: a paragraph under 200 characters, outside a table and the table of contents,
   reading "Summary of …" or "Status of …" and naming suspensions and disallowances (or NS and
   ND), or "Notice of Suspensions, Disallowances …". Before the table of contents is the
   executive summary; after Part II's heading, Part II or III.
2. What follows, up to the next heading ("Status of Implementation …", a part, an annex) or
   ten blocks: COA's paragraphs, and any table whose rows or columns name the notices.
3. Columns are read from their headings, laid on the table's grid so a heading spanning two
   columns lines up with both. "Ending", "Unsettled" or December 31 of the year audited mean
   the year-end balance; "Beginning", "Beg. Bal." or a date in the year before mean the
   opening balance. The province's CY 2022 Part II table dates both balance columns
   "Balance 12/31/2021", so the last is taken as the year-end balance, and the check's detail
   says so.
4. With no table, COA's sentence: "has an outstanding … in the amount of …", "has no
   outstanding …", "stood at P0.00".
5. Of several sections in one report, one with a balance comes first, then Part II or III over
   the executive summary.

### What the numbers mean

- **A dash or a blank cell in COA's table means nil**, and COA's totals bear this out
  (Baungon: disallowances "-", total equal to the suspensions). We show 0.00. That is not our
  own dash ([data rule 4](data-rules.md)), which means the report doesn't give the figure.
- **Settlements** printed in brackets, "(10,400.00)", or with a minus after, "144,630.00-", are
  read as amounts settled.
- **Unsettled includes disallowances under appeal.** Malaybalay's ₱2.935 million of its
  ₱3,010,067.91 awaits a decision on appeal; the province's ₱1,072,200.00 is "currently under
  appeal"; Sumilao filed appeal memoranda for ₱4,212,663.92 (CY 2022) and ₱3,655,582.97
  (CY 2023). COA's words in `quote` say so where it does.
- **Funds.** Damulog, Valencia and Pangantucan give the funds separately with no total.
  Disallowances outside the General Fund are nil in every one, so `disallowances` is never a
  sum of ours. Valencia's CY 2022 suspensions are: the General Fund's 387,400.00 and the Trust
  Fund's 3,174,983.50, added by us to 3,562,383.50, and the note says so.
- **Not the receivable.** The notes to the statements carry "Receivables – Disallowances and
  Charges", the government's own record of amounts due from persons liable under final
  disallowances. It isn't COA's balance and can differ: Cabanglasan's books carry
  ₱1,837,776.76 where COA's balance is nil (a CY 2024 finding is about that account), and
  Kalilangan's ₱4,562,225.95 dates from the 1970s and 1980s. It isn't pulled; where COA's words
  mention it, the note says what it is.

### Results

| | CY 2022 | CY 2023 | CY 2024 | CY 2025 |
| --- | --- | --- | --- | --- |
| Disallowances unsettled | 18 | 17 | 17 | 18 |
| None | 3 | 5 | 6 | 5 |
| Not given | 2 (Kalilangan, Pangantucan) | 1 (Kalilangan) | | |
| Largest | Talakag 14,223,727.47 | Talakag 14,223,727.47 | Talakag 14,223,727.47 | Malaybalay 79,438,191.21 |
| Smallest | Don Carlos 51,100.00 | Don Carlos 51,100.00 | Valencia 43,500.00 | Valencia 43,500.00 |
| Suspensions unsettled | 13 | 14 | 15 | 14 |

The largest suspension balance is the province's ₱135,736,327.29 in all four years.
Malaybalay's rose from ₱15,093,621.32 to ₱53,001,224.36 in CY 2024, with ₱37,907,603.04 issued
over "the en masse grant of monetary incentive to all regular and casual employees". In CY 2025
₱76,428,123.30 of its suspensions over that grant became a disallowance: its table shows them
settled as suspensions and issued as a disallowance, taking disallowances from ₱3,010,067.91 to
₱79,438,191.21 and suspensions back to ₱15,093,621.32.

### Checks

| Check | Compares | n/a when |
| --- | --- | --- |
| Balance found | A table or sentence giving the year-end balance | |
| Rows add across | Opening balance (the adjusted one where COA gives it) + issued − settled = year-end balance, each row | The table gives year-end balances only, or the balance is in words |
| Notices add to COA's total | Suspensions + disallowances + charges against the total row, each column | No total row |
| Funds add to all funds | Each fund's rows against the all-funds rows | Not split by fund, or no all-funds rows |
| COA's sentence agrees with the table | Each amount in COA's words before the table is in the table | No amount there |
| Executive summary agrees | The summary's year-end balances against Part II or III | The summary is the source, or doesn't give them |
| Executive summary PDF shows the same amounts | Every amount in the Word copy is on the PDF page cited, or the next | Taken from Part II or III |
| Opens at last report's balance | Each opening balance against the last report's year-end balance | CY 2022, or either isn't given |

Every report opens at the last report's balance where both are given. Fourteen checks fail,
none of them on a figure we show, so nothing is corrected:

| Report | What differs | Reading |
| --- | --- | --- |
| Kalilangan CY 2022 and 2023, Pangantucan CY 2022 | No balance | A dash, with COA's words. The note says what the next report opens with: Kalilangan's CY 2024 report says there were none at January 1, 2024; Pangantucan's CY 2023 report opens the General Fund at nil |
| San Fernando CY 2022 | The total row opens at ₱9,213,064.38 and closes at ₱8,773,066.53; the notices add to 8,773,066.53 and 8,770,466.53 | The total's year-end figure is the two opening balances before COA's adjustment. Each notice's row adds up, and the CY 2023 report opens at 8,770,466.53 |
| Kitaotao CY 2023 | The total row leaves out the ₱596,400.00 of suspensions issued, so it doesn't add across. COA's sentence says no suspensions were issued that year | The suspension row adds up, and the CY 2024 report says the ₱596,400.00 "pertains to the present administration" |
| Libona CY 2023 and 2024 | The total row opens at 9,542,500.00; suspensions and disallowances add to 9,542,000.00 | A typo in the total's opening balance. The year-end total agrees |
| Dangcagan CY 2024 | The total row leaves blank the ₱814,733.73 of disallowances settled | The disallowance row adds up |
| Sumilao CY 2025 | COA's sentence gives ₱8,739,538.47, which isn't in the table | The table has no total row; the sentence's figure is its suspensions and disallowances added (1,030,490.67 + 7,709,047.80) |

Also read and left alone: Kalilangan's CY 2024 Part II repeats the CY 2023 paragraph ("As of
December 31, 2023, the Receivables- Disallowances and Charges account …"); its balance comes
from Part III, section B.

### Executive summary PDFs

COA posts each report's executive summary as a separate PDF, 4 to 8 pages, locked with an
owner password (AES). [`scripts/pdf_pages.py`](../scripts/pdf_pages.py) saves each one's text,
page by page, beside it in `raw/` (`<name>.pages.txt`); it needs `pypdf` and `cryptography`,
which aren't dependencies of the repo, so it runs in a throwaway environment. The extractor
finds the page carrying the section's heading and checks that every amount in the Word
report's copy is on it or the next page. All 38 reports taken from the executive summary
pass, on PDF pages 4 to 7.

The script also saves the text of the one report that is a PDF (Valencia CY 2023), so the
appropriations read from it by hand can be checked against the pages they cite.

## Appropriations and obligations

Every report's Part I has a Statement of Comparison of Budget and Actual Amounts. For each
fund it sets the budget beside what was done with it:

- **Appropriations** are what the local council authorized the government to spend, in its
  annual budget and any supplemental budgets.
- **Current appropriations** are the year's own budget. **Continuing appropriations** are
  earlier years' appropriations for capital outlay and the like that the law lets the
  government still use.
- The **original** budget is the one enacted for the year; the **final** budget includes the
  supplemental budgets and changes made during the year.
- The **actual amounts** beside the appropriations are the **obligations**: what the
  government committed itself to pay (contracts awarded, salaries due, orders placed), not
  what it paid out.

Decided 2026-11-08:

1. **The site shows the final budget for the current year against its obligations.** It is
   the figure COA's own executive summaries lead with, and the budget the year's obligations
   are measured against. The final budget includes the supplemental budgets (Maramag passed
   three in CY 2022, ₱120,625,476.69 in all). Continuing appropriations aren't a reliable
   headline, because some statements leave them out (below). Original, continuing and total
   figures stay in the CSV as printed.
2. **Each fund on its own line, as COA prints it, never added together.** The General Fund
   is the main line; the Special Education Fund has its own. Where COA gives the two funds
   only in one statement (Cabanglasan CY 2022, Malaybalay CY 2023 and 2024), the site shows
   COA's combined line with its label and a note.
3. **The share obligated is shown, labeled as our arithmetic** ("73.1% obligated":
   obligations ÷ final budget, to one decimal). The About page says that money not obligated
   isn't necessarily saved or wasted. Where obligations exceed the final budget (Pangantucan
   CY 2023), or equal it to the centavo, the note says so. Kitaotao CY 2024's statement prints
   obligations equal to the final budget, in both funds and on every line; the same report's
   appendix gives the obligations, and we show those ([corrections](#corrections)).
4. **Where COA prints no total for current appropriations, we add up its rows under Current
   Appropriations**, with a note saying so, and check the sum against COA's total and the
   executive summary. Where the statement also lists no continuing appropriations, COA's own
   total is the current year's and is used instead, with a note.

`appropriations.csv` has one row per report and fund; `appropriation-tables.csv` has COA's
rows of appropriations, so every sum of ours can be redone.

### How the reports show them

Surveyed in all 69 reports on 2026-11-08, before the rules were decided.

All 68 Word reports list the statement in their table of contents, with its pages; Valencia
CY 2023's PDF has it on PDF pp. 28–31 (COA pp. 14–18). The usual layout, in about 60 of the
69 reports: a statement per fund, the General Fund then the Special Education Fund, each with
its revenue, then its appropriations under "Current Appropriations" and "Continuing
Appropriations", with a total row for each and a Total Appropriations row. Five columns:
original budget, final budget, difference between the two, actual amounts, difference between
the final budget and the actual amounts. Some reports subtract one way, some the other.

The actual amounts are obligations: the executive summaries that give both figures call them
"Obligations" and agree with the statement (below), and Valencia CY 2024 prints a "Summary on
Appropriations vs. Obligations" equal to its statement.

| How it varies | Reports |
| --- | --- |
| No total for current appropriations, only one for current and continuing together | Cabanglasan 2022 (its combined statement) and 2023–24 (General Fund), Kalilangan 2022 and 2024 (both funds), Pangantucan 2022 (both funds), Maramag 2023–24 (SEF) |
| No total for current appropriations and no continuing appropriations listed: COA's total is the current year's | Valencia 2023 (General Fund, PDF), Cabanglasan 2023–24 (SEF) |
| The two funds in one statement | Cabanglasan 2022 ("General Fund and Special Education Fund"), Malaybalay 2023–24 ("Consolidated") |
| The fund isn't named | Don Carlos 2022–24, Cabanglasan 2023–24, Sumilao 2022–24: the statement before the SEF's, or the only one. We call it the General Fund, and the note says COA doesn't name it |
| No SEF statement | Sumilao 2022–23 |
| The statement is a picture | Sumilao 2022–23: an EMF picture in the Word file, whose text records the script reads |
| The SEF's table sits inside a cell of the General Fund's | Damulog 2023–24 |
| Two rows in one cell | Province 2023 SEF: "Capital Outlay Total Current Appropriations", each cell holding both amounts; its total is labeled just "Total" |
| CY 2022 and CY 2021 columns side by side | Don Carlos 2022 |
| An extra empty column | Province 2024 SEF |
| Other labels | "Statement of Comparison of Budgeted and Actual Amounts" (Lantapan 2024), "General Fundnd" (Maramag), "Total Current Approrpiations" (6 rows), "Total Expenses Current Approrpiations" and "Total Expenses Current & Continuing" (Kalilangan 2023 SEF), "Total Expenditures" for the total (14 rows) |
| Revenue side lists "Continuing Appropriation" and "Total Sources" | Kalilangan 2024 |

**COA's General Fund can include the economic enterprises.** Valencia's CY 2022 executive
summary gives the General Fund (₱2,036,214,714.83) and the Economic Enterprise
(₱83,496,954.79) separately; its statement's General Fund is the two together
(₱2,119,711,669.62). Pangantucan CY 2022 lists Economic Enterprises as an office inside the
General Fund. We show the General Fund as COA's statement gives it.

**Some statements leave out continuing appropriations that the executive summary gives**,
from COA's Statement of Appropriations, Allotments, Obligations and Balances: Valencia
CY 2022 (General Fund ₱185,812,058.10, SEF ₱25,450,000.00) and Malaybalay CY 2023
(₱1,266,926,637.78 and ₱44,243,175.96) and 2024. The statement shows a dash; the note gives
the summary's figures. That statement is an annex in only about 15 reports, so it isn't used.

### How the script finds them

1. **The statement:** in Part I (after the table of contents and the auditor's report
   heading), the first paragraph or table titled "Statement(s) of Comparison of Budget(s)
   (or Budgeted) and Actual Amounts", read up to the notes to the financial statements (or
   the reconciliation, or Valencia's summary tables, that some reports put after it). Where
   there is none, the Word file's EMF pictures are searched for the title.
2. **Columns:** read from their headings laid on the table's grid, so a heading spanning two
   columns lines up with both. "Original", "Final", "Actual" (or "Obligations"), and
   "Difference": before the actual amounts it is the difference between the original and
   final budgets, after them between the final budget and the actual amounts. "Budgeted
   Amounts" alone heads the original budget (the province). A column headed with another year
   is skipped (Don Carlos CY 2022's 2021 columns). Headings repeated on a new page are read
   again.
3. **Placing the amounts:** COA's cells don't always sit under their headings, so the reading
   whose own differences agree with its amounts is taken: the amounts in order when the row
   has one per column (most rows), else each cell under the column it sits in, where one cell
   spanning the original and final columns counts for both (COA merges them when they are
   equal), else in order with an empty column's dash skipped (the province's CY 2024 SEF),
   else the placing of a row with blank cells that its arithmetic allows, with the blanks as
   nil. `read` in `appropriation-tables.csv` says which.
4. **Funds and sections:** a heading or a heading row naming the fund starts its rows; headings
   "Current Appropriations", "Continuing Appropriations" and "Expenditures" start their
   sections. COA's total rows are found by their labels, typos included.
5. **The figures:** COA's "Total Current Appropriations" row where it prints one; else, where
   it lists no continuing appropriations, its total row; else our sum of its rows under
   Current Appropriations (or Expenditures, where there is no "Current" heading).

### What the numbers mean

- **Obligations aren't payments.** An obligation commits the money; it may be paid the next
  year. They aren't savings either: an unobligated balance can lapse, revert or continue,
  depending on the appropriation.
- **A dash or a blank cell in COA's statement means nil**, and the rows' differences bear this
  out, as in the disallowance tables ([data rule 4](data-rules.md)). Kitaotao's CY 2022 SEF
  prints its final budget as a dash in every row, with obligations of ₱931,464.97 against an
  original budget of ₱1,514,724.00; we show the dash's nil, and the note says the share
  can't be worked out.
- **Our sums.** Cabanglasan CY 2022 (General Fund and SEF together, 22 rows), CY 2023 and 2024
  (General Fund, 35 and 24 rows), Kalilangan CY 2022 (22 and 2 rows) and 2024 (22 and 2),
  Pangantucan CY 2022 (23 and 3), Maramag CY 2023 and 2024 (SEF, 3 rows each). In every one,
  our current sum plus the continuing appropriations gives COA's total to the centavo.
  Cabanglasan's CY 2023 executive summary splits the same total differently: current
  ₱210,063,140.87 and continuing ₱26,003,987.46, where the statement's rows give
  ₱212,352,152.49 and ₱23,714,975.84. The statement is the source; the check shows the
  difference.

### Results

| | CY 2022 | CY 2023 | CY 2024 | CY 2025 |
| --- | --- | --- | --- | --- |
| Reports | 23 | 23 | 23 | 23 |
| General Fund (or COA's combined statement) | 23 | 23 | 23 | 23 |
| Special Education Fund on its own | 21 | 21 | 22 | 21 |
| Funds | 44 | 44 | 45 | 44 |
| Current year from COA's current total | 39 | 40 | 40 | 40 |
| From COA's total (no continuing listed) | | 2 (Valencia's PDF, Cabanglasan SEF) | 1 (Cabanglasan SEF) | 2 (Cabanglasan SEF, Sumilao) |
| Our sum of COA's rows | 5 | 2 | 4 | 2 (Cabanglasan GF, Maramag SEF) |
| General Fund share obligated, range | 57.6–87.9% | 66.5–102.6% | 60.8–93.3% | 56.9–92.5% |

The province's General Fund has the largest budget, ₱5,651,422,777.19 to ₱6,397,879,806.97
over the four years.

**CY 2025 layouts** the script now reads:

- **Dangcagan** titles the statement "Statement of Budget and Actual Amounts", without
  "Comparison of". The title pattern allows that, but not "Comparison Statement of Budget and
  Actual", which heads the notes' reconciliation table (Sumilao).
- **The province** labels its current totals "Total Current" (General Fund) and "Total- Current"
  (SEF). Read as rows at first, they doubled our sum of the General Fund (₱12.8 billion).
- **Kibawe** sets its Statement of Management Responsibility in a Word table, and the letter
  names "the related Statement of Financial Performance" and the "Statement of Comparison of
  Budget and Actual Amounts". A statement's title now counts only as a heading (a short row), not
  in a paragraph of prose. Its statements are "Consolidated Condensed".
- **Pangantucan** leaves the original-to-final difference blank on rows where the budget changed
  ("112,909,219.50 | 129,366,223.86 | | 120,341,183.68 | 9,025,040.18"). Where the other difference
  places every amount one way only, the row is read that way, the blank left blank (`read`: "in
  order, a blank difference left blank, placed by the row's arithmetic"), unless a reading the
  row's arithmetic doesn't contradict is already there.
- **Sumilao** gives one consolidated statement for both funds, with no continuing
  appropriations, so COA's total is the current year's (CY 2022–2023 were pictures of an unnamed
  fund only, CY 2024 an unnamed fund and the SEF).
- **Malaybalay** keeps its consolidated statement.

### Checks

| Check | Compares | n/a when |
| --- | --- | --- |
| Page in the table of contents | COA's table of contents lists the statement with its pages | |
| Statement found | The statement and its funds are found | |
| Current-year figures found | Every fund has a final budget and obligations for the current year | |
| Rows add across | In every row of appropriations, final − original and final − actual give the printed differences (sign aside) | |
| Current + continuing = total | For original, final and actual amounts: COA's current total (or our sum) plus COA's continuing total (or its rows) against COA's total | The fund has only one total |
| Obligations within the final budget | Obligations against the final budget, each fund | |
| Executive summary agrees | Every current-year figure is in the executive summary's highlights: each fund's, or two of the summary's amounts that add to it, or the funds together, or with continuing appropriations included (the statement's total). A fund the highlights don't name isn't held against them; where they give appropriations only, obligations aren't looked for | The highlights give no appropriations (21 reports) |
| Report PDF shows the same amounts | Valencia CY 2023: every amount entered is on the PDF page cited | A Word report |
| Appendix obligations agree | The report's Status of Appropriations, Allotments and Obligations (an appendix or annex, in Part I in Malitbog CY 2024), each fund: the obligations on its total row whose appropriation equals the statement's final budget, against the statement's. Only tables after Part I starts, headed appropriation, allotment and obligation (not "disbursement", as in Damulog's), and only total rows (Grand Total first, then the current-year total, then Total); continuing appropriations are left out | No such table, or none of its totals gives the same budget (110 of 131 funds) |
| Corrected obligations found in the report | A corrected obligations figure is in the same report, in a row with the same final budget (the appendix's Grand Total: appropriations, allotment, obligation). Run only where there is a correction | |

Results: 54 executive summaries agree (15 in CY 2025), 22 give no appropriations (1 in
CY 2025). The failures, none of them corrected:

| Report | What differs | Reading |
| --- | --- | --- |
| Quezon CY 2022 | Summary: General Fund ₱694,437,468.00; statement ₱760,177,216.53. Obligations agree (₱513,144,655.90) | The summary disagrees with the statement |
| Lantapan CY 2022 | Summary: General Fund ₱381,655,908.59; statement ₱357,392,945.59. SEF agrees | Same |
| Don Carlos CY 2023 | Summary: General Fund ₱468,732,921.44; statement ₱468,172,025.04 | Same |
| Damulog CY 2024 | Summary: ₱232,271,514.96 and ₱205,382,194.51; statement ₱267,231,514.96 and ₱240,001,897.29 | Same |
| Maramag CY 2022–24 | The summary's "Comparison of Budget and Actual Amounts – GF and SEF (current)" gives both funds together. CY 2022 appropriations agree (₱678,420,068.32); its obligations (₱571,196,769.72) and the later years don't, and CY 2024's "Obligations" line is the statement's General Fund final budget | Same |
| Cabanglasan CY 2022 | Summary: General Fund ₱237,005,578.29 and SEF ₱989,126.74; the statement's rows add to ₱237,155,359.04 for both, its total less continuing appropriations | A sum of ours (no COA total); the statement is self-consistent |
| Cabanglasan CY 2023 | The summary splits current and continuing differently (above) | Same |
| Kadingilan CY 2025 | None of the statement's four figures is in the summary. The summary's first is ₱266,323,408.00 where the statement's General Fund budget is ₱226,323,408.00; the General Fund obligations are ₱209,314,848.90 (the appendix ₱212,382,043.36, below) | The summary disagrees with the statement |
| Valencia CY 2025 | The summary's figures (₱2,300,125,548.92, ₱2,141,762,162.29 …) include neither the statement's General Fund budget, ₱2,282,378,348.92, nor its obligations, ₱1,965,486,265.62 | Same |
| Sumilao CY 2025 | The summary gives ₱257,029,030.82; the statement's consolidated budget is ₱260,279,648.82, obligations ₱233,078,837.87 | Same |
| Dangcagan CY 2025 | The final budgets agree; the statement's General Fund obligations, ₱247,127,970.73, aren't among the summary's figures | Same |
| Quezon CY 2025 | Summary General Fund obligations ₱688,841,344.87; statement ₱688,841,344.83. The SEF's obligations aren't in the summary | Same |
| Don Carlos CY 2025 | The summary gives ₱114,701,762.86 and ₱24,877.48, neither a final budget in the statement | Same |
| Maramag CY 2025 | As in CY 2022–24, the summary gives both funds together | Same |

Row and total arithmetic: 13 reports have a row whose printed differences don't fit its
amounts (Kibawe CY 2024 prints "364.595.00"; Damulog CY 2022 "57.947.13" and
"3.411,797.60"; the rest are a difference that doesn't match). Three of those rows are a
fund's current-year total, and none is corrected:

- Valencia CY 2024, General Fund: the original-to-final difference is printed (111,664,198.00)
  where the amounts give 31,664,198.00. The final budget agrees with the other difference and
  with the executive summary, so the slip is in the difference.
- Maramag CY 2022, General Fund: the final-to-actual difference is a centavo off.
- Sumilao CY 2024, SEF: 5,000,000.00 − 4,319,705.28 is 680,294.72; COA prints 1,129,167.27.
  The executive summary doesn't give the figures, so it can't be told which is off.

CY 2025 adds six such reports: Baungon ("11.997,057.53"), the province, Dangcagan (4
centavos), Kibawe, Maramag and Talakag. One row is a current-year total, not corrected:

- Kibawe CY 2025, General Fund: the original-to-final difference is printed 39,076,305.01
  where the amounts give 39,201,305.01 (the notes' reconciliation shows 39,201,305.01). The
  final budget, 327,408,467.01, agrees with COA's total less its continuing appropriations, so
  the slip is in the difference. Its continuing row's final-to-actual difference is taken from
  the original budget instead of the final.

Four reports fail current + continuing = total: Quezon CY 2022 (₱2.00 apart), Maramag
CY 2024 (its total obligations print 595,818,978.07 where current and continuing give
595,881,978.07), Damulog CY 2022 (an amount that can't be read) and the province CY 2025 (its
General Fund's total obligations print 5,942,270,234.77 where current and continuing give
5,942,267,234.77, ₱3,000.00 apart). Two fail obligations
within the final budget: Pangantucan CY 2023 (₱296,115,388.97 against ₱288,486,437.21) and
Kitaotao CY 2022's SEF (its dash).

Appendix obligations (added 2026-11-08, after the [spot check](#spot-check)): 21 funds in 13
reports have an appendix total with the same budget, and 15 agree. Six don't. Only
Kitaotao CY 2024's is corrected, because its statement is plainly broken (the final budget
repeated as obligations on every line). In the other four the statement's rows add up and
nothing in the report says which figure is right, so the statement stays the figure we show,
as with the executive summary:

| Report | Statement | Appendix | Reading |
| --- | --- | --- | --- |
| Kadingilan CY 2022, General Fund | 186,224,707.97 | 179,377,469.29: Appendix E, SAAOB, Grand Total | 6,847,238.68 apart on the same 214,317,336.00. The executive summary gives no appropriations |
| Kadingilan CY 2023, SEF | 822,005.78 | 722,399.08: Appendix F, SAAOB, Grand Total | The statement's 822,005.78 is maintenance and other operating expenses 722,399.08 plus capital outlay 99,606.70; the appendix leaves the 100,000.00 for the Tuburan ES building unobligated. No executive summary figures |
| Kibawe CY 2024, General Fund | 282,819,348.32 | 260,488,080.32: Appendix E, SAAOB, Grand Total | 22,331,268.00 apart on the same 313,459,681.47. The executive summary agrees with the statement |
| Malitbog CY 2024, General Fund | 261,577,563.43 | 266,132,325.39: Annex E, Status of Appropriations, Allotments, Obligations and Balances (Condensed) | Personnel services agree (82,513,690.11); the annex's maintenance and other operating expenses are 3,499,411.96 higher and its capital outlay 1,055,350.00 higher. The executive summary agrees with the statement |
| Kitaotao CY 2024, both funds | 656,181,029.40 and 1,110,000.00 | 565,976,080.76 and 1,065,224.15: Appendix E.1 and F.1 | Corrected ([corrections](#corrections)). The check stays on the printed figures, so it fails |

Pangantucan CY 2023, whose obligations exceed its budget, has no such appendix to check
against.

CY 2025: 11 funds in 7 reports have an appendix total with the same budget, and 7 agree. Four
don't. In each the statement's current and continuing totals give its total and its
obligations sit within the budget (Kibawe's only slip is the difference above), so the
statement stays the figure we show, as for Kadingilan CY 2022 and Kibawe CY 2024:

| Report | Statement | Appendix (Grand Total) |
| --- | --- | --- |
| Kadingilan CY 2025, General Fund | 209,314,848.90 | 212,382,043.36 |
| Kibawe CY 2025, General Fund | 268,400,521.96 | 303,097,640.23 |
| Kibawe CY 2025, SEF | 2,467,533.38 | 3,336,261.00 |
| Kitaotao CY 2025, SEF | 1,987,062.98 | 953,813.41 |

Kibawe's appendix differs from its statement for the second year running (CY 2024 above).
Decided 2026-11-08: Kibawe's statement stays the figure we show in both years. In both its
executive summary gives the statement's figures, and in CY 2025 the notes' reconciliation of
budget and actual amounts adds to 284,236,881.55 against the statement's 284,259,881.55
(current and continuing); the appendix, though it adds up on its own, is the only place with
another figure. Then, the same day: the site notes the appendix's figure on Kibawe's budget for
both years (General Fund in CY 2024 and CY 2025, SEF in CY 2025), saying which parts of the
report agree with the statement. The notes are rows in
[`data/phase1/appendix-notes.csv`](../data/phase1/appendix-notes.csv); the script adds each to
its fund's `note` and stops if the appendix no longer reads the figure the note cites. Later
the same day, every other appendix difference got a note too: Kadingilan CY 2022 (General
Fund), CY 2023 (SEF) and CY 2025 (General Fund), Malitbog CY 2024 (General Fund) and Kitaotao
CY 2025 (SEF). In all five, as in Kibawe's, the notes' reconciliation of budget and actual
amounts gives the statement's total to the centavo, so the statement stays the figure we show.
Kitaotao CY 2024 needs no note: its obligations are corrected from the appendix.

## Corrections

Decided 2026-11-07: when the report's own subtotals show a printed figure is a typo, the
site shows the corrected figure with a note quoting what COA printed ([data rule
4](data-rules.md)). Each correction is a row in `data/phase1/corrections.csv`, with its
date and source, and goes in the public changelog. The script refuses to run if a
correction no longer matches what the report prints.

| Report | Figure | COA printed | We show | From |
| --- | --- | --- | --- | --- |
| Malitbog CY 2022 | Total liabilities | 817,000,032.58 | 82,959,327.76 | The same statement's current-liabilities subtotal (non-current: none), and the executive summary |
| Malitbog CY 2022 | Past recommendations | thirty-one (30) | 30 | The same sentence's statuses (11 + 17 + 2), and Part III's table |
| Manolo Fortich CY 2022 | Past recommendations | twenty (26) | 26 | Part III's table: 16 fully, 8 partially and 2 not implemented |
| Kibawe CY 2024 | Fully implemented | thirteen (10) | 10 | The same sentence's total (10 + 11 = 21), and Part III's table |
| San Fernando CY 2024 | Fully implemented, not implemented | fifty-five (56), fifty-eight (57) | 56, 57 | Part III's numbered statuses, ending at Implemented56 and Not Implemented57 |
| Kitaotao CY 2024 | General Fund obligations | 656,181,029.40 (the final budget again) | 565,976,080.76 (86.3%) | Appendix E.1, Status of Appropriations, Allotments and Obligations, Current Appropriation, General Fund: Grand Total |
| Manolo Fortich CY 2025 | Past recommendations: total, fully implemented, not implemented, closed, reiterated | 68; seventeen (17); thirty-two (32); nineteen (19); none | 61; 32; 17; none; 12 | Part III's table by year of report, Total row (61 = 32 fully implemented + 17 not implemented + 12 reiterated in Part II, each year's row adding up), and the executive summary (32 fully implemented and 29 unimplemented, of 61) |
| Kitaotao CY 2024 | Special Education Fund obligations | 1,110,000.00 (the final budget again) | 1,065,224.15 (96.0%) | Appendix F.1, the same for the Special Education Fund: Current Year Appropriations |

Decided 2026-11-08, after a spot check: a statement figure that the same report's appendix
shows is wrong is corrected the same way. Kitaotao CY 2024's Statement of Comparison of
Budget and Actual Amounts repeats the final budget in the Actual column on every line of both
funds, so every difference column is a dash and obligations come to 100.0%. Its Appendix E.1
and F.1 (Status of Appropriations, Allotments and Obligations, as of December 31, 2024) give
the same appropriations with 565,976,080.76 and 1,065,224.15 obligated. The statement also
lists no continuing appropriations, where Appendix E.2 gives 175,596,455.69 (99,573,417.11
obligated); continuing appropriations aren't a headline, so that isn't corrected. The CSV
keeps COA's printed figure in `current_obligations`; `obligations` and `share_obligated` take
the appendix's, and `correction_note` says why. The checks on the statement stay on what it
prints. A correction row for obligations is named `obligations_<fund>`
(`obligations_general_fund`), and the script checks that the corrected figure sits in the
report beside the same final budget.

Where a count's words and figure disagree, the row holds the figure until a correction
says which is right; there is a correction for each one.

Differences between the executive summary and the statements, or Part III, aren't
corrected: the statement or Part III is the figure we show, and the summary is only a
check.

## Valencia CY 2023 (PDF)

The full report is a PDF that blocks copying. Its text extracts with `pypdf` once
`cryptography` is installed (the file is AES-encrypted with an empty open password): 180
pages, 360,000 characters. The six verdict and figure records were read from that text by
hand, checked (the statement balances, matches the summary, and revenue less expenses and
transfers gives the surplus) and entered in `pdf-reports.csv` with both COA's page from the
table of contents and the PDF page. The seventh, past recommendations, is Part III's
sentence on PDF p. 118 (COA p. 102); the executive summary (PDF p. 12) says the same, and
Part III's numbered statuses give 22 fully implemented and 24 not. The script checks the
numbers entered against the quoted sentence.

Its 20 findings (PDF pp. 55–113, COA pp. 40–98) are entered the same way, one `finding` row
each with its PDF page, plus a `finding_count` row. Findings 21 to 24 ("Other Thrust Areas",
PDF p. 114) are notes on taxes, PhilHealth and Pag-IBIG, GSIS and GAD with no recommendation.
The quotes come from `pdfminer.six`, because `pypdf` splits words ("Circul ar", "an d"). Three
slips in that text were fixed by hand against the PDF: finding 3 runs on past a line that
starts "3.3 COA Circular", finding 7 was first taken from a list inside finding 6, and
"e-NGAS" in finding 10 breaks across two lines. COA's own typos stay ("IPSAS No .12",
"P2,482,451.047.19").

Its unsettled disallowances are in the executive summary only (G. Summary of Total
Suspensions, Disallowances and Charges, report PDF p. 12, and the same table on p. 6 of the
separate Executive Summary PDF, which is cited as for the other reports). They are entered as a
`disallowances` row and six `disallowance_row` rows, the General Fund's and the Trust Fund's.
Where a cell's column was unclear in the text (the Trust Fund's settlement row prints two
values for three columns), it was placed by the text's position on the page. The script
checks that the rows give the figures entered, add up, open at the CY 2022 balance, and are
on the page cited.

Its appropriations are in the Statement of Comparison of Budget and Actual Amounts, PDF
pp. 28–31 (COA pp. 14–18). The General Fund's lists its current appropriations and a Total
Appropriations row, with no current subtotal and no continuing appropriations, so COA's total
is the current year's: final budget ₱1,961,239,922.23, obligations ₱1,672,730,213.13. The
SEF's has its own current total: ₱40,000,000.00 and ₱31,262,606.66. The 26 rows of
appropriations were read from the PDF's text by hand and entered as `appropriation_row`
records, with an `appropriations` record per fund. Two Capital Outlay rows print three
amounts and a difference with the actual amount blank; the rows' differences, and the
totals, show the blank is nil. The script checks that the rows give the figures entered, add
across and to COA's totals, agree with the executive summary PDF, and are on the PDF pages
cited (all 108 amounts are).

`pypdf` and `pdfminer.six` aren't dependencies of the repo; they ran in a throwaway
environment.

## Errata

Neither errata sheet touches Phase 1's verdicts or figures. Don Carlos's corrects the
executive summary's count of past recommendations; the script applies it from
`errata.csv` before checking the summary against Part III, which already says "fifteen
(15)". The errata sheet is a scanned image, read by eye.

| Report | Errata dated | Corrects |
| --- | --- | --- |
| Don Carlos CY 2022 | 2023-08-09 | Executive summary p. vi, prior years' recommendations: "Sixteen (15)" should read "Fifteen (15)". Matters for the count of past recommendations |
| Impasug-ong CY 2023 | 2025-04-02 | Annex E pp. 169–171, a list of prior-period adjustments: rows were misaligned. Replacement pages attached |

## Spot check

On 2026-11-08 a person checked 20 records, drawn at random, by eye against the report in
Word (one against COA's executive summary PDF), each found by searching for its amount or
opening words. None was misread:

| Data | Records checked |
| --- | --- |
| Verdicts | Kitaotao CY 2023 (the one disclaimer, picked on purpose), San Fernando CY 2023, Libona CY 2024 |
| Headline figures | Don Carlos CY 2023 total liabilities, Manolo Fortich CY 2023 surplus, Damulog CY 2024 equity, the province CY 2022 total revenue, Kalilangan CY 2024 total assets |
| Past recommendations | Baungon CY 2022, the province CY 2024 (its table's Total row), Manolo Fortich CY 2023 |
| Number of findings | Don Carlos CY 2024, Malaybalay CY 2024 (with 19–21 numbered after), Kitaotao CY 2022 |
| Unsettled disallowances | Kitaotao CY 2023 (executive summary PDF), the province CY 2024, Kalilangan CY 2024 (balance in words) |
| Appropriations and obligations | Baungon CY 2022 General Fund, Kitaotao CY 2024 General Fund, Talakag CY 2023 SEF |

What it turned up:

- **Kitaotao CY 2024's budget statement is wrong in COA's report.** It was read as printed,
  but it repeats the final budget as obligations; the same report's appendix gives the
  obligations. Corrected ([corrections](#corrections)), and the corrected figures checked
  in Word against Appendix E.1 and F.1.
- **The province CY 2024's past recommendations:** the table puts two columns under one "Not
  Implemented" heading. The figures were right; the description here was fixed ([past
  recommendations](#what-the-numbers-mean)).
- Things that look wrong but are COA's and already recorded: Kitaotao CY 2023's total row of
  suspensions and disallowances, and its sentence saying none were issued (above). Not
  errors: Damulog CY 2024 prints its equity "629,837,996.7" in one place; the province
  writes the peso sign as a struck-through "P", which the data keeps as "P".

## CY 2025

Added on 2026-11-08. All 23 CY 2025 reports were on COA's site (uploaded September–October
2026); the download and the files are in
[data-sources/coa-annual-audit-reports.md](data-sources/coa-annual-audit-reports.md#cy-2025).
All 23 are Word files, with no errata. The executive summaries' text was saved with
`pdf_pages.py`, and Word's list numbers with `word_list_numbers.ps1`, as for the other years.

The reports changed in ways the script didn't yet read, each now handled and noted in its
section above: the past-recommendations sentence counts observations and then recommendations;
Don Carlos spells "fourty"; Kibawe sets its management letter in a table and condenses its
statements; Dangcagan drops "Comparison of" from the budget statement's title; the province
labels its subtotals "Total Current" and "Total- Current"; Pangantucan rounds its disallowance
balances to millions in Part II and leaves differences blank in its budget statement; Quezon's
observation 4 sits on a list level formatted "none". After each change the script was run on
all 92 reports, and no CY 2022–2024 row changed in any file.

Checks for CY 2025: 679 pass, 26 fail, 143 can't be run. Every failure is listed above, in its
section. One figure is corrected: Manolo Fortich's past recommendations, whose Part III
sentence its own table and executive summary show is wrong ([corrections](#corrections)).
Pangantucan's balances aren't a correction: they are COA's own figures to the centavo, from its
executive summary.

## Open

- **Phase 1's data is pulled for CY 2022–2025** (CY 2025 on 2026-11-08), and the site in
  [`site/`](../site/README.md) shows all four years.
- **Kept but not shown:** the budget statement's rows by sector and expense class
  (`appropriation-tables.csv`), should a later phase want them.
- **Left for Phase 2:** individual notices where a report lists them (Sumilao CY 2022's
  Part II gives each notice's number, date and amount), and what COA says about appeals
  beyond the quote kept with each balance.
