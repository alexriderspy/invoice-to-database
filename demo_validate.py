# demo_validate.py
# Runs the validation checks on the values PRINTED on a few invoices (from data/labels.json).
# No model is involved here: this shows what validate() says when it is given an invoice's real contents.
import json
from pathlib import Path
from sqlalchemy import select
from pipeline.db import engine, suppliers
from pipeline.schema import Invoice
from pipeline.validate import validate

labels = json.loads(Path("data/labels.json").read_text())
with engine.connect() as conn:
    known = {r.gstin for r in conn.execute(select(suppliers))}

def pick(kind):
    return next(n for n, l in sorted(labels.items()) if l["broken"] == kind and n.endswith(".pdf"))

for name in [pick(None), pick("line_math"), pick("total"), pick("gstin")]:
    label = labels[name]
    inv = Invoice(**{k: v for k, v in label.items() if k != "broken"})
    problems = validate(inv, known, seen=set())
    print(f"{name}  ({'clean' if not label['broken'] else 'broken: ' + label['broken']})")
    if not problems:
        print("  no problems")
    for p in problems:
        print(f"  PROBLEM  {p}")
    print()
