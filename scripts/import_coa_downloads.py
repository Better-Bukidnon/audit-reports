"""File COA Annual Audit Report downloads into raw/<year>/<lgu>/ and write source manifests.

Usage:
    python -I scripts/import_coa_downloads.py <year> <listing.tsv> <downloads-dir>

<listing.tsv> is the file list read from COA's WP File Download folders (one row per file):
    category_id  file_id  slug  ext  size  created  modified

For every row this script:
  1. finds the downloaded file (named from the COA title, e.g. Baungon-Annual-Audit-Report-2024.zip),
  2. checks its size against COA's listing and moves it to raw/<year>/<lgu-slug>/,
  3. unzips report ZIPs into raw/<year>/<lgu-slug>/extracted/,
  4. checks every file for password protection and dumps .docx text to a .txt beside it,
  5. writes data/sources/coa-aar-<year>-files.csv and data/sources/coa-aar-<year>-contents.csv.

raw/ is git-ignored (see plan D3); the manifests record what was downloaded and its SHA-256.
Uses only the standard library. Never executes anything from the downloads.
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEVEN_ZIP = Path(r"C:\Program Files\7-Zip\7z.exe")

# COA title prefix -> (our slug, display name, type). Names follow docs/auditees.md.
LGUS = {
    "Bukidnon": ("bukidnon-province", "Province of Bukidnon", "Province"),
    "Malaybalay City": ("malaybalay", "Malaybalay", "Component city"),
    "Valencia City": ("valencia", "Valencia", "Component city"),
    "Baungon": ("baungon", "Baungon", "Municipality"),
    "Cabanglasan": ("cabanglasan", "Cabanglasan", "Municipality"),
    "Damulog": ("damulog", "Damulog", "Municipality"),
    "Dangcagan": ("dangcagan", "Dangcagan", "Municipality"),
    "Don Carlos": ("don-carlos", "Don Carlos", "Municipality"),
    "Impasugong": ("impasug-ong", "Impasug-ong", "Municipality"),
    "Kadingilan": ("kadingilan", "Kadingilan", "Municipality"),
    "Kalilangan": ("kalilangan", "Kalilangan", "Municipality"),
    "Kibawe": ("kibawe", "Kibawe", "Municipality"),
    "Kitaotao": ("kitaotao", "Kitaotao", "Municipality"),
    "Lantapan": ("lantapan", "Lantapan", "Municipality"),
    "Libona": ("libona", "Libona", "Municipality"),
    "Malitbog": ("malitbog", "Malitbog", "Municipality"),
    "Manolo Fortich": ("manolo-fortich", "Manolo Fortich", "Municipality"),
    "Maramag": ("maramag", "Maramag", "Municipality"),
    "Pangantucan": ("pangantucan", "Pangantucan", "Municipality"),
    "Quezon": ("quezon", "Quezon", "Municipality"),
    "San Fernando": ("san-fernando", "San Fernando", "Municipality"),
    "Sumilao": ("sumilao", "Sumilao", "Municipality"),
    "Talakag": ("talakag", "Talakag", "Municipality"),
}
DOC_TYPES = {"annual-audit-report": "annual_audit_report", "executive-summary": "executive_summary"}
PDF_PERMS = {"print": 2, "modify": 3, "copy": 4, "annotate": 5, "accessibility": 9}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_slug(slug: str, year: str) -> tuple[str, str]:
    """'san-fernando-annual-audit-report-2024-2' -> ('San Fernando', 'annual-audit-report')."""
    m = re.fullmatch(rf"(.+?)-(annual-audit-report|executive-summary)-{year}(?:-\d+)?", slug)
    if not m:
        raise ValueError(f"unexpected COA slug: {slug}")
    words = m.group(1).split("-")
    title_prefix = " ".join(w.capitalize() for w in words)
    return title_prefix, m.group(2)


def download_name(title_prefix: str, doc: str, year: str, ext: str) -> str:
    """Chrome saves COA files as the title with spaces turned into hyphens."""
    doc_title = "Annual-Audit-Report" if doc == "annual-audit-report" else "Executive-Summary"
    return f"{title_prefix.replace(' ', '-')}-{doc_title}-{year}.{ext}"


def pdf_protection(data: bytes) -> str:
    enc = re.search(rb"/Encrypt\s+\d+\s+\d+\s+R", data)
    if not enc:
        return "none"
    m = re.search(rb"/P\s+(-?\d+)", data)
    if not m:
        return "encrypted (permissions unknown)"
    p = int(m.group(1)) & 0xFFFFFFFF
    blocked = [name for name, bit in PDF_PERMS.items() if not p & (1 << bit)]
    return "owner-password; blocks " + ("+".join(blocked) if blocked else "nothing")


def docx_protection_and_text(path: Path) -> tuple[str, int, int]:
    """Return (protection, text chars, table count) and write <name>.txt beside the file."""
    head = path.read_bytes()[:8]
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return "encrypted (password to open)", 0, 0
    if not zipfile.is_zipfile(path):
        kind = "Word lock file" if path.name.startswith("~$") else f"not a Word file (starts {head!r})"
        return f"{kind}, {path.stat().st_size} bytes", 0, 0
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        settings = z.read("word/settings.xml").decode("utf8", "replace") if "word/settings.xml" in names else ""
        doc = z.read("word/document.xml").decode("utf8", "replace")
    m = re.search(r"<w:documentProtection\b[^>]*>", settings)
    if m:
        edit = re.search(r'w:edit="([^"]*)"', m.group(0))
        enforced = re.search(r'w:enforcement="(1|true|on)"', m.group(0))
        protection = f"edit-restricted ({edit.group(1) if edit else '?'})" + ("" if enforced else ", not enforced")
    else:
        protection = "none"
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", doc, flags=re.S):
        t = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p)).strip()
        if t:
            paras.append(t)
    text = "\n".join(paras)
    path.with_suffix(".txt").write_text(text, encoding="utf8")
    return protection, len(text), doc.count("<w:tbl>")


def xlsx_protection(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            xml = "".join(
                z.read(n).decode("utf8", "replace") for n in z.namelist() if n.startswith("xl/") and n.endswith(".xml")
            )
    except zipfile.BadZipFile:
        return "encrypted (password to open)"
    flags = [tag for tag in ("workbookProtection", "sheetProtection") if f"<{tag}" in xml]
    return ("edit-restricted (" + "+".join(flags) + ")") if flags else "none"


def extract_zip(zip_path: Path, out_dir: Path) -> tuple[bool, list[zipfile.ZipInfo]]:
    with zipfile.ZipFile(zip_path) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        encrypted = any(i.flag_bits & 0x1 for i in infos)
        if encrypted:
            return True, infos
        out_dir.mkdir(parents=True, exist_ok=True)
        # Skip members already extracted at the right size (COA marks some files read-only).
        todo = [i for i in infos if not ((out_dir / i.filename).is_file() and (out_dir / i.filename).stat().st_size == i.file_size)]
        try:
            for info in todo:
                z.extract(info, out_dir)  # zipfile strips absolute paths and '..' components
        except NotImplementedError:  # e.g. Deflate64; fall back to 7-Zip
            subprocess.run([str(SEVEN_ZIP), "x", str(zip_path), f"-o{out_dir}", "-y"], check=True, capture_output=True)
    return False, infos


def describe(path: Path) -> tuple[str, int, int]:
    ext = path.suffix.lower()
    if ext == ".docx":
        return docx_protection_and_text(path)
    if ext == ".pdf":
        return pdf_protection(path.read_bytes()), 0, 0
    if ext in (".xlsx", ".xlsm"):
        return xlsx_protection(path), 0, 0
    if ext in (".doc", ".xls"):
        return "legacy Office format (not checked)", 0, 0
    return "not checked", 0, 0


def main(year: str, listing: Path, downloads: Path) -> int:
    rows = list(csv.DictReader(listing.open(encoding="utf-8-sig"), delimiter="\t"))  # tolerate a BOM
    raw_year = REPO / "raw" / year
    files_out, contents_out, problems = [], [], []
    today = date.today().isoformat()

    for r in rows:
        title_prefix, doc = parse_slug(r["slug"], year)
        slug, name, lgu_type = LGUS[title_prefix]
        fname = download_name(title_prefix, doc, year, r["ext"])
        dest_dir = raw_year / slug
        dest = dest_dir / fname
        src = downloads / fname
        expected = int(r["size"])

        if src.exists():
            if src.stat().st_size != expected:
                problems.append(f"{fname}: size {src.stat().st_size} != COA {expected}; left in Downloads")
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if sha256(dest) != sha256(src):
                    problems.append(f"{fname}: differs from the copy already in {dest_dir}; left in Downloads")
                    continue
                try:
                    src.unlink()  # identical copy already filed
                except OSError:
                    problems.append(f"{fname}: identical copy already filed; Downloads copy is in use, delete it later")
            else:
                try:
                    shutil.move(str(src), dest)
                except PermissionError:  # another program has the download open
                    if not (dest.exists() and dest.stat().st_size == expected):
                        shutil.copy2(src, dest)
                    problems.append(f"{fname}: copied; Downloads copy is in use, delete it later")
        if not dest.exists():
            problems.append(f"{fname}: not downloaded")
            continue
        if dest.stat().st_size != expected:
            problems.append(f"{fname}: filed copy is {dest.stat().st_size} bytes, COA lists {expected}")

        zip_encrypted, protection, chars, tables = "", "", 0, 0
        if r["ext"] == "zip":
            enc, infos = extract_zip(dest, dest_dir / "extracted")
            zip_encrypted = "yes" if enc else "no"
            for info in infos:
                inner = dest_dir / "extracted" / info.filename
                if enc or not inner.exists():
                    contents_out.append([year, slug, fname, info.filename, info.file_size, "", "zip encrypted" if enc else "missing", 0, 0])
                    continue
                prot, chars_i, tables_i = describe(inner)
                contents_out.append([year, slug, fname, info.filename, info.file_size, sha256(inner), prot, chars_i, tables_i])
        else:
            protection, chars, tables = describe(dest)

        files_out.append([
            year, slug, name, lgu_type, DOC_TYPES[doc], r["file_id"], r["category_id"], r["slug"],
            f"https://www.coa.gov.ph/wpfd_file/{r['slug']}/", fname, r["ext"], dest.stat().st_size, sha256(dest),
            r["created"], r["modified"], today, zip_encrypted, protection,
        ])

    out_dir = REPO / "data" / "sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / f"coa-aar-{year}-files.csv").open("w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow([
            "year", "lgu_slug", "lgu", "lgu_type", "document", "coa_file_id", "coa_category_id", "coa_slug",
            "coa_file_page", "filename", "ext", "bytes", "sha256", "coa_uploaded", "coa_modified", "downloaded",
            "zip_encrypted", "protection",
        ])
        w.writerows(sorted(files_out, key=lambda x: (x[1], x[4])))
    with (out_dir / f"coa-aar-{year}-contents.csv").open("w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["year", "lgu_slug", "zip", "path_in_zip", "bytes", "sha256", "protection", "text_chars", "tables"])
        w.writerows(sorted(contents_out, key=lambda x: (x[1], x[3])))

    print(f"filed {len(files_out)} of {len(rows)} files; {len(contents_out)} files inside ZIPs")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])))
