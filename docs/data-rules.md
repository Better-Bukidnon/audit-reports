# Data rules

Every page that shows a figure or a quote keeps these rules.

## Sources

1. **The COA report is the source.** Every figure and quote stores the report's URL and
   where in the report it came from, and the site links to both. For a Word report, that
   is the part and item (the statement, note or observation number), plus COA's page
   number where the report's own table of contents gives it. For a PDF (executive
   summaries, errata, Valencia CY 2023), it is the PDF page. See
   [plan D7](plan.md#open-decisions).
2. **Other sources are leads.** Wikidata figures and LGU action plans can point us to
   something, but what the site shows comes from the AAR. The one exception is COA's own
   validation results in an LGU action plan, which are shown as such and labeled with the
   plan's date.
3. **Each report belongs to one calendar year (CY)**: the year audited, not the year it was
   published. The CY 2024 report comes out in 2025.

## Figures

4. **Amounts exactly as printed**, in pesos and centavos where the report has them. A dash
   means "the report doesn't give this", never zero. (In COA's own balance tables a dash
   means nil, and we read it that way: see
   [phase1-data.md](phase1-data.md#unsettled-disallowances).) The one exception is a
   printed figure that the same report shows is wrong (its own subtotals, sentence, table
   or appendix): the site shows the
   corrected figure, with a note quoting what COA printed and where the correction comes
   from, and the correction goes in the changelog (rule 12). See
   [phase1-data.md](phase1-data.md#corrections).
5. **Years sit side by side.** Amounts from different years are never added together.
6. **Counts are ours, so say how they were counted.** "14 findings" means 14 numbered
   observations in Part II, each with its own recommendation: not the last number COA
   prints, which in some reports goes on to compliance notes with no recommendation (see
   [phase1-data.md](phase1-data.md#findings)). The About page explains each count. The same
   goes for arithmetic of ours, such as the share of a budget obligated, or a total COA
   doesn't print: it is labeled as ours (see
   [phase1-data.md](phase1-data.md#appropriations-and-obligations)).

## Words

7. **Quote, don't paraphrase.** Findings, recommendations and management replies are shown
   in COA's words. Short labels we add (categories like "Cash" or "Property") are marked
   as ours.
8. **Management's reply sits next to every finding** when the report has one.
9. **A finding is not proof of wrongdoing.** Every findings list carries that note, and the
   About page explains what findings, disallowances and verdicts mean.
10. **No scores, grades or rankings of our own.** Sorting a table is fine; labeling a
    government "worst" is not.
11. **No individual names.** COA refers to positions ("the Municipal Accountant"), and so do
    we, even where a source document names people.

## Corrections

12. **Nothing changes silently.** Every correction goes in the public changelog with the date
    and the reason.
