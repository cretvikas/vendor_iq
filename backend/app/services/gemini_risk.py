"""Gemini-based AI risk scoring for vendor submissions.

Sends ALL vendor form fields + extracted document content to Gemini,
then applies threshold logic to return a final_status decision:
  score <= LOW_THRESHOLD  → APPROVED  (auto-accept)
  score >= HIGH_THRESHOLD → REJECTED  (auto-reject)
  between               → PENDING   (manual review queue)
"""
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import VendorDocument, VendorSubmission

logger = logging.getLogger(__name__)

# ── Threshold defaults (overridable via config) ──────────────────────────────
_DEFAULT_LOW = 30   # score <= this → AUTO APPROVED
_DEFAULT_HIGH = 70  # score >= this → AUTO REJECTED


def _build_prompt(vendor: "VendorSubmission", documents: list["VendorDocument"]) -> str:
    """Build the full structured prompt for Gemini, including document content."""

    name_match = vendor.legal_name.lower().strip() == vendor.bank_account_holder.lower().strip()
    country_match = vendor.country_code == vendor.bank_country

    # Build document section — one block per uploaded document
    doc_sections: list[str] = []
    for idx, doc in enumerate(documents, start=1):
        fields = (doc.extraction_json or {}).get("fields", {})
        fields_str = "\n".join(f"    {k}: {v}" for k, v in fields.items()) if fields else "    (no structured fields extracted)"
        # Trim extracted text to avoid token bloat
        text_preview = (doc.extracted_text or "").strip()[:3000]
        text_block = text_preview if text_preview else "(no text could be extracted)"
        doc_sections.append(
            f"Document {idx}: {doc.document_type.replace('_', ' ').title()}\n"
            f"  Filename: {doc.original_filename}\n"
            f"  Extraction method: {doc.extraction_method}\n"
            f"  Extracted fields:\n{fields_str}\n"
            f"  Extracted text preview:\n    {text_block[:1000]}"
        )

    docs_block = "\n\n".join(doc_sections) if doc_sections else "(no documents uploaded)"

    return f"""You are a strict procurement compliance AI. Your job is to evaluate a vendor onboarding application and determine its risk level.

═══ VENDOR FORM FIELDS ═══
Legal company name:        {vendor.legal_name}
Country of registration:   {vendor.country_code}
Tax ID type:               {vendor.tax_id_type}
Tax ID value:              {vendor.tax_id}
Company registration ID:   {vendor.registration_id or "Not provided"}
Registered address:        {vendor.registered_address}
Supplier category:         {vendor.supplier_category}
Business justification:    {vendor.business_justification}
Contact name:              {vendor.contact_name}
Contact email:             {vendor.contact_email}
Bank account holder:       {vendor.bank_account_holder}
Bank country:              {vendor.bank_country}
Bank routing code:         {vendor.bank_code}

═══ AUTOMATED FLAGS ═══
Bank holder name matches legal name:     {"YES" if name_match else "NO — possible mismatch"}
Bank country matches registration:       {"YES" if country_match else "NO — cross-border banking"}
Registration ID provided:                {"YES" if vendor.registration_id else "NO — missing"}
Documents uploaded:                      {len(documents)} document(s)

═══ EXTRACTED DOCUMENT CONTENT ═══
{docs_block}

═══ EVALUATION RUBRIC ═══
Carefully assess each of the following risk factors:

1. IDENTITY CONSISTENCY — Does the company name in uploaded documents match the submitted legal name?
2. TAX ID CONSISTENCY — Does the tax identifier in uploaded documents match the submitted tax ID?
3. BANK ACCOUNT HOLDER — Does the bank account holder match the legal company name? Is there a credible explanation if not?
4. CROSS-BORDER BANKING — If the bank country differs from the registration country, is this suspicious or explainable?
5. BUSINESS JUSTIFICATION — Is the justification specific, proportionate and credible? Vague justifications are a red flag.
6. DOCUMENT COMPLETENESS — Are the required documents present and readable? Missing or unreadable documents increase risk.
7. DOCUMENT AUTHENTICITY SIGNALS — Are there any inconsistencies, mismatches or anomalies in the extracted document content?
8. EMAIL DOMAIN PLAUSIBILITY — Does the contact email domain match or relate to the company name? Generic free-email providers for large companies are a mild red flag.
9. REGISTRATION ID — Is a company registration ID provided? Absence for formal entities increases risk.
10. OVERALL PATTERN — Taken together, does the application look like a legitimate, well-documented supplier?

═══ SCORING GUIDE ═══
 0–20: Very low risk — everything matches, documents are present and consistent, justification is clear
21–30: Low risk — minor gaps but no real red flags
31–50: Medium risk — some inconsistencies or missing information that need human review
51–69: Medium-high risk — notable mismatches or red flags, definitely needs manual review
70–85: High risk — significant mismatches, missing documents, or suspicious patterns
86–100: Very high risk — multiple serious red flags, possible fraud indicators

Respond ONLY with a valid JSON object (no markdown, no code fences, no explanation outside the JSON):
{{"risk_score": <integer 0-100>, "risk_level": "<LOW|MEDIUM|HIGH>", "reason": "<1-2 sentence plain-English summary suitable for display on a dashboard>", "detail_notes": "<detailed paragraph listing EXACTLY which fields, document findings, and patterns drove the score — specific field values must be quoted, written for an admin who is deciding whether to approve or reject>"}}"""


