"""Pull Phase 1 data from the COA Word reports in raw/: verdicts, headline figures, past
recommendations, the number of findings, unsettled disallowances, and appropriations and
obligations.

Usage:
    python -I scripts/extract_phase1.py

Reads every raw/<year>/<lgu>/extracted/**/*.docx (skipping Word lock files) and writes:
  data/phase1/verdicts.csv               one row per report: COA's opinion and the sentence that gives it
  data/phase1/figures.csv                one row per report and figure, from the audited statements
  data/phase1/prior-recommendations.csv  one row per report: how many of COA's earlier recommendations
                                         were fully implemented, from Part III
  data/phase1/findings.csv               one row per finding: each numbered observation in Part II that
                                         has its own recommendation, with COA's number and its opening
                                         paragraph
  data/phase1/finding-counts.csv         one row per report: the number of findings
  data/phase1/disallowances.csv          one row per report: suspensions, disallowances and charges
                                         unsettled at December 31, from Part II or III, else the
                                         executive summary
  data/phase1/disallowance-tables.csv    one row per row of the COA table those come from
  data/phase1/appropriations.csv         one row per report and fund: the final budget for the
                                         current year and its obligations, from Part I's Statement
                                         of Comparison of Budget and Actual Amounts
  data/phase1/appropriation-tables.csv   one row per row of that statement's appropriations
  data/phase1/checks.csv                 every consistency check, so failures are visible, not fixed

Where a disallowance balance is given only in the executive summary, the record cites COA's
separate Executive Summary PDF and its page. The page is found in the PDF's text, which
scripts/pdf_pages.py saves beside the PDF (<name>.pages.txt), and the check confirms the page
shows the same amounts as the copy inside the Word report.

Most finding numbers are Word list numbers, which aren't in the file's text: Word works them
out when it shows the file. This script works them out the same way (see list_info). Where
scripts/word_list_numbers.ps1 has saved Word's own numbers beside a report
(<report>.word-lists.tsv), a check compares the two.

Sumilao's CY 2022 and 2023 budget statements are pictures (EMF) in the Word file; their text
is read from the picture's text records.

Reports that aren't Word files (Valencia CY 2023 is a PDF) are read by hand and kept in
data/phase1/pdf-reports.csv; this script merges those rows in unchanged, and checks the
amounts against the PDF's text that scripts/pdf_pages.py saves.

A printed figure that the same report shows is wrong (its own subtotals, sentence, table or
appendix) is corrected through
data/phase1/corrections.csv, never by hand in the output (see docs/phase1-data.md). COA's
errata sheets are applied from data/phase1/errata.csv.

Where each record comes from follows plan D7: the part and item, plus the page from the
report's own table of contents. Amounts are kept exactly as printed (data rule 4), with a
parsed number beside them for sorting. Nothing COA printed is corrected here; a check that
fails is written to checks.csv and left for a person to read.

Uses only the standard library. Never executes anything from the downloads.
"""
from __future__ import annotations

import csv
import itertools
import re
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "raw"
OUT = REPO / "data" / "phase1"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# An amount as COA prints a total: digit groups, centavos, optional parentheses for a
# negative. Requiring the comma groups keeps note numbers such as "4.14" out.
AMOUNT = re.compile(r"^(?:P|₱)?\s*(\()?\s*(?:P|₱)?\s*(\d{1,3}(?:,\d{3})+\.\d{2})\s*(\))?$")
# Part I's pages are arabic numerals; roman numerals in a contents table are part numbers.
PAGES = re.compile(r"^\d+(?:\s*[-–]\s*\d+)?$")

VERDICTS = {"qualified": "qualified", "adverse": "adverse", "disclaimer of": "disclaimer", "": "unmodified"}
# "Basis for Qualified Opinion"; some reports write "Bases for" or "Bases of".
BASIS = re.compile(r"^Bas[ie]s\s+(?:for|of)\s+(Qualified\s+|Adverse\s+|Disclaimer\s+of\s+)?Opinion\s*:?$", re.I)
OPINION_START = re.compile(r"^(In our opinion|Because of the significance)", re.I)


# ---------------------------------------------------------------------------- Word reading

@dataclass
class Table:
    index: int
    rows: list[list[str]]
    # The same rows laid on the table's grid: a cell spanning k columns is repeated k times,
    # so a column heading lines up with the cells under it.
    grid: list[list[str]] = field(default_factory=list)
    # Tables inside this table's cells, in order (their text is also in the cell's text).
    nested: list[Table] = field(default_factory=list)

    def text(self, n: int | None = None) -> str:
        return " ".join(" ".join(r) for r in self.rows[:n])


@dataclass
class ParaInfo:
    label: str  # the list number Word shows ("6.", "4.2", "a)"), "" if none, "•" for a bullet
    fmt: str  # the list level's number format: decimal, lowerLetter, bullet ...
    bold: float  # share of the paragraph's characters in bold
    in_table: bool


@dataclass
class Report:
    year: str
    lgu: str
    path: Path
    paragraphs: list[str] = field(default_factory=list)  # every paragraph, tables included, in order
    blocks: list[str | Table] = field(default_factory=list)  # top-level paragraphs and tables
    block_start: list[int] = field(default_factory=list)  # index in paragraphs where each block begins
    info: list[ParaInfo] = field(default_factory=list)  # list number and bold, one per paragraph


def para_text(p: ET.Element) -> str:
    out = []
    for el in p.iter():
        if el.tag == W + "t":
            out.append(el.text or "")
        elif el.tag == W + "tab":
            out.append("\t")
    return re.sub(r"[  ]+", " ", "".join(out)).strip()


def cell_text(tc: ET.Element) -> str:
    return " ".join(t for t in (para_text(p) for p in tc.iter(W + "p")) if t)


def grid_row(tr: ET.Element) -> list[str]:
    """A table row's cells on the grid: empty cells for columns the row skips at its start,
    and a cell spanning k columns repeated k times."""
    before = int(_val(tr.find(W + "trPr"), W + "gridBefore") or 0)
    out = [""] * before
    for tc in tr.findall(W + "tc"):
        span = int(_val(tc.find(W + "tcPr"), W + "gridSpan") or 1)
        out += [cell_text(tc)] * span
    return out


def read_report(year: str, lgu: str, path: Path) -> Report:
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    rep = Report(year, lgu, path)
    rep.paragraphs = [para_text(p) for p in body.iter(W + "p")]
    rep.info = list_info(z, body)
    n = at = 0
    for el in body:
        if el.tag == W + "p":
            rep.blocks.append(para_text(el))
            rep.block_start.append(at)
        elif el.tag == W + "tbl":
            trs = el.findall(W + "tr")
            rows = [[cell_text(tc) for tc in tr.findall(W + "tc")] for tr in trs]
            inner = []
            for k, sub in enumerate(t for t in el.iter(W + "tbl") if t is not el):
                strs = sub.findall(W + "tr")
                inner.append(Table(k, [[cell_text(tc) for tc in tr.findall(W + "tc")] for tr in strs],
                                   [grid_row(tr) for tr in strs]))
            rep.blocks.append(Table(n, rows, [grid_row(tr) for tr in trs], inner))
            rep.block_start.append(at)
            n += 1
        at += sum(1 for _ in el.iter(W + "p"))
    return rep


def find_reports() -> list[tuple[str, str, Path]]:
    found = []
    for path in sorted(RAW.glob("20*/*/extracted/**/*.docx")):
        if path.name.startswith("~$"):
            continue
        rel = path.relative_to(RAW).parts
        found.append((rel[0], rel[1], path))
    return found


# ---------------------------------------------------------------------------- list numbers
#
# Most of COA's observation numbers are Word list numbers: the file stores "this paragraph is
# item n of list L at level k", and Word counts the items when it shows the file. We count
# them the way Word does. Checked against Word itself on 2026-11-07 (docs/phase1-data.md):
# every finding's number matches.

def _val(el: ET.Element | None, path: str) -> str | None:
    x = el.find(path) if el is not None else None
    return x.get(W + "val") if x is not None else None


def _on(el: ET.Element | None, path: str) -> bool:
    x = el.find(path) if el is not None else None
    return x is not None and x.get(W + "val") not in ("0", "false", "off")


def _roman(n: int) -> str:
    out = ""
    for v, s in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"),
                 (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out, n = out + s, n - v
    return out


def _number(n: int, fmt: str) -> str:
    if fmt == "decimalZero":
        return f"{n:02d}"
    if fmt in ("lowerLetter", "upperLetter"):
        s = chr(ord("a") + (n - 1) % 26) * ((n - 1) // 26 + 1)
        return s.upper() if fmt == "upperLetter" else s
    if fmt in ("lowerRoman", "upperRoman"):
        return _roman(n).upper() if fmt == "upperRoman" else _roman(n)
    if fmt == "none":
        return ""
    return str(n)


def list_info(z: zipfile.ZipFile, body: ET.Element) -> list[ParaInfo]:
    """The list number Word shows on each paragraph (in body.iter order), and how bold it is.

    As Word does: a paragraph's numbering comes from its own properties or its style's; every
    w:num pointing at the same abstract list shares one set of counters; a w:num's
    startOverride applies the first time that w:num is used; a level that has never been shown
    counts as shown at its start value when a lower level is shown; and showing a level resets
    the levels below it."""
    names = set(z.namelist())
    styles: dict[str, tuple] = {}  # id -> (basedOn, numId, ilvl, bold)
    if "word/styles.xml" in names:
        for s in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
            styles[s.get(W + "styleId")] = (_val(s, W + "basedOn"), _val(s, f"{W}pPr/{W}numPr/{W}numId"),
                                           _val(s, f"{W}pPr/{W}numPr/{W}ilvl"), _on(s, f"{W}rPr/{W}b"))

    def style_num(sid, depth=0):
        if not sid or sid not in styles or depth > 10:
            return None, None
        based, num, lvl, _ = styles[sid]
        return (num, lvl) if num is not None else style_num(based, depth + 1)

    def style_bold(sid, depth=0):
        if not sid or sid not in styles or depth > 10:
            return False
        return styles[sid][3] or style_bold(styles[sid][0], depth + 1)

    abstract: dict[str, dict[int, tuple[int, str, str]]] = {}  # id -> level -> (start, format, text)
    style_link: dict[str, str] = {}
    num_link: dict[str, str] = {}
    nums: dict[str, tuple[str, dict[int, int]]] = {}  # numId -> (abstract id, level -> startOverride)
    if "word/numbering.xml" in names:
        nroot = ET.fromstring(z.read("word/numbering.xml"))
        for a in nroot.iter(W + "abstractNum"):
            aid = a.get(W + "abstractNumId")
            abstract[aid] = {int(lv.get(W + "ilvl")): (int(_val(lv, W + "start") or 1), _val(lv, W + "numFmt") or "decimal",
                                                       _val(lv, W + "lvlText") or "")
                             for lv in a.findall(W + "lvl")}
            if _val(a, W + "styleLink"):
                style_link[_val(a, W + "styleLink")] = aid
            if _val(a, W + "numStyleLink"):
                num_link[aid] = _val(a, W + "numStyleLink")
        for n in nroot.iter(W + "num"):
            overrides = {int(o.get(W + "ilvl")): int(_val(o, W + "startOverride"))
                         for o in n.findall(W + "lvlOverride") if _val(o, W + "startOverride") is not None}
            nums[n.get(W + "numId")] = (_val(n, W + "abstractNumId"), overrides)

    def resolve(aid):
        """A list defined by a numbering style uses that style's list."""
        if aid in num_link:
            st = num_link[aid]
            if st in style_link:
                return style_link[st]
            n, _ = style_num(st)
            if n in nums:
                return nums[n][0]
        return aid

    in_table = {id(p) for tbl in body.iter(W + "tbl") for p in tbl.iter(W + "p")}
    counters: dict[str, list[int | None]] = {}
    used: set[str] = set()
    out = []
    for p in body.iter(W + "p"):
        ppr = p.find(W + "pPr")
        sid = _val(ppr, W + "pStyle")
        num, lvl = _val(ppr, f"{W}numPr/{W}numId"), _val(ppr, f"{W}numPr/{W}ilvl")
        if num is None:
            num, slvl = style_num(sid)
            lvl = lvl if lvl is not None else slvl
        ilvl = int(lvl or 0)

        bold_chars = total = 0
        sbold = style_bold(sid)
        for r in p.iter(W + "r"):
            t = "".join(x.text or "" for x in r if x.tag == W + "t").strip()
            if not t:
                continue
            total += len(t)
            rpr = r.find(W + "rPr")
            b = rpr.find(W + "b") if rpr is not None else None
            if (b.get(W + "val") not in ("0", "false", "off")) if b is not None else sbold:
                bold_chars += len(t)

        label = fmt = ""
        if num and num != "0" and num in nums:
            aid0, overrides = nums[num]
            aid = resolve(aid0)
            levels = abstract.get(aid, {})
            if ilvl in levels:
                c = counters.setdefault(aid, [None] * 9)
                if num not in used:
                    used.add(num)
                    for k, so in overrides.items():
                        if k < 9:
                            c[k] = so - 1
                start, fmt, text = levels[ilvl]
                for k in range(ilvl):
                    if c[k] is None and k in levels:
                        c[k] = levels[k][0]
                c[ilvl] = (c[ilvl] if c[ilvl] is not None else start - 1) + 1
                for k in range(ilvl + 1, 9):
                    c[k] = None

                def sub(m):
                    k = int(m.group(1)) - 1
                    if k not in levels:
                        return ""
                    return _number(c[k] if c[k] is not None else levels[k][0], levels[k][1])

                label = "•" if fmt == "bullet" else re.sub(r"%(\d)", sub, text)
        out.append(ParaInfo(label, fmt, bold_chars / total if total else 0.0, id(p) in in_table))
    return out


# ---------------------------------------------------------------------------- amounts

def parse_amount(cell: str) -> Decimal | None:
    m = AMOUNT.match(cell.replace(" ", "").strip())
    if not m:
        return None
    value = Decimal(m.group(2).replace(",", ""))
    return -value if m.group(1) and m.group(3) else value


def printed_label(row: list[str]) -> str:
    """The row's label as COA printed it, with runs of spaces collapsed."""
    return next((re.sub(r"\s+", " ", c).strip() for c in row if c.strip()), "")


def label_of(row: list[str]) -> str:
    """The label normalised for matching: capitals, no spaces around slashes."""
    return re.sub(r"\s*/\s*", "/", printed_label(row)).upper()


# Anything that looks like a printed amount, well formed or not ("629,837,996.7" is in a
# real report). The comma keeps note numbers ("11", "9.1", "4.14") out.
AMOUNTISH = re.compile(r"^(?:P|₱)?\(?(?:P|₱)?\d{1,3}(?:,\d{1,3})+(?:\.\d*)?\)?$")


def first_amount(row: list[str]) -> tuple[str, Decimal] | None:
    """The first amount after the label: statements print the current year first.

    Stops at the first amount-like cell even when it is malformed, so a typo in the
    current-year column can never fall through to the prior year's figure. The value is
    then parsed as best it can be and the printed text kept beside it."""
    values, seen_label = [], False
    for c in row:
        if not c.strip():
            continue
        if not seen_label:
            seen_label = True
            continue
        cell = c.replace(" ", "").strip()
        if cell in ("-", "–") or AMOUNTISH.match(cell):
            values.append((c.strip(), cell))
    # A dash before two amounts sits in the Note column (Maramag does this), not a year column.
    if len(values) >= 3 and values[0][1] in ("-", "–"):
        values = values[1:]
    if not values:
        return None
    printed, cell = values[0]
    if cell in ("-", "–"):
        return printed, Decimal(0)  # kept as printed; the balance check flags a dash total
    v = parse_amount(cell)
    if v is None:  # malformed: keep the digits it shows
        v = Decimal(re.sub(r"[^\d.]", "", cell)) * (-1 if "(" in cell else 1)
    return printed, v


# ---------------------------------------------------------------------------- table of contents

def toc_entries(rep: Report) -> list[tuple[str, str]]:
    """(title, page) pairs from the report's own table of contents.

    Some reports lay it out as a Word table (title and page in separate cells, so they
    arrive as consecutive paragraphs), others as one paragraph per entry with tabs
    between title and page. Both are read from the flat paragraph list."""
    paras = rep.paragraphs
    start = next((i for i, p in enumerate(paras) if re.match(r"^TABLE OF CONTENTS\b", p, re.I)), None)
    if start is None:
        return []
    window = []
    for p in paras[start + 1:start + 250]:
        if p.startswith("INDEPENDENT AUDITOR"):  # the report's own heading is in capitals
            break
        pieces = [x.strip() for x in p.split("\t") if x.strip()]
        if pieces:
            window.append(pieces)

    # Column layout: every title first, then a "Page" heading and the pages in the same
    # order. Pair Part I's titles (between the PART I and PART II headings) with the pages.
    for k, pieces in enumerate(window):
        if re.match(r"^Page", pieces[0], re.I) and len(pieces) == 1:
            run = []
            for nxt in window[k + 1:]:
                if len(nxt) == 1 and PAGES.match(nxt[0]):
                    run.append(nxt[0])
                else:
                    break
            if len(run) >= 3:
                titles, in_part1 = [], False
                for t in window[:k]:
                    line = " ".join(t)
                    if re.match(r"^PART I\b(?!I)", line):
                        in_part1 = True
                    elif re.match(r"^PART II\b", line):
                        break
                    elif in_part1:
                        titles.append(line)
                return list(zip(titles, run))

    # Inline layout: title and page on one line (tabs between), or in neighbouring cells.
    entries, recent = [], []
    for pieces in window:
        if len(pieces) >= 2 and PAGES.match(pieces[-1]):
            entries.append((" ".join(pieces[:-1]), pieces[-1]))
            recent = []
        elif len(pieces) == 1 and PAGES.match(pieces[0]) and recent:
            entries.append((" ".join(recent[-2:]), pieces[0]))  # a title can wrap onto two cells
            recent = []
        else:
            recent.append(" ".join(pieces))
    return entries


def toc_pages(rep: Report) -> dict[str, str]:
    """Page ranges for the items Phase 1 cites."""
    pages: dict[str, str] = {}
    for title, page in toc_entries(rep):
        t = title.lower()
        for key, pattern in (
            ("Independent Auditor's Report", r"independent auditor"),
            ("Statement of Financial Position", r"statement of financial position"),
            ("Statement of Financial Performance", r"statement of financial performance"),
            ("Statement of Comparison of Budget and Actual Amounts", r"comparison of budget"),
        ):
            if key not in pages and re.search(pattern, t) and "note" not in t:
                pages[key] = page.replace("–", "-").replace(" ", "")
    return pages


# ---------------------------------------------------------------------------- verdict

def verdict(rep: Report) -> dict[str, str]:
    paras = rep.paragraphs
    for i, p in enumerate(paras):
        m = BASIS.match(p)
        if not m:
            continue
        kind = VERDICTS[re.sub(r"\s+", " ", (m.group(1) or "")).strip().lower()]
        quote = ""
        for j in range(i - 1, max(i - 15, -1), -1):
            if OPINION_START.match(paras[j]):
                quote = paras[j]
                break
        if not quote:  # disclaimers put "Because of the significance..." under the heading
            quote = next((q for q in paras[max(i - 6, 0):i] if "do not express an opinion" in q), "")
        return {"verdict": kind, "basis_heading": p, "opinion_quote": quote}
    return {"verdict": "", "basis_heading": "", "opinion_quote": ""}


def stated_verdicts(rep: Report) -> set[str]:
    """What the transmittal letters and executive summary say COA rendered."""
    said = set()
    for p in rep.paragraphs:
        for m in re.finditer(r"(?:rendered|expressed|issued)\s+an?\s+(qualified|unqualified|unmodified|modified|adverse|disclaimer)", p, re.I):
            said.add(m.group(1).lower())
    return said


# ---------------------------------------------------------------------------- statements

STATEMENTS = {
    "Statement of Financial Position": {
        "total_assets": [r"TOTAL ASSETS"],
        "total_liabilities": [r"TOTAL LIABILITIES"],
        "net_assets_equity": [r"TOTAL NET ASSETS/EQUITY", r"TOTAL EQUITY", r"TOTAL GOVERNMENT EQUITY",
                              r"TOTAL NET ASSETS", r"NET ASSETS/EQUITY", r"GOVERNMENT EQUITY", r"EQUITY"],
    },
    "Statement of Financial Performance": {
        "total_revenue": [r"TOTAL REVENUES?"],
        "surplus_deficit": [r"(?:NET )?SURPLUS ?/? ?\(?DEFICIT\)? FOR THE (?:PERIOD|YEAR)",
                            r"(?:NET )?SURPLUS ?/? ?\(?DEFICIT\)?"],
    },
}
OTHER_TITLES = ["STATEMENT OF FINANCIAL PERFORMANCE", "STATEMENT OF CHANGES IN NET ASSETS",
                "STATEMENT OF CASH FLOWS", "STATEMENT OF COMPARISON OF BUDGET", "NOTES TO FINANCIAL STATEMENTS"]


def statement_tables(rep: Report, title: str) -> tuple[list[Table], list[str]]:
    """The statement's table and any continuation tables, up to the next statement."""
    t_up = title.upper()
    key = re.compile(r"^TOTAL ASSETS$" if "POSITION" in t_up else r"^TOTAL REVENUES?$")
    others = [t for t in OTHER_TITLES if t != t_up]
    start = None
    headings: list[str] = []
    for i, b in enumerate(rep.blocks):
        if isinstance(b, str):
            if b and len(b) < 120:  # a heading line, not executive-summary prose
                headings = (headings + [b.upper()])[-6:]
            elif b:
                headings = []
            continue
        # The title as a heading: a heading line before the table, or a short row in its first
        # ten. Not a title named in prose: Kibawe CY 2025 sets its Statement of Management
        # Responsibility in a table whose letter mentions "the related Statement of Financial
        # Performance".
        rows10 = [" ".join(r) for r in b.rows[:10]]
        head = " ".join(headings) + " " + " ".join(r for r in rows10 if len(r) < 400).upper()
        headings = []
        if t_up not in head and t_up in b.text().upper() and "TABLE OF CONTENTS" not in head:
            # Two statements in one Word table (Dangcagan CY 2022): start at the title row.
            cut = next(n for n, r in enumerate(b.rows) if t_up in " ".join(r).upper())
            part = Table(b.index, b.rows[cut:])
            if any(key.match(label_of(r)) for r in part.rows):
                return [part], []
        if t_up not in head or "TABLE OF CONTENTS" in head:
            continue
        # The statement itself has a "TOTAL ASSETS" / "TOTAL REVENUE" row in this table or
        # the next few; the executive summary's highlights say plain "Assets" / "Revenue".
        following = [x for x in rep.blocks[i:i + 12] if isinstance(x, Table)][:3]
        if any(key.match(label_of(r)) for t in following for r in t.rows):
            start = i
            break
    if start is None:
        return [], []
    tables: list[Table] = []
    notes: list[str] = []
    for b in rep.blocks[start:]:
        if isinstance(b, Table):
            if tables and any(o in b.text(10).upper() for o in others):
                break
            tables.append(b)
            if len(tables) >= 4:
                break
        elif tables and any(o in b.upper() for o in others):
            break
    hdr = " ".join(t.text(12) for t in tables[:2])
    years = re.findall(r"\b(20\d\d)\b", hdr)
    if years and years[0] != rep.year:
        notes.append(f"first year in header is {years[0]}, not {rep.year}")
    return tables, notes


def figures(rep: Report) -> tuple[list[dict], list[str], dict[str, Decimal]]:
    """Headline figures from the statements, notes on anything not found, and extras that
    only the checks use (the surplus from current operation, which some executive
    summaries report as "Surplus")."""
    rows_out, notes, extras = [], [], {}
    for title, wanted in STATEMENTS.items():
        tables, tnotes = statement_tables(rep, title)
        notes += [f"{title}: {n}" for n in tnotes]
        if not tables:
            notes.append(f"{title}: table not found")
            continue
        for fig, patterns in wanted.items():
            hit = None
            for pat in patterns:
                rx = re.compile(rf"^{pat}$")
                for t in tables:
                    for r in t.rows:
                        lab = label_of(r)
                        if rx.match(lab):
                            amt = first_amount(r)
                            if amt:
                                hit = (printed_label(r), amt, t.index)
                                break
                    if hit:
                        break
                if hit:
                    break
            if not hit:
                notes.append(f"{title}: {fig} not found")
                continue
            lab, (printed, value), tidx = hit
            rows_out.append({"figure": fig, "label_as_printed": lab, "amount_as_printed": printed,
                             "amount": f"{value:.2f}", "statement": title, "word_table": tidx})
        for t in tables:
            for r in t.rows:
                if "FROM CURRENT OPERATION" in label_of(r) and "surplus_current_operation" not in extras:
                    amt = first_amount(r)
                    if amt:
                        extras["surplus_current_operation"] = amt[1]
    return rows_out, notes, extras


def summary_figures(rep: Report) -> dict[str, tuple[str, Decimal]]:
    """Assets, liabilities, equity and surplus from the executive summary's highlights."""
    found: dict[str, tuple[str, Decimal]] = {}
    keys = {"ASSETS": "total_assets", "TOTAL ASSETS": "total_assets", "LIABILITIES": "total_liabilities",
            "TOTAL LIABILITIES": "total_liabilities", "GOVERNMENT EQUITY": "net_assets_equity",
            "GOVT. EQUITY": "net_assets_equity", "EQUITY": "net_assets_equity",
            "SURPLUS": "surplus_deficit", "SURPLUS (DEFICIT)": "surplus_deficit",
            "SURPLUS/(DEFICIT)": "surplus_deficit", "NET SURPLUS": "surplus_deficit",
            "SURPLUS (DEFICIT) FOR THE PERIOD": "surplus_deficit", "SURPLUS FOR THE PERIOD": "surplus_deficit",
            "NET INCOME": "surplus_deficit"}
    for b in rep.blocks:
        if isinstance(b, str):
            if b.startswith("INDEPENDENT AUDITOR"):
                break  # Part I has started
            continue
        for r in b.rows:
            k = keys.get(label_of(r))
            if k and k not in found:
                amt = first_amount(r)
                if amt:
                    found[k] = amt
    return found


def same_amount(summary: tuple[str, Decimal], statement: Decimal) -> bool:
    """Equal at the precision the summary printed (some print whole pesos)."""
    printed, value = summary
    if "." not in printed:
        return value == statement.quantize(Decimal(1), rounding="ROUND_HALF_UP")
    return value == statement


# ---------------------------------------------------------------------------- past recommendations
#
# Part III of every report gives the status of the recommendations COA made in earlier
# years. Most reports sum it up in one sentence ("Out of the twenty-three (23) prior years'
# audit recommendations, seventeen (17) were fully implemented and six (6) ..."), in Part III,
# in the executive summary, or both; some give a table with a Total row instead. We take
# COA's own count, preferring Part III, and check it against everything else the report says.

PRIOR_ITEM = "Status of Implementation of Prior Years' Audit Recommendations"
STATUSES = ["fully_implemented", "partially_implemented", "not_implemented", "for_implementation", "closed"]

_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
# "fourty four (44)": COA's spelling in Don Carlos CY 2025.
NUMBER_WORDS = {w: i for i, w in enumerate(_UNITS)} | {w: 20 + 10 * i for i, w in enumerate(_TENS)} | {"fourty": 40}
_WORD = "(?:" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True) + ["hundred"]) + ")"
_WORDS = rf"{_WORD}(?:(?:\s*-\s*|\s+)(?:and\s+)?{_WORD})*"
# A count the way COA writes one: "twenty-three (23)", "(5) five", "23" or "eight". A bare
# number must not be part of a date, an amount or a percentage ("December 31, 2023", "74%").
COUNT = (rf"(?:(?P<w1>\b{_WORDS})\s*\(\s*(?P<n1>\d+)\s*\)|\(\s*(?P<n2>\d+)\s*\)\s*(?P<w2>{_WORDS})\b"
         rf"|(?<![\d.,])\b(?P<n3>\d{{1,3}})\b(?![\d.,%)])|(?P<w3>\b{_WORDS})\b)")
