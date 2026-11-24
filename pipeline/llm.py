"""LLM client: sends batches of items to Gemini with a fixed prompt + JSON schema, caches every answer.

- Structured output: the response is forced into RESULT_SCHEMA, then validated per item.
- Resumable: answers are stored in llm_results keyed by (item_kind, item_id); re-running skips done items.
- Never silent: a batch that fails, or an item missing from the answer, is recorded in llm_errors.
- Free-tier aware: on a daily-quota 429 the run stops cleanly and tells you to resume later.
"""
import json
import os
import re
import sqlite3
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data/ap.db"
MODEL = os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite")
PROMPT = (ROOT / "prompts/classify_extract.md").read_text()
MAX_CHARS = {"email": 2500, "document": 5000}  # per item; truncation is flagged on the item
LABELS = ["invoice", "statement", "payment_reminder", "remittance", "other"]

RESULT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "label": {"type": "string", "enum": LABELS},
            "dunning_level": {"type": "string", "enum": ["reminder", "escalation", "final_notice"], "nullable": True},
            "confidence": {"type": "number"},
            "evidence": {"type": "string"},
            "vendor": {"type": "string", "nullable": True},
            "invoice": {
                "type": "object", "nullable": True,
                "properties": {
                    "invoice_number": {"type": "string", "nullable": True},
                    "invoice_date": {"type": "string", "nullable": True},
                    "due_date": {"type": "string", "nullable": True},
                    "total_amount": {"type": "number", "nullable": True},
                    "currency": {"type": "string", "nullable": True},
                    "po_number": {"type": "string", "nullable": True},
                },
            },
            "referenced_invoice_numbers": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "label", "confidence", "evidence", "referenced_invoice_numbers"],
    },
}


class DailyQuotaExhausted(Exception):
    pass


def init_tables(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS llm_results (item_kind TEXT, item_id TEXT, task TEXT, model TEXT,
        truncated INTEGER, result TEXT, created_at REAL, PRIMARY KEY (item_kind, item_id));
    CREATE TABLE IF NOT EXISTS llm_errors (item_kind TEXT, item_id TEXT, task TEXT, error TEXT, created_at REAL);
    """)


def render_item(db, kind, item_id):
    """Text the model sees for one item, plus whether it was truncated."""
    if kind == "email":
        subj, frm, body = db.execute(
            "SELECT subject, from_name || ' <' || from_email || '>', body_text FROM messages WHERE id=?",
            (item_id,)).fetchone()
        atts = [r[0] for r in db.execute(
            "SELECT filename FROM attachments WHERE message_id=? AND NOT is_inline", (item_id,))]
        body = re.sub(r"\n{3,}", "\n\n", body or "")
        text = f"EMAIL\nSubject: {subj}\nFrom: {frm}\nAttachments: {atts}\nBody:\n{body}"
    else:
        name, body = db.execute(
            "SELECT a.filename, d.text FROM documents d JOIN attachments a USING (file_id) WHERE d.file_id=?",
            (item_id,)).fetchone()
        text = f"DOCUMENT\nFilename: {name}\nText:\n{re.sub(r'[ \t]+', ' ', body or '')}"
    limit = MAX_CHARS[kind]
    return text[:limit], len(text) > limit


def _call(client, payload, model):
    for attempt in range(6):
        try:
            r = client.models.generate_content(
                model=model, contents=payload,
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT, temperature=0,
                    response_mime_type="application/json", response_schema=RESULT_SCHEMA))
            return json.loads(r.text)
        except errors.ClientError as e:
            if e.code == 429:
                msg = str(e)
                if "PerDay" in msg or "per day" in msg.lower():
                    raise DailyQuotaExhausted(msg[:300])
                wait = float((re.search(r"retry in ([\d.]+)s", msg) or [None, 30])[1])
                time.sleep(wait + 1)
                continue
            raise
        except (errors.ServerError, json.JSONDecodeError):
            time.sleep(2 ** attempt * 5)
    raise RuntimeError("gave up after 6 attempts (server errors / invalid JSON)")


def run(items, task, model=MODEL, batch_size=25):
    """items: list of (kind, item_id). Sends only those without a cached answer."""
    db = sqlite3.connect(DB, timeout=30)
    init_tables(db)
    done = set(db.execute("SELECT item_kind, item_id FROM llm_results"))
    todo = [i for i in items if i not in done]
    print(f"[{task}] {len(items)} items, {len(todo)} not yet processed, model {model}")
    client = genai.Client(http_options=types.HttpOptions(api_version="v1beta"))
    for start in range(0, len(todo), batch_size):
        batch = todo[start:start + batch_size]
        rendered = {}
        for kind, iid in batch:
            rendered[iid] = (kind, *render_item(db, kind, iid))
        payload = "\n\n".join(f"### ITEM id={iid}\n{text}" for iid, (_, text, _) in rendered.items())
        try:
            answer = _call(client, payload, model)
        except DailyQuotaExhausted as e:
            print(f"Daily free quota reached - stopping. Re-run the same command tomorrow to resume.\n{e}")
            return False
        except Exception as e:  # recorded per item; the run continues with the next batch
            for kind, iid in batch:
                db.execute("INSERT INTO llm_errors VALUES (?,?,?,?,?)", (kind, iid, task, str(e)[:500], time.time()))
            db.commit()
            continue
        by_id = {a.get("id"): a for a in answer if isinstance(a, dict)}
        for iid, (kind, _, truncated) in rendered.items():
            a = by_id.get(iid)
            if a is None:
                db.execute("INSERT INTO llm_errors VALUES (?,?,?,?,?)",
                           (kind, iid, task, "item missing from model answer", time.time()))
                continue
            db.execute("INSERT OR REPLACE INTO llm_results VALUES (?,?,?,?,?,?,?)",
                       (kind, iid, task, model, int(truncated), json.dumps(a), time.time()))
        db.commit()
        print(f"[{task}/{model}] {min(start + batch_size, len(todo))}/{len(todo)}", flush=True)
    return True
