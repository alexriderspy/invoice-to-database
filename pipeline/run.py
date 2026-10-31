# pipeline/run.py
import sys
from pathlib import Path
from sqlalchemy import select
from pipeline.db import engine, suppliers, invoices, save_invoice, queue_for_review
from pipeline.extract import extract
from pipeline.validate import validate, needs_review

def run(folder: Path):
    with engine.connect() as conn:
        known = {r.gstin for r in conn.execute(select(suppliers))}
        seen = {(r.supplier_gstin, r.invoice_number) for r in conn.execute(select(invoices))}
    saved = reviewed = 0
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
            continue
        inv, usage = extract(path)
        problems = validate(inv, known, seen) if inv else ["The model couldn't extract this file"]
        if needs_review(inv, problems):
            queue_for_review(inv, problems + [f"Unsure about: {f}" for f in (inv.uncertain_fields if inv else [])], path.name)
            reviewed += 1
            print(f"{path.name}  review  ({usage['seconds']} s)  {problems[0] if problems else 'model unsure'}")
        else:
            save_invoice(inv, path.name)
            seen.add((inv.supplier_gstin, inv.invoice_number))
            saved += 1
            print(f"{path.name}  saved   ({usage['seconds']} s)")
    print(f"Saved straight away: {saved}   Sent to review: {reviewed}")

if __name__ == "__main__":
    run(Path(sys.argv[1]))
