# Anomaly Detection System - Technical Documentation

Complete technical specification for the 6-stage anomaly detection pipeline in the Terms & Conditions Analysis System.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Stage-by-Stage Documentation](#stage-by-stage-documentation)
4. [Configuration Options](#configuration-options)
5. [Performance Tuning](#performance-tuning)
6. [Baseline Corpus Requirements](#baseline-corpus-requirements)
7. [Active Learning Setup](#active-learning-setup)
8. [Monitoring & Metrics](#monitoring--metrics)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The anomaly detection system uses a sophisticated 6-stage pipeline to identify unusual or concerning clauses in Terms & Conditions documents while minimizing false positives and alert fatigue.

### Key Features

- **Multi-Method Detection**: Pattern-based, semantic similarity, and statistical outlier detection
- **Context-Aware Filtering**: Industry-specific and service-type filtering
- **ML-Powered Clustering**: Deduplication and noise reduction using legal-BERT embeddings
- **Compound Risk Detection**: Identifies systemic patterns across multiple clauses
- **Confidence Calibration**: Isotonic regression for accurate confidence scores
- **Alert Budget Management**: Prevents alert fatigue (MAX_ALERTS=10, TARGET_ALERTS=5)
- **Active Learning**: Continuous improvement through user feedback

### Performance Targets

| Metric | Target | Stage |
|--------|--------|-------|
| Recall | ≥ 95% | Stage 1 |
| False Positive Reduction | ≥ 70% | Stage 2 |
| Noise Reduction | 50-70% | Stage 3 |
| ECE (Calibration Error) | < 0.05 | Stage 5 |
| Max Alerts | ≤ 10 | Stage 6 |
| Total Processing Time | < 30s | Full Pipeline |

---

## Architecture

### Pipeline Flow

```
                        INPUT: Clauses from T&C Document
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 1: Multi-Method Detection                    │
        │  • Pattern-Based (40% weight)                       │
        │  • Semantic Similarity (35% weight)                 │
        │  • Statistical Outlier (25% weight)                 │
        │  Output: ~15-30 initial anomalies                   │
        └─────────────────┬───────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 2: Context Filtering                         │
        │  • Industry-Specific Filter                         │
        │  • Service Type Filter                              │
        │  • Temporal Filter (Changes vs New)                 │
        │  Output: ~10-20 filtered anomalies                  │
        └─────────────────┬───────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 3: Clustering & Deduplication                │
        │  • ML-Powered Clustering (legal-BERT)               │
        │  • Similarity Threshold: 0.85                       │
        │  • Representative Selection                         │
        │  Output: ~5-15 unique anomalies                     │
        └─────────────────┬───────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 4: Compound Risk Detection                   │
        │  • Privacy Erosion (3+ privacy violations)          │
        │  • Lock-in (subscription + fees + contract)         │
        │  • Legal Shield (arbitration + liability + class)   │
        │  • Control Imbalance (unilateral powers)            │
        │  • Children Exploitation (COPPA violations)         │
        │  • Dark Patterns (manipulative tactics)             │
        │  Output: 0-3 compound risk patterns                 │
        └─────────────────┬───────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 5: Confidence Calibration                    │
        │  • Isotonic Regression                              │
        │  • 3 Tiers: HIGH (85-100), MODERATE (60-85), LOW    │
        │  • Active Learning Feedback Loop                    │
        │  • Automatic Retraining (every 100 samples)         │
        │  Output: Calibrated confidence + tier labels        │
        └─────────────────┬───────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────────────┐
        │  STAGE 6: Alert Ranking & Budget                    │
        │  • Multi-Factor Scoring:                            │
        │    (Severity × Confidence × User_Relevance) + Bonus │
        │  • Alert Budget: MAX_ALERTS=10, TARGET_ALERTS=5     │
        │  • Categorization: HIGH / MEDIUM / LOW / SUPPRESSED │
        │  Output: 3-10 ranked, prioritized alerts            │
        └─────────────────┬───────────────────────────────────┘
                          ▼
                  Final Anomaly Report
              • Overall Risk Score (1-10)
              • Categorized Alerts
              • Compound Risks
              • Pipeline Performance Metrics
```

### File Structure

```
backend/app/core/
├── anomaly_detector.py              # Main pipeline orchestrator
├── confidence_calibrator.py         # Stage 5: Isotonic regression
├── active_learning_manager.py       # Stage 5: Feedback loop
├── alert_ranker.py                  # Stage 6: Ranking & budget
├── anomaly_detection_monitor.py     # Performance monitoring
└── filters/
    ├── industry_filter.py           # Stage 2: Industry filtering
    ├── service_type_filter.py       # Stage 2: Service type filtering
    └── temporal_filter.py           # Stage 2: Change detection

backend/app/core/clustering/
└── anomaly_clusterer.py             # Stage 3: ML clustering

backend/app/core/compound/
└── compound_risk_detector.py        # Stage 4: Pattern detection

backend/tests/
├── test_confidence_calibrator.py    # 30+ tests
├── test_active_learning_manager.py  # 40+ tests
├── test_alert_ranker.py             # 35+ tests
├── test_anomaly_detection_monitor.py # 35+ tests
└── test_anomaly_detection_pipeline.py # 20+ integration tests
```

---

## Stage-by-Stage Documentation

### Stage 1: Multi-Method Detection

**Purpose**: Maximize recall by using three complementary detection methods.

**File**: `backend/app/core/anomaly_detector.py`

#### Detection Methods

**1. Pattern-Based Detection (40% weight)**

Uses regex patterns to identify known problematic clauses:

```python
PATTERN_LIBRARY = {
    'data_selling': [
        r'sell.*personal\s+(data|information)',
        r'share.*data.*third\s+part(y|ies).*marketing',
        r'monetiz(e|ing).*user\s+(data|information)'
    ],
    'unlimited_liability_waiver': [
        r'not\s+liable\s+for\s+any\s+(damages|losses)',
        r'waive.*right.*sue',
        r'absolve.*responsibility'
    ],
    # ... 40+ pattern categories
}
```

**2. Semantic Similarity Detection (35% weight)**

Uses Pinecone vector database to find clauses similar to known anomalies:

```python
def _detect_semantic_anomalies(clause_text):
    # Embed clause text
    embedding = get_embedding(clause_text)

    # Query baseline corpus for similar clauses
    results = pinecone.query(
        vector=embedding,
        namespace='baseline',
        top_k=5,
        include_metadata=True
    )

    # Low similarity to baseline = potential anomaly
    if max(results['scores']) < SIMILARITY_THRESHOLD:
        return {
            'is_anomaly': True,
            'method': 'semantic_similarity',
            'baseline_similarity': max(results['scores'])
        }
```

**3. Statistical Outlier Detection (25% weight)**

Identifies clauses with unusual characteristics:

```python
def _detect_statistical_outliers(clause_text):
    features = {
        'length': len(clause_text),
        'complexity': calculate_complexity(clause_text),
        'negative_sentiment': get_sentiment_score(clause_text),
        'legal_jargon_density': calculate_jargon_ratio(clause_text)
    }

    # Compare to baseline distribution
    z_scores = calculate_z_scores(features)

    if any(abs(z) > 3 for z in z_scores.values()):
        return {'is_anomaly': True, 'method': 'statistical_outlier'}
```

#### Configuration

```python
# Detection weights (must sum to 1.0)
DETECTION_WEIGHTS = {
    'pattern_based': 0.40,
    'semantic_similarity': 0.35,
    'statistical_outlier': 0.25
}

# Thresholds
PATTERN_CONFIDENCE_BOOST = 0.15  # Boost for pattern matches
SEMANTIC_SIMILARITY_THRESHOLD = 0.70  # Lower = more dissimilar
STATISTICAL_Z_SCORE_THRESHOLD = 3.0  # Standard deviations
```

#### Performance

- **Target Recall**: ≥ 95%
- **Processing Time**: < 5 seconds for 50 clauses
- **Memory**: ~200MB for embeddings

---

### Stage 2: Context Filtering

**Purpose**: Reduce false positives by filtering context-appropriate anomalies.

**Files**:
- `backend/app/core/filters/industry_filter.py`
- `backend/app/core/filters/service_type_filter.py`
- `backend/app/core/filters/temporal_filter.py`

#### Industry Filter

Adjusts anomaly scores based on industry norms:

```python
INDUSTRY_ADJUSTMENTS = {
    'healthcare': {
        'hipaa_compliance': -0.3,  # Expected, reduce score
        'data_collection': -0.2,   # Medical records normal
        'third_party_sharing': 0.0 # Still concerning
    },
    'financial': {
        'account_termination': -0.2,  # Regulatory requirement
        'transaction_monitoring': -0.3, # AML compliance
        'data_retention': -0.1  # Required by law
    },
    'gaming': {
        'user_generated_content': -0.3,  # Expected
        'in_app_purchases': -0.2,  # Common
        'age_restrictions': -0.1  # Standard
    }
}
```

#### Service Type Filter

Filters based on service delivery model:

```python
SERVICE_TYPE_FILTERS = {
    'mobile_app': [
        'location_tracking',  # Common for mobile
        'push_notifications',  # Expected
        'device_permissions'   # Standard
    ],
    'subscription': [
        'auto_renewal',        # Expected for subscriptions
        'cancellation_policy', # Required disclosure
        'refund_policy'        # Standard
    ],
    'marketplace': [
        'user_transactions',   # Core functionality
        'seller_agreements',   # Required
        'dispute_resolution'   # Expected
    ]
}
```

#### Temporal Filter

Applies different thresholds for policy changes vs new policies:

```python
def apply_temporal_filter(anomalies, is_change=False):
    if is_change:
        # More lenient for changes
        for anomaly in anomalies:
            if anomaly['risk_category'] in EXPECTED_CHANGES:
                anomaly['confidence'] *= 0.8  # 20% reduction
    else:
        # Stricter for new policies
        for anomaly in anomalies:
            if anomaly['severity'] == 'low':
                anomaly['confidence'] *= 1.2  # 20% increase
```

#### Performance

- **Target FP Reduction**: ≥ 70%
- **Processing Time**: < 50ms per anomaly
- **False Negative Rate**: < 5%

---

### Stage 3: Clustering & Deduplication

**Purpose**: Group similar anomalies and reduce noise by 50-70%.

**File**: `backend/app/core/clustering/anomaly_clusterer.py`

#### Clustering Algorithm

Uses DBSCAN with legal-BERT embeddings:

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN

class AnomalyClusterer:
    def __init__(self):
        # Legal-BERT model for embeddings
        self.model = SentenceTransformer('nlpaueb/legal-bert-base-uncased')

    def cluster(self, anomalies):
        # Generate embeddings
        texts = [a['clause_text'] for a in anomalies]
        embeddings = self.model.encode(texts)

        # Cluster with DBSCAN
        clustering = DBSCAN(
            eps=0.15,        # Distance threshold (1 - 0.85 similarity)
            min_samples=2,   # Minimum cluster size
            metric='cosine'
        )
        labels = clustering.fit_predict(embeddings)

        # Select representatives
        return self._select_representatives(anomalies, labels, embeddings)
```

#### Representative Selection

Chooses the most representative anomaly from each cluster:

```python
def _select_representatives(self, anomalies, labels, embeddings):
    representatives = []

    for cluster_id in set(labels):
        if cluster_id == -1:  # Noise points
            continue

        # Get cluster members
        cluster_indices = [i for i, l in enumerate(labels) if l == cluster_id]
        cluster_anomalies = [anomalies[i] for i in cluster_indices]
        cluster_embeddings = embeddings[cluster_indices]

        # Select centroid (most central anomaly)
        centroid = cluster_embeddings.mean(axis=0)
        distances = [cosine_distance(emb, centroid) for emb in cluster_embeddings]
        representative_idx = cluster_indices[distances.index(min(distances))]

        # Add metadata
        representative = anomalies[representative_idx].copy()
        representative['cluster_size'] = len(cluster_indices)
        representative['related_clauses'] = [
            a['clause_number'] for a in cluster_anomalies
            if a['clause_number'] != representative['clause_number']
        ]

        representatives.append(representative)

    return representatives
```

#### Configuration

```python
# Clustering parameters
SIMILARITY_THRESHOLD = 0.85  # Cosine similarity for grouping
MIN_CLUSTER_SIZE = 2         # Minimum anomalies to form cluster
MAX_DISTANCE = 0.15          # 1 - SIMILARITY_THRESHOLD

# Representative selection
SELECTION_METHOD = 'centroid'  # 'centroid', 'highest_confidence', 'highest_severity'
```

#### Performance

- **Target Noise Reduction**: 50-70%
- **Processing Time**: < 2 seconds for 20 anomalies
- **Memory**: ~500MB for BERT model

---

### Stage 4: Compound Risk Detection

**Purpose**: Identify systemic patterns that span multiple clauses.

**File**: `backend/app/core/compound/compound_risk_detector.py`

#### Compound Patterns

**1. Privacy Erosion** (3+ privacy violations)
```python
PRIVACY_CATEGORIES = [
    'data_selling',
    'excessive_tracking',
    'behavioral_advertising',
    'location_tracking',
    'third_party_sharing',
    'biometric_data',
    'browsing_history'
]

# Trigger: 3 or more privacy-related anomalies
if len([a for a in anomalies if a['risk_category'] in PRIVACY_CATEGORIES]) >= 3:
    compound_risk = {
        'type': 'privacy_erosion',
        'name': 'Systematic Privacy Erosion',
        'severity': 'high',
        'description': 'Multiple clauses systematically erode user privacy'
    }
```

**2. Lock-in** (subscription + fees + long contract)
```python
LOCK_IN_INDICATORS = {
    'subscription': ['auto_renewal', 'subscription_terms'],
    'fees': ['cancellation_fee', 'early_termination_fee'],
    'contract': ['minimum_term', 'binding_period']
}

# Trigger: At least one from each category
if all(any(ind in anomalies for ind in indicators)
       for indicators in LOCK_IN_INDICATORS.values()):
    compound_risk = {'type': 'lock_in', ...}
```

**3. Legal Shield** (arbitration + liability + class action ban)
```python
LEGAL_SHIELD_COMPONENTS = [
    'mandatory_arbitration',
    'unlimited_liability_waiver',
    'class_action_waiver',
    'venue_selection',
    'short_statute_limitations'
]

# Trigger: 3+ legal shield components
if len([a for a in anomalies if a['risk_category'] in LEGAL_SHIELD_COMPONENTS]) >= 3:
    compound_risk = {'type': 'legal_shield', ...}
```

**4. Control Imbalance** (unilateral powers)
```python
CONTROL_CATEGORIES = [
    'unilateral_modification',
    'unilateral_termination',
    'forced_acceptance',
    'retroactive_changes'
]

# Trigger: 3+ control imbalance indicators
```

**5. Children Exploitation** (COPPA violations)
```python
CHILDREN_INDICATORS = [
    'coppa_violation',
    'collect_child_data',
    'market_to_children',
    'inadequate_parental_consent'
]

# Trigger: 2+ children-related violations
```

**6. Dark Patterns** (manipulative tactics)
```python
DARK_PATTERN_INDICATORS = [
    'hidden_costs',
    'bait_and_switch',
    'forced_continuity',
    'disguised_ads',
    'trick_questions'
]

# Trigger: 3+ dark pattern tactics
```

#### Configuration

```python
# Detection thresholds
COMPOUND_THRESHOLDS = {
    'privacy_erosion': 3,      # Min violations
    'lock_in': 3,              # All categories needed
    'legal_shield': 3,         # Min components
    'control_imbalance': 3,    # Min indicators
    'children_exploitation': 2, # Min violations
    'dark_patterns': 3          # Min tactics
}

# Severity mapping
COMPOUND_SEVERITY = {
    'privacy_erosion': 'high',
    'lock_in': 'high',
    'legal_shield': 'high',
    'control_imbalance': 'medium',
    'children_exploitation': 'critical',
    'dark_patterns': 'high'
}
```

#### Performance

- **Detection Rate**: 85-90% of known patterns
- **Processing Time**: < 1 second
- **False Positive Rate**: < 10%

---

### Stage 5: Confidence Calibration

**Purpose**: Provide accurate, well-calibrated confidence scores with ECE < 0.05.

**Files**:
- `backend/app/core/confidence_calibrator.py`
- `backend/app/core/active_learning_manager.py`

#### Isotonic Regression

Uses isotonic regression to calibrate confidence scores:

```python
from sklearn.isotonic import IsotonicRegression

class ConfidenceCalibrator:
    def __init__(self):
        self.calibrator = IsotonicRegression(
            out_of_bounds='clip',  # Clip to [0, 1]
            y_min=0.0,
            y_max=1.0
        )
        self.is_fitted = False

    def fit(self, predicted_probs, actual_labels):
        """
        Train calibrator on historical feedback.

        Args:
            predicted_probs: Raw confidence scores (0-1)
            actual_labels: True labels (1=correct, 0=incorrect)
        """
        self.calibrator.fit(predicted_probs, actual_labels)
        self.is_fitted = True

        # Calculate calibration quality
        calibrated_probs = self.calibrator.predict(predicted_probs)
        self.last_ece = self._calculate_expected_calibration_error(
            calibrated_probs, actual_labels
        )
        self.brier_score_before = brier_score_loss(actual_labels, predicted_probs)
        self.brier_score_after = brier_score_loss(actual_labels, calibrated_probs)
```

#### Confidence Tiers

Three tiers for user communication:

```python
CONFIDENCE_TIERS = {
    'HIGH': {
        'range': (0.85, 1.00),
        'label': 'High Confidence',
        'explanation_template': (
            'We are {calibrated_confidence:.0%} confident this is a genuine concern '
            'based on our analysis of 100+ similar documents.'
        )
    },
    'MODERATE': {
        'range': (0.60, 0.85),
        'label': 'Moderate Confidence',
        'explanation_template': (
            'This appears concerning ({calibrated_confidence:.0%} confidence), '
            'but review the specifics for your situation.'
        )
    },
    'LOW': {
        'range': (0.00, 0.60),
        'label': 'Low Confidence',
        'explanation_template': (
            'This might be an issue ({calibrated_confidence:.0%} confidence). '
            'Check if it applies to your use case.'
        )
    }
}
```

#### Active Learning

Continuous improvement through user feedback:

```python
class ActiveLearningManager:
    def __init__(self, calibrator):
        self.calibrator = calibrator
        self.feedback_buffer = []
        self.dismissal_threshold = 0.20  # Alert if >20% dismissed
        self.retrain_after_samples = 100  # Retrain frequency

    def collect_feedback(self, anomaly_id, user_action, confidence):
        """
        Collect user feedback for active learning.

        Args:
            anomaly_id: Unique anomaly identifier
            user_action: 'helpful', 'acted_on', 'dismissed', 'false_positive'
            confidence: Confidence score when shown to user
        """
        was_correct = user_action in ['helpful', 'acted_on']

        self.feedback_buffer.append({
            'anomaly_id': anomaly_id,
            'user_action': user_action,
            'confidence': confidence,
            'was_correct': was_correct,
            'timestamp': datetime.utcnow()
        })

        # Check if retraining needed
        if len(self.feedback_buffer) >= self.retrain_after_samples:
            self._retrain_calibrator()

    def _retrain_calibrator(self):
        """Retrain calibrator with accumulated feedback."""
        predictions = [f['confidence'] for f in self.feedback_buffer]
        labels = [1 if f['was_correct'] else 0 for f in self.feedback_buffer]

        self.calibrator.fit(predictions, labels)

        # Monitor dismissal rate
        dismissals = sum(1 for f in self.feedback_buffer
                        if f['user_action'] in ['dismissed', 'false_positive'])
        dismissal_rate = dismissals / len(self.feedback_buffer)

        if dismissal_rate > self.dismissal_threshold:
            logger.warning(
                f'High dismissal rate: {dismissal_rate:.1%} '
                f'(threshold: {self.dismissal_threshold:.1%})'
            )

        # Clear buffer
        self.feedback_buffer.clear()
```

#### Expected Calibration Error (ECE)

Measures calibration quality:

```python
def _calculate_expected_calibration_error(self, predicted, actual, n_bins=10):
    """
    Calculate Expected Calibration Error.

    ECE measures the difference between predicted probabilities and
    actual frequencies. Lower is better (perfect = 0.0).

    Target: ECE < 0.05 (5%)
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        # Get predictions in this bin
        bin_mask = (predicted >= bin_boundaries[i]) & (predicted < bin_boundaries[i+1])
        if not bin_mask.any():
            continue

        # Calculate average confidence and accuracy in bin
        avg_confidence = predicted[bin_mask].mean()
        avg_accuracy = actual[bin_mask].mean()
        bin_weight = bin_mask.sum() / len(predicted)

        # Add weighted difference to ECE
        ece += bin_weight * abs(avg_confidence - avg_accuracy)

    return ece
```

#### Configuration

```python
# Calibration settings
CALIBRATION_METHOD = 'isotonic'  # 'isotonic', 'platt', 'beta'
MIN_TRAINING_SAMPLES = 50        # Minimum samples to fit

# Active learning
RETRAIN_AFTER_SAMPLES = 100      # Automatic retraining frequency
DISMISSAL_THRESHOLD = 0.20       # Alert if >20% dismissed
UNCERTAINTY_SAMPLING = True      # Prioritize uncertain samples

# Confidence tiers
HIGH_CONFIDENCE_MIN = 0.85
MODERATE_CONFIDENCE_MIN = 0.60
```

#### Performance

- **Target ECE**: < 0.05
- **Training Time**: < 1 second for 100 samples
- **Inference Time**: < 1ms per anomaly
- **Memory**: ~10MB

---

### Stage 6: Alert Ranking & Budget

**Purpose**: Prevent alert fatigue by ranking and limiting alerts to 3-10.

**File**: `backend/app/core/alert_ranker.py`

#### Multi-Factor Scoring

Scores each anomaly using multiple factors:

```python
def _score_anomaly(anomaly, document_context):
    """
    Score = (Severity_Weight × Confidence × User_Relevance) + Bonuses
    """
    # Base score components
    severity_weight = SEVERITY_WEIGHTS[anomaly['severity']]  # 1-4
    confidence = anomaly['confidence_calibration']['calibrated_confidence']
    user_relevance = self._calculate_user_relevance(anomaly, document_context)

    base_score = severity_weight * confidence * user_relevance

    # Bonuses
    bonuses = 0.0

    # Compound risk bonus (+5.0)
    if anomaly.get('is_compound_risk'):
        bonuses += BONUS_COMPOUND_RISK

    # Recent change bonus (+2.0)
    if document_context.get('is_change'):
        bonuses += BONUS_RECENT_CHANGE

    # Industry critical bonus (+1.5)
    if self._is_industry_critical(anomaly, document_context):
        bonuses += BONUS_INDUSTRY_CRITICAL

    # Regulatory violation bonus (+3.0)
    if self._is_regulatory_violation(anomaly):
        bonuses += BONUS_REGULATORY_VIOLATION

    final_score = base_score + bonuses

    return {
        'final_score': final_score,
        'base_score': base_score,
        'bonus_total': bonuses,
        'breakdown': {
            'severity_weight': severity_weight,
            'confidence': confidence,
            'user_relevance': user_relevance,
            'bonuses': {
                'compound_risk': bonuses if anomaly.get('is_compound_risk') else 0,
                'recent_change': bonuses if document_context.get('is_change') else 0,
                'industry_critical': bonuses if self._is_industry_critical(anomaly, document_context) else 0,
                'regulatory': bonuses if self._is_regulatory_violation(anomaly) else 0
            }
        }
    }
```

#### Alert Budget Management

Enforces MAX_ALERTS=10, targets 3-5 alerts:

```python
def rank_and_filter(self, calibrated_anomalies, compound_risks, document_context):
    """
    Rank and filter anomalies to prevent alert fatigue.
    """
    # Combine regular anomalies and compound risks
    all_anomalies = calibrated_anomalies + self._convert_compound_risks(compound_risks)

    # Score each anomaly
    for anomaly in all_anomalies:
        scoring = self._score_anomaly(anomaly, document_context)
        anomaly['ranking_score'] = scoring['final_score']
        anomaly['scoring_breakdown'] = scoring['breakdown']

    # Sort by score (descending)
    sorted_anomalies = sorted(all_anomalies, key=lambda x: x['ranking_score'], reverse=True)

    # Categorize by confidence tier
    high_severity = []
    medium_severity = []
    low_severity = []
    suppressed = []

    for anomaly in sorted_anomalies:
        tier = anomaly['confidence_calibration']['confidence_tier']

        # Apply alert budget
        total_shown = len(high_severity) + len(medium_severity) + len(low_severity)

        if total_shown >= MAX_ALERTS:
            suppressed.append(anomaly)
            continue

        # Categorize
        if tier == 'HIGH' or anomaly.get('is_compound_risk'):
            high_severity.append(anomaly)
        elif tier == 'MODERATE':
            medium_severity.append(anomaly)
        else:
            low_severity.append(anomaly)

    return {
        'high_severity': high_severity,
        'medium_severity': medium_severity,
        'low_severity': low_severity,
        'suppressed': suppressed,
        'total_detected': len(all_anomalies),
        'total_shown': len(high_severity) + len(medium_severity) + len(low_severity),
        'ranking_metadata': {
            'alert_budget_applied': len(suppressed) > 0,
            'avg_score': np.mean([a['ranking_score'] for a in sorted_anomalies]),
            'top_score': sorted_anomalies[0]['ranking_score'] if sorted_anomalies else 0
        }
    }
```

#### Configuration

```python
# Alert budget
MAX_ALERTS = 10      # Hard limit
TARGET_ALERTS = 5    # Ideal target

# Severity weights
SEVERITY_WEIGHTS = {
    'low': 1.0,
    'medium': 2.0,
    'high': 3.0,
    'critical': 4.0
}

# Bonuses
BONUS_COMPOUND_RISK = 5.0          # Systemic patterns
BONUS_RECENT_CHANGE = 2.0          # Policy changes
BONUS_INDUSTRY_CRITICAL = 1.5      # Industry-specific
BONUS_REGULATORY_VIOLATION = 3.0   # Legal violations

# Industry critical combinations
INDUSTRY_CRITICAL_COMBINATIONS = {
    'health_apps': ['data_selling', 'hipaa_violation', 'medical_data_sharing'],
    'financial_apps': ['unauthorized_transaction_liability', 'financial_data_selling'],
    'children_apps': ['coppa_violation', 'market_to_children', 'collect_child_data'],
    'dating_apps': ['sexual_orientation_sharing', 'precise_location']
}

# Regulatory violations
REGULATORY_VIOLATIONS = [
    'gdpr_violation',
    'ccpa_violation',
    'coppa_violation',
    'hipaa_violation',
    'cfpb_prohibited_term'
]
```

#### Performance

- **Alert Budget Compliance**: 100%
- **Processing Time**: < 100ms
- **User Satisfaction**: Target 75%+ alerts rated helpful

---

## Configuration Options

### Environment Variables

```bash
# Anomaly Detection Settings
ANOMALY_DETECTION_ENABLED=true
BASELINE_CORPUS_SIZE=100            # Minimum baseline T&Cs

# Stage 1: Detection
PATTERN_WEIGHT=0.40                 # Pattern-based weight
SEMANTIC_WEIGHT=0.35                # Semantic similarity weight
STATISTICAL_WEIGHT=0.25             # Statistical outlier weight

# Stage 2: Filtering
ENABLE_INDUSTRY_FILTER=true
ENABLE_SERVICE_TYPE_FILTER=true
ENABLE_TEMPORAL_FILTER=true

# Stage 3: Clustering
CLUSTERING_SIMILARITY_THRESHOLD=0.85
CLUSTERING_MIN_SAMPLES=2

# Stage 4: Compound Risks
COMPOUND_DETECTION_ENABLED=true
PRIVACY_EROSION_THRESHOLD=3
LOCK_IN_THRESHOLD=3

# Stage 5: Calibration
CALIBRATION_METHOD=isotonic
MIN_CALIBRATION_SAMPLES=50
RETRAIN_AFTER_SAMPLES=100
DISMISSAL_THRESHOLD=0.20

# Stage 6: Alert Ranking
MAX_ALERTS=10
TARGET_ALERTS=5
ENABLE_USER_PREFERENCES=true

# Performance
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_PROCESSING_TIME_SECONDS=30
```

### Configuration File

`config/anomaly_detection.yaml`:

```yaml
anomaly_detection:
  enabled: true

  stage1_detection:
    methods:
      pattern_based:
        enabled: true
        weight: 0.40
      semantic_similarity:
        enabled: true
        weight: 0.35
        threshold: 0.70
      statistical_outlier:
        enabled: true
        weight: 0.25
        z_score_threshold: 3.0

  stage2_filtering:
    industry_filter:
      enabled: true
      adjustments:
        healthcare:
          hipaa_compliance: -0.3
          data_collection: -0.2
    service_type_filter:
      enabled: true
    temporal_filter:
      enabled: true
      change_penalty: 0.8

  stage3_clustering:
    enabled: true
    similarity_threshold: 0.85
    min_cluster_size: 2
    model: "nlpaueb/legal-bert-base-uncased"

  stage4_compound:
    enabled: true
    patterns:
      privacy_erosion: 3
      lock_in: 3
      legal_shield: 3

  stage5_calibration:
    method: "isotonic"
    min_samples: 50
    active_learning:
      enabled: true
      retrain_after: 100
      dismissal_threshold: 0.20

  stage6_ranking:
    max_alerts: 10
    target_alerts: 5
    severity_weights:
      low: 1.0
      medium: 2.0
      high: 3.0
      critical: 4.0
    bonuses:
      compound_risk: 5.0
      recent_change: 2.0
      industry_critical: 1.5
      regulatory: 3.0
```

---

## Performance Tuning

### Memory Optimization

**1. Model Caching**
```python
# Cache BERT model to avoid reloading
@lru_cache(maxsize=1)
def get_bert_model():
    return SentenceTransformer('nlpaueb/legal-bert-base-uncased')
```

**2. Embedding Batching**
```python
# Batch embed clauses for efficiency
def batch_embed(texts, batch_size=32):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch)
        embeddings.extend(batch_embeddings)
    return np.array(embeddings)
```

**3. Vector DB Query Optimization**
```python
# Use metadata filtering to reduce query scope
results = pinecone.query(
    vector=embedding,
    filter={'industry': 'healthcare'},  # Narrow search
    top_k=5
)
```

### Processing Speed

**1. Parallel Stage Execution**
```python
from concurrent.futures import ThreadPoolExecutor

# Stages 1-2 can run in parallel with document processing
with ThreadPoolExecutor(max_workers=2) as executor:
    future_stage1 = executor.submit(run_stage1, clauses)
    future_metadata = executor.submit(extract_metadata, document)

    stage1_result = future_stage1.result()
    metadata = future_metadata.result()
```

**2. Early Termination**
```python
# Skip expensive stages if few anomalies detected
if len(stage1_anomalies) < 3:
    logger.info("Few anomalies detected, skipping clustering")
    return simple_filter(stage1_anomalies)
```

**3. Caching**
```python
# Cache calibrated confidences
@lru_cache(maxsize=1000)
def calibrate_confidence(raw_confidence):
    return calibrator.calibrate(raw_confidence)
```

### Accuracy Improvements

**1. Ensemble Methods**
```python
# Combine multiple detection methods with voting
def ensemble_detect(clause):
    votes = []
    votes.append(pattern_detect(clause))
    votes.append(semantic_detect(clause))
    votes.append(statistical_detect(clause))

    # Require 2/3 agreement
    return sum(votes) >= 2
```

**2. Calibrator Fine-Tuning**
```python
# Use stratified sampling for balanced training
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5)
for train_idx, val_idx in skf.split(predictions, labels):
    train_preds = predictions[train_idx]
    train_labels = labels[train_idx]
    calibrator.fit(train_preds, train_labels)
```

**3. Active Learning Prioritization**
```python
# Prioritize uncertain samples for feedback
def get_uncertainty_samples(anomalies, n=5):
    # Uncertainty = distance from 0.5
    uncertainties = [abs(0.5 - a['confidence']) for a in anomalies]
    sorted_indices = np.argsort(uncertainties)
    return [anomalies[i] for i in sorted_indices[:n]]
```

---

## Baseline Corpus Requirements

### Minimum Requirements

**Quantity**: 100+ Terms & Conditions documents

**Diversity**:
- 10+ industries (healthcare, finance, gaming, etc.)
- 5+ service types (mobile app, web service, subscription, etc.)
- Various document lengths (5-50 pages)
- Multiple jurisdictions (US, EU, etc.)

**Quality**:
- Legitimate, real-world T&Cs from established companies
- Recent documents (within 2 years)
- Clean text extraction (no OCR errors)
- Proper structure (sections, clauses)

### Collection Process

1. **Identify Sources**:
   - App stores (iOS App Store, Google Play)
   - Company websites
   - Public policy archives
   - Legal databases

2. **Download & Process**:
   ```bash
   # Use data collection script
   python scripts/collect_baseline_corpus.py \
       --target-count 100 \
       --industries healthcare,finance,gaming \
       --output data/baseline_corpus/
   ```

3. **Quality Check**:
   ```bash
   # Validate corpus quality
   python scripts/validate_corpus.py \
       --corpus-dir data/baseline_corpus/ \
       --min-documents 100 \
       --check-diversity
   ```

4. **Index to Pinecone**:
   ```bash
   # Index baseline corpus
   python scripts/index_baseline.py \
       --corpus-dir data/baseline_corpus/ \
       --namespace baseline \
       --batch-size 100
   ```

### Baseline Update Strategy

**Frequency**: Quarterly (every 3 months)

**Process**:
1. Collect 25-50 new T&Cs
2. Remove outdated documents (>2 years old)
3. Re-index updated corpus
4. Validate detection accuracy on test set

---

## Active Learning Setup

### Initial Calibrator Training

**Minimum Requirements**: 500+ labeled feedback samples

**Data Collection Strategy**:

1. **Cold Start (0-100 samples)**:
   - Use synthetic labels from expert review
   - Label high-confidence detections manually
   - Focus on diverse anomaly types

2. **Warm Start (100-500 samples)**:
   - Deploy to limited user group (beta testers)
   - Collect natural feedback
   - Monitor dismissal rate

3. **Production (500+ samples)**:
   - Full deployment with active learning
   - Continuous improvement
   - Automatic retraining every 100 samples

### Feedback Collection

**API Integration**:
```python
# POST /api/v1/anomalies/{anomaly_id}/feedback
{
    "user_action": "helpful",  # or "dismiss", "not_applicable", "acted_on"
    "feedback_text": "This helped me avoid a bad contract",
    "confidence_at_detection": 0.87
}
```

**User Actions**:
- `helpful`: User found anomaly useful (label: correct)
- `acted_on`: User took action based on anomaly (label: correct)
- `dismiss`: User dismissed as unimportant (label: incorrect)
- `not_applicable`: Doesn't apply to user's situation (label: incorrect)

### Retraining Schedule

**Automatic Retraining**:
- Triggers after 100 new feedback samples
- Runs asynchronously to avoid blocking
- Updates calibrator model
- Logs performance metrics

**Manual Retraining**:
```bash
# Force calibrator retraining
python scripts/retrain_calibrator.py \
    --feedback-source database \
    --min-samples 100 \
    --validate
```

### Quality Monitoring

**Dismissal Rate Alert**:
```python
# Alert if dismissal rate > 20%
if dismissal_rate > 0.20:
    send_alert(
        severity='warning',
        message=f'High dismissal rate: {dismissal_rate:.1%}',
        recommendations=[
            'Review recent anomaly detections',
            'Check for pattern overfitting',
            'Consider adjusting detection thresholds'
        ]
    )
```

---

## Monitoring & Metrics

### Key Performance Indicators

**Detection Quality**:
- Recall: % of true anomalies detected (target: ≥95%)
- Precision: % of detections that are true anomalies (target: ≥80%)
- F1 Score: Harmonic mean of precision and recall (target: ≥0.85)
- False Positive Rate: % of normal clauses flagged (target: <10%)

**Calibration Quality**:
- Expected Calibration Error (ECE): Calibration accuracy (target: <0.05)
- Brier Score: Probabilistic accuracy (lower is better)
- Confidence Distribution: Should match actual accuracy

**User Experience**:
- Dismissal Rate: % of alerts dismissed (target: <20%)
- Helpful Rate: % of alerts rated helpful (target: >75%)
- Average Alerts per Document: (target: 3-7)
- Alert Fatigue Score: User engagement over time

**System Performance**:
- Stage 1 Time: Detection time (target: <5s)
- Stage 2 Time: Filtering time (target: <1s)
- Stage 3 Time: Clustering time (target: <2s)
- Total Pipeline Time: End-to-end (target: <30s)
- Memory Usage: Peak memory (target: <1GB)

### Monitoring Endpoints

**GET /api/v1/anomalies/performance**:
```json
{
    "total_documents_analyzed": 1250,
    "total_anomalies_detected": 8750,
    "total_feedback_collected": 3200,
    "false_positive_rate": 0.12,
    "dismissal_rate": 0.16,
    "average_alerts_per_document": 5.2,
    "expected_calibration_error": 0.04,
    "calibrator_fitted": true,
    "retrain_count": 32,
    "last_retrain_date": "2025-01-15T10:30:00Z",
    "avg_processing_time_ms": 4500,
    "pipeline_health_status": "healthy"
}
```

### Daily Monitoring

**Automated Daily Report**:
```bash
# Scheduled at 1 AM UTC
python scripts/daily_monitoring.py
```

**Report Contents**:
- Detection statistics (counts, rates)
- Calibration quality (ECE, Brier score)
- User feedback summary (dismissal rate, helpful rate)
- Performance metrics (processing times)
- Threshold violations (alerts)
- Recommendations (if any issues detected)

### Alerting Rules

**Critical Alerts** (immediate notification):
- ECE > 0.10 (poor calibration)
- Dismissal rate > 40% (very high false positives)
- Pipeline failure rate > 5%
- Processing time > 60s (2x target)

**Warning Alerts** (daily digest):
- ECE > 0.05 (calibration degrading)
- Dismissal rate > 25% (elevated false positives)
- Avg alerts per doc > 10 (alert fatigue risk)
- Processing time > 45s (1.5x target)

---

## Troubleshooting

### High False Positive Rate

**Symptoms**:
- Dismissal rate > 25%
- Low helpful rate < 60%
- Users complaining about irrelevant alerts

**Diagnosis**:
```python
# Analyze recent detections
python scripts/analyze_false_positives.py \
    --last-n-days 7 \
    --min-dismissal-rate 0.30
```

**Solutions**:
1. **Adjust Stage 2 Thresholds**:
   ```python
   # Increase filtering aggressiveness
   INDUSTRY_FILTER_STRENGTH = 1.5  # Default: 1.0
   ```

2. **Retrain Calibrator**:
   ```bash
   python scripts/retrain_calibrator.py --force
   ```

3. **Review Pattern Library**:
   - Identify overmatching patterns
   - Add negative examples
   - Refine regex precision

### Low Recall (Missing Anomalies)

**Symptoms**:
- Known problematic clauses not detected
- User reports missing issues
- Recall < 90% on test set

**Diagnosis**:
```python
# Run recall analysis
python scripts/analyze_recall.py \
    --test-set data/test_sets/labeled_anomalies.json
```

**Solutions**:
1. **Add Missing Patterns**:
   ```python
   # Add new pattern to library
   PATTERN_LIBRARY['new_category'] = [
       r'new_pattern_regex',
       r'another_pattern'
   ]
   ```

2. **Adjust Detection Weights**:
   ```python
   # Increase pattern weight
   DETECTION_WEIGHTS = {
       'pattern_based': 0.50,  # Increased from 0.40
       'semantic_similarity': 0.30,
       'statistical_outlier': 0.20
   }
   ```

3. **Update Baseline Corpus**:
   - Add more diverse examples
   - Include edge cases
   - Re-index Pinecone

### Slow Processing Times

**Symptoms**:
- Pipeline taking > 30 seconds
- Stage 3 (clustering) slow
- High memory usage

**Diagnosis**:
```bash
# Profile pipeline performance
python scripts/profile_pipeline.py \
    --document-id abc123 \
    --detailed
```

**Solutions**:
1. **Enable Caching**:
   ```python
   # Cache embeddings
   @lru_cache(maxsize=1000)
   def get_embedding(text):
       return model.encode(text)
   ```

2. **Batch Processing**:
   ```python
   # Process clauses in batches
   BATCH_SIZE = 32
   for i in range(0, len(clauses), BATCH_SIZE):
       batch = clauses[i:i+BATCH_SIZE]
       process_batch(batch)
   ```

3. **Reduce Model Complexity**:
   ```python
   # Use smaller BERT model
   model = SentenceTransformer('paraphrase-MiniLM-L3-v2')  # Faster, less accurate
   ```

### Poor Calibration (High ECE)

**Symptoms**:
- ECE > 0.05
- Confidence scores don't match accuracy
- Overconfident or underconfident predictions

**Diagnosis**:
```python
# Analyze calibration curve
python scripts/plot_calibration_curve.py \
    --feedback-data feedback.json \
    --output calibration_plot.png
```

**Solutions**:
1. **Collect More Feedback**:
   ```bash
   # Need 500+ samples for good calibration
   python scripts/check_feedback_count.py
   ```

2. **Try Different Calibration Method**:
   ```python
   # Switch to Platt scaling
   CALIBRATION_METHOD = 'platt'  # Instead of 'isotonic'
   ```

3. **Check Data Distribution**:
   ```python
   # Ensure balanced feedback
   python scripts/check_feedback_balance.py
   ```

### Alert Fatigue

**Symptoms**:
- Users ignoring alerts
- Dismissal rate increasing over time
- Low engagement with medium/low alerts

**Diagnosis**:
```python
# Analyze alert engagement trends
python scripts/analyze_engagement.py \
    --time-window 30 \
    --group-by-tier
```

**Solutions**:
1. **Reduce MAX_ALERTS**:
   ```python
   MAX_ALERTS = 7  # Down from 10
   TARGET_ALERTS = 4  # Down from 5
   ```

2. **Increase Severity Threshold**:
   ```python
   # Only show HIGH and CRITICAL in main view
   SHOW_MEDIUM_ALERTS_IN_EXPANDABLE = True
   ```

3. **Improve Ranking**:
   ```python
   # Increase bonus for user-relevant categories
   BONUS_USER_RELEVANT = 2.0  # New bonus
   ```

---

## Additional Resources

### Related Documentation
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Pre-deployment requirements
- [API.md](./API.md) - API endpoint documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview

### External References
- [Isotonic Regression](https://scikit-learn.org/stable/modules/isotonic.html) - scikit-learn documentation
- [Legal-BERT](https://huggingface.co/nlpaueb/legal-bert-base-uncased) - HuggingFace model
- [Pinecone](https://docs.pinecone.io/) - Vector database documentation
- [Expected Calibration Error](https://arxiv.org/abs/1706.04599) - Research paper

### Support
- GitHub Issues: https://github.com/Akhil-Lokesh/termsandconditions/issues
- Email: support@termsandconditions.ai
- Slack: #anomaly-detection

---

**Last Updated**: 2025-01-12
**Version**: 1.0.0
**Authors**: AI Engineering Team
