// Numbers are always grouped the Philippine way (1,234,567.89), whatever the language.

const peso2 = new Intl.NumberFormat('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat('en-PH');

/** ₱1,234,567.89, to the centavo, as COA prints it (data rule 4). Negative amounts get a minus sign. */
export function peso(n: number): string {
  return (n < 0 ? '−₱' : '₱') + peso2.format(Math.abs(n));
}

export function count(n: number): string {
  return whole.format(n);
}

/** One decimal, as phase1-data.md decides for the share obligated. */
export function percent(n: number): string {
  return `${n.toFixed(1)}%`;
}

/** "10-12" → "10–12". COA's ranges are kept as printed otherwise (Quezon CY 2022's "116-113"). */
export function pageRange(pages: string): string {
  return pages.replace(/-/g, '–');
}

export function isRange(pages: string): boolean {
  return /[-–,]/.test(pages);
}

export function fileSize(bytes: number): string {
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  return `${Math.round(bytes / 1e3)} KB`;
}