# "fifty-six (56) or 84 percent were fully implemented", "43 ARs have been “fully implemented" (CY 2025)
_FILLER = (r"(?:\s+or\s+[\d.]+\s*(?:%|percent\b))?(?:\s+(?:audit|recommendations?|ARs?|were|are|was|is|found|still"
           r"|remained|already|only|previous|prior|years?['’]?|that|have|been))*\s*[\"“”']?\s*")
_STATUS = (r"(?P<status>fully\s+implemented|partially\s+implemented|not\s+(?:yet\s+)?implemented|unimplemented"
           r"|for\s+implementation|implemented|closed|reiterated|evaluated)")
# "seventeen (17) were fully implemented", "eight (8) “For Implementation”", "31 were found fully implemented"
PAIR = re.compile(COUNT + _FILLER + _STATUS, re.I)
# "Out of the twenty-three (23)", "Of the Fifty-Three (53)", "There are fifteen (15)"
LEAD = re.compile(r"(?:\b(?:out\s+of|of)\s+(?:the\s+|these\s+)?(?:remaining\s+)?|\bthere\s+(?:are|were)\s+)" + COUNT,
                  re.I)
# CY 2025 reports count observations and then their recommendations: "Out of the 36 prior
# years' audit observations with 217 number of recommendations, 146 have been fully implemented"
# (Dangcagan). The statuses count recommendations, so the recommendations are the total. Baungon
# writes "26 prior year's audit recommendations with 75 Audit Recommendations (ARs)".
WITH_RECS = re.compile(r"\b(?:observations?|recommendations)\s+with\s+" + COUNT
                       + r"\s+(?:number\s+of\s+)?(?:audit\s+)?recommendations\b(?:\s*\(ARs?\))?", re.I)
# A sentence about one earlier report only ("Out of fifteen (15) CY 2021 audit recommendations",
# "For the 2022 Annual Audit Report"), not the total. A range ("CY 2014-2021", "in CY 2021 and
# previous years") is the total.
PER_YEAR = re.compile(r"\b(?:in|from)\s+(?:the\s+)?(?:AAR|CY)\s*20\d\d\b(?!\s*(?:-|–|to\b|up\b|and\b))"
                      r"|\)\s+CY\s+20\d\d\b|\bfor\s+(?:the\s+)?20\d\d\s+(?:AAR|Annual\s+Audit\s+Report)", re.I)
CATEGORY = {"fully implemented": "fully_implemented", "implemented": "fully_implemented",
            "partially implemented": "partially_implemented", "not implemented": "not_implemented",
            "not yet implemented": "not_implemented", "unimplemented": "not_implemented",
            "for implementation": "for_implementation", "closed": "closed", "reiterated": "reiterated",
            "evaluated": "evaluated"}
_CATEGORY_NS = {k.replace(" ", ""): v for k, v in CATEGORY.items()}


def category(status: str) -> str:
    return _CATEGORY_NS[re.sub(r"\s+", "", status.lower())]


@dataclass
class Count:
    printed: str
    value: int
    words: int | None = None
    numeral: int | None = None

    def mismatch(self) -> bool:
        return self.words is not None and self.numeral is not None and self.words != self.numeral


def words_to_int(s: str) -> int:
    total = 0
    for t in re.split(r"[\s\-]+", s.lower()):
        if not t or t == "and":
            continue
        total = (total or 1) * 100 if t == "hundred" else total + NUMBER_WORDS[t]
    return total


def read_count(m: re.Match) -> Count:
    """The count a COUNT match holds. Where words and numeral disagree ("thirteen (10)"), the
    numeral is the value; the mismatch is checked and needs a row in corrections.csv."""
    g = m.groupdict()
    words = g["w1"] or g["w2"] or g["w3"]
    numeral = g["n1"] or g["n2"] or g["n3"]
    w = words_to_int(words) if words else None
    n = int(numeral) if numeral else None
    keys = [k for k in ("w1", "n1", "n2", "w2", "n3", "w3") if g[k] is not None]
    start = min(m.start(k) for k in keys)
    if g["n2"]:
        start = m.string.rindex("(", 0, m.start("n2"))  # "(5) five"
    end = max(m.end(k) for k in keys)
    if g["n1"]:
        end = m.string.index(")", end) + 1  # "twenty-three (23)"
    return Count(m.string[start:end], n if n is not None else w, w, n)


@dataclass
class Statement:
    text: str
    total: Count
    counts: dict[str, Count]
    others: list[Count]  # every count in the text, for the words-and-numerals check


def parse_statement(text: str) -> Statement | None:
    """COA's summary sentence, or None if the text isn't one."""
    if not re.search(r"recommendation|findings", text, re.I):
        return None
    leads = list(LEAD.finditer(text))
    pairs = [m for m in PAIR.finditer(text)
             if not any(l.start() <= m.start() < l.end() for l in leads)]  # "twenty (26) unimplemented and ..."
    status = [m for m in pairs if category(m.group("status")) in STATUSES]
    if not any(category(m.group("status")) == "fully_implemented" for m in status):
        return None
    first = status[0]
    if PER_YEAR.search(text[:first.start()]):
        return None
    # The total is the last count given before the statuses: the last "Out of the N", or
    # "only N were evaluated" when COA left reiterated recommendations out.
    base = [(l.start(), read_count(l)) for l in leads if l.end() <= first.start()]
    base += [(m.start(), read_count(m)) for m in pairs
             if m.start() < first.start() and category(m.group("status")) == "evaluated"]
    withs = [m for m in WITH_RECS.finditer(text) if m.end() <= first.start()]
    base += [(m.start(), read_count(m)) for m in withs]
    if not base:
        return None
    base.sort(key=lambda b: b[0])
    counts: dict[str, Count] = {}
    for m in pairs:
        cat = category(m.group("status"))
        if cat != "evaluated" and m.start() >= base[-1][0]:
            counts.setdefault(cat, read_count(m))
    others = ([read_count(l) for l in leads if l.end() <= first.start()] + [read_count(m) for m in withs]
              + [read_count(m) for m in pairs])
    return Statement(text, base[-1][1], counts, others)


def part3_range(rep: Report) -> tuple[int, int]:
    """Block indices of Part III: from its heading to Part IV's."""
    p1 = next(i for i, b in enumerate(rep.blocks) if isinstance(b, str) and b.startswith("INDEPENDENT AUDITOR"))
    s = next((i for i, b in enumerate(rep.blocks)
              if i > p1 and isinstance(b, str) and re.match(r"^PART\s+III\b", b.strip(), re.I) and len(b) < 200), None)
    if s is None:
        return 0, 0
    e = next((i for i, b in enumerate(rep.blocks)
              if i > s and isinstance(b, str) and re.match(r"^PART\s+IV\b(?!\.)", b.strip(), re.I) and len(b) < 200),
             len(rep.blocks))
    return s, e


def toc_part3_page(rep: Report) -> str:
    """Part III's page from the report's table of contents."""
    paras = rep.paragraphs
    start = next((i for i, p in enumerate(paras) if re.match(r"^TABLE OF CONTENTS\b", p, re.I)), None)
    if start is None:
        return ""
    window = []
    for p in paras[start + 1:start + 250]:
        if p.startswith("INDEPENDENT AUDITOR"):
            break
        if p.strip():
            window.append(p)
    k = next((i for i, p in enumerate(window) if re.search(r"status of (?:implementation of )?prior", p, re.I)), None)
    if k is None:
        return ""
    for j, p in enumerate(window[k:k + 6]):  # the page follows the title, on its line or a line or two below
        if j and re.match(r"^(?:PART\s+)?IV\b", p, re.I):
            break
        last = [x.strip() for x in p.split("\t") if x.strip()][-1]
        if PAGES.match(last):
            return last.replace("–", "-").replace(" ", "")
    # Column layout (Don Carlos, Kitaotao): every title, then a "Page" heading and the pages in
    # the same order. Part headings other than Part III's own title have no page.
    pg = next((i for i, p in enumerate(window) if re.match(r"^Page\b", p, re.I) and len(p) < 8), None)
    if pg is None or pg < k:
        return ""
    titles = [p for p in window[:pg] if not re.match(r"^PART\s+(?:I|II|IV)\b(?!I)", p)]
    pages = []
    for p in window[pg + 1:]:
        if not PAGES.match(p.strip()):
            break
        pages.append(p.strip())
    i = titles.index(window[k])
    return pages[i].replace("–", "-").replace(" ", "") if i < len(pages) else ""


def part3_texts(rep: Report) -> list[str]:
    s, e = part3_range(rep)
    end = rep.block_start[e] if e < len(rep.blocks) else len(rep.paragraphs)
    return rep.paragraphs[rep.block_start[s]:end] if e > s else []


def summary_texts(rep: Report) -> list[str]:
    """The executive summary: everything before the table of contents."""
    toc = next((i for i, p in enumerate(rep.paragraphs) if re.match(r"^TABLE OF CONTENTS\b", p, re.I)), 0)
    return rep.paragraphs[:toc]


def first_statement(texts: list[str]) -> Statement | None:
    for t in texts:
        st = parse_statement(t)
        if st:
            return st
    return None


YEAR_HEAD = re.compile(r"^(?:calendar\s+year|aar\s+year|year)$", re.I)


