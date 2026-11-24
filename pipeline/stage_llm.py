"""Step 3b/3d - which items go to the LLM.

  python pipeline/stage_llm.py sample [N]  -> label a random sample of items the rules left undecided
                                            (training data for the classifier, step 3c)
  python pipeline/stage_llm.py rest        -> (after the classifier) everything that still needs the LLM:
       * items the classifier is unsure about (confidence < CLASSIFIER_THRESHOLD)
       * every invoice (to extract its fields)
       * every payment_reminder / statement / remittance (vendor + which invoices they reference)

Documents are sent once per unique content (sha256); duplicates inherit the answer.
"""
import os
import random
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import sys

from pipeline.llm import DB, run

CLASSIFIER_THRESHOLD = 0.85


def unique_docs_sql(where):
    # one representative file_id per identical content
    return f"""SELECT 'document', min(d.file_id) FROM documents d
               JOIN classifications c ON c.item_kind='document' AND c.item_id=d.file_id
               WHERE {where} GROUP BY d.sha256"""


def main():
    db = sqlite3.connect(DB)
    mode = sys.argv[1]
    if mode == "sample":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
        undecided = db.execute("SELECT 'email', item_id FROM classifications WHERE item_kind='email' AND label IS NULL").fetchall()
        undecided += db.execute(unique_docs_sql("c.label IS NULL")).fetchall()
        random.Random(42).shuffle(undecided)
        ok = run([tuple(x) for x in undecided[:n]], "train_sample")
    elif mode == "rest":
        need = f"c.label IS NULL OR c.confidence < {CLASSIFIER_THRESHOLD} OR c.label IN ('invoice','payment_reminder','statement','remittance')"
        # an invoice email whose attachment is itself an invoice adds nothing: fields come from the attachment
        has_invoice_doc = """EXISTS (SELECT 1 FROM attachments a JOIN classifications ca
                             ON ca.item_kind='document' AND ca.item_id=a.file_id
                             WHERE a.message_id=c.item_id AND ca.label='invoice')"""
        items = db.execute(f"""SELECT 'email', item_id FROM classifications c WHERE item_kind='email' AND ({need})
                               AND NOT (c.label IS 'invoice' AND {has_invoice_doc})""").fetchall()
        items += db.execute(unique_docs_sql(f"c.decided_by IS NOT 'extract' AND ({need})")).fetchall()
        # free-tier quotas are per model, so split the work across several models in parallel
        models = os.environ.get("LLM_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",")
        items = [tuple(x) for x in items]
        with ThreadPoolExecutor(len(models)) as pool:
            ok = all(pool.map(lambda i: run(items[i::len(models)], "label_extract", models[i]), range(len(models))))
    else:
        sys.exit(__doc__)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
