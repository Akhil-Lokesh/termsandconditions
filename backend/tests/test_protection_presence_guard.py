"""Tests for the missing-protection presence guard.

Regression for the "advance notice inversion" bug (Meta ToS, first run): the
missing-protections pass flagged advance_notice_for_changes as HIGH even though
the document explicitly granted 30-day advance notice. The deterministic
presence guard suppresses such false-absent findings.
"""

from app.core.expected_protections import (
    EXPECTED_PROTECTIONS,
    protection_is_present,
)

ADVANCE_NOTICE = next(
    p for p in EXPECTED_PROTECTIONS if p["id"] == "advance_notice_for_changes"
)


def test_meta_30_day_notice_is_detected_as_present():
    """The exact Meta §4.1 wording must register the protection as present."""
    doc = (
        "We may change these Terms. We will notify you of material changes and "
        "give you the opportunity to review them, at least 30 days before we "
        "make changes, where required by law."
    )
    assert protection_is_present(ADVANCE_NOTICE, doc) is True


def test_advance_notice_present_variants():
    for doc in [
        "We will give you 30 days' prior notice before changing these terms.",
        "Material modifications take effect 14 days before we modify the service.",
        "We provide advance notice before any change to this agreement.",
    ]:
        assert protection_is_present(ADVANCE_NOTICE, doc) is True, doc


def test_absent_when_no_notice_commitment():
    """A doc that changes terms with NO notice commitment is genuinely missing
    the protection — guard must not suppress it."""
    doc = (
        "We reserve the right to modify these Terms at any time. Your continued "
        "use of the service constitutes acceptance of the revised Terms."
    )
    assert protection_is_present(ADVANCE_NOTICE, doc) is False


def test_protection_without_indicators_is_never_guarded():
    """Protections that define no presence_indicators keep prior behaviour."""
    no_indicator = {"id": "x", "title": "y"}
    assert protection_is_present(no_indicator, "anything at all") is False


def test_guard_is_case_insensitive():
    doc = "WE WILL NOTIFY YOU AT LEAST 30 DAYS BEFORE WE MAKE CHANGES."
    assert protection_is_present(ADVANCE_NOTICE, doc) is True