def table_field(label: str) -> str | None:
    lab = re.sub(r"\s+", " ", label.lower())
    if "beg" in lab and "balance" in lab:
        return "total"  # recommendations still open at the start of the year
    if "previously" in lab:
        return None
    if re.match(r"^(?:no\.|number) of", lab) and "implemented" not in lab or lab == "total":
        return "total?"
    for key, f in (("closed", "closed"), ("reiterated", "reiterated"), ("partial", "partially_implemented"),
                   ("for implementation", "for_implementation"), ("not implemented", "not_implemented"),
                   ("unimplemented", "not_implemented"), ("implemented", "fully_implemented")):
        if key in lab:
            return f
    return None


def summary_table(rep: Report) -> tuple[dict[str, Count], Table] | None:
    """The Total row of Part III's table by year of report, where it has one."""
    s, e = part3_range(rep)
    for t in [b for b in rep.blocks[s:e] if isinstance(b, Table)]:
        if not t.rows or not YEAR_HEAD.match(t.rows[0][0].strip()):
            continue
        total_row = next((r for r in t.rows if r and r[0].strip().lower() == "total"), None)
        if total_row is None:
            continue
        head = []
        for r in t.rows:
            if re.match(r"^(?:CY\s*)?20\d\d$", r[0].strip()):
                break
            head.append(r)
        found: dict[str, Count] = {}
        candidates: list[tuple[str, Count]] = []
        for i, cell in enumerate(total_row[1:], start=1):
            label = next((r[i] for r in reversed(head) if len(r) > i and r[i].strip()), "")
            f = table_field(label)
            txt = cell.strip()
            if f is None or not txt.isdigit():
                continue  # "n/a", or a dash: not given (data rule 4), never zero
            c = Count(txt, int(txt))
            if f == "total?":
                candidates.append((label.lower(), c))
            else:
                found.setdefault(f, c)
        if "total" not in found and candidates:
            pick = next((c for lab, c in candidates if "recommendation" in lab), None) or candidates[0][1]
            found["total"] = pick
        if "total" in found and "fully_implemented" in found:
            return found, t
    return None


# A bare "Implemented" counts only as a status of its own ("1. Implemented"), not inside a
# phrase ("Parially Implemented", "deemed implemented"). Lantapan marks recommendations already
# counted in earlier years "Implemented*".
STATUS_CELL = re.compile(r"fully\s*implemented|partially\s*implemented|not\s*(?:yet\s*)?implemented|unimplemented"
                         r"|for\s*implementation|(?<![A-Za-z:]\s)(?<![A-Za-z])implemented(?!\*)|closed|reiterated",
                         re.I)
STARTS_WITH_STATUS = re.compile(r"^[\s(\[]*(?:[a-z]|\d+(?:[.-]\d+)?)?[.)\]]?\s*"
                                r"(?:fully|partial|not\b|unimplemented|for\s*implementation|implemented|closed|reiterated)",
                                re.I)
DEHYPHEN = re.compile(r"(?<=[A-Za-z])-\s*(?=[a-z])")  # "Partial-ly Imple-mented"


def statement_checks(st: Statement, total: int, counts: dict[str, int]) -> list[tuple[str, bool | None, str]]:
    """Words against numerals, and statuses against the total."""
    mism = list(dict.fromkeys(c.printed for c in st.others + [st.total] if c.mismatch()))
    out = [("past recommendations: words match numerals", not mism,
            "; ".join(f"'{m}'" for m in mism) or "all agree")]
    s = sum(counts.get(k, 0) for k in STATUSES)
    r = counts.get("reiterated")
    parts = " + ".join(f"{counts[k]} {k.replace('_', ' ')}" for k in STATUSES if k in counts)
    if s == total:
        out.append(("past recommendations: statuses add up to the total", True, f"{parts} = {total}"))
    elif r is not None and s + r == total:
        out.append(("past recommendations: statuses add up to the total", True,
                    f"{parts} + {r} reiterated = {total}"))
    else:
        out.append(("past recommendations: statuses add up to the total", False, f"{parts} = {s}, total {total}"))
    return out


def prior_recommendations(rep: Report, errata: list[dict]) -> tuple[dict, list[tuple[str, bool | None, str]]]:
    """The report's row and its checks as (name, ok, detail); ok None means the check can't
    be run on this report."""
    texts, applied = summary_texts(rep), []
    for e in errata:
        if (e["year"], e["lgu_slug"]) != (rep.year, rep.lgu):
            continue
        rx = re.compile(re.escape(e["printed"]), re.I)
        if not any(rx.search(t) for t in texts):
            raise SystemExit(f"errata no longer matches the report: {e}")
        texts = [rx.sub(e["should_read"], t) for t in texts]
        applied.append(f"COA's errata of {e['errata_date']} applied: '{e['printed']}' reads '{e['should_read']}'")
    p3, es, tb, sc = first_statement(part3_texts(rep)), first_statement(texts), summary_table(rep), status_column_counts(rep)

    row: dict = {"part": "Part III", "item": PRIOR_ITEM, "toc_pages": toc_part3_page(rep), "quote": ""}
    st = p3 or (None if tb else es)
    if p3:
        row["stated_in"] = "Part III"
    elif tb:
        row["stated_in"] = "Part III table, Total row"
    elif es:
        row |= {"stated_in": "Executive summary", "part": "Executive Summary", "toc_pages": ""}
    elif sc.get("fully_implemented"):
        row["stated_in"] = "Part III status column, our count"
    else:
        return row | {"stated_in": ""}, [("past recommendations found", False, "no total in Part III or the executive summary")]
    if st:
        found: dict[str, Count] = {"total": st.total} | st.counts
        row["quote"] = st.text
    elif tb:
        found = tb[0]
    else:
        found = {k: Count("", v) for k, v in sc.items() if k in STATUSES}
        found["total"] = Count("", sum(found[k].value for k in found))
    for k, c in found.items():
        row[k] = c.value
    row["total_as_printed"] = found["total"].printed
    row["fully_implemented_as_printed"] = found["fully_implemented"].printed
    total, fully = found["total"].value, found["fully_implemented"].value
    counts = {k: c.value for k, c in found.items() if k != "total"}

    # "Reiterated" means different things from report to report: recommendations left out of
    # the total, a part of those not implemented, or (the only kind kept) recommendations COA
    # counts in the total without a status because Part II repeats them.
    s = sum(counts.get(k, 0) for k in STATUSES)
    if "reiterated" in counts and not (s != total and s + counts["reiterated"] == total):
        row.pop("reiterated")

    checks: list[tuple[str, bool | None, str]] = [("past recommendations found", True, row["stated_in"])]
    if st:
        checks += statement_checks(st, total, counts)
    else:
        checks.append(("past recommendations: words match numerals", None, "no sentence: the figures are a table's"))
        s += counts.get("reiterated") or 0
        checks.append(("past recommendations: statuses add up to the total", s == total, f"{counts} total {total}"))
    ours = f"{fully} of {total} fully implemented"
    if es and row["stated_in"] != "Executive summary":
        e_full = es.counts["fully_implemented"].value
        checks.append(("past recommendations: executive summary agrees with Part III",
                       (es.total.value, e_full) == (total, fully),
                       f"summary: {e_full} of {es.total.value}; Part III: {ours}" + "".join(f"; {a}" for a in applied)))
        checks.append(("past recommendations: executive summary words match numerals",
                       not any(c.mismatch() for c in es.others + [es.total]),
                       ("; ".join(dict.fromkeys(f"'{c.printed}'" for c in es.others + [es.total] if c.mismatch()))
                        or "all agree")
                       + "".join(f"; {a}" for a in applied)))
    else:
        checks.append(("past recommendations: executive summary agrees with Part III", None,
                       "the summary is the source" if es else "no total in the executive summary"))
    if tb and row["stated_in"] != "Part III table, Total row":
        t_total, t_full = tb[0]["total"].value, tb[0]["fully_implemented"].value
        checks.append(("past recommendations: Part III table agrees", (t_total, t_full) == (total, fully),
                       f"table: {t_full} of {t_total}; {row['stated_in']}: {ours}"))
    else:
        checks.append(("past recommendations: Part III table agrees", None,
                       "the table is the source" if tb else "no table by year of report"))
    if sc.get("fully_implemented") and not row["stated_in"].endswith("our count"):
        checks.append(("past recommendations: our count of the Part III status column agrees",
                       sc["fully_implemented"] == fully,
                       f"status column: {sc}; {row['stated_in']}: {ours}"))
    else:
        checks.append(("past recommendations: our count of the Part III status column agrees", None,
                       "the count is the source" if sc else "status column not read"))
    return row, checks


def is_status_head(cell: str) -> bool:
    return bool(re.search(r"\bstatus\b", cell, re.I)) and not re.search(r"\breason", cell, re.I)


def status_column_counts(rep: Report) -> dict[str, int]:
    """Our own count of the Part III status column: every status written in it, including
    several in one cell ("1. Implemented 2. Not Implemented"). A check only."""
    s, e = part3_range(rep)
    counts: dict[str, int] = {}
    head: list[str] | None = None
    col = width = None
    for t in [b for b in rep.blocks[s:e] if isinstance(b, Table)]:
        if not t.rows or YEAR_HEAD.match(t.rows[0][0].strip()):
            continue
        hdr = next((r for r in t.rows[:3] if len(r) >= 3 and any(is_status_head(c) for c in r)), None)
        if hdr is not None:
            head, col = hdr, next(i for i, c in enumerate(hdr) if is_status_head(c))
            width = max(len(r) for r in t.rows)
        elif head is None or max(len(r) for r in t.rows) != width:
            continue  # not a status table, nor a continuation of one
        for r in t.rows:
            if r is hdr:
                continue
            if len(r) == len(head):
                cell = DEHYPHEN.sub("", r[col])
            else:  # merged cells shift the columns: take the first cell that starts with a status
                cell = next((DEHYPHEN.sub("", c) for c in r[1:] if STARTS_WITH_STATUS.match(DEHYPHEN.sub("", c))), "")
            for m in STATUS_CELL.finditer(cell):
                cat = category(m.group(0))
                counts[cat] = counts.get(cat, 0) + 1
    return counts


# ---------------------------------------------------------------------------- findings
#
# A finding is a numbered observation in Part II that has its own recommendation (data rule
# 6). COA numbers its observations 1, 2, 3 ... straight through Part II's sections (financial
# audit, compliance audit, other issues), each followed by its recommendation. Some reports
# then keep numbering the paragraphs on taxes, GSIS, GAD and the like, or even the headings,
# with no recommendation: those aren't findings. So we count the observations instead of
# taking the last number COA prints, and keep COA's number on each one as a check.

FINDINGS_ITEM = "Observations and Recommendations"
PART2_HEAD = re.compile(r"^PART\s*(?:II|2)\b(?!I)", re.I)
PART3_HEAD = re.compile(r"^PART\s*(?:III|3)\b", re.I)
# A typed number opening a paragraph: "12. ", "12) " or "12 ", but not "1.19 Recommendations".
TYPED_NUMBER = re.compile(r"^(\d{1,3})(?:\.(?!\d)|\)|\s)\s*")
# "Recommendation:", "1.19 Recommendations:", "We recommended that ...", "It is recommended ..."
RECOMMENDATION = re.compile(
    r"^(?:[\d.]+\s*|[a-z][.)]\s*)?(?:(?:Audit\s+|Our\s+)?Recommendations?\b"
    r"|(?:We|It\s+is|The\s+Audit\s+Team)\s+(?:also\s+|further\s+|strongly\s+|again\s+)?(?:recommend|reiterate))",
    re.I)


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Finding:
    number: int  # as COA numbers it
    numbered: str  # "Word list" or "typed"
    index: int  # paragraph index in the report
    text: str  # the opening paragraph, word for word, without a typed number


def part2_range(rep: Report) -> tuple[int, int] | None:
    """Paragraph indices of Part II: the PART II heading (outside tables) followed by the most
    paragraphs before a PART III heading. The table of contents names Part II too, briefly."""
    heads3 = [j for j, p in enumerate(rep.paragraphs) if not rep.info[j].in_table and PART3_HEAD.match(flat(p))]
    best = None
    for k, p in enumerate(rep.paragraphs):
        if rep.info[k].in_table or not PART2_HEAD.match(flat(p)):
            continue
        end = next((j for j in heads3 if j > k), len(rep.paragraphs))
        if best is None or end - k > best[1] - best[0]:
            best = (k, end)
    return best


def observation_number(text: str, info: ParaInfo) -> tuple[int, str] | None:
    """(number, how) when the paragraph opens with a whole number, from Word's list or typed."""
    if info.label:
        # The label Word shows, whatever the level's own format: Quezon CY 2025's observation 4
        # sits on a level formatted "none" whose text is "%1.", the level above's counter.
        m = re.fullmatch(r"\(?(\d+)[.)]?", info.label.strip())
        return (int(m.group(1)), "Word list") if m else None
    m = TYPED_NUMBER.match(text)
    return (int(m.group(1)), "typed") if m else None


def findings(rep: Report) -> tuple[list[Finding], list[int]]:
    """Part II's findings, and the numbers COA goes on to print, after the last finding's
    recommendation, on paragraphs that have none."""
    rng = part2_range(rep)
    if not rng:
        return [], []
    a, b = rng
    rec_at: list[int] = []
    cands: list[tuple[int, str, int, int]] = []  # (number, how, paragraph, recommendations before it)
    for i in range(a, b):
        t = flat(rep.paragraphs[i])
        if not t or rep.info[i].in_table:
            continue
        if RECOMMENDATION.match(t):
            rec_at.append(i)
            continue
        nv = observation_number(t, rep.info[i])
        if nv and len(t) >= 60:
            cands.append((nv[0], nv[1], i, len(rec_at)))

    # The longest run of numbered paragraphs 1, 2, 3 ... with a recommendation between each
    # pair. A repeated or skipped number, or a restart at 1, is allowed at a cost, so that a
    # slip in COA's numbering shows in the checks instead of cutting the run short. A bold
    # opening wins a tie (detail lists inside an observation are rarely bold).
    best: list[tuple[float, int] | None] = [None] * len(cands)
    for j, (vj, _, ij, rj) in enumerate(cands):
        bonus = 0.01 if rep.info[ij].bold >= 0.5 else 0
        opts = [(1 + bonus, -1)] if vj == 1 else []
        for i, (vi, _, _, ri) in enumerate(cands[:j]):
            if best[i] is None or rj <= ri:  # no recommendation between them
                continue
            if vj == vi + 1:
                opts.append((best[i][0] + 1 + bonus, i))
            elif vj in (vi, vi + 2) or (vj == 1 and vi >= 2):
                opts.append((best[i][0] + 1 + bonus - 3, i))
        if opts:
            best[j] = max(opts, key=lambda o: o[0])
    if not any(best):
        return [], []
    k = max((k for k in range(len(cands)) if best[k]), key=lambda k: (best[k][0], -k))
    chain = []
    while k != -1:
        chain.append(cands[k])
        k = best[k][1]
    chain.reverse()
    # The last finding needs a recommendation of its own before Part II ends. A numbered
    # paragraph with none after it is a compliance note ("The Municipality withheld and
    # remitted taxes ..."), not a finding.
    while chain and not any(r > chain[-1][2] for r in rec_at):
        chain.pop()

    out = []
    for v, how, i, _ in chain:
        t = flat(rep.paragraphs[i])
        out.append(Finding(v, how, i, TYPED_NUMBER.sub("", t, count=1) if how == "typed" else t))
    after: list[int] = []
    if out:
        nxt = out[-1].number + 1
        for i in range(next(r for r in rec_at if r > out[-1].index) + 1, b):
            t = flat(rep.paragraphs[i])
            nv = observation_number(t, rep.info[i]) if t and not rep.info[i].in_table else None
            if nv and nv[0] == nxt:
                after.append(nxt)
                nxt += 1
    return out, after


def toc_part2_pages(rep: Report) -> str:
    """Part II's pages from the report's table of contents: from the first page it gives under
    Part II to the last, or to the page before Part III where it gives only start pages."""
    paras = rep.paragraphs
    start = next((i for i, p in enumerate(paras) if re.match(r"^TABLE OF CONTENTS\b", p, re.I)), None)
    if start is None:
        return ""
    window = []
    for p in paras[start + 1:start + 250]:
        if p.startswith("INDEPENDENT AUDITOR"):
            break
        if p.strip():
            window.append(p)
    k2 = next((i for i, p in enumerate(window) if re.match(r"^PART\s*II\b(?!I)", p.strip(), re.I)
               or re.search(r"(?:observations?|findings)\s+and\s+recommendations", p, re.I)), None)
    if k2 is None:
        return ""
    k3 = next((i for i in range(k2 + 1, len(window))
               if re.search(r"status of (?:implementation of )?prior", window[i], re.I)
               or re.match(r"^(?:PART\s*)?III\b", window[i].strip(), re.I)), len(window))
    pages = []
    for p in window[k2:k3]:
        last = [x.strip() for x in p.split("\t") if x.strip()][-1]
        if PAGES.match(last):
            pages.append(last)
    if not pages:
        # Column layout (Don Carlos, Kitaotao): every title, then a "Page" heading and the
        # pages in the same order; part headings have no page.
        pg = next((i for i, p in enumerate(window) if re.match(r"^Page\b", p, re.I) and len(p) < 8), None)
        if pg is not None and pg > k3:
            titles = [p for p in window[:pg] if not re.match(r"^PART\s+(?:I|II|IV)\b(?!I)", p)]
            col = []
            for p in window[pg + 1:]:
                if not PAGES.match(p.strip()):
                    break
                col.append(p.strip())
            pages = [col[titles.index(p)] for p in window[k2 + 1:k3] if p in titles and titles.index(p) < len(col)]
    if not pages:
        return ""
    pages = [p.replace("–", "-").replace(" ", "") for p in pages]
    first, last = pages[0].split("-")[0], pages[-1]
    if "-" in last:
        end = last.split("-")[-1]
    else:
        p3 = toc_part3_page(rep).split("-")[0]
        end = str(int(p3) - 1) if p3.isdigit() and int(p3) - 1 > int(last) else last
    return first if end == first else f"{first}-{end}"


def number_ranges(nums: list[int]) -> str:
    """1, 2, 3, 4, 6, 7 -> "1-4, 6-7"."""
    out: list[list[int]] = []
    for n in nums:
        if out and n == out[-1][-1] + 1:
            out[-1].append(n)
        else:
            out.append([n])
    return ", ".join(f"{r[0]}-{r[-1]}" if len(r) > 1 else str(r[0]) for r in out)


def count_row(numbers: list[int], after: list[int]) -> dict:
    n = len(numbers)
    note = "" if numbers == list(range(1, n + 1)) else f"COA numbers these {n} findings {number_ranges(numbers)}."
    return {"findings": n, "numbers_as_printed": number_ranges(numbers), "count_note": note,
            "numbered_after_findings": number_ranges(after)}


