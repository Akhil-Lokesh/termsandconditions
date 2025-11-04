"""
Risk assessment prompts.
"""

RISK_ASSESSMENT_TEMPLATE = """
Assess the risk level of this Terms & Conditions clause:

Clause: {clause_text}
Type: {clause_type}
Prevalence: Found in {prevalence}% of similar T&Cs
Risk Indicators: {risk_indicators}

Evaluate:
- Does this waive important user rights?
- Are there hidden costs or obligations?
- Is it unusually restrictive?
- Does it favor the company unfairly?

Return JSON with:
{{
  "risk_level": "high|medium|low",
  "explanation": "Clear explanation of the risk",
  "affected_rights": ["specific rights affected"],
  "recommendation": "What users should know"
}}
"""
