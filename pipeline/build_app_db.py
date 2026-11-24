"""Step 6 - Build app/app.db: the small, read-only database the chat agent queries (and that gets deployed).

Contains only results + text needed to answer questions; no raw dump, no attachment binaries.
Invoices are de-duplicated: the same invoice number from the same vendor seen in several emails/files is one row
(`occurrences` counts how often it was received).
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/ap.db"
OUT = ROOT / "app/app.db"


def main():
    OUT.parent.mkdir(exist_ok=True)
    OUT.unlink(missing_ok=True)
    db = sqlite3.connect(OUT)
    db.execute(f"ATTACH '{SRC}' AS src")
    db.executescript("""
    CREATE TABLE emails AS
    SELECT m.id AS email_id, m.sent_at, m.is_inbound, m.from_name, m.from_email, m.subject,
           f.label, f.dunning_level, round(f.confidence, 2) AS confidence, f.decided_by, f.vendor, f.flags,
           (SELECT count(*) FROM src.attachments a WHERE a.message_id = m.id AND NOT a.is_inline) AS n_attachments
    FROM src.messages m LEFT JOIN src.final_labels f ON f.item_kind = 'email' AND f.item_id = m.id;

    CREATE TABLE attachments AS
    SELECT a.file_id, a.message_id AS email_id, a.filename, a.content_type, a.is_inline,
           a.file_status, d.extract_status, d.extract_note, d.page_count,
           f.label, f.dunning_level, round(f.confidence, 2) AS confidence, f.decided_by, f.vendor, f.flags
    FROM src.attachments a
    LEFT JOIN src.documents d USING (file_id)
    LEFT JOIN src.final_labels f ON f.item_kind = 'document' AND f.item_id = a.file_id;

    CREATE TABLE invoices AS
    SELECT max(vendor) AS vendor, max(invoice_number) AS invoice_number, max(invoice_date) AS invoice_date,
           max(due_date) AS due_date, max(total_amount) AS total_amount, max(currency) AS currency,
           max(po_number) AS po_number, round(min(confidence), 2) AS confidence,
           CASE WHEN count(DISTINCT total_amount) > 1 THEN 'conflicting totals across copies; ' ELSE '' END
             || group_concat(DISTINCT checks) AS checks,
           count(*) AS occurrences, min(item_kind || ':' || item_id) AS source_item,
           group_concat(DISTINCT message_id) AS email_ids
    FROM src.invoices
    GROUP BY vendor_key, coalesce(invoice_no_norm, item_kind || item_id);

    CREATE TABLE problem_files AS
    SELECT file_id, email_id, filename,
           CASE WHEN file_status = 'missing' THEN 'missing from export' ELSE 'could not read: ' || extract_status END AS problem,
           coalesce(extract_note, content_type) AS detail
    FROM attachments
    WHERE extract_status IN ('unreadable', 'empty', 'unsupported') OR (file_status = 'missing' AND NOT is_inline);

    CREATE TABLE chases AS SELECT coalesce(vendor, '(vendor unknown)') AS vendor, highest_level, chase_messages, invoices_chased, chased_invoices_in_inbox,
           chased_invoices_missing, first_chased, last_chased FROM src.chases;
    CREATE TABLE chased_invoices AS SELECT coalesce(vendor, '(vendor unknown)') AS vendor, invoice_number, highest_level, first_chased, last_chased,
           times_chased, in_inbox, source_items FROM src.chased_invoices;

    CREATE TABLE email_bodies AS SELECT id AS email_id, body_text FROM src.messages;
    CREATE TABLE document_texts AS SELECT file_id, text FROM src.documents;

    CREATE VIRTUAL TABLE search USING fts5(kind, id, title, body, tokenize = 'porter unicode61');
    INSERT INTO search SELECT 'email', id, subject, body_text FROM src.messages;
    INSERT INTO search SELECT 'document', d.file_id, a.filename, d.text
      FROM src.documents d JOIN src.attachments a USING (file_id) GROUP BY d.file_id;
    """)
    if db.execute("SELECT count(*) FROM src.sqlite_master WHERE name='accuracy'").fetchone()[0]:
        db.execute("CREATE TABLE accuracy AS SELECT * FROM src.accuracy")
    db.commit()
    db.execute("DETACH src")
    db.execute("VACUUM")
    db.close()
    print(f"{OUT} {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
