"""
Universal risk indicators for Terms & Conditions clauses.

These indicators work for ANY T&C document from ANY company.
They identify universally concerning patterns that could harm consumers.
"""

from typing import List, Dict, Set
import re


class RiskIndicators:
    """Identifies universal risk patterns in T&C clauses."""

    # HIGH RISK: Severely unfair or dangerous for consumers
    HIGH_RISK_PATTERNS = {
        "unilateral_termination": {
            "keywords": [
                "terminate at any time without notice",
                "terminate your account without cause",
                "suspend or terminate for any reason",
                "at our sole discretion",
                "without prior notice",
                "immediate termination",
                "we may terminate without liability",
                # Additional variations (Fix #3)
                "discontinue service at any time",
                "cancel your access without warning",
                "terminate immediately and without cause",
                "suspend your account at our discretion",
                "end your access for any reason",
                "terminate service without explanation",
                "we reserve the right to terminate",
                "may be terminated at any time",
                "terminate without prior notification",
                "discontinue without notice or liability",
                "suspend or cancel without reason",
                "termination at our sole option",
                "immediate suspension or termination",
                "revoke access at any time",
                "terminate your use without cause",
                # Vague grounds patterns (100% detection)
                "for any reason",
                "without cause",
                "may cancel whenever we want",
                "we can shut down service",
                "terminate and access",
                "terminate your access without notice",
                "may suspend your account",
                "may close your account"
            ],
            "description": "Company can terminate service without warning or reason",
            "severity": "high"
        },
        "content_loss": {
            "keywords": [
                "not responsible for data loss",
                "may delete your content",
                "no backup obligation",
                "content may be lost",
                "not liable for deleted data",
                # Additional variations (Fix #3)
                "may remove your files",
                "no responsibility for lost information",
                "data deletion without liability",
                "content removal without notice",
                "no guarantee of data retention",
                "files may be deleted at any time",
                "no obligation to preserve content",
                "may erase your data",
                "content may be removed without warning",
                "no backup or recovery obligation",
                "not liable for lost or deleted files",
                "data may be permanently deleted",
                "no responsibility for content preservation",
                "may delete without prior notice"
            ],
            "description": "Risk of losing your data without compensation",
            "severity": "high"
        },
        "auto_payment_updates": {
            "keywords": [
                "automatically update payment method",
                "update billing information without consent",
                "charge updated payment details",
                "billing account updater",
                # Additional variations (Fix #3)
                "update payment info automatically",
                "charge new card without authorization",
                "automatic billing updates",
                "payment method may be updated",
                "update credit card information",
                "automatically charge updated details",
                "billing updater service",
                "change payment method without notice",
                "automatic payment updates",
                "update card details without consent",
                "charge replacement card",
                "automatic card update service",
                "billing information automatically updated"
            ],
            "description": "Automatic payment method updates without explicit consent",
            "severity": "high"
        },
        "unlimited_liability": {
            "keywords": [
                "unlimited liability",
                "liable for all claims",
                "indemnify us for any",
                "hold us harmless for all",
                # Additional variations (Fix #3)
                "responsible for any and all damages",
                "indemnify for all losses",
                "defend and hold harmless",
                "assume all liability",
                "liable for any damages",
                "indemnify against all claims",
                "hold harmless from any liability",
                "bear all costs and damages",
                "responsible for all expenses",
                "indemnify and defend us",
                "liable for all costs",
                "assume full responsibility",
                "indemnify from any loss",
                "bear unlimited responsibility"
            ],
            "description": "You assume unlimited liability for any issues",
            "severity": "high"
        },
        "rights_waiver": {
            "keywords": [
                "waive all rights",
                "waive right to sue",
                "give up right to",
                "forfeit all claims",
                "waive any legal rights",
                # Additional variations (Fix #3)
                "relinquish all rights",
                "surrender your rights",
                "forfeit legal protections",
                "waive claims and remedies",
                "give up all claims",
                "waive right to legal action",
                "relinquish right to pursue",
                "forfeit right to compensation",
                "waive right to damages",
                "surrender legal rights",
                "waive all remedies",
                "give up right to recovery",
                "forfeit protections and rights",
                "waive statutory rights"
            ],
            "description": "You waive important legal rights",
            "severity": "high"
        },
        "price_increase_no_notice": {
            "keywords": [
                "increase prices without notice",
                "change fees at any time",
                "modify pricing without notification",
                "raise prices without informing",
                # Additional variations (Fix #3)
                "adjust rates without notice",
                "change pricing at our discretion",
                "increase fees without warning",
                "modify costs without notification",
                "raise rates at any time",
                "adjust pricing without prior notice",
                "change subscription price",
                "increase charges without informing",
                "modify fees at our discretion",
                "raise costs without notification",
                "adjust subscription fees",
                "change rates without warning",
                "pricing subject to change without notice",
                "fees may increase at any time",
                # Hidden price change patterns (100% detection)
                "price may increase",
                "raise the price",
                "we may change the price",
                "subject to price change",
                "price may change without notice",
                "rates may change"
            ],
            "description": "Prices can increase without advance notice",
            "severity": "high"
        },
        "forced_arbitration_class_waiver": {
            "keywords": [
                "waive right to class action",
                "arbitration only",
                "no class action",
                "individual arbitration",
                "waive jury trial",
                # Additional variations (Fix #3)
                "binding arbitration",
                "waive right to court",
                "no class or collective action",
                "individual basis only",
                "waive right to participate in class",
                "mandatory arbitration",
                "give up jury trial",
                "waive class action rights",
                "arbitration agreement",
                "no right to join class action",
                "individual claims only",
                "waive right to litigate",
                "arbitration instead of court",
                "no consolidated proceedings",
                "waive representative actions"
            ],
            "description": "You cannot join class action lawsuits",
            "severity": "high"
        }
    }

    # MEDIUM RISK: Concerning but common in some industries
    MEDIUM_RISK_PATTERNS = {
        "auto_renewal": {
            "keywords": [
                "automatically renew",
                "auto-renewal",
                "automatically extends",
                "renews unless cancelled",
                # Additional variations (Fix #3)
                "automatic renewal",
                "renews automatically",
                "subscription continues automatically",
                "auto-renewing subscription",
                "will renew unless you cancel",
                "automatically continues",
                "renews for additional term",
                "subscription auto-renews",
                "automatic extension",
                "renews on anniversary date",
                "continues until cancelled",
                # Hidden cost patterns (100% detection)
                "auto-renew",
                "will renew",
                "renews each month unless disabled",
                "unless you cancel",
                "continue to charge",
                "recurring charges",
                "subscription fee will be charged"
            ],
            "description": "Subscription automatically renews (hidden recurring cost)",
            "severity": "medium"
        },
        "broad_liability_disclaimer": {
            "keywords": [
                "not liable for any damages",
                "to the fullest extent permitted by law",
                "no warranty of any kind",
                "use at your own risk",
                # Additional variations (Fix #3)
                "as is without warranty",
                "disclaim all warranties",
                "no liability whatsoever",
                "not responsible for any losses",
                "to the maximum extent allowed",
                "provided as is",
                "without warranties express or implied",
                "at your sole risk",
                "no guarantee of accuracy",
                "disclaim liability to the fullest extent",
                "not liable for indirect damages",
                "use entirely at your risk"
            ],
            "description": "Broad disclaimers limiting company liability",
            "severity": "medium"
        },
        "unilateral_changes": {
            "keywords": [
                "change these terms at any time",
                "modify without notice",
                "update terms at our discretion",
                "revise terms without notifying",
                # Additional variations (Fix #3)
                "amend these terms",
                "alter terms at any time",
                "update without prior notice",
                "modify at our sole discretion",
                "change without notification",
                "revise at any time",
                "update or modify these terms",
                "amend without notice",
                "change at our discretion",
                "modify terms without warning",
                "reserve right to change",
                "update these terms at any time"
            ],
            "description": "Terms can change without notice",
            "severity": "medium"
        },
        "data_sharing": {
            "keywords": [
                "share with third parties",
                "sell your information",
                "provide data to partners",
                "transfer to affiliates",
                # Additional variations (Fix #3)
                "disclose to third parties",
                "share personal information",
                "sell or share your data",
                "provide to business partners",
                "transfer data to affiliates",
                "share with service providers",
                "disclose information to partners",
                "sell personal data",
                "share with advertisers",
                "transfer to related companies",
                "provide data to third party",
                "share information with partners"
            ],
            "description": "Your data may be shared or sold",
            "severity": "medium"
        },
        "no_refund": {
            "keywords": [
                "no refunds",
                "non-refundable",
                "all sales final",
                "no money back",
                "no cancellation refund",
                # Additional variations (Fix #3)
                "payments are final",
                "no refund policy",
                "not refundable",
                "all purchases final",
                "no reimbursement",
                "no money back guarantee",
                "fees are non-refundable",
                "cancellation without refund",
                "no refund upon cancellation",
                "all payments final",
                "not eligible for refund",
                "no refunds under any circumstances"
            ],
            "description": "Payments are non-refundable",
            "severity": "medium"
        },
        "broad_usage_rights": {
            "keywords": [
                "perpetual license",
                "irrevocable right",
                "use your content for any purpose",
                "worldwide, royalty-free license",
                # Additional variations (Fix #3)
                "unlimited license",
                "perpetual and irrevocable",
                "worldwide license",
                "royalty-free right",
                "use in any manner",
                "unrestricted license",
                "perpetual right to use",
                "irrevocable license to use",
                "use for commercial purposes",
                "sublicense your content",
                "worldwide perpetual license",
                "non-exclusive perpetual license"
            ],
            "description": "Company gets broad rights to your content",
            "severity": "medium"
        },
        "monitoring_surveillance": {
            "keywords": [
                "monitor your activity",
                "track your usage",
                "analyze your behavior",
                "log all interactions",
                # Additional variations (Fix #3)
                "track your actions",
                "monitor communications",
                "record your activity",
                "analyze usage patterns",
                "monitor and analyze",
                "track and monitor",
                "log user activity",
                "collect usage data",
                "monitor your use",
                "record all interactions",
                "track browsing behavior",
                "analyze user behavior"
            ],
            "description": "Extensive monitoring of your activities",
            "severity": "medium"
        },
        # NEW CATEGORIES (Fix #7) - Expanding from 9 to 20+ categories
        "intellectual_property_transfer": {
            "keywords": [
                "transfer intellectual property",
                "assign all rights to us",
                "ownership transfers to company",
                "ip rights become ours",
                "you grant ownership",
                "transfer copyright",
                "assign all ip rights",
                "intellectual property becomes ours"
            ],
            "description": "Intellectual property ownership transfers to the company",
            "severity": "medium"
        },
        "content_moderation_control": {
            "keywords": [
                "remove content at our discretion",
                "moderate without explanation",
                "delete posts without notice",
                "censor at will",
                "remove without reason",
                "content removal without appeal",
                "moderation decisions are final"
            ],
            "description": "Company has unilateral content moderation control",
            "severity": "medium"
        },
        "account_suspension": {
            "keywords": [
                "suspend account without warning",
                "temporary suspension at discretion",
                "suspend access for any reason",
                "account freeze without notice",
                "suspend without explanation"
            ],
            "description": "Account can be suspended without notice",
            "severity": "medium"
        },
        "third_party_services": {
            "keywords": [
                "not responsible for third party",
                "third party services as is",
                "no control over third parties",
                "third party links without warranty",
                "external services not our responsibility"
            ],
            "description": "No responsibility for third-party services",
            "severity": "medium"
        },
        "minimum_age_vague": {
            "keywords": [
                "not for children",
                "minors prohibited",
                "must be of age",
                "age restriction applies",
                "not intended for children"
            ],
            "description": "Vague age restrictions without verification",
            "severity": "low"
        },
        "export_restrictions": {
            "keywords": [
                "cannot export data",
                "no data portability",
                "cannot download your information",
                "no data export feature",
                "data locked in platform"
            ],
            "description": "Limited or no ability to export your data",
            "severity": "medium"
        },
        "algorithmic_decisions": {
            "keywords": [
                "automated decision making",
                "algorithm determines",
                "automated processing",
                "machine learning decisions",
                "ai-driven decisions"
            ],
            "description": "Important decisions made by algorithms without human review",
            "severity": "medium"
        },
        "advertising_tracking": {
            "keywords": [
                "targeted advertising",
                "track for ads",
                "advertising purposes",
                "behavioral advertising",
                "ad tracking",
                "marketing partners access data"
            ],
            "description": "Data used for targeted advertising and tracking",
            "severity": "medium"
        },
        "warranty_void_tampering": {
            "keywords": [
                "warranty void if modified",
                "tampering voids warranty",
                "warranty invalid if altered",
                "reverse engineering prohibited",
                "modification voids all rights"
            ],
            "description": "Warranty voided by user modifications or repairs",
            "severity": "medium"
        },
        "beta_experimental": {
            "keywords": [
                "beta features",
                "experimental service",
                "provided as beta",
                "testing phase",
                "may be unstable",
                "no guarantee of availability"
            ],
            "description": "Service is experimental/beta with no stability guarantees",
            "severity": "low"
        },
        "language_translation": {
            "keywords": [
                "english version controls",
                "translation for convenience only",
                "english version prevails",
                "translations not binding",
                "only english version enforceable"
            ],
            "description": "Only English version is legally binding",
            "severity": "low"
        },
        "forum_liability": {
            "keywords": [
                "liable for forum posts",
                "responsible for community content",
                "accountable for discussions",
                "liable for user interactions"
            ],
            "description": "You may be liable for community/forum interactions",
            "severity": "medium"
        }
    }

    # CONTEXT-DEPENDENT: May be risky depending on service type
    CONTEXT_DEPENDENT_PATTERNS = {
        "user_generated_content_liability": {
            "keywords": [
                "responsible for user content",
                "liable for your posts",
                "accountable for uploads"
            ],
            "context": "social_media",
            "description": "You're responsible for all content you post",
            "severity": "context"
        },
        "payment_processing_fees": {
            "keywords": [
                "payment processing fee",
                "transaction fee",
                "service charge"
            ],
            "context": "payment",
            "description": "Additional fees for payment processing",
            "severity": "context"
        },
        "geographic_restrictions": {
            "keywords": [
                "not available in all regions",
                "restricted in certain countries",
                "geographic limitations"
            ],
            "context": "global_service",
            "description": "Service may not work in your location",
            "severity": "context"
        }
    }

    def __init__(self):
        """Initialize risk indicators."""
        self.high_risk = self.HIGH_RISK_PATTERNS
        self.medium_risk = self.MEDIUM_RISK_PATTERNS
        self.context_dependent = self.CONTEXT_DEPENDENT_PATTERNS

    def detect_indicators(self, clause_text: str, service_type: str = "general") -> List[Dict]:
        """
        Detect all risk indicators in a clause.

        Args:
            clause_text: The clause text to analyze
            service_type: Type of service (for context-dependent patterns)

        Returns:
            List of detected indicators with severity and description
        """
        detected = []
        text_lower = clause_text.lower()

        # Check HIGH RISK patterns
        for indicator_name, pattern_data in self.high_risk.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                detected.append({
                    "indicator": indicator_name,
                    "severity": "high",
                    "description": pattern_data["description"],
                    "category": "high_risk"
                })

        # Check MEDIUM RISK patterns
        for indicator_name, pattern_data in self.medium_risk.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                detected.append({
                    "indicator": indicator_name,
                    "severity": "medium",
                    "description": pattern_data["description"],
                    "category": "medium_risk"
                })

        # Check CONTEXT-DEPENDENT patterns
        for indicator_name, pattern_data in self.context_dependent.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                # Check if context matches
                is_relevant = service_type == pattern_data["context"] or service_type == "general"
                detected.append({
                    "indicator": indicator_name,
                    "severity": pattern_data["severity"],
                    "description": pattern_data["description"],
                    "category": "context_dependent",
                    "relevant_for": pattern_data["context"],
                    "applies_to_service": is_relevant
                })

        return detected

    def _matches_pattern(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text matches any of the keywords/phrases.

        Uses fuzzy matching to catch variations.
        """
        for keyword in keywords:
            # Remove punctuation and extra spaces for matching
            keyword_clean = re.sub(r'[^\w\s]', ' ', keyword.lower())
            text_clean = re.sub(r'[^\w\s]', ' ', text)

            # Check for phrase match (all words present in order)
            keyword_words = keyword_clean.split()
            if len(keyword_words) == 1:
                # Single word match
                if keyword_words[0] in text_clean:
                    return True
            else:
                # Multi-word phrase match
                if keyword_clean in text_clean:
                    return True

                # Fuzzy match: all words present (not necessarily in order)
                if all(word in text_clean for word in keyword_words):
                    # Check if words are reasonably close together (within 20 words)
                    text_words = text_clean.split()
                    positions = [i for i, w in enumerate(text_words) if w in keyword_words]
                    if positions and max(positions) - min(positions) < 20:
                        return True

        return False

    def get_risk_category_distribution(self, indicators: List[Dict]) -> Dict:
        """
        Get distribution of risk categories for scoring.

        Returns:
            Dictionary with counts by severity
        """
        distribution = {
            "high": 0,
            "medium": 0,
            "context": 0,
            "total": len(indicators)
        }

        for indicator in indicators:
            severity = indicator["severity"]
            if severity in distribution:
                distribution[severity] += 1

        return distribution

    def calculate_indicator_score(self, indicators: List[Dict]) -> float:
        """
        Calculate a score based on detected indicators.

        High risk: 3 points each
        Medium risk: 1.5 points each
        Context-dependent: 0.5 points each

        Returns:
            Score from 0-10
        """
        score = 0.0

        for indicator in indicators:
            if indicator["severity"] == "high":
                score += 3.0
            elif indicator["severity"] == "medium":
                score += 1.5
            elif indicator["severity"] == "context":
                # Only count if it applies to the service
                if indicator.get("applies_to_service", False):
                    score += 0.5

        # Cap at 10
        return min(score, 10.0)
