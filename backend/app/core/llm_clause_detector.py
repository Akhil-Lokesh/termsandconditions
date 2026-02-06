"""
LLM-based clause detector for Terms & Conditions analysis.

Sends all clauses to Claude in 1-2 batch API calls to identify risky clauses.
This replaces per-clause keyword matching as the primary detection method,
with keyword patterns serving as a supplementary fallback.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

# Approximate tokens per word for estimation
TOKENS_PER_WORD = 1.3
# Conservative input limit per call (leave room for prompt + output)
MAX_INPUT_TOKENS = 80000


DETECTION_PROMPT = """You are a CONSUMER PROTECTION ADVOCATE analyzing a {service_type} Terms & Conditions document from {company_name}.

Your job is to identify EVERY clause that could surprise, disadvantage, or harm the average consumer. Be thorough — it is far better to flag a clause that turns out to be standard than to miss a genuinely harmful one.

SEVERITY LEVELS — Use the FULL range. Most flagged clauses should be "medium" or "low". Reserve "high" and "critical" for truly exceptional cases.

- "critical": RARE. Waives fundamental legal rights, potentially illegal provisions, extreme consumer harm with no recourse. Examples: waiving right to sue entirely, selling personal data to third parties without consent, collecting biometrics without notice. Expect 0-2 per document.
- "high": Severely unfair terms that most consumers would NOT expect and that cause real harm. Examples: perpetual irrevocable content license covering name/image/voice/likeness, forced arbitration WITH class action waiver, waiver of moral rights, shortened statute of limitations (less than standard), one-sided termination with no notice. Expect 2-5 per document.
- "medium": Concerning but COMMON in the industry — worth flagging but consumers encounter these regularly. Examples: unilateral right to modify terms, broad warranty disclaimers, auto-renewal, revenue exclusion (company profits from your content), unilateral service changes, automated content analysis/scanning, account termination at sole discretion, broad indemnification, liability caps. Expect 5-10 per document.
- "low": Standard legal provisions that are worth noting but cause minimal practical harm. Examples: governing law/venue selection, standard liability limitations, identity disclosure to IP claimants, feedback/ideas license, content declared non-confidential, standard data retention. Expect 3-8 per document.

CALIBRATION RULE: If a practice appears in >50% of major tech/social media ToS (e.g., broad content license, warranty disclaimers, unilateral modification, limitation of liability, indemnification), it should be "medium" at most — unless the specific wording goes SIGNIFICANTLY beyond industry norms.

RISK CATEGORIES (use exactly one):
liability, payment, privacy, arbitration, modification, termination, content, data, rights, surveillance, other

IMPORTANT CATEGORIES TO WATCH FOR (often missed by automated systems):
- Moral rights waivers ("waive any and all moral rights")
- User-to-user content licenses ("authorize other users to use, modify, reproduce")
- Name/image/voice/likeness licenses
- Privacy and publicity rights waivers
- Shortened statutes of limitations (less than standard period)
- Revenue exclusion (company profits from your content, you get nothing)
- Automated content analysis (scanning your content including emails)
- Account termination at sole discretion without clear cause
- Cross-platform data sharing/syncing
- Post-termination data retention
- Feedback/ideas perpetual license
- Content declared non-confidential

Here are ALL {num_clauses} clauses from the document. Analyze each one:

