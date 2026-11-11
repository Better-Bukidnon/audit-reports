#!/usr/bin/env node
// Builds the site's data from the CSVs in ../data, on every `npm run dev` and `npm run build`:
//   public/data/index.json        every government's summary per year, the corrections, the downloads
//   public/data/gov/<slug>.json   one government: every figure and quote, each with its source
//   public/data/csv/...           the CSVs themselves, for download
// The CSVs are the record (docs/phase1-data.md). Nothing here changes a figure: it only
// reshapes, and it stops with an error if a report is missing something the site shows.

import { readFile, writeFile, mkdir, rm, cp, readdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const site = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dataDir = resolve(site, '..', 'data');
const phase1 = resolve(dataDir, 'phase1');
const out = resolve(site, 'public', 'data');

const VERDICTS = new Set(['unmodified', 'qualified', 'adverse', 'disclaimer']);
const FIGURES = ['total_assets', 'total_liabilities', 'net_assets_equity', 'total_revenue', 'surplus_deficit'];

// ---------- CSV ----------

function parseCsv(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += c;
  }
  if (field !== '' || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [head, ...body] = rows.filter((r) => !(r.length === 1 && r[0] === ''));
  return body.map((r) => {
    if (r.length !== head.length) throw new Error(`CSV row has ${r.length} fields, header has ${head.length}: ${r.join(',')}`);
    return Object.fromEntries(head.map((h, i) => [h, r[i]]));
  });
}

async function csv(path) {
  return parseCsv(await readFile(path, 'utf8'));
}

// ---------- Values ----------

const str = (s) => (s === undefined || s === '' ? null : s);

function num(s, what) {
  if (s === '' || s === undefined) return null;
  const n = Number(s);
  if (!Number.isFinite(n)) throw new Error(`${what}: not a number: ${JSON.stringify(s)}`);
  return n;
}

function need(value, what) {
  if (value === null || value === undefined) throw new Error(`Missing ${what}`);
  return value;
}

function source(r) {
  return {
    url: need(str(r.report_url), 'report_url'),
    file: str(r.file_in_zip),
    sha256: str(r.file_sha256),
    part: need(str(r.part), 'part'),
    item: need(str(r.item), 'item'),
    pages: str(r.toc_pages),
    pdfPage: str(r.pdf_page),
  };
}

const key = (r) => `${r.year}|${r.lgu_slug}`;

function byReport(rows) {
  const m = new Map();
  for (const r of rows) {
    if (m.has(key(r))) throw new Error(`Two rows for ${key(r)}`);
    m.set(key(r), r);
  }
  return m;
}

function groupByReport(rows) {
  const m = new Map();
  for (const r of rows) {
    if (!m.has(key(r))) m.set(key(r), []);
    m.get(key(r)).push(r);
  }
  return m;
}

// ---------- Read ----------

const governments = await csv(resolve(dataDir, 'governments.csv'));
const verdictRows = await csv(resolve(phase1, 'verdicts.csv'));
const verdicts = byReport(verdictRows);
// The years are the ones in the data: every government needs a record for each (checked below).
const YEARS = [...new Set(verdictRows.map((r) => Number(r.year)))].sort((a, b) => a - b);
const priorRecs = byReport(await csv(resolve(phase1, 'prior-recommendations.csv')));
const findingCounts = byReport(await csv(resolve(phase1, 'finding-counts.csv')));
const disallowances = byReport(await csv(resolve(phase1, 'disallowances.csv')));
const figures = groupByReport(await csv(resolve(phase1, 'figures.csv')));
const findings = groupByReport(await csv(resolve(phase1, 'findings.csv')));
const appropriations = groupByReport(await csv(resolve(phase1, 'appropriations.csv')));
const corrections = await csv(resolve(phase1, 'corrections.csv'));

const files = new Map();
for (const year of YEARS) {
  for (const r of await csv(resolve(dataDir, 'sources', `coa-aar-${year}-files.csv`))) {
    files.set(`${r.year}|${r.lgu_slug}|${r.document}`, r);
  }
}

// ---------- Shape ----------

function yearRecord(slug, year) {
  const k = `${year}|${slug}`;
  const v = need(verdicts.get(k), `verdict for ${k}`);
  if (!VERDICTS.has(v.verdict)) throw new Error(`${k}: unknown verdict ${v.verdict}`);

  const report = need(files.get(`${year}|${slug}|annual_audit_report`), `report file for ${k}`);
  const summary = files.get(`${year}|${slug}|executive_summary`);

  const figs = {};
  for (const r of need(figures.get(k), `figures for ${k}`)) {
    figs[r.figure] = {
      label: r.label_as_printed,
      value: need(num(r.amount, `${k} ${r.figure}`), `${k} ${r.figure}`),
      printed: r.amount_as_printed,
      correction: str(r.correction_note),
      source: source(r),
    };
  }
  for (const f of FIGURES) need(figs[f], `${k} ${f}`);

  const p = need(priorRecs.get(k), `past recommendations for ${k}`);
  const fc = need(findingCounts.get(k), `finding count for ${k}`);
  const items = (findings.get(k) ?? []).map((r) => ({ number: r.number, text: r.observation, source: source(r) }));
  if (items.length !== Number(fc.findings)) throw new Error(`${k}: ${items.length} findings listed, count says ${fc.findings}`);

  const d = need(disallowances.get(k), `disallowances for ${k}`);
  const budget = need(appropriations.get(k), `appropriations for ${k}`).map((r) => ({
    fund: r.fund,
    fundAsPrinted: r.fund_as_printed,
    final: need(num(r.final_appropriations, `${k} final`), `${k} final`),
    obligations: need(num(r.obligations, `${k} obligations`), `${k} obligations`),
    share: num(r.share_obligated, `${k} share`),
    currentFrom: r.current_from,
    note: str(r.note),
    correction: str(r.correction_note),
    source: source(r),
  }));

  return {
    year,
    report: { url: report.coa_file_page, format: report.ext, bytes: Number(report.bytes) },
    summary: summary ? { url: summary.coa_file_page, bytes: Number(summary.bytes) } : null,
    verdict: { verdict: v.verdict, quote: v.opinion_quote, source: source(v) },
    figures: figs,
    priorRecs: {
      total: need(num(p.total, `${k} total`), `${k} total`),
      fully: need(num(p.fully_implemented, `${k} fully`), `${k} fully`),
      partially: num(p.partially_implemented, k),
      notImplemented: num(p.not_implemented, k),
      forImplementation: num(p.for_implementation, k),
      closed: num(p.closed, k),
      reiterated: num(p.reiterated, k),
      statedIn: p.stated_in,
      quote: str(p.quote),
      correction: str(p.correction_note),
      source: source(p),
    },
    findings: {
      count: Number(fc.findings),
      numbersAsPrinted: fc.numbers_as_printed,
      countNote: str(fc.count_note),
      numberedAfter: str(fc.numbered_after_findings),
      source: source(fc),
      items,
    },
    disallowances: {
      disallowances: num(d.disallowances, k),
      suspensions: num(d.suspensions, k),
      charges: num(d.charges, k),
      note: str(d.note),
      quote: str(d.quote),
      source: source(d),
    },
    budget,
  };
}

// The General Fund line, or COA's combined statement where it gives the funds together.
function mainFund(budget) {
  return budget.find((b) => b.fund === 'General Fund') ?? budget.find((b) => b.fund !== 'Special Education Fund') ?? null;
}

let dataAsOf = null;
try {
  dataAsOf = execFileSync('git', ['log', '-1', '--format=%cs', '--', 'data'], { cwd: resolve(site, '..'), encoding: 'utf8' }).trim() || null;
} catch {
  /* not a git checkout */
}

await rm(out, { recursive: true, force: true });
await mkdir(resolve(out, 'gov'), { recursive: true });

const index = { dataAsOf, years: YEARS, governments: [], corrections: [], downloads: [] };

for (const g of governments) {
  const years = {};
  const summary = {};
  for (const year of YEARS) {
    const y = yearRecord(g.slug, year);
    years[year] = y;
    const main = mainFund(y.budget);
    summary[year] = {
      verdict: y.verdict.verdict,
      findings: y.findings.count,
      recsFully: y.priorRecs.fully,
      recsTotal: y.priorRecs.total,
      disallowances: y.disallowances.disallowances,
      suspensions: y.disallowances.suspensions,
      mainFund: main && { fund: main.fund, share: main.share, final: main.final, obligations: main.obligations },
      reportUrl: y.report.url,
    };
  }
  const meta = { slug: g.slug, name: g.name, type: g.type, district: str(g.district) };
  await writeFile(resolve(out, 'gov', `${g.slug}.json`), JSON.stringify({ ...meta, years }));
  index.governments.push({ ...meta, years: summary });
}

const names = new Map(governments.map((g) => [g.slug, g.name]));
index.corrections = corrections.map((c) => ({
  date: c.date,
  year: Number(c.year),
  slug: c.lgu_slug,
  name: need(names.get(c.lgu_slug), `government ${c.lgu_slug}`),
  figure: c.figure,
  printed: c.printed,
  corrected: c.corrected_amount,
  from: c.source_of_correction,
  note: c.note,
}));

// Downloads: the CSVs as they are in the repo.
await mkdir(resolve(out, 'csv', 'sources'), { recursive: true });
await cp(resolve(dataDir, 'governments.csv'), resolve(out, 'csv', 'governments.csv'));
index.downloads.push({ path: 'csv/governments.csv', rows: governments.length });
for (const name of (await readdir(phase1)).filter((n) => n.endsWith('.csv')).sort()) {
  await cp(resolve(phase1, name), resolve(out, 'csv', name));
  index.downloads.push({ path: `csv/${name}`, rows: (await csv(resolve(phase1, name))).length });
}
for (const year of YEARS) {
  const name = `coa-aar-${year}-files.csv`;
  await cp(resolve(dataDir, 'sources', name), resolve(out, 'csv', 'sources', name));
  index.downloads.push({ path: `csv/sources/${name}`, rows: (await csv(resolve(dataDir, 'sources', name))).length });
}

await writeFile(resolve(out, 'index.json'), JSON.stringify(index));
console.log(
  `public/data ready: ${index.governments.length} governments x ${YEARS.length} years, ` +
    `${index.corrections.length} corrections, ${index.downloads.length} CSVs, data as of ${dataAsOf ?? 'unknown'}`,
);
