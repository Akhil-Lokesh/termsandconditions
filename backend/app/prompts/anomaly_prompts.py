"""
Prompt templates for anomaly detection and risk assessment.

Used for identifying unusual/risky clauses in T&C documents.
"""

RISK_ASSESSMENT_PROMPT = """You are a consumer protection expert analyzing Terms & Conditions clauses.

Clause to Analyze:
{clause_text}

Section: {section}
Clause Number: {clause_number}

Similar Clauses from Standard T&Cs (for comparison):
{baseline_examples}

Detected Risk Indicators: {risk_flags}

Assess the risk level of this clause for consumers. Consider:
1. How it compares to standard T&C clauses
2. Consumer protection concerns
3. Fairness and transparency
4. Potential for consumer harm

Respond with a JSON object:
{{
  "severity": "low" | "medium" | "high",
  "risk_category": "liability" | "payment" | "privacy" | "arbitration" | "modification" | "other",
  "explanation": "2-3 sentences explaining why this clause is risky (or not)",
  "consumer_impact": "Brief description of how this affects consumers",
  "recommendation": "What users should know about this clause"
}}

Rules:
- "high" severity: Severely unfair, hidden costs, unusual liability waivers
- "medium" severity: Uncommon but not necessarily harmful
- "low" severity: Common clause with no major concerns
- Be objective and specific in explanations
- Return ONLY the JSON object

JSON Response:"""

PREVALENCE_EXPLANATION_PROMPT = """You are a legal analyst. Explain why a clause is unusual compared to standard T&Cs.

Clause Text:
{clause_text}

Prevalence Score: {prevalence:.2f} (0.0 = very rare, 1.0 = very common)

Most Similar Standard Clauses:
{similar_clauses}

Explain in 1-2 sentences why this clause is less common than standard T&Cs. What makes it different?

Explanation:"""

CLAUSE_COMPARISON_PROMPT = """You are a legal expert. Compare two clauses and explain the key differences.

User's Clause (from uploaded T&C):
{user_clause}

Standard Clause (from baseline T&C):
{standard_clause}

Explain the key differences in 2-3 sentences. Focus on:
1. What's different in the user's clause
2. Why this difference matters
3. Is the user's clause more/less favorable to consumers?

Comparison:"""

ANOMALY_SUMMARY_PROMPT = """You are a legal analyst. Summarize the detected anomalies in a Terms & Conditions document.

Document: {document_name}

Detected Anomalies:
{anomalies_list}

Provide a brief summary (3-4 sentences) covering:
1. Overall assessment of the document (e.g., "mostly standard", "several concerning clauses")
2. The most critical issues to be aware of
3. Recommended next steps for the user

Summary:"""
