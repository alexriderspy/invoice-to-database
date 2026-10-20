# data/make_invoices.py (the core of it)
import json, random
from pathlib import Path
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SUPPLIERS = [("Deccan Castings Pvt Ltd", "27AABCD1234E1Z5"), ("Shree Motors & Winding", "27AAKFS5678G1Z2"),
             ("Kaveri Seals and Gaskets", "29AAGCK4321H1Z9")]   # 27 = Maharashtra, 29 = Karnataka
BUYER_GSTIN = "27AAACV9876K1Z3"                                 # Vardhan Pumps, Pune
ITEMS = [("Impeller VP-100", "8413", 1450.0), ("Mechanical seal 25mm", "8484", 620.0),
         ("Motor winding wire 1kg", "8544", 980.0), ("Pump casing VS-200", "8413", 5200.0)]

def make_invoice(i, out_dir, break_it=None):
    name, gstin = random.choice(SUPPLIERS)
    lines = []
    for desc, hsn, price in random.sample(ITEMS, k=random.randint(1, 3)):
        qty = random.randint(1, 10)
        lines.append({"description": desc, "hsn_code": hsn, "quantity": qty, "unit_price": price,
                      "taxable_value": round(qty * price, 2), "gst_rate": 18.0})
    taxable = sum(l["taxable_value"] for l in lines)
    same_state = gstin[:2] == BUYER_GSTIN[:2]
    tax = round(taxable * 0.18, 2)
    inv = {"supplier_name": name, "supplier_gstin": gstin, "buyer_gstin": BUYER_GSTIN,
           "invoice_number": f"{name.split()[0][:3].upper()}/26-27/{1000 + i}", "invoice_date": "2026-10-03",
           "line_items": lines, "cgst": tax / 2 if same_state else 0.0, "sgst": tax / 2 if same_state else 0.0,
           "igst": 0.0 if same_state else tax, "total_amount": round(taxable + tax, 2)}
    if break_it == "line_math":
        inv["line_items"][0]["taxable_value"] += 100        # quantity x price no longer matches
    elif break_it == "total":
        inv["total_amount"] += 500                          # total doesn't add up
    elif break_it == "gstin":
        inv["supplier_gstin"] = inv["supplier_gstin"][:-1]  # one character missing
    draw_pdf(inv, out_dir / f"inv_{i:03d}.pdf")
    return inv

def to_phone_photo(pdf_page_png, out_path):
    img = Image.open(pdf_page_png).convert("RGB").rotate(random.uniform(-4, 4), expand=True, fillcolor="white")
    img.filter(ImageFilter.GaussianBlur(0.8)).save(out_path, quality=70)


# ---------------------------------------------------------------------------
# The rest: drawing the PDF, and the command line that writes the whole folder.
# ---------------------------------------------------------------------------
import argparse, shutil, tempfile
import pypdfium2 as pdfium
from reportlab.lib import colors

ADDRESSES = {
    "27AABCD1234E1Z5": ["Plot 14, MIDC Bhosari", "Pune 411026, Maharashtra"],
    "27AAKFS5678G1Z2": ["Gala 7, Kudalwadi Industrial Estate, Chikhli", "Pune 411062, Maharashtra"],
    "29AAGCK4321H1Z9": ["No. 42, Peenya Industrial Area, Phase 2", "Bengaluru 560058, Karnataka"],
}
STATES = {"27": "Maharashtra", "29": "Karnataka"}
BREAK_TYPES = ["line_math", "total", "gstin"]


