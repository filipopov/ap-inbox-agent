"""Tools the chat agent can call. Shared by the chat loop (agent.py) and the MCP server (mcp_server.py).

All tools are read-only. Every result is capped in size (the free Groq tier allows ~8k tokens per minute),
and truncation is always stated in the result so the model can tell the user.
"""
import json
import os
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("APP_DB", ROOT / "app/app.db"))
SKILLS = ROOT / "agent/skills"
MAX_ROWS = 50
MAX_CHARS = 5000


def _db():
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)  # read-only at the SQLite level
    db.row_factory = sqlite3.Row
    return db


def _cap(text, limit=MAX_CHARS):
    return text if len(text) <= limit else text[:limit] + f"\n...[truncated, {len(text) - limit} more chars]"


def run_sql(query: str) -> str:
    """Run one read-only SQL SELECT on the inbox database. Returns up to 50 rows as JSON."""
    q = query.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with)\b", q) or ";" in q:
        return "ERROR: only a single SELECT / WITH query is allowed."
    try:
        with _db() as db:
            rows = db.execute(q).fetchmany(MAX_ROWS + 1)
            total = len(rows) if len(rows) <= MAX_ROWS else \
                db.execute(f"SELECT count(*) FROM ({q})").fetchone()[0]
    except sqlite3.Error as e:
        return f"SQL ERROR: {e}. Check table/column names in the schema."
    out = json.dumps({"total_rows": total, "rows": [dict(r) for r in rows[:MAX_ROWS]]}, default=str)
    note = f"\n[showing {min(total, MAX_ROWS)} of {total} rows - use COUNT/GROUP BY for totals]" if total > MAX_ROWS else ""
    return _cap(out) + note


def get_email(email_id: str) -> str:
    """Show one email: metadata, classification, body (truncated) and its attachments with their status."""
    with _db() as db:
        e = db.execute("SELECT * FROM emails WHERE email_id=?", (email_id,)).fetchone()
        if not e:
            return f"ERROR: no email with id {email_id}"
        body = db.execute("SELECT body_text FROM email_bodies WHERE email_id=?", (email_id,)).fetchone()[0] or ""
        atts = db.execute("""SELECT file_id, filename, file_status, extract_status, label, confidence
                             FROM attachments WHERE email_id=? AND NOT is_inline""", (email_id,)).fetchall()
    return _cap(json.dumps({**dict(e), "attachments": [dict(a) for a in atts]}, default=str)
                + "\nBODY:\n" + re.sub(r"\n{3,}", "\n\n", body), 4000)


def get_document(file_id: str) -> str:
    """Show one attachment: classification, extraction status, extracted invoice fields and text (truncated)."""
    with _db() as db:
        a = db.execute("SELECT * FROM attachments WHERE file_id=?", (file_id,)).fetchone()
        if not a:
            return f"ERROR: no attachment with id {file_id}"
        t = db.execute("SELECT text FROM document_texts WHERE file_id=?", (file_id,)).fetchone()
        inv = db.execute("SELECT * FROM invoices WHERE source_item=?", (f"document:{file_id}",)).fetchone()
    text = (t[0] if t else None) or "[no text: file missing or unreadable - see file_status / extract_status]"
    return _cap(json.dumps({**dict(a), "invoice_fields": dict(inv) if inv else None}, default=str)
                + "\nTEXT:\n" + re.sub(r"[ \t]+", " ", text), 4000)


def search(query: str, kind: str = "any") -> str:
    """Full-text search over email subjects/bodies and attachment filenames/text. kind: email | document | any."""
    terms = " ".join(f'"{w}"' for w in re.findall(r"\w+", query))
    if not terms:
        return "ERROR: empty query"
    sql = "SELECT kind, id, title, snippet(search, 3, '[', ']', '...', 12) AS snippet FROM search WHERE search MATCH ?"
    args = [terms]
    if kind in ("email", "document"):
        sql += " AND kind = ?"
        args.append(kind)
    with _db() as db:
        rows = db.execute(sql + " ORDER BY rank LIMIT 15", args).fetchall()
        total = db.execute("SELECT count(*) FROM search WHERE search MATCH ?", [terms]).fetchone()[0]
    return _cap(json.dumps({"total_matches": total, "top_15": [dict(r) for r in rows]}, default=str))


