from core import email_utils
from core.config import settings


def test_send_email_uses_brevo_api(monkeypatch):
    logs = []
    captured = {}

    class Response:
        status_code = 201
        content = b'{"messageId":"brevo-message-1"}'
        text = '{"messageId":"brevo-message-1"}'

        def json(self):
            return {"messageId": "brevo-message-1"}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(settings, "DISABLE_EMAIL_DELIVERY", False)
    monkeypatch.setattr(settings, "BREVO_API", "test-brevo-key")
    monkeypatch.setattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "rkdevzone@gmail.com")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "Hiresy")
    monkeypatch.setattr(email_utils.requests, "post", fake_post)
    monkeypatch.setattr(email_utils, "_log_email", lambda **kwargs: logs.append(kwargs))

    assert email_utils.send_email(
        "candidate@example.com",
        "Assessment invite",
        "<p>Start test</p>",
        stage="shortlisting_test",
        application_id=123,
        meta={"candidate_name": "Rajkumar G"},
    ) is True

    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "test-brevo-key"
    assert captured["json"]["sender"] == {
        "name": "Hiresy",
        "email": "rkdevzone@gmail.com",
    }
    assert captured["json"]["to"] == [{"email": "candidate@example.com", "name": "Rajkumar G"}]
    assert captured["json"]["subject"] == "Assessment invite"
    assert "htmlContent" in captured["json"]
    assert logs[-1]["provider"] == "brevo"
    assert logs[-1]["status"] == "sent"
    assert logs[-1]["meta"]["brevo_message_id"] == "brevo-message-1"


def test_send_email_fails_clearly_when_brevo_missing(monkeypatch):
    logs = []

    monkeypatch.setattr(settings, "DISABLE_EMAIL_DELIVERY", False)
    monkeypatch.setattr(settings, "BREVO_API", "")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "rkdevzone@gmail.com")
    monkeypatch.setattr(email_utils, "_log_email", lambda **kwargs: logs.append(kwargs))

    assert email_utils.send_email("candidate@example.com", "Subject", "<p>Body</p>") is False
    assert logs[-1]["provider"] == "brevo"
    assert logs[-1]["status"] == "failed"
    assert logs[-1]["error_message"] == "brevo_not_configured: missing BREVO_API"


def test_send_email_respects_disable_delivery(monkeypatch):
    logs = []
    posted = {"called": False}

    def fake_post(*args, **kwargs):
        posted["called"] = True
        raise AssertionError("Brevo should not be called when delivery is disabled")

    monkeypatch.setattr(settings, "DISABLE_EMAIL_DELIVERY", True)
    monkeypatch.setattr(settings, "BREVO_API", "test-brevo-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "rkdevzone@gmail.com")
    monkeypatch.setattr(email_utils.requests, "post", fake_post)
    monkeypatch.setattr(email_utils, "_log_email", lambda **kwargs: logs.append(kwargs))

    assert email_utils.send_email("candidate@example.com", "Subject", "<p>Body</p>") is False
    assert posted["called"] is False
    assert logs[-1]["provider"] == "brevo"
    assert logs[-1]["status"] == "skipped"
    assert logs[-1]["error_message"] == "email_delivery_disabled"
