# pipeline/validate.py
import re
from datetime import date
from pipeline.schema import Invoice

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
GST_RATES_BEFORE = {0, 5, 12, 18, 28}          # invoices dated before 22 Sep 2025
GST_RATES_FROM = {0, 5, 18, 40}                # from 22 Sep 2025 (check the current CBIC list)
RATE_CHANGE = date(2025, 9, 22)
TOLERANCE = 1.0                                # rupees, for rounding

def validate(inv: Invoice, known_gstins: set[str], seen: set[tuple[str, str]]) -> list[str]:
    problems = []
    for n, line in enumerate(inv.line_items, 1):
        if abs(line.quantity * line.unit_price - line.taxable_value) > TOLERANCE:
            problems.append(f"Line {n}: {line.quantity} x {line.unit_price} is not {line.taxable_value}")
    taxable = sum(l.taxable_value for l in inv.line_items)
    expected_total = taxable + inv.cgst + inv.sgst + inv.igst
    if abs(expected_total - inv.total_amount) > TOLERANCE:
        problems.append(f"Total {inv.total_amount} doesn't match lines plus tax ({expected_total:.2f})")
    for label, g in (("Supplier", inv.supplier_gstin), ("Buyer", inv.buyer_gstin)):
        if not g or not GSTIN_RE.match(g):
            problems.append(f"{label} GSTIN '{g}' is missing or not a valid format")
    if inv.supplier_gstin and inv.buyer_gstin:
        same_state = inv.supplier_gstin[:2] == inv.buyer_gstin[:2]
        if same_state and inv.igst > 0:
            problems.append("Same-state supply should have CGST + SGST, not IGST")
        if not same_state and (inv.cgst > 0 or inv.sgst > 0):
            problems.append("Inter-state supply should have IGST, not CGST + SGST")
    try:
        allowed = GST_RATES_FROM if date.fromisoformat(inv.invoice_date) >= RATE_CHANGE else GST_RATES_BEFORE
    except ValueError:
        problems.append(f"Invoice date '{inv.invoice_date}' isn't a YYYY-MM-DD date")
        allowed = GST_RATES_FROM
    for n, line in enumerate(inv.line_items, 1):
        if line.gst_rate is not None and line.gst_rate not in allowed:
            problems.append(f"Line {n}: GST rate {line.gst_rate}% isn't a valid rate for that date")
    if inv.supplier_gstin and inv.supplier_gstin not in known_gstins:
        problems.append(f"Supplier GSTIN {inv.supplier_gstin} isn't in the supplier master")
    if (inv.supplier_gstin, inv.invoice_number) in seen:
        problems.append(f"Invoice {inv.invoice_number} from this supplier is already in the books")
    return problems

def needs_review(inv: Invoice | None, problems: list[str]) -> bool:
    return inv is None or bool(problems) or bool(inv.uncertain_fields)
