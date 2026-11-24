"""Gold-set labelling page (local only): python -m eval.label_app

Draws a fixed random sample (100 emails + 100 unique attachments, seed 7) and lets a human label each item
WITHOUT seeing the pipeline's label. For invoices, the pipeline's extracted number/total are then shown to verify.
Answers are saved after every item to eval/gold_labels.csv (resumable). evaluate.py compares them to the pipeline.
"""
import csv
import json
import random
import sqlite3
from pathlib import Path

import gradio as gr

from pipeline.llm import DB, render_item

HERE = Path(__file__).parent
SAMPLE = HERE / "gold_sample.json"
LABELS_CSV = HERE / "gold_labels.csv"
FIELDS = ["item_kind", "item_id", "label", "dunning_level", "invoice_number_ok", "total_ok", "note"]
LABELS = ["invoice", "statement", "payment_reminder", "remittance", "other"]


def sample():
    if SAMPLE.exists():
        return json.loads(SAMPLE.read_text())
    db = sqlite3.connect(DB)
    emails = [r[0] for r in db.execute("SELECT id FROM messages ORDER BY id")]
    docs = [r[0] for r in db.execute("""SELECT min(file_id) FROM documents
                                        WHERE extract_status IN ('ok','ocr') GROUP BY sha256 ORDER BY 1""")]
    rnd = random.Random(7)
    items = [["email", i] for i in rnd.sample(emails, 100)] + [["document", i] for i in rnd.sample(docs, 100)]
    rnd.shuffle(items)
    SAMPLE.write_text(json.dumps(items))
    return items


def done():
    if not LABELS_CSV.exists():
        return {}
    with LABELS_CSV.open() as f:
        return {(r["item_kind"], r["item_id"]): r for r in csv.DictReader(f)}


def next_item():
    d = done()
    items = sample()
    for i, (kind, iid) in enumerate(items):
        if (kind, iid) not in d:
            text = render_item(sqlite3.connect(DB), kind, iid)[0]
            return kind, iid, f"Item {len(d) + 1} of {len(items)} - {kind} `{iid}`", text
    return None, None, f"All {len(items)} items labelled. Run: python -m eval.evaluate", ""


def extracted_fields(kind, iid):
    r = sqlite3.connect(DB).execute(
        "SELECT invoice_number, total_amount FROM invoices WHERE item_kind=? AND item_id=?", (kind, iid)).fetchone()
    return f"Pipeline extracted: invoice number **{r[0]}**, total **{r[1]}**" if r else \
        "Pipeline extracted no invoice fields for this item."


def save(kind, iid, label, level, num_ok, total_ok, note):
    if not kind or not label:
        return (kind, iid, *next_item()[2:], "Pick a label first.")
    new = not LABELS_CSV.exists()
    with LABELS_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow({"item_kind": kind, "item_id": iid, "label": label,
                    "dunning_level": level if label == "payment_reminder" else "",
                    "invoice_number_ok": num_ok if label == "invoice" else "",
                    "total_ok": total_ok if label == "invoice" else "", "note": note})
    k, i, header, text = next_item()
    return k, i, header, text, "Saved."


with gr.Blocks(title="Gold set labelling") as demo:
    kind, iid = gr.State(), gr.State()
    header = gr.Markdown()
    text = gr.Textbox(lines=22, max_lines=22, label="Item as the pipeline saw it", interactive=False)
    label = gr.Radio(LABELS, label="What is it?")
    level = gr.Radio(["reminder", "escalation", "final_notice"], label="If payment_reminder: how far did they go?")
    fields = gr.Markdown()
    with gr.Row():
        num_ok = gr.Radio(["yes", "no", "n/a"], label="If invoice: extracted number correct?")
        total_ok = gr.Radio(["yes", "no", "n/a"], label="If invoice: extracted total correct?")
    note = gr.Textbox(label="Note (optional)")
    status = gr.Markdown()
    btn = gr.Button("Save & next", variant="primary")
    label.change(lambda lab, k, i: extracted_fields(k, i) if lab == "invoice" else "", [label, kind, iid], fields)
    btn.click(save, [kind, iid, label, level, num_ok, total_ok, note], [kind, iid, header, text, status]).then(
        lambda: (None, None, None, None, "", ""), None, [label, level, num_ok, total_ok, note, fields])
    demo.load(lambda: next_item(), None, [kind, iid, header, text])

if __name__ == "__main__":
    demo.launch()
