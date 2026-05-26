"""
Document Context Detector for T&C Analyzer.

Auto-detects document context from content analysis:
- Industry/vertical (developer_tools, social_media, gig_economy, etc.)
- User profile (professional, consumer, vulnerable_population)
- Power dynamics (negotiable, take_it_or_leave_it, monopoly)
- Data sensitivity level (low, medium, high, critical)

This context is used to adjust risk scores and reduce false positives.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DocumentContext:
    """Detected document context."""

    # Industry detection
    industry: str = "general"
    industry_confidence: float = 0.0
    industry_signals: List[str] = field(default_factory=list)

    # User profile
    user_profile: str = "consumer"
    user_profile_confidence: float = 0.0

    # Power dynamics
    power_dynamics: str = "take_it_or_leave_it"
    power_dynamics_confidence: float = 0.0

    # Data sensitivity
    data_sensitivity: str = "medium"
    data_types_detected: List[str] = field(default_factory=list)

    # Metadata
    company_name: Optional[str] = None
    jurisdiction: Optional[str] = None

    # Detection metadata
    detection_timestamp: datetime = field(default_factory=datetime.utcnow)
    detection_version: str = "1.0.0"


class DocumentContextDetector:
    """
    Auto-detects document context from content analysis.

    Uses keyword scoring and company name hints to determine:
    - What industry the T&C belongs to
    - Who the typical user is
    - What power dynamics exist
    - How sensitive the data being collected is
    """

    # =========================================================================
    # INDUSTRY DETECTION SIGNALS
    # Phase 1: 4 priority industries (developer_tools, social_media, gig_economy, saas)
    # =========================================================================

    INDUSTRY_SIGNALS = {
        'developer_tools': {
            'keywords': [
                'api', 'sdk', 'developer', 'webhook', 'endpoint', 'deploy',
                'integration', 'oauth', 'repository', 'code', 'github',
                'authentication', 'token', 'cli', 'documentation',
                'sandbox', 'production environment', 'staging',
                'rate limit', 'throttling', 'quota',
                'application programming interface', 'software development kit',
                'developer agreement', 'developer terms', 'api terms',
                'developer account', 'app store', 'marketplace',
            ],
            'company_hints': [
                'stripe', 'twilio', 'aws', 'amazon web services', 'azure',
                'google cloud', 'heroku', 'vercel', 'netlify', 'github',
                'gitlab', 'bitbucket', 'docker', 'kubernetes',
                'firebase', 'supabase', 'mongodb', 'redis',
                'apple developer', 'xcode', 'android studio',
                'npm', 'pypi', 'rubygems', 'maven',
            ],
            'document_type_hints': [
                'developer agreement', 'api terms', 'sdk license',
                'developer terms of service', 'platform terms',
            ],
            'weight': 1.0,
            'description': 'Developer tools, APIs, SDKs, cloud platforms'
        },

        'social_media': {
            'keywords': [
                'post', 'share', 'followers', 'following', 'feed', 'profile',
                'friends', 'messaging', 'reactions', 'stories', 'viral',
                'influencer', 'content creator', 'community guidelines',
                'user generated content', 'ugc', 'timeline', 'news feed',
                'like', 'comment', 'repost', 'retweet', 'hashtag',
                'direct message', 'dm', 'live stream', 'broadcast',
                'recommendation algorithm', 'for you page', 'fyp',
                'content moderation', 'community standards',
                'advertising', 'sponsored content', 'promoted',
            ],
            'company_hints': [
                'facebook', 'meta', 'instagram', 'twitter', 'x corp',
                'tiktok', 'bytedance', 'snapchat', 'snap inc',
                'linkedin', 'pinterest', 'reddit', 'discord',
                'youtube', 'twitch', 'threads', 'mastodon',
                'whatsapp', 'telegram', 'signal',
            ],
            'document_type_hints': [
                'community guidelines', 'content policy', 'terms of service',
            ],
            'weight': 1.0,
            'description': 'Social media platforms and messaging services'
        },

        'gig_economy': {
            'keywords': [
                'independent contractor', 'contractor', 'gig', 'flexible schedule',
                'driver', 'delivery', 'rider', 'courier', 'shopper',
                'task', 'on-demand', 'freelance', 'freelancer',
                'platform fee', 'service fee', 'booking fee',
                'rating', 'review', 'deactivation', 'reactivation',
                'background check', 'vehicle requirements',
                'earnings', 'payout', 'cash out', 'instant pay',
                'surge pricing', 'dynamic pricing', 'peak hours',
                'acceptance rate', 'cancellation rate', 'completion rate',
                'partner', 'fleet', 'dasher', 'shopper',
                '1099', 'self-employed', 'not an employee',
            ],
            'company_hints': [
                'uber', 'lyft', 'doordash', 'instacart', 'grubhub',
                'postmates', 'shipt', 'gopuff', 'spark',
                'fiverr', 'upwork', 'taskrabbit', 'handy',
                'rover', 'wag', 'care.com',
                'airbnb host', 'vrbo host', 'turo',
            ],
            'document_type_hints': [
                'driver agreement', 'dasher agreement', 'shopper agreement',
                'independent contractor agreement', 'partner terms',
            ],
            'weight': 1.0,
            'description': 'Gig economy and freelance platforms'
        },

        'saas': {
            'keywords': [
                'subscription', 'license', 'seat', 'user license',
                'enterprise', 'business', 'team', 'organization',
                'admin', 'administrator', 'workspace', 'tenant',
                'data processing', 'data retention', 'backup',
                'sla', 'service level agreement', 'uptime',
                'support', 'customer success', 'onboarding',
                'integration', 'export', 'import', 'migration',
                'saas', 'software as a service', 'cloud service',
                'annual', 'monthly', 'per user', 'per seat',
                'professional', 'business', 'enterprise plan',
            ],
            'company_hints': [
                'salesforce', 'hubspot', 'zendesk', 'intercom',
                'slack', 'zoom', 'microsoft 365', 'google workspace',
                'notion', 'asana', 'monday', 'trello', 'jira',
                'dropbox', 'box', 'docusign', 'adobe',
                'shopify', 'squarespace', 'wix',
                'mailchimp', 'sendgrid', 'twilio',
            ],
            'document_type_hints': [
                'subscription agreement', 'master service agreement',
                'terms of service', 'end user license agreement',
            ],
            'weight': 1.0,
            'description': 'SaaS and B2B software services'
        },

        # Phase 2 industries (basic detection, will be expanded later)
        'financial': {
            'keywords': [
                'bank', 'banking', 'transfer', 'deposit', 'withdrawal',
                'investment', 'loan', 'credit', 'debit', 'fdic',
                'finra', 'securities', 'trading', 'brokerage',
                'payment', 'transaction', 'balance', 'account',
            ],
            'company_hints': [
                'chase', 'wells fargo', 'bank of america', 'citi',
                'robinhood', 'venmo', 'paypal', 'cash app', 'zelle',
                'coinbase', 'binance', 'kraken',
            ],
            'document_type_hints': [],
            'weight': 0.8,
            'description': 'Financial services and fintech'
        },

        'healthcare': {
            'keywords': [
                'hipaa', 'medical', 'health record', 'prescription',
                'diagnosis', 'treatment', 'patient', 'provider',
                'phi', 'healthcare', 'telehealth', 'telemedicine',
            ],
            'company_hints': [
                'epic', 'cerner', 'teladoc', 'mdlive',
                'zocdoc', 'healthgrades',
            ],
            'document_type_hints': [],
            'weight': 0.8,
            'description': 'Healthcare and medical services'
        },

        'ecommerce': {
            'keywords': [
                'purchase', 'order', 'shipping', 'delivery', 'return',
                'refund', 'cart', 'checkout', 'payment', 'product',
                'seller', 'buyer', 'marketplace', 'listing',
            ],
            'company_hints': [
                'amazon', 'ebay', 'etsy', 'walmart', 'target',
                'shopify store', 'wayfair', 'overstock',
            ],
            'document_type_hints': [],
            'weight': 0.8,
            'description': 'E-commerce and online retail'
        },

        'streaming': {
            'keywords': [
                'stream', 'watch', 'video', 'movie', 'show', 'series',
                'subscription', 'premium', 'download', 'offline',
                'content', 'library', 'catalog',
            ],
            'company_hints': [
                'netflix', 'hulu', 'disney', 'hbo', 'paramount',
                'peacock', 'amazon prime video', 'apple tv',
                'spotify', 'apple music', 'youtube music',
            ],
            'document_type_hints': [],
            'weight': 0.8,
            'description': 'Streaming and entertainment services'
        },
    }

    # =========================================================================
    # USER PROFILE DETECTION
    # =========================================================================

    USER_PROFILE_SIGNALS = {
        'professional': {
            'keywords': [
                'business', 'enterprise', 'commercial use', 'b2b',
                'organization', 'company', 'corporate', 'professional',
                'team', 'workspace', 'admin', 'administrator',
                'commercial license', 'business account',
                'developer', 'api access', 'integration',
            ],
            'weight': 1.0
        },
        'consumer': {
            'keywords': [
                'personal use', 'individual', 'consumer', 'home',
                'family', 'non-commercial', 'user', 'member',
                'personal account', 'free tier', 'basic plan',
            ],
            'weight': 1.0
        },
        'vulnerable_population': {
            'keywords': [
                'child', 'children', 'minor', 'under 13', 'under 18',
                'coppa', 'parental consent', 'parent or guardian',
                'student', 'educational', 'school',
                'disability', 'accessibility', 'ada',
                'senior', 'elderly',
            ],
            'weight': 1.5  # Higher weight - more important to detect
        }
    }

    # =========================================================================
    # POWER DYNAMICS DETECTION
    # =========================================================================

    POWER_DYNAMICS_SIGNALS = {
        'negotiable': {
            'keywords': [
                'negotiate', 'negotiation', 'custom terms', 'custom agreement',
                'enterprise agreement', 'master service agreement',
                'contact sales', 'contact us for', 'tailored', 'bespoke',
                'volume discount', 'enterprise pricing',
            ],
            'weight': 1.0
        },
        'take_it_or_leave_it': {
            'keywords': [
                'by using', 'by accessing', 'by continuing',
                'agree to be bound', 'click to accept', 'i agree',
                'continued use constitutes acceptance',
                'your use of', 'if you do not agree',
                'binding agreement', 'binding arbitration',
            ],
            'weight': 1.0
        },
        'monopoly': {
            'keywords': [
                'no alternative', 'essential service', 'required by',
                'government mandate', 'exclusive', 'only provider',
            ],
            'company_hints': [
                # For certain services, these companies have monopoly-like positions
                'google', 'apple', 'microsoft', 'amazon',
            ],
            'weight': 0.8
        }
    }

    # =========================================================================
    # DATA SENSITIVITY DETECTION
    # =========================================================================

    DATA_SENSITIVITY_SIGNALS = {
        'critical': {
            'keywords': [
                'biometric', 'biometrics', 'fingerprint', 'face recognition',
                'facial recognition', 'voice print', 'retina', 'iris scan',
                'genetic', 'dna', 'health record', 'medical record',
                'ssn', 'social security', 'passport', 'government id',
                'driver license', 'financial account', 'bank account',
                'credit card number', 'debit card', 'cvv',
            ],
            'weight': 2.0
        },
        'high': {
            'keywords': [
                'location', 'gps', 'geolocation', 'precise location',
                'contacts', 'address book', 'phone contacts',
                'messages', 'sms', 'text messages', 'chat history',
                'emails', 'email content', 'call logs', 'call history',
                'browsing history', 'search history', 'web activity',
                'photos', 'camera', 'videos', 'microphone', 'audio',
                'health data', 'fitness data', 'sleep data',
            ],
            'weight': 1.5
        },
        'medium': {
            'keywords': [
                'name', 'email', 'email address', 'phone number',
                'address', 'mailing address', 'zip code',
                'date of birth', 'age', 'gender',
                'demographics', 'preferences', 'interests',
            ],
            'weight': 1.0
        },
        'low': {
            'keywords': [
                'anonymous', 'anonymized', 'aggregated', 'aggregate data',
                'device type', 'os version', 'browser type',
                'screen resolution', 'language preference',
                'crash reports', 'error logs', 'performance data',
            ],
            'weight': 0.5
        }
    }

    def __init__(self):
        """Initialize the document context detector."""
        self.industry_patterns = self._compile_patterns(self.INDUSTRY_SIGNALS)
        self.user_profile_patterns = self._compile_patterns(self.USER_PROFILE_SIGNALS)
        self.power_dynamics_patterns = self._compile_patterns(self.POWER_DYNAMICS_SIGNALS)
        self.data_sensitivity_patterns = self._compile_patterns(self.DATA_SENSITIVITY_SIGNALS)

    def _compile_patterns(self, signals: Dict) -> Dict:
        """Pre-compile regex patterns for faster matching."""
        compiled = {}
        for category, data in signals.items():
            keywords = data.get('keywords', [])
            # Create regex pattern that matches whole words
            pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
            compiled[category] = {
                'pattern': re.compile(pattern, re.IGNORECASE),
                'company_hints': [h.lower() for h in data.get('company_hints', [])],
                'document_type_hints': [h.lower() for h in data.get('document_type_hints', [])],
                'weight': data.get('weight', 1.0),
            }
        return compiled

    def detect_context(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentContext:
        """
        Analyze document to detect context.

        Args:
            document_text: Full document text
            metadata: Extracted metadata (company_name, document_type, etc.)

        Returns:
            DocumentContext with industry, user_profile, power_dynamics, data_sensitivity
        """
        metadata = metadata or {}
        text_lower = document_text.lower()

        # Detect industry
        industry, industry_confidence, industry_signals = self._detect_industry(
            text_lower, metadata
        )

        # Detect user profile
        user_profile, user_profile_confidence = self._detect_user_profile(text_lower)

        # Detect power dynamics
        power_dynamics, power_dynamics_confidence = self._detect_power_dynamics(
            text_lower, metadata
        )

        # Detect data sensitivity
        data_sensitivity, data_types = self._detect_data_sensitivity(text_lower)

        context = DocumentContext(
            industry=industry,
            industry_confidence=industry_confidence,
            industry_signals=industry_signals,
            user_profile=user_profile,
            user_profile_confidence=user_profile_confidence,
            power_dynamics=power_dynamics,
            power_dynamics_confidence=power_dynamics_confidence,
            data_sensitivity=data_sensitivity,
            data_types_detected=data_types,
            company_name=metadata.get('company_name'),
            jurisdiction=metadata.get('jurisdiction'),
        )

        logger.info(
            f"Context detected: industry={industry} ({industry_confidence:.2f}), "
            f"user_profile={user_profile}, power_dynamics={power_dynamics}, "
            f"data_sensitivity={data_sensitivity}"
        )

        return context

    def _detect_industry(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Tuple[str, float, List[str]]:
        """
        Detect industry from document text and metadata.

        Returns:
            Tuple of (industry, confidence, signals_found)
        """
        scores = {}
        signals_found = {}

        company_name = (metadata.get('company_name') or '').lower()
        document_type = (metadata.get('document_type') or '').lower()

        for industry, patterns in self.industry_patterns.items():
            score = 0.0
            signals = []

            # Keyword matching
            matches = patterns['pattern'].findall(text)
            if matches:
                # Count unique matches
                unique_matches = set(m.lower() for m in matches)
                keyword_score = len(unique_matches) * patterns['weight']
                score += keyword_score
                signals.extend(list(unique_matches)[:5])  # Keep top 5 signals

            # Company name hints (high weight)
            for hint in patterns['company_hints']:
                if hint in company_name:
                    score += 5.0 * patterns['weight']
                    signals.append(f"company:{hint}")
                    break

            # Document type hints
            for hint in patterns['document_type_hints']:
                if hint in document_type:
                    score += 2.0 * patterns['weight']
                    signals.append(f"doctype:{hint}")
                    break

            scores[industry] = score
            signals_found[industry] = signals

        # Find best match
        if not scores or max(scores.values()) == 0:
            return 'general', 0.0, []

        best_industry = max(scores, key=scores.get)
        best_score = scores[best_industry]

        # Calculate confidence (normalize to 0-1)
        # Score of 10+ = high confidence (1.0)
        # Score of 5 = medium confidence (0.5)
        # Score of 1 = low confidence (0.1)
        confidence = min(best_score / 10.0, 1.0)

        # If confidence is too low, default to 'general'
        if confidence < 0.2:
            return 'general', confidence, signals_found.get(best_industry, [])

        return best_industry, confidence, signals_found[best_industry]

    def _detect_user_profile(self, text: str) -> Tuple[str, float]:
        """
        Detect user profile type.

        Returns:
            Tuple of (user_profile, confidence)
        """
        scores = {}

        for profile, patterns in self.user_profile_patterns.items():
            matches = patterns['pattern'].findall(text)
            score = len(set(m.lower() for m in matches)) * patterns['weight']
            scores[profile] = score

        if not scores or max(scores.values()) == 0:
            return 'consumer', 0.5  # Default to consumer with medium confidence

        # Check for vulnerable population first (highest priority)
        if scores.get('vulnerable_population', 0) > 2:
            return 'vulnerable_population', min(scores['vulnerable_population'] / 5.0, 1.0)

        # Then check professional vs consumer
        if scores.get('professional', 0) > scores.get('consumer', 0):
            return 'professional', min(scores['professional'] / 5.0, 1.0)

        return 'consumer', min(scores.get('consumer', 0) / 5.0 + 0.3, 1.0)

    def _detect_power_dynamics(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Detect power dynamics.

        Returns:
            Tuple of (power_dynamics, confidence)
        """
        scores = {}
        company_name = (metadata.get('company_name') or '').lower()

        for dynamics, patterns in self.power_dynamics_patterns.items():
            matches = patterns['pattern'].findall(text)
            score = len(set(m.lower() for m in matches)) * patterns['weight']

            # Check company hints for monopoly detection
            if dynamics == 'monopoly':
                for hint in patterns.get('company_hints', []):
                    if hint in company_name:
                        score += 2.0
                        break

            scores[dynamics] = score

        # Default is take_it_or_leave_it (most common)
        if scores.get('negotiable', 0) > 3:
            return 'negotiable', min(scores['negotiable'] / 5.0, 1.0)

        if scores.get('monopoly', 0) > 2:
            return 'monopoly', min(scores['monopoly'] / 5.0, 1.0)

        # Most T&Cs are take-it-or-leave-it
        return 'take_it_or_leave_it', 0.8

    def _detect_data_sensitivity(self, text: str) -> Tuple[str, List[str]]:
        """
        Detect data sensitivity level.

        Returns:
            Tuple of (sensitivity_level, data_types_detected)
        """
        detected_types = []
        highest_sensitivity = 'low'
        sensitivity_order = ['low', 'medium', 'high', 'critical']

        for sensitivity, patterns in self.data_sensitivity_patterns.items():
            matches = patterns['pattern'].findall(text)
            if matches:
                unique_matches = list(set(m.lower() for m in matches))
                detected_types.extend(unique_matches[:3])  # Keep top 3 per category

                # Update highest sensitivity
                if sensitivity_order.index(sensitivity) > sensitivity_order.index(highest_sensitivity):
                    highest_sensitivity = sensitivity

        return highest_sensitivity, detected_types[:10]  # Keep top 10 overall
