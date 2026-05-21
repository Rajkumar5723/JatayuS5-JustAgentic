"""
Shared email helper for all Hiresy services.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import smtplib
import socket
import ssl
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings
from core.database import SessionLocal

logger = logging.getLogger(__name__)

_LOGO_CACHE: str | None = None
SMTP_HOST = "smtp.gmail.com"
SMTP_SSL_PORT = 465
SMTP_STARTTLS_PORT = 587
SMTP_TIMEOUT = 20
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT = 20


def _ipv4_sockaddrs(host: str, port: int) -> list[tuple]:
    return [
        info[4]
        for info in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    ]


def _connect_smtp_ssl_ipv4(host: str, port: int, context: ssl.SSLContext) -> smtplib.SMTP_SSL:
    last_exc: Exception | None = None
    for sockaddr in _ipv4_sockaddrs(host, port):
        try:
            raw_sock = socket.create_connection(sockaddr, timeout=SMTP_TIMEOUT)
            ssl_sock = context.wrap_socket(raw_sock, server_hostname=host)
            server = smtplib.SMTP_SSL(timeout=SMTP_TIMEOUT, context=context)
            server.sock = ssl_sock
            server.file = ssl_sock.makefile("rb")
            server._host = host
            code, msg = server.getreply()
            if code != 220:
                server.close()
                raise smtplib.SMTPConnectError(code, msg)
            return server
        except Exception as exc:
            last_exc = exc
    raise last_exc or OSError("No IPv4 SMTP SSL address available")


def _connect_smtp_starttls_ipv4(host: str, port: int, context: ssl.SSLContext) -> smtplib.SMTP:
    last_exc: Exception | None = None
    for sockaddr in _ipv4_sockaddrs(host, port):
        server = smtplib.SMTP(timeout=SMTP_TIMEOUT)
        try:
            server.connect(sockaddr[0], port)
            server._host = host
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            return server
        except Exception as exc:
            last_exc = exc
            try:
                server.close()
            except Exception:
                pass
    raise last_exc or OSError("No IPv4 SMTP STARTTLS address available")


def _load_logo() -> str:
    global _LOGO_CACHE
    if _LOGO_CACHE is not None:
        return _LOGO_CACHE

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "emaillogo.jpg"),
        os.path.join(here, "..", "..", "Backend", "emaillogo.jpg"),
        os.path.join(here, "..", "..", "Frontend", "public", "emaillogo.jpg"),
        os.path.join(here, "..", "..", "frontend", "public", "emaillogo.jpg"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                _LOGO_CACHE = base64.b64encode(fh.read()).decode()
            logger.info("Email logo loaded from %s", path)
            return _LOGO_CACHE

    logger.warning("emaillogo.jpg not found - emails will have no logo")
    _LOGO_CACHE = ""
    return _LOGO_CACHE


def _wrap_body(body_html: str, company: str = "Hiresy") -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f4f4f4;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
  <tr><td align="center">
  <table width="560" cellpadding="0" cellspacing="0"
         style="background:#fff;border-radius:12px;overflow:hidden;
                box-shadow:0 2px 16px rgba(0,0,0,0.07);">
    <tr><td style="padding:28px 40px 22px;text-align:center;
                   background:#0a0a0a;border-bottom:3px solid #ff4400;">
      <span style="font-size:26px;font-weight:900;color:#ff4400;letter-spacing:-1px;">{company}</span>
      <span style="font-size:12px;color:#666;display:block;margin-top:2px;">AI Hiring Platform</span>
    </td></tr>
    <tr><td style="padding:36px 40px;">
      {body_html}
    </td></tr>
    <tr><td style="padding:18px 40px;background:#fafafa;border-top:1px solid #f0f0f0;">
      <p style="margin:0;font-size:11px;color:#ccc;text-align:center;">
        {company} AI Hiring Platform &middot; Automated email &mdash; please do not reply.
      </p>
    </td></tr>
  </table>
  </td></tr>
</table>
</body>
</html>"""


