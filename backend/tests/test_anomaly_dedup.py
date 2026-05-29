"""Tests for finding deduplication in the anomaly detector orchestrator.

Regression coverage for the dashboard duplication (Apple Media Services, Run 5):
multiple DISTINCT catalog patterns match the same clause/risk, so the detector
emitted several findings for what the benchmark counts as one risk
(e.g. termination "M x3", California jurisdiction "M+L"). dedup keyed only on
pattern_id never collapsed these because the pattern_ids differ.
"""

from app.core.anomaly_detector import _dedupe_findings


def _f(pattern_id, severity, clause_number, title, category="other"):
    return {
        "pattern_id": pattern_id,
        "severity": severity,
        "clause_number": clause_number,
        "risk_title": title,
        "risk_category": category,
        "explanation": f"{title} explanation",
    }


def test_same_pattern_across_batches_collapses():
    """Existing behaviour: same catalog pattern emitted twice collapses to one,
    keeping the higher severity."""
    findings = [
        _f("perpetual_content_license", "medium", "17", "Perpetual content license"),
        _f("perpetual_content_license", "high", "18", "Perpetual content license"),
    ]
    out = _dedupe_findings(findings)
    assert len(out) == 1
    assert out[0]["severity"] == "high"


def test_two_patterns_same_clause_collapse_to_highest():
    """Real Run-5 case: two different termination patterns fire on clause 11.
    The benchmark counts this as ONE risk — collapse to the highest severity."""
    findings = [
        _f("termination_with_prepaid_forfeit", "high", "11", "Termination with prepaid forfeiture", "termination"),
        _f("sole_discretion_account_termination", "medium", "11", "Sole-discretion account termination", "termination"),
    ]
    out = _dedupe_findings(findings)
    assert len(out) == 1, f"expected clause-11 pair to collapse, got {len(out)}"
    assert out[0]["severity"] == "high"


def test_distinct_clauses_are_preserved():
    """Findings on different clauses are distinct risks and must NOT collapse."""
    findings = [
        _f("perpetual_content_license", "high", "17", "Perpetual content license", "rights"),
        _f("sole_remedy_company_discretion", "high", "4", "Sole remedy at company discretion", "liability"),
        _f("law_enforcement_disclosure_no_notice", "high", "49", "Law enforcement disclosure", "privacy"),
    ]
    out = _dedupe_findings(findings)
    assert len(out) == 3


def test_missing_protection_findings_never_merge():
    """Missing-protection findings carry no real clause_number; they must never
    be merged together by the clause-level pass."""
    findings = [
        {"pattern_id": "missing:breach_notification", "severity": "medium",
         "risk_title": "No breach notification", "clause_number": None,
         "risk_category": "data", "explanation": "x"},
        {"pattern_id": "missing:advance_notice_changes", "severity": "medium",
         "risk_title": "No advance notice of changes", "clause_number": None,
         "risk_category": "modification", "explanation": "y"},
    ]
    out = _dedupe_findings(findings)
    assert len(out) == 2


def test_full_run5_shape_collapses_duplicates_only():
    """The 18 real Run-5 findings: only the same-clause pairs (clause 11, 17)
    should collapse; everything else is preserved."""
    findings = [
        _f("perpetual_content_license", "high", "17", "Perpetual content license"),
        _f("indefinite_retention", "high", "35", "Indefinite retention"),
        _f("sole_remedy_company_discretion", "high", "4", "Sole remedy"),
        _f("termination_with_prepaid_forfeit", "high", "11", "Termination prepaid forfeit", "termination"),
        _f("unilateral_terms_modification", "medium", "38", "Unilateral terms mod"),
        _f("sole_discretion_account_termination", "medium", "11", "Sole-discretion termination", "termination"),
        _f("sole_discretion_content_removal", "medium", "17", "Content removal at discretion"),
        _f("cascading_payment_charges", "medium", "3", "Cascading payments"),
        _f("free_trial_no_reactivation", "medium", "14", "Free trial no reactivation"),
        _f("broad_indemnification", "medium", "45", "Broad indemnification"),
        _f("law_enforcement_disclosure_no_notice", "high", "49", "Law enforcement disclosure"),
        _f("mandatory_venue_jurisdiction", "medium", "32", "Mandatory venue"),
    ]
    out = _dedupe_findings(findings)
    # clause 11 (2->1) and clause 17 (2->1): 12 -> 10
    assert len(out) == 10
    clause_11 = [f for f in out if f["clause_number"] == "11"]
    clause_17 = [f for f in out if f["clause_number"] == "17"]
    assert len(clause_11) == 1 and clause_11[0]["severity"] == "high"
    assert len(clause_17) == 1 and clause_17[0]["severity"] == "high"
