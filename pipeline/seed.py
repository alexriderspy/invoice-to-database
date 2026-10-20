# pipeline/seed.py
# Load the supplier master once. In a real company this comes from the accounts system.
from sqlalchemy import insert, select
from pipeline.db import engine, suppliers

SUPPLIER_MASTER = [
    ("27AABCD1234E1Z5", "Deccan Castings Pvt Ltd"),
    ("27AAKFS5678G1Z2", "Shree Motors & Winding"),
    ("29AAGCK4321H1Z9", "Kaveri Seals and Gaskets"),
]

if __name__ == "__main__":
    with engine.begin() as conn:
        existing = {r.gstin for r in conn.execute(select(suppliers))}
        new = [{"gstin": g, "name": n} for g, n in SUPPLIER_MASTER if g not in existing]
        if new:
            conn.execute(insert(suppliers), new)
        print(f"Supplier master: added {len(new)}, already there {len(existing)}")
        for r in conn.execute(select(suppliers).order_by(suppliers.c.gstin)):
            print(f"  {r.gstin}  {r.name}")