def _log_email(
    *,
    to: str,
    subject: str,
    stage: str | None,
    status: str,
    provider: str = "smtp_ssl_gmail",
    error_message: str | None = None,
    application_id: int | None = None,
    test_session_id: int | None = None,
    coding_session_id: int | None = None,
    live_session_id: int | None = None,
    verification_case_id: int | None = None,
    meta: dict | None = None,
) -> None:
    try:
        from core.models import EmailDeliveryLog

        db = SessionLocal()
        try:
            db.add(
                EmailDeliveryLog(
                    to_email=to,
                    subject=subject,
                    stage=stage,
                    status=status,
                    provider=provider,
                    error_message=error_message,
                    application_id=application_id,
                    test_session_id=test_session_id,
                    coding_session_id=coding_session_id,
                    live_session_id=live_session_id,
                    verification_case_id=verification_case_id,
                    meta_json=json.dumps(meta or {}),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover
        logger.warning("Email log write failed for %s | %s | %s", to, subject, exc)


def send_email(
    to: str,
    subject: str,
    body_html: str,
    *,
    company: str = "Hiresy",
    wrap: bool = True,
    stage: str | None = None,
    application_id: int | None = None,
    test_session_id: int | None = None,
    coding_session_id: int | None = None,
    live_session_id: int | None = None,
    verification_case_id: int | None = None,
    meta: dict | None = None,
) -> bool:
    smtp_pass = (settings.SMTP_PASS or "").strip()
    if " " in smtp_pass and len(smtp_pass.replace(" ", "")) == 16:
        smtp_pass = smtp_pass.replace(" ", "")
    email_provider = settings.email_provider
    resend_configured = bool(settings.RESEND_API_KEY)
    smtp_configured = bool(settings.SMTP_USER and smtp_pass)

    if settings.DISABLE_EMAIL_DELIVERY:
        logger.info("Email delivery disabled - skipping email to %s", to)
        _log_email(
            to=to,
            subject=subject,
            stage=stage,
            status="skipped",
            provider=email_provider,
            error_message="email_delivery_disabled",
            application_id=application_id,
            test_session_id=test_session_id,
            coding_session_id=coding_session_id,
            live_session_id=live_session_id,
            verification_case_id=verification_case_id,
            meta=meta,
        )
        return False

    if email_provider == "resend" and not resend_configured:
        logger.warning("Resend not configured - skipping email to %s", to)
        _log_email(
            to=to,
            subject=subject,
            stage=stage,
            status="skipped",
            provider="resend",
            error_message="resend_not_configured",
            application_id=application_id,
            test_session_id=test_session_id,
            coding_session_id=coding_session_id,
            live_session_id=live_session_id,
            verification_case_id=verification_case_id,
            meta=meta,
        )
        return False

    html = _wrap_body(body_html, company) if wrap else body_html

    def _send_via_resend() -> tuple[bool, str | None, str | None]:
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        message_hash = hashlib.sha256(f"{to}|{subject}".encode("utf-8")).hexdigest()[:12]
        idempotency_bits = [
            "hiresy",
            stage or "general",
            str(application_id or "na"),
            str(test_session_id or coding_session_id or live_session_id or verification_case_id or "na"),
            message_hash,
        ]
        headers["Idempotency-Key"] = "-".join(idempotency_bits)
        payload = {
            "from": settings.resend_from_addr,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        res = requests.post(RESEND_API_URL, headers=headers, json=payload, timeout=RESEND_TIMEOUT)
        if res.status_code >= 400:
            raise RuntimeError(f"resend_http_{res.status_code}: {res.text[:500]}")
        data = res.json() if res.content else {}
        return True, data.get("id"), None

    def _send_via_smtp() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{company} <{settings.smtp_from_addr}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()
        send_errors: list[str] = []
        try:
            with _connect_smtp_ssl_ipv4(SMTP_HOST, SMTP_SSL_PORT, context) as server:
                server.login(settings.SMTP_USER, smtp_pass)
                server.sendmail(settings.smtp_from_addr, to, msg.as_string())
        except Exception as ssl_exc:
            send_errors.append(f"smtp_ssl_465_ipv4: {ssl_exc}")
            try:
                with _connect_smtp_starttls_ipv4(SMTP_HOST, SMTP_STARTTLS_PORT, context) as server:
                    server.login(settings.SMTP_USER, smtp_pass)
                    server.sendmail(settings.smtp_from_addr, to, msg.as_string())
            except Exception as starttls_exc:
                raise RuntimeError("; ".join([*send_errors, f"smtp_starttls_587_ipv4: {starttls_exc}"]))

    providers: list[str] = []
    if email_provider == "resend":
        providers = ["resend"]
    elif email_provider == "smtp":
        providers = ["smtp"]
    else:
        providers = ["resend", "smtp"] if resend_configured else ["smtp"]

    errors: list[str] = []
    for provider in providers:
        try:
            if provider == "resend":
                if not resend_configured:
                    errors.append("resend_not_configured")
                    continue
                _, resend_id, _ = _send_via_resend()
                logger.info("Email sent via Resend -> %s | %s | %s", to, subject, resend_id)
                meta_with_provider = {**(meta or {}), "resend_id": resend_id}
                _log_email(
                    to=to,
                    subject=subject,
                    stage=stage,
                    status="sent",
                    provider="resend",
                    application_id=application_id,
                    test_session_id=test_session_id,
                    coding_session_id=coding_session_id,
                    live_session_id=live_session_id,
                    verification_case_id=verification_case_id,
                    meta=meta_with_provider,
                )
                return True

            if not smtp_configured:
                errors.append("smtp_not_configured")
                continue
            _send_via_smtp()
            logger.info("Email sent via SMTP -> %s | %s", to, subject)
            _log_email(
                to=to,
                subject=subject,
                stage=stage,
                status="sent",
                provider="smtp_ssl_gmail",
                application_id=application_id,
                test_session_id=test_session_id,
                coding_session_id=coding_session_id,
                live_session_id=live_session_id,
                verification_case_id=verification_case_id,
                meta=meta,
            )
            return True
        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    error_message = "; ".join(errors) or "email_provider_not_configured"
    logger.error("Email failed -> %s | %s | %s", to, subject, error_message)
    _log_email(
        to=to,
        subject=subject,
        stage=stage,
        status="failed",
        provider=",".join(providers) or email_provider,
        error_message=error_message,
        application_id=application_id,
        test_session_id=test_session_id,
        coding_session_id=coding_session_id,
        live_session_id=live_session_id,
        verification_case_id=verification_case_id,
        meta=meta,
    )
    return False


# ── Candidate Stage Result Emails ──────────────────────────────────

def send_shortlist_result_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    passed: bool,
    application_id: int,
    test_session_id: int | None = None,
    next_round_url: str | None = None,
    assessment_label: str = "Screening Test",
    next_stage_label: str = "Next Interview Round",
) -> bool:
    """Send shortlist test result (pass/reject) email to candidate."""
    if passed:
        button_html = ""
        if next_round_url:
            button_html = f"""
<table cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td style="background:#ff4400;border-radius:8px;">
    <a href="{next_round_url}" style="display:inline-block;padding:14px 36px;font-size:16px;
       font-weight:700;color:#fff;text-decoration:none;">Continue to {next_stage_label}</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Direct link: {next_round_url}</p>
"""
        body_html = f"""
<h2 style="color:#0a0a0a;margin-top:0;">Congratulations! 🎉</h2>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Great news! You have successfully passed the <strong>{assessment_label}</strong> for the 
  <strong>{job_title}</strong> position.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  We are pleased to invite you to the next phase of our hiring process:
  <strong>{next_stage_label}</strong>.
</p>
{button_html}
<p style="color:#444;line-height:1.6;margin:16px 0;">
  If you have any questions, please don't hesitate to contact us.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        subject = f"✓ Passed - Next Round: {next_stage_label} | {job_title}"
    else:
        body_html = f"""
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Thank you for your interest in the position of <strong>{job_title}</strong>. 
  We know it takes time and energy to apply, so we appreciate you considering us.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  The hiring manager has chosen to move forward with another candidate so we will not be able to 
  explore this particular role further at this time. We will continue to consider you for similar 
  roles as they become available, and we look forward to exploring those opportunities with you.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        subject = f"Update on Your Application for {job_title}"

    return send_email(
        to=candidate_email,
        subject=subject,
        body_html=body_html,
        stage="shortlist_test_result",
        application_id=application_id,
        test_session_id=test_session_id,
    )


def send_coding_result_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    passed: bool,
    application_id: int,
    coding_session_id: int | None = None,
    next_round_url: str | None = None,
) -> bool:
    """Send coding test result (pass/reject) email to candidate."""
    if passed:
        button_html = ""
        if next_round_url:
            button_html = f"""
<table cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td style="background:#ff4400;border-radius:8px;">
    <a href="{next_round_url}" style="display:inline-block;padding:14px 36px;font-size:16px;
       font-weight:700;color:#fff;text-decoration:none;">Join Live Interview</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Direct link: {next_round_url}</p>
"""
        body_html = f"""
<h2 style="color:#0a0a0a;margin-top:0;">Excellent Performance! 🌟</h2>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Congratulations! You have successfully passed the <strong>Coding Assessment</strong> for the 
  <strong>{job_title}</strong> position.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  We are impressed with your performance! The next phase will be an 
  <strong>Interactive Live Interview</strong> with our team.
</p>
{button_html}
<p style="color:#444;line-height:1.6;margin:16px 0;">
  If you have any questions, please don't hesitate to contact us.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        subject = f"✓ Passed - Next Round: Live Interview | {job_title}"
    else:
        body_html = f"""
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Thank you for your interest in the position of <strong>{job_title}</strong>. 
  We know it takes time and energy to apply, so we appreciate you considering us.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  The hiring manager has chosen to move forward with another candidate so we will not be able to 
  explore this particular role further at this time. We will continue to consider you for similar 
  roles as they become available, and we look forward to exploring those opportunities with you.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        subject = f"Update on Your Application for {job_title}"

    return send_email(
        to=candidate_email,
        subject=subject,
        body_html=body_html,
        stage="coding_test_result",
        application_id=application_id,
        coding_session_id=coding_session_id,
    )


def send_api_status_update_email(
    candidate_email: str,
    candidate_name: str,
    job_title: str,
    old_status: str,
    new_status: str,
    application_id: int,
    next_round_url: str | None = None,
) -> bool:
    """Send email when application status changes via direct API update."""
    # Only send emails for meaningful transitions
    passing_statuses = [
        "round_2",
        "round_3",
        "joining_pending",
        "bgv_pending",
        "offer_pending",
        "offer_sent",
        "offer_signed",
        "approval_pending",
        "selected",
        "hired",
        "on_hold",
        "onboarding_in_progress",
        "onboarding_completed",
    ]
    if new_status not in passing_statuses + ["rejected"]:
        return True  # Don't send email for internal transitions

    if new_status in passing_statuses:
        stage_name = {
            "round_2": "Coding Assessment",
            "round_3": "Live Interview",
            "joining_pending": "Joining Setup",
            "bgv_pending": "Background Verification",
            "offer_pending": "Offer Preparation",
            "offer_sent": "Offer Letter",
            "offer_signed": "Signed Offer Review",
            "approval_pending": "Final HR Approval",
            "selected": "Final Selection",
            "hired": "Hiring Confirmation",
            "on_hold": "Offer Hold Review",
            "onboarding_in_progress": "Employee Onboarding",
            "onboarding_completed": "Onboarding Complete",
        }.get(new_status, new_status)

        button_html = ""
        if next_round_url:
            button_text = "Start Coding Assessment" if new_status == "round_2" else "Join Live Interview" if new_status == "round_3" else "Continue Process"
            button_html = f"""
<table cellpadding="0" cellspacing="0" style="margin:24px 0;">
  <tr><td style="background:#ff4400;border-radius:8px;">
    <a href="{next_round_url}" style="display:inline-block;padding:14px 36px;font-size:16px;
       font-weight:700;color:#fff;text-decoration:none;">{button_text}</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Direct link: {next_round_url}</p>
"""

        body_html = f"""
<h2 style="color:#0a0a0a;margin-top:0;">Good News! 🎉</h2>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Great news! You have progressed to the next stage: <strong>{stage_name}</strong> for the 
  <strong>{job_title}</strong> position.
</p>
{button_html}
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Thank you for your continued interest.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        if new_status in {"selected", "hired"}:
            body_html = f"""
<h2 style="color:#0a0a0a;margin-top:0;">Congratulations! 🎊</h2>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Excellent news! We are pleased to offer you the position of <strong>{job_title}</strong>.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Our HR team will be in touch with you shortly to discuss the next steps and finalize the details.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Welcome to our team!<br>
  <strong>Hiresy Team</strong>
</p>
"""
            subject = "Congratulations! Job Offer | " + job_title
        else:
            subject = f"✓ Progressed to {stage_name} | {job_title}"
    else:  # rejected
        body_html = f"""
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Hello <strong>{candidate_name}</strong>,
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Thank you for your interest in the position of <strong>{job_title}</strong>. 
  We know it takes time and energy to apply, so we appreciate you considering us.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  The hiring manager has chosen to move forward with another candidate so we will not be able to 
  explore this particular role further at this time. We will continue to consider you for similar 
  roles as they become available, and we look forward to exploring those opportunities with you.
</p>
<p style="color:#444;line-height:1.6;margin:16px 0;">
  Best regards,<br>
  <strong>Hiresy Team</strong>
</p>
"""
        subject = f"Update on Your Application for {job_title}"

    return send_email(
        to=candidate_email,
        subject=subject,
        body_html=body_html,
        stage="api_status_update",
        application_id=application_id,
        meta={"old_status": old_status, "new_status": new_status},
    )
