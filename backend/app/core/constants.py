"""
Detection pipeline constants.

Centralizes all magic numbers and thresholds used across the anomaly detection
pipeline. This makes the code more readable and easier to tune.

Refactoring: Replace Magic Numbers with Named Constants
"""

from dataclasses import dataclass
from typing import Dict
from enum import Enum


# =============================================================================
# INVERTED FUNNEL: THREAT LEVELS (Layer 3)
# =============================================================================

class ThreatLevel(str, Enum):
    """
    Threat levels based on consumer harm potential - INDEPENDENT of commonness.
    A clause can be UNIVERSAL but still HIGH threat (e.g., perpetual license).
    """
    CRITICAL = "critical"  # 9-10: Serious harm - data selling, biometrics, rights waiver
    HIGH = "high"          # 7-8: Significant harm - perpetual license, forced arbitration
    MEDIUM = "medium"      # 5-6: Concerning - auto-renewal, content removal rights
    LOW = "low"            # 3-4: Worth knowing - liability limits, warranty disclaimers
    INFO = "info"          # 1-2: Standard boilerplate - severability, entire agreement


class CommonnessLevel(str, Enum):
    """
    How common a pattern is across T&Cs - used for CONTEXT, not filtering.
    Common doesn't mean safe. Rare + High threat = RED FLAG.
    """
    UNIVERSAL = "universal"      # 90%+ of T&Cs have this
    VERY_COMMON = "very_common"  # 70-89% of T&Cs
    COMMON = "common"            # 50-69% of T&Cs
    UNCOMMON = "uncommon"        # 30-49% of T&Cs
    RARE = "rare"                # 10-29% of T&Cs
    VERY_RARE = "very_rare"      # <10% of T&Cs - RED FLAG


# =============================================================================
# INVERTED FUNNEL: PATTERN THREAT SCORES (Layer 3)
# =============================================================================

# Maps each detectable pattern to its threat score (1-10)
# These scores are based on CONSUMER HARM, not prevalence
PATTERN_THREAT_LEVELS: Dict[str, float] = {
    # =========================================================================
    # CRITICAL (9-10) - Serious harm to consumer
    # =========================================================================
    'data_selling': 10.0,
    'data_monetization': 10.0,
    'sell_personal_data': 10.0,
    'biometric_data_collection': 10.0,
    'biometric_data': 10.0,
    'biometric': 10.0,
    'facial_recognition': 10.0,
    'voice_print': 10.0,
    'rights_waiver': 9.5,
    'waive_all_rights': 9.5,
    'waive_statutory_rights': 9.5,
    'coppa_violation': 10.0,
    'children_data_violation': 10.0,
    'hipaa_violation': 10.0,
    'medical_data_sharing': 9.0,
    'warrantless_law_enforcement': 9.0,
    'warrantless_disclosure': 9.0,

    # =========================================================================
    # HIGH (7-8) - Significant harm
    # =========================================================================
    'perpetual_irrevocable_license': 8.0,
    'perpetual_license': 7.5,
    'irrevocable_license': 7.5,
    'broad_content_license': 7.0,
    'user_content_license': 8.0,  # Other users can copy your content
    'ai_training_data': 7.5,
    'ai_training_content': 7.5,
    'forced_arbitration_class_waiver': 8.5,
    'arbitration_class_action_waiver': 8.5,
    'class_action_waiver': 7.5,
    'binding_arbitration': 7.0,
    'unlimited_liability': 8.0,
    'unlimited_financial_exposure': 8.0,
    'indemnify_all_claims': 7.5,
    'unilateral_termination': 7.5,
    'explicit_account_termination': 7.5,
    'terminate_without_reason': 7.5,
    'terminate_without_notice': 8.0,
    'deactivation_no_appeal': 8.5,
    'survival_clauses': 5.0,
    'asymmetric_assignment': 5.0,
    'fund_holds_freezing': 7.5,
    'fund_freeze_no_process': 8.0,
    'content_loss': 7.5,
    'content_loss_on_cancellation': 7.5,
    'shortened_limitations': 7.0,
    'shortened_statute_limitations': 7.0,

    # =========================================================================
    # MEDIUM (5-6) - Concerning, user should know
    # =========================================================================
    'auto_renewal': 6.0,
    'auto_renewal_hidden': 6.5,
    'price_changes': 5.5,
    'unilateral_price_changes': 5.5,
    'unilateral_content_removal': 4.5,
    'content_removal_right': 5.0,
    'account_inactivity_reclaim': 5.5,  # Username reclaimed after inactivity
    'modification': 5.0,
    'modification_of_terms': 5.0,
    'terms_modification': 3.5,
    'surveillance_monitoring': 6.0,
    'location_tracking': 5.5,
    'digital_ownership_illusion': 4.5,

    # =========================================================================
    # LOW (3-4) - Worth knowing, standard protection clauses
    # =========================================================================
    'liability_limitation': 4.0,
    'liability_limitation_specific': 3.0,  # "Not responsible for loss"
    'liability_disclaimer': 3.0,  # General "not responsible" language
    'indemnification': 4.5,
    'warranty_disclaimer': 3.5,
    'no_warranties': 3.5,
    'cross_platform_sync': 4.0,  # Data synced across services
    'no_content_guarantee': 2.5,  # No guarantee content is accurate
    'data_sharing': 4.0,
    'third_party_data_sharing': 4.5,

    # =========================================================================
    # INFO (1-2) - Standard boilerplate, minimal concern
    # =========================================================================
    'governing_law': 2.0,
    'jurisdiction': 2.0,
    'severability': 1.0,
    'entire_agreement': 1.5,
    'contact_information': 1.0,
    'relationship_disclaimer': 1.5,
    'age_verification': 2.0,
}


