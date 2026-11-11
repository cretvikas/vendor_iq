"""Email dispatch service using Python's built-in smtplib.

Sends vendor decision emails (APPROVED / REJECTED / MANUAL REVIEW) automatically.
No third-party package required.

Configure in .env:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""
from __future__ import annotations
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Pipeline stage metadata ───────────────────────────────────────────────────
STAGE_META = {
    "DOCUMENT_VERIFICATION": {"label": "Document Verification", "order": 1, "icon": "📄"},
    "IDENTITY_TAX_VALIDATION": {"label": "Identity & Tax Validation", "order": 2, "icon": "🆔"},
    "FINANCIAL_COMPLIANCE": {"label": "Financial Compliance", "order": 3, "icon": "🏦"},
    "BUSINESS_PROCUREMENT": {"label": "Business & Procurement", "order": 4, "icon": "📋"},
    "AI_RISK_ASSESSMENT": {"label": "AI Risk Assessment", "order": 5, "icon": "🤖"},
}

STAGE_ORDER = ["DOCUMENT_VERIFICATION", "IDENTITY_TAX_VALIDATION", "FINANCIAL_COMPLIANCE", "BUSINESS_PROCUREMENT", "AI_RISK_ASSESSMENT"]


def send_vendor_email(to: str, subject: str, body_plain: str, body_html: str | None = None) -> bool:
    """
    Send an email via configured SMTP server.
    Returns True if sent successfully, False otherwise (never raises).
    """
    from ..config import settings  # local import avoids circular

    if not settings.email_enabled:
        # In demo mode, simulate a successful send so the UI shows "Sent"
        if settings.verification_mode == "demo":
            logger.info("Demo mode — simulating email send to %s", to)
            return True
        logger.info("Email not configured — skipping send to %s", to)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject

        # Plain-text part
        msg.attach(MIMEText(body_plain, "plain", "utf-8"))

        # HTML part
        html = body_html or body_plain.replace("\n", "<br>")
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_from, [to], msg.as_string())

        logger.info("Email sent to %s — subject: %s", to, subject)
        return True

    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)
        return False


# ── Pipeline HTML builder ─────────────────────────────────────────────────────

def _stage_status_style(status: str) -> dict:
    """Return inline styles for a pipeline stage based on its status."""
    if status == "PASS":
        return {
            "bg": "#ecfdf5", "border": "#10b981", "color": "#059669",
            "icon": "✅", "label": "Passed", "label_bg": "#d1fae5",
        }
    elif status == "FAIL":
        return {
            "bg": "#fef2f2", "border": "#ef4444", "color": "#dc2626",
            "icon": "❌", "label": "Failed", "label_bg": "#fee2e2",
        }
    elif status == "NEEDS_INFORMATION":
        return {
            "bg": "#fffbeb", "border": "#f59e0b", "color": "#d97706",
            "icon": "⏳", "label": "Needs Review", "label_bg": "#fef3c7",
        }
    else:
        return {
            "bg": "#f8fafc", "border": "#cbd5e1", "color": "#94a3b8",
            "icon": "⬜", "label": "Not Reached", "label_bg": "#f1f5f9",
        }


def build_pipeline_html(stages: list[dict], final_status: str) -> str:
    """Generate the HTML pipeline visualization section for emails."""
    # Sort stages by order
    sorted_stages = sorted(stages, key=lambda s: STAGE_META.get(s.get("stage"), {}).get("order", 99))

    # Build the set of stages we have data for
    stage_map = {s["stage"]: s for s in sorted_stages}

    # Determine if there's a failure — stages after first failure are "not reached"
    first_fail_order = 999
    for stage_key in STAGE_ORDER:
        if stage_key in stage_map and stage_map[stage_key].get("status") == "FAIL":
            first_fail_order = STAGE_META[stage_key]["order"]
            break

    rows_html = ""
    for stage_key in STAGE_ORDER:
        meta = STAGE_META[stage_key]
        stage_data = stage_map.get(stage_key)

        if stage_data and meta["order"] <= first_fail_order:
            status = stage_data.get("status", "PASS")
        elif meta["order"] > first_fail_order:
            status = "NOT_REACHED"
        elif not stage_data:
            status = "NOT_REACHED"
        else:
            status = stage_data.get("status", "PASS")

        style = _stage_status_style(status)
        summary = ""
        if stage_data and meta["order"] <= first_fail_order:
            summary = stage_data.get("summary", "")

        # Build findings HTML for failed stages
        findings_html = ""
        if status == "FAIL" and stage_data:
            findings = stage_data.get("findings", [])
            if findings:
                items = "".join(
                    f'<li style="margin:0 0 4px;padding:4px 0;font-size:13px;color:#991b1b;line-height:1.5;">{f}</li>'
                    for f in findings
                )
                findings_html = f'''
                <div style="margin-top:8px;background:#fff5f5;border:1px solid #fecaca;border-radius:6px;padding:10px 12px;">
                    <div style="font-size:10px;font-weight:700;color:#991b1b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">⚠ Issues Found</div>
                    <ul style="margin:0;padding:0 0 0 16px;">{items}</ul>
                </div>'''

        rows_html += f'''
        <tr>
            <td style="padding:12px 14px;border-bottom:1px solid #f1f5f9;width:44px;vertical-align:top;">
                <div style="width:36px;height:36px;border-radius:50%;background:{style['bg']};border:2px solid {style['border']};display:inline-block;text-align:center;line-height:32px;font-size:18px;">
                    {style['icon']}
                </div>
            </td>
            <td style="padding:12px 14px 12px 0;border-bottom:1px solid #f1f5f9;vertical-align:top;">
                <div style="font-weight:700;color:#1e293b;font-size:14px;margin-bottom:2px;">{meta['icon']} {meta['label']}</div>
                <div style="font-size:12px;color:#64748b;line-height:1.4;">{summary}</div>
                {findings_html}
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid #f1f5f9;text-align:right;vertical-align:top;width:100px;">
                <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;background:{style['label_bg']};color:{style['color']};letter-spacing:0.3px;">
                    {style['label']}
                </span>
            </td>
        </tr>'''

    # Status banner
    if final_status == "APPROVED":
        banner_bg = "linear-gradient(135deg, #059669 0%, #10b981 100%)"
        banner_text = "✅ All verification stages passed — Application Approved"
    elif final_status == "REJECTED":
        banner_bg = "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)"
        banner_text = "❌ Verification failed — Application could not be approved"
    else:
        banner_bg = "linear-gradient(135deg, #d97706 0%, #f59e0b 100%)"
        banner_text = "⏳ Under Manual Review — Our team is reviewing your application"

    return f'''
    <div style="margin:20px 0;">
        <div style="background:{banner_bg};color:#fff;padding:14px 18px;border-radius:10px 10px 0 0;font-weight:700;font-size:14px;letter-spacing:-0.2px;">
            {banner_text}
        </div>
        <table style="width:100%;border-collapse:collapse;background:#ffffff;border:1px solid #e2e8f0;border-top:0;border-radius:0 0 10px 10px;overflow:hidden;" cellpadding="0" cellspacing="0">
            <thead>
                <tr>
                    <th style="padding:10px 14px;text-align:left;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e2e8f0;background:#f8fafc;" colspan="2">Verification Stage</th>
                    <th style="padding:10px 14px;text-align:right;font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #e2e8f0;background:#f8fafc;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>'''


def _wrap_email_html(content: str) -> str:
    """Wrap email content in the premium VendorIQ email template."""
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family:'Segoe UI',Arial,Helvetica,sans-serif;background:#f1f5f9;margin:0;padding:0;-webkit-font-smoothing:antialiased;">
    <div style="max-width:600px;margin:32px auto;background:#ffffff;border-radius:14px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1e40af 100%);padding:32px 32px 28px;color:#ffffff;">
            <div style="display:inline-block;width:36px;height:36px;background:rgba(255,255,255,0.15);border-radius:10px;text-align:center;line-height:36px;font-size:18px;margin-bottom:12px;">🏢</div>
            <h1 style="margin:0;font-size:22px;font-weight:800;letter-spacing:-0.5px;line-height:1.3;">VendorIQ</h1>
            <p style="margin:6px 0 0;font-size:12px;opacity:0.7;letter-spacing:0.5px;">VENDOR ONBOARDING PLATFORM</p>
        </div>

        <!-- Body -->
        <div style="padding:28px 32px 32px;color:#334155;font-size:14px;line-height:1.7;">
            {content}
        </div>

        <!-- Footer -->
        <div style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:11px;line-height:1.5;">
            <p style="margin:0;">This is an automated notification from <strong style="color:#64748b;">VendorIQ</strong>. Please do not reply directly to this email.</p>
            <p style="margin:6px 0 0;font-size:10px;">If you have questions, contact your procurement representative and reference your application number.</p>
        </div>
    </div>
</body>
</html>'''


# ── Email content builders ────────────────────────────────────────────────────

def build_approval_email(vendor, stages: list[dict] | None = None) -> tuple[str, str, str]:
    """Build approval email with pipeline visualization. Returns (subject, plain_text, html)."""
    subject = f"✅ Your vendor application has been approved — VendorIQ #{vendor.id}"

    plain_body = f"""Hello {vendor.contact_name},

