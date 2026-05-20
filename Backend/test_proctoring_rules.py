from types import SimpleNamespace

from core.proctoring import summarize_proctoring


def make_row(event_type: str, risk_delta: float) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        risk_delta=risk_delta,
        evidence_json="{}",
    )


def test_permissions_denied_hard_blocks_attempt():
    summary = summarize_proctoring([make_row("permissions_denied", 7)])

    assert summary["blocked"] is True
    assert summary["risk_level"] == "severe"
    assert summary["block_reason"] == "camera_or_permission_denied"


def test_screen_share_loss_hard_blocks_attempt():
    summary = summarize_proctoring([make_row("screen_share_stopped", 6)])

    assert summary["blocked"] is True
    assert summary["risk_level"] == "severe"
    assert summary["block_reason"] == "screen_share_stopped"
