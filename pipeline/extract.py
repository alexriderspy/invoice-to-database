# pipeline/extract.py
import math
from pathlib import Path
from statistics import median
import pypdfium2 as pdfium
from pydantic import ValidationError
from rapidocr_onnxruntime import RapidOCR
from pipeline.llm import chat_json
from pipeline.schema import Invoice

ocr = RapidOCR()      # small local OCR models, downloaded with the pip package

PROMPT = """You turn the text of one supplier invoice into JSON that matches the schema.
Copy values exactly as printed. Do not calculate, round or correct anything,
even if the supplier's numbers look wrong. Amounts are plain numbers: 2,060.00 becomes 2060.0.
Fill supplier_gstin and buyer_gstin from the lines that start with GSTIN.
Text from a phone photo comes from OCR, which can drop the spaces between words.
Put the spaces back in names, so VardhanPumpsPvtLtd becomes Vardhan Pumps Pvt Ltd,
but never change a letter or a digit.
Dates in YYYY-MM-DD, so 03-Oct-2026 becomes 2026-10-03.
If a field is missing, leave it null. uncertain_fields is a list of schema field names.
Leave it empty, [], unless a value was missing or unreadable in the text."""

def pdf_boxes(path: Path) -> list:
    boxes, offset = [], 0.0
    for page in pdfium.PdfDocument(str(path)):
        height, text_page = page.get_height(), page.get_textpage()
        for i in range(text_page.count_rects()):               # one rect per printed run of text
            left, bottom, right, top = text_page.get_rect(i)
            text = text_page.get_text_bounded(left, bottom, right, top).strip()
            top, bottom = offset + height - top, offset + height - bottom   # PDF y goes up, image y goes down
            boxes.append([[[left, top], [right, top], [right, bottom], [left, bottom]], text, 1.0])
        offset += height                                      # the next page goes below this one
    return boxes

def to_lines(boxes: list) -> str:
    # each box: [4 corners, text, confidence], from the PDF or from OCR
    if not boxes:
        return ""                                  # nothing readable: the model gets empty text
    tilt = median(math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0]) for c, _, _ in boxes)
    words = []
    for c, text, _ in boxes:
        x, y = sum(p[0] for p in c) / 4, sum(p[1] for p in c) / 4
        level_y = y * math.cos(tilt) - x * math.sin(tilt)            # y with the photo's tilt undone
        words.append((level_y, x, c[2][1] - c[0][1], text))
    rows = []
    for y, x, height, text in sorted(words):
        if rows and y - rows[-1]["y"] < height / 2:
            rows[-1]["words"].append((x, text))                       # same printed line
        else:
            rows.append({"y": y, "words": [(x, text)]})
    return "\n".join("   ".join(t for _, t in sorted(r["words"])) for r in rows)

def read_text(path: Path) -> str:
    boxes = pdf_boxes(path) if path.suffix.lower() == ".pdf" else ocr(str(path))[0]
    return to_lines(boxes or [])

def extract(path: Path) -> tuple[Invoice | None, dict]:
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": read_text(path)}]
    text, usage = chat_json(messages, Invoice)
    try:
        return Invoice.model_validate_json(text), usage
    except ValidationError:
        return None, usage        # a person handles this one
