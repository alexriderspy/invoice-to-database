# app/review.py
import json
import pypdfium2 as pdfium
import streamlit as st
from pathlib import Path
from sqlalchemy import select, update
from pipeline.db import engine, review_queue, save_invoice, log
from pipeline.schema import Invoice

st.set_page_config(page_title="Invoice review", layout="wide")
reviewer = st.sidebar.text_input("Your name", "")
with engine.connect() as conn:
    pending = conn.execute(select(review_queue).where(review_queue.c.status == "pending")).fetchall()
st.sidebar.write(f"{len(pending)} invoices waiting")
if not pending:
    st.success("Nothing to review."); st.stop()

item = st.sidebar.selectbox("Invoice", pending, format_func=lambda r: r.source_file)
left, right = st.columns(2)
path = Path("data/invoices") / item.source_file
with left:
    if path.suffix == ".pdf":
        st.image(pdfium.PdfDocument(str(path))[0].render(scale=2).to_pil(), use_container_width=True)
    else:
        st.image(str(path), use_container_width=True)
with right:
    for p in json.loads(item.problems):
        st.error(p)
    data = json.loads(item.extracted) or {}
    edited = st.text_area("Extracted fields (edit before approving)", json.dumps(data, indent=2), height=480)
    a, r = st.columns(2)
    if a.button("Approve", type="primary", disabled=not reviewer):
        save_invoice(Invoice.model_validate_json(edited), item.source_file, actor=reviewer)
        with engine.begin() as conn:
            conn.execute(update(review_queue).where(review_queue.c.id == item.id).values(status="approved"))
        st.rerun()
    if r.button("Reject", disabled=not reviewer):
        with engine.begin() as conn:
            conn.execute(update(review_queue).where(review_queue.c.id == item.id).values(status="rejected"))
            log(conn, item.source_file, "rejected", reviewer)
        st.rerun()