# =============================================================================
# INVERTED FUNNEL: COMMONNESS THRESHOLDS (Layer 2)
# =============================================================================

@dataclass(frozen=True)
class CommonnessThresholds:
    """Thresholds for determining commonness level from prevalence percentage."""
    UNIVERSAL: float = 0.90      # >= 90% = universal
    VERY_COMMON: float = 0.70    # >= 70% = very common
    COMMON: float = 0.50         # >= 50% = common
    UNCOMMON: float = 0.30       # >= 30% = uncommon
    RARE: float = 0.10           # >= 10% = rare
    # < 10% = very_rare

    @classmethod
    def get_level(cls, prevalence: float) -> CommonnessLevel:
        """Convert prevalence (0-1) to CommonnessLevel."""
        if prevalence >= cls.UNIVERSAL:
            return CommonnessLevel.UNIVERSAL
        elif prevalence >= cls.VERY_COMMON:
            return CommonnessLevel.VERY_COMMON
        elif prevalence >= cls.COMMON:
            return CommonnessLevel.COMMON
        elif prevalence >= cls.UNCOMMON:
            return CommonnessLevel.UNCOMMON
        elif prevalence >= cls.RARE:
            return CommonnessLevel.RARE
        else:
            return CommonnessLevel.VERY_RARE


# =============================================================================
# INVERTED FUNNEL: USER IMPORTANCE CALCULATION (Layer 4)
# =============================================================================

@dataclass(frozen=True)
class UserImportanceConfig:
    """
    Configuration for calculating user importance score.
    Formula: importance = (threat_score * THREAT_WEIGHT) + (rareness_bonus * RARENESS_WEIGHT)
    """
    THREAT_WEIGHT: float = 2.0       # Threat level is primary factor
    RARENESS_WEIGHT: float = 1.0     # Rareness adds bonus

    # Rareness bonuses by commonness level
    VERY_RARE_BONUS: float = 3.0     # Unusual = extra attention
    RARE_BONUS: float = 2.0
    UNCOMMON_BONUS: float = 1.0
    COMMON_BONUS: float = 0.0
    VERY_COMMON_PENALTY: float = -0.5  # Slight penalty for very common
    UNIVERSAL_PENALTY: float = -1.0    # Slight penalty for universal

    @classmethod
    def get_rareness_bonus(cls, commonness: CommonnessLevel) -> float:
        """Get rareness bonus for a commonness level."""
        bonuses = {
            CommonnessLevel.VERY_RARE: cls.VERY_RARE_BONUS,
            CommonnessLevel.RARE: cls.RARE_BONUS,
            CommonnessLevel.UNCOMMON: cls.UNCOMMON_BONUS,
            CommonnessLevel.COMMON: cls.COMMON_BONUS,
            CommonnessLevel.VERY_COMMON: cls.VERY_COMMON_PENALTY,
            CommonnessLevel.UNIVERSAL: cls.UNIVERSAL_PENALTY,
        }
        return bonuses.get(commonness, 0.0)

    @classmethod
    def calculate_importance(cls, threat_score: float, commonness: CommonnessLevel) -> float:
        """
        Calculate user importance score.
        Higher = more important for user to see.
        """
        rareness_bonus = cls.get_rareness_bonus(commonness)
        importance = (threat_score * cls.THREAT_WEIGHT) + (rareness_bonus * cls.RARENESS_WEIGHT)
        return max(0.0, importance)  # Never negative


