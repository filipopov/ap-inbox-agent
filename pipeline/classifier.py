"""Step 3c - Small trained classifier: the second, free stage of the cascade.

Model: TF-IDF (words 1-2 grams) + logistic regression, one model per item kind (email / document).
Training labels: rule decisions (step 3a) + LLM labels on a random sample of undecided items (step 3b).
It only decides undecided items where its probability >= THRESHOLD; the rest stay open for the LLM.

Used for DOCUMENTS only: on emails the held-out check showed ~72% agreement with the LLM at any threshold
(emails are too varied for 241 training samples), so undecided emails go straight to the LLM.

It also prints a held-out check (LLM-labelled items it never saw): accuracy and coverage at the threshold,
so the choice of threshold is measured, not guessed.
"""
import json
import sqlite3

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from pipeline.llm import DB, render_item
from pipeline.stage_llm import CLASSIFIER_THRESHOLD as THRESHOLD


def build_model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True),
        LogisticRegression(max_iter=2000, class_weight="balanced", C=4.0))


def main():
    db = sqlite3.connect(DB)
    llm = {(k, i): json.loads(r)["label"] for k, i, r in
           db.execute("SELECT item_kind, item_id, result FROM llm_results WHERE task='train_sample'")}
    for kind in ("document",):
        rule_rows = db.execute("SELECT item_id, label FROM classifications WHERE item_kind=? AND decided_by='rule'",
                               (kind,)).fetchall()
        llm_rows = [(i, lab) for (k, i), lab in llm.items() if k == kind]
        if len(llm_rows) < 30:
            print(f"{kind}: only {len(llm_rows)} LLM-labelled samples - skipping classifier")
            continue
        text = lambda iid: render_item(db, kind, iid)[0]

        # held-out check on LLM-labelled items (the hard, undecided kind of item)
        llm_train, llm_test = train_test_split(llm_rows, test_size=0.3, random_state=42)
        m = build_model().fit([text(i) for i, _ in rule_rows + llm_train], [l for _, l in rule_rows + llm_train])
        probs = m.predict_proba([text(i) for i, _ in llm_test])
        preds = m.classes_[probs.argmax(1)]
        sure = probs.max(1) >= THRESHOLD
        gold = [l for _, l in llm_test]
        acc_sure = sum(p == g for p, g, s in zip(preds, gold, sure) if s) / max(sure.sum(), 1)
        print(f"{kind}: held-out {len(llm_test)} items -> covers {sure.mean():.0%} at p>={THRESHOLD}, "
              f"agreement with LLM there {acc_sure:.0%} (overall {sum(p == g for p, g in zip(preds, gold)) / len(gold):.0%})")

        # final model on all labels, applied to items nobody has decided yet
        m = build_model().fit([text(i) for i, _ in rule_rows + llm_rows], [l for _, l in rule_rows + llm_rows])
        open_ids = [r[0] for r in db.execute(
            "SELECT item_id FROM classifications WHERE item_kind=? AND label IS NULL", (kind,))]
        if not open_ids:
            continue
        probs = m.predict_proba([text(i) for i in open_ids])
        decided = 0
        for iid, p in zip(open_ids, probs):
            if p.max() >= THRESHOLD:
                decided += 1
                db.execute("UPDATE classifications SET label=?, confidence=?, decided_by='classifier', evidence=? "
                           "WHERE item_kind=? AND item_id=?",
                           (m.classes_[p.argmax()], float(p.max()), f"classifier p={p.max():.2f}", kind, iid))
        db.commit()
        print(f"{kind}: classifier decided {decided} of {len(open_ids)} open items")


if __name__ == "__main__":
    main()
