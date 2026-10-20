# invoice-pipeline

Supplier invoices (PDFs and phone photos) into database rows: Claude extracts the fields into a fixed
schema, plain Python checks the maths, GST and GSTINs, clean invoices are saved, and anything doubtful
goes to a Streamlit review screen. Every step is written to an audit log.

**Extraction needs an Anthropic API key.** `pipeline/run.py`, `pipeline/extract.py` and
`evals/run_evals.py` call the Claude API and will not run without `ANTHROPIC_API_KEY` in `.env`.
Everything else (making invoices, the checks, the database, the review screen) runs without one.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your real ANTHROPIC_API_KEY in .env

python data/make_invoices.py --count 60 --broken 12 --photos 10   # test invoices + data/labels.json
python -m pipeline.seed                                           # load the supplier master (once)

python -m pipeline.run data/invoices                              # extract, check, save or queue (needs the key)
python -m streamlit run app/review.py                             # review screen (python -m so `pipeline` imports)
python -m evals.run_evals                                         # accuracy, straight-through, broken caught, cost (needs the key)
```

Run everything from this folder, so `data/invoices` and `invoices.db` resolve.

## What's where

| File | What it does |
|---|---|
| `data/make_invoices.py` | Draws realistic A4 tax invoices with ReportLab, turns some into blurry rotated phone photos, breaks 12 on purpose (line maths, total, GSTIN typo) and writes `data/labels.json` with the printed values and a `broken` field. Seeded, so it's reproducible. |
| `pipeline/schema.py` | The `Invoice` and `LineItem` Pydantic models. |
| `pipeline/extract.py` | PDF or image to `Invoice` with `client.messages.parse` and Claude Opus 5.5. |
| `pipeline/validate.py` | The checks: line maths, total, GSTIN format, CGST+SGST vs IGST, valid GST rate for the date, known supplier, duplicates. |
| `pipeline/db.py` | SQLAlchemy tables (suppliers, invoices, invoice_lines, review_queue, audit_log) and writes. |
| `pipeline/seed.py` | Loads the three suppliers into the supplier master. |
| `pipeline/run.py` | Runs a whole folder through extract, validate, save or review. |
| `app/review.py` | Streamlit review screen. |
| `evals/run_evals.py` | Scores the pipeline against `data/labels.json` and prints the cost per invoice. |
| `demo_validate.py`, `demo_db.py`, `demo_queue.py` | Small demos that use the label values (no model) to show the checks, the database and the review queue. |

## Notes

- `DATABASE_URL` in `.env` switches between SQLite (default, `sqlite:///invoices.db`) and Postgres.
- GST rates live in `pipeline/validate.py`; check the current CBIC list, they change.
- Model prices live in `evals/run_evals.py`; check the current Anthropic pricing page.
- Never commit `.env`. It's in `.gitignore`.
