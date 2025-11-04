"""
Classification prompts for clause categorization.
"""

CLAUSE_CLASSIFICATION_PROMPT = """
Classify the following Terms & Conditions clause into one of these categories:
- payment: Payment terms, fees, billing
- privacy: Data collection, usage, sharing
- liability: Liability limitations, disclaimers
- termination: Account termination, cancellation
- arbitration: Dispute resolution, arbitration clauses
- ip: Intellectual property, content ownership
- warranty: Warranties, guarantees
- content: User-generated content policies
- modification: Right to modify terms
- other: Other categories

Return only the category name.
"""