{clauses_text}

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "risky_clauses": [
    {{
      "clause_number": "exact clause number from input",
      "severity": "critical|high|medium|low",
      "risk_category": "one of the categories above",
      "explanation": "2-3 sentences explaining the consumer risk in plain language",
      "consumer_impact": "One practical sentence about real-world impact on the user",
      "recommendation": "What should the consumer do about this"
    }}
  ]
}}"""


class LLMClauseDetector:
    """Detects risky clauses using Claude batch analysis."""

    def __init__(self, claude_service: ClaudeService):
        self.claude = claude_service

    async def detect_risky_clauses(
        self,
        clauses: List[Dict[str, Any]],
        company_name: str = "Unknown",
        service_type: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        Send all clauses to Claude in 1-2 batch calls to identify risky ones.

        Args:
            clauses: List of dicts with 'text', 'section', 'clause_number'
            company_name: Company name for context
            service_type: Type of service (general, social_media, etc.)

        Returns:
            List of risky clause dicts with severity, explanation, etc.
        """
        if not clauses:
            return []

        logger.info(f"LLM clause detection: analyzing {len(clauses)} clauses for {company_name}")

        try:
            # Split into batches if needed
            batches = self._split_into_batches(clauses)
            logger.info(f"Split into {len(batches)} batch(es)")

            all_findings = []

            if len(batches) == 1:
                try:
                    findings = await self._analyze_batch(batches[0], company_name, service_type)
                    all_findings.extend(findings)
                except Exception as e:
                    logger.error(f"Single batch analysis failed: {e}", exc_info=True)
                    # Graceful degradation — keyword detection still runs
            else:
                # Run batches in parallel
                tasks = [
                    self._analyze_batch(batch, company_name, service_type)
                    for batch in batches
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch analysis failed: {result}")
                    else:
                        all_findings.extend(result)

            logger.info(f"LLM detection found {len(all_findings)} risky clauses")
            return all_findings

        except Exception as e:
            logger.error(f"LLM clause detection failed entirely: {e}", exc_info=True)
            return []  # Graceful fallback — keyword detection still runs

    async def _analyze_batch(
        self,
        clauses: List[Dict[str, Any]],
        company_name: str,
        service_type: str = "general",
    ) -> List[Dict[str, Any]]:
        """Analyze a batch of clauses with one Claude API call."""

        # Build the clauses text
        clauses_text = self._format_clauses(clauses)

        # Build the prompt
        prompt = DETECTION_PROMPT.format(
            company_name=company_name,
            service_type=service_type,
            num_clauses=len(clauses),
            clauses_text=clauses_text,
        )

        logger.info(f"Sending {len(clauses)} clauses to Claude (prompt ~{len(prompt)} chars)")

        # Scale max_tokens based on clause count (~150 tokens per finding)
        max_tokens = max(8192, len(clauses) * 150)
        max_tokens = min(max_tokens, 16384)  # Cap at 16K

        # Call Claude
        response = await self.claude.create_structured_completion(
            prompt=prompt,
            temperature=0.3,
            max_tokens=max_tokens,
        )

        # Parse response
        return self._parse_response(response, clauses)

    def _format_clauses(self, clauses: List[Dict[str, Any]]) -> str:
        """Format clauses for the prompt."""
        parts = []
        for clause in clauses:
            section = clause.get("section", "Unknown")
            number = clause.get("clause_number", "?")
            text = clause.get("text", "").strip()
            # Truncate very long clauses to save tokens
            if len(text) > 2000:
                text = text[:2000] + "... [truncated]"
            parts.append(f"[{number}] Section: \"{section}\"\n{text}")
        return "\n\n---\n\n".join(parts)

    def _estimate_tokens(self, clauses: List[Dict[str, Any]]) -> int:
        """Estimate token count for a list of clauses."""
        total_words = sum(
            len(c.get("text", "").split()) for c in clauses
        )
        # Add overhead for formatting and section headers
        return int(total_words * TOKENS_PER_WORD) + len(clauses) * 20

    def _split_into_batches(
        self, clauses: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Split clauses into batches that fit within token limits. Recurses if needed."""
        total_tokens = self._estimate_tokens(clauses)

        if total_tokens <= MAX_INPUT_TOKENS:
            return [clauses]

        # Base case: can't split a single clause further
        if len(clauses) <= 1:
            logger.warning(
                f"Single clause exceeds token limit ({total_tokens} > {MAX_INPUT_TOKENS}). "
                f"Sending anyway — Claude may truncate."
            )
            return [clauses]

        # Split roughly in half and recurse
        mid = len(clauses) // 2
        batch1 = clauses[:mid]
        batch2 = clauses[mid:]

        logger.info(
            f"Splitting {len(clauses)} clauses (estimated {total_tokens} tokens "
            f"> {MAX_INPUT_TOKENS} limit)"
        )

        # Recursively split each half if still too large
        return self._split_into_batches(batch1) + self._split_into_batches(batch2)

    def _parse_response(
        self,
        response: Dict[str, Any],
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Parse and validate Claude's response."""
        # Build clause lookup for validation
        clause_numbers = {c.get("clause_number", "") for c in clauses}
        clause_map = {c.get("clause_number", ""): c for c in clauses}

        risky_clauses = response.get("risky_clauses", [])
        if not isinstance(risky_clauses, list):
            logger.warning(f"Unexpected response format: {type(risky_clauses)}")
            return []

        validated = []
        valid_severities = {"critical", "high", "medium", "low"}

        for finding in risky_clauses:
            clause_num = finding.get("clause_number", "")
            severity = finding.get("severity", "medium").lower()

            # Validate severity
            if severity not in valid_severities:
                severity = "medium"

            # Validate clause_number exists in our input
            if clause_num not in clause_numbers:
                # Try suffix match (Claude sometimes drops section prefix)
                # e.g., LLM returns "3" but we have "User Content.3"
                # Only accept if exactly one match to avoid ambiguity
                suffix = f".{clause_num}"
                candidates = [k for k in clause_numbers if k.endswith(suffix)]
                if len(candidates) == 1:
                    clause_num = candidates[0]
                else:
                    if candidates:
                        logger.warning(
                            f"LLM clause '{clause_num}' matched {len(candidates)} "
                            f"candidates: {candidates} — skipping ambiguous match"
                        )
                    else:
                        logger.warning(f"LLM referenced unknown clause: {clause_num}")
                    continue

            # Get the original clause data
            original = clause_map.get(clause_num, {})

            validated.append({
                "clause_number": clause_num,
                "section": original.get("section", finding.get("section", "Unknown")),
                "clause_text": original.get("text", ""),
                "severity": severity,
                "risk_category": finding.get("risk_category", "other"),
                "explanation": finding.get("explanation", ""),
                "consumer_impact": finding.get("consumer_impact", ""),
                "recommendation": finding.get("recommendation", ""),
                "detection_source": "llm",
            })

        logger.info(
            f"Validated {len(validated)}/{len(risky_clauses)} LLM findings "
            f"(severity: {sum(1 for v in validated if v['severity'] in ('critical','high'))} high, "
            f"{sum(1 for v in validated if v['severity'] == 'medium')} medium, "
            f"{sum(1 for v in validated if v['severity'] == 'low')} low)"
        )

        return validated