def word_numbers(path: Path) -> list[tuple[str, str]] | None:
    """Word's own list numbers, if scripts/word_list_numbers.ps1 saved them beside the report:
    (number, opening text) per list paragraph, in order."""
    tsv = path.with_name(path.stem + ".word-lists.tsv")
    if not tsv.exists():
        return None
    rows = []
    for line in tsv.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            # Word's text keeps a footnote's reference mark (\x02) that the file's text doesn't
            rows.append((parts[1].strip(), flat(re.sub(r"[\x00-\x08\x0b-\x1f]", "", " ".join(parts[2:])))))
    return rows


def word_labels(rep: Report, word: list[tuple[str, str]]) -> dict[int, str]:
    """Word's number for each of our numbered paragraphs, matched by opening text.

    Every numbered paragraph is matched, in document order, not just the findings: the
    executive summary often repeats a finding's opening words in a list of its own, and only
    walking the whole document in order keeps the two apart."""
    index: dict[str, list[int]] = {}
    for j, (_, t) in enumerate(word):
        index.setdefault(t[:30], []).append(j)
    used: set[int] = set()
    out: dict[int, str] = {}
    last = -1
    for i, info in enumerate(rep.info):
        if not info.label and info.fmt not in ("bullet", "none"):
            continue
        key = flat(rep.paragraphs[i])[:30]
        cands = [j for j in index.get(key, []) if j not in used] if key else []
        if not cands:
            continue
        j = next((c for c in cands if c > last), cands[0])
        used.add(j)
        out[i] = word[j][0]
        last = j
    return out


def finding_checks(rep: Report, found: list[Finding], after: list[int], pages: str
                   ) -> list[tuple[str, bool | None, str]]:
    numbers = [f.number for f in found]
    printed = number_ranges(numbers)
    then = f"; then {number_ranges(after)} on paragraphs without a recommendation" if after else ""
    checks: list[tuple[str, bool | None, str]] = [
        ("findings found", bool(found), f"{len(found)}, numbered {printed}" if found
         else "no numbered observation with a recommendation in Part II"),
        ("findings: COA's numbers run 1 to N", numbers == list(range(1, len(found) + 1)), f"{printed}{then}"),
        ("findings: Part II's pages in the table of contents", bool(pages), pages or "not found"),
    ]
    word = word_numbers(rep.path)
    listed = [f for f in found if f.numbered == "Word list"]
    if word is None:
        checks.append(("findings: numbers match Word's", None, "Word's numbers not saved for this report"))
    elif not listed:
        checks.append(("findings: numbers match Word's", None, "every number is typed"))
    else:
        labels = word_labels(rep, word)
        bad = []
        for f in listed:
            shown = labels.get(f.index)
            m = re.match(r"\(?(\d+)", shown or "")
            if shown is None:
                bad.append(f"{f.number}: not found in Word's list")
            elif not m or int(m.group(1)) != f.number:
                bad.append(f"{f.number}: Word shows '{shown}'")
        checks.append(("findings: numbers match Word's", not bad,
                       "; ".join(bad) or f"all {len(listed)} Word list numbers agree"))
    return checks


# ---------------------------------------------------------------------------- disallowances
#
# COA keeps a running record of the notices it issues: suspensions (documents still missing),
# disallowances (spending it rules improper) and charges, each until it is settled. Every
# report gives the balance at December 31, under a heading such as "Summary of NS, ND, NC
# issued during the year" or "Status of Audit Suspensions, Disallowances and Charges". It sits
# in the executive summary, in Part II or in Part III (from CY 2024, section B), often in two
# of these. The site shows the disallowances still unsettled; suspensions and charges are kept
# beside them, never added in (docs/phase1-data.md#unsettled-disallowances).

NOTICES = ["suspension", "disallowance", "charge"]
FUND_NAMES = {"general fund": "General Fund", "special education fund": "Special Education Fund",
              "trust fund": "Trust Fund", "all funds": "all"}
ND_HEAD = re.compile(r"^(?:[A-Z]|\d{1,2})?[.)]?\s*(?:(?:summary|status)\s+of\b.*?\b(?:suspensions?|NS)\b.*?"
                     r"\b(?:disallowances?|ND)\b|notices?\s+of\s+suspensions?,\s*disallowances?)", re.I)
ND_STOP = re.compile(r"^(?:[A-Z][.)]\s*|\d{1,2}\.\s*)?(?:status\s+of\s+implementation|part\s*(?:[IVX]+|\d)\b"
                     r"|table\s+of\s+contents|annex|appendi)", re.I)
ND_KINDS = ["beginning", "error_in_previous_aar", "adjusted_beginning", "issued", "matured_to_nd", "settled",
            "ending"]
FULL_AMOUNT = re.compile(r"\d{1,3}(?:,\d{3})+\.\d{2}")


@dataclass
class NDRow:
    fund: str  # "all" where COA gives one figure for the government, else the fund
    notice: str  # suspension, disallowance, charge or total
    label: str  # as printed
    cells: dict[str, str]  # kind (ND_KINDS) -> amount as printed


@dataclass
class NDSection:
    block: int
    part: str  # Executive summary, Part II or Part III
    heading: str
    paras: list[str]  # COA's paragraphs under the heading
    intro: list[str]  # those before the first table
    rows: list[NDRow] = field(default_factory=list)
    said: dict[str, tuple[str, Decimal]] = field(default_factory=dict)  # from a sentence: notice -> amount
    said_total: str = ""
    opens_nil_said: bool = False  # "no unsettled ... as of January 1"
    note: str = ""


def nd_amount(cell: str) -> Decimal | None:
    """An amount in COA's table. A dash or a blank cell in a row COA prints means nil (the
    totals bear this out); a settlement may be printed "(10,400.00)" or "144,630.00-". None
    if the cell isn't an amount."""
    t = re.sub(r"[₱P\s]", "", cell)
    if t in ("", "-", "–", "—"):
        return Decimal(0)
    neg = t.startswith("(") and t.endswith(")") or t.endswith("-") or t.startswith("-")
    t = t.strip("()-")
    if not re.fullmatch(r"\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?", t):
        return None
    v = Decimal(t.replace(",", ""))
    return -v if neg else v


def money(v: Decimal) -> str:
    return f"{v:.2f}"


def notice_of(label: str) -> str | None:
    s = flat(label).lower()
    if re.match(r"^(?:grand\s+)?total\b", s):
        return "total"
    if re.search(r"suspension|^ns\b", s):
        return "suspension"
    if re.search(r"disallowance|^nd\b", s):
        return "disallowance"
    if re.search(r"\bcharges?\b|^nc\b", s):
        return "charge"
    return None


def fund_of(row: list[str]) -> str | None:
    """A row that only names a fund ("GENERAL FUND", "ALL FUNDS") starts that fund's rows."""
    cells = [flat(c) for c in row if flat(c)]
    if len(cells) == 1 or (cells and len(set(cells)) == 1):
        return FUND_NAMES.get(cells[0].lower())
    return None


def nd_column(head: str, year: int) -> str | None:
    """What a column of COA's table holds, from its heading."""
    h = flat(head).lower()
    date = lambda y: rf"(?:dec(?:ember|\.)?\s*31,?\s*|12/31/){y}\b"
    if not h:
        return None
    if "unsettled" in h:
        return "ending"
    if "nssdc" in h or "settle" in h:  # Notice of Settlement of Suspensions, Disallowances and Charges
        return "settled"
    if "matured" in h:
        return "matured_to_nd"
    if "error" in h:
        return "error_in_previous_aar"
    if "adjusted" in h:
        return "adjusted_beginning"
    if re.search(r"\bbeg", h):
        return "beginning"
    if "ending" in h:
        return "ending"
    if "issu" in h or "this period" in h or re.search(r"\bn[sdc]\s*/", h):
        return "issued"
    if re.search(date(year), h):
        return "ending"
    if re.search(date(year - 1), h) or re.search(rf"jan(?:uary|\.)?\s*1,?\s*{year}\b", h):
        return "beginning"
    if "balance" in h:
        return "balance"
    return None


def nd_line(label: str) -> str | None:
    """What a row holds, in a table that runs the notices across (Damulog, Valencia)."""
    s = flat(label).lower()
    if re.search(r"begin|january\s+1|jan\.\s*1", s):
        return "beginning"
    if "issu" in s:
        return "issued"
    if "settle" in s:
        return "settled"
    if re.search(r"ending|december\s+31|dec\.\s*31", s):
        return "ending"
    return None


def nd_table(t: Table, year: int, fund: str) -> tuple[list[NDRow], str]:
    """COA's rows from one table, and a note on anything read by position rather than heading."""
    g = [[flat(c) for c in r] for r in (t.grid or t.rows)]
    if not g:
        return [], ""
    across = {j: notice_of(c) for j, c in enumerate(g[0]) if j and notice_of(c) in NOTICES}
    if len(across) >= 2:
        # The notices run across and the balances down, one table or block per fund.
        fund = FUND_NAMES.get(g[0][0].lower(), fund)
        cells: dict[tuple[str, str], dict[str, str]] = {}
        for r in g[1:]:
            f = fund_of(r)
            if f:
                fund = f
                continue
            kind = nd_line(r[0]) if r else None
            if kind:
                for j, n in across.items():
                    cells.setdefault((fund, n), {})[kind] = r[j] if j < len(r) else ""
        labels = {n: g[0][j] for j, n in across.items()}
        return [NDRow(f, n, labels[n], c) for (f, n), c in cells.items()], ""

    first = next((i for i, r in enumerate(g) if r and (notice_of(r[0]) or fund_of(r))), None)
    if first is None:
        return [], ""
    width = max(len(r) for r in g)
    heads = [" ".join(dict.fromkeys(h[j] for h in g[:first] if j < len(h) and h[j])) for j in range(width)]
    kinds = {j: nd_column(heads[j], year) for j in range(1, width)}
    note = ""
    if "ending" not in kinds.values():
        if "balance" in kinds.values():  # "Balance" alone: the year-end balance
            kinds = {j: "ending" if k == "balance" else k for j, k in kinds.items()}
        else:
            begins = [j for j, k in kinds.items() if k == "beginning"]
            if len(begins) >= 2:  # both balance columns dated the year before: a slip in the heading
                kinds[begins[-1]] = "ending"
                note = f"the column headings date both balances {heads[begins[0]]!r}; read by position"
    rows = []
    for r in g[first:]:
        f = fund_of(r)
        if f:
            fund = f
            continue
        n = notice_of(r[0]) if r else None
        if not n:
            continue
        got: dict[str, str] = {}
        for j, k in kinds.items():
            if k and j < len(r) and r[j] not in ("₱", "P") and (k not in got or r[j]):
                got[k] = r[j]
        for k in set(kinds.values()) - {None}:
            got.setdefault(k, "")
        rows.append(NDRow(fund, n, r[0], got))
    return rows, note


def nd_sentence(sec: NDSection) -> None:
    """Balances COA gives in words, where there is no table: "has an outstanding Notice of
    Suspensions and Disallowances in the amount of P11,439,050.25 and P7,674,912.61 ...,
    respectively", "has no outstanding suspensions, disallowances, and charges", "stood at P0.00"."""
    text = " ".join(sec.paras)
    named = lambda s: [n for n in re.findall(r"suspension|disallowance|charge", s, re.I)]
    m = re.search(r"\bstood\s+at\s+((?:P|₱)\s*0\.00)", text)
    if m:
        sec.said = {n: ("", Decimal(0)) for n in NOTICES}
        sec.said_total = m.group(1)
    for m in re.finditer(r"\bno\s+outstanding\s+((?:(?!\bbut\b|\bas\s+of\b)[^.])*)", text, re.I):
        for n in named(m.group(1)):
            sec.said[n.lower()] = ("", Decimal(0))
    amt = r"((?:P|₱)\s*\d{1,3}(?:,\d{3})*\.\d{2})"
    for m in re.finditer(rf"(?<!no )\boutstanding\s+((?:(?!outstanding)[^.])*?)\s+in\s+the\s+amount\s+of\s+{amt}"
                         rf"(?:\s+and\s+{amt})?", text, re.I):
        for n, a in zip(named(m.group(1)), [g for g in m.groups()[1:] if g]):
            sec.said[n.lower()] = (a, nd_amount(a))
    sec.opens_nil_said = bool(re.search(r"no\s+unsettled\s+suspensions[^.]*as\s+of\s+January\s+1", text, re.I))


def nd_sections(rep: Report) -> list[NDSection]:
    """Every block of the report headed as COA's status of suspensions, disallowances and
    charges, outside the table of contents, with what follows it up to the next heading."""
    year = int(rep.year)
    blocks = rep.blocks
    toc = next((i for i, b in enumerate(blocks)
                if isinstance(b, str) and re.match(r"^TABLE OF CONTENTS\b", b.strip(), re.I)), None)
    toc_end = next((i for i, b in enumerate(blocks) if toc is not None and i > toc and isinstance(b, str)
                    and b.startswith("INDEPENDENT AUDITOR")), toc)
    p2 = part2_range(rep)
    out = []
    for i, b in enumerate(blocks):
        if not isinstance(b, str) or len(flat(b)) >= 200 or not ND_HEAD.match(flat(b)):
            continue
        if toc is not None and toc <= i < toc_end:
            continue
        p = rep.block_start[i]
        if toc is not None and i < toc:
            part = "Executive summary"
        elif p2 and p >= p2[0]:
            part = "Part II" if p < p2[1] else "Part III"
        else:
            continue  # Part I: the notes to the statements carry the receivable, not COA's balances
        sec = NDSection(i, part, flat(b), [], [])
        seen = 0
        for j in range(i + 1, len(blocks)):
            nb = blocks[j]
            if isinstance(nb, str):
                t = flat(nb)
                if not t:
                    continue
                if ND_HEAD.match(t) and len(t) < 200 or ND_STOP.match(t):
                    break
                sec.paras.append(t)
                if not sec.rows:
                    sec.intro.append(t)
            else:
                rows, note = nd_table(nb, year, "General Fund" if re.search(
                    r"for\s+the\s+general\s+fund", " ".join(sec.intro), re.I) else "all")
                if not rows:
                    if sec.rows:
                        break  # another section's table
                else:
                    sec.rows += rows
                    sec.note = "; ".join(x for x in (sec.note, note) if x)
            seen += 1
            if seen >= 10:
                break
        if not sec.rows:
            nd_sentence(sec)
        out.append(sec)
    return out


def nd_value(rows: list[NDRow], notice: str, kind: str) -> tuple[Decimal | None, str, list[NDRow]]:
    """The figure for one notice: COA's own row for the whole government where it gives one,
    else its fund rows added (the rows are returned so the caller can say so)."""
    whole = [r for r in rows if r.notice == notice and r.fund == "all" and kind in r.cells]
    if whole:
        return nd_amount(whole[-1].cells[kind]), whole[-1].cells[kind], whole[-1:]
    funds = [r for r in rows if r.notice == notice and r.fund != "all" and kind in r.cells]
    if not funds:
        return None, "", []
    vals = [nd_amount(r.cells[kind]) for r in funds]
    if any(v is None for v in vals):
        return None, "", funds
    nonzero = [r for r, v in zip(funds, vals) if v]
    printed = nonzero[0].cells[kind] if len(nonzero) == 1 else funds[0].cells[kind] if not nonzero else ""
    return sum(vals, Decimal(0)), printed, funds


def nd_shown(sec: NDSection) -> dict:
    """The row of disallowances.csv for one section: the figures we show and how we got them."""
    out: dict = {"item": sec.heading, "quote": " ".join(sec.paras)}
    notes = []
    if sec.rows:
        funds = list(dict.fromkeys(r.fund for r in sec.rows if r.fund != "all"))
        whole = any(r.fund == "all" for r in sec.rows)
        for n in NOTICES:
            v, printed, used = nd_value(sec.rows, n, "ending")
            out[f"{n}s"] = "" if v is None else money(v)
            out[f"{n}s_as_printed"] = printed
            nonzero = [r for r in used if nd_amount(r.cells["ending"])]
            if len(nonzero) > 1:
                notes.append(f"{n.capitalize()}s are the " + " and the ".join(f"{r.fund}'s {r.cells['ending']}"
                                                                           for r in nonzero)
                             + ", added together by us; COA gives no total.")
        tot = [r for r in sec.rows if r.notice == "total" and r.fund == "all" and "ending" in r.cells]
        out["total_as_printed"] = tot[-1].cells["ending"] if tot else ""
        if funds and not whole:
            out["funds"] = ", ".join(funds)
            notes.insert(0, "COA gives each fund separately, with no total for all funds." if len(funds) == 3 else
                         f"COA gives the {' and '.join(funds)} only, with no total for all funds; "
                         "what it says of the other funds is in the quote.")
    elif sec.said:
        for n in NOTICES:
            printed, v = sec.said.get(n, ("", None))
            out[f"{n}s"] = "" if v is None else money(v)
            out[f"{n}s_as_printed"] = printed
        out["total_as_printed"] = sec.said_total
        notes.append("COA gives the balance in words, with no table.")
    out["note"] = " ".join(notes)
    return out


def nd_opening(sec: NDSection | None, rows: list[NDRow] | None = None) -> dict[str, Decimal | None]:
    rows = sec.rows if sec is not None else rows or []
    return {n: nd_value(rows, n, "beginning")[0] for n in NOTICES}


