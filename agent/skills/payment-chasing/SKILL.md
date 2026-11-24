---
name: payment-chasing
description: How to answer questions about vendors chasing payment, dunning levels and whether chased invoices are in the inbox.
---
# Payment chasing

Data: `chases` (one row per vendor) and `chased_invoices` (one row per invoice number a vendor chased).

- `chase_messages` = number of reminder emails/files (some name no invoice, so invoices_chased can be 0).
- "Who chases us / how far did they go": `SELECT vendor, highest_level, chase_messages, invoices_chased, chased_invoices_in_inbox,
  chased_invoices_missing, first_chased, last_chased FROM chases ORDER BY CASE highest_level WHEN 'final_notice' THEN 3
  WHEN 'escalation' THEN 2 WHEN 'reminder' THEN 1 ELSE 0 END DESC, invoices_chased DESC`.
- Levels: reminder (polite, due/coming due) < escalation (past due, overdue, account on hold, delivery blocked until paid)
  < final_notice (final notice, collections, legal action, service suspension).
- `chased_invoices.in_inbox`:
  - `yes` - the invoice itself was received in this inbox;
  - `yes (filed under a different vendor name)` - found, but extracted vendor name differs (e.g. distributor vs brand);
  - `only listed on a statement/remittance, invoice itself not in inbox`;
  - `no` - we never received that invoice in this month's inbox (it may predate 24 Aug);
  - `no invoice number given in reminder` - the reminder did not name invoices; cannot be matched.
- Chases come from reminder emails/files AND from invoices that embed dunning (Nabis invoices list
  "previous overdue invoices" and may block delivery until paid -> escalation).
- Show evidence: for a vendor, list its chased invoices with source_items (email:<id> / document:<id>) and offer
  `get_email` for the strongest notice.
- Caveat to state: "not in inbox" means not in this one-month export, not that it was never sent.
