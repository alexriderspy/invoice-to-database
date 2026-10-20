# evals/run_evals.py (the scoring part)
FIELDS = ["supplier_name", "supplier_gstin", "invoice_number", "invoice_date", "cgst", "sgst", "igst", "total_amount"]

def score(predicted: dict, expected: dict) -> tuple[int, int]:
    right = sum(1 for f in FIELDS if str(predicted.get(f)).strip() == str(expected.get(f)).strip())
    right += sum(1 for p, e in zip(predicted.get("line_items", []), expected["line_items"])
                 if abs(p["taxable_value"] - e["taxable_value"]) < 0.01)
    return right, len(FIELDS) + len(expected["line_items"])

# report: field accuracy, straight-through rate, broken invoices caught (must be all of them), cost per invoice


# ---------------------------------------------------------------------------
# Running it: extract + validate every file in data/invoices, compare with data/labels.json.
# Needs ANTHROPIC_API_KEY in .env. Nothing is written to the database.
# Run from the project folder:  python -m evals.run_evals
# ---------------------------------------------------------------------------
import json
from pathlib import Path
from sqlalchemy import select
from pipeline.db import engine, suppliers
from pipeline.extract import extract
from pipeline.validate import validate, needs_review

# Claude Opus 5.5 prices in US dollars per million tokens.
# CHECK CURRENT PRICING on https://www.anthropic.com/pricing before quoting these to anyone.
INPUT_PRICE_PER_MTOK = 5.00
OUTPUT_PRICE_PER_MTOK = 25.00


def main(folder=Path("data/invoices"), labels_file=Path("data/labels.json")):
    labels = json.loads(labels_file.read_text())
    with engine.connect() as conn:
        known = {r.gstin for r in conn.execute(select(suppliers))}
    seen = set()
    right = total = straight_through = 0
    input_tokens = output_tokens = 0
    broken_caught, broken_missed = [], []

    for name, expected in sorted(labels.items()):
        inv, usage = extract(folder / name)
        input_tokens += usage["input_tokens"]
        output_tokens += usage["output_tokens"]
        problems = validate(inv, known, seen) if inv else ["The model couldn't extract this file"]
        review = needs_review(inv, problems)
        r, t = score(inv.model_dump() if inv else {}, expected)
        right, total = right + r, total + t
        if not review:
            straight_through += 1
            seen.add((inv.supplier_gstin, inv.invoice_number))
        if expected["broken"]:
            (broken_caught if review else broken_missed).append(name)
        print(f"{name}  fields {r}/{t}  {'review' if review else 'saved'}"
              + (f"  (broken: {expected['broken']})" if expected["broken"] else ""))

    n = len(labels)
    n_broken = len(broken_caught) + len(broken_missed)
    cost = input_tokens / 1e6 * INPUT_PRICE_PER_MTOK + output_tokens / 1e6 * OUTPUT_PRICE_PER_MTOK
    print()
    print(f"Field accuracy:        {right}/{total} = {right / total:.1%}")
    print(f"Straight-through rate: {straight_through}/{n} = {straight_through / n:.1%}")
    print(f"Broken caught:         {len(broken_caught)} of {n_broken}"
          + ("" if not broken_missed else f"   MISSED: {', '.join(broken_missed)}"))
    print(f"Tokens:                {input_tokens:,} in, {output_tokens:,} out")
    print(f"Cost per invoice:      ${cost / n:.4f}  (total ${cost:.2f} for {n} invoices)")


if __name__ == "__main__":
    main()
