"""Step 3a - Rules: the first, free stage of the cascade.

Labels: invoice | statement | payment_reminder | remittance | other
Reminders also get a dunning level: reminder < escalation < final_notice.

Rules only decide when a *strong* pattern fires (mostly subject lines and filenames, which are
written by vendors' billing systems and very regular). Everything else is left undecided
(label NULL) and goes to the next stage. Each decision stores the rule that fired as evidence.

Output table: classifications(item_kind, item_id, label, dunning_level, confidence, decided_by, evidence)
"""
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data/ap.db"

# Dunning levels, checked strongest first. Same patterns work for email subjects and documents.
DUNNING = [
    ("final_notice", r"final (notice|demand|reminder)|last notice|transferred to collections|"
                     r"collection agency|sent to collections|service (will be )?(suspended|interrupted|disconnected)|"
                     r"disconnection notice|legal action"),
    ("escalation", r"past[- ]due|overdue|delinquent|second notice|2nd notice|"
                   r"seriously past|immediate attention|account (is )?on hold|credit hold"),
    ("reminder", r"payment reminder|friendly reminder|reminder:|coming due|is due|now due|due soon|"
                 r"receivable open reminder|upcoming payment|outstanding (balance|invoices?)"),
]

# Strong subject-line patterns (email). Order matters: first match wins.
EMAIL_SUBJECT = [
    ("remittance", r"thank you for (your )?(the )?payment|payment (confirmation|receipt|received|processed)|"
                   r"remittance|payment advice|scheduled (an )?(online )?payment|thank you for scheduling|"
                   r"automatic payment has been scheduled|receipt for your payment|^(re: )?receipt"),
    ("statement", r"\bstatement\b|open balance|aging report|account summary"),
    ("invoice", r"\binvoice\b|\bbill is ready|new bill|bill notification|your bill\b|ebill|e-bill"),
]

# Strong filename patterns (attachments).
DOC_FILENAME = [
    ("remittance", r"remittance|receipt|payment[ _-]?confirmation|paid[ _-]invoice"),
    ("statement", r"statement|open[ _-]?balance|aging"),
    ("payment_reminder", r"past[ _-]?due|overdue|final[ _-]?notice|dunning|reminder"),
    ("invoice", r"^(inv|invoice|bill)[ _#-]|[ _-]inv(oice)?[ _#-]?\d|invoice"),
]
# Filenames that look like invoices but are not (seen in this inbox).
DOC_NOT_INVOICE = r"payment terms|credit[ _-]?application|w-?9|coa\b|certificate of analysis"


def dunning_level(text: str):
    for level, pat in DUNNING:
        if re.search(pat, text, re.I):
            return level, pat
    return None, None


def classify_email(subject: str):
    s = (subject or "").strip()
    level, pat = dunning_level(s)
    if level:
        return "payment_reminder", level, f"subject matches /{pat}/"
    for label, pat in EMAIL_SUBJECT:
        if re.search(pat, s, re.I):
            return label, None, f"subject matches /{pat}/"
    return None, None, None


def classify_document(filename: str, text: str):
    f = (filename or "").lower()
    head = (text or "")[:1500].lower()
    if re.search(DOC_NOT_INVOICE, f):
        return None, None, None
    for label, pat in DOC_FILENAME:
        if re.search(pat, f, re.I):
            level = dunning_level(f + " " + head)[0] if label == "payment_reminder" else None
            return label, level, f"filename matches /{pat}/"
    # Strong text signals: document titles and high-volume templates seen in this inbox.
    first = head.strip().split("\n", 1)[0].strip()
    for label, pat, why in TEXT_RULES:
        if re.search(pat, first if pat.startswith("^") else head[:400]):
            return label, None, why
    return None, None, None


TEXT_RULES = [  # (label, regex, evidence). Patterns starting with ^ are matched on the first line only.
    ("other", r"^pro-?forma invoice", "pro-forma invoice (not a bill)"),
    ("invoice", r"^(tax |commercial )?invoice\b(?! & payment terms)", "document title starts with 'invoice'"),
    ("statement", r"^statement\b", "document title is 'statement'"),
    ("invoice", r"order # \d+\s+invoice # \d+", "distributor delivery invoice template (ORDER # / INVOICE #)"),
    ("other", r"certificate of analysis", "certificate of analysis (lab report)"),
    ("other", r"^purchase order\b", "purchase order (issued by the buyer, not a bill)"),
    ("statement", r"\bopen ar\b|aged on:", "open A/R aging report"),
    ("other", r"payment instructions (have|has) changed", "vendor bank-details change notice"),
]


def main():
    db = sqlite3.connect(DB)
    db.executescript("""
    DROP TABLE IF EXISTS classifications;
    CREATE TABLE classifications (item_kind TEXT, item_id TEXT, label TEXT, dunning_level TEXT,
        confidence REAL, decided_by TEXT, evidence TEXT, PRIMARY KEY (item_kind, item_id));
    """)
    n = {"email": [0, 0], "document": [0, 0]}
    for mid, subject in db.execute("SELECT id, subject FROM messages").fetchall():
        label, level, ev = classify_email(subject)
        n["email"][label is not None] += 1
        db.execute("INSERT INTO classifications VALUES ('email',?,?,?,?,?,?)",
                   (mid, label, level, 0.95 if label else None, "rule" if label else None, ev))
    # Documents: one decision per unique content (sha256); duplicates inherit it later.
    rows = db.execute("""SELECT d.file_id, a.filename, d.text, d.extract_status FROM documents d
                         JOIN attachments a USING (file_id) GROUP BY d.file_id""").fetchall()
    for fid, filename, text, status in rows:
        if status in ("unreadable", "empty"):
            label, level, ev = "unknown", None, f"could not read file ({status})"
            conf, by = 0.0, "extract"
        else:
            label, level, ev = classify_document(filename, text)
            conf, by = (0.95, "rule") if label else (None, None)
        n["document"][label is not None] += 1
        db.execute("INSERT INTO classifications VALUES ('document',?,?,?,?,?,?)",
                   (fid, label, level, conf, by, ev))
    db.commit()
    for kind, (undecided, decided) in n.items():
        print(f"{kind}: decided by rules {decided}, left for next stage {undecided}")
    for row in db.execute("SELECT item_kind, label, dunning_level, count(*) FROM classifications "
                          "GROUP BY 1,2,3 ORDER BY 1, 4 DESC"):
        print(row)


if __name__ == "__main__":
    main()
