# demo_queue.py
# Fills the review queue for a demo of the review screen, WITHOUT calling the model:
# each broken invoice's printed values (data/labels.json) stand in for the extracted JSON,
# and the problems come from the real validate().
import json
from pathlib import Path
from sqlalchemy import select
from pipeline.db import engine, suppliers, queue_for_review
from pipeline.schema import Invoice
from pipeline.validate import validate

labels = json.loads(Path("data/labels.json").read_text())
with engine.connect() as conn:
    known = {r.gstin for r in conn.execute(select(suppliers))}
order = {"line_math": 0, "total": 1, "gstin": 2}
broken = sorted((n for n, l in labels.items() if l["broken"]), key=lambda n: (order[labels[n]["broken"]], n))
for name in broken:
    inv = Invoice(**{k: v for k, v in labels[name].items() if k != "broken"})
    queue_for_review(inv, validate(inv, known, seen=set()), name)
print(f"Queued {len(broken)} broken invoices for review (label values standing in for extraction)")