def nd_checks(sec: NDSection, rows: list[NDRow]) -> list[tuple[str, bool | None, str]]:
    """Arithmetic inside COA's table: each row across, notices down to the total, funds to all funds."""
    checks = []
    bad, tested = [], 0
    for r in rows:
        c = {k: nd_amount(v) for k, v in r.cells.items()}
        if "ending" not in c or "beginning" not in c:
            continue
        tested += 1
        start = c["adjusted_beginning"] if r.cells.get("adjusted_beginning") else c["beginning"]
        parts = [start, c.get("issued", Decimal(0)), c.get("settled", Decimal(0)), c["ending"]]
        if any(v is None for v in parts):
            bad.append(f"{r.fund} {r.label}: an amount can't be read")
        elif start + parts[1] - abs(parts[2]) != parts[3]:
            bad.append(f"{r.fund} {r.label}: {start} + {parts[1]} - {abs(parts[2])} = "
                       f"{start + parts[1] - abs(parts[2])}, printed {r.cells['ending']}")
    checks.append(("disallowances: rows add across", None if not tested else not bad,
                   "; ".join(bad) or (f"{tested} rows: beginning + issued - settled = ending" if tested
                                      else "the table gives year-end balances only")))
    bad, tested = [], 0
    for fund in dict.fromkeys(r.fund for r in rows):
        mine = [r for r in rows if r.fund == fund]
        total = [r for r in mine if r.notice == "total"]
        if not total:
            continue
        for k in total[-1].cells:
            if k not in ND_KINDS or not any(k in r.cells for r in mine if r.notice != "total"):
                continue
            tested += 1
            parts = [nd_amount(r.cells.get(k, "")) for r in mine if r.notice in NOTICES]
            t = nd_amount(total[-1].cells[k])
            if t is None or any(v is None for v in parts):
                bad.append(f"{fund} {k}: an amount can't be read")
            elif sum(map(abs, parts), Decimal(0)) != abs(t):
                bad.append(f"{fund} {k}: notices add to {sum(map(abs, parts), Decimal(0))}, "
                           f"total printed {total[-1].cells[k] or 'blank'}")
    checks.append(("disallowances: notices add to COA's total", None if not tested else not bad,
                   "; ".join(bad) or (f"{tested} columns" if tested else "no total row")))
    funds = [f for f in dict.fromkeys(r.fund for r in rows) if f != "all"]
    if funds and any(r.fund == "all" for r in rows):
        bad, tested = [], 0
        for n in NOTICES + ["total"]:
            whole = [r for r in rows if r.fund == "all" and r.notice == n]
            if not whole:
                continue
            for k in whole[-1].cells:
                tested += 1
                parts = [nd_amount(r.cells.get(k, "")) for r in rows if r.fund in funds and r.notice == n]
                t = nd_amount(whole[-1].cells[k])
                if t is None or any(v is None for v in parts) or sum(map(abs, parts), Decimal(0)) != abs(t):
                    each = ", ".join(r.cells.get(k, "") or "blank" for r in rows if r.fund in funds and r.notice == n)
                    bad.append(f"{n} {k}: funds {each}, all funds {whole[-1].cells[k] or 'blank'}")
        checks.append(("disallowances: funds add to all funds", not bad, "; ".join(bad) or f"{tested} amounts"))
    else:
        checks.append(("disallowances: funds add to all funds", None,
                       "not split by fund" if not funds else "no total for all funds"))
    if sec is not None:
        amounts = [a for p in sec.intro for a in FULL_AMOUNT.findall(p)]
        printed = {nd_amount(v) for r in rows for v in r.cells.values()}
        missing = [a for a in amounts if nd_amount(a) not in printed]
        checks.append(("disallowances: COA's sentence agrees with the table",
                       None if not amounts or not rows else not missing,
                       f"not in the table: {', '.join(missing)}" if missing else
                       f"{', '.join(amounts)}" if amounts and rows else "no amount before the table"))
    return checks


def nd_toc_page(rep: Report, sec: NDSection) -> str:
    """The section's page where COA's table of contents lists it, else its part's pages."""
    key = re.sub(r"[^a-z]", "", re.sub(r"^(?:[A-Z]|\d{1,2})[.)]\s*", "", sec.heading).lower())
    for title, page in toc_entries(rep):
        t = re.sub(r"[^a-z]", "", re.sub(r"^(?:[A-Z]|\d{1,2})\s*[.)–-]\s*", "", title).lower())
        if t and (t in key or key in t) and len(t) > 15:
            return page.replace("–", "-").replace(" ", "")
    return toc_part2_pages(rep) if sec.part == "Part II" else toc_part3_page(rep)


def summary_pdf_page(year: str, lgu: str, heading: str, amounts: list[str]) -> tuple[str, bool, str]:
    """The page of COA's executive summary PDF that carries the section, from the text that
    scripts/pdf_pages.py saved beside the PDF, and whether it shows the same amounts."""
    saved = sorted((RAW / year / lgu).glob("*Executive-Summary*.pages.txt"))
    if not saved:
        return "", False, "the PDF's text isn't saved; run scripts/pdf_pages.py"
    split = re.split(r"^=== PDF page (\d+) ===$", saved[0].read_text(encoding="utf-8"), flags=re.M)
    pages = {int(split[k]): split[k + 1] for k in range(1, len(split), 2)}
    key = re.sub(r"[^a-z]", "", re.sub(r"^(?:[A-Z]|\d{1,2})[.)]\s*", "", heading).lower())
    hit = next((n for n, t in sorted(pages.items()) if key in re.sub(r"[^a-z]", "", t.lower())), None)
    if hit is None:
        return "", False, f"{saved[0].name}: heading not found"
    near = re.sub(r"\s+", "", pages[hit] + pages.get(hit + 1, ""))
    missing = [a for a in amounts if a not in near]
    shown = f"missing {', '.join(missing)}" if missing else f"all {len(amounts)} amounts shown"
    return str(hit), not missing, f"{saved[0].name} p. {hit}: {shown}"


def printed_amounts(rows: list[NDRow], said: dict[str, tuple[str, Decimal]] | None = None) -> list[str]:
    """Every non-nil amount COA prints in the section, digits only, for finding it in the PDF."""
    cells = [v for r in rows for v in r.cells.values()] + [a for a, _ in (said or {}).values()]
    return list(dict.fromkeys(m.group(0) for c in cells for m in [FULL_AMOUNT.search(c)] if m and nd_amount(c)))


# ---------------------------------------------------------------------------- appropriations
#
# Part I's Statement of Comparison of Budget and Actual Amounts sets each fund's budget
# (original and final, for current and continuing appropriations) beside the actual amounts,
# which for appropriations are the obligations. We take the final budget for the current year
# and its obligations, each fund as COA prints it (docs/phase1-data.md#appropriations-and-obligations).

BUDGET_ITEM = "Statement of Comparison of Budget and Actual Amounts"
# Dangcagan CY 2025 titles it "STATEMENT OF BUDGET AND ACTUAL AMOUNTS". Not the notes'
# reconciliation table, whose rows say "Comparison Statement of Budget and Actual" (Sumilao).
BUDGET_TITLE = re.compile(r"(?<!comparison )STATEMENTS?\s+OF\s+(?:COMPARISON\s+OF\s+)?BUDGET(?:S|ED)?\s+AND\s+ACTUAL",
                          re.I)
# Where the statement ends: the notes, or the reconciliation and summaries some reports add.
BUDGET_STOP = re.compile(r"^(?:(?:CONSOLIDATED\s+|CONDENSED\s+)?NOTES?\s+TO\s+(?:THE\s+)?(?:CONDENSED\s+|CONSOLIDATED\s+)?"
                         r"FINANCIAL\s+STATEMENTS?|RECONCILIATION\s+BETWEEN|SUMMARY\s+ON\s+APPROPRIATIONS"
                         r"|STATEMENTS?\s+OF\s+CASH\s+FLOWS?|STATEMENTS?\s+OF\s+CHANGES|PART\s+II\b)", re.I)
BUDGET_FUND = re.compile(r"^(?:[A-Z]\.\s*|[IVX]+\.\s*)?(GENERAL\s+FUND\w*(?:\s+(?:AND|&)\s+SPECIAL\s+EDUCATION\s+FUND)?"
                         r"|SPECIAL\s+EDUCATION\s+FUND|CONSOLIDATED|ALL\s+FUNDS)\b", re.I)
# An amount in the statement, well formed or not ("3.411,797.60" is in Damulog's CY 2022).
BUDGET_AMOUNT = re.compile(r"^(?:P|₱)?\(?(?:P|₱)?\d{1,3}(?:[,.]\d{3})*[.,]\d{2}\)?-?$")
BUDGET_COLUMNS = ["original", "final", "diff_original_final", "actual", "diff_final_actual"]
BUDGET_KINDS = {"total_current": "current", "total_continuing": "continuing", "total": "total"}

B_TOTAL_REV = re.compile(r"^TOTAL\s+(?:REVENUES?|RECEIPTS|SOURCES)\b")
# The province's CY 2025 statement labels it just "Total Current" (General Fund) and
# "Total- Current" (SEF).
B_TOTAL_CUR = re.compile(r"^(?:SUB-?\s*)?TOTAL(?:,?\s+|\s*[-–]\s*)(?:EXPENSES?\s+)?CURRENT"
                         r"(?:\s+(?:YEAR\s+)?(?:APP?R|EXPEND|OBLIG|BUDGET)|\s*$)")
B_TOTAL_CONT = re.compile(r"^(?:SUB-?\s*)?TOTAL,?\s+(?:EXPENSES?\s+)?CONTINU\w*\s+(?:APP?R|EXPEND|OBLIG)")
B_TOTAL = re.compile(r"^(?:GRAND\s+)?TOTAL,?\s+(?:EXPENSES?\s+CURRENT\s*(?:&|AND)\s*CONTINU"
                     r"|(?:APP?R\w*|EXPENDITURES?|OBLIGATIONS?)\b)")
B_SURPLUS = re.compile(r"^(?:NET\s+)?SURPLUS|^EXCESS|^\(?DEFICIT|^DETAILS\s+OF\s+SURPLUS")
B_HEAD_CUR = re.compile(r"^(?:[A-Z0-9]+[.)]\s*)?CURRENT\s+(?:YEAR\s+)?(?:APP?R\w*|EXPEND\w*|BUDGET)")
B_HEAD_CONT = re.compile(r"^(?:[A-Z0-9]+[.)]\s*)?CONTINU\w*\s+(?:APP?R\w*|EXPEND\w*)")
B_HEAD_EXP = re.compile(r"^(?:[A-Z0-9]+[.)]\s*)?(?:EXPENDITURES?|APPROPRIATIONS?|OBLIGATIONS?)\b")
B_HEAD_REV = re.compile(r"^(?:[A-Z0-9]+[.)]\s*)?(?:REVENUES?|RECEIPTS)\b")


def is_budget_amount(cell: str) -> bool:
    c = cell.strip()
    if re.search(r"\d\s+\(?\d", c):  # two amounts in one cell, not one amount
        return False
    c = c.replace(" ", "")
    return c in ("-", "–", "—") or bool(BUDGET_AMOUNT.match(c))


def budget_amount(cell: str) -> Decimal | None:
    """A statement amount: a blank cell or a dash in a row COA prints is nil (the row's own
    differences bear this out). None if it isn't a well-formed amount."""
    c = re.sub(r"[₱P\s]", "", cell or "")
    if c in ("", "-", "–", "—"):
        return Decimal(0)
    neg = c.startswith("(") or c.endswith(")") or c.endswith("-")
    c = c.strip("()-")
    if not re.fullmatch(r"\d{1,3}(?:,\d{3})*\.\d{2}", c):
        return None
    return -Decimal(c.replace(",", "")) if neg else Decimal(c.replace(",", ""))


def budget_fund(text: str) -> str | None:
    """The fund a heading names: "General Fund" (also COA's "General Fundnd"), "Special
    Education Fund", the two together, or a consolidated statement."""
    t = flat(text)
    if len(t) > 90 or re.search(r"\btotal\b", t, re.I):
        return None
    m = BUDGET_FUND.match(t)
    if not m:
        return None
    s = m.group(1).upper()
    if "SPECIAL" in s and "GENERAL" in s:
        return "General Fund and Special Education Fund"
    return ("General Fund" if s.startswith("GENERAL") else "Special Education Fund" if s.startswith("SPECIAL")
            else "Consolidated" if s.startswith("CONSOLIDATED") else "All funds")


def budget_column(head: str, year: str) -> str | None:
    """What a column holds, from its headings. A "Difference" column is settled by position."""
    h = flat(head).lower()
    if not h:
        return None
    years = set(re.findall(r"\b20\d\d\b", h))
    if years and year not in years:
        return "other_year"  # Don Carlos CY 2022 sets each 2021 amount beside the 2022 one
    if re.search(r"differ|varian", h):
        return "diff"
    if "original" in h:
        return "original"
    if "final" in h:
        return "final"
    if re.search(r"actual|obligat", h):
        return "actual"
    if "budget" in h:  # "Budgeted Amounts" alone over the original budget (the province)
        return "original"
    return None


def budget_header_row(g: list[str]) -> bool:
    cells = [c for c in dict.fromkeys(flat(c) for c in g) if c]
    if len(cells) < 2 or any(is_budget_amount(c) for c in cells):
        return False
    return any(re.search(r"original|final|actual|differ|budget", c, re.I) for c in cells) or all(
        re.fullmatch(r"(?:CY\s*)?20\d\d", c) for c in cells)


def budget_columns(rows: list[list[str]], year: str) -> list[str | None]:
    width = max(len(g) for g in rows)
    heads = [" ".join(dict.fromkeys(g[j] for g in rows if j < len(g) and g[j])) for j in range(width)]
    cols = [budget_column(h, year) for h in heads]
    seen_actual = False
    for j, c in enumerate(cols):
        if c == "actual":
            seen_actual = True
        elif c == "diff":
            cols[j] = "diff_final_actual" if seen_actual else "diff_original_final"
    return cols


def budget_consistent(cells: dict[str, str], strict: bool = False) -> bool | None:
    """Whether a row's own differences agree with its amounts (sign aside: reports differ on
    which way they subtract). None if the row has no difference to test. Strict: a blank
    difference counts as nil too, so both differences are always tested."""
    v = {k: budget_amount(cells[k]) for k in BUDGET_COLUMNS if k in cells}
    if any(x is None for x in v.values()):
        return False
    if strict:
        v = {k: v.get(k, Decimal(0)) for k in BUDGET_COLUMNS}
    tested, ok = False, True
    if "diff_original_final" in v and ("original" in v or "final" in v):
        tested = True
        ok &= abs(v.get("final", Decimal(0)) - v.get("original", Decimal(0))) == abs(v["diff_original_final"])
    if "diff_final_actual" in v and ("final" in v or "actual" in v):
        tested = True
        ok &= abs(v.get("final", Decimal(0)) - v.get("actual", Decimal(0))) == abs(v["diff_final_actual"])
    return ok if tested else None


@dataclass
class BudgetRow:
    fund: str
    section: str  # revenue, sources, current, expenditures (no "Current" heading), continuing, after
    kind: str  # line, total_revenue, total_current, total_continuing, total
    label: str  # as printed
    cells: dict[str, str]  # column -> amount as printed; a blank cell is left out
    read: str  # how the amounts were placed in their columns


@dataclass
class BudgetStatement:
    where: str  # "Word table 9", "picture word/media/image12.emf", "PDF"
    rows: list[BudgetRow] = field(default_factory=list)
    funds: dict[str, str] = field(default_factory=dict)  # fund -> its name as printed


class BudgetReader:
    """Reads the statement's rows in order, keeping track of the fund, the section (revenue,
    current or continuing appropriations) and what each column holds."""

    def __init__(self, year: str, where: str):
        self.year = year
        self.st = BudgetStatement(where)
        self.fund = ""
        self.section = ""
        self.cols: list[str | None] = []
        self.order: list[str] = []

    def set_fund(self, fund: str, printed: str) -> None:
        if fund != self.fund:  # the same fund named again on a new page carries on
            self.fund = fund
            self.st.funds.setdefault(fund, flat(printed))
            self.section = ""

    def text(self, t: str) -> None:
        f = budget_fund(t)
        if f:
            self.set_fund(f, t)

    def set_columns(self, cols: list[str | None]) -> None:
        if any(c in BUDGET_COLUMNS for c in cols):
            self.cols = cols
            self.order = list(dict.fromkeys(c for c in cols if c in BUDGET_COLUMNS))

    def table(self, t: Table) -> None:
        grid = t.grid or t.rows
        i = 0
        while i < len(grid):
            if budget_header_row(grid[i]):
                # A block of heading rows, at the top or repeated on a new page. It runs to the
                # last heading row before the next amount, so a row between ("of Original and"
                # in Lantapan's) is part of it.
                j = last = i
                while j < len(grid) and not any(is_budget_amount(c) for c in grid[j][1:]):
                    if budget_header_row(grid[j]):
                        last = j
                    j += 1
                block = [g for g in grid[i:last + 1] if any(flat(c) for c in g)]
                first = next((c for c in block[0] if flat(c)), "")
                if budget_fund(first):  # "GENERAL FUND | Budgeted Amounts | ..."
                    self.set_fund(budget_fund(first), first)
                self.set_columns(budget_columns(block, self.year))
                i = last + 1
                continue
            self.row(t.rows[i], grid[i])
            i += 1
        for sub in t.nested:  # Damulog's SEF statement sits in a cell of the General Fund's table
            self.table(sub)

    def row(self, r: list[str], g: list[str]) -> None:
        k = next((j for j, c in enumerate(r) if flat(c)), None)
        if k is None:
            return
        label = flat(r[k])
        if is_budget_amount(label):
            label, k = "", k - 1
        vals = [flat(c) for c in r[k + 1:] if is_budget_amount(c)]
        # Two of COA's rows in one cell, each cell holding both amounts (the province's CY 2023
        # SEF: "Capital Outlay Total Current Appropriations | 80,462,653.40 94,000,000.00 | ...").
        multi = [flat(c).split(" ") for c in r[k + 1:] if flat(c)]
        if not vals and multi and all(len(m) == len(multi[0]) > 1 and all(map(is_budget_amount, m)) for m in multi):
            n = len(multi[0])
            parts = re.split(r"\s+(?=Total\b)", label)
            labels = parts if len(parts) == n else [label] * n
            for q in range(n):
                cells = [labels[q]] + [m[q] for m in multi]
                self.row(cells, cells)
            return
        up = label.upper()
        if not vals:
            f = budget_fund(label)
            if f:
                self.set_fund(f, label)
            elif B_HEAD_CUR.match(up):
                self.section = "current"
            elif B_HEAD_CONT.match(up):
                self.section = "continuing"
            elif B_HEAD_EXP.match(up):
                self.section = "expenditures"
            elif B_HEAD_REV.match(up):
                self.section = "revenue"
            return
        spending = self.section in ("current", "expenditures", "continuing")
        if B_TOTAL_REV.match(up):
            kind = "total_revenue"
        elif B_TOTAL_CUR.match(up):
            kind = "total_current"
        elif B_TOTAL_CONT.match(up):
            kind = "total_continuing"
        elif B_TOTAL.match(up) or (up in ("TOTAL", "GRAND TOTAL") and spending):
            kind = "total"  # the province's CY 2023 SEF labels its total just "Total"
        elif B_SURPLUS.match(up):
            kind = "surplus"
        else:
            kind = "line"
            if B_HEAD_CONT.match(up) and spending:  # "Continuing Appropriations (Capital Outlay)" with amounts
                self.section = "continuing"
        if self.section == "after" and kind != "total":
            return  # the surplus and its details, below the fund's total
        if kind == "surplus":
            self.section = "after"
            return
        read, cells = self.place(vals, g)
        self.st.rows.append(BudgetRow(self.fund, self.section, kind, label, cells, read))
        if kind == "total":
            self.section = "after"
        elif kind == "total_revenue":
            self.section = "sources"  # "Add: Continuing Appropriation", "Total Sources" (Kalilangan)

    def place(self, vals: list[str], g: list[str]) -> tuple[str, dict[str, str]]:
        """Put a row's amounts in their columns. The headings' grid and the cells' grid don't
        always line up, so the reading whose differences agree with its amounts is taken:
        the amounts in order when there is one per column, else by the column under each
        cell, else in order with an empty column's dash skipped (the province's CY 2024 SEF)."""
        n, other = len(self.order), "other_year" in self.cols
        tries: list[tuple[str, dict[str, str]]] = []
        if n and len(vals) == n and not other:
            tries.append(("in order", dict(zip(self.order, vals))))
        by_col, stray = self.by_column(g)
        if not stray:
            tries.append(("by column" + (", one cell across columns" if by_col.pop("_merged", "") else ""), by_col))
        if n and len(vals) > n and not other:
            dashes = [i for i, v in enumerate(vals) if v in ("-", "–", "—")]
            if len(dashes) >= len(vals) - n:
                for drop in itertools.combinations(dashes, len(vals) - n):
                    kept = [v for i, v in enumerate(vals) if i not in drop]
                    tries.append(("in order, an empty column skipped", dict(zip(self.order, kept))))
        for read, cells in tries:
            if budget_consistent(cells):
                return read, cells
        if n and 1 < len(vals) < n and not other:
            # Blank cells, and the cells don't sit under their headings: the placings whose
            # arithmetic works with the blanks as nil, if they all read the same (Pangantucan's
            # CY 2024 SEF Capital Outlay: 87,000.00 | 87,000.00 | - is original and difference).
            fits = [dict(zip([self.order[p] for p in pos], vals))
                    for pos in itertools.combinations(range(n), len(vals))]
            fits = [c for c in fits if budget_consistent(c, strict=True)]
            readings = {tuple(budget_amount(c.get(k, "")) for k in ("original", "final", "actual")) for c in fits}
            if len(readings) == 1:
                return "in order, blank columns placed by the row's arithmetic", fits[0]
            # A blank difference that isn't nil: Pangantucan CY 2025's General Fund leaves the
            # original-to-final difference blank on rows where the budget changed ("112,909,219.50
            # | 129,366,223.86 | | 120,341,183.68 | 9,025,040.18"). Every amount present, the other
            # difference agreeing, and only one way to place them.
            fits = [dict(zip([self.order[p] for p in pos], vals))
                    for pos in itertools.combinations(range(n), len(vals))]
            fits = [c for c in fits if all(k in c for k in ("original", "final", "actual"))
                    and budget_consistent(c) is True]
            readings = {tuple(budget_amount(c[k]) for k in ("original", "final", "actual")) for c in fits}
            # Not over a reading the row's arithmetic doesn't contradict (San Fernando CY 2022).
            uncontradicted = any(budget_consistent(c) is None for _, c in tries)
            if len(readings) == 1 and not uncontradicted:
                return "in order, a blank difference left blank, placed by the row's arithmetic", fits[0]
        if tries:
            return tries[0]  # COA's own arithmetic is off; the check says so
        return "can't place: " + ", ".join(stray), {k: v for k, v in by_col.items() if not k.startswith("_")}

    def by_column(self, g: list[str]) -> tuple[dict[str, str], list[str]]:
        """Each amount under the column its cell sits in. A cell spanning several columns
        (COA merges the budget cells when they are equal) counts for each budget or actual
        column it covers."""
        cells: dict[str, str] = {}
        stray = []
        j = 1
        while j < len(g):
            k = j
            while k + 1 < len(g) and g[k + 1] == g[j]:
                k += 1
            if is_budget_amount(g[j]):
                cols = list(dict.fromkeys(self.cols[m] for m in range(j, k + 1) if m < len(self.cols)))
                mine = [c for c in cols if c in BUDGET_COLUMNS]
                amounts = [c for c in mine if c in ("original", "final", "actual")]
                if len(amounts) > 1:
                    for c in amounts:
                        cells.setdefault(c, flat(g[j]))
                    cells["_merged"] = "yes"
                elif mine and mine[0] not in cells:
                    cells[mine[0]] = flat(g[j])
                elif "other_year" not in cols:
                    stray.append(flat(g[j]))
            j = k + 1
        return cells, stray


