# Architecture

## 1. The problem in one paragraph

An accounts-payable (AP) inbox receives invoices, statements, payment reminders and payment confirmations from
hundreds of vendors, mixed with noise (marketing, delivery notices, lab certificates). We have a one-month export
(a Front helpdesk Postgres dump + a zip of 8,554 attachments). We need to know what every item is, the fields of
every invoice, who is chasing us for money and how hard, whether we even have the invoices they chase, and be
able to ask questions about all of it – while being honest about what could not be read or is uncertain.

## 2. The key design decision: extract first, then query

The standard way to build this (document processing / "intelligent document processing") is two phases:

1. **Offline, once:** read every email and file and store structured results (labels, invoice fields, chases) in
   a database.
2. **Online:** a chat agent answers questions by querying that database with tools.

Why not let the chat model read files when asked? Counting and totalling questions ("how many invoices",
"total overdue") need every item processed; doing that per question would be slow, expensive and inconsistent.
Why not RAG (embedding search) only? Same reason: retrieval finds similar text, it cannot count or sum reliably,
and its accuracy is hard to measure. We still add full-text search for "find me anything about X" questions.

The inbox is a fixed snapshot, so the offline phase runs once. New mail would only process the new items.

## 3. Offline pipeline (`pipeline/`)

### Step 1 – Ingest (`ingest.py`)
- Parses the plain-SQL dump directly (Postgres `COPY` blocks are tab-separated text), so no Postgres server is
  needed. Loads raw tables, then a clean `messages` table.
- Each message has an `attachments` JSON list with file ids (`fil_…`); every file in the zip is named
  `fil_<id>__<name>`, so files are linked by id.
- **Findings:** all 8,554 files are referenced; 1,349 referenced attachments are not in the zip – 1,267 are inline
  images (logos, signatures) and **82 are real missing attachments** (75 images, 3 forwarded emails, 3 HTML, 1 calendar).
  Every one is recorded with `file_status = missing`.

### Step 2 – Extract text (`extract.py`)
- PDFs: text layer via PyMuPDF; a page with < 25 characters is treated as a scan and read with **Tesseract OCR**
  (first 5 pages; files with more pages get a note). Also xlsx, docx, csv/txt/ics/html, nested zips, images.
- Every file gets an explicit `extract_status`: `ok`, `ocr`, `empty`, `unreadable`, `unsupported`, plus a reason.
- Files are fingerprinted with SHA-256: 8,554 files are only **5,662 unique contents**, so duplicates are processed once.
- **Result:** 8,543 of 8,554 read (2,686 via OCR); 11 not readable, all explained (9 password-protected, 2 blank scans).

### Step 3 – Classify and extract: a cascade
Industry practice for cost and reliability: cheap, predictable methods first; the expensive model only for what
is left. Every decision records **which stage made it** and its **evidence**.

| Stage | What | Cost | Notes |
|---|---|---|---|
| 3a Rules (`rules.py`) | Regexes on subject lines and filenames (vendor billing systems are very regular), plus a few document-title / template patterns | free, instant | Only fires on strong patterns; otherwise leaves the item undecided |
| 3a' Template (`templates.py`) | Exact parser for the biggest invoice layout (Nabis delivery invoices, ~1,000 files) | free, instant | Accepts a file only if every field matches; also captures embedded dunning ("Payment required for previous overdue invoices…", "Must pay previous balance prior to delivery") |
| 3b LLM sample (`stage_llm.py sample`) | Gemini labels a random 600 undecided items | free tier | Training data for 3c |
| 3c Classifier (`classifier.py`) | TF-IDF + logistic regression, trained on rule labels + LLM sample | free, seconds | **Used for attachments only**: held-out agreement with the LLM 96% at 90% coverage. On emails it reached only ~72% at any threshold, so emails skip it (measured, not assumed) |
| 3d LLM (`stage_llm.py rest`, `llm.py`) | Gemini for: items still unsure, **every invoice's fields**, every reminder/statement/remittance (vendor + which invoices they mention) | free tier | Batches of 25 items, JSON schema-enforced output, resumable, two models in parallel (free quotas are per model) |

**The prompt** (`prompts/classify_extract.md`) defines the labels, the three dunning levels, the fields, and rules
such as "copy values exactly as printed; never compute a value". Output is forced into a JSON schema.

**Free-tier engineering** (`llm.py`): answers are cached per item, so re-running continues where it stopped;
a daily-quota error stops the run cleanly; a failed batch is written to `llm_errors` and retried on the next run;
an item missing from a model answer is also recorded. Text longer than the per-item limit is truncated **and flagged**.

### Step 4 – Analyse (`analyse.py`) – plain code, no AI
- **Merge** the cascade into `final_labels`. Priority: unreadable file > rule > LLM > classifier. Where two stages
  disagree (e.g. rule said invoice, LLM said statement), the item gets a flag – an honest uncertainty signal.
- **Invoices** with automatic checks against the source text: invoice number and total must appear verbatim, dates must
  be valid and due ≥ invoice date. Any failing check is stored with the invoice.
- **Vendors** are normalised (lower-case, punctuation and suffixes like Inc/LLC removed); if the LLM found no vendor, the
  sender's name is used and flagged.
