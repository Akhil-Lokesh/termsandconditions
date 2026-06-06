"""
Detection pipeline constants.

Curated thresholds and keyword catalogs used by the active (checklist-mode)
detection pipeline. Everything here is referenced by `risk_indicators.py` or the
statistical-detector scripts; the legacy scoring/prevalence tables from the old
multi-stage pipeline were removed (they had no remaining call sites).
"""

from dataclasses import dataclass


# =============================================================================
# CRITICAL PATTERNS - NEVER DOWNGRADE
# =============================================================================

@dataclass(frozen=True)
class CriticalPatterns:
    """
    Patterns that should ALWAYS be classified as critical severity.
    These patterns cause significant consumer harm and should never be downgraded
    regardless of industry context or prevalence.
    """
    # Frozen set of patterns that are always classified as critical severity.
    # IMPORTANT: Keep this list SMALL - only truly critical consumer harm patterns.
    # Patterns NOT in this list will still be flagged as HIGH, just not auto-upgraded to CRITICAL.
    ALWAYS_CRITICAL: frozenset = frozenset({
        # Data exploitation - monetizing personal data
        'data_selling',
        'data_monetization',
        'sell_personal_data',
        'sell_user_data',

        # Biometric data collection
        'biometric_data_collection',
        'biometric_without_consent',
        'biometric_data',
        'biometric',
        'facial_recognition',
        'voice_print',
        'fingerprint_collection',

        # Rights elimination - waiving legal rights
        'rights_waiver',
        'waive_all_rights',
        'waive_statutory_rights',
        'waive_legal_rights',
        'waive_consumer_rights',

        # Gig economy exploitation (no appeal/recourse)
        'deactivation_no_appeal',
        'fund_freeze_no_process',
        'account_termination_no_recourse',

        # Surveillance without warrant
        'warrantless_law_enforcement',
        'warrantless_disclosure',

        # Healthcare violations
        'hipaa_violation',
        'medical_data_sharing',

        # Children's data violations
        'coppa_violation',
        'children_data_violation',
        'collect_child_data',

        # Keystroke monitoring (extreme surveillance)
        'keystroke_monitoring',
    })

    # Threshold for critical severity (score-based)
    CRITICAL_THRESHOLD: float = 6.0  # Raised from 5.0

    # High threshold
    HIGH_THRESHOLD: float = 4.0


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ModelConfig:
    """Configuration for ML models used in detection."""
    SEMANTIC_MODEL: str = 'sentence-transformers/all-MiniLM-L6-v2'
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.45  # DECREASED from 0.75 - Critical fix!
    LEGAL_BERT_MODEL: str = 'nlpaueb/legal-bert-base-uncased'
    DUPLICATE_THRESHOLD: float = 0.90  # DECREASED from 0.95
    STATISTICAL_CONTAMINATION: float = 0.15  # INCREASED from 0.1 - More sensitive
    STATISTICAL_RANDOM_STATE: int = 42


# =============================================================================
# FALSE POSITIVE REDUCTION: WHITELIST PATTERNS
# =============================================================================

# Clauses matching these patterns are STANDARD and should NOT be flagged
# These represent legitimately normal T&C clauses found in 80%+ of services
WHITELIST_PATTERNS = {
    # Content moderation (all platforms have this - it's GOOD)
    "spam_protection": ["spam", "junk mail", "unsolicited", "bulk email"],
    "malware_protection": ["malware", "virus", "trojan", "worms", "logic bombs", "harmful code"],
    "impersonation_protection": ["impersonate", "false identity", "misrepresent yourself"],
    "harassment_protection": ["harassment", "bullying", "hate speech", "discrimination", "threats"],

    # Normal IP protection (legally required)
    "ip_infringement": ["copyright infringement", "trademark infringement", "intellectual property"],
    "ip_violation": ["material which does or may infringe", "infringing content"],

    # Business protections (standard everywhere)
    # NOTE: Removed "derivative works" and "sublicense" - these are risky in license grants, not safe
    "reselling_prohibition": ["resell", "redistribute"],
    "commercial_use_restriction": ["commercial purpose", "commercial solicitation", "without written consent"],
    "account_security": ["password", "confidential", "account credentials", "login information"],

    # Normal content policy
    "fake_content": ["fake reviews", "false information", "misleading content"],
    "explicit_content": ["sexually explicit", "pornographic", "obscene material"],
    "illegal_content": ["illegal activity", "unlawful purpose", "violate any law"],

    # Age verification (legally required)
    "age_verification": ["under age", "parental consent", "legal guardian", "minimum age"],

    # Standard legal boilerplate
    "contact_info": ["contact us", "reach us", "mailing address", "customer support"],
    "relationship_disclaimer": ["not create any partnership", "independent contractors"],
    "entire_agreement": ["entire agreement", "supersedes all prior"],
    "severability": ["severability", "if any provision", "remaining provisions"],
    "waiver_clause": ["failure to enforce", "not constitute a waiver"],

    # Normal data practices
    "data_security": ["reasonable security", "protect your information", "security measures"],
    # NOTE: Removed "not responsible for" - too broad, blocks legitimate liability detection
    "third_party_links": ["third-party websites", "external links", "third party content"],
}


# =============================================================================
# BOILERPLATE SECTION DETECTION
# =============================================================================

# Standard section names that should have REDUCED severity
# These sections typically contain legal boilerplate that isn't uniquely risky
BOILERPLATE_SECTIONS = frozenset({
    # Introductory sections
    'introduction', 'overview', 'about', 'welcome', 'about these terms',
    'about this agreement', 'agreement overview',

    # Definitions
    'definitions', 'defined terms', 'glossary', 'terminology',
    'key terms', 'meaning of terms',

    # General/Miscellaneous
    'general terms', 'general provisions', 'general', 'miscellaneous',
    'other terms', 'additional terms', 'supplementary terms',

    # Contact information
    'contact', 'contact us', 'contact information', 'how to contact us',
    'customer support', 'support',

    # Legal boilerplate
    'governing law', 'applicable law', 'jurisdiction', 'choice of law',
    'dispute resolution', 'legal disputes',
    'entire agreement', 'complete agreement',
    'severability', 'separability',
    'waiver', 'no waiver',
    'assignment', 'transfer',
    'notices', 'notice',
    'relationship of parties', 'independent contractors', 'no partnership',
    'survival', 'surviving provisions',
    'amendments', 'changes to terms', 'modifications',
    'effective date', 'last updated',
})