def emf_lines(data: bytes) -> list[list[str]]:
    """The text an EMF picture draws (its EMR_EXTTEXTOUTW records), as lines of cells:
    grouped by height on the page, then left to right."""
    pos, items = 0, []
    while pos + 8 <= len(data):
        rtype, size = struct.unpack_from("<II", data, pos)
        if size < 8:
            break
        if rtype in (83, 84):  # EMR_EXTTEXTOUTA, EMR_EXTTEXTOUTW
            x, y = struct.unpack_from("<ii", data, pos + 36)
            nchars, offset = struct.unpack_from("<II", data, pos + 44)
            raw = data[pos + offset:pos + offset + (nchars * 2 if rtype == 84 else nchars)]
            items.append((y, x, raw.decode("utf-16-le" if rtype == 84 else "latin-1", errors="replace")))
        pos += size
    lines: dict[int, list[tuple[int, str]]] = {}
    for y, x, t in items:
        lines.setdefault(round(y / 6), []).append((x, t))
    return [[t.strip() for _, t in sorted(v) if t.strip()] for _, v in sorted(lines.items())]


def budget_statement(rep: Report) -> BudgetStatement | None:
    """The statement in Part I: from its title to the notes. Sumilao's CY 2022 and 2023
    statements are pictures; their text is read from the picture."""
    blocks = rep.blocks
    toc = next((i for i, b in enumerate(blocks) if isinstance(b, str) and re.match(r"^TABLE OF CONTENTS\b", b, re.I)), None)
    part1 = next((i for i, b in enumerate(blocks) if toc is not None and i > toc and isinstance(b, str)
                  and b.startswith("INDEPENDENT AUDITOR")), None)
    start = None
    for i in range(part1 or 0, len(blocks) if part1 is not None else 0):
        b = blocks[i]
        if isinstance(b, str):
            if BUDGET_TITLE.search(b) and len(b) < 200 and not b.lower().startswith("note"):
                start = i
                break
        # The title in a short row, not named in a letter's prose (Kibawe CY 2025's Statement of
        # Management Responsibility is a table).
        elif (BUDGET_TITLE.search(" ".join(t for t in (" ".join(r) for r in b.rows[:8]) if len(t) < 400))
              and not re.search(r"reconciliation", b.text(2), re.I)):
            start = i
            break
    if start is None:
        return budget_picture(rep)
    rd = BudgetReader(rep.year, "")
    for j in range(start, min(start + 400, len(blocks))):
        b = blocks[j]
        if isinstance(b, str):
            t = flat(b)
            if j > start and len(t) < 120 and BUDGET_STOP.match(t):
                break
            rd.text(t)
        else:
            if j > start and BUDGET_STOP.match(flat(b.text(2))):
                break
            rd.st.where = rd.st.where or f"Word table {b.index}"
            rd.table(b)
    return rd.st


def budget_picture(rep: Report) -> BudgetStatement | None:
    z = zipfile.ZipFile(rep.path)
    for name in sorted(n for n in z.namelist() if n.lower().endswith(".emf")):
        lines = emf_lines(z.read(name))
        if not any(BUDGET_TITLE.search(" ".join(line)) for line in lines[:12]):
            continue
        rd = BudgetReader(rep.year, f"picture {name}")
        rd.set_columns([None] + BUDGET_COLUMNS)
        for line in lines:
            if not line:
                continue
            label = line[0] if not is_budget_amount(line[0]) else ""
            vals = line[1:] if label else line
            if budget_fund(" ".join(line)) and not vals:
                rd.text(" ".join(line))
            else:
                rd.row([label] + vals, [label] + vals)
        return rd.st
    return None


def budget_sum(rows: list[BudgetRow], col: str) -> Decimal | None:
    vals = [budget_amount(r.cells.get(col, "")) for r in rows]
    return None if any(v is None for v in vals) else sum(vals, Decimal(0))


def budget_funds(st: BudgetStatement) -> list[dict]:
    """One record per fund: the final budget for the current year and its obligations, the
    other figures as printed, and how the current-year figures were found."""
    out = []
    for fund in dict.fromkeys(r.fund for r in st.rows):
        rows = [r for r in st.rows if r.fund == fund]
        last = lambda kind: next((r for r in reversed(rows) if r.kind == kind), None)
        cur, cont, tot = last("total_current"), last("total_continuing"), last("total")
        lines = [r for r in rows if r.kind == "line" and r.section in ("current", "expenditures")]
        clines = [r for r in rows if r.kind == "line" and r.section == "continuing"]
        nil = lambda rs: all(budget_amount(r.cells.get(c, "")) == 0 for r in rs for c in ("original", "final", "actual"))
        no_continuing = nil(clines) and (cont is None or nil([cont]))
        rec: dict = {"fund": fund or "General Fund", "fund_as_printed": st.funds.get(fund, ""), "rows": rows,
                     "lines": [], "cur_lines": lines, "notes": []}
        if fund == "General Fund and Special Education Fund":
            rec["notes"].append("COA gives the General Fund and the Special Education Fund together, in one "
                                "statement.")
        elif fund == "Consolidated":
            rec["notes"].append("COA gives one consolidated statement for the General Fund and the Special "
                                "Education Fund together.")
        if not fund:
            rec["notes"].append("COA's statement doesn't name the fund; it is the one before the Special "
                                "Education Fund's." if any(r.fund == "Special Education Fund" for r in st.rows)
                                else "COA's statement doesn't name the fund.")
        if cur is not None:
            rec["current_from"] = "COA's row"
            final, actual = budget_amount(cur.cells.get("final", "")), budget_amount(cur.cells.get("actual", ""))
        elif tot is not None and no_continuing:
            rec["current_from"] = "COA's total"
            final, actual = budget_amount(tot.cells.get("final", "")), budget_amount(tot.cells.get("actual", ""))
            rec["notes"].append(f"COA prints no subtotal for current appropriations and lists no continuing "
                                f"appropriations, so its {tot.label} is the current year's.")
        elif lines:
            rec["current_from"] = f"our sum of {len(lines)} rows"
            rec["lines"] = lines
            final, actual = budget_sum(lines, "final"), budget_sum(lines, "actual")
            head = "Current Appropriations" if any(r.section == "current" for r in lines) else "Expenditures"
            rec["notes"].append(f"COA prints no total for current appropriations; this is our sum of its "
                                f"{len(lines)} rows under {head}.")
        else:
            rec["current_from"], final, actual = "", None, None
        rec["final"], rec["actual"] = final, actual
        rec["current"], rec["continuing"], rec["total"] = cur, cont, tot
        rec["no_continuing"] = no_continuing
        rec["clines"] = clines
        if cur is not None and cur.cells.get("final", "").strip() in ("-", "–", "—"):
            rec["notes"].append(f"COA prints the final budget as a dash (the original budget is "
                                f"{cur.cells.get('original', '')}), so the share obligated can't be worked out.")
        elif final and actual is not None:
            if actual == final:
                rec["notes"].append(OBLIGATIONS_EQUAL_NOTE)
            elif actual > final:
                rec["notes"].append(f"Obligations are larger than the final budget, by {actual - final:,.2f}.")
        out.append(rec)
    return out


OBLIGATIONS_EQUAL_NOTE = "Obligations equal the final budget to the centavo."


def share_obligated(final: Decimal | None, actual: Decimal | None) -> str:
    """Obligations as a share of the final budget: our arithmetic, a percentage to one decimal."""
    if not final or actual is None:
        return ""
    return str((actual * 100 / final).quantize(Decimal("0.1"), rounding="ROUND_HALF_UP"))


def budget_checks(funds: list[dict]) -> list[tuple[str, bool | None, str]]:
    checks = []
    bad, tested = [], 0
    for f in funds:
        for r in f["rows"]:
            if r.kind == "total_revenue" or r.section not in ("current", "expenditures", "continuing", "after"):
                continue
            ok = budget_consistent(r.cells)
            if ok is None:
                continue
            tested += 1
            if not ok:
                c = r.cells
                bad.append(f"{f['fund']} {r.label}: " + ", ".join(f"{k} {c[k]}" for k in BUDGET_COLUMNS if k in c))
    checks.append(("budget: rows add across", None if not tested else not bad,
                   "; ".join(bad) or f"{tested} rows: final - original and final - actual give the printed differences"))
    bad, tested = [], []
    for f in funds:
        cur, cont, tot = f["current"], f["continuing"], f["total"]
        if tot is None:
            continue
        for col in ("original", "final", "actual"):
            # COA's current subtotal, else its rows under current appropriations (where its
            # total is taken as the current year's, they should add to it).
            a = budget_amount(cur.cells.get(col, "")) if cur else budget_sum(f["cur_lines"], col)
            b = budget_amount(cont.cells.get(col, "")) if cont else budget_sum(f["clines"], col)
            c = budget_amount(tot.cells.get(col, ""))
            if cur is None and not f["cur_lines"]:
                continue
            if None in (a, b, c):
                bad.append(f"{f['fund']} {col}: an amount can't be read")
                continue
            tested.append(f["fund"])
            if a + b != c:
                bad.append(f"{f['fund']} {col}: {money(a)} + {money(b)} = {money(a + b)}, {tot.label} printed "
                           f"{tot.cells.get(col, 'blank')}")
    checks.append(("budget: current + continuing = total", None if not tested and not bad else not bad,
                   "; ".join(bad) or (", ".join(dict.fromkeys(tested)) if tested else
                                      "no total beside the current appropriations")))
    over = [f"{f['fund']}: obligations {money(f['actual'])}, final budget {money(f['final'])}"
            for f in funds if f["final"] is not None and f["actual"] is not None and f["actual"] > f["final"]]
    checks.append(("budget: obligations within the final budget", not over if any(f["final"] for f in funds) else None,
                   "; ".join(over) or ", ".join(f"{f['fund']} {share_obligated(f['final'], f['actual'])}%"
                                                for f in funds if f["final"])))
    return checks


# The headings of the executive summary's sections after its financial highlights (the scope
# of the audit comes before them in some reports, after in others).
SUMMARY_AFTER_HIGHLIGHTS = re.compile(
    r"^(?:[A-Z]|[IVX]+)?[.)]?\s*(?:(?:the\s+)?(?:independent\s+)?auditor['’]?s?\s+(?:report|opinion)"
    r"|significant\s+(?:audit\s+)?(?:observations|findings)|summary\s+of\s+(?:significant\s+)?(?:audit\s+)?"
    r"(?:observations|findings))", re.I)


def summary_budget(rep: Report) -> tuple[set[Decimal], bool, dict[str, Decimal], str]:
    """What the executive summary's highlights say of appropriations: every amount where they
    speak of them, whether they give obligations, continuing appropriations by fund where a
    table of them is headed "Continuing", and the text (to see which funds it names)."""
    amounts, obligations, continuing, texts = set(), False, {}, []
    start = next((i for i, b in enumerate(rep.blocks) if isinstance(b, str) and len(b) < 60
                  and re.match(r"^EXECUTIVE\s+SUMMARY\b", b, re.I)), 0)
    for b in rep.blocks[start:]:
        if isinstance(b, str):
            if re.match(r"^TABLE OF CONTENTS\b", b, re.I) or (len(b) < 120 and SUMMARY_AFTER_HIGHLIGHTS.match(b)):
                break
            t = b
        else:
            t = b.text()
        if not re.search(r"appropriat", t, re.I):
            continue
        texts.append(t)
        amounts |= {v for v in (nd_amount(a) for a in FULL_AMOUNT.findall(t)) if v}
        obligations |= bool(re.search(r"obligat", t, re.I))
        if isinstance(b, Table) and re.search(r"\bcontinuing\b", b.text(2), re.I) and not re.search(
                r"\bcurrent\b", b.text(2), re.I):
            for r in b.rows:
                f = budget_fund(printed_label(r))
                amt = next((nd_amount(c) for c in r[1:] if FULL_AMOUNT.fullmatch(c.strip())), None)
                if f and amt:
                    continuing[f] = amt
    return amounts, obligations, continuing, " ".join(texts)


FUND_WORDS = {"General Fund": r"general\s+fund|\bGF\b", "Special Education Fund": r"special\s+education|\bSEF\b"}


SAAOB_TITLE = re.compile(r"appropriations?,?\s+allotments?|\bSAAOB\b|status\s+of\s+appropriation|"
                         r"statement\s+of\s+appropriation", re.I)
# The rows of an appendix that can carry a fund's whole current-year appropriation, best first.
SAAOB_TOTALS = [re.compile(r"^grand\s+total\b", re.I),
                re.compile(r"^(?:total\s+current\s+appropriations?|current\s+year\s+appropriations?|"
                           r"current\s+appropriations?|a\.?)(?:\s|$)", re.I),
                re.compile(r"^total\b", re.I)]
SAAOB_SECTION = re.compile(r"^(?:[A-Z][.)]\s*)?(continuing|current)(?:\s+(?:year|legislative|school\s+board))?"
                           r"\s+appropriations?\b", re.I)


def saaob_fund(text: str) -> str | None:
    g = re.search(r"general\s+fund|\(GF\)", text, re.I)
    s = re.search(r"special\s+education\s+fund|\bSEF\b|school\s+board", text, re.I)
    return "both" if g and s else "General Fund" if g else "Special Education Fund" if s else None


