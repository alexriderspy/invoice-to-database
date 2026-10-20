# pipeline/db.py
import json, os
from datetime import datetime
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Float, Text, DateTime,
                        ForeignKey, UniqueConstraint, insert, select)

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///invoices.db"))
meta = MetaData()
suppliers = Table("suppliers", meta, Column("gstin", String(15), primary_key=True), Column("name", String))
invoices = Table("invoices", meta,
    Column("id", Integer, primary_key=True), Column("supplier_gstin", String(15)), Column("invoice_number", String),
    Column("invoice_date", String), Column("cgst", Float), Column("sgst", Float), Column("igst", Float),
    Column("total_amount", Float), Column("source_file", String), Column("approved_by", String),
    UniqueConstraint("supplier_gstin", "invoice_number"))
lines = Table("invoice_lines", meta, Column("id", Integer, primary_key=True),
    Column("invoice_id", ForeignKey("invoices.id")), Column("description", String), Column("hsn_code", String),
    Column("quantity", Float), Column("unit_price", Float), Column("taxable_value", Float), Column("gst_rate", Float))
review_queue = Table("review_queue", meta, Column("id", Integer, primary_key=True), Column("source_file", String),
    Column("extracted", Text), Column("problems", Text), Column("status", String, default="pending"))
audit = Table("audit_log", meta, Column("id", Integer, primary_key=True), Column("at", DateTime),
    Column("source_file", String), Column("action", String), Column("actor", String), Column("detail", Text))
meta.create_all(engine)

def save_invoice(inv, source_file, actor="pipeline"):
    with engine.begin() as conn:
        row = conn.execute(insert(invoices).values(
            supplier_gstin=inv.supplier_gstin, invoice_number=inv.invoice_number, invoice_date=inv.invoice_date,
            cgst=inv.cgst, sgst=inv.sgst, igst=inv.igst, total_amount=inv.total_amount,
            source_file=source_file, approved_by=actor))
        conn.execute(insert(lines), [{"invoice_id": row.inserted_primary_key[0], **l.model_dump()} for l in inv.line_items])
        log(conn, source_file, "saved", actor)

def queue_for_review(inv, problems, source_file):
    with engine.begin() as conn:
        conn.execute(insert(review_queue).values(source_file=source_file,
            extracted=inv.model_dump_json() if inv else "{}", problems=json.dumps(problems)))
        log(conn, source_file, "sent to review", "pipeline", problems)

def log(conn, source_file, action, actor, detail=None):
    conn.execute(insert(audit).values(at=datetime.now(), source_file=source_file, action=action,
                                      actor=actor, detail=json.dumps(detail) if detail else None))