We are pleased to inform you that the vendor application submitted for {vendor.legal_name} has been reviewed and APPROVED.

All verification stages have been completed successfully:
✅ Document Verification — Passed
✅ Identity & Tax Validation — Passed
✅ Financial Compliance — Passed
✅ Business & Procurement — Passed
✅ AI Risk Assessment — Passed

You are now registered as an approved supplier in our system. Our procurement team will reach out to you shortly with the next steps for onboarding.

Application reference: #{vendor.id}
Supplier category: {vendor.supplier_category}
Approval date: {__import__('datetime').datetime.utcnow().strftime('%d %B %Y')}

If you have any questions, please contact your procurement representative.

Regards,
Vendor Onboarding Team
VendorIQ"""

    pipeline_html = build_pipeline_html(stages or [], "APPROVED")

    html_content = f'''
        <p style="font-size:16px;margin:0 0 6px;">Hello <strong>{vendor.contact_name}</strong>,</p>
        <p style="margin:0 0 20px;">We are pleased to inform you that the vendor application for <strong>{vendor.legal_name}</strong> has been reviewed and <span style="color:#059669;font-weight:700;">APPROVED</span>.</p>

        {pipeline_html}

        <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:16px 18px;margin:20px 0;">
            <div style="font-weight:700;color:#059669;font-size:14px;margin-bottom:6px;">🎉 Welcome aboard!</div>
            <p style="margin:0;font-size:13px;color:#065f46;line-height:1.5;">You are now registered as an approved supplier. Our procurement team will reach out shortly with the next steps for onboarding.</p>
        </div>

        <table style="width:100%;border-collapse:collapse;margin:16px 0;" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px 0 0 6px;font-size:11px;color:#64748b;font-weight:700;">Application Ref</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;font-size:11px;color:#1e293b;font-weight:600;">#{vendor.id}</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;font-size:11px;color:#64748b;font-weight:700;">Category</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 6px 6px 0;font-size:11px;color:#1e293b;font-weight:600;">{vendor.supplier_category}</td>
            </tr>
        </table>

        <p style="margin:16px 0 0;font-size:13px;color:#64748b;">If you have any questions, please contact your procurement representative.</p>
        <p style="margin:8px 0 0;font-size:13px;color:#334155;">Regards,<br><strong>Vendor Onboarding Team</strong></p>
    '''

    html_body = _wrap_email_html(html_content)
    return subject, plain_body, html_body


def build_rejection_email(vendor, stages: list[dict] | None = None) -> tuple[str, str, str]:
    """Build rejection email with pipeline showing which stage failed. Returns (subject, plain_text, html)."""
    subject = f"❌ Your vendor application could not be approved — VendorIQ #{vendor.id}"
    reason_text = vendor.ai_risk_reason or "The application did not meet our onboarding criteria."

    # Find failing stage
    failing_stages = []
    for s in (stages or []):
        if s.get("status") == "FAIL":
            meta = STAGE_META.get(s.get("stage"), {})
            failing_stages.append(meta.get("label", s.get("stage", "Unknown")))

    failing_stage_text = ", ".join(failing_stages) if failing_stages else "verification"

    plain_body = f"""Hello {vendor.contact_name},

