---
name: invoice-lookup
description: How to find, total and verify invoices and their extracted fields.
---
# Invoice lookup

- `invoices` has one row per unique invoice (vendor + invoice number); `occurrences` = how many copies arrived.
- Fields come from the LLM or the Nabis template parser. `checks` lists automatic verification results:
  `ok`, `invoice number not found verbatim in text`, `total not found verbatim in text`, `no total`,
  `due date before invoice date`, `conflicting totals across copies`. Mention any non-ok check when you use that row.
- Totals: `SELECT round(sum(total_amount),2), count(*) FROM invoices WHERE ...`; always also report how many rows
  had a NULL total (they are excluded from the sum).
- Due dates are often absent (only terms like "Net 60" printed); the pipeline never computes dates. Say so.
- To verify one invoice, open its source: `source_item` is `document:<file_id>` (use get_document) or `email:<id>`.
- Vendor names: use `lower(vendor) LIKE '%keyword%'`; distributors (Nabis, Kiva) and brands can both appear.