# =============================================================================
# INVERTED FUNNEL: DISPLAY CATEGORIES (Layer 4)
# =============================================================================

class DisplayCategory(str, Enum):
    """
    Categories for displaying anomalies to users.
    Based on combination of threat level and commonness.
    """
    UNUSUAL_DANGEROUS = "unusual_dangerous"    # Rare + High/Critical threat (RED)
    COMMON_DANGEROUS = "common_dangerous"      # Common + High/Critical threat (ORANGE)
    UNUSUAL_MINOR = "unusual_minor"            # Rare + Low threat (YELLOW)
    STANDARD_TERMS = "standard_terms"          # Common + Low threat (GRAY)


def get_display_category(threat_level: ThreatLevel, commonness: CommonnessLevel) -> DisplayCategory:
    """Determine display category from threat and commonness."""
    is_dangerous = threat_level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH)
    is_unusual = commonness in (CommonnessLevel.VERY_RARE, CommonnessLevel.RARE, CommonnessLevel.UNCOMMON)

    if is_dangerous and is_unusual:
        return DisplayCategory.UNUSUAL_DANGEROUS
    elif is_dangerous:
        return DisplayCategory.COMMON_DANGEROUS
    elif is_unusual:
        return DisplayCategory.UNUSUAL_MINOR
    else:
        return DisplayCategory.STANDARD_TERMS


def get_threat_level_from_score(score: float) -> ThreatLevel:
    """Convert numeric threat score to ThreatLevel enum."""
    if score >= 9.0:
        return ThreatLevel.CRITICAL
    elif score >= 7.0:
        return ThreatLevel.HIGH
    elif score >= 5.0:
        return ThreatLevel.MEDIUM
    elif score >= 3.0:
        return ThreatLevel.LOW
    else:
        return ThreatLevel.INFO


# =============================================================================
# STAGE 1: DETECTION METHOD WEIGHTS
# =============================================================================

@dataclass(frozen=True)
class DetectionWeights:
    """Weights for multi-method detection in Stage 1."""
    PATTERN_BASED: float = 0.50  # INCREASED from 0.40 - Primary method when others unavailable
    SEMANTIC: float = 0.30       # DECREASED from 0.35
    STATISTICAL: float = 0.20   # DECREASED from 0.25


# =============================================================================
# STAGE 1: CONFIDENCE CALCULATION
# =============================================================================

@dataclass(frozen=True)
class PatternConfidenceConfig:
    """Configuration for pattern-based confidence calculation."""
    BASE_CONFIDENCE: float = 0.6  # INCREASED from 0.5
    HIGH_SEVERITY_BOOST: float = 0.25  # INCREASED from 0.2
    MEDIUM_SEVERITY_BOOST: float = 0.15  # INCREASED from 0.1
    MAX_CONFIDENCE: float = 1.0


# =============================================================================
# PREVALENCE THRESHOLDS
# =============================================================================

@dataclass(frozen=True)
class PrevalenceThresholds:
    """Thresholds for clause prevalence (how common a clause is)."""
    UNUSUAL_THRESHOLD: float = 0.25    # < 25% = unusual, flag it (was 0.30)
    COMMON_THRESHOLD: float = 0.80     # >= 80% = suppress by default (was 0.70)
    VERY_COMMON_THRESHOLD: float = 0.90  # >= 90% = always suppress (was 0.85)
    DEFAULT_UNKNOWN: float = 0.15

    # Prevalence-based actions - RAISED to reduce over-suppression
    SUPPRESS_ABOVE: float = 0.85   # Suppress if prevalence >= 85% (was 0.70)
    REDUCE_ABOVE: float = 0.60     # Reduce severity if prevalence >= 60% (was 0.50)


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
# STAGE 2: CONTEXT FILTERING THRESHOLDS
# =============================================================================

@dataclass(frozen=True)
class Stage2Thresholds:
    """Thresholds for Stage 2 context filtering."""
    MIN_RISK_SCORE_FOR_STAGE3: float = 3.0  # DECREASED from 5.0
    MIN_CONFIDENCE_FOR_STAGE3: float = 0.25  # DECREASED from 0.60 - Critical fix!
    STAGE1_WEIGHT: float = 0.80      # INCREASED from 0.70
    CONTEXT_WEIGHT: float = 0.20     # DECREASED from 0.30


