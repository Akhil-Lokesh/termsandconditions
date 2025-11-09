"""
Advanced Semantic Anomaly Detector for T&C Clauses.

Uses SentenceTransformer (legal-BERT) to detect clauses semantically similar
to known problematic patterns. This is Stage 2 of the multi-stage anomaly
detection pipeline.

The detector pre-computes embeddings for 12+ known problematic clause examples
and uses cosine similarity to identify similar clauses in user documents.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import pickle
import os

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SemanticAnomalyDetector:
    """
    Detects semantically anomalous clauses using legal-BERT embeddings.

    This detector identifies clauses that are semantically similar to known
    problematic patterns by comparing embeddings in vector space.

    Attributes:
        model: SentenceTransformer model for encoding text
        problematic_patterns: List of problematic clause examples
        pattern_embeddings: Pre-computed embeddings for problematic patterns
        similarity_threshold: Minimum cosine similarity to flag as anomalous
        is_available: Whether the model loaded successfully
    """

    # Known problematic clause patterns (12+ examples across 5 categories)
    PROBLEMATIC_PATTERNS = [
        # Data Selling (3 examples)
        {
            'category': 'data_selling',
            'severity': 'high',
            'text': 'We may sell, transfer, or share your personal information with third parties '
                    'for commercial purposes including marketing and advertising.',
            'description': 'Selling personal data to third parties'
        },
        {
            'category': 'data_selling',
            'severity': 'high',
            'text': 'Your data may be shared with advertisers, data brokers, and marketing partners '
                    'who may use it for their own business purposes.',
            'description': 'Sharing data with multiple commercial entities'
        },
        {
            'category': 'data_selling',
            'severity': 'high',
            'text': 'We reserve the right to monetize user data by providing it to partners, '
                    'affiliates, and other third parties for any lawful business purpose.',
            'description': 'Monetizing user data without restrictions'
        },

        # Rights Waivers (3 examples)
        {
            'category': 'rights_waiver',
            'severity': 'high',
            'text': 'You hereby waive all rights to pursue legal action against the company, '
                    'including but not limited to the right to sue, seek damages, or join class actions.',
            'description': 'Complete waiver of legal rights'
        },
        {
            'category': 'rights_waiver',
            'severity': 'high',
            'text': 'By accepting these terms, you give up your right to a jury trial and agree '
                    'that all disputes must be resolved through binding arbitration.',
            'description': 'Waiving jury trial rights'
        },
        {
            'category': 'rights_waiver',
            'severity': 'high',
            'text': 'You irrevocably waive any claims, rights, or remedies you may have against us, '
                    'whether known or unknown, arising from your use of the service.',
            'description': 'Irrevocable waiver of all claims'
        },

        # Auto-Renewal Traps (2 examples)
        {
            'category': 'auto_renewal',
            'severity': 'medium',
            'text': 'Your subscription will automatically renew at the end of each billing period. '
                    'You will be charged automatically unless you cancel at least 48 hours before renewal.',
            'description': 'Automatic renewal with short cancellation window'
        },
        {
            'category': 'auto_renewal',
            'severity': 'medium',
            'text': 'We will automatically charge your payment method for renewal. '
                    'The price may increase without notice, and cancellation must occur before the renewal date.',
            'description': 'Auto-renewal with potential price increases'
        },

        # Unilateral Changes (2 examples)
        {
            'category': 'unilateral_changes',
            'severity': 'medium',
            'text': 'We reserve the right to modify, suspend, or discontinue the service at any time '
                    'without notice or liability to you.',
            'description': 'Service changes without notice or liability'
        },
        {
            'category': 'unilateral_changes',
            'severity': 'high',
            'text': 'These terms may be changed at our sole discretion without prior notification. '
                    'Continued use after changes constitutes acceptance of new terms.',
            'description': 'Terms changes without notification requirement'
        },

        # Hidden Fees (2 examples)
        {
            'category': 'hidden_fees',
            'severity': 'medium',
            'text': 'Additional fees, charges, and surcharges may apply to your account. '
                    'These fees can be added at any time and will be charged automatically.',
            'description': 'Undisclosed additional fees'
        },
        {
            'category': 'hidden_fees',
            'severity': 'medium',
            'text': 'Transaction fees, processing fees, and service charges may be applied. '
                    'Fee amounts are determined at our discretion and subject to change.',
            'description': 'Variable fees at company discretion'
        },

        # Bonus: Liability Limitations (2 examples)
        {
            'category': 'liability_limitation',
            'severity': 'high',
            'text': 'We are not liable for any damages whatsoever, including data loss, service interruption, '
                    'or financial loss, regardless of the cause or our negligence.',
            'description': 'Complete liability exemption'
        },
        {
            'category': 'liability_limitation',
            'severity': 'medium',
            'text': 'The company disclaims all warranties and accepts no responsibility for errors, '
                    'omissions, or any damages arising from use of the service.',
            'description': 'Broad warranty disclaimer'
        },

        # Bonus: Data Retention (1 example)
        {
            'category': 'data_retention',
            'severity': 'medium',
            'text': 'We may retain your data indefinitely even after account deletion. '
                    'Retained data may be used for internal purposes or shared with third parties.',
            'description': 'Indefinite data retention after deletion'
        },
    ]

    def __init__(
        self,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
        similarity_threshold: float = 0.75,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the Semantic Anomaly Detector.

        Args:
            model_name: Name of the sentence transformer model to use
                       Default is a lightweight model; use 'nlpaueb/legal-bert-base-uncased' for legal domain
            similarity_threshold: Minimum cosine similarity to flag as anomalous (0.0 to 1.0)
            cache_dir: Directory to cache model and embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '.cache')
        self.is_available = False
        self.model = None
        self.pattern_embeddings = None
        self.problematic_patterns = self.PROBLEMATIC_PATTERNS

        # Try to initialize the model
        self._initialize_model()

    def _initialize_model(self) -> None:
        """
        Initialize the SentenceTransformer model and pre-compute embeddings.

        Falls back gracefully if sentence-transformers is not available.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning(
                "sentence-transformers not available. "
                "Semantic anomaly detection will be disabled. "
                "Install with: pip install sentence-transformers"
            )
            self.is_available = False
            return

        try:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")

            # Load the model
            self.model = SentenceTransformer(self.model_name)

            # Pre-compute embeddings for problematic patterns
            logger.info(f"Pre-computing embeddings for {len(self.problematic_patterns)} problematic patterns")
            self.pattern_embeddings = self._load_problematic_clauses()

            self.is_available = True
            logger.info(f"SemanticAnomalyDetector initialized successfully with {len(self.problematic_patterns)} patterns")

        except Exception as e:
            logger.error(f"Failed to initialize SemanticAnomalyDetector: {e}", exc_info=True)
            logger.warning("Semantic anomaly detection will be disabled")
            self.is_available = False

    def _load_problematic_clauses(self) -> np.ndarray:
        """
        Load and compute embeddings for problematic clause patterns.

        Returns:
            NumPy array of embeddings, shape (num_patterns, embedding_dim)
        """
        if not self.is_available or self.model is None:
            return np.array([])

        # Check cache first
        cache_file = os.path.join(
            self.cache_dir,
            f"pattern_embeddings_{self.model_name.replace('/', '_')}.pkl"
        )

        if os.path.exists(cache_file):
            try:
                logger.info(f"Loading cached embeddings from {cache_file}")
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if len(cached_data) == len(self.problematic_patterns):
                        return cached_data
                    else:
                        logger.warning("Cached embeddings count mismatch, re-computing")
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}")

        # Compute embeddings
        try:
            texts = [pattern['text'] for pattern in self.problematic_patterns]
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True  # Normalize for cosine similarity
            )

            # Cache the embeddings
            os.makedirs(self.cache_dir, exist_ok=True)
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(embeddings, f)
                logger.info(f"Cached embeddings to {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to cache embeddings: {e}")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to compute embeddings: {e}", exc_info=True)
            return np.array([])

    def detect_semantic_anomalies(self, clause_text: str) -> Dict[str, Any]:
        """
        Detect if a clause is semantically similar to known problematic patterns.

        Args:
            clause_text: The clause text to analyze

        Returns:
            Dictionary containing:
                - is_anomalous (bool): True if clause matches a problematic pattern
                - similarity_score (float): Highest cosine similarity score (0 to 1)
                - matched_pattern (str): Description of the matched pattern
                - matched_category (str): Category of the matched pattern
                - confidence (float): Confidence of the detection (0 to 1)
                - severity (str): Severity level (high, medium, low)
                - stage (int): Detection stage (2 for semantic)
                - detector (str): Name of this detector
                - all_matches (list): All patterns above threshold with scores
        """
        # Default response if model not available
        if not self.is_available or self.model is None or self.pattern_embeddings is None:
            return {
                'is_anomalous': False,
                'similarity_score': 0.0,
                'matched_pattern': None,
                'matched_category': None,
                'confidence': 0.0,
                'severity': 'unknown',
                'stage': 2,
                'detector': 'semantic_anomaly',
                'available': False,
                'all_matches': []
            }

        if not clause_text or len(clause_text.strip()) < 10:
            return {
                'is_anomalous': False,
                'similarity_score': 0.0,
                'matched_pattern': None,
                'matched_category': None,
                'confidence': 0.0,
                'severity': 'unknown',
                'stage': 2,
                'detector': 'semantic_anomaly',
                'error': 'Clause text too short',
                'all_matches': []
            }

        try:
            # Encode the clause
            clause_embedding = self.model.encode(
                clause_text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True
            )

            # Calculate cosine similarities with all patterns
            similarities = util.cos_sim(clause_embedding, self.pattern_embeddings)[0].numpy()

            # Find the best match
            max_similarity_idx = int(np.argmax(similarities))
            max_similarity = float(similarities[max_similarity_idx])

            # Get all matches above threshold
            all_matches = []
            for idx, sim in enumerate(similarities):
                if sim >= self.similarity_threshold:
                    pattern = self.problematic_patterns[idx]
                    all_matches.append({
                        'category': pattern['category'],
                        'description': pattern['description'],
                        'severity': pattern['severity'],
                        'similarity': float(sim)
                    })

            # Sort by similarity (highest first)
            all_matches.sort(key=lambda x: x['similarity'], reverse=True)

            # Determine if anomalous
            is_anomalous = max_similarity >= self.similarity_threshold

            # Get matched pattern info
            matched_pattern_info = self.problematic_patterns[max_similarity_idx]

            # Calculate confidence (scale similarity to confidence)
            # Similarity of 0.75 = 50% confidence, 1.0 = 100% confidence
            if is_anomalous:
                confidence = min(1.0, (max_similarity - self.similarity_threshold) / (1.0 - self.similarity_threshold))
                confidence = 0.5 + (confidence * 0.5)  # Scale to [0.5, 1.0] range
            else:
                confidence = max_similarity / self.similarity_threshold  # Scale to [0, 1.0] range
                confidence = confidence * 0.5  # Scale to [0, 0.5] range

            result = {
                'is_anomalous': is_anomalous,
                'similarity_score': max_similarity,
                'matched_pattern': matched_pattern_info['description'] if is_anomalous else None,
                'matched_category': matched_pattern_info['category'] if is_anomalous else None,
                'confidence': confidence,
                'severity': matched_pattern_info['severity'] if is_anomalous else 'low',
                'stage': 2,
                'detector': 'semantic_anomaly',
                'available': True,
                'all_matches': all_matches if is_anomalous else []
            }

            # Log detection
            if is_anomalous:
                logger.info(
                    f"Semantic anomaly detected: {matched_pattern_info['category']} "
                    f"(similarity={max_similarity:.3f}, confidence={confidence:.2f})"
                )
                logger.debug(f"Clause preview: {clause_text[:100]}...")
            else:
                logger.debug(
                    f"No semantic anomaly: max_similarity={max_similarity:.3f} "
                    f"< threshold={self.similarity_threshold}"
                )

            return result

        except Exception as e:
            logger.error(f"Error during semantic anomaly detection: {e}", exc_info=True)
            return {
                'is_anomalous': False,
                'similarity_score': 0.0,
                'matched_pattern': None,
                'matched_category': None,
                'confidence': 0.0,
                'severity': 'unknown',
                'stage': 2,
                'detector': 'semantic_anomaly',
                'error': str(e),
                'all_matches': []
            }

    def get_pattern_details(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get details about the problematic patterns used for detection.

        Args:
            category: Optional category filter

        Returns:
            List of pattern dictionaries
        """
        if category:
            return [p for p in self.problematic_patterns if p['category'] == category]
        return self.problematic_patterns

    def get_categories(self) -> List[str]:
        """
        Get all unique pattern categories.

        Returns:
            List of category names
        """
        return list(set(p['category'] for p in self.problematic_patterns))

    def analyze_multiple_clauses(self, clauses: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple clauses in batch for efficiency.

        Args:
            clauses: List of clause texts

        Returns:
            List of detection results (same format as detect_semantic_anomalies)
        """
        results = []
        for clause_text in clauses:
            result = self.detect_semantic_anomalies(clause_text)
            results.append(result)
        return results

    def update_threshold(self, new_threshold: float) -> None:
        """
        Update the similarity threshold for detection.

        Args:
            new_threshold: New threshold value (0.0 to 1.0)

        Raises:
            ValueError: If threshold is not in valid range
        """
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {new_threshold}")

        old_threshold = self.similarity_threshold
        self.similarity_threshold = new_threshold
        logger.info(f"Updated similarity threshold from {old_threshold:.2f} to {new_threshold:.2f}")

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get the embedding vector for a given text.

        Useful for debugging and analysis.

        Args:
            text: Input text

        Returns:
            NumPy array of embedding or None if model not available
        """
        if not self.is_available or self.model is None:
            return None

        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def compare_clauses(self, clause1: str, clause2: str) -> float:
        """
        Compare semantic similarity between two clauses.

        Args:
            clause1: First clause text
            clause2: Second clause text

        Returns:
            Cosine similarity score (0.0 to 1.0) or 0.0 if model not available
        """
        if not self.is_available or self.model is None:
            return 0.0

        try:
            embeddings = self.model.encode(
                [clause1, clause2],
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            similarity = util.cos_sim(embeddings[0], embeddings[1])[0][0].item()
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to compare clauses: {e}")
            return 0.0

    def save_cache(self, filepath: str) -> None:
        """
        Save the pattern embeddings cache to disk.

        Args:
            filepath: Path to save the cache file
        """
        if self.pattern_embeddings is None:
            raise RuntimeError("No embeddings to save")

        with open(filepath, 'wb') as f:
            pickle.dump({
                'embeddings': self.pattern_embeddings,
                'patterns': self.problematic_patterns,
                'model_name': self.model_name,
                'threshold': self.similarity_threshold
            }, f)

        logger.info(f"Saved embeddings cache to {filepath}")

    def load_cache(self, filepath: str) -> None:
        """
        Load pattern embeddings cache from disk.

        Args:
            filepath: Path to load the cache file from
        """
        with open(filepath, 'rb') as f:
            cache_data = pickle.load(f)

        self.pattern_embeddings = cache_data['embeddings']
        self.problematic_patterns = cache_data['patterns']
        self.similarity_threshold = cache_data.get('threshold', self.similarity_threshold)

        logger.info(f"Loaded embeddings cache from {filepath}")