def load_skill(name: str) -> str:
    """Load a skill (playbook) by name: payment-chasing | invoice-lookup | data-quality."""
    p = SKILLS / name / "SKILL.md"
    return p.read_text() if p.exists() else f"ERROR: unknown skill. Available: {[d.name for d in SKILLS.iterdir()]}"


def data_quality_report() -> str:
    """Coverage, unreadable/missing files, unprocessed and low-confidence items, and measured accuracy."""
    q = {
        "emails_by_label": "SELECT label, count(*) n FROM emails GROUP BY label",
        "decided_by": "SELECT 'email' kind, decided_by, count(*) n FROM emails GROUP BY 2 UNION ALL "
                      "SELECT 'attachment', decided_by, count(*) FROM attachments WHERE NOT is_inline GROUP BY 2",
        "unreadable_files": "SELECT extract_status, extract_note, count(*) n FROM attachments "
                            "WHERE extract_status IN ('unreadable','empty','unsupported') GROUP BY 1,2",
        "missing_files": "SELECT is_inline, content_type, count(*) n FROM attachments WHERE file_status='missing' GROUP BY 1,2",
        "low_confidence_items": "SELECT 'email' kind, count(*) n FROM emails WHERE confidence < 0.6 AND decided_by NOT IN ('none','extract') "
                                "UNION ALL SELECT 'attachment', count(*) FROM attachments WHERE confidence < 0.6 "
                                "AND decided_by NOT IN ('none','extract')",
        "invoice_checks": "SELECT checks, count(*) n FROM invoices GROUP BY 1 ORDER BY 2 DESC LIMIT 8",
    }
    out = {}
    with _db() as db:
        for k, sql in q.items():
            out[k] = [dict(r) for r in db.execute(sql)]
        has_acc = db.execute("SELECT count(*) FROM sqlite_master WHERE name='accuracy'").fetchone()[0]
        out["accuracy"] = [dict(r) for r in db.execute("SELECT * FROM accuracy")] if has_acc else \
            "NOT MEASURED YET - gold set not labelled"
    return _cap(json.dumps(out, default=str), 6000)


TOOLS = {f.__name__: f for f in (run_sql, get_email, get_document, search, load_skill, data_quality_report)}

SCHEMAS = [
    {"type": "function", "function": {"name": "run_sql", "description": run_sql.__doc__,
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_email", "description": get_email.__doc__,
     "parameters": {"type": "object", "properties": {"email_id": {"type": "string"}}, "required": ["email_id"]}}},
    {"type": "function", "function": {"name": "get_document", "description": get_document.__doc__,
     "parameters": {"type": "object", "properties": {"file_id": {"type": "string"}}, "required": ["file_id"]}}},
    {"type": "function", "function": {"name": "search", "description": search.__doc__,
     "parameters": {"type": "object", "properties": {"query": {"type": "string"},
                    "kind": {"type": "string", "enum": ["email", "document", "any"]}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "load_skill", "description": load_skill.__doc__,
     "parameters": {"type": "object", "properties": {"name": {"type": "string",
                    "enum": ["payment-chasing", "invoice-lookup", "data-quality"]}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "data_quality_report", "description": data_quality_report.__doc__,
     "parameters": {"type": "object", "properties": {}}}},
]


def call_tool(name, args_json):
    """Execute a tool call from the model. Errors are returned as text, never raised, so the model can react."""
    if name not in TOOLS:
        return f"ERROR: unknown tool {name}"
    try:
        args = json.loads(args_json or "{}")
        return TOOLS[name](**args)
    except Exception as e:  # reported back to the model (and visible in the UI), not swallowed
        return f"TOOL ERROR ({type(e).__name__}): {e}"