def appendix_obligations(rep: Report) -> list[dict]:
    """The total rows of the report's Status of Appropriations, Allotments and Obligations
    (an appendix in most reports that have one): any table after Part I starts whose columns
    are headed appropriation, allotment and obligation. The fund comes from the heading above
    the table, or a row inside it that names one; tables or parts headed continuing
    appropriations are left out."""
    blocks = rep.blocks
    toc = next((i for i, b in enumerate(blocks) if isinstance(b, str) and re.match(r"^TABLE OF CONTENTS\b", b, re.I)), None)
    part1 = next((i for i, b in enumerate(blocks) if toc is not None and i > toc and isinstance(b, str)
                  and b.startswith("INDEPENDENT AUDITOR")), 0)
    out = []
    for k in range(part1, len(blocks)):
        if not isinstance(blocks[k], Table):
            continue
        for t in [blocks[k]] + blocks[k].nested:
            grid = t.grid or t.rows
            nhead = next((i for i, row in enumerate(grid)
                          if any(budget_amount(c) not in (None, Decimal(0)) for c in row if c.strip())), len(grid))
            width = max((len(r) for r in grid), default=0)
            labs = [" ".join(dict.fromkeys(h[i].strip() for h in grid[:nhead] if i < len(h) and h[i].strip())).lower()
                    for i in range(width)]
            if not any("allot" in lab for lab in labs):
                continue
            app = [i for i, lab in enumerate(labs) if "appropriation" in lab and not re.search(
                r"obligation|balance|unobligated|unexpended|function|program|project|particular", lab)]
            obl = [i for i, lab in enumerate(labs) if re.search(r"\bobligation", lab)
                   and not re.search(r"appropriation|unobligated|balance", lab)]
            if not app or not obl:
                continue
            # The title just above the table (not its column headings, which also read
            # "Appropriations Allotment"), else the table's own heading rows.
            above = " ".join(b for b in blocks[max(0, k - 8):k] if isinstance(b, str))[-500:]
            titles = list(SAAOB_TITLE.finditer(above))
            heading = above[titles[-1].start():] if titles else t.text(nhead)
            fund = saaob_fund(heading) or saaob_fund(t.text(nhead))
            continuing = bool(re.search(r"continuing", heading, re.I) and not re.search(r"current", heading, re.I))
            for row in grid[nhead:]:
                texts = [c.strip() for c in row if c.strip()]
                if texts and all(budget_amount(c) is None for c in texts):  # a heading row inside the table
                    line = flat(" ".join(texts))
                    if budget_fund(line) in ("General Fund", "Special Education Fund"):
                        fund = budget_fund(line)
                    section = SAAOB_SECTION.match(line)
                    if section and len(line) < 80:  # "B. Continuing Appropriations", not a line item
                        continuing = section.group(1).lower() == "continuing"
                    continue
                label = next((c for c in texts if budget_amount(c) is None), "")
                rank = next((n for n, rx in enumerate(SAAOB_TOTALS) if rx.match(label)), None)
                if rank is None or continuing:
                    continue
                for ai in app:
                    a = budget_amount(row[ai]) if ai < len(row) else None
                    oi = next((o for o in obl if o > ai), None)
                    if a and oi is not None and oi < len(row) and budget_amount(row[oi]) is not None:
                        out.append({"fund": fund, "appropriation": a, "obligation": budget_amount(row[oi]),
                                    "label": label, "rank": rank, "table": t.index})
                        break
    return out


def appendix_check(f: dict, rows: list[dict]) -> tuple[bool | None, str]:
    """Whether the appendix's total row with the same current-year appropriation gives the same
    obligations as the statement."""
    if f["final"] is None or f["actual"] is None:
        return None, f"{f['fund']}: no current-year figures"
    mine = [r for r in rows if r["appropriation"] == f["final"]
            and (r["fund"] in (None, "both") or r["fund"] == f["fund"]
                 or f["fund"] not in ("General Fund", "Special Education Fund"))]
    if not mine:
        return None, f"{f['fund']}: no appendix total with a final budget of {f['final']:,.2f}"
    best = min(r["rank"] for r in mine)
    gives = list(dict.fromkeys(r["obligation"] for r in mine if r["rank"] == best))
    where = "; ".join(dict.fromkeys(f"Word table {r['table']}, {r['label']!r}" for r in mine if r["rank"] == best))
    ok = gives == [f["actual"]]
    return ok, (f"{f['fund']}: statement {f['actual']:,.2f}, appendix "
                + " / ".join(f"{g:,.2f}" for g in gives) + f" ({where})")


def budget_summary_check(funds: list[dict], said: tuple) -> tuple[bool | None, str]:
    """Whether the executive summary's highlights give the same current-year figures: each
    fund's, or the funds' together, or with continuing appropriations included (then the
    statement's total), saying which. A fund the highlights don't name isn't held against them."""
    amounts, obligations, _, text = said
    if not amounts:
        return None, "the executive summary doesn't give appropriations"
    found, missing, unnamed = [], [], []
    for what, col, key in (("final budget", "final", "final"), ("obligations", "actual", "actual")):
        if col == "actual" and not obligations:
            continue
        cur = {f["fund"]: f[key] for f in funds if f[key]}
        tot = {f["fund"]: budget_amount(f["total"].cells.get(col, "")) for f in funds if f["total"] is not None}
        together = sum(cur.values(), Decimal(0)) if len(cur) > 1 else None
        totals = sum((v for v in tot.values() if v), Decimal(0)) if len(tot) > 1 else None
        for fund, v in cur.items():
            pair = next(((a, b) for a in amounts for b in amounts if a < b and a + b == v), None)
            if v in amounts:
                found.append(f"{fund} {what} {money(v)}")
            elif pair:
                found.append(f"{fund} {what} {money(v)} (the summary's {money(pair[0])} and {money(pair[1])})")
            elif together in amounts:
                found.append(f"{fund} {what}, with the other funds: {money(together)}")
            elif tot.get(fund) and tot[fund] in amounts:
                found.append(f"{fund} {what} with continuing appropriations: {money(tot[fund])}")
            elif totals in amounts:
                found.append(f"{fund} {what} with continuing appropriations and the other funds: {money(totals)}")
            elif fund in FUND_WORDS and not re.search(FUND_WORDS[fund], text, re.I):
                unnamed.append(fund)
            else:
                missing.append(f"{fund} {what} {money(v)}")
    if missing:
        near = sorted(amounts, reverse=True)[:6]
        return False, f"not in the summary: {'; '.join(missing)}. It gives {', '.join(map(money, near))}"
    if not found:
        return None, "the highlights name no fund's appropriations"
    return True, ("; ".join(dict.fromkeys(found)) + ("" if obligations else " (the summary gives appropriations only)")
                  + "".join(f"; the summary doesn't give the {u}" for u in dict.fromkeys(unnamed)))


BUDGET_FIELDS = ["fund", "fund_as_printed", "final_appropriations", "obligations", "share_obligated", "current_from",
                 "current_label", "current_original", "current_final", "current_obligations", "continuing_label",
                 "continuing_original", "continuing_final", "continuing_obligations", "total_label", "total_original",
                 "total_final", "total_obligations", "note", "correction_note"]
BUDGET_TABLE_FIELDS = ["fund", "section", "row", "label_as_printed", "original", "final", "diff_original_final",
                       "actual", "diff_final_actual", "read"]


def budget_record(f: dict, summary_continuing: dict[str, Decimal]) -> dict:
    """The row of appropriations.csv for one fund."""
    cur, cont, tot = f["current"], f["continuing"], f["total"]
    took = cur if cur is not None else tot if f["current_from"] == "COA's total" else None
    get = lambda r, c: r.cells.get(c, "") if r is not None else ""
    notes = list(f["notes"])
    if f["no_continuing"]:
        named = {k: v for k, v in summary_continuing.items() if k == f["fund"] or f["fund"] in (
            "Consolidated", "General Fund and Special Education Fund")}
        if named:
            notes.append("The statement lists no continuing appropriations; the executive summary gives "
                         + " and ".join(f"{v:,.2f} for the {k}" for k, v in named.items()) + ".")
    return {"fund": f["fund"], "fund_as_printed": f["fund_as_printed"],
            "final_appropriations": money(f["final"]) if f["final"] is not None else "",
            "obligations": money(f["actual"]) if f["actual"] is not None else "",
            "share_obligated": share_obligated(f["final"], f["actual"]), "current_from": f["current_from"],
            "current_label": took.label if took is not None else "",
            "current_original": get(took, "original"), "current_final": get(took, "final"),
            "current_obligations": get(took, "actual"),
            "continuing_label": cont.label if cont is not None else "", "continuing_original": get(cont, "original"),
            "continuing_final": get(cont, "final"), "continuing_obligations": get(cont, "actual"),
            "total_label": tot.label if tot is not None else "", "total_original": get(tot, "original"),
            "total_final": get(tot, "final"), "total_obligations": get(tot, "actual"), "note": " ".join(notes)}


def budget_table_rows(f: dict) -> list[dict]:
    """COA's rows of appropriations for one fund, for appropriation-tables.csv."""
    out = []
    for r in f["rows"]:
        if r.kind == "total_revenue" or r.section in ("revenue", "sources", ""):
            continue
        out.append({"fund": f["fund"], "section": {"expenditures": "current"}.get(r.section, r.section),
                    "row": "line" if r.kind == "line" else BUDGET_KINDS.get(r.kind, r.kind),
                    "label_as_printed": r.label, "read": r.read} | {k: r.cells.get(k, "") for k in BUDGET_COLUMNS})
    return out


def saved_pdf_pages(path: Path) -> dict[int, str]:
    """The text scripts/pdf_pages.py saved for a PDF, page by page."""
    split = re.split(r"^=== PDF page (\d+) ===$", path.read_text(encoding="utf-8"), flags=re.M)
    return {int(split[k]): split[k + 1] for k in range(1, len(split), 2)}


def summary_pdf_budget(year: str, lgu: str) -> tuple:
    """summary_budget() for a report that is a PDF: from the text of COA's Executive Summary PDF."""
    saved = sorted((RAW / year / lgu).glob("*Executive-Summary*.pages.txt"))
    pages = [t for t in saved_pdf_pages(saved[0]).values() if re.search(r"appropriat", t, re.I)] if saved else []
    text = " ".join(pages)
    amounts = {v for v in (nd_amount(a) for a in FULL_AMOUNT.findall(text)) if v}
    return amounts, bool(re.search(r"obligat", text, re.I)), {}, text


def report_pdf_shows(year: str, lgu: str, rows: list[dict]) -> tuple[bool, str]:
    """Whether every amount entered by hand is on the report PDF's page cited for its row."""
    saved = sorted((RAW / year / lgu / "extracted").glob("**/*.pages.txt"))
    if not saved:
        return False, "the report PDF's text isn't saved; run scripts/pdf_pages.py"
    pages = {n: re.sub(r"\s+", "", t) for n, t in saved_pdf_pages(saved[0]).items()}
    missing = [f"{t['label_as_printed']} {t[k]} (p. {t['pdf_page']})" for t in rows for k in BUDGET_COLUMNS
               if FULL_AMOUNT.search(t[k]) and t[k].strip("()") not in pages.get(int(t["pdf_page"]), "")]
    n = sum(1 for t in rows for k in BUDGET_COLUMNS if FULL_AMOUNT.search(t[k]))
    return not missing, f"{saved[0].name}: " + (f"missing {'; '.join(missing)}" if missing else
                                                 f"all {n} amounts on the pages cited")


def budget_from_rows(rows: list[dict]) -> BudgetStatement:
    """A statement rebuilt from appropriation-tables.csv rows (Valencia CY 2023, read by hand)."""
    st = BudgetStatement("PDF")
    kinds = {v: k for k, v in BUDGET_KINDS.items()}
    for t in rows:
        kind = kinds.get(t["row"], "line")
        section = "after" if kind == "total" else t["section"]
        st.funds.setdefault(t["fund"], t["fund"])
        st.rows.append(BudgetRow(t["fund"], section, kind, t["label_as_printed"],
                                 {k: t[k] for k in BUDGET_COLUMNS if t[k]}, t.get("read", "")))
    return st


# ---------------------------------------------------------------------------- output

