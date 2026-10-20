# demo_db.py
# Saves one clean invoice, queues one broken one, then tries to save the clean one again.
# Invoice values come from data/labels.json (what's printed on the page), not from the model.
import json
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from pipeline.db import engine, suppliers, invoices, lines, audit, save_invoice, queue_for_review
from pipeline.schema import Invoice
from pipeline.validate import validate

labels = json.loads(Path("data/labels.json").read_text())
with engine.connect() as conn:
    known = {r.gstin for r in conn.execute(select(suppliers))}

def load(kind):
    name = next(n for n, l in sorted(labels.items()) if l["broken"] == kind and n.endswith(".pdf"))
    return name, Invoice(**{k: v for k, v in labels[name].items() if k != "broken"})

clean_name, clean = load(None)
save_invoice(clean, clean_name)
print(f"Saved {clean_name}: {clean.invoice_number}, total {clean.total_amount}")

broken_name, broken = load("line_math")
problems = validate(broken, known, seen=set())
queue_for_review(broken, problems, broken_name)
print(f"Sent {broken_name} to review: {len(problems)} problems")

try:
    save_invoice(clean, clean_name + " (resent)")
except IntegrityError as e:
    print(f"Duplicate refused by the database: {e.orig}")

with engine.connect() as conn:
    n_inv = conn.execute(select(func.count()).select_from(invoices)).scalar()
    n_lines = conn.execute(select(func.count()).select_from(lines)).scalar()
    print(f"\ninvoices: {n_inv} row   invoice_lines: {n_lines} rows   (nothing half-saved from the duplicate)")
    print("\naudit_log")
    for r in conn.execute(select(audit).order_by(audit.c.id)):
        print(f"  {r.id}  {r.at:%Y-%m-%d %H:%M:%S}  {r.source_file:<12} {r.action:<15} {r.actor:<9} {r.detail or ''}")