def inr(x):
    """Format a number the Indian way: 1,23,456.00"""
    whole, frac = f"{x:.2f}".split(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    return f"{sign}{whole}.{frac}"


def draw_pdf(inv, path):
    """A plain, normal-looking A4 tax invoice: supplier block, buyer, line items, taxes, total."""
    W, H = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"Tax invoice {inv['invoice_number']}")
    left, right = 40, W - 40
    ink, grey, rule = colors.HexColor("#1a1a1a"), colors.HexColor("#555555"), colors.HexColor("#999999")

    # supplier block
    y = H - 56
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(left, y, inv["supplier_name"])
    c.setFont("Helvetica", 9.5)
    c.setFillColor(grey)
    # the address follows the real supplier, even when the printed GSTIN has a typo
    addr = next(a for g, a in ADDRESSES.items() if g.startswith(inv["supplier_gstin"]))
    for k, text in enumerate(addr + [f"GSTIN: {inv['supplier_gstin']}"]):
        c.drawString(left, y - 16 - 13 * k, text)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(right, y, "TAX INVOICE")
    c.setFont("Helvetica", 9.5)
    d = inv["invoice_date"]
    printed_date = f"{d[8:10]}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(d[5:7]) - 1]}-{d[:4]}"
    c.drawRightString(right, y - 16, f"Invoice No: {inv['invoice_number']}")
    c.drawRightString(right, y - 29, f"Invoice Date: {printed_date}")
    c.drawRightString(right, y - 42, "Original for Recipient")
    y -= 66
    c.setStrokeColor(rule)
    c.line(left, y, right, y)

    # buyer block
    y -= 18
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(left, y, "Bill to")
    c.drawString(W / 2 + 10, y, "Place of supply")
    c.setFont("Helvetica", 9.5)
    for k, text in enumerate(["Vardhan Pumps Pvt Ltd", "S. No. 118, Hadapsar Industrial Estate",
                              "Pune 411013, Maharashtra", f"GSTIN: {inv['buyer_gstin']}"]):
        c.drawString(left, y - 14 - 13 * k, text)
    c.drawString(W / 2 + 10, y - 14, f"{STATES[inv['buyer_gstin'][:2]]} ({inv['buyer_gstin'][:2]})")
    c.drawString(W / 2 + 10, y - 27, "Payment terms: 30 days")
    y -= 80

    # line-items table
    cols = [(left, "Sr", "l"), (left + 26, "Description", "l"), (left + 220, "HSN", "l"),
            (left + 300, "Qty", "r"), (left + 375, "Rate", "r"), (left + 465, "Taxable value", "r"),
            (right, "GST %", "r")]
    c.setFillColor(colors.HexColor("#eeeeee"))
    c.rect(left, y - 6, right - left, 20, stroke=0, fill=1)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 9)
    for x, title, align in cols:
        (c.drawString if align == "l" else c.drawRightString)(x + (4 if align == "l" else -4 if x == right else 0), y, title)
    c.setFont("Helvetica", 9.5)
    for n, l in enumerate(inv["line_items"], 1):
        y -= 22
        values = [str(n), l["description"], l["hsn_code"], str(l["quantity"]), inr(l["unit_price"]),
                  inr(l["taxable_value"]), f"{l['gst_rate']:g}%"]
        for (x, _, align), v in zip(cols, values):
            (c.drawString if align == "l" else c.drawRightString)(x + (4 if align == "l" else -4 if x == right else 0), y, v)
    y -= 12
    c.line(left, y, right, y)

    # tax lines and total
    taxable = sum(l["taxable_value"] for l in inv["line_items"])
    rows = [("Taxable value", taxable)]
    if inv["igst"]:
        rows.append(("IGST @ 18%", inv["igst"]))
    else:
        rows += [("CGST @ 9%", inv["cgst"]), ("SGST @ 9%", inv["sgst"])]
    lx = left + 330
    for label, amount in rows:
        y -= 18
        c.drawString(lx, y, label)
        c.drawRightString(right - 4, y, inr(amount))
    y -= 10
    c.line(lx, y, right, y)
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawString(lx, y, "Total (INR)")
    c.drawRightString(right - 4, y, inr(inv["total_amount"]))

    # footer
    c.setFont("Helvetica", 8.5)
    c.setFillColor(grey)
    c.drawString(left, 120, "Bank: HDFC Bank, Pune.  A/c details on request.")
    c.drawString(left, 107, "Goods once sold will not be taken back. Subject to local jurisdiction.")
    c.setFillColor(ink)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(right, 120, f"For {inv['supplier_name']}")
    c.drawRightString(right, 80, "Authorised Signatory")
    c.save()


def clean_numbers(inv):
    """Round floats to the paisa so labels.json matches what's printed on the page."""
    out = dict(inv)
    for k in ("cgst", "sgst", "igst", "total_amount"):
        out[k] = round(out[k], 2)
    out["line_items"] = [{**l, "quantity": float(l["quantity"]), "taxable_value": round(l["taxable_value"], 2)}
                         for l in inv["line_items"]]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Make realistic test invoices, some broken on purpose.")
    ap.add_argument("--count", type=int, default=60)
    ap.add_argument("--broken", type=int, default=12)
    ap.add_argument("--photos", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)

    here = Path(__file__).parent
    out_dir = here / "invoices"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)

    broken_ids = random.sample(range(args.count), args.broken)
    broken = {i: BREAK_TYPES[k % len(BREAK_TYPES)] for k, i in enumerate(sorted(broken_ids))}
    photo_ids = set(random.sample(range(args.count), args.photos))

    labels = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(args.count):
            inv = make_invoice(i, out_dir, break_it=broken.get(i))
            pdf_path = out_dir / f"inv_{i:03d}.pdf"
            name = pdf_path.name
            if i in photo_ids:                      # this supplier sent a phone photo instead of a PDF
                png = Path(tmp) / f"inv_{i:03d}.png"
                doc = pdfium.PdfDocument(str(pdf_path))
                doc[0].render(scale=2).to_pil().save(png)
                doc.close()
                to_phone_photo(png, out_dir / f"inv_{i:03d}.jpg")
                pdf_path.unlink()
                name = f"inv_{i:03d}.jpg"
            labels[name] = {**clean_numbers(inv), "broken": broken.get(i)}

    (here / "labels.json").write_text(json.dumps(labels, indent=2))
    n_pdf = sum(1 for n in labels if n.endswith(".pdf"))
    print(f"Wrote {len(labels)} invoices to {out_dir.relative_to(here.parent)}/  ({n_pdf} PDFs, {len(labels) - n_pdf} phone photos)")
    for t in BREAK_TYPES:
        files = [n for n, l in labels.items() if l["broken"] == t]
        print(f"  broken on purpose ({t}): {len(files)}  {', '.join(files)}")
    print(f"Labels for every file: {(here / 'labels.json').relative_to(here.parent)}")
