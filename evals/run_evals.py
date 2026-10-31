# evals/run_evals.py (the scoring part)
FIELDS = ["supplier_name", "supplier_gstin", "invoice_number", "invoice_date", "cgst", "sgst", "igst", "total_amount"]

def score(predicted: dict, expected: dict) -> tuple[int, int]:
    right = sum(1 for f in FIELDS if str(predicted.get(f)).strip() == str(expected.get(f)).strip())
    right += sum(1 for p, e in zip(predicted.get("line_items", []), expected["line_items"])
                 if abs(p["taxable_value"] - e["taxable_value"]) < 0.01)
    return right, len(FIELDS) + len(expected["line_items"])

# report: field accuracy, straight-through rate, broken invoices caught (must be all of them), time and cost per invoice


# ---------------------------------------------------------------------------
# Running it: extract + validate every file in data/invoices, compare with data/labels.json.
# Needs Ollama running with qwen2.5:7b (or LLM_BASE_URL / LLM_MODEL pointing at another model).
# Nothing is written to the database.
# Run from the project folder:  python -m evals.run_evals
# ---------------------------------------------------------------------------
import json
from pathlib import Path
from sqlalchemy import select
from pipeline import config
from pipeline.db import engine, suppliers
from pipeline.extract import extract
from pipeline.validate import validate, needs_review


def main(folder=Path("data/invoices"), labels_file=Path("data/labels.json")):
    labels = json.loads(labels_file.read_text())
    with engine.connect() as conn:
        known = {r.gstin for r in conn.execute(select(suppliers))}
    seen = set()
    right = total = straight_through = 0
    input_tokens = output_tokens = seconds = 0
    broken_caught, broken_missed = [], []

    for name, expected in sorted(labels.items()):
        inv, usage = extract(folder / name)
        input_tokens += usage["input_tokens"]
        output_tokens += usage["output_tokens"]
        seconds += usage["seconds"]          # measured on the first call, kept in the cache
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
    cost = (input_tokens * config.PRICE_IN_PER_M + output_tokens * config.PRICE_OUT_PER_M) / 1e6
    print()
    print(f"Field accuracy:        {right}/{total} = {right / total:.1%}")
    print(f"Straight-through rate: {straight_through}/{n} = {straight_through / n:.1%}")
    print(f"Broken caught:         {len(broken_caught)} of {n_broken}"
          + ("" if not broken_missed else f"   MISSED: {', '.join(broken_missed)}"))
    print(f"Tokens:                {input_tokens:,} in, {output_tokens:,} out")
    print(f"Model time:            {seconds / n:.1f} s per invoice on {config.LLM_MODEL}")
    print(f"Cost per invoice:      ${cost / n:.4f}  (total ${cost:.2f} for {n} invoices)")


if __name__ == "__main__":
    main()
