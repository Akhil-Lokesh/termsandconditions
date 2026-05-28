"""Catalog of expected consumer protections.

The detector flags PRESENT risky clauses. This module is the inverse —
protective clauses that *should* be in a fair ToS / Privacy Policy and
that we want to flag when they're ABSENT.

The reference comparison tool's "Missing clauses (5)" panel comes from
exactly this kind of checklist. It's a different capability from the
risk-pattern detector: the risk catalog asks "is bad thing X here?",
this asks "is good thing Y missing?"

Severity if ABSENT:
- "high_if_missing": absence is a serious red flag (e.g., no opt-out
  from arbitration, no clear data-deletion path).
- "medium_if_missing": notable but not a blocker.
- "low_if_missing": worth noting; many doc types omit these.

The LLM is asked to mark each protection as present | partial | absent.
"absent" produces a finding with severity = severity_if_missing.
"""

from __future__ import annotations

from typing import List, TypedDict


class ExpectedProtection(TypedDict, total=False):
    id: str
    title: str
    severity_if_missing: str
    category: str
    description: str
    keywords: List[str]
    # When True, the LLM must first establish that the protection is
    # RELEVANT to this specific document type/jurisdiction/feature set
    # before reporting it as absent. Some protections only apply when
    # the doc has the corresponding risk (e.g., arbitration_opt_out
    # only matters if the doc imposes binding arbitration).
    requires_context: bool
    # Plain-English statement of what makes this protection RELEVANT.
    # Used by the LLM to gate the absence check.
    relevance_test: str


