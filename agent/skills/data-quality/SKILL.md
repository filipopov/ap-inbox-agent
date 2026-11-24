---
name: data-quality
description: How to report accuracy, unreadable/missing files and uncertainty honestly.
---
# Data quality & accuracy

- Call `data_quality_report` first; it returns coverage, unreadable/missing files, unprocessed items, low-confidence
  counts and the measured accuracy table.
- Accuracy is measured on a hand-checked gold set (random sample, labels verified by a human). Quote metric, value
  and sample size n, and mention the confidence interval note if present. If the accuracy table is empty, say accuracy
  has not been measured yet - never estimate it yourself.
- "Which files could not be read / are missing": `SELECT problem, filename, detail, file_id, email_id FROM problem_files`.
  `ocr` files are NOT problems: they were scanned and read with OCR.
- Unreadable = password-protected or blank files. Missing = referenced by an email but absent from the export
  (mostly inline logos; non-inline missing files matter more).
- Low confidence: confidence < 0.6. Flags such as "llm disagrees: X" mean two cascade stages disagreed - treat as uncertain.