# =============================================================================
# SEVERITY SCORING
# =============================================================================

@dataclass(frozen=True)
class SeverityScores:
    """Risk scores by severity level."""
    HIGH: float = 8.0
    MEDIUM: float = 5.0
    LOW: float = 3.0

    @classmethod
    def get_score(cls, severity: str) -> float:
        """Get score for a severity level."""
        mapping = {
            'high': cls.HIGH,
            'medium': cls.MEDIUM,
            'low': cls.LOW
        }
        return mapping.get(severity.lower(), cls.MEDIUM)


# =============================================================================
# RISK SCORE CALCULATION
# =============================================================================

@dataclass(frozen=True)
class RiskScoreWeights:
    """Weights for calculating overall document risk score."""
    HIGH_SEVERITY_WEIGHT: float = 3.0
    MEDIUM_SEVERITY_WEIGHT: float = 2.0
    LOW_SEVERITY_WEIGHT: float = 1.0
    COMPOUND_RISK_WEIGHT: float = 2.5
    MAX_SEVERITY_SCORE: float = 30.0
    DEFAULT_CONFIDENCE: float = 0.5


# =============================================================================
# CLAUSE LENGTH THRESHOLDS
# =============================================================================

@dataclass(frozen=True)
class ClauseLengthThresholds:
    """Thresholds for clause text length."""
    MIN_CLAUSE_LENGTH: int = 15       # DECREASED from 20 - Catch shorter clauses
    LONG_CLAUSE_LENGTH: int = 400     # DECREASED from 500


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
# RISK LEVEL BOUNDARIES
# =============================================================================

@dataclass(frozen=True)
class RiskLevelBoundaries:
    """Boundaries for determining risk levels from scores."""
    HIGH_RISK_THRESHOLD: float = 6.0  # DECREASED from 7.0
    MEDIUM_RISK_THRESHOLD: float = 3.0  # DECREASED from 4.0
    MIN_SCORE: float = 1.0
    MAX_SCORE: float = 10.0


# =============================================================================
# VAGUE LANGUAGE DETECTION
# =============================================================================

VAGUE_LANGUAGE_TERMS = [
    "may",
    "might",
    "could",
    "at our discretion",
    "as we see fit",
    "in our sole discretion",
    "reserve the right",
    "at any time",
    "without notice",
    "without cause",
    "for any reason",
]


# =============================================================================
# DEFAULT VALUES
# =============================================================================

@dataclass(frozen=True)
class DefaultValues:
    """Default values used throughout the pipeline."""
    DEFAULT_INDUSTRY: str = 'saas'
    DEFAULT_SERVICE_TYPE: str = 'subscription'
    DEFAULT_COMPANY_NAME: str = 'Unknown'


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

# Keywords that by themselves should NOT trigger flags (too common)
SKIP_SINGLE_KEYWORDS = {
    "spam", "malware", "virus", "trojan", "impersonate",
    "fake reviews", "harassment", "hate speech", "copyright",
    "trademark", "password", "confidential", "commercial purpose",
    "sexually explicit", "violence", "resell", "derivative",
    "parental consent", "minimum age", "contact us", "entire agreement",
}


# =============================================================================
# FALSE POSITIVE REDUCTION: MULTI-FACTOR THRESHOLDS
# =============================================================================

@dataclass(frozen=True)
class MultiFactor:
    """Thresholds for multi-factor detection."""
    HIGH_SEVERITY_FACTORS_REQUIRED: int = 2    # Need 2+ factors for HIGH
    MEDIUM_SEVERITY_FACTORS_REQUIRED: int = 2  # Need 2+ factors for MEDIUM
    MIN_KEYWORDS_FOR_FLAG: int = 2             # Need 2+ red flags, not just 1
    MIN_SEVERITY_SCORE: float = 2.0            # Minimum combined score to flag


# =============================================================================
# FALSE POSITIVE REDUCTION: BASELINE PREVALENCE DATA
# =============================================================================

