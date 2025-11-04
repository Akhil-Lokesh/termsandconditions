"""
Prompt templates for metadata extraction.

Used by MetadataExtractor to extract structured information from T&C documents.
"""

METADATA_EXTRACTION_PROMPT = """You are a legal document analyst. Extract metadata from the following Terms & Conditions document.

Document Text (first 2000 characters):
{text_preview}

Extract the following information and respond with a JSON object:

{{
  "company_name": "Name of the company/service provider",
  "jurisdiction": "Legal jurisdiction (e.g., 'Delaware', 'California', 'United Kingdom')",
  "effective_date": "Effective date of the terms (ISO format YYYY-MM-DD if available, or null)",
  "last_updated": "Last updated date (ISO format YYYY-MM-DD if available, or null)",
  "document_type": "Type of document (e.g., 'Terms of Service', 'Privacy Policy', 'EULA')",
  "governing_law": "Governing law/jurisdiction mentioned",
  "version": "Version number if mentioned",
  "contact_email": "Contact email if mentioned",
  "website": "Company website if mentioned"
}}

Rules:
1. Only extract information explicitly stated in the document
2. Use null for fields not found
3. Be precise with dates (use ISO format YYYY-MM-DD)
4. For jurisdiction, extract the specific location (state/country)
5. Return ONLY the JSON object, no additional text

JSON Response:"""

CLAUSE_TYPE_CLASSIFICATION_PROMPT = """You are a legal expert. Classify the type of the following clause from a Terms & Conditions document.

Clause Text:
{clause_text}

Classify this clause into ONE of the following categories:
- payment_terms: Payment, pricing, fees, billing
- liability: Liability limitations, disclaimers, indemnification
- termination: Account termination, service cancellation
- intellectual_property: Copyright, trademarks, ownership
- privacy: Data collection, privacy, personal information
- dispute_resolution: Arbitration, legal disputes, class action
- user_obligations: User responsibilities, prohibited activities
- service_description: What the service provides, features
- modifications: Changes to terms, service changes
- warranties: Warranties, guarantees, representations
- general: Other general terms

Respond with ONLY the category name (e.g., "payment_terms"), nothing else.

Category:"""

DOCUMENT_SUMMARY_PROMPT = """You are a legal analyst. Provide a brief summary of this Terms & Conditions document.

Document Text:
{full_text}

Create a 2-3 sentence summary covering:
1. What service/product this T&C governs
2. The main obligations or restrictions for users
3. Any notable unusual clauses

Summary:"""
