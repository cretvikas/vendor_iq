from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Float, Integer, String, Text, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class VendorSubmission(Base):
    __tablename__ = "vendor_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    legal_name: Mapped[str] = mapped_column(String(240), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    tax_id_type: Mapped[str] = mapped_column(String(24))
    tax_id: Mapped[str] = mapped_column(String(80), index=True)
    registration_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registered_address: Mapped[str] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_email: Mapped[str] = mapped_column(String(254), index=True)
    supplier_category: Mapped[str] = mapped_column(String(100))
    business_justification: Mapped[str] = mapped_column(Text)
    bank_account_holder: Mapped[str] = mapped_column(String(240))
    bank_country: Mapped[str] = mapped_column(String(2))
    bank_code: Mapped[str] = mapped_column(String(40))
    bank_reference: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED", index=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    # AI risk assessment (populated by Gemini after evaluation)
    ai_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ai_risk_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Gemini's detailed reasoning paragraph — shown to admins for manual review
    ai_detail_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Snapshot of all vendor form fields captured at evaluation time
    vendor_fields_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    documents: Mapped[list["VendorDocument"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewResult"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    communications: Mapped[list["CommunicationLog"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class VendorDocument(Base):
    __tablename__ = "vendor_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("vendor_submissions.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    document_type: Mapped[str] = mapped_column(String(60), index=True)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extraction_json: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_method: Mapped[str] = mapped_column(String(40), default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submission: Mapped[VendorSubmission] = relationship(back_populates="documents")


class ReviewResult(Base):
    __tablename__ = "review_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("vendor_submissions.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30))
    findings: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    required_actions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submission: Mapped[VendorSubmission] = relationship(back_populates="reviews")


class CommunicationLog(Base):
    __tablename__ = "communication_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("vendor_submissions.id", ondelete="CASCADE"), index=True)
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(30), default="EMAIL_DRAFT")
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submission: Mapped[VendorSubmission] = relationship(back_populates="communications")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("vendor_submissions.id", ondelete="CASCADE"), index=True)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submission: Mapped[VendorSubmission] = relationship(back_populates="audit_logs")


class ApprovedVendor(Base):
    __tablename__ = "approved_vendors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(240), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    tax_id_type: Mapped[str] = mapped_column(String(24))
    tax_id: Mapped[str] = mapped_column(String(80), index=True)
    source_submission_id: Mapped[int] = mapped_column(Integer, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


Index("ix_vendor_tax_country", VendorSubmission.country_code, VendorSubmission.tax_id)
