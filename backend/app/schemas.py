from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
import re


class VendorSubmissionCreate(BaseModel):
    legal_name: str = Field(min_length=2, max_length=240)
    country_code: str = Field(min_length=2, max_length=2)
    tax_id_type: str = Field(min_length=2, max_length=24)
    tax_id: str = Field(min_length=3, max_length=80)
    registration_id: str | None = Field(default=None, max_length=100)
    registered_address: str = Field(min_length=5, max_length=2000)
    contact_name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr
    supplier_category: str = Field(min_length=2, max_length=100)
    business_justification: str = Field(min_length=5, max_length=3000)
    bank_account_holder: str = Field(min_length=2, max_length=240)
    bank_country: str = Field(min_length=2, max_length=2)
    bank_code: str = Field(min_length=2, max_length=40)
    bank_reference: str = Field(min_length=3, max_length=120, description="Token/reference from bank verification provider; do not submit a raw account number")

    @field_validator("country_code", "bank_country")
    @classmethod
    def uppercase_country(cls, value: str) -> str:
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("Use a two-letter ISO country code")
        return value

    @field_validator("legal_name", "bank_account_holder")
    @classmethod
    def trim_names(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("tax_id_type")
    @classmethod
    def normalize_tax_id_type(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("tax_id")
    @classmethod
    def normalize_tax_id(cls, value: str) -> str:
        return re.sub(r"\s+", "", value).upper()


class VendorSubmissionUpdate(BaseModel):
    legal_name: str | None = None
    country_code: str | None = None
    tax_id_type: str | None = None
    tax_id: str | None = None
    registration_id: str | None = None
    registered_address: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    supplier_category: str | None = None
    business_justification: str | None = None
    bank_account_holder: str | None = None
    bank_country: str | None = None
    bank_code: str | None = None
    bank_reference: str | None = None

    @field_validator("country_code", "bank_country")
    @classmethod
    def uppercase_optional_country(cls, value):
        if value is None:
            return value
        value = value.upper()
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("Use a two-letter ISO country code")
        return value

    @field_validator("tax_id_type")
    @classmethod
    def uppercase_optional_tax_type(cls, value):
        return value.strip().upper() if value else value

    @field_validator("tax_id")
    @classmethod
    def uppercase_optional_tax_id(cls, value):
        return re.sub(r"\s+", "", value).upper() if value else value


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stage: str
    status: str
    findings: list
    evidence: list
    required_actions: list
    created_at: datetime


class CommunicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recipient: str
    subject: str
    body: str
    channel: str
    sent: bool
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    document_type: str
    extraction_method: str
    extraction_json: dict
    created_at: datetime


class VendorSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    legal_name: str
    country_code: str
    tax_id_type: str
    tax_id: str
    registration_id: str | None
    registered_address: str
    contact_name: str
    contact_email: str
    supplier_category: str
    business_justification: str
    bank_account_holder: str
    bank_country: str
    bank_code: str
    bank_reference: str
    status: str
    demo_mode: bool
    submitted_at: datetime
    updated_at: datetime
    # Gemini AI fields
    ai_risk_score: int | None = None
    ai_risk_level: str | None = None
    ai_risk_reason: str | None = None
    ai_detail_notes: str | None = None
    vendor_fields_snapshot: dict | None = None
    documents: list[DocumentOut] = []
    communications: list[CommunicationOut] = []
    reviews: list[ReviewOut] = []

