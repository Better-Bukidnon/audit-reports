# Bukidnon Audit Reports: documentation

| Read | For |
| --- | --- |
| [plan.md](plan.md) | Goals, what people see, phases, **open decisions**, risks |
| [data-sources/](data-sources/README.md) | Where the data comes from, what we confirmed, what's still unknown |
| [auditees.md](auditees.md) | The 23 governments COA audits in Bukidnon, and report coverage found so far |
| [data-rules.md](data-rules.md) | Rules every figure and quote on the site keeps |
| [phase1-data.md](phase1-data.md) | Verdicts, headline figures, past recommendations fixed, findings, disallowances and budgets for CY 2022–2025: what we took, from where, and the checks |
| [../data/sources/](../data/sources/) | One list per year of every COA file we downloaded, with sizes and SHA-256 |
| [../data/phase1/](../data/phase1/) | Verdicts, figures, past recommendations, findings and check results as CSV |
| [../site/](../site/README.md) | The website: how to run it, how its data is built, and where the strings and styles live |
| [../scripts/](../scripts/README.md) | How to run the scripts again, and in what order: `import_coa_downloads.py`, which files and checks downloaded reports; `pdf_pages.py`, which saves the executive summary PDFs' text; `word_list_numbers.ps1`, which saves the list numbers Word shows, to check ours; `extract_phase1.py`, which pulls the data into `data/phase1/` |

Survey date for everything in these docs: **2026-11-07**.