EXPECTED_PROTECTIONS: List[ExpectedProtection] = [
    # ---- Dispute resolution / legal recourse ------------------------------
    {
        "id": "arbitration_opt_out",
        "title": "Arbitration opt-out window",
        "severity_if_missing": "high_if_missing",
        "category": "arbitration",
        "description": "If the doc imposes binding arbitration, users should have a 30-day window to opt out without penalty. Absence locks users into arbitration with no escape.",
        "keywords": ["opt out", "opt-out", "30 days", "reject arbitration"],
        "requires_context": True,
        "relevance_test": "Only relevant if the document imposes binding individual arbitration. UK / EU consumer terms typically do not — they preserve court access. If the doc does not force arbitration, mark this protection 'not_applicable'.",
    },
    {
        "id": "small_claims_carve_out",
        "title": "Small-claims court carve-out",
        "severity_if_missing": "medium_if_missing",
        "category": "arbitration",
        "description": "Even with binding arbitration, users should retain the right to pursue claims in small-claims court for low-value disputes.",
        "keywords": ["small claims", "small-claims court"],
        "requires_context": True,
        "relevance_test": "Only relevant if the doc imposes arbitration. If the doc preserves court access, mark 'not_applicable'.",
    },
    # (REMOVED: injunctive_relief_preserved — inverted logic, same class as
    # moral_rights_preserved. Nearly every ToS reserves injunctive relief for the
    # company only; flagging the absence of a symmetric consumer right fired as a
    # false positive on almost every document.)

    # ---- Data protection / privacy ---------------------------------------
    {
        "id": "data_deletion_right",
        "title": "Right to delete personal data",
        "severity_if_missing": "high_if_missing",
        "category": "data",
        "description": "Users should be able to request deletion of their personal data with a clear process and committed timeline.",
        "keywords": ["delete", "deletion", "erase", "right to erasure", "right to be forgotten"],
    },
    {
        "id": "data_export_right",
        "title": "Right to export / portability of data",
        "severity_if_missing": "medium_if_missing",
        "category": "data",
        "description": "Users should be able to download a copy of their data in a portable format (GDPR Art. 20).",
        "keywords": ["data portability", "download your data", "export"],
    },
    {
        "id": "data_access_right",
        "title": "Right to access personal data",
        "severity_if_missing": "medium_if_missing",
        "category": "data",
        "description": "Users should be able to request a copy of personal data held about them (GDPR Art. 15, CCPA right to know).",
        "keywords": ["access your data", "data subject access", "DSAR"],
    },
    {
        "id": "advertising_optout",
        "title": "Opt-out from targeted advertising",
        "severity_if_missing": "high_if_missing",
        "category": "privacy",
        "description": "Users should be able to opt out of cross-context behavioral / targeted advertising (CCPA, GDPR, GPC).",
        "keywords": ["opt out of advertising", "do not sell", "do not share", "targeted ads"],
        "requires_context": True,
        "relevance_test": "Only relevant if the doc describes behavioral / cross-context / targeted advertising or data sale. Subscription-only services (e.g. Apple Music, Netflix) that don't run ad networks should mark this 'not_applicable'.",
    },
    {
        "id": "retention_period_specific",
        "title": "Specific data retention periods",
        "severity_if_missing": "medium_if_missing",
        "category": "data",
        "description": "Concrete retention periods (e.g., '24 months after last login') rather than vague 'as long as necessary'.",
        "keywords": ["retention period", "we retain", "we will keep"],
        "requires_context": True,
        "relevance_test": "Only relevant for documents that collect and store personal data (privacy policies, or a ToS with a data-handling section). A pure ToS with no personal-data processing should mark 'not_applicable'.",
    },
    {
        "id": "breach_notification",
        "title": "Data breach notification commitment",
        "severity_if_missing": "medium_if_missing",
        "category": "data",
        "description": "Commitment to notify users of data breaches affecting their personal data, with a timeline.",
        "keywords": ["data breach", "notify you", "security incident"],
        "requires_context": True,
        "relevance_test": "Only relevant for documents that collect and store personal data (privacy policies, or a ToS with a data-handling section). A pure ToS with no personal-data processing should mark 'not_applicable'.",
    },

    # ---- Account / service ------------------------------------------------
    {
        "id": "advance_notice_for_changes",
        "title": "Advance notice for material terms changes",
        "severity_if_missing": "high_if_missing",
        "category": "modification",
        "description": "Material changes to the terms should be communicated with reasonable advance notice (typically 30 days) and an opportunity to disagree.",
        "keywords": ["advance notice", "30 days notice", "we will notify you"],
        "requires_context": True,
        "relevance_test": "Only relevant if the document reserves a right to modify the terms (e.g. 'we may update these terms'). A fixed agreement with no unilateral modification clause should mark 'not_applicable'.",
    },
    {
        "id": "termination_appeals_process",
        "title": "Appeal process for account termination",
        "severity_if_missing": "medium_if_missing",
        "category": "termination",
        "description": "Users should be able to appeal an account termination decision through a defined process.",
        "keywords": ["appeal", "request reinstatement", "challenge our decision"],
        "requires_context": True,
        "relevance_test": "Only relevant for services with user accounts that can be terminated or suspended. A document with no account model should mark 'not_applicable'.",
    },
    {
        "id": "refund_on_termination",
        "title": "Pro-rata refund of prepaid amounts",
        "severity_if_missing": "medium_if_missing",
        "category": "payment",
        "description": "If the company terminates the relationship without cause, users should receive a pro-rata refund of any prepaid amounts.",
        "keywords": ["refund", "pro-rata", "prepaid"],
        "requires_context": True,
        "relevance_test": "Only relevant for paid services (subscriptions, prepaid credits, virtual currency). Free-only services should mark 'not_applicable'.",
    },

    # ---- Content / IP -----------------------------------------------------
    {
        "id": "license_end_on_deletion",
        "title": "Content license terminates on deletion",
        "severity_if_missing": "high_if_missing",
        "category": "content",
        "description": "When a user deletes their content (or their account), the company's license to that content should end.",
        "keywords": ["license terminates", "license ends", "when you delete"],
        "requires_context": True,
        "relevance_test": "Only relevant if the doc grants the company a license over user-generated content. Pure consumption services (music streaming, video streaming) where users don't upload content should mark 'not_applicable'.",
    },
    # (REMOVED: moral_rights_preserved — inverted logic. The protective
    # state IS the absence of a waiver, so the present/partial/absent
    # framing produces the wrong signal. The corresponding risk pattern
    # `moral_rights_waiver` in risk_patterns.py covers the positive case
    # — if the doc waives moral rights, that fires; if it doesn't waive
    # them, no finding is needed.)

    # ---- Liability / fairness --------------------------------------------
    {
        "id": "consumer_law_savings",
        "title": "Consumer law non-derogation clause",
        "severity_if_missing": "low_if_missing",
        "category": "liability",
        "description": "Statement that nothing in the agreement limits rights consumers have under applicable consumer-protection law.",
        "keywords": ["nothing in this", "consumer rights", "statutory rights"],
        "requires_context": True,
        "relevance_test": "Only relevant where mandatory consumer-protection law applies (UK / EU / Australia consumer contracts). A US-only or B2B agreement may legitimately omit it — mark 'not_applicable' if the doc shows no consumer-law jurisdiction.",
    },
]


def get_protections_summary() -> dict:
    """Counts by severity_if_missing — useful for stats."""
    from collections import Counter
    return dict(Counter(p["severity_if_missing"] for p in EXPECTED_PROTECTIONS))
