# pipeline/extract.py
import base64
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from pipeline.schema import Invoice

load_dotenv()
client = anthropic.Anthropic()

PROMPT = """Extract this supplier invoice into the schema.
Copy values exactly as printed. Do not calculate, round or correct anything,
even if the supplier's numbers look wrong. Dates in YYYY-MM-DD.
If a field is missing, leave it null. If you had to guess any field or could not
read it clearly, add its name to uncertain_fields."""

def file_block(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    if path.suffix.lower() == ".pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}

def extract(path: Path) -> tuple[Invoice | None, dict]:
    response = client.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": [file_block(path), {"type": "text", "text": PROMPT}]}],
        output_format=Invoice,
    )
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    if response.stop_reason == "refusal":
        return None, usage        # a person handles this one
    return response.parsed_output, usage
