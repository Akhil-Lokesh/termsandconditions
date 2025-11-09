"""
Anomaly Clusterer for Stage 3 Processing.

Clusters and deduplicates anomalies to reduce noise and group related issues.
Uses semantic embeddings, UMAP dimensionality reduction, and HDBSCAN clustering.
"""

import logging
import time
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnomalyClusterer:
    """
    Clusters and deduplicates anomalies using semantic similarity.

    Uses advanced ML techniques:
    - SentenceTransformer (legal-BERT) for semantic embeddings
    - UMAP for dimensionality reduction
    - HDBSCAN for density-based clustering
    - Cosine similarity for duplicate detection
    """

    def __init__(
        self,
        model_name: str = 'nlpaueb/legal-bert-base-uncased',
        duplicate_threshold: float = 0.95,
        umap_n_neighbors: int = 15,
        umap_n_components: int = 5,
        hdbscan_min_cluster_size: int = 2,
        hdbscan_min_samples: int = 1,
        hdbscan_cluster_selection_epsilon: float = 0.5
    ):
        """
        Initialize the anomaly clusterer.

        Args:
            model_name: SentenceTransformer model for embeddings
            duplicate_threshold: Cosine similarity threshold for duplicates (0-1)
            umap_n_neighbors: UMAP n_neighbors parameter
            umap_n_components: UMAP n_components parameter
            hdbscan_min_cluster_size: Minimum cluster size for HDBSCAN
            hdbscan_min_samples: Minimum samples for HDBSCAN
            hdbscan_cluster_selection_epsilon: Cluster selection epsilon for HDBSCAN
        """
        self.model_name = model_name
        self.duplicate_threshold = duplicate_threshold
        self.umap_n_neighbors = umap_n_neighbors
        self.umap_n_components = umap_n_components
        self.hdbscan_min_cluster_size = hdbscan_min_cluster_size
        self.hdbscan_min_samples = hdbscan_min_samples
        self.hdbscan_cluster_selection_epsilon = hdbscan_cluster_selection_epsilon

        # Initialize models (lazy loading)
        self.sentence_transformer = None
        self.umap_reducer = None
        self.hdbscan_clusterer = None
        self.is_available = False

        # Try to import and initialize
        try:
            self._initialize_models()
        except Exception as e:
            logger.warning(f"Failed to initialize clustering models: {e}")
            logger.warning("Clustering will not be available")

    def _initialize_models(self):
        """Initialize ML models for clustering."""
        try:
            # Import SentenceTransformer
            from sentence_transformers import SentenceTransformer
            self.sentence_transformer = SentenceTransformer(self.model_name)
            logger.info(f"SentenceTransformer loaded: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            raise

        try:
            # Import UMAP
            import umap
            self.umap_reducer = umap.UMAP(
                n_neighbors=self.umap_n_neighbors,
                n_components=self.umap_n_components,
                metric='cosine',
                random_state=42
            )
            logger.info(
                f"UMAP initialized: n_neighbors={self.umap_n_neighbors}, "
                f"n_components={self.umap_n_components}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize UMAP: {e}")
            raise

        try:
            # Import HDBSCAN
            import hdbscan
            self.hdbscan_clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.hdbscan_min_cluster_size,
                min_samples=self.hdbscan_min_samples,
                cluster_selection_epsilon=self.hdbscan_cluster_selection_epsilon,
                metric='euclidean'
            )
            logger.info(
                f"HDBSCAN initialized: min_cluster_size={self.hdbscan_min_cluster_size}, "
                f"epsilon={self.hdbscan_cluster_selection_epsilon}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize HDBSCAN: {e}")
            raise

        self.is_available = True
        logger.info("Anomaly clusterer fully initialized and available")

    def cluster_anomalies(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Cluster and deduplicate anomalies.

        Main clustering pipeline:
        1. Generate embeddings for all anomaly texts
        2. Find exact/near duplicates (similarity >= 0.95)
        3. Consolidate duplicates, keep highest confidence representative
        4. Apply UMAP + HDBSCAN clustering on unique anomalies
        5. Create cluster summaries

        Args:
            anomalies: List of anomaly dictionaries from Stage 2

        Returns:
            Dict with clusters, noise, and statistics
        """
        logger.info(f"Starting clustering on {len(anomalies)} anomalies")
        clustering_start = time.time()

        # Edge case: Less than 2 anomalies
        if len(anomalies) < 2:
            logger.info("Less than 2 anomalies, returning as-is without clustering")
            return {
                'clusters': [{
                    'cluster_id': 'single',
                    'representative_anomaly': anomalies[0] if anomalies else None,
                    'member_anomalies': anomalies,
                    'section_references': [a.get('section', 'unknown') for a in anomalies],
                    'consolidated_text': anomalies[0].get('clause_text', '') if anomalies else '',
                    'cluster_size': len(anomalies)
                }] if anomalies else [],
                'noise': [],
                'reduction_ratio': 0.0,
                'original_count': len(anomalies),
                'final_count': len(anomalies),
                'timing_ms': {
                    'total': (time.time() - clustering_start) * 1000
                }
            }

        # Check if models are available
        if not self.is_available:
            logger.warning("Clustering models not available, returning anomalies as individual clusters")
            return self._fallback_clustering(anomalies)

        try:
            # STEP 1: Generate embeddings
            logger.info("Step 1: Generating embeddings")
            embedding_start = time.time()
            embeddings, anomalies_with_embeddings = self._generate_embeddings(anomalies)
            embedding_time = (time.time() - embedding_start) * 1000
            logger.info(f"Generated {len(embeddings)} embeddings in {embedding_time:.2f}ms")

            # STEP 2: Find duplicates
            logger.info("Step 2: Finding duplicates")
            duplicate_start = time.time()
            duplicate_groups = self._find_duplicates(embeddings, anomalies_with_embeddings)
            duplicate_time = (time.time() - duplicate_start) * 1000
            logger.info(
                f"Found {len(duplicate_groups)} duplicate groups in {duplicate_time:.2f}ms"
            )

            # STEP 3: Consolidate duplicates
            logger.info("Step 3: Consolidating duplicates")
            consolidate_start = time.time()
            unique_anomalies, consolidated_mapping = self._consolidate_duplicates(
                anomalies_with_embeddings,
                duplicate_groups
            )
            consolidate_time = (time.time() - consolidate_start) * 1000
            logger.info(
                f"Consolidated to {len(unique_anomalies)} unique anomalies in {consolidate_time:.2f}ms"
            )

            # Edge case: All anomalies are duplicates
            if len(unique_anomalies) < 2:
                logger.info("All anomalies are duplicates, returning single cluster")
                return self._create_single_cluster_result(
                    unique_anomalies,
                    consolidated_mapping,
                    len(anomalies),
                    {
                        'embedding': embedding_time,
                        'duplicate_detection': duplicate_time,
                        'consolidation': consolidate_time,
                        'total': (time.time() - clustering_start) * 1000
                    }
                )

            # STEP 4: Apply UMAP + HDBSCAN clustering
            logger.info("Step 4: Applying UMAP + HDBSCAN clustering")
            clustering_ml_start = time.time()

            # Extract embeddings from unique anomalies
            unique_embeddings = np.array([a['embedding'] for a in unique_anomalies])

            # UMAP dimensionality reduction
            logger.info(f"Running UMAP on {len(unique_embeddings)} embeddings")
            reduced_embeddings = self.umap_reducer.fit_transform(unique_embeddings)
            logger.info(f"UMAP reduced to {reduced_embeddings.shape[1]} dimensions")

            # HDBSCAN clustering
            logger.info("Running HDBSCAN clustering")
            cluster_labels = self.hdbscan_clusterer.fit_predict(reduced_embeddings)

            clustering_ml_time = (time.time() - clustering_ml_start) * 1000
            logger.info(f"Clustering complete in {clustering_ml_time:.2f}ms")

            # Count clusters
            unique_labels = set(cluster_labels)
            n_clusters = len([l for l in unique_labels if l != -1])
            n_noise = sum(1 for l in cluster_labels if l == -1)

            logger.info(
                f"Found {n_clusters} clusters and {n_noise} noise points"
            )

            # STEP 5: Group by cluster and create summaries
            logger.info("Step 5: Creating cluster summaries")
            summary_start = time.time()

            clusters, noise = self._group_by_cluster(
                unique_anomalies,
                cluster_labels,
                consolidated_mapping
            )

            summary_time = (time.time() - summary_start) * 1000
            logger.info(f"Created {len(clusters)} cluster summaries in {summary_time:.2f}ms")

            # Calculate reduction ratio
            original_count = len(anomalies)
            final_count = len(clusters) + len(noise)
            reduction_ratio = (original_count - final_count) / original_count if original_count > 0 else 0.0

            total_time = (time.time() - clustering_start) * 1000

            logger.info(
                f"Clustering complete: {original_count} -> {final_count} anomalies "
                f"({reduction_ratio:.1%} reduction) in {total_time:.2f}ms"
            )

            return {
                'clusters': clusters,
                'noise': noise,
                'reduction_ratio': reduction_ratio,
                'original_count': original_count,
                'final_count': final_count,
                'n_clusters': n_clusters,
                'n_noise': n_noise,
                'timing_ms': {
                    'embedding': embedding_time,
                    'duplicate_detection': duplicate_time,
                    'consolidation': consolidate_time,
                    'clustering': clustering_ml_time,
                    'summary': summary_time,
                    'total': total_time
                }
            }

        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
            return self._fallback_clustering(anomalies)

    def _generate_embeddings(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Generate embeddings for all anomalies.

        Args:
            anomalies: List of anomaly dicts

        Returns:
            Tuple of (embeddings array, anomalies with embeddings)
        """
        texts = [a.get('clause_text', '') for a in anomalies]

        # Generate embeddings
        embeddings = self.sentence_transformer.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        # Attach embeddings to anomalies
        anomalies_with_embeddings = []
        for i, anomaly in enumerate(anomalies):
            anomaly_copy = anomaly.copy()
            anomaly_copy['embedding'] = embeddings[i]
            anomalies_with_embeddings.append(anomaly_copy)

        return embeddings, anomalies_with_embeddings

    def _find_duplicates(
        self,
        embeddings: np.ndarray,
        anomalies: List[Dict[str, Any]]
    ) -> List[List[int]]:
        """
        Find duplicate anomalies based on cosine similarity.

        Args:
            embeddings: Embedding matrix
            anomalies: List of anomalies

        Returns:
            List of duplicate groups (each group is list of indices)
        """
        from sklearn.metrics.pairwise import cosine_similarity

        # Calculate pairwise cosine similarities
        similarities = cosine_similarity(embeddings)

        # Find duplicates
        n = len(anomalies)
        visited = set()
        duplicate_groups = []

        for i in range(n):
            if i in visited:
                continue

            # Find all anomalies similar to i
            similar_indices = []
            for j in range(i, n):
                if similarities[i, j] >= self.duplicate_threshold:
                    similar_indices.append(j)
                    visited.add(j)

            # Only create group if there are duplicates (more than 1)
            if len(similar_indices) > 1:
                duplicate_groups.append(similar_indices)
                logger.debug(
                    f"Duplicate group {len(duplicate_groups)}: {len(similar_indices)} anomalies "
                    f"(similarity >= {self.duplicate_threshold})"
                )

        return duplicate_groups

    def _consolidate_duplicates(
        self,
        anomalies: List[Dict[str, Any]],
        duplicate_groups: List[List[int]]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, int]]:
        """
        Consolidate duplicate anomalies, keeping highest confidence representative.

        Args:
            anomalies: List of anomalies
            duplicate_groups: List of duplicate groups

        Returns:
            Tuple of (unique_anomalies, consolidated_mapping)
            - unique_anomalies: List of unique anomalies (representatives)
            - consolidated_mapping: Dict mapping original index to representative index
        """
        # Track which anomalies are duplicates
        duplicate_indices = set()
        for group in duplicate_groups:
            duplicate_indices.update(group)

        # Create mapping from original index to representative index
        consolidated_mapping = {}

        # Process duplicate groups
        unique_anomalies = []
        unique_index = 0

        for group in duplicate_groups:
            # Select representative: highest stage2_confidence
            representatives = [(idx, anomalies[idx]) for idx in group]

            # Sort by stage2_confidence (descending)
            representatives.sort(
                key=lambda x: x[1].get('stage2_confidence', x[1].get('stage1_detection', {}).get('stage1_confidence', 0)),
                reverse=True
            )

            rep_idx, representative = representatives[0]

            # Create consolidated anomaly
            consolidated = representative.copy()
            consolidated['is_consolidated'] = True
            consolidated['original_indices'] = group
            consolidated['duplicate_count'] = len(group)
            consolidated['section_references'] = list(set(
                anomalies[idx].get('section', 'unknown') for idx in group
            ))

            # Map all group members to this representative
            for idx in group:
                consolidated_mapping[idx] = unique_index

            unique_anomalies.append(consolidated)
            unique_index += 1

        # Add non-duplicate anomalies
        for i, anomaly in enumerate(anomalies):
            if i not in duplicate_indices:
                consolidated_mapping[i] = unique_index
                unique_anomalies.append(anomaly)
                unique_index += 1

        logger.info(
            f"Consolidated {len(anomalies)} anomalies into {len(unique_anomalies)} unique anomalies "
            f"({len(duplicate_groups)} duplicate groups)"
        )

        return unique_anomalies, consolidated_mapping

    def _group_by_cluster(
        self,
        anomalies: List[Dict[str, Any]],
        labels: np.ndarray,
        consolidated_mapping: Dict[int, int]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Group anomalies by cluster labels.

        Args:
            anomalies: List of unique anomalies
            labels: Cluster labels from HDBSCAN
            consolidated_mapping: Mapping for consolidated duplicates

        Returns:
            Tuple of (clusters, noise)
        """
        # Group by label
        cluster_dict = defaultdict(list)
        for i, (anomaly, label) in enumerate(zip(anomalies, labels)):
            cluster_dict[int(label)].append(anomaly)

        # Separate clusters from noise
        clusters = []
        noise = cluster_dict.get(-1, [])

        # Process each cluster
        for label, members in cluster_dict.items():
            if label == -1:  # Skip noise
                continue

            cluster_summary = self._create_cluster_summary(label, members)
            clusters.append(cluster_summary)

        # Sort clusters by size (descending)
        clusters.sort(key=lambda x: x['cluster_size'], reverse=True)

        return clusters, noise

    def _create_cluster_summary(
        self,
        label: int,
        members: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create summary for a cluster.

        Args:
            label: Cluster label
            members: List of anomalies in cluster

        Returns:
            Cluster summary dict
        """
        # Select representative: highest stage2_confidence
        members_sorted = sorted(
            members,
            key=lambda x: x.get('stage2_confidence', x.get('stage1_detection', {}).get('stage1_confidence', 0)),
            reverse=True
        )
        representative = members_sorted[0]

        # Collect section references
        section_references = list(set(
            m.get('section', 'unknown') for m in members
        ))

        # Create consolidated text
        if len(members) == 1:
            consolidated_text = representative.get('clause_text', '')
        else:
            # For multiple members, use representative text + note
            consolidated_text = (
                f"{representative.get('clause_text', '')} "
                f"[+{len(members)-1} similar clause(s) in sections: {', '.join(section_references[1:])}]"
            )

        # Calculate average confidence
        avg_confidence = np.mean([
            m.get('stage2_confidence', m.get('stage1_detection', {}).get('stage1_confidence', 0))
            for m in members
        ])

        # Determine overall severity (take highest)
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        severities = [m.get('severity', 'medium') for m in members]
        overall_severity = max(severities, key=lambda s: severity_order.get(s, 0))

        return {
            'cluster_id': f'cluster_{label}',
            'representative_anomaly': representative,
            'member_anomalies': members,
            'section_references': section_references,
            'consolidated_text': consolidated_text,
            'cluster_size': len(members),
            'average_confidence': float(avg_confidence),
            'overall_severity': overall_severity,
            'risk_categories': list(set(m.get('risk_category', 'other') for m in members))
        }

    def _create_single_cluster_result(
        self,
        unique_anomalies: List[Dict[str, Any]],
        consolidated_mapping: Dict[int, int],
        original_count: int,
        timing: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Create result for single cluster (when all anomalies are duplicates).

        Args:
            unique_anomalies: List of unique anomalies (should be 1)
            consolidated_mapping: Mapping for duplicates
            original_count: Original anomaly count
            timing: Timing information

        Returns:
            Cluster result dict
        """
        if not unique_anomalies:
            return {
                'clusters': [],
                'noise': [],
                'reduction_ratio': 0.0,
                'original_count': original_count,
                'final_count': 0,
                'timing_ms': timing
            }

        representative = unique_anomalies[0]

        cluster = {
            'cluster_id': 'all_duplicates',
            'representative_anomaly': representative,
            'member_anomalies': unique_anomalies,
            'section_references': representative.get('section_references', [representative.get('section', 'unknown')]),
            'consolidated_text': representative.get('clause_text', ''),
            'cluster_size': len(unique_anomalies),
            'duplicate_count': representative.get('duplicate_count', 1)
        }

        reduction_ratio = (original_count - 1) / original_count if original_count > 0 else 0.0

        return {
            'clusters': [cluster],
            'noise': [],
            'reduction_ratio': reduction_ratio,
            'original_count': original_count,
            'final_count': 1,
            'timing_ms': timing
        }

    def _fallback_clustering(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback clustering when ML models are not available.

        Simply returns each anomaly as its own cluster.

        Args:
            anomalies: List of anomalies

        Returns:
            Cluster result with each anomaly as separate cluster
        """
        logger.info("Using fallback clustering (no ML models available)")

        clusters = []
        for i, anomaly in enumerate(anomalies):
            cluster = {
                'cluster_id': f'fallback_{i}',
                'representative_anomaly': anomaly,
                'member_anomalies': [anomaly],
                'section_references': [anomaly.get('section', 'unknown')],
                'consolidated_text': anomaly.get('clause_text', ''),
                'cluster_size': 1
            }
            clusters.append(cluster)

        return {
            'clusters': clusters,
            'noise': [],
            'reduction_ratio': 0.0,
            'original_count': len(anomalies),
            'final_count': len(anomalies),
            'fallback': True,
            'timing_ms': {'total': 0}
        }

    def get_cluster_statistics(self, clustering_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about clustering result.

        Args:
            clustering_result: Result from cluster_anomalies

        Returns:
            Statistics dict
        """
        clusters = clustering_result.get('clusters', [])
        noise = clustering_result.get('noise', [])

        cluster_sizes = [c['cluster_size'] for c in clusters]

        return {
            'n_clusters': len(clusters),
            'n_noise': len(noise),
            'total_anomalies': sum(cluster_sizes) + len(noise),
            'avg_cluster_size': np.mean(cluster_sizes) if cluster_sizes else 0,
            'max_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
            'min_cluster_size': min(cluster_sizes) if cluster_sizes else 0,
            'reduction_ratio': clustering_result.get('reduction_ratio', 0.0)
        }
