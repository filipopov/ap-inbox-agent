"""Step 4 - Analyse: merge the cascade, build invoices, vendors and payment-chasing tables. Plain code, no AI.

Tables produced:
  final_labels   one row per email / attachment: label, dunning level, confidence, which stage decided
                 (rule | classifier | llm | extract), evidence, and flags (disagreement, truncated, ...)
  invoices       one row per extracted invoice occurrence + automatic sanity checks
  chases         one row per vendor that chases payment: highest dunning level, dates, counts
  chased_invoices one row per invoice number a vendor chases + whether that invoice is in the inbox
"""
import json
import re
import sqlite3
from datetime import date

from pipeline.llm import DB

LEVEL_RANK = {"reminder": 1, "escalation": 2, "final_notice": 3}
SUFFIXES = r"\b(inc|llc|l\.l\.c|co|corp|corporation|company|ltd|limited|lp|llp|dba|the|distribution|dist)\b"


def norm_vendor(name):
    if not name:
        return None
    s = re.sub(r"\(.*?\)", " ", name.lower())
    s = re.sub(SUFFIXES, " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s or None


def norm_invoice_no(n):
    s = re.sub(r"[^A-Za-z0-9]", "", n or "").upper()
    s = re.sub(r"^(INVOICE|INV|NO|NUMBER)+", "", s)
    return s.lstrip("0") or None


def merged_labels(db):
    """Priority: unreadable file > rule > LLM > classifier. Records where stages disagree."""
    llm = {(k, i): json.loads(r) | {"_trunc": t} for k, i, r, t in
           db.execute("SELECT item_kind, item_id, result, truncated FROM llm_results")}
    # documents: share the LLM answer across identical files
    rep = dict(db.execute("SELECT file_id, (SELECT min(file_id) FROM documents d2 WHERE d2.sha256=d.sha256) "
                          "FROM documents d"))
    out = []
    for kind, iid, label, level, conf, by, ev in db.execute("SELECT * FROM classifications").fetchall():
        a = llm.get((kind, rep.get(iid, iid) if kind == "document" else iid))
        flags = []
        if a and a.get("_trunc"):
            flags.append("llm saw truncated text")
        if by == "extract":
            pass
        elif by == "rule":
            if a and a["label"] != label:
                flags.append(f"llm disagrees: {a['label']}")
            if label == "payment_reminder" and a and a.get("dunning_level") and a["dunning_level"] != level:
                flags.append(f"llm level: {a['dunning_level']}")
        elif a:
            if by == "classifier" and a["label"] != label:
                flags.append(f"classifier said: {label}")
            label, level, conf, by, ev = a["label"], a.get("dunning_level"), a["confidence"], "llm", a["evidence"]
        elif label is None:
            label, conf, by, ev = "unknown", 0.0, "none", "not processed yet (LLM quota / error)"
            flags.append("unprocessed")
        if label == "payment_reminder" and not level:
            level = (a or {}).get("dunning_level")
        out.append((kind, iid, label, level, conf, by, ev, "; ".join(flags) or None,
                    (a or {}).get("vendor")))
    return out, llm, rep


def main():
    db = sqlite3.connect(DB, timeout=60)
    rows, llm, rep = merged_labels(db)
    db.executescript("""
    DROP TABLE IF EXISTS final_labels; DROP TABLE IF EXISTS invoices;
    DROP TABLE IF EXISTS chases; DROP TABLE IF EXISTS chased_invoices;
    CREATE TABLE final_labels (item_kind TEXT, item_id TEXT, label TEXT, dunning_level TEXT, confidence REAL,
        decided_by TEXT, evidence TEXT, flags TEXT, vendor TEXT, vendor_key TEXT, message_id TEXT, sent_at TEXT);
    CREATE TABLE invoices (item_kind TEXT, item_id TEXT, message_id TEXT, vendor TEXT, vendor_key TEXT,
        invoice_number TEXT, invoice_no_norm TEXT, invoice_date TEXT, due_date TEXT, total_amount REAL,
        currency TEXT, po_number TEXT, confidence REAL, checks TEXT);
    """)
    # message context (for attachments: the first email that carried them)
    msg_of = dict(db.execute("SELECT file_id, min(message_id) FROM attachments WHERE message_id IS NOT NULL GROUP BY 1"))
    sent = dict(db.execute("SELECT id, sent_at FROM messages"))
    sender = dict(db.execute("SELECT id, from_name FROM messages WHERE is_inbound"))
    for kind, iid, label, level, conf, by, ev, flags, vendor in rows:
        mid = iid if kind == "email" else msg_of.get(iid)
        if not vendor and label != "other" and sender.get(mid):
            vendor = sender[mid]  # fallback: the email sender's display name
            flags = "; ".join(filter(None, [flags, "vendor taken from email sender"]))
        db.execute("INSERT INTO final_labels VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (kind, iid, label, level, conf, by, ev, flags, vendor, norm_vendor(vendor), mid, sent.get(mid)))

    # invoices with sanity checks against the source text
    texts = dict(db.execute("SELECT file_id, text FROM documents"))
    texts.update(db.execute("SELECT id, coalesce(subject,'') || ' ' || coalesce(body_text,'') FROM messages"))
    for kind, iid, label, *_ in rows:
        a = llm.get((kind, rep.get(iid, iid) if kind == "document" else iid))
        if label != "invoice" or not a or not a.get("invoice"):
            continue
        inv, src = a["invoice"], texts.get(iid) or ""
        compact = re.sub(r"[\s,$]", "", src)
        checks = []
        if not inv.get("invoice_number"):
            checks.append("no invoice number")
        elif re.sub(r"\s", "", inv["invoice_number"]) not in re.sub(r"\s", "", src):
            checks.append("invoice number not found verbatim in text")
        amt = inv.get("total_amount")
        if amt is None:
            checks.append("no total")
        elif f"{amt:.2f}" not in compact and f"{amt:g}" not in compact:
            checks.append("total not found verbatim in text")
        for f in ("invoice_date", "due_date"):
            if inv.get(f):
                try:
                    date.fromisoformat(inv[f])
                except ValueError:
                    checks.append(f"{f} not a valid date")
        if inv.get("invoice_date") and inv.get("due_date") and inv["due_date"] < inv["invoice_date"]:
            checks.append("due date before invoice date")
        db.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            kind, iid, iid if kind == "email" else msg_of.get(iid), a.get("vendor"), norm_vendor(a.get("vendor")),
            inv.get("invoice_number"), norm_invoice_no(inv.get("invoice_number")), inv.get("invoice_date"),
            inv.get("due_date"), amt, inv.get("currency"), inv.get("po_number"), a["confidence"],
            "; ".join(checks) or "ok"))

    # payment chasing: reminders grouped by vendor, chased invoice numbers matched to the inbox
    known = {}
    for no, vk in db.execute("SELECT invoice_no_norm, vendor_key FROM invoices WHERE invoice_no_norm IS NOT NULL"):
        known.setdefault(no, set()).add(vk)
        base = re.sub(r"(?<=\d)[A-Z]$", "", no)  # Nabis: invoice 971102-A is chased as "971102"
        if base != no:
            known.setdefault(base, set()).add(vk)
    statement_refs = {}
    for kind, iid, label, *_ in rows:
        a = llm.get((kind, rep.get(iid, iid) if kind == "document" else iid))
        if a and label in ("statement", "remittance"):
            for n in a.get("referenced_invoice_numbers") or []:
                statement_refs.setdefault(norm_invoice_no(n), set()).add(label)
    db.executescript("""
    CREATE TABLE chased_invoices (vendor_key TEXT, vendor TEXT, invoice_number TEXT, invoice_no_norm TEXT,
        highest_level TEXT, first_chased TEXT, last_chased TEXT, times_chased INTEGER, in_inbox TEXT,
        source_items TEXT);
    """)
    chased = {}
    reminders = db.execute("""SELECT item_kind, item_id, vendor, vendor_key, dunning_level, sent_at
                              FROM final_labels WHERE label='payment_reminder'""").fetchall()
    for kind, iid, vendor, vk, level, sent_at in reminders:
        a = llm.get((kind, rep.get(iid, iid) if kind == "document" else iid)) or {}
        nums = a.get("referenced_invoice_numbers") or [None]
        for n in nums:
            key = (vk, norm_invoice_no(n) if n else None)
            c = chased.setdefault(key, {"vendor": vendor, "number": n, "levels": [], "dates": [], "items": []})
            c["levels"].append(level)
            c["dates"].append(sent_at)
            c["items"].append(f"{kind}:{iid}")
    # chases embedded in invoices (e.g. Nabis: "Payment required for previous overdue invoices: ...")
    for (kind, iid), a in llm.items():
        ec = a.get("embedded_chase")
        if not ec:
            continue
        mid = msg_of.get(iid)
        for n in ec["invoice_numbers"]:
            c = chased.setdefault((norm_vendor(ec["chaser"]), norm_invoice_no(n)),
                                  {"vendor": ec["chaser"], "number": n, "levels": [], "dates": [], "items": []})
            c["levels"].append(ec["level"])
            c["dates"].append(sent.get(mid))
            c["items"].append(f"{kind}:{iid}")
    for (vk, no), c in chased.items():
        if no is None:
            status = "no invoice number given in reminder"
        elif no in known and vk in known[no]:
            status = "yes"
        elif no in known:
            status = "yes (filed under a different vendor name)"
        elif no in statement_refs:
            status = "only listed on a statement/remittance, invoice itself not in inbox"
        else:
            status = "no"
        lv = max((l for l in c["levels"] if l), key=LEVEL_RANK.get, default=None)
        ds = sorted(d for d in c["dates"] if d)
        db.execute("INSERT INTO chased_invoices VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (vk, c["vendor"], c["number"], no, lv, ds[0] if ds else None, ds[-1] if ds else None,
                    len(c["items"]), status, ",".join(c["items"])))
    db.executescript("""
    CREATE TABLE chases AS
    SELECT vendor_key, max(vendor) AS vendor,
           CASE max(CASE highest_level WHEN 'final_notice' THEN 3 WHEN 'escalation' THEN 2 WHEN 'reminder' THEN 1 ELSE 0 END)
                WHEN 3 THEN 'final_notice' WHEN 2 THEN 'escalation' WHEN 1 THEN 'reminder' ELSE 'unknown' END AS highest_level,
           count(invoice_number) AS invoices_chased,
           sum(in_inbox = 'yes' OR in_inbox LIKE 'yes %') AS chased_invoices_in_inbox,
           sum(in_inbox NOT LIKE 'yes%' AND invoice_number IS NOT NULL) AS chased_invoices_missing,
           min(first_chased) AS first_chased, max(last_chased) AS last_chased
    FROM chased_invoices GROUP BY vendor_key;
    ALTER TABLE chases ADD COLUMN chase_messages INTEGER;
    """)
    # number of distinct reminder emails/files per vendor (a reminder may name 0..n invoices)
    msgs = {}
    for (vk, _), c in chased.items():
        msgs.setdefault(vk, set()).update(c["items"])
    for vk, items in msgs.items():
        db.execute("UPDATE chases SET chase_messages=? WHERE vendor_key IS ?", (len(items), vk))
    db.commit()
    print(db.execute("SELECT count(*) FROM invoices").fetchone()[0], "invoice occurrences,",
          db.execute("SELECT count(*) FROM chases").fetchone()[0], "chasing vendors,",
          db.execute("SELECT count(*) FROM chased_invoices").fetchone()[0], "chased invoice refs")
    for r in db.execute("SELECT decided_by, count(*) FROM final_labels GROUP BY 1"):
        print("decided by", r)


if __name__ == "__main__":
    main()
