# demo_extract.py
# Reads one invoice, prints the text the model sees, then what it extracted.
import sys
from pathlib import Path
from pipeline.extract import extract, read_text

path = Path(sys.argv[1])
print(f"--- text read from {path.name} ---")
print(read_text(path))
inv, usage = extract(path)
print("\n--- extracted ---")
print(inv.model_dump_json(indent=2) if inv else "Nothing usable came back: this one goes to a person")
print(f"\n{usage['input_tokens']} tokens in, {usage['output_tokens']} out, {usage['seconds']} s")
