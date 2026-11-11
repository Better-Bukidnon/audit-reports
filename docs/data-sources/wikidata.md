# Wikidata

Someone has been adding figures from COA reports to the Wikidata entries for Bukidnon
towns and cities, citing COA's folders. That's how we found most of the folder ids in
[coa-annual-audit-reports.md](coa-annual-audit-reports.md).

| Entry | Item | Years cited |
| --- | --- | --- |
| [Cabanglasan](https://www.wikidata.org/wiki/Q356971) | Q356971 | CY 2011–2024 |
| [Libona](https://www.wikidata.org/wiki/Q357226) | Q357226 | CY 2011–2024 |
| [Valencia](https://www.wikidata.org/wiki/Q2158) | Q2158 | CY 2012–2024 (liabilities from CY 2011) |

All three carry the same four figures, each cited to COA:

| Property | Label |
| --- | --- |
| P2403 | total assets |
| P2138 | total liabilities |
| P2402 | total expenditure |
| P3087 | fiscal/tax revenue |

Each citation has a title such as "Financial Statement of Cabanglasan" or "2020 Annual
Audit Report, Municipality of Cabanglasan", a publication date, and a COA URL.

Fetch an entry with:

```sh
curl -s -A "<your client name>" "https://www.wikidata.org/wiki/Special:EntityData/Q356971.json"
```

## How we use it

- To find COA folders and files.
- To cross-check figures we type in from the reports.
- **Not as a source for anything shown on the site.** The publication dates are all set to
  June 30 and the citations point at folders, not files, so they can't replace the PDF
  ([data rule 2](../data-rules.md)).

## Not yet checked

The other 19 municipalities, Malaybalay, and the province.
