"""
Statistical Outlier Detector for T&C Clause Anomaly Detection.

Uses Isolation Forest to detect clauses with unusual statistical properties
compared to a baseline corpus. This is Stage 1 of the multi-stage anomaly
detection pipeline.

Features extracted:
1. Clause length (characters)
2. Sentence count
3. Average sentence length
4. Flesch-Kincaid readability score
5. Modal verb count (must, shall, may, can)
6. Negation count (not, no, never, neither)
7. Conditional count (if, unless, except, provided)
8. Risk keyword count
9. Legal jargon density
"""

import re
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StatisticalOutlierDetector:
    """
    Detects statistically unusual clauses using Isolation Forest.

    This detector identifies clauses that deviate from normal statistical
    patterns found in the baseline corpus. It uses 9 statistical features
    to characterize each clause and flags outliers.

    Attributes:
        model: IsolationForest model for outlier detection
        scaler: StandardScaler for feature normalization
        is_fitted: Whether the model has been trained
        feature_names: Names of the extracted features
    """

    # Modal verbs that indicate obligations or permissions
    MODAL_VERBS = [
        r'\bmust\b', r'\bshall\b', r'\bmay\b', r'\bcan\b',
        r'\bshould\b', r'\bwill\b', r'\bcould\b', r'\bwould\b',
        r'\bmight\b', r'\bought\b'
    ]

    # Negation words
    NEGATIONS = [
        r'\bnot\b', r'\bno\b', r'\bnever\b', r'\bneither\b',
        r'\bnor\b', r'\bnone\b', r'\bnobody\b', r'\bnothing\b',
        r'\bnowhere\b', r"\bcan't\b", r"\bwon't\b", r"\bdon't\b",
        r"\bdidn't\b", r"\bdoesn't\b", r"\bisn't\b", r"\baren't\b",
        r"\bwasn't\b", r"\bweren't\b", r"\bhadn't\b", r"\bhasn't\b",
        r"\bhaven't\b", r"\bshouldn't\b", r"\bwouldn't\b", r"\bcouldn't\b"
    ]

    # Conditional indicators
    CONDITIONALS = [
        r'\bif\b', r'\bunless\b', r'\bexcept\b', r'\bprovided\b',
        r'\bprovided that\b', r'\bin the event\b', r'\bshould\b',
        r'\bwhen\b', r'\bwhere\b', r'\bwherever\b', r'\bwhenever\b',
        r'\bin case\b', r'\bas long as\b', r'\bso long as\b'
    ]

    # Common legal jargon terms
    LEGAL_JARGON = [
        r'\bthereof\b', r'\btherein\b', r'\bthereby\b', r'\bwhereof\b',
        r'\bwherein\b', r'\bwhereby\b', r'\bheretofore\b', r'\bhereinafter\b',
        r'\bhereby\b', r'\bherein\b', r'\bhereto\b', r'\bhereof\b',
        r'\baforesaid\b', r'\bforthwith\b', r'\bnotwithstanding\b',
        r'\bpursuant to\b', r'\bin accordance with\b', r'\bsubject to\b',
        r'\bwith respect to\b', r'\bin respect of\b', r'\bin relation to\b',
        r'\bto the extent\b', r'\bto the effect that\b', r'\binsofar as\b',
        r'\binasmuch as\b', r'\bviz\b', r'\bi\.e\.\b', r'\be\.g\.\b',
        r'\bindemnify\b', r'\bindemnification\b', r'\bliability\b',
        r'\bliable\b', r'\bwaive\b', r'\bwaiver\b', r'\bgoverning law\b',
        r'\bjurisdiction\b', r'\barbitration\b', r'\bforce majeure\b',
        r'\bterminate\b', r'\btermination\b', r'\bbreach\b',
        r'\brepresentation\b', r'\bwarranty\b', r'\bwarranties\b'
    ]

    # Risk-related keywords (from risk_indicators.py)
    RISK_KEYWORDS = [
        r'\bterminate\b', r'\bsuspend\b', r'\bcancel\b', r'\bdelete\b',
        r'\bremove\b', r'\bliability\b', r'\bliable\b', r'\bindemnify\b',
        r'\bwaive\b', r'\bforfeit\b', r'\bno refund\b', r'\bnon-refundable\b',
        r'\bchange.*price\b', r'\bincrease.*fee\b', r'\bauto.*renew\b',
        r'\bautomatically\b', r'\bshare.*data\b', r'\bsell.*information\b',
        r'\bthird.*part\b', r'\bmonitor\b', r'\btrack\b', r'\bcollect\b',
        r'\bdiscretion\b', r'\bat any time\b', r'\bwithout notice\b',
        r'\bwithout.*cause\b', r'\bfor any reason\b', r'\bas-is\b',
        r'\bno warranty\b', r'\bdisclaim\b', r'\bat.*risk\b'
    ]

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize the Statistical Outlier Detector.

        Args:
            contamination: Expected proportion of outliers (0.0 to 0.5)
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state

        # Initialize models
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples='auto',
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1,  # Use all CPU cores
            verbose=0
        )

        self.scaler = StandardScaler()
        self.is_fitted = False

        # Feature names for debugging and interpretation
        self.feature_names = [
            'clause_length',
            'sentence_count',
            'avg_sentence_length',
            'flesch_kincaid_score',
            'modal_verb_count',
            'negation_count',
            'conditional_count',
            'risk_keyword_count',
            'legal_jargon_density'
        ]

        logger.info(f"Initialized StatisticalOutlierDetector with contamination={contamination}")

    def extract_statistical_features(self, clause: Dict[str, Any]) -> np.ndarray:
        """
        Extract 9 statistical features from a clause.

        Args:
            clause: Dictionary containing clause data with 'text' or 'clause_text' key

        Returns:
            NumPy array of shape (9,) containing the features

        Raises:
            ValueError: If clause text is empty or missing
        """
        # Extract text from clause dict (handle different key names)
        text = clause.get('text') or clause.get('clause_text') or clause.get('content', '')

        if not text or not isinstance(text, str):
            raise ValueError("Clause must contain non-empty 'text', 'clause_text', or 'content' field")

        text = text.strip()

        if len(text) < 10:
            raise ValueError(f"Clause text too short (< 10 characters): {len(text)}")

        try:
            # 1. Clause length (characters)
            clause_length = len(text)

            # 2. Sentence count
            sentence_count = self._count_sentences(text)

            # 3. Average sentence length
            avg_sentence_length = clause_length / max(sentence_count, 1)

            # 4. Flesch-Kincaid readability score
            fk_score = self._flesch_kincaid_score(text)

            # 5. Modal verb count
            modal_verb_count = self._count_patterns(text, self.MODAL_VERBS)

            # 6. Negation count
            negation_count = self._count_patterns(text, self.NEGATIONS)

            # 7. Conditional count
            conditional_count = self._count_patterns(text, self.CONDITIONALS)

            # 8. Risk keyword count
            risk_keyword_count = self._count_risk_keywords(text)

            # 9. Legal jargon density
            legal_jargon_density = self._legal_jargon_density(text)

            features = np.array([
                clause_length,
                sentence_count,
                avg_sentence_length,
                fk_score,
                modal_verb_count,
                negation_count,
                conditional_count,
                risk_keyword_count,
                legal_jargon_density
            ], dtype=np.float64)

            # Validate features (check for NaN or inf)
            if not np.all(np.isfinite(features)):
                logger.warning(f"Non-finite features detected: {features}")
                # Replace NaN/inf with 0
                features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

            return features

        except Exception as e:
            logger.error(f"Error extracting features from clause: {e}")
            logger.error(f"Clause text preview: {text[:100]}...")
            # Return zero features as fallback
            return np.zeros(9, dtype=np.float64)

    def fit(self, clauses: List[Dict[str, Any]]) -> None:
        """
        Fit the Isolation Forest model on baseline corpus clauses.

        Args:
            clauses: List of clause dictionaries from baseline corpus

        Raises:
            ValueError: If clauses list is empty or contains invalid data
        """
        if not clauses or len(clauses) == 0:
            raise ValueError("Cannot fit model on empty clause list")

        logger.info(f"Fitting StatisticalOutlierDetector on {len(clauses)} baseline clauses")

        # Extract features from all clauses
        features_list = []
        valid_count = 0

        for idx, clause in enumerate(clauses):
            try:
                features = self.extract_statistical_features(clause)
                features_list.append(features)
                valid_count += 1
            except ValueError as e:
                logger.debug(f"Skipping clause {idx}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing clause {idx}: {e}")
                continue

        if valid_count == 0:
            raise ValueError("No valid clauses found for training")

        logger.info(f"Successfully extracted features from {valid_count}/{len(clauses)} clauses")

        # Convert to numpy array
        X = np.array(features_list)

        # Log feature statistics
        logger.info(f"Feature matrix shape: {X.shape}")
        for i, feature_name in enumerate(self.feature_names):
            mean_val = np.mean(X[:, i])
            std_val = np.std(X[:, i])
            min_val = np.min(X[:, i])
            max_val = np.max(X[:, i])
            logger.debug(
                f"  {feature_name}: mean={mean_val:.2f}, std={std_val:.2f}, "
                f"min={min_val:.2f}, max={max_val:.2f}"
            )

        # Fit scaler
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        # Fit Isolation Forest
        self.model.fit(X_scaled)

        self.is_fitted = True
        logger.info("StatisticalOutlierDetector fitted successfully")

    def predict(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict whether a clause is a statistical outlier.

        Args:
            clause: Clause dictionary to analyze

        Returns:
            Dictionary containing:
                - is_outlier (bool): True if clause is an outlier
                - anomaly_score (float): Anomaly score from Isolation Forest (-1 to 1)
                - confidence (float): Confidence of prediction (0 to 1)
                - features (dict): Extracted feature values for debugging
                - stage (int): Detection stage (1 for statistical)

        Raises:
            RuntimeError: If model has not been fitted yet
            ValueError: If clause is invalid
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction. Call fit() first.")

        try:
            # Extract features
            features = self.extract_statistical_features(clause)

            # Scale features
            X = features.reshape(1, -1)
            X_scaled = self.scaler.transform(X)

            # Predict outlier (-1 = outlier, 1 = inlier)
            prediction = self.model.predict(X_scaled)[0]
            is_outlier = (prediction == -1)

            # Get anomaly score (more negative = more anomalous)
            # Score is in range approximately [-0.5, 0.5] but can vary
            anomaly_score = self.model.score_samples(X_scaled)[0]

            # Convert anomaly score to confidence (0 to 1)
            # More negative score = higher confidence of being an outlier
            # We normalize using typical score range: [-0.5, 0.5]
            if is_outlier:
                # For outliers, confidence increases with more negative score
                confidence = min(1.0, max(0.0, (-anomaly_score - 0.1) / 0.4))
            else:
                # For inliers, confidence increases with more positive score
                confidence = min(1.0, max(0.0, (anomaly_score + 0.1) / 0.4))

            # Ensure confidence is at least 0.5 for detected outliers
            if is_outlier and confidence < 0.5:
                confidence = 0.5

            # Create feature dict for debugging
            feature_dict = {
                name: float(value)
                for name, value in zip(self.feature_names, features)
            }

            result = {
                'is_outlier': bool(is_outlier),
                'anomaly_score': float(anomaly_score),
                'confidence': float(confidence),
                'features': feature_dict,
                'stage': 1,  # Stage 1: Statistical outlier detection
                'detector': 'statistical_outlier'
            }

            if is_outlier:
                logger.debug(
                    f"Outlier detected: score={anomaly_score:.3f}, "
                    f"confidence={confidence:.2f}"
                )

            return result

        except ValueError as e:
            logger.error(f"Invalid clause for prediction: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            # Return safe default
            return {
                'is_outlier': False,
                'anomaly_score': 0.0,
                'confidence': 0.0,
                'features': {},
                'stage': 1,
                'detector': 'statistical_outlier',
                'error': str(e)
            }

    def _count_sentences(self, text: str) -> int:
        """
        Count the number of sentences in text.

        Args:
            text: Input text

        Returns:
            Number of sentences (minimum 1)
        """
        # Split on sentence-ending punctuation followed by space or end
        sentences = re.split(r'[.!?]+\s+|\n+', text.strip())
        # Filter out empty strings
        sentences = [s for s in sentences if s.strip()]
        return max(len(sentences), 1)

    def _count_syllables(self, word: str) -> int:
        """
        Estimate syllable count in a word (simplified algorithm).

        Args:
            word: Input word

        Returns:
            Estimated syllable count
        """
        word = word.lower().strip()
        if len(word) <= 3:
            return 1

        # Count vowel groups
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e'
        if word.endswith('e'):
            syllable_count -= 1

        # Ensure at least 1 syllable
        return max(syllable_count, 1)

    def _flesch_kincaid_score(self, text: str) -> float:
        """
        Calculate Flesch-Kincaid readability score.

        Higher scores indicate easier readability.
        Typical scores: 0-30 (very difficult), 60-70 (standard), 90-100 (very easy)

        Formula: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)

        Args:
            text: Input text

        Returns:
            Flesch-Kincaid readability score (typically 0-100)
        """
        try:
            # Count sentences
            sentence_count = self._count_sentences(text)

            # Count words
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            word_count = len(words)

            if word_count == 0:
                return 0.0

            # Count syllables
            syllable_count = sum(self._count_syllables(word) for word in words)

            # Calculate Flesch-Kincaid score
            score = (
                206.835
                - 1.015 * (word_count / sentence_count)
                - 84.6 * (syllable_count / word_count)
            )

            # Clamp to reasonable range
            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.debug(f"Error calculating Flesch-Kincaid score: {e}")
            return 50.0  # Default to medium difficulty

    def _count_patterns(self, text: str, patterns: List[str]) -> int:
        """
        Count occurrences of regex patterns in text.

        Args:
            text: Input text
            pattern_list: List of regex patterns

        Returns:
            Total count of pattern matches
        """
        text_lower = text.lower()
        count = 0

        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            count += len(matches)

        return count

    def _count_risk_keywords(self, text: str) -> int:
        """
        Count occurrences of risk-related keywords.

        Args:
            text: Input text

        Returns:
            Count of risk keywords
        """
        return self._count_patterns(text, self.RISK_KEYWORDS)

    def _legal_jargon_density(self, text: str) -> float:
        """
        Calculate density of legal jargon in text.

        Args:
            text: Input text

        Returns:
            Legal jargon density (jargon terms per 100 words)
        """
        # Count words
        words = re.findall(r'\b[a-zA-Z]+\b', text)
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Count legal jargon
        jargon_count = self._count_patterns(text, self.LEGAL_JARGON)

        # Calculate density (per 100 words)
        density = (jargon_count / word_count) * 100.0

        return density

    def save_model(self, filepath: str) -> None:
        """
        Save the fitted model to disk.

        Args:
            filepath: Path to save the model

        Raises:
            RuntimeError: If model has not been fitted yet
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted model")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'contamination': self.contamination,
            'random_state': self.random_state,
            'feature_names': self.feature_names
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """
        Load a fitted model from disk.

        Args:
            filepath: Path to load the model from
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.contamination = model_data['contamination']
        self.random_state = model_data['random_state']
        self.feature_names = model_data['feature_names']
        self.is_fitted = True

        logger.info(f"Model loaded from {filepath}")

    def get_feature_importance(self, clause: Dict[str, Any]) -> Dict[str, float]:
        """
        Get relative importance of features for a given clause.

        This helps explain why a clause was flagged as an outlier.

        Args:
            clause: Clause to analyze

        Returns:
            Dictionary mapping feature names to deviation scores
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting feature importance")

        try:
            features = self.extract_statistical_features(clause)
            X_scaled = self.scaler.transform(features.reshape(1, -1))[0]

            # Calculate deviation from mean (in standard deviations)
            feature_importance = {}
            for i, name in enumerate(self.feature_names):
                # Scaled features have mean 0, std 1
                deviation = abs(X_scaled[i])
                feature_importance[name] = float(deviation)

            return feature_importance

        except Exception as e:
            logger.error(f"Error calculating feature importance: {e}")
            return {}