# Real prevalence data (based on analyzing 50+ T&Cs)
# Higher values = more common, less likely to be anomalous
BASELINE_PREVALENCE = {
    # VERY COMMON (>80% of platforms) - Almost never flag
    "account_termination_right": 0.95,
    "content_removal_right": 0.95,
    "no_warranties": 0.90,
    "ip_protection": 0.90,
    "no_liability_for_third_party": 0.85,
    "user_responsibility_for_content": 0.85,
    "no_refunds_for_free": 0.80,
    "modification_of_terms": 0.85,
    "governing_law": 0.90,

    # COMMON (50-80%) - Rarely flag unless combined with other factors
    "perpetual_license": 0.65,
    "sole_discretion_general": 0.70,
    "sole_discretion_termination": 0.60,
    "one_year_limitation": 0.45,
    "royalty_free_content": 0.55,

    # UNCOMMON (20-50%) - Consider flagging with context
    "license_transfer": 0.40,
    "irrevocable_waiver": 0.30,
    "no_security_guarantees": 0.25,
    "binding_arbitration": 0.45,
    "class_action_waiver": 0.40,

    # RARE (<20%) - Usually flag
    "perpetual_irrevocable_transfer": 0.15,
    "waive_privacy_rights": 0.08,
    "waive_moral_rights": 0.12,
    "full_liability_waiver": 0.05,
    "unlimited_data_sharing": 0.10,
}


# =============================================================================
# FALSE POSITIVE REDUCTION: CONTEXT-AWARE FILTERING
# =============================================================================

# Keywords that are ONLY concerning in specific contexts
CONTEXT_DEPENDENT_KEYWORDS = {
    "sole discretion": {
        "problematic_contexts": ["terminate", "disable", "delete account", "remove your content", "ban"],
        "safe_contexts": ["spam", "malware", "harassment", "copyright", "illegal", "moderate content"],
    },
    "irrevocable": {
        "problematic_contexts": ["user content", "your content", "waive", "license to us"],
        "safe_contexts": ["tiktok content", "our content", "company content"],
    },
    "perpetual": {
        "problematic_contexts": ["user content", "your content", "license", "worldwide"],
        "safe_contexts": ["account deletion", "upon termination"],
    },
    "no liability": {
        "problematic_contexts": ["data loss", "deletion", "corruption", "security breach", "your data"],
        "safe_contexts": ["third party", "force majeure", "carrier", "acts of god"],
    },
    "without notice": {
        "problematic_contexts": ["terminate", "delete", "remove", "disable", "suspend account"],
        "safe_contexts": ["update terms", "modify features", "improve service", "maintenance"],
    },
    "at any time": {
        "problematic_contexts": ["terminate", "delete data", "remove content", "close account"],
        "safe_contexts": ["cancel subscription", "contact support", "request data"],
    },
}


# =============================================================================
# FALSE POSITIVE REDUCTION: SECTION CONTEXT
# =============================================================================

