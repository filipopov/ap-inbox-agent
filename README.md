# AP Inbox Agent

An AI agent over one month of an accounts-payable inbox (5,705 emails, 24 Aug – 30 Sep 2026, and the 8,554 files
attached to them). It:

- **classifies** every email and attachment: invoice, statement, payment reminder, remittance or other;
- **extracts** the key fields of every invoice (vendor, number, dates, total, currency, PO);
- finds **vendors who chase payment**, how far they went (reminder → escalation → final notice) and whether the
  invoices they chase are actually in the inbox;
- **answers questions** in a web chat (and CLI / MCP);
- **never fails silently**: unreadable or missing files, low confidence and unprocessed items are recorded and
  reported, and accuracy is measured against a hand-checked gold set.

Built to run for **$0**: local processing + free Gemini and Groq tiers + free Hugging Face hosting.

## How it works (one picture)

```
 OFFLINE, once (on a laptop)                                              ONLINE (Hugging Face Space)
 ───────────────────────────                                              ───────────────────────────
 ap_inbox.sql ─┐                                                           user question
 attachments ──┴► 1 ingest ─► 2 extract text ─► 3 classify (cascade) ─►     │
                    link       PDF/OCR/xlsx      a rules (free)              ▼
                    files      status per file   b LLM sample → c classifier  chat agent (LLM + tools)
                                                 d LLM: unsure + fields     run_sql · get_email · get_document
                               ─► 4 analyse (vendors, chases, matching)     search · load_skill · data_quality
                               ─► 5 evaluate (gold set → accuracy)            │
                               ─► 6 app.db  ─────────────────────────────►  read-only SQLite
```

Full explanation, design decisions and trade-offs: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Repository layout

| Path | What |
|---|---|
| `pipeline/` | Offline processing, steps 1–6 (`ingest`, `extract`, `rules`, `stage_llm` + `llm`, `templates`, `classifier`, `analyse`, `build_app_db`) |
| `prompts/classify_extract.md` | The one prompt used for LLM classification + invoice extraction |
| `eval/` | Gold-set labelling page, gold labels, accuracy evaluation |
| `agent/AGENTS.md` | Agent persona, rules and database schema (its system prompt) |
| `agent/skills/*/SKILL.md` | Playbooks the agent loads on demand: payment chasing, invoice lookup, data quality |
| `agent/tools.py` | The agent's read-only tools |
| `agent/agent.py` | Tool-calling loop with free-tier model fallback |
| `agent/mcp_server.py` | Same tools as an MCP server |
| `app.py` | Web chat (Gradio) – the Hugging Face Space entry point |

## Run it

Requirements: Python 3.11+, `tesseract` (for OCR, e.g. `brew install tesseract`), free API keys
(see `.env.example`): `GEMINI_API_KEY` (pipeline + chat) and `GROQ_API_KEY` (chat fallback).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-pipeline.txt
export GEMINI_API_KEY=... GROQ_API_KEY=...

# put the inputs in data/raw/: ap_inbox.sql and the unzipped attachments/ folder
python -m pipeline.ingest                 # 1  load + link emails and files
python -m pipeline.extract                # 2  text from every file (OCR for scans)
python -m pipeline.rules                  # 3a rules
python -m pipeline.templates              # 3a' Nabis invoice template parser
python -m pipeline.stage_llm sample 600   # 3b LLM labels a random sample (classifier training data)
python -m pipeline.classifier             # 3c classifier for attachments
python -m pipeline.stage_llm rest         # 3d LLM for the rest; resumable - re-run if the daily free quota stops it
python -m pipeline.analyse                # 4  invoices, vendors, chases
python -m eval.label_app                  # 5  label the gold set in the browser (one-off, ~1h)
python -m eval.evaluate                   # 5  accuracy
python -m pipeline.build_app_db           # 6  app/app.db

python app.py                             # web chat on http://127.0.0.1:7860
python -m agent.cli                       # terminal chat
python -m agent.mcp_server                # MCP server (stdio) for Claude Desktop / Claude Code
```

The data itself (`data/`, `app/app.db`) is not in this repository.