Thank you for submitting a vendor application for {vendor.legal_name}. After careful review, we are unable to approve it at this time.

Your application was rejected at the {failing_stage_text} stage.

Reason: {reason_text}

Application reference: #{vendor.id}

If you believe this decision is incorrect, or if you have additional supporting documents that address the concerns above, please contact our compliance team and reference the application number above.

Regards,
Vendor Onboarding Team
VendorIQ"""

    pipeline_html = build_pipeline_html(stages or [], "REJECTED")

    html_content = f'''
        <p style="font-size:16px;margin:0 0 6px;">Hello <strong>{vendor.contact_name}</strong>,</p>
        <p style="margin:0 0 20px;">Thank you for submitting a vendor application for <strong>{vendor.legal_name}</strong>. After careful review, we are unable to approve it at this time.</p>

        {pipeline_html}

        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:16px 18px;margin:20px 0;">
            <div style="font-weight:700;color:#dc2626;font-size:13px;margin-bottom:6px;">Reason for Decision</div>
            <p style="margin:0;font-size:13px;color:#7f1d1d;line-height:1.6;">{reason_text}</p>
        </div>

        <table style="width:100%;border-collapse:collapse;margin:16px 0;" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:11px;color:#64748b;font-weight:700;">Application Ref</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:11px;color:#1e293b;font-weight:600;">#{vendor.id}</td>
            </tr>
        </table>

        <p style="margin:16px 0 0;font-size:13px;color:#64748b;line-height:1.6;">If you believe this decision is incorrect, or if you have additional supporting documents, please contact our compliance team and reference application <strong>#{vendor.id}</strong>.</p>
        <p style="margin:8px 0 0;font-size:13px;color:#334155;">Regards,<br><strong>Vendor Onboarding Team</strong></p>
    '''

    html_body = _wrap_email_html(html_content)
    return subject, plain_body, html_body


def build_manual_review_email(vendor, stages: list[dict] | None = None) -> tuple[str, str, str]:
    """Build manual review email with pipeline showing current progress. Returns (subject, plain_text, html)."""
    subject = f"⏳ Your vendor application is under review — VendorIQ #{vendor.id}"

    plain_body = f"""Hello {vendor.contact_name},

