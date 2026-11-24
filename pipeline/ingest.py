"""Step 1 - Ingest: load the Postgres dump into SQLite and link attachments to files on disk.

Reads the plain-SQL dump directly (no Postgres server needed): every `COPY ... FROM stdin;`
block is tab-separated text in Postgres' COPY format, which we decode row by row.

Output tables (data/ap.db):
  messages     one row per email
  attachments  one row per attachment reference, with file_status:
               ok | missing (referenced, not in zip) ; orphan files (in zip, never referenced)
               are recorded too so nothing disappears silently.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "data/raw/ap_inbox.sql"
FILES_DIR = ROOT / "data/raw/attachments"
DB = ROOT / "data/ap.db"

COPY_RE = re.compile(r"^COPY (\S+) \((.+)\) FROM stdin;$")
_ESC = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\"}
_ESC_RE = re.compile(r"\\(x[0-9a-fA-F]{1,2}|[0-7]{1,3}|.)")


def _unescape(field: str):
    if field == r"\N":
        return None

    def repl(m):
        s = m.group(1)
        if s in _ESC:
            return _ESC[s]
        if s[0] == "x":
            return chr(int(s[1:], 16))
        if s[0].isdigit():
            return chr(int(s, 8))
        return s

    return _ESC_RE.sub(repl, field)


def read_copy_blocks(path: Path):
    """Yield (table, columns, rows) for every COPY block in the dump."""
    with path.open(encoding="utf-8") as f:
        for line in f:
            m = COPY_RE.match(line.rstrip("\n"))
            if not m:
                continue
            table, cols = m.group(1), [c.strip() for c in m.group(2).split(",")]
            rows = []
            for row in f:
                row = row.rstrip("\n")
                if row == r"\.":
                    break
                fields = row.split("\t")
                if len(fields) != len(cols):
                    raise ValueError(f"{table}: expected {len(cols)} fields, got {len(fields)}")
                rows.append([_unescape(x) for x in fields])
            yield table, cols, rows


def main():
    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)

    # 1. raw tables, 1:1 with the dump (prefixed raw_)
    for table, cols, rows in read_copy_blocks(DUMP):
        name = "raw_" + table.split(".")[-1].replace("frontapp_", "")
        db.execute(f"CREATE TABLE {name} ({', '.join(cols)})")
        db.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})", rows)
        print(f"{name}: {len(rows)} rows")

    # 2. clean messages table
    db.executescript("""
    CREATE TABLE messages AS
    SELECT id, conversation_id, frontapp_message_id, is_inbound = 't' AS is_inbound, event_type,
           subject, recipient_from_name AS from_name, lower(recipient_from_handle) AS from_email,
           recipient_to_handle AS to_email, message_created_at AS sent_at, body_text, attachments
    FROM raw_messages;
    CREATE INDEX ix_msg_from ON messages(from_email);
    """)

    # 3. attachments: one row per reference, linked to the file on disk
    files_on_disk = {p.name.split("__", 1)[0]: p for p in FILES_DIR.iterdir() if p.is_file()}
    db.execute("""CREATE TABLE attachments (
        file_id TEXT, message_id TEXT, filename TEXT, content_type TEXT, size INTEGER,
        is_inline INTEGER, path TEXT, file_status TEXT)""")
    referenced = set()
    for msg_id, att_json in db.execute("SELECT id, attachments FROM messages").fetchall():
        for a in json.loads(att_json or "[]"):
            fid = a["id"]
            referenced.add(fid)
            p = files_on_disk.get(fid)
            db.execute("INSERT INTO attachments VALUES (?,?,?,?,?,?,?,?)", (
                fid, msg_id, a.get("filename"), a.get("content_type"), a.get("size"),
                int(bool((a.get("metadata") or {}).get("is_inline"))),
                str(p.relative_to(ROOT)) if p else None, "ok" if p else "missing"))
    for fid, p in files_on_disk.items():
        if fid not in referenced:
            db.execute("INSERT INTO attachments VALUES (?,?,?,?,?,?,?,?)", (
                fid, None, p.name.split("__", 1)[-1], None, p.stat().st_size, 0,
                str(p.relative_to(ROOT)), "orphan"))
    db.execute("CREATE INDEX ix_att_msg ON attachments(message_id)")
    db.commit()

    for status, n in db.execute("SELECT file_status, count(*) FROM attachments GROUP BY 1"):
        print(f"attachments {status}: {n}")
    print("messages:", db.execute("SELECT count(*) FROM messages").fetchone()[0])


if __name__ == "__main__":
    sys.exit(main())