- **Payment chasing:** every reminder (and every Nabis invoice with embedded overdue lists) contributes chased invoice
  numbers. Each chased number is matched against the extracted invoices:
  `yes` / `yes (filed under a different vendor name)` / `only listed on a statement or remittance` / `no` /
  `no invoice number given`. Per vendor: the highest level reached, number of chase messages, chased invoices
  in / not in the inbox, first and last chase date.

### Step 5 – Accuracy (`eval/`)
- A fixed random **gold set** (100 emails + 100 unique attachments, seed 7) is labelled by a human in a small local page
  (`label_app.py`) **without seeing the pipeline's answer**; for invoices the extracted number and total are then
  shown to be verified.
- `evaluate.py` compares and stores metrics in an `accuracy` table: label accuracy overall / per item kind /
  **per cascade stage** / per confidence band, precision and recall for invoices and reminders, dunning-level accuracy,
  invoice number and total correctness – each with a 95% confidence interval (Wilson).
- The agent quotes these numbers when asked "how accurate are you?". If they are missing, it says accuracy has not
  been measured – it never estimates.

### Step 6 – App database (`build_app_db.py`)
A slim read-only SQLite file for the hosted agent: results tables, email bodies and document text, a
`problem_files` table, de-duplicated `invoices`, and an FTS5 full-text index. No raw dump, no binaries.

## 4. Online: the chat agent (`agent/`, `app.py`)

- **Persona and rules:** `agent/AGENTS.md` is the system prompt: answer only from tool results, cite ids, never
  count rows by eye (numbers must come from a query), always surface unreadable/missing/low-confidence items.
- **Tools** (`agent/tools.py`), all read-only:

  | Tool | Purpose |
  |---|---|
  | `run_sql` | One SELECT on the database (SQLite opened in read-only mode). Returns ≤ 50 rows **plus the true total row count**, so the model can't invent totals |
  | `get_email`, `get_document` | Open one item: classification, status, fields, text |
  | `search` | Full-text keyword search over emails and documents |
  | `load_skill` | Load a playbook (`skills/*/SKILL.md`) on demand – keeps the base prompt small |
  | `data_quality_report` | Coverage, unreadable/missing files, unprocessed and low-confidence counts, measured accuracy |

- **Skills:** `payment-chasing`, `invoice-lookup`, `data-quality` – short playbooks with the right queries and caveats.
  Loaded only when needed (progressive disclosure), the same pattern as Claude Agent Skills.
- **Models:** OpenAI-compatible endpoints, so providers are interchangeable. Chain: Gemini 3.1 Flash-Lite → Groq
  gpt-oss-120b → Groq Qwen. Free tiers have per-minute token limits, so on a rate limit the agent waits briefly or
  moves to the next model; when switching models mid-answer, earlier tool steps are passed as text (providers
  reject tool-call history they did not produce). If every model is busy the user gets an explicit message.
  A weaker model (gpt-oss-20b) was removed after it hallucinated in testing.
- **Transparency:** every web answer has a collapsible "How I got this" listing the tool calls and the model used.
- **Interfaces:** web chat (Gradio, hosted on a Hugging Face Space), terminal (`agent/cli.py`), MCP server
  (`agent/mcp_server.py`) exposing the same tools to any MCP client.

## 5. "Never fail silently" – where each guarantee lives

| Situation | Where it is caught | What the user sees |
|---|---|---|
| Attachment missing from export | ingest: `file_status = missing` | `problem_files`, data-quality report |
| File cannot be read (password, blank, unknown format) | extract: `extract_status` + reason | same, and label `unknown` (decided_by `extract`) |
| Scanned file | extract: OCR, status `ocr` | treated as readable, noted |
| Very long document | extract / LLM: page / character limit | flag "llm saw truncated text" |
| LLM batch failed / item missing from answer | `llm_errors`, retried on re-run | items not yet processed show `decided_by = none` |
| Stages disagree | analyse: flag | agent mentions it as uncertain |
| Extracted value not in source text | analyse: invoice `checks` | agent mentions non-ok checks |
| Model unsure | LLM confidence < 0.6 | agent flags low confidence |
| All chat models rate-limited | agent | explicit "rate-limited, retry in a minute" message |
| "How accurate are you?" | eval → `accuracy` table | measured numbers with confidence intervals |

## 6. Cost

Everything runs on free tiers: local CPU for extraction/OCR/rules/classifier; Gemini free tier for the LLM steps
(~6,000 items in batches); Groq + Gemini free tiers for chat; Hugging Face Spaces free CPU for hosting; GitHub.
The price of $0 is time (the LLM pass is rate-limited to roughly an hour or two) and chat rate limits under load.
Switching to a paid model is a configuration change (`LLM_MODELS`, `CHAT_MODELS`).

## 7. Known limitations and next steps

- Free-tier models are weaker than frontier models on messy OCR; the measured accuracy shows where.
- Vendor names are normalised by simple rules; a distributor (Nabis, Kiva) and the brand on the invoice can differ.
- "Not in inbox" means not in this one-month export – the invoice may predate it.
- Due dates are only stored when printed; terms like "Net 60" are not turned into dates.
- Next: incremental processing for new mail, vendor master-data matching, a reviewer queue for low-confidence items.
