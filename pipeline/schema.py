# pipeline/schema.py
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    hsn_code: str | None = Field(None, description="HSN or SAC code if printed")
    quantity: float
    unit_price: float
    taxable_value: float = Field(description="Line amount before GST, as printed")
    gst_rate: float | None = Field(None, description="GST rate in percent, e.g. 18")

class Invoice(BaseModel):
    supplier_name: str
    supplier_gstin: str | None = Field(None, description="15-character GSTIN of the supplier")
    buyer_gstin: str | None = None
    invoice_number: str
    invoice_date: str = Field(description="ISO format YYYY-MM-DD")
    line_items: list[LineItem]
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_amount: float = Field(description="Grand total payable, as printed")
    uncertain_fields: list[str] = Field(default_factory=list,
        description="Names of fields you guessed or could not read clearly")
