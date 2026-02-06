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
                "we may terminate without liability",
                "discontinue service at any time",
                "cancel your access without warning",
                "terminate immediately and without cause",
                "terminate service without explanation",
                "we reserve the right to terminate",
                "terminate without prior notification",
                "discontinue without notice or liability",
                "suspend or cancel without reason",
                "termination at our sole option",
                "terminate your use without cause",
                "terminate your access without notice",
                # TikTok-style soft termination language
                "termination may happen without",
                "suspension or termination may happen",
                "may not give you advance notice",
                "permanently restrict or terminate",
                "temporarily suspend, permanently restrict",
            ],
            "description": "Company can terminate service without warning or reason",
            "severity": "high",
        },
        "content_loss": {
            "keywords": [
                "not responsible for data loss",
                "may delete your content without",
                "no backup obligation",
                "not liable for deleted data",
                "no guarantee of data retention",
                "files may be deleted at any time",
                "no obligation to preserve content",
                "data may be permanently deleted",
                "no backup or recovery obligation",
            ],
            "description": "Risk of losing your data without compensation",
            "severity": "high",
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
                "billing information automatically updated",
            ],
            "description": "Automatic payment method updates without explicit consent",
            "severity": "high",
        },
        "unlimited_liability": {
            "keywords": [
                "unlimited liability",
                "liable for all claims",
                "indemnify us for any and all",
                "hold us harmless for all",
                "responsible for any and all damages",
                "indemnify for all losses",
                "assume all liability",
                "indemnify against all claims",
                "bear all costs and damages",
                "indemnify and defend us against",
                "assume full responsibility for all",
                "bear unlimited responsibility",
            ],
            "description": "You assume unlimited liability for any issues",
            "severity": "high",
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
                "waive statutory rights",
            ],
            "description": "You waive important legal rights",
            "severity": "high",
        },
        "price_increase_no_notice": {
            "keywords": [
                "increase prices without notice",
                "change fees at any time",
                "modify pricing without notification",
                "raise prices without informing",
                "increase fees without warning",
                "pricing subject to change without notice",
                "price may change without notice",
                "change rates without warning",
                "adjust pricing without prior notice",
            ],
            "description": "Prices can increase without advance notice",
            "severity": "medium",
        },
        "forced_arbitration_class_waiver": {
            "keywords": [
                "waive right to class action",
                "no class action",
                "individual arbitration",
                "waive jury trial",
                "waive right to court",
                "no class or collective action",
                "individual basis only",
                "waive right to participate in class",
                "mandatory arbitration",
                "give up jury trial",
                "waive class action rights",
                "no right to join class action",
                "individual claims only",
                "waive right to litigate",
                "no consolidated proceedings",
                "waive representative actions",
                "past, pending, or future claims",
            ],
            "description": "Forced arbitration eliminates courts + class actions",
            "severity": "high",
        },
        "biometric_data_collection": {
            "keywords": [
                "faceprint", "voiceprint", "facial recognition", "voice recognition",
                "biometric data", "biometric information", "facial features",
                "voice characteristics", "fingerprint data", "retina scan",
                "iris scan", "gait analysis", "behavioral biometrics",
                "collect biometric", "process biometric", "use your face",
                "scan your face", "analyze your voice", "voice patterns",
                "facial geometry", "unique identifier from face"
            ],
            "description": "Collection of biometric data (faceprints, voiceprints, facial recognition)",
            "severity": "high"
        },
        "location_tracking_always_on": {
            "keywords": [
                "track location when app closed", "location in background",
                "always track location", "location when not using",
                "precise location continuously", "geolocation at all times",
                "track your movements", "monitor your location",
                "location tracking while inactive", "location data continuously",
                "even when app not open", "background location access",
                "track where you go", "location history tracking"
            ],
            "description": "Continuous location tracking even when app is closed",
            "severity": "high"
        },
        "keystroke_monitoring": {
            "keywords": [
                "keystroke", "typing patterns", "keyboard activity",
                "what you type", "monitor typing", "keylogging",
                "input monitoring", "text input patterns",
                "typing behavior", "keyboard usage", "track keystrokes",
                "capture keyboard", "record typing"
            ],
            "description": "Monitoring of keystroke patterns and typing behavior",
            "severity": "high"
        },
        "contact_harvesting": {
            "keywords": [
                "access your contacts", "phone book access",
                "upload your contacts", "harvest contacts",
                "contact list access", "phonebook sync",
                "contacts to our servers", "collect contact information",
                "access address book", "sync phonebook",
                "upload phonebook", "contact scraping"
            ],
            "description": "Harvesting and uploading your phone contacts",
            "severity": "high"
        },
        "cross_border_data_transfer": {
            "keywords": [
                "transfer to china",
                "servers in china",
                "foreign government access",
                "share with foreign entity",
                "transfer to foreign government",
            ],
            "description": "Transfer of data to foreign countries with weak privacy laws",
            "severity": "high"
        },
        "children_data_violation": {
            "keywords": [
                "collect children data without consent",
                "minors under 13", "coppa violation",
                "data from children", "knowingly collect from children",
                "under age 13", "child privacy violation",
                "children under 13"
            ],
            "description": "Collecting data from children without proper consent",
            "severity": "high"
        },
        # ============================================================
        # NEW HIGH RISK PATTERNS - Added based on Meta T&C analysis
        # ============================================================
        "perpetual_irrevocable_license": {
            "keywords": [
                # The "holy trinity" of bad content licensing
                "perpetual, irrevocable",
                "irrevocable, perpetual",
                "perpetual and irrevocable",
                "irrevocable and perpetual",
                "perpetual, irrevocable, transferable",
                "perpetual, irrevocable, royalty-free",
                "perpetual, irrevocable, sublicensable",
                "irrevocable license to use",
                "perpetual license that survives",
                "license survives termination",
                "even after you delete",
                "even after account deletion",
                "remains after you stop using",
                "continues after termination",
                # Explicit forever language
                "forever license",
                "license in perpetuity",
                "right survives termination",
                # Broad license combos (must be multi-word phrases)
                "sublicensable and transferable",
                "royalty-free, sublicensable",
                "sublicensable license",
                "license to use, copy, modify",
                "reproduce, modify, adapt",
                # AI Training (Reddit $203M+, Figma lawsuit)
                "use your content for AI",
                "train AI models",
                "train our systems",
                "use your content to train",
                # Moral rights waiver
                "moral rights waiver",
                "waive moral rights",
                "waive any rights of privacy",
                "waive publicity rights",
                # Commercial exploitation of user content
                "commercial exploitation",
                "use in advertisements",
                "without paying you",
                "without giving you anything in return",
                "without any compensation",
                # Content persistence after deletion
                "continue after you have removed",
                "licence granted will continue",
                "license shall continue after",
                "remains after you remove",
                "persists after you delete",
            ],
            "description": "Perpetual irrevocable content license + AI training - you lose control FOREVER",
            "severity": "high"
        },
        "explicit_account_termination": {
            "keywords": [
                "suspend or permanently disable your access",
                "permanently disable or delete your account",
                "permanently disable your account",
                "permanently delete your account",
                "disable your account permanently",
                "terminate your account permanently",
                # No appeal language
                "without appeal",
                "no right to reinstatement",
                "cannot be restored",
                "permanently banned",
            ],
            "description": "Company can permanently disable/delete your account with no recourse",
            "severity": "high"
        },
        "unilateral_content_removal": {
            "keywords": [
                "delete posts without notice",
                "remove content without warning",
                "remove content at our discretion",
                "take down without notice",
                "remove your content without explanation",
            ],
            "description": "Company can remove your content without notice or explanation",
            "severity": "medium"
        },
        "shortened_statute_limitations": {
            "keywords": [
                "must file within one year",
                "claims within 1 year",
                "within one (1) year",
                "one year statute",
                "one-year limitation",
                "shorten the statute",
                "reduced limitations period",
                "claim must be filed within",
                "waive longer limitation",
                "claims must be brought within",
                "action within one year",
                "limitation period of one year",
            ],
            "description": "Shortened time period to file legal claims",
            "severity": "high"
        },
        "asymmetric_jurisdiction": {
            "keywords": [
                "exclusive jurisdiction",
                "you agree to litigate in",
                "must bring claims in",
                "waive objection to venue",
                "submit to exclusive jurisdiction",
            ],
            "description": "Asymmetric jurisdiction - you must sue in company's home court",
            "severity": "medium"
        },
        # ============================================================
        # NEW HIGH RISK PATTERNS - From Comprehensive Research (24 patterns)
        # ============================================================
        "survival_clauses": {
            "keywords": [
                "survive termination", "survives expiration", "survive cancellation",
                "obligations shall survive", "provisions survive",
                "survives any termination", "continue after termination",
                "remain effective after", "binding after termination",
                # TikTok-style content persistence language
                "continue after you have removed",
                "licence granted will continue",
                "license granted will continue",
                "license shall continue after",
                "after you have removed your content",
                "may stay on third party",
            ],
            "description": "Obligations continue indefinitely after account closure",
            "severity": "medium"
        },
        "fund_holds_freezing": {
            "keywords": [
                "hold funds for 180 days", "reserve funds", "withhold payments",
                "freeze your account", "hold your balance", "payment reserve",
                "funds may be held", "rolling reserve", "payout delay",
                "hold for 90 days", "hold for 60 days", "withhold your funds",
                "payment hold", "balance reserve", "funds withheld",
                "account frozen", "suspend payouts", "delay disbursement"
            ],
            "description": "Company can freeze your money for extended periods (60-180+ days)",
            "severity": "high"
        },
        "warrantless_law_enforcement": {
            "keywords": [
                "law enforcement without warrant",
                "disclose to police without",
                "emergency disclosure without",
                "law enforcement partnership",
                "share with authorities without",
                "without a warrant",
                "without judicial oversight",
            ],
            "exclusions": [
                "warranty", "warranties", "disclaim", "as is", "as-is",
                "no warranty", "without warranty", "exclusion of warranties",
            ],
            "description": "Data shared with law enforcement without warrant requirement",
            "severity": "high"
        },
        "voice_video_retention": {
            "keywords": [
                "retain voice recordings", "store video indefinitely",
                "voice data retained",
                "employee access to recordings", "human review of recordings",
                "voice commands stored", "video footage retained",
                "recordings may be reviewed",
            ],
            "description": "Voice/video recordings stored indefinitely with employee access",
            "severity": "high"
        },
        "digital_ownership_illusion": {
            "keywords": [
                "purchase is a license",
                "purchased content may become unavailable",
                "terminate upon death",
                "no inheritance of digital",
                "license not ownership",
                "rights terminate upon death",
            ],
            "description": "Digital 'purchases' are revocable licenses, not ownership",
            "severity": "medium"
        },
        "worker_misclassification": {
            "keywords": [
                "independent contractor", "not an employee", "no employment benefits",
                "1099 contractor", "no workers compensation",
                "not entitled to benefits",
                "you are not our employee",
                "no employer-employee relationship",
            ],
            "description": "Workers denied employee protections via contractor classification",
            "severity": "medium"
        },
        "asymmetric_assignment": {
            "keywords": [
                "we may assign", "company may transfer", "assign without consent",
                "you may not assign", "non-transferable by you",
                "assign our rights", "transfer this agreement",
                "you cannot assign", "your rights are not assignable",
                "we may transfer without notice",
            ],
            "description": "Company can transfer your data/contract; you cannot",
            "severity": "medium"
        },
        # ============================================================
        # NEW: User-to-User License Pattern (for TikTok-style clauses)
        # ============================================================
        "user_content_license": {
            "keywords": [
                "grant to each user",
                "grant each user",
                "license to other users",
                "licence to other users",
                "other users may",
                "other users can",
                "each user of the platform",
                "users of the platform a",
                "non-exclusive, royalty-free, worldwide licence to access",
                "non-exclusive, royalty-free, worldwide license to access",
                "reproduce, adapt or make derivative",
                "access and use your content",
                "user a license to",
                "user a licence to",
            ],
            "description": "Other users get rights to copy and modify your content",
            "severity": "high"
        },
    }

    # MEDIUM RISK: Concerning but common in some industries
    MEDIUM_RISK_PATTERNS = {
        # ============================================================
        # NEW: Account Inactivity Reclaim Pattern
        # ============================================================
        "account_inactivity_reclaim": {
            "keywords": [
                "reclaim your account",
                "reclaim your account name",
                "not logged in for",
                "have not logged into",
                "inactive for",
                "6 months",
                "six months",
                "account name may be",
                "username reclaimed",
                "reclaim username",
                "account dormant",
            ],
            "description": "Your username/account can be reclaimed after inactivity",
            "severity": "medium"
        },
        # ============================================================
        # NEW: Cross-Platform Sync Pattern
        # ============================================================
        "cross_platform_sync": {
            "keywords": [
                "sync across",
                "settings will sync",
                "will sync across",
                "across each",
                "sync across the platform",
                "shared across services",
                "across all services",
                "data shared between",
                "information shared across",
            ],
            "description": "Your data and settings are shared across multiple services/apps",
            "severity": "medium"
        },
        "auto_renewal": {
            "keywords": [
                "automatically renew",
                "auto-renewal",
                "automatically extends",
                "renews unless cancelled",
                "automatic renewal",
                "renews automatically",
                "subscription continues automatically",
                "will renew unless you cancel",
                "renews for additional term",
                # Cancellation friction patterns
                "early termination fee", "cancellation fee",
                "call to cancel", "written notice to cancel",
                "penalty for early cancellation",
                "cancel only by phone",
            ],
            "description": "Subscription automatically renews with cancellation friction",
            "severity": "medium",
        },
        "broad_liability_disclaimer": {
            "keywords": [
                "not liable for any damages",
                "to the fullest extent permitted by law",
                "no warranty of any kind",
                "as is without warranty",
                "disclaim all warranties",
                "no liability whatsoever",
                "to the maximum extent allowed",
                "without warranties express or implied",
                "disclaim liability to the fullest extent",
                "not liable for indirect damages",
                "under no circumstances shall",
                "in no event shall",
                "consequential damages excluded",
                "loss of profits excluded",
            ],
            "description": "Broad disclaimers limiting company liability",
            "severity": "low",
        },
        "unilateral_changes": {
            "keywords": [
                "change these terms at any time",
                "modify without notice",
                "update terms at our discretion",
                "revise terms without notifying",
                "update without prior notice",
                "change without notification",
                "amend without notice",
                "modify terms without warning",
            ],
            "exclusions": [
                "notify you",
                "30 days",
                "prior notice",
                "advance notice",
                "reasonable notice",
                "written notice",
                "email notification",
            ],
            "description": "Terms can change without notice",
            "severity": "medium",
        },
        # NEW: Terms modification (even with notice - user should know)
        "terms_modification": {
            "keywords": [
                "may modify these terms",
                "modify these terms from time to time",
                "may change these terms",
                "reserve the right to modify these terms",
                "reserve the right to change these terms",
                "may update these terms",
                "amend these terms",
                "revise these terms",
                "changes that materially affect",
            ],
            "description": "Company can modify terms - check how you'll be notified of changes",
            "severity": "low",
        },
        # NEW: Binding arbitration (general - per inverted funnel, detect all)
        "binding_arbitration": {
            "keywords": [
                "resolved by arbitration",
                "finally resolved by arbitration",
                "referred to arbitration",
                "submit to arbitration",
                "shall be arbitrated",
                "binding arbitration",
                "arbitration proceedings",
                "arbitration process",
                "arbitral tribunal",
                "arbitration under",
                "arbitration rules",
                "International Chamber of Commerce",
                "ICC arbitration",
                "SIAC arbitration",
                "LCIA arbitration",
                "Hong Kong International Arbitration Centre",
                "Singapore International Arbitration Centre",
            ],
            "description": "Disputes must go to arbitration instead of court",
            "severity": "medium",
        },
        # NEW: Liability disclaimer (general)
        "liability_disclaimer": {
            "keywords": [
                "not take responsibility",
                "do not take responsibility",
                "disclaim all liability",
                "shall not be liable for any",
                "we are not liable for any",
                "we shall not be held liable",
                "not be responsible for any damage",
            ],
            "description": "Company limits its responsibility for damages and losses",
            "severity": "low",
        },
        "data_sharing": {
            "keywords": [
                "share with third parties",
                "sell your information",
                "sell or share your data",
                "sell personal data",
                "share with advertisers",
                "share personal information with third",
                "provide data to third party",
                "disclose personal information to",
            ],
            "description": "Your data may be shared or sold",
            "severity": "medium",
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
                "no refunds under any circumstances",
            ],
            "description": "Payments are non-refundable",
            "severity": "medium",
        },
        "broad_usage_rights": {
            "keywords": [
                "use your content for any purpose",
                "unlimited license to your content",
                "unrestricted license to use your",
                "use your content in any manner",
                "sublicense your content",
                "worldwide perpetual license to your",
            ],
            "description": "Company gets broad rights to your content",
            "severity": "medium",
        },
        "monitoring_surveillance": {
            "keywords": [
                "monitor your activity",
                "track your usage",
                "analyze your behavior",
                "log all interactions",
                "monitor communications",
                "record your activity",
                "track browsing behavior",
                "analyze user behavior",
            ],
            "description": "Extensive monitoring of your activities",
            "severity": "medium",
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
                "intellectual property becomes ours",
            ],
            "description": "Intellectual property ownership transfers to the company",
            "severity": "medium",
        },
        "content_moderation_control": {
            "keywords": [
                "remove content at our discretion",
                "moderate without explanation",
                "delete posts without notice",
                "censor at will",
                "remove without reason",
                "content removal without appeal",
                "moderation decisions are final",
            ],
            "description": "Company has unilateral content moderation control",
            "severity": "medium",
        },
        "account_suspension": {
            "keywords": [
                "suspend account without warning",
                "temporary suspension at discretion",
                "suspend access for any reason",
                "account freeze without notice",
                "suspend without explanation",
            ],
            "description": "Account can be suspended without notice",
            "severity": "medium",
        },
        "third_party_services": {
            "keywords": [
                "not responsible for third party",
                "third party services as is",
                "no control over third parties",
                "third party links without warranty",
                "external services not our responsibility",
            ],
            "description": "No responsibility for third-party services",
            "severity": "medium",
        },
        "minimum_age_vague": {
            "keywords": [
                "not for children",
                "minors prohibited",
                "must be of age",
                "age restriction applies",
                "not intended for children",
            ],
            "description": "Vague age restrictions without verification",
            "severity": "low",
        },
        "export_restrictions": {
            "keywords": [
                "cannot export data",
                "no data portability",
                "cannot download your information",
                "no data export feature",
                "data locked in platform",
            ],
            "description": "Limited or no ability to export your data",
            "severity": "medium",
        },
        "algorithmic_decisions": {
            "keywords": [
                "automated decision making",
                "algorithm determines",
                "automated processing",
                "machine learning decisions",
                "ai-driven decisions",
            ],
            "description": "Important decisions made by algorithms without human review",
            "severity": "medium",
        },
        "advertising_tracking": {
            "keywords": [
                "targeted advertising",
                "track for ads",
                "advertising purposes",
                "behavioral advertising",
                "ad tracking",
                "marketing partners access data",
            ],
            "description": "Data used for targeted advertising and tracking",
            "severity": "medium",
        },
        "warranty_void_tampering": {
            "keywords": [
                "warranty void if modified",
                "tampering voids warranty",
                "warranty invalid if altered",
                "reverse engineering prohibited",
                "modification voids all rights",
            ],
            "description": "Warranty voided by user modifications or repairs",
            "severity": "medium",
        },
        "beta_experimental": {
            "keywords": [
                "beta features",
                "experimental service",
                "provided as beta",
                "testing phase",
                "may be unstable",
                "no guarantee of availability",
            ],
            "description": "Service is experimental/beta with no stability guarantees",
            "severity": "low",
        },
        "language_translation": {
            "keywords": [
                "english version controls",
                "translation for convenience only",
                "english version prevails",
                "translations not binding",
                "only english version enforceable",
            ],
            "description": "Only English version is legally binding",
            "severity": "low",
        },
        "forum_liability": {
            "keywords": [
                "liable for forum posts",
                "responsible for community content",
                "accountable for discussions",
                "liable for user interactions",
            ],
            "description": "You may be liable for community/forum interactions",
            "severity": "medium",
        },
        "browsing_history_tracking": {
            "keywords": [
                "browsing history", "websites you visit",
                "track browsing", "web history", "online activity tracking",
                "sites you visit", "browser activity", "web tracking",
                "internet usage", "search history"
            ],
            "description": "Extensive tracking of browsing history",
            "severity": "medium"
        },
        "device_fingerprinting": {
            "keywords": [
                "device fingerprint", "unique device identifier",
                "hardware identifiers", "device characteristics",
                "browser fingerprint", "device signature",
                "unique device id", "device profiling"
            ],
            "description": "Creating unique device fingerprints for tracking",
            "severity": "medium"
        },
        "sensitive_data_categories": {
            "keywords": [
                "collect health information", "collect medical data",
                "sexual orientation", "religious beliefs", "political views",
                "racial data", "genetic information", "union membership",
                "sensitive personal data", "special category data"
            ],
            "description": "Collection of sensitive personal data categories",
            "severity": "medium"
        },
        # ============================================================
        # NEW MEDIUM RISK PATTERNS - Added based on Meta T&C analysis
        # ============================================================
        "slow_content_deletion": {
            "keywords": [
                # Slow deletion timeline (Meta Section 3.3)
                "up to 90 days to delete",
                "90 days to remove",
                "may take up to 90 days",
                "another 90 days",
                "remove from backups",
                "delete from backups",
                "backup and disaster recovery",
                "backup systems",
                "residual copies",
                "may remain in backups",
                "archived copies",
                "cached content",
                "180 days",
                "several months to delete",
                "deletion process takes",
                "not immediately deleted",
                "deletion may take time",
            ],
            "description": "Content deletion takes extended time (90-180 days) due to backup systems",
            "severity": "medium"
        },
        "indefinite_data_retention": {
            "keywords": [
                # Indefinite retention under legal excuse
                "retain indefinitely",
                "preserve for legal",
                "legal obligations for preservation",
                "record-keeping obligations",
                "retain for compliance",
                "keep data indefinitely",
                "no time limit on retention",
                "retain as long as necessary",
                "indefinite retention",
                "preserve evidence",
                "legal hold",
                "regulatory retention",
            ],
            "description": "Company can retain your data indefinitely under vague legal justification",
            "severity": "medium"
        },
        "broad_content_license": {
            "keywords": [
                "worldwide, royalty-free license",
                "worldwide, non-exclusive, royalty-free",
                "sublicensable, transferable license",
                "license to use, copy, modify",
                "create derivative works",
                "commercially exploit your content",
                "license to your content",
                "grant us a license to use",
                "you grant us a worldwide",
            ],
            "description": "Broad content licensing rights (sublicensable, worldwide, royalty-free)",
            "severity": "medium"
        },
        # ============================================================
        # NEW MEDIUM RISK PATTERNS - From Comprehensive Research
        # ============================================================
        "hipaa_coverage_gap": {
            "keywords": [
                "not HIPAA covered", "not subject to HIPAA", "wellness app",
                "health data not protected", "consumer health app",
                "not a covered entity", "non-clinical services",
                "not a healthcare provider", "wellness services",
                "fitness tracking", "health information not regulated"
            ],
            "description": "Health data lacks HIPAA protection - can be shared with employers/insurers",
            "severity": "medium"
        },
        "data_throttling": {
            "keywords": [
                "deprioritization", "may reduce speeds", "network management",
                "throttle data", "slower speeds during congestion",
                "unlimited plan may be slowed", "prioritization",
                "data may be slowed", "network congestion",
                "reduced speeds", "data speeds limited"
            ],
            "description": "Unlimited data plans subject to throttling/deprioritization",
            "severity": "medium"
        },
        "p2p_scam_liability": {
            "keywords": [
                "authorized transaction", "you authorized the transfer",
                "scam not covered", "fraud protection limited",
                "only unauthorized covered", "authorized payments final",
                "you initiated the payment", "your responsibility",
                "not liable for authorized", "fraud by third party"
            ],
            "description": "No protection if you're tricked into sending money (scams)",
            "severity": "medium"
        },
        "fdic_passthrough": {
            "keywords": [
                "partner bank", "FDIC pass-through", "funds held at",
                "third-party custodian", "banking partner", "member FDIC",
                "not directly insured", "held by partner",
                "banking services provided by", "deposits held at"
            ],
            "description": "FDIC protection depends on partner bank records (Synapse risk)",
            "severity": "medium"
        },
        "crypto_bankruptcy_risk": {
            "keywords": [
                "unsecured creditor", "no SIPC protection", "no FDIC for crypto",
                "bankruptcy", "insolvency", "customer assets may be",
                "not segregated", "general creditor",
                "cryptocurrency not insured", "digital assets risk",
                "no deposit insurance"
            ],
            "description": "Crypto holdings unprotected in company bankruptcy",
            "severity": "medium"
        },
        # ============================================================
        # NEW: Specific Liability Limitation Pattern (TikTok-style)
        # ============================================================
        "liability_limitation_specific": {
            "keywords": [
                "do not take responsibility for any loss",
                "not take responsibility for any damage",
                "we do not take responsibility",
                "not responsible for loss or damage",
            ],
            "description": "Company specifically disclaims responsibility for losses/damages",
            "severity": "low"
        },
        # ============================================================
        # NEW: No Content Guarantee Pattern (TikTok-style)
        # ============================================================
        "no_content_guarantee": {
            "keywords": [
                "does not promise that",
                "do not promise that",
                "not suited to your purpose",
                "does not represent our views",
                "no guarantees about accuracy",
            ],
            "description": "No guarantees about accuracy, legality, or quality of content",
            "severity": "low"
        },
    }

    # CONTEXT-DEPENDENT: May be risky depending on service type
    CONTEXT_DEPENDENT_PATTERNS = {
        "user_generated_content_liability": {
            "keywords": [
                "responsible for user content",
                "liable for your posts",
                "accountable for uploads",
            ],
            "context": "social_media",
            "description": "You're responsible for all content you post",
            "severity": "context",
        },
        "payment_processing_fees": {
            "keywords": ["payment processing fee", "transaction fee", "service charge"],
            "context": "payment",
            "description": "Additional fees for payment processing",
            "severity": "context",
        },
        "geographic_restrictions": {
            "keywords": [
                "not available in all regions",
                "restricted in certain countries",
                "geographic limitations",
            ],
            "context": "global_service",
            "description": "Service may not work in your location",
            "severity": "context",
        },
    }

    # ============================================================
    # DANGEROUS PATTERN CLUSTERS - Compound Risk Detection
    # When multiple patterns appear together, risk compounds
    # ============================================================
    DANGEROUS_PATTERN_CLUSTERS = {
        "legal_immunity_cluster": {
            "patterns": [
                "forced_arbitration_class_waiver", "broad_liability_disclaimer",
                "unlimited_liability", "asymmetric_jurisdiction"
            ],
            "description": "Near-complete legal immunity - makes any legal recourse impossible",
            "combined_severity": "critical",
            "min_patterns": 2  # Need at least 2 patterns to trigger
        },
        "content_exploitation_cluster": {
            "patterns": [
                "perpetual_irrevocable_license", "survival_clauses",
                "asymmetric_assignment", "broad_content_license"
            ],
            "description": "Permanent content control transferred to company forever",
            "combined_severity": "critical",
            "min_patterns": 2
        },
        "financial_trap_cluster": {
            "patterns": [
                "auto_renewal", "fund_holds_freezing", "explicit_account_termination",
                "unilateral_termination"
            ],
            "description": "Maximum financial extraction with no recourse",
            "combined_severity": "critical",
            "min_patterns": 2
        },
        "surveillance_cluster": {
            "patterns": [
                "data_sharing", "warrantless_law_enforcement",
                "voice_video_retention", "biometric_data_collection",
                "browsing_history_tracking", "device_fingerprinting"
            ],
            "description": "Comprehensive surveillance with law enforcement access",
            "combined_severity": "critical",
            "min_patterns": 3
        },
        "worker_exploitation_cluster": {
            "patterns": [
                "worker_misclassification", "forced_arbitration_class_waiver",
                "unlimited_liability", "unilateral_termination"
            ],
            "description": "Gig worker exploitation - no benefits, no recourse, no job security",
            "combined_severity": "critical",
            "min_patterns": 2
        },
        "digital_ownership_trap": {
            "patterns": [
                "digital_ownership_illusion", "unilateral_termination",
                "unilateral_changes", "explicit_account_termination"
            ],
            "description": "Your 'purchases' can be revoked at any time for any reason",
            "combined_severity": "high",
            "min_patterns": 2
        }
    }

    def __init__(self):
        """Initialize risk indicators."""
        self.high_risk = self.HIGH_RISK_PATTERNS
        self.medium_risk = self.MEDIUM_RISK_PATTERNS
        self.context_dependent = self.CONTEXT_DEPENDENT_PATTERNS

    def detect_indicators(
        self, clause_text: str, service_type: str = "general", section_name: str = ""
    ) -> List[Dict]:
        """
        Detect all risk indicators in a clause.

        Args:
            clause_text: The clause text to analyze
            service_type: Type of service (for context-dependent patterns)
            section_name: Name of the section (for boilerplate detection)

        Returns:
            List of detected indicators with severity and description
        """
        from .constants import WHITELIST_PATTERNS, SKIP_SINGLE_KEYWORDS, BOILERPLATE_SECTIONS

        detected = []
        text_lower = clause_text.lower()
        section_lower = section_name.lower().strip() if section_name else ""

        # ============================================================
        # WHITELIST CHECK: Skip flagging for standard/safe content
        # ============================================================
        for whitelist_category, whitelist_terms in WHITELIST_PATTERNS.items():
            for term in whitelist_terms:
                if term.lower() in text_lower:
                    # This clause contains whitelisted content (spam protection, etc.)
                    # Only skip if it's PRIMARILY about the whitelisted topic
                    if len(text_lower) < 500:  # Short clause = probably just about this topic
                        return []  # Skip detection entirely for safe content

        # ============================================================
        # BOILERPLATE SECTION CHECK: Reduce sensitivity for standard sections
        # ============================================================
        is_boilerplate_section = any(
            bp_section in section_lower for bp_section in BOILERPLATE_SECTIONS
        )

        # Import critical patterns to know which ones should never be skipped
        from .constants import CriticalPatterns

        # Check HIGH RISK patterns
        for indicator_name, pattern_data in self.high_risk.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                # Check for exclusions (pro-consumer language that negates the risk)
                exclusions = pattern_data.get("exclusions", [])
                if exclusions and self._matches_pattern(text_lower, exclusions):
                    # Has pro-consumer protection, skip this indicator
                    continue

                # Normalize indicator name for comparison
                indicator_normalized = indicator_name.lower().replace('-', '_').replace(' ', '_')

                # Check if this is a CRITICAL pattern that should never be skipped
                is_critical = indicator_normalized in CriticalPatterns.ALWAYS_CRITICAL

                # BOILERPLATE SKIP: Skip non-critical patterns in boilerplate sections
                if is_boilerplate_section and not is_critical:
                    continue  # Skip this indicator in boilerplate sections

                # Use the pattern's own severity (some HIGH_RISK patterns were downgraded to medium)
                pattern_severity = pattern_data.get("severity", "high")
                if is_critical:
                    pattern_severity = "critical"

                detected.append(
                    {
                        "indicator": indicator_name,
                        "severity": pattern_severity,
                        "description": pattern_data["description"],
                        "category": "high_risk" if pattern_severity in ("high", "critical") else "medium_risk",
                        "is_critical_pattern": is_critical,
                    }
                )

        # Check MEDIUM RISK patterns
        for indicator_name, pattern_data in self.medium_risk.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                # Check for exclusions (pro-consumer language that negates the risk)
                exclusions = pattern_data.get("exclusions", [])
                if exclusions and self._matches_pattern(text_lower, exclusions):
                    # Has pro-consumer protection, skip this indicator
                    continue

                # BOILERPLATE SKIP: Skip medium risk patterns in boilerplate sections
                if is_boilerplate_section:
                    continue  # Skip medium risk indicators in boilerplate sections

                # Use the pattern's own severity (some may have been set to low)
                medium_pattern_severity = pattern_data.get("severity", "medium")
                detected.append(
                    {
                        "indicator": indicator_name,
                        "severity": medium_pattern_severity,
                        "description": pattern_data["description"],
                        "category": "medium_risk" if medium_pattern_severity == "medium" else "low_risk",
                    }
                )

        # Check CONTEXT-DEPENDENT patterns
        for indicator_name, pattern_data in self.context_dependent.items():
            if self._matches_pattern(text_lower, pattern_data["keywords"]):
                # Check if context matches
                is_relevant = (
                    service_type == pattern_data["context"] or service_type == "general"
                )
                detected.append(
                    {
                        "indicator": indicator_name,
                        "severity": pattern_data["severity"],
                        "description": pattern_data["description"],
                        "category": "context_dependent",
                        "relevant_for": pattern_data["context"],
                        "applies_to_service": is_relevant,
                    }
                )

        return detected

    def _matches_pattern(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text matches any of the keywords/phrases.

        Uses fuzzy matching to catch variations.
        """
        for keyword in keywords:
            # Remove punctuation and extra spaces for matching
            keyword_clean = re.sub(r"[^\w\s]", " ", keyword.lower())
            text_clean = re.sub(r"[^\w\s]", " ", text.lower())  # FIXED: lowercase text for case-insensitive matching

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
                    positions = [
                        i for i, w in enumerate(text_words) if w in keyword_words
                    ]
                    if positions and max(positions) - min(positions) < 20:  # Keep tight proximity for accuracy
                        return True

        return False

    def get_risk_category_distribution(self, indicators: List[Dict]) -> Dict:
        """
        Get distribution of risk categories for scoring.

        Returns:
            Dictionary with counts by severity
        """
        distribution = {"high": 0, "medium": 0, "context": 0, "total": len(indicators)}

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

    def detect_pattern_clusters(self, detected_patterns: List[str]) -> List[Dict]:
        """
        Detect dangerous combinations of patterns that compound risk.

        When multiple patterns from a cluster appear together, the combined
        risk is greater than the sum of individual patterns.

        Args:
            detected_patterns: List of pattern names that were detected

        Returns:
            List of detected clusters with metadata
        """
        detected_clusters = []

        for cluster_name, cluster_info in self.DANGEROUS_PATTERN_CLUSTERS.items():
            matching_patterns = [
                p for p in cluster_info["patterns"]
                if p in detected_patterns
            ]

            min_required = cluster_info.get("min_patterns", 2)

            if len(matching_patterns) >= min_required:
                detected_clusters.append({
                    "cluster": cluster_name,
                    "description": cluster_info["description"],
                    "severity": cluster_info["combined_severity"],
                    "patterns_found": matching_patterns,
                    "patterns_possible": cluster_info["patterns"],
                    "coverage": f"{len(matching_patterns)}/{len(cluster_info['patterns'])}",
                    "coverage_ratio": len(matching_patterns) / len(cluster_info["patterns"])
                })

        # Sort by coverage ratio (most complete clusters first)
        detected_clusters.sort(key=lambda x: x["coverage_ratio"], reverse=True)

        return detected_clusters