# Section-specific concern levels - same clause means different things in different sections
SECTION_CONTEXT = {
    "Content": {
        "high_concern": ["license to your content", "modify your content", "derivative works"],
        "low_concern": ["our content", "platform content", "service content"],
    },
    "User Content": {
        "high_concern": ["perpetual", "irrevocable", "royalty-free worldwide"],
        "low_concern": ["display your content", "share your content"],
    },
    "Account": {
        "high_concern": ["terminate without reason", "disable at sole discretion", "forfeit"],
        "low_concern": ["you may close", "account security", "password"],
    },
    "Liability": {
        "high_concern": ["no liability for data loss", "no liability for security"],
        "low_concern": ["no liability for third party", "limited liability"],
    },
    "Prohibited Content": {
        "low_concern": ["spam", "malware", "harassment", "illegal"],  # All good!
    },
    "Acceptable Use": {
        "low_concern": ["prohibited activities", "restricted uses"],  # Usually good
    },
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


# =============================================================================
# INDUSTRY COMPETITOR BENCHMARKS
# =============================================================================

# Known risk scores for major companies by industry
# Used for competitive comparison: "This T&C is worse/better than X"
INDUSTRY_COMPETITORS = {
    'streaming': {
        'apple': {
            'company_name': 'Apple (iTunes/Apple TV+)',
            'avg_risk_score': 6.5,
            'notable_issues': ['24-hour cancellation window', 'Family sharing liability', 'Broad content license'],
        },
        'netflix': {
            'company_name': 'Netflix',
            'avg_risk_score': 4.2,
            'notable_issues': ['Cancel anytime', 'No family liability', 'Standard content license'],
        },
        'spotify': {
            'company_name': 'Spotify',
            'avg_risk_score': 4.8,
            'notable_issues': ['Individual payment methods', 'Prorated refunds', 'Moderate data sharing'],
        },
        'youtube': {
            'company_name': 'YouTube Premium',
            'avg_risk_score': 5.5,
            'notable_issues': ['Google account integration', 'Broad data usage', 'Standard cancellation'],
        },
        'disney': {
            'company_name': 'Disney+',
            'avg_risk_score': 5.0,
            'notable_issues': ['Bundle complexity', 'Standard cancellation', 'Content license'],
        },
        'hulu': {
            'company_name': 'Hulu',
            'avg_risk_score': 5.2,
            'notable_issues': ['Ad-tier data collection', 'Standard cancellation', 'Disney integration'],
        },
    },
    'social_media': {
        'facebook': {
            'company_name': 'Facebook/Meta',
            'avg_risk_score': 7.5,
            'notable_issues': ['Extensive data collection', 'Broad content license', 'AI training on content'],
        },
        'instagram': {
            'company_name': 'Instagram',
            'avg_risk_score': 7.2,
            'notable_issues': ['Same as Facebook', 'Photo/video licensing', 'Influencer monetization terms'],
        },
        'twitter': {
            'company_name': 'X (Twitter)',
            'avg_risk_score': 6.8,
            'notable_issues': ['Content licensing', 'API restrictions', 'Verification requirements'],
        },
        'tiktok': {
            'company_name': 'TikTok',
            'avg_risk_score': 8.0,
            'notable_issues': ['Extensive data collection', 'Perpetual content license', 'AI training'],
        },
        'linkedin': {
            'company_name': 'LinkedIn',
            'avg_risk_score': 6.0,
            'notable_issues': ['Professional data usage', 'Recruiter access', 'Microsoft integration'],
        },
    },
    'financial': {
        'paypal': {
            'company_name': 'PayPal',
            'avg_risk_score': 6.5,
            'notable_issues': ['Fund holds', 'Dispute resolution', 'Account limitations'],
        },
        'venmo': {
            'company_name': 'Venmo',
            'avg_risk_score': 6.8,
            'notable_issues': ['Social features data', 'PayPal parent company', 'P2P liability'],
        },
        'cashapp': {
            'company_name': 'Cash App',
            'avg_risk_score': 7.0,
            'notable_issues': ['Bitcoin terms', 'Fund holds', 'Limited dispute resolution'],
        },
        'stripe': {
            'company_name': 'Stripe',
            'avg_risk_score': 5.5,
            'notable_issues': ['Business-focused', 'Reserve requirements', 'Standard processing terms'],
        },
    },
    'ecommerce': {
        'amazon': {
            'company_name': 'Amazon',
            'avg_risk_score': 6.0,
            'notable_issues': ['Broad data collection', 'Prime auto-renewal', 'Return policy variations'],
        },
        'ebay': {
            'company_name': 'eBay',
            'avg_risk_score': 5.8,
            'notable_issues': ['Seller/buyer liability', 'Dispute resolution', 'Fee structures'],
        },
        'shopify': {
            'company_name': 'Shopify',
            'avg_risk_score': 5.0,
            'notable_issues': ['Merchant-focused', 'Payment processing', 'App integrations'],
        },
    },
    'gig_economy': {
        'uber': {
            'company_name': 'Uber',
            'avg_risk_score': 8.5,
            'notable_issues': ['Worker classification', 'Forced arbitration', 'Deactivation policies'],
        },
        'lyft': {
            'company_name': 'Lyft',
            'avg_risk_score': 8.2,
            'notable_issues': ['Similar to Uber', 'Deactivation', 'Liability limitations'],
        },
        'doordash': {
            'company_name': 'DoorDash',
            'avg_risk_score': 8.0,
            'notable_issues': ['Tip policies', 'Deactivation', 'Worker classification'],
        },
        'instacart': {
            'company_name': 'Instacart',
            'avg_risk_score': 7.8,
            'notable_issues': ['Tip baiting history', 'Batch payments', 'Rating system'],
        },
    },
    'cloud_saas': {
        'google_workspace': {
            'company_name': 'Google Workspace',
            'avg_risk_score': 5.5,
            'notable_issues': ['Data usage for AI', 'Service discontinuation', 'Privacy controls'],
        },
        'microsoft_365': {
            'company_name': 'Microsoft 365',
            'avg_risk_score': 5.2,
            'notable_issues': ['Telemetry collection', 'License compliance', 'Service changes'],
        },
        'dropbox': {
            'company_name': 'Dropbox',
            'avg_risk_score': 4.8,
            'notable_issues': ['File scanning', 'Sharing liability', 'Storage limits'],
        },
        'slack': {
            'company_name': 'Slack',
            'avg_risk_score': 5.0,
            'notable_issues': ['Workspace admin access', 'Data retention', 'Salesforce integration'],
        },
    },
}