def manifests() -> tuple[dict, dict]:
    files, contents = {}, {}
    for year_csv in sorted((REPO / "data" / "sources").glob("coa-aar-*-files.csv")):
        with year_csv.open(encoding="utf8") as f:
            for r in csv.DictReader(f):
                files[(r["year"], r["lgu_slug"], r["document"])] = r
    for year_csv in sorted((REPO / "data" / "sources").glob("coa-aar-*-contents.csv")):
        with year_csv.open(encoding="utf8") as f:
            for r in csv.DictReader(f):
                contents[(r["year"], r["lgu_slug"], Path(r["path_in_zip"]).name)] = r
    return files, contents


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf8") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    files, contents = manifests()
    verdict_rows, figure_rows, prior_rows, check_rows = [], [], [], []
    finding_rows, count_rows, pdf_counts = [], [], []
    nd_rows, nd_table_rows, nd_pdf_tables, nd_meta = [], [], [], {}
    budget_rows, budget_table, budget_pdf_tables = [], [], []
    errata = read_csv(OUT / "errata.csv")
    corrections = read_csv(OUT / "corrections.csv")
    appendix_notes = read_csv(OUT / "appendix-notes.csv")
    appendix_read: dict[tuple[str, str, str], str] = {}  # (year, lgu, fund) -> the appendix check's detail
    # The paragraphs of each report with a corrected obligations figure, to find its source in.
    budget_sources = {(c["year"], c["lgu_slug"]): [] for c in corrections if c["figure"].startswith("obligations_")}

    def check(year, lgu, name, ok, detail=""):
        result = "n/a" if ok is None else "pass" if ok else "FAIL"
        check_rows.append({"year": year, "lgu_slug": lgu, "check": name, "result": result, "detail": detail})

    for year, lgu, path in find_reports():
        rep = read_report(year, lgu, path)
        if (year, lgu) in budget_sources:
            budget_sources[(year, lgu)] = rep.paragraphs
        src = files.get((year, lgu, "annual_audit_report"), {})
        inzip = contents.get((year, lgu, path.name), {})
        base = {"year": year, "lgu_slug": lgu, "lgu": src.get("lgu", ""),
                "report_url": src.get("coa_file_page", ""), "file_in_zip": inzip.get("path_in_zip", path.name),
                "file_sha256": inzip.get("sha256", "")}
        pages = toc_pages(rep)

        v = verdict(rep)
        verdict_rows.append(base | v | {"part": "Part I", "item": "Independent Auditor's Report",
                                        "toc_pages": pages.get("Independent Auditor's Report", "")})
        check(year, lgu, "verdict found", bool(v["verdict"]), v["basis_heading"])
        check(year, lgu, "opinion sentence found", bool(v["opinion_quote"]))
        said = stated_verdicts(rep)
        clash = {s for s in said if s not in ("modified", v["verdict"])}
        if v["verdict"] == "qualified":
            clash -= {"qualified"}
        check(year, lgu, "summary agrees with auditor's report", not clash,
              f"auditor's report: {v['verdict']}; elsewhere: {', '.join(sorted(said)) or 'nothing stated'}")
        check(year, lgu, "table of contents pages found",
              all(k in pages for k in ("Independent Auditor's Report", "Statement of Financial Position",
                                       "Statement of Financial Performance")), str(pages))

        figs, notes, extras = figures(rep)
        for n in notes:
            check(year, lgu, "statement read", False, n)
        by = {f["figure"]: f for f in figs}
        for f in figs:
            figure_rows.append(base | f | {"part": "Part I", "item": f["statement"],
                                           "toc_pages": pages.get(f["statement"], "")})
        if {"total_assets", "total_liabilities", "net_assets_equity"} <= by.keys():
            a, l, e = (Decimal(by[k]["amount"]) for k in ("total_assets", "total_liabilities", "net_assets_equity"))
            check(year, lgu, "assets = liabilities + equity", a == l + e, f"{a} vs {l} + {e} = {l + e}")
        for k, sv in summary_figures(rep).items():
            if k not in by:
                continue
            fv = Decimal(by[k]["amount"])
            ok, detail = same_amount(sv, fv), f"summary {sv[0]} vs statement {by[k]['amount_as_printed']}"
            cur = extras.get("surplus_current_operation")
            if not ok and k == "surplus_deficit" and cur is not None and same_amount(sv, cur):
                ok, detail = True, (f"summary {sv[0]} is the statement's surplus from current operation; "
                                    f"surplus for the period is {by[k]['amount_as_printed']}")
            check(year, lgu, f"executive summary matches statement: {k}", ok, detail)

        prow, pchecks = prior_recommendations(rep, errata)
        prior_rows.append(base | prow)
        for name, ok, detail in pchecks:
            check(year, lgu, name, ok, detail)

        found, after = findings(rep)
        p2pages = toc_part2_pages(rep)
        where = {"part": "Part II", "toc_pages": p2pages}
        for f in found:
            finding_rows.append(base | where | {"number": f.number, "numbered": f.numbered, "observation": f.text,
                                                "item": f"Observation {f.number}"})
        count_rows.append(base | where | count_row([f.number for f in found], after) | {"item": FINDINGS_ITEM})
        for name, ok, detail in finding_checks(rep, found, after, p2pages):
            check(year, lgu, name, ok, detail)

        # Appropriations and obligations: Part I's Statement of Comparison of Budget and Actual
        # Amounts, each fund as COA prints it.
        bwhere = {"part": "Part I", "item": BUDGET_ITEM, "toc_pages": pages.get(BUDGET_ITEM, "")}
        check(year, lgu, "budget: page in the table of contents", bool(bwhere["toc_pages"]),
              bwhere["toc_pages"] or "not found")
        st = budget_statement(rep)
        if st is None or not st.rows:
            check(year, lgu, "budget: statement found", False, "no Statement of Comparison of Budget and Actual Amounts")
            budget_rows.append(base | bwhere | {"note": "The statement wasn't found."})
        else:
            bfunds = budget_funds(st)
            check(year, lgu, "budget: statement found", True,
                  f"{st.where}: " + ", ".join(f["fund"] + (f" (printed {f['fund_as_printed']!r})"
                                                           if f["fund_as_printed"].upper() != f["fund"].upper() else "")
                                              for f in bfunds))
            gaps = [f["fund"] for f in bfunds if f["final"] is None or f["actual"] is None]
            check(year, lgu, "budget: current-year figures found", not gaps,
                  "; ".join(f"{f['fund']}: {f['current_from'] or 'nothing'}" for f in bfunds))
            said = summary_budget(rep)
            for f in bfunds:
                budget_rows.append(base | bwhere | budget_record(f, said[2]))
                budget_table.extend(base | bwhere | t for t in budget_table_rows(f))
            for name, ok, detail in budget_checks(bfunds):
                check(year, lgu, name, ok, detail)
            check(year, lgu, "budget: executive summary agrees", *budget_summary_check(bfunds, said))
            arows = appendix_obligations(rep)
            for f in bfunds:
                ok, detail = appendix_check(f, arows)
                appendix_read[(year, lgu, f["fund"])] = detail
                check(year, lgu, "budget: appendix obligations agree", ok, detail)

        # Unsettled disallowances: from Part II or III where the report has it there, else the
        # executive summary, cited by the page of COA's executive summary PDF.
        # A section whose year-end balances can't all be read exactly comes after one whose can:
        # Pangantucan CY 2025's Part II rounds them ("0.333 million"), its executive summary gives
        # 332,940.58.
        secs = nd_sections(rep)
        has = lambda s: bool(s.rows) or bool(s.said)
        exact = lambda s: bool(s.said) or all(nd_amount(r.cells["ending"]) is not None for r in s.rows
                                              if r.notice in NOTICES and "ending" in r.cells)
        src = (max(secs, key=lambda s: (has(s), exact(s), s.part != "Executive summary", bool(s.rows), s.block))
               if secs else None)
        if src is None:
            check(year, lgu, "disallowances: balance found", False, "no section on suspensions and disallowances")
            nd_rows.append(base | {"note": "No section on suspensions and disallowances found."})
            continue
        if src.part == "Executive summary":
            es = files.get((year, lgu, "executive_summary"), {})
            page, ok, detail = summary_pdf_page(year, lgu, src.heading, printed_amounts(src.rows, src.said))
            where = {"report_url": es.get("coa_file_page", ""), "file_in_zip": "", "file_sha256": es.get("sha256", ""),
                     "part": "Executive summary", "toc_pages": "", "pdf_page": page}
            check(year, lgu, "disallowances: executive summary PDF shows the same amounts", ok, detail)
        else:
            where = {"part": src.part, "toc_pages": nd_toc_page(rep, src)}
            check(year, lgu, "disallowances: executive summary PDF shows the same amounts", None,
                  f"taken from {src.part}")
        row = base | where | nd_shown(src)
        nd_rows.append(row)
        nd_meta[(year, lgu)] = {"has": has(src), "opening": nd_opening(src), "opens_nil_said": src.opens_nil_said}
        check(year, lgu, "disallowances: balance found", has(src),
              f"{src.part}: {src.heading}" + (f" ({src.note})" if src.note else "") if has(src)
              else f"COA gives no balance under {src.part}: {src.heading}")
        for r in src.rows:
            other = "; ".join(f"{k}: {r.cells[k] or 'blank'}" for k in ND_KINDS
                              if k in r.cells and k not in ("beginning", "issued", "settled", "ending"))
            nd_table_rows.append(base | where | {"fund": r.fund, "notice": r.notice, "label_as_printed": r.label,
                                                 "other_columns": other, "item": src.heading}
                                 | {k: r.cells.get(k, "") for k in ("beginning", "issued", "settled", "ending")})
        for name, ok, detail in nd_checks(src, src.rows):
            check(year, lgu, name, ok, detail)
        summ = [s for s in secs if s.part == "Executive summary" and has(s)]
        if src.part != "Executive summary" and summ:
            a = nd_shown(summ[-1])
            pairs = [(n, a[f"{n}s"], row[f"{n}s"]) for n in NOTICES if a[f"{n}s"] and row[f"{n}s"]]
            diffs = [f"{n}: summary {x}, {src.part} {y}" for n, x, y in pairs if Decimal(x) != Decimal(y)]
            check(year, lgu, "disallowances: executive summary agrees", not diffs,
                  "; ".join(diffs) or ", ".join(f"{n} {y}" for n, _, y in pairs))
        else:
            check(year, lgu, "disallowances: executive summary agrees", None,
                  "the executive summary is the source" if src.part == "Executive summary"
                  else "the executive summary doesn't give it")

    pdf_rows = OUT / "pdf-reports.csv"
    if pdf_rows.exists():
        for r in read_csv(pdf_rows):
            {"verdict": verdict_rows, "figure": figure_rows, "prior_recommendations": prior_rows,
             "finding": finding_rows, "finding_count": pdf_counts, "disallowances": nd_rows,
             "disallowance_row": nd_pdf_tables, "appropriations": budget_rows,
             "appropriation_row": budget_pdf_tables}[r["record"]].append(r)
        for year, lgu in dict.fromkeys((r["year"], r["lgu_slug"]) for r in budget_rows if r.get("record")):
            # Read by hand: the rows entered must give the figures entered, add up, agree with
            # the executive summary, and appear on the report PDF's pages cited.
            entered = [r for r in budget_rows if r.get("record") and (r["year"], r["lgu_slug"]) == (year, lgu)]
            mine = [t for t in budget_pdf_tables if (t["year"], t["lgu_slug"]) == (year, lgu)]
            budget_table.extend(mine)
            bfunds = budget_funds(budget_from_rows(mine))
            got = {f["fund"]: (money(f["final"]), money(f["actual"]), share_obligated(f["final"], f["actual"]),
                               f["current_from"]) for f in bfunds}
            same = all(got.get(r["fund"]) == (r["final_appropriations"], r["obligations"], r["share_obligated"],
                                              r["current_from"]) for r in entered) and len(got) == len(entered)
            check(year, lgu, "budget: statement found", True, "read by hand from PDF: "
                  + ", ".join(r["fund"] for r in entered))
            check(year, lgu, "budget: page in the table of contents", bool(entered[0]["toc_pages"]),
                  entered[0]["toc_pages"])
            check(year, lgu, "budget: current-year figures found", same,
                  "the rows entered give the figures entered" if same else f"the rows entered give {got}")
            for name, ok, detail in budget_checks(bfunds):
                check(year, lgu, name, ok, detail)
            check(year, lgu, "budget: executive summary agrees", *budget_summary_check(bfunds, summary_pdf_budget(year, lgu)))
            check(year, lgu, "budget: report PDF shows the same amounts", *report_pdf_shows(year, lgu, mine))
        for r in [r for r in nd_rows if r.get("record")]:
            # Read by hand: the table rows entered must give the figures entered, add up, and
            # appear on the executive summary PDF's page cited.
            year, lgu = r["year"], r["lgu_slug"]
            mine = [t for t in nd_pdf_tables if (t["year"], t["lgu_slug"]) == (year, lgu)]
            rows = [NDRow(t["fund"], t["notice"], t["label_as_printed"],
                          {k: t[k] for k in ("beginning", "issued", "settled", "ending")}) for t in mine]
            nd_table_rows.extend(mine)
            same = all((money(v) if v is not None else "") == r[f"{n}s"]
                       for n in NOTICES for v in [nd_value(rows, n, "ending")[0]])
            check(year, lgu, "disallowances: balance found", same,
                  f"{r['part']}: {r['item']} (read by hand from PDF; the rows entered give the same figures)" if same
                  else "the figures entered differ from the rows entered")
            for name, ok, detail in nd_checks(None, rows):
                check(year, lgu, name, ok, detail)
            page, ok, detail = summary_pdf_page(year, lgu, r["item"], printed_amounts(rows))
            check(year, lgu, "disallowances: executive summary PDF shows the same amounts",
                  ok and page == r["pdf_page"], f"{detail}; entered as p. {r['pdf_page']}")
            check(year, lgu, "disallowances: executive summary agrees", None, "the executive summary is the source")
            check(year, lgu, "disallowances: COA's sentence agrees with the table", None, "read by hand from PDF")
            nd_meta[(year, lgu)] = {"has": True, "opening": nd_opening(None, rows), "opens_nil_said": False}
        for c in pdf_counts:
            # Read by hand: the count is the finding rows entered, checked like the Word reports'.
            mine = [r for r in finding_rows if r.get("record") and (r["year"], r["lgu_slug"]) == (c["year"], c["lgu_slug"])]
            numbers = [int(r["number"]) for r in mine]
            after = [int(x) for x in re.findall(r"\d+", c["numbered_after_findings"])]
            after = list(range(after[0], after[-1] + 1)) if after else []
            count_rows.append(c | count_row(numbers, after))
            then = f"; then {c['numbered_after_findings']} on paragraphs without a recommendation" if after else ""
            check(c["year"], c["lgu_slug"], "findings found", bool(mine),
                  f"{len(mine)}, numbered {number_ranges(numbers)} (read by hand from PDF)")
            check(c["year"], c["lgu_slug"], "findings: COA's numbers run 1 to N",
                  numbers == list(range(1, len(numbers) + 1)), f"{number_ranges(numbers)}{then}")
            check(c["year"], c["lgu_slug"], "findings: Part II's pages in the table of contents", bool(c["toc_pages"]),
                  c["toc_pages"] or "not found")
            check(c["year"], c["lgu_slug"], "findings: numbers match Word's", None, "a PDF: the numbers are printed")
        for r in [r for r in prior_rows if r.get("record")]:
            # Read by hand: check the numbers entered against COA's sentence, quoted beside them.
            st = parse_statement(r["quote"])
            counts = {k: int(r[k]) for k in STATUSES + ["reiterated"] if r.get(k)}
            same = st is not None and st.total.value == int(r["total"]) and all(
                st.counts.get(k) and st.counts[k].value == v for k, v in counts.items())
            check(r["year"], r["lgu_slug"], "past recommendations found", same,
                  f"{r['stated_in']} (read by hand from PDF; the quote gives the same figures)" if same
                  else "the figures entered differ from the quote")
            if st:
                for name, ok, detail in statement_checks(st, int(r["total"]), counts):
                    check(r["year"], r["lgu_slug"], name, ok, detail)
        for (year, lgu) in {(r["year"], r["lgu_slug"]) for r in figure_rows if r.get("record")}:
            by = {r["figure"]: Decimal(r["amount"]) for r in figure_rows
                  if (r["year"], r["lgu_slug"]) == (year, lgu)}
            a, l, e = by["total_assets"], by["total_liabilities"], by["net_assets_equity"]
            check(year, lgu, "assets = liabilities + equity", a == l + e, f"{a} vs {l} + {e} = {l + e} (read by hand from PDF)")

    # Corrections: a printed figure that the same report shows is wrong. The printed text
    # stays in amount_as_printed; amount takes the corrected figure and
    # correction_note says why. The checks above stay on the printed figures, so COA's
    # error remains visible in checks.csv.
    for c in corrections:
        if c["figure"].startswith("obligations_"):
            # Obligations the statement prints wrong, as the same report's Status of
            # Appropriations, Allotments and Obligations shows (Kitaotao CY 2024 prints the final
            # budget again in the Actual column). The printed text stays in current_obligations;
            # obligations and share_obligated take the corrected figure, and the corrected figure
            # must sit in the report beside the same final budget.
            fund = c["figure"].removeprefix("obligations_")
            row = next((r for r in budget_rows if (r["year"], r["lgu_slug"]) == (c["year"], c["lgu_slug"])
                        and re.sub(r"\W+", "_", r.get("fund", "").lower()) == fund), None)
            if row is None or row["current_obligations"] != c["printed"]:
                raise SystemExit(f"correction no longer matches the report: {c}")
            final, fixed = Decimal(row["final_appropriations"]), Decimal(c["corrected_amount"])
            row["obligations"], row["share_obligated"] = money(fixed), share_obligated(final, fixed)
            row["note"] = " ".join(row["note"].replace(OBLIGATIONS_EQUAL_NOTE, "").split())
            row["correction_note"] = c["note"]
            paras = [p.strip() for p in budget_sources[(c["year"], c["lgu_slug"])]]
            found = any(p == f"{fixed:,.2f}" and f"{final:,.2f}" in paras[max(0, i - 3):i]
                        for i, p in enumerate(paras))
            check(c["year"], c["lgu_slug"], "budget: corrected obligations found in the report", found,
                  f"{row['fund']}: {fixed:,.2f} in a row with a final budget of {final:,.2f}" if found
                  else f"{row['fund']}: {fixed:,.2f} not found beside {final:,.2f}")
            continue
        if c["figure"].startswith("prior_recommendations_"):
            # A count whose words and numeral disagree ("thirteen (10)"): the row already holds
            # the numeral; the correction confirms or replaces it and adds the note. A sentence
            # the same report's Part III table shows is wrong (Manolo Fortich CY 2025) takes a
            # row per count; an empty corrected_amount clears a status the table doesn't have,
            # and an empty printed is a status the sentence doesn't give.
            field_ = c["figure"].removeprefix("prior_recommendations_")
            row = next((r for r in prior_rows if (r["year"], r["lgu_slug"]) == (c["year"], c["lgu_slug"])), None)
            printed = row.get(f"{field_}_as_printed") if row else None
            if row is None or (printed != c["printed"] if printed is not None else c["printed"] not in row["quote"]):
                raise SystemExit(f"correction no longer matches the report: {c}")
            row[field_] = int(c["corrected_amount"]) if c["corrected_amount"] else ""
            if c["note"] not in row.get("correction_note", ""):  # one note can cover two counts
                row["correction_note"] = " ".join(x for x in (row.get("correction_note", ""), c["note"]) if x)
            continue
        row = next((r for r in figure_rows if (r["year"], r["lgu_slug"], r["figure"])
                    == (c["year"], c["lgu_slug"], c["figure"])), None)
        if row is None or row["amount_as_printed"] != c["printed"]:
            raise SystemExit(f"correction no longer matches the report: {c}")
        row["amount"], row["correction_note"] = c["corrected_amount"], c["note"]
        by = {r["figure"]: Decimal(r["amount"]) for r in figure_rows
              if (r["year"], r["lgu_slug"]) == (c["year"], c["lgu_slug"])}
        a, l, e = by["total_assets"], by["total_liabilities"], by["net_assets_equity"]
        check(c["year"], c["lgu_slug"], "assets = liabilities + equity, after corrections", a == l + e,
              f"{a} vs {l} + {e} = {l + e}")

    # Appendix notes (data/phase1/appendix-notes.csv): where the same report's appendix gives
    # other obligations and we keep the statement's, a note on the site says so (decided for
    # Kibawe CY 2024-2025 on 2026-11-08). The script stops if the appendix no longer reads the
    # figure the note cites.
    for n in appendix_notes:
        row = next((r for r in budget_rows if (r["year"], r["lgu_slug"], r.get("fund")) == (n["year"], n["lgu_slug"], n["fund"])),
                   None)
        read = appendix_read.get((n["year"], n["lgu_slug"], n["fund"]), "")
        if row is None or f"appendix {n['appendix_obligations']} (" not in read:
            raise SystemExit(f"appendix note no longer matches the report: {n} (read: {read!r})")
        row["note"] = " ".join(x for x in (row.get("note", ""), n["note"]) if x)

    # Disallowances across reports: each year should open at the balance the report before
    # closed with (a check only; no figure is taken from another year's report). Where a report
    # gives no balance, its note says what the next report opens with.
    by_report = {(r["year"], r["lgu_slug"]): r for r in nd_rows}
    for (year, lgu), meta in sorted(nd_meta.items()):
        prev = by_report.get((str(int(year) - 1), lgu))
        pairs = [(n, meta["opening"][n], prev[f"{n}s"]) for n in NOTICES
                 if prev and meta["opening"][n] is not None and prev.get(f"{n}s")]
        bad = [f"{n}: opens {money(o)}, CY {int(year) - 1} closed {p}" for n, o, p in pairs if o != Decimal(p)]
        check(year, lgu, "disallowances: opens at last report's balance", None if not pairs else not bad,
              "; ".join(bad) or (", ".join(f"{n} {money(o)}" for n, o, _ in pairs) if pairs else
                                 "CY 2022 is the first year we have" if year == "2022" else
                                 "an opening balance isn't given in this report or a closing one in the last"))
        row = by_report[(year, lgu)]
        receivable = ("The receivable COA mentions is the government's own account, not COA's record of "
                      "unsettled notices.") if "receivable" in row.get("quote", "").lower() else ""
        if meta["has"]:
            row["note"] = " ".join(x for x in (row.get("note", ""), receivable) if x)
        else:
            note = " ".join(x for x in ("COA gives no year-end balance in this report; the quote has what it "
                                        "says instead.", receivable) if x)
            nxt, nrow = nd_meta.get((str(int(year) + 1), lgu)), by_report.get((str(int(year) + 1), lgu))
            if nxt and nxt["opens_nil_said"]:
                note += f" COA's CY {int(year) + 1} report says there were none as of January 1, {int(year) + 1}."
            elif nxt and all(v == 0 for v in nxt["opening"].values() if v is not None) \
                    and any(v is not None for v in nxt["opening"].values()):
                note += (f" COA's CY {int(year) + 1} report opens "
                         f"{'the ' + nrow['funds'] if nrow.get('funds') else 'the year'} at nil.")
            row["note"] = note

    key = lambda r: (r["year"], r["lgu_slug"])
    verdict_rows.sort(key=key)
    figure_rows.sort(key=lambda r: (r["year"], r["lgu_slug"], list(STATEMENTS["Statement of Financial Position"]) .__add__(list(STATEMENTS["Statement of Financial Performance"])).index(r["figure"])))
    common = ["year", "lgu_slug", "lgu", "report_url", "file_in_zip", "file_sha256", "part", "item", "toc_pages"]
    write(OUT / "verdicts.csv", verdict_rows, common[:3] + ["verdict", "opinion_quote"] + common[3:] + ["pdf_page"])
    write(OUT / "figures.csv", figure_rows,
          common[:3] + ["figure", "label_as_printed", "amount_as_printed", "amount", "correction_note"]
          + common[3:] + ["pdf_page"])
    prior_rows.sort(key=key)
    write(OUT / "prior-recommendations.csv", prior_rows,
          common[:3] + ["total", "fully_implemented"] + STATUSES[1:] + ["reiterated", "total_as_printed",
                                                                         "fully_implemented_as_printed", "stated_in",
                                                                         "quote", "correction_note"]
          + common[3:] + ["pdf_page"])
    finding_rows.sort(key=key)  # stable: each report's findings stay in COA's order
    write(OUT / "findings.csv", finding_rows,
          common[:3] + ["number", "numbered", "observation"] + common[3:] + ["pdf_page"])
    count_rows.sort(key=key)
    write(OUT / "finding-counts.csv", count_rows,
          common[:3] + ["findings", "numbers_as_printed", "count_note", "numbered_after_findings"]
          + common[3:] + ["pdf_page"])
    nd_rows.sort(key=key)
    write(OUT / "disallowances.csv", nd_rows,
          common[:3] + [f"{n}s" for n in NOTICES] + [f"{n}s_as_printed" for n in NOTICES]
          + ["total_as_printed", "funds", "note", "quote"] + common[3:] + ["pdf_page"])
    nd_table_rows.sort(key=key)  # stable: each report's rows stay in COA's order
    write(OUT / "disallowance-tables.csv", nd_table_rows,
          common[:3] + ["fund", "notice", "label_as_printed", "beginning", "issued", "settled", "ending",
                        "other_columns"] + common[3:] + ["pdf_page"])
    budget_rows.sort(key=key)  # stable: each report's funds stay in COA's order
    write(OUT / "appropriations.csv", budget_rows, common[:3] + BUDGET_FIELDS + common[3:] + ["pdf_page"])
    budget_table.sort(key=key)
    write(OUT / "appropriation-tables.csv", budget_table, common[:3] + BUDGET_TABLE_FIELDS + common[3:] + ["pdf_page"])
    write(OUT / "checks.csv", check_rows, ["year", "lgu_slug", "check", "result", "detail"])

    fails = [c for c in check_rows if c["result"] == "FAIL"]
    tally: dict[str, int] = {}
    for r in verdict_rows:
        tally[r["verdict"] or "?"] = tally.get(r["verdict"] or "?", 0) + 1
    print(f"{len(verdict_rows)} verdicts: {tally}")
    print(f"{len(figure_rows)} figures, {len(prior_rows)} past-recommendation rows, "
          f"{len(finding_rows)} findings in {len(count_rows)} reports, "
          f"{len(nd_rows)} disallowance rows ({len(nd_table_rows)} table rows), "
          f"{len(budget_rows)} appropriation rows ({len(budget_table)} table rows), "
          f"{len(check_rows)} checks, {len(fails)} failed")
    for c in fails:
        print(f"  FAIL {c['year']} {c['lgu_slug']}: {c['check']} - {c['detail'][:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
