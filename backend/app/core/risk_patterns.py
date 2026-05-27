"""Curated risk-pattern catalog for checklist-based ToS / privacy detection.

The open-ended approach ("look at this document and flag what's risky") makes
the LLM responsible for both *finding* and *evaluating* clauses. Empirically
this misses specific high-severity patterns (TikTok demo: 5 of 6 highest-
impact clauses were not detected at all). LLMs are reliable *matchers* —
unreliable *exhaustive searchers*. This module gives them a list to match
against.

Each pattern includes:
- ``id``: stable slug used by clients/UI
- ``title``: lawyer-style 5-8 word risk title (shows up in cards)
- ``severity``: default severity if the pattern is present (the LLM may
  promote/demote based on context, but this is the prior)
- ``category``: one of the 11-category risk vocabulary
- ``description``: what the pattern looks like in plain language
- ``example``: a representative clause snippet so the LLM has a concrete
  anchor (few-shot grounding)
- ``aliases``: alternate phrasings the LLM should also recognize

Severity priors map to the 4-tier vocabulary
(critical/high/medium/low) from ``LLMClauseDetector``.
"""

from __future__ import annotations

from typing import List, TypedDict


class RiskPattern(TypedDict, total=False):
    id: str
    title: str
    severity: str
    category: str
    description: str
    example: str
    aliases: List[str]


# Curated by hand from UNFAIR-ToS, OPP-115, and review of high-traffic ToS
# (TikTok, Meta, Apple, Google, OpenAI, Amazon). Ordered by approximate
# severity so the prompt reads top-down from worst to lightest.

