"""Step 3b' - Template parser for the biggest invoice layout (Nabis delivery invoices, ~1,100 files).

Deterministic and free. Writes into llm_results in the same JSON shape the LLM returns (model='template:nabis'),
so later steps treat it identically and the LLM pass skips these files.
A file is only accepted when every required field matches; otherwise it falls through to the LLM.

Nabis invoices also carry embedded dunning ("Payment required for previous overdue invoices: 971102, 995092",
"Must Pay Previous Balance Prior To Delivery") - captured as `embedded_chase`.
"""
import json
import re
import sqlite3
import time

from pipeline.llm import DB, init_tables

MONEY = r"\$?(-?[\d,]+\.\d{2})"


def _after(label, text, value=r"(.+)"):
    m = re.search(rf"^{label}\s*\n\s*{value}\s*$", text, re.M | re.I)
    return m.group(1).strip() if m else None


def parse_nabis(text):
    if not re.search(r"ORDER #\s*\n\s*\d+\s*\n\s*INVOICE #", text[:300]):
        return None
    inv_no = _after(r"INVOICE #", text, r"(\d+-[A-Z])")
    total = _after(r"Total Balance Due", text, MONEY)
    vendor = _after(r"Contact", text)
    if not (inv_no and total and vendor):
        return None
    dep = _after(r"Departure Time", text, r"(\d{2}/\d{2}/\d{4})")
    overdue = re.search(r"previous overdue invoices?:\s*([\d,\s]+)", text, re.I)
    overdue_nos = [n for n in re.split(r"[,\s]+", overdue.group(1)) if n] if overdue else []
    overdue_bal = re.search(r"Required Overdue Balance\s*\n\s*" + MONEY, text)
    hold = bool(re.search(r"must pay previous balance prior to delivery", text, re.I))
    return {
        "id": None, "label": "invoice", "dunning_level": None, "confidence": 0.97,
        "evidence": f"INVOICE # {inv_no}; Total Balance Due ${total}",
        "vendor": vendor.title(),
        "invoice": {
            "invoice_number": inv_no,
            "invoice_date": f"{dep[6:]}-{dep[:2]}-{dep[3:5]}" if dep else None,  # delivery (departure) date
            "due_date": None,  # only "Net 60" terms are printed; we never compute dates
            "total_amount": float(total.replace(",", "")),
            "currency": "USD",
            "po_number": _after(r"PO / SO", text),
        },
        "referenced_invoice_numbers": overdue_nos,
        "embedded_chase": {
            "chaser": "Nabis",
            "invoice_numbers": overdue_nos,
            "overdue_balance": float(overdue_bal.group(1).replace(",", "")) if overdue_bal else None,
            "level": "escalation" if hold else "reminder",
            "evidence": "Must Pay Previous Balance Prior To Delivery" if hold else "previous overdue invoices listed",
        } if overdue_nos else None,
    }


def main():
    db = sqlite3.connect(DB, timeout=30)
    init_tables(db)
    rows = db.execute("""SELECT min(file_id), text FROM documents
                         WHERE text LIKE 'ORDER #%' GROUP BY sha256""").fetchall()
    ok = 0
    for fid, text in rows:
        r = parse_nabis(text or "")
        if r:
            ok += 1
            r["id"] = fid
            db.execute("INSERT OR REPLACE INTO llm_results VALUES ('document',?,?,?,?,?,?)",
                       (fid, "template", "template:nabis", 0, json.dumps(r), time.time()))
    db.commit()
    print(f"nabis template: parsed {ok} of {len(rows)} candidate files (rest fall through to the LLM)")


if __name__ == "__main__":
    main()
