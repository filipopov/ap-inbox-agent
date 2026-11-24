"""Step 2 - Extract text from every attachment file.

Every file ends with an explicit extract_status, never a silent blank:
  ok           text layer read directly
  ocr          no text layer -> rendered pages read with Tesseract OCR
  empty        file opened, but no text even after OCR
  unreadable   corrupt / encrypted / failed to parse (reason in extract_note)
  unsupported  file type we do not read (reason in extract_note)
Files are de-duplicated by SHA-256 so identical PDFs are processed once (documents.sha256).

Output table: documents (one row per unique file_id, with sha256, text, status, page counts).
"""
import hashlib
import io
import sqlite3
import subprocess
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data/ap.db"
MIN_CHARS_PER_PAGE = 25   # below this a PDF page is treated as a scan and OCR'd
MAX_OCR_PAGES = 5         # invoices rarely exceed this; noted in extract_note when hit


def _ocr_png(png: bytes) -> str:
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6"], input=png,
                       capture_output=True, timeout=120)
    return r.stdout.decode("utf-8", "replace")


def _pdf(data: bytes):
    doc = pymupdf.open(stream=data, filetype="pdf")
    if doc.needs_pass:
        return "", "unreadable", "password-protected PDF", doc.page_count
    texts, ocr_used, notes = [], False, []
    for i, page in enumerate(doc):
        t = page.get_text()
        if len(t.strip()) < MIN_CHARS_PER_PAGE:
            if i < MAX_OCR_PAGES:
                t = _ocr_png(page.get_pixmap(dpi=200).tobytes("png"))
                ocr_used = True
            else:
                notes.append(f"page {i + 1}+ not OCR'd (limit {MAX_OCR_PAGES})")
                break
        texts.append(t)
    text = "\n\f\n".join(texts)
    status = "empty" if not text.strip() else ("ocr" if ocr_used else "ok")
    return text, status, "; ".join(notes) or None, doc.page_count


def _xlsx(data: bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for ws in wb.worksheets:
        lines.append(f"# sheet {ws.title}")
        for row in ws.iter_rows(values_only=True):
            if any(c is not None for c in row):
                lines.append("\t".join("" if c is None else str(c) for c in row))
    return "\n".join(lines), None


def _docx(data: bytes):
    import docx
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        parts += ["\t".join(c.text for c in r.cells) for r in t.rows]
    return "\n".join(parts), None


def _zip(data: bytes):
    out, notes = [], []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            inner = z.read(info)
            text, status, note, _ = extract_bytes(inner, info.filename)
            out.append(f"=== {info.filename} [{status}] ===\n{text}")
            if note:
                notes.append(f"{info.filename}: {note}")
    return "\n".join(out), "; ".join(notes) or None


def extract_bytes(data: bytes, name: str):
    """Return (text, status, note, page_count) for a file's bytes."""
    lower = name.lower()
    try:
        if data[:5] == b"%PDF-" or lower.endswith(".pdf"):
            return _pdf(data)
        if data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff" or data[:4] == b"GIF8":
            text = _ocr_png(pymupdf.Pixmap(data).tobytes("png"))
            return text, ("ocr" if text.strip() else "empty"), "image file", 1
        if data[:4] == b"\xd0\xcf\x11\xe0":
            return "", "unreadable", "password-protected or legacy (OLE) Office file", None
        if data[:2] == b"PK":
            if lower.endswith(".xlsx"):
                text, note = _xlsx(data)
            elif lower.endswith(".docx"):
                text, note = _docx(data)
            else:
                text, note = _zip(data)
        elif lower.endswith((".csv", ".txt", ".ics", ".json", ".html", ".htm")) or not data[:512].count(b"\x00"):
            text, note = data.decode("utf-8", "replace"), None
        else:
            return "", "unsupported", f"unknown binary format ({name})", None
        return text, ("ok" if text.strip() else "empty"), note, None
    except Exception as e:  # recorded, never swallowed: status + reason end up in the table
        return "", "unreadable", f"{type(e).__name__}: {e}"[:300], None


def _work(row):
    file_id, path, filename = row
    data = (ROOT / path).read_bytes()
    text, status, note, pages = extract_bytes(data, filename or path)
    return file_id, hashlib.sha256(data).hexdigest(), text, status, note, pages


def main():
    db = sqlite3.connect(DB)
    db.execute("DROP TABLE IF EXISTS documents")
    db.execute("""CREATE TABLE documents (file_id TEXT PRIMARY KEY, sha256 TEXT, text TEXT,
                  extract_status TEXT, extract_note TEXT, page_count INTEGER)""")
    rows = db.execute("SELECT DISTINCT file_id, path, filename FROM attachments WHERE path IS NOT NULL").fetchall()
    with ProcessPoolExecutor() as pool:
        for i, res in enumerate(pool.map(_work, rows, chunksize=8), 1):
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?)", res)
            if i % 500 == 0:
                db.commit()
                print(f"{i}/{len(rows)}", flush=True)
    db.execute("CREATE INDEX ix_doc_sha ON documents(sha256)")
    db.commit()
    for s, n in db.execute("SELECT extract_status, count(*) FROM documents GROUP BY 1 ORDER BY 2 DESC"):
        print(f"{s}: {n}")
    print("unique contents:", db.execute("SELECT count(DISTINCT sha256) FROM documents").fetchone()[0])


if __name__ == "__main__":
    main()