def score_vendor_risk(vendor: "VendorSubmission", documents: list["VendorDocument"] | None = None) -> dict:
    """
    Send vendor fields + document content to Gemini.
    Returns a dict with:
      risk_score     int 0-100
      risk_level     LOW | MEDIUM | HIGH
      reason         short summary (1-2 sentences)
      detail_notes   detailed paragraph for admin manual review
      final_status   APPROVED | PENDING | REJECTED  (based on thresholds)
    """
    from ..config import settings  # local import avoids circular imports

    docs = documents or []
    fallback = {
        "risk_score": None,
        "risk_level": None,
        "reason": "Gemini API key not configured.",
        "detail_notes": "",
        "final_status": "PENDING",  # safe default — route to manual review
    }

    if not settings.gemini_enabled:
        return fallback

    try:
        from google import genai  # New SDK (google-genai package)

        client = genai.Client(api_key=settings.gemini_api_key)

        prompt = _build_prompt(vendor, docs)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        raw = response.text.strip()

        # Strip markdown code fences if the model adds them
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                cleaned = part.strip()
                if cleaned.startswith("{"):
                    raw = cleaned
                    break
            else:
                raw = parts[1].lstrip("json").strip()

        data = json.loads(raw)

        score = max(0, min(100, int(data.get("risk_score", 50))))
        level = str(data.get("risk_level", "MEDIUM")).upper()
        if level not in ("LOW", "MEDIUM", "HIGH"):
            level = "HIGH" if score >= settings.ai_high_threshold else ("MEDIUM" if score > settings.ai_low_threshold else "LOW")

        reason = str(data.get("reason", ""))
        detail_notes = str(data.get("detail_notes", ""))

        # ── Apply threshold decisioning ───────────────────────────────────────
        if score <= settings.ai_low_threshold:
            final_status = "APPROVED"
        elif score >= settings.ai_high_threshold:
            final_status = "REJECTED"
        else:
            final_status = "PENDING"   # → manual review queue

        logger.info(
            "Gemini risk scored vendor %s: score=%d level=%s status=%s",
            vendor.legal_name, score, level, final_status,
        )

        return {
            "risk_score": score,
            "risk_level": level,
            "reason": reason,
            "detail_notes": detail_notes,
            "final_status": final_status,
        }

    except Exception as exc:
        logger.error("Gemini risk scoring failed: %s", exc)
        return {
            "risk_score": None,
            "risk_level": None,
            "reason": f"AI scoring unavailable: {exc}",
            "detail_notes": "",
            "final_status": "PENDING",   # safe fallback
        }
