# invoice-pipeline

Supplier invoices (PDFs and phone photos) into database rows, running fully on your own machine.
pypdfium2 reads the text out of PDFs, RapidOCR reads phone photos, a local model on Ollama
(`qwen2.5:7b`) fills a fixed Pydantic schema in JSON mode, plain Python checks the maths, GST and
GSTINs, clean invoices are saved, and anything doubtful goes to a Streamlit review screen.
Every step is written to an audit log. No API key needed.

## Quickstart

```bash
# 1. the model (once): install Ollama from https://ollama.com, then
ollama pull qwen2.5:7b            # about 4.7 GB

# 2. the project
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # RapidOCR brings its small OCR models with it
cp .env.example .env

python data/make_invoices.py --count 60 --broken 12 --photos 10   # test invoices + data/labels.json
python -m pipeline.seed                                           # load the supplier master (once)

python demo_extract.py data/invoices/inv_000.pdf                  # one invoice: the text, then the JSON
python -m pipeline.run data/invoices                              # extract, check, save or queue
python -m streamlit run app/review.py                             # review screen (python -m so `pipeline` imports)
python -m evals.run_evals                                         # accuracy, straight-through, broken caught, time
```

Run everything from this folder, so `data/invoices` and `invoices.db` resolve.

## Swapping in a cloud model

The model is called through the OpenAI-compatible API, and Ollama serves that API on
`localhost:11434/v1`. To use a hosted model instead, change three lines in `.env`:

```bash
LLM_BASE_URL=https://api.your-provider.com/v1
LLM_API_KEY=your-key
LLM_MODEL=the-model-name
```

Set `PRICE_IN_PER_M` and `PRICE_OUT_PER_M` (US dollars per million tokens) if you want the eval to print a cost.

## What's where

| File | What it does |
|---|---|
| `data/make_invoices.py` | Draws realistic A4 tax invoices with ReportLab, turns some into blurry rotated phone photos, breaks 12 on purpose (line maths, total, GSTIN typo) and writes `data/labels.json` with the printed values and a `broken` field. Seeded, so it's reproducible. |
| `pipeline/schema.py` | The `Invoice` and `LineItem` Pydantic models. |
| `pipeline/config.py` | Model URL, key, name and prices, read from `.env`. |
| `pipeline/llm.py` | One call to the model in JSON mode, locked to a Pydantic schema, with a SQLite cache. |
| `pipeline/extract.py` | PDF text with pypdfium2, photo text with RapidOCR (tilt undone, words grouped into lines), then text to `Invoice`. |
| `pipeline/validate.py` | The checks: line maths, total, GSTIN format, CGST+SGST vs IGST, valid GST rate for the date, known supplier, duplicates. |
| `pipeline/db.py` | SQLAlchemy tables (suppliers, invoices, invoice_lines, review_queue, audit_log) and writes. |
| `pipeline/seed.py` | Loads the three suppliers into the supplier master. |
| `pipeline/run.py` | Runs a whole folder through extract, validate, save or review. |
| `app/review.py` | Streamlit review screen. |
| `evals/run_evals.py` | Scores the pipeline against `data/labels.json` and prints time and cost per invoice. |
| `demo_extract.py` | Shows the text read from one file and what the model extracted. |
| `demo_validate.py`, `demo_db.py` | Small demos that use the label values (no model) to show the checks and the database. |

## Notes

- `DATABASE_URL` in `.env` switches between SQLite (default, `sqlite:///invoices.db`) and Postgres.
- GST rates live in `pipeline/validate.py`; check the current CBIC list, they change.
- Model answers are cached in `llm_cache.db`, keyed on the model and the exact messages. Delete it to call the model again.
- Never commit `.env`. It's in `.gitignore`.