RISK_PATTERNS: List[RiskPattern] = [
    # ---- CRITICAL ----------------------------------------------------------
    {
        "id": "sale_of_personal_data_without_consent",
        "title": "Sale of personal data without consent",
        "severity": "critical",
        "category": "data",
        "description": "Company sells personal information to third parties / data brokers without an explicit opt-in.",
        "example": "We may sell your personal information to advertising partners and data brokers.",
        "aliases": ["sell your data", "transfer for monetary consideration"],
    },
    {
        "id": "biometric_collection_without_consent",
        "title": "Biometric data collection without notice",
        "severity": "critical",
        "category": "data",
        "description": "Collection of biometric identifiers (face geometry, fingerprints, voiceprints) without explicit opt-in.",
        "example": "We may collect biometric identifiers from the photos and videos you upload.",
        "aliases": ["faceprint", "voiceprint", "face geometry"],
    },
    {
        "id": "tracking_children_without_parental_consent",
        "title": "Tracking children without parental consent",
        "severity": "critical",
        "category": "privacy",
        "description": "Collection of personal data from users under 13 without verifiable parental consent (COPPA violation).",
        "example": "Users under 13 may use the service if they have a parental confirmation email on file.",
    },

    # ---- HIGH (content / IP) ----------------------------------------------
    {
        "id": "perpetual_content_license",
        "title": "Perpetual, irrevocable content license",
        "severity": "high",
        "category": "content",
        "description": "User grants a perpetual + irrevocable + sublicensable license to their content. Survives account deletion.",
        "example": "You grant us a perpetual, irrevocable, worldwide, royalty-free, sublicensable license to use, reproduce, modify, adapt, publish, translate, and distribute your User Content.",
        "aliases": ["perpetual license", "irrevocable license", "royalty-free worldwide license"],
    },
    {
        "id": "likeness_license_royalty_free",
        "title": "Royalty-free name and likeness license",
        "severity": "high",
        "category": "content",
        "description": "User grants the company a royalty-free license to use their name, image, voice, and likeness.",
        "example": "You grant us a royalty-free license to use your name, image, voice, and likeness in connection with the Services.",
        "aliases": ["name and likeness", "name, image, voice", "right of publicity"],
    },
    {
        "id": "moral_rights_waiver",
        "title": "Moral rights waiver",
        "severity": "high",
        "category": "rights",
        "description": "User waives moral rights — right of attribution and right of integrity over their content.",
        "example": "You waive any and all moral rights you may have in your User Content.",
        "aliases": ["waive moral rights", "right of attribution", "right of integrity"],
    },
    {
        "id": "feedback_perpetual_commercial_rights",
        "title": "Feedback grants perpetual commercial rights",
        "severity": "high",
        "category": "rights",
        "description": "Any feedback, ideas, or suggestions submitted to the company become its property with perpetual commercial rights and no compensation.",
        "example": "Any feedback you submit becomes our property and we may use it for any commercial purpose without compensation.",
        "aliases": ["feedback ideas", "suggestions become our property"],
    },

    # ---- HIGH (privacy / surveillance) ------------------------------------
    {
        "id": "automated_analysis_of_all_content",
        "title": "Automated analysis of all stored content",
        "severity": "high",
        "category": "surveillance",
        "description": "Automated systems scan all stored user content (including emails, DMs, files, private messages) for any purpose other than security/abuse detection.",
        "example": "Our automated systems analyze your content (including emails) to provide personally relevant features.",
        "aliases": ["scan your content", "automated analysis of emails"],
    },
    {
        "id": "unnamed_third_party_data_sharing",
        "title": "Sharing data with unnamed third parties",
        "severity": "high",
        "category": "data",
        "description": "Personal data is shared with 'affiliates' or 'partners' without naming them or the purpose.",
        "example": "We share your information with our affiliates and trusted partners.",
        "aliases": ["affiliates", "partners", "service providers"],
    },
    {
        "id": "no_behavioral_advertising_optout",
        "title": "No opt-out from behavioral advertising",
        "severity": "high",
        "category": "privacy",
        "description": "User cannot opt out of cross-context behavioral advertising / targeted ads based on their activity.",
        "example": "We use your activity across our services to show you personalized ads.",
    },
    {
        "id": "indefinite_retention",
        "title": "Indefinite retention for business needs",
        "severity": "high",
        "category": "data",
        "description": "Personal data is retained 'as long as necessary' with no concrete maximum window or deletion mechanism.",
        "example": "We retain your data as long as necessary to provide our services and for business purposes.",
        "aliases": ["as long as necessary", "for legitimate business purposes"],
    },
    {
        "id": "automated_decision_no_human_review",
        "title": "Automated decision-making without human review",
        "severity": "high",
        "category": "privacy",
        "description": "Significant decisions (account termination, eligibility, pricing) made by automated systems with no human-review path.",
        "example": "We may use automated systems to make decisions that affect your account.",
    },

    # ---- HIGH (legal / liability) -----------------------------------------
    {
        "id": "shortened_statute_of_limitations",
        "title": "Shortened statute of limitations",
        "severity": "high",
        "category": "arbitration",
        "description": "Time limit to file legal claims is shortened below the statutory default (typically 1 year instead of 2-6 years).",
        "example": "Any claim arising out of these Terms must be filed within one year.",
        "aliases": ["one year limitation", "1-year limitation", "time-bar"],
    },
    {
        "id": "forced_arbitration_class_waiver",
        "title": "Forced arbitration with class-action waiver",
        "severity": "high",
        "category": "arbitration",
        "description": "Forced individual arbitration with a class-action waiver, even when an opt-out is available.",
        "example": "You and Company agree to resolve disputes by binding individual arbitration. You waive any right to a class action.",
        "aliases": ["binding individual arbitration", "class action waiver"],
    },
    {
        "id": "jury_trial_waiver",
        "title": "Jury trial waiver",
        "severity": "high",
        "category": "arbitration",
        "description": "User explicitly waives the right to a jury trial.",
        "example": "You waive any right to a trial by jury.",
    },
    {
        "id": "liability_cap_fees_paid",
        "title": "Liability cap at fees paid",
        "severity": "high",
        "category": "liability",
        "description": "Company's total liability is capped at fees paid in a short period (e.g., 12 months) or a small fixed amount ($100).",
        "example": "Our total liability shall not exceed the amounts you paid us in the 12 months preceding the claim, or US $100, whichever is greater.",
    },
    {
        "id": "termination_with_prepaid_forfeit",
        "title": "Termination with prepaid forfeiture",
        "severity": "high",
        "category": "termination",
        "description": "Account termination triggers forfeiture of prepaid credits or balances with no refund.",
        "example": "Upon termination, any unused credits in your account will be forfeited.",
    },
    {
        "id": "silent_terms_changes",
        "title": "Silent terms changes (no advance notice)",
        "severity": "high",
        "category": "modification",
        "description": "Company may change terms at any time with no advance notice, and continued use means acceptance.",
        "example": "We may change these Terms at any time without notice. Your continued use constitutes acceptance.",
    },

    # ---- MEDIUM ------------------------------------------------------------
    {
        "id": "broad_indemnification",
        "title": "Broad user indemnification",
        "severity": "medium",
        "category": "liability",
        "description": "User indemnifies the company against claims arising from their use of the service, often without a reciprocal company indemnification.",
        "example": "You agree to indemnify and hold us harmless from any claim arising from your use of the Service.",
    },
    {
        "id": "warranty_disclaimer_as_is",
        "title": "As-is warranty disclaimer",
        "severity": "medium",
        "category": "liability",
        "description": "Service provided 'as-is' with all implied warranties disclaimed.",
        "example": "The Service is provided AS-IS without warranties of any kind.",
    },
    {
        "id": "auto_renewal_optout_friction",
        "title": "Auto-renewal with cancellation friction",
        "severity": "medium",
        "category": "payment",
        "description": "Subscription auto-renews and cancellation requires advance notice through a specific channel.",
        "example": "Your subscription will auto-renew unless cancelled at least 7 days before the renewal date through your account settings.",
    },
    {
        "id": "sole_discretion_account_termination",
        "title": "Sole-discretion account termination",
        "severity": "medium",
        "category": "termination",
        "description": "Company may terminate accounts at its sole discretion with stated breach grounds (cause-based but unilateral).",
        "example": "We may terminate your account at our sole discretion if we believe you have breached these Terms.",
    },
    {
        "id": "sole_discretion_content_removal",
        "title": "Sole-discretion content removal",
        "severity": "medium",
        "category": "content",
        "description": "Company may remove user content at its sole discretion.",
        "example": "We may remove any content at our sole discretion.",
    },
    {
        "id": "mandatory_venue_jurisdiction",
        "title": "Mandatory venue / jurisdiction",
        "severity": "medium",
        "category": "arbitration",
        "description": "Forces venue selection to a specific jurisdiction that may be inconvenient for the user.",
        "example": "Any dispute shall be brought exclusively in the courts of California.",
    },
    {
        "id": "broad_data_sharing_named",
        "title": "Broad data sharing with named partners",
        "severity": "medium",
        "category": "data",
        "description": "Sharing of personal data with named categories of partners (advertisers, service providers, analytics) with disclosed purposes.",
        "example": "We share data with our advertising partners, including Google and Meta, for ad measurement.",
    },
    {
        "id": "unilateral_terms_modification_with_notice",
        "title": "Unilateral terms modification with notice",
        "severity": "medium",
        "category": "modification",
        "description": "Company may change terms with reasonable advance notice; continued use means acceptance.",
        "example": "We may modify these Terms with reasonable advance notice. Your continued use after the effective date constitutes acceptance.",
    },

    # ---- LOW (boilerplate) ------------------------------------------------
    {
        "id": "governing_law_reasonable",
        "title": "Governing law clause",
        "severity": "low",
        "category": "other",
        "description": "Standard governing-law selection with a reasonable jurisdiction.",
        "example": "These Terms are governed by the laws of the State of California.",
    },
    {
        "id": "severability",
        "title": "Severability clause",
        "severity": "low",
        "category": "other",
        "description": "Standard severability — invalid provisions don't void the entire agreement.",
        "example": "If any provision is held unenforceable, the remainder shall remain in effect.",
    },
    {
        "id": "ip_disclosure_dmca",
        "title": "IP disclosure under DMCA",
        "severity": "low",
        "category": "rights",
        "description": "Standard DMCA notice procedure — identity may be disclosed to IP claimants under formal process.",
        "example": "We will disclose user identity to copyright holders pursuant to DMCA process.",
    },
]


def get_patterns_by_severity(severity: str) -> List[RiskPattern]:
    """Filter the catalog by a severity tier."""
    return [p for p in RISK_PATTERNS if p.get("severity") == severity]


def patterns_summary() -> dict:
    """Counts by severity tier — useful for stats / dashboard rendering."""
    from collections import Counter
    return dict(Counter(p["severity"] for p in RISK_PATTERNS))