Thank you for submitting a vendor application for {vendor.legal_name}. Your application has been received and is currently under manual review by our team.

Our verification system has completed its automated checks, and your application has been forwarded to our team for further evaluation. We will notify you as soon as a decision has been made.

Application reference: #{vendor.id}
Supplier category: {vendor.supplier_category}

No action is required from you at this time. If you have any questions, please contact your procurement representative and reference the application number above.

Regards,
Vendor Onboarding Team
VendorIQ"""

    pipeline_html = build_pipeline_html(stages or [], "PENDING")

    html_content = f'''
        <p style="font-size:16px;margin:0 0 6px;">Hello <strong>{vendor.contact_name}</strong>,</p>
        <p style="margin:0 0 20px;">Thank you for submitting a vendor application for <strong>{vendor.legal_name}</strong>. Your application is currently <span style="color:#d97706;font-weight:700;">under manual review</span>.</p>

        {pipeline_html}

        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:16px 18px;margin:20px 0;">
            <div style="font-weight:700;color:#b45309;font-size:13px;margin-bottom:6px;">⏳ What happens next?</div>
            <p style="margin:0;font-size:13px;color:#78350f;line-height:1.6;">Our team is reviewing your application. This typically takes 1–3 business days. You will receive an email notification once a decision has been made. No action is required from you at this time.</p>
        </div>

        <table style="width:100%;border-collapse:collapse;margin:16px 0;" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px 0 0 6px;font-size:11px;color:#64748b;font-weight:700;">Application Ref</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;font-size:11px;color:#1e293b;font-weight:600;">#{vendor.id}</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;font-size:11px;color:#64748b;font-weight:700;">Category</td>
                <td style="padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 6px 6px 0;font-size:11px;color:#1e293b;font-weight:600;">{vendor.supplier_category}</td>
            </tr>
        </table>

        <p style="margin:16px 0 0;font-size:13px;color:#64748b;">If you have questions, please contact your procurement representative.</p>
        <p style="margin:8px 0 0;font-size:13px;color:#334155;">Regards,<br><strong>Vendor Onboarding Team</strong></p>
    '''

    html_body = _wrap_email_html(html_content)
    return subject, plain_body, html_body
