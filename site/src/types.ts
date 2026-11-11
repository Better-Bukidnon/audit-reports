// The shape of public/data/*.json, written by scripts/build-data.mjs.

export type Verdict = 'unmodified' | 'qualified' | 'adverse' | 'disclaimer';
export type FigureKey = 'total_assets' | 'total_liabilities' | 'net_assets_equity' | 'total_revenue' | 'surplus_deficit';
export const FIGURE_KEYS: FigureKey[] = ['total_assets', 'total_liabilities', 'net_assets_equity', 'total_revenue', 'surplus_deficit'];

/** Where in COA's report a figure or quote comes from. */
export type Source = {
  /** COA's page for the file: the report's ZIP, or the executive summary PDF. */
  url: string;
  /** The file inside the ZIP; null for the executive summary PDF. */
  file: string | null;
  sha256: string | null;
  part: string;
  item: string;
  /** The page(s) COA's own table of contents gives. */
  pages: string | null;
  /** The real page, for PDFs only. */
  pdfPage: string | null;
};

export type GovernmentMeta = {
  slug: string;
  name: string;
  type: 'Province' | 'City' | 'Municipality';
  district: string | null;
};

export type YearSummary = {
  verdict: Verdict;
  findings: number;
  recsFully: number;
  recsTotal: number;
  disallowances: number | null;
  suspensions: number | null;
  mainFund: { fund: string; share: number | null; final: number; obligations: number } | null;
  reportUrl: string;
};

export type Correction = {
  date: string;
  year: number;
  slug: string;
  name: string;
  figure: string;
  printed: string;
  corrected: string;
  from: string;
  note: string;
};

export type Index = {
  dataAsOf: string | null;
  years: number[];
  governments: (GovernmentMeta & { years: Record<string, YearSummary> })[];
  corrections: Correction[];
  downloads: { path: string; rows: number }[];
};

export type Figure = { label: string; value: number; printed: string; correction: string | null; source: Source };

export type Fund = {
  fund: string;
  fundAsPrinted: string;
  final: number;
  obligations: number;
  share: number | null;
  currentFrom: string;
  note: string | null;
  correction: string | null;
  source: Source;
};

export type YearRecord = {
  year: number;
  report: { url: string; format: string; bytes: number };
  summary: { url: string; bytes: number } | null;
  verdict: { verdict: Verdict; quote: string; source: Source };
  figures: Record<FigureKey, Figure>;
  priorRecs: {
    total: number;
    fully: number;
    partially: number | null;
    notImplemented: number | null;
    forImplementation: number | null;
    closed: number | null;
    reiterated: number | null;
    statedIn: string;
    quote: string | null;
    correction: string | null;
    source: Source;
  };
  findings: {
    count: number;
    numbersAsPrinted: string;
    countNote: string | null;
    numberedAfter: string | null;
    source: Source;
    items: { number: string; text: string; source: Source }[];
  };
  disallowances: {
    disallowances: number | null;
    suspensions: number | null;
    charges: number | null;
    note: string | null;
    quote: string | null;
    source: Source;
  };
  budget: Fund[];
};

export type Government = GovernmentMeta & { years: Record<string, YearRecord> };
