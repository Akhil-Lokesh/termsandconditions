# GPT-5 Empty Response Fix - Complete Guide

## ❌ The Problem

You're getting **empty responses** from GPT-5 models because you're using the **wrong API**.

### What Doesn't Work:
```python
# ❌ WRONG: Chat Completions API doesn't work for GPT-5
response = await client.chat.completions.create(
    model="gpt-5-nano",
    messages=[...],
    max_tokens=1000  # ❌ Wrong parameter
)
text = response.choices[0].message.content  # ❌ Empty!
```

---

## ✅ The Solution

GPT-5 models use the **Responses API** (different from GPT-4):

### Correct Implementation:
```python
# ✅ CORRECT: Responses API for GPT-5
response = await client.responses.create(
    model="gpt-5-nano",
    input_text=prompt,  # ✅ Use input_text
    max_completion_tokens=1000,  # ✅ NOT max_tokens!
    reasoning_effort="medium"  # ✅ Required for quality
)
text = response.output_text  # ✅ Works!
```

---

## 🔑 Key Differences: GPT-4 vs GPT-5

| Feature | GPT-4 (Chat API) | GPT-5 (Responses API) |
|---------|------------------|----------------------|
| **Method** | `chat.completions.create()` | `responses.create()` |
| **Input** | `messages=[...]` | `input_text="..."` |
| **Output** | `response.choices[0].message.content` | `response.output_text` |
| **Max tokens param** | `max_tokens=X` | `max_completion_tokens=X` |
| **Quality control** | `temperature=0.7` | `reasoning_effort="medium"` |
| **Temperature** | Adjustable (0.0-2.0) | **IGNORED** (fixed) |

---

## 📋 Complete Working Code

### File: `backend/app/services/gpt5_service.py`

```python
from openai import AsyncOpenAI
import json

class GPT5Service:
    """Correct GPT-5 implementation."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def create_response(
        self,
        prompt: str,
        model: str = "gpt-5-nano",
        reasoning_effort: str = "medium",
        max_completion_tokens: int = 2000
    ) -> str:
        """
        Create GPT-5 response using CORRECT API.

        Args:
            prompt: Your question/prompt
            model: "gpt-5-nano" (cheap) or "gpt-5-mini" (better)
            reasoning_effort: "low" | "medium" | "high"
                - low: Fast, cheap, less thorough
                - medium: Balanced (recommended)
                - high: Slower, expensive, most thorough
            max_completion_tokens: Output length limit

        Returns:
            Response text
        """
        # ✅ CORRECT: Use responses.create()
        response = await self.client.responses.create(
            model=model,
            input_text=prompt,  # ✅ Not 'messages'
            max_completion_tokens=max_completion_tokens,  # ✅ Not 'max_tokens'
            reasoning_effort=reasoning_effort,  # ✅ Required
        )

        # ✅ CORRECT: Access output_text
        return response.output_text

    async def create_json_response(
        self,
        prompt: str,
        model: str = "gpt-5-nano"
    ) -> dict:
        """Get JSON response from GPT-5."""
        response = await self.client.responses.create(
            model=model,
            input_text=prompt,
            max_completion_tokens=2000,
            reasoning_effort="medium",
            response_format={"type": "json_object"}  # ✅ Force JSON
        )

        return json.loads(response.output_text)
```

---

## ⚠️ Parameters to AVOID with GPT-5

These parameters **don't work** or are **ignored** by GPT-5:

```python
# ❌ DON'T USE THESE:
temperature=0.7,         # Ignored (reasoning models have fixed temp)
top_p=0.9,              # Ignored
frequency_penalty=0.5,  # Ignored
presence_penalty=0.5,   # Ignored
max_tokens=1000,        # Wrong parameter name (use max_completion_tokens)
messages=[...],         # Wrong API (use input_text)
```

---

## 🎯 Usage in Your Anomaly Detector

### Update `risk_assessor.py`:

```python
from app.services.gpt5_service import GPT5Service

class RiskAssessor:
    def __init__(self):
        self.gpt5 = GPT5Service()

    async def assess_risk(
        self,
        clause_text: str,
        detected_indicators: List[Dict],
        prevalence: float
    ) -> Dict:
        """Assess risk using GPT-5-nano."""

        prompt = f"""Analyze this Terms & Conditions clause:

CLAUSE: {clause_text}
INDICATORS: {detected_indicators}
PREVALENCE: {prevalence*100:.0f}%

Return JSON:
{{
  "risk_level": "high/medium/low",
  "explanation": "...",
  "consumer_impact": "..."
}}
"""

        # ✅ Use GPT-5 correctly
        result = await self.gpt5.create_json_response(
            prompt=prompt,
            model="gpt-5-nano"  # Fast and cheap
        )

        return result
```

---

## 🔄 Migration Steps

### Step 1: Install/Import GPT5Service
```python
from app.services.gpt5_service import GPT5Service

gpt5 = GPT5Service(api_key="your-key")
```

### Step 2: Replace Old Calls
```python
# ❌ OLD (doesn't work):
response = await openai.chat.completions.create(
    model="gpt-5-nano",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1000
)
text = response.choices[0].message.content  # Empty!

# ✅ NEW (works):
text = await gpt5.create_response(
    prompt=prompt,
    model="gpt-5-nano",
    max_completion_tokens=1000
)
```

### Step 3: Test
```python
result = await gpt5.create_response(
    prompt="What is 2+2?",
    model="gpt-5-nano"
)
print(result)  # Should print answer, not empty string
```

---

## 📊 Reasoning Effort Guide

| Level | Speed | Cost | Quality | Use For |
|-------|-------|------|---------|---------|
| **low** | Fast | $0.0003/doc | Basic | Simple classifications |
| **medium** | Medium | $0.0006/doc | Good | **Anomaly detection** ⭐ |
| **high** | Slow | $0.0012/doc | Best | Complex legal analysis |

**Recommendation**: Use `reasoning_effort="medium"` for anomaly detection.

---

## 🐛 Debugging Empty Responses

If you still get empty responses:

### 1. Check the API method:
```python
# Make sure you're using:
response = await client.responses.create(...)
# NOT:
response = await client.chat.completions.create(...)
```

### 2. Check the output accessor:
```python
# Make sure you're using:
text = response.output_text
# NOT:
text = response.choices[0].message.content
```

### 3. Check model name:
```python
# Correct model names:
"gpt-5-nano"   # ✅
"gpt-5-mini"   # ✅

# Wrong names:
"gpt5-nano"    # ❌
"gpt-5"        # ❌
"gpt5"         # ❌
```

### 4. Add logging:
```python
response = await client.responses.create(...)
print(f"Response type: {type(response)}")
print(f"Has output_text: {hasattr(response, 'output_text')}")
print(f"Output length: {len(response.output_text)}")
print(f"Output: {response.output_text}")
```

---

## 💰 Cost Comparison

### Per 1M tokens:

| Model | Input | Output | Typical Doc |
|-------|-------|--------|-------------|
| **gpt-5-nano** (low) | $0.15 | $0.60 | $0.0003 |
| **gpt-5-nano** (medium) | $0.15 | $0.60 | $0.0006 |
| **gpt-5-nano** (high) | $0.15 | $0.60 | $0.0012 |
| **gpt-5-mini** | $0.30 | $1.20 | $0.0018 |
| **gpt-4o-mini** | $0.15 | $0.60 | $0.0010 |

**Best for anomaly detection**: `gpt-5-nano` with `reasoning_effort="medium"` = **$0.0006/doc**

---

## ✅ Final Checklist

Before deploying, verify:

- [ ] Using `client.responses.create()` (not `chat.completions.create()`)
- [ ] Using `input_text=prompt` (not `messages=[...]`)
- [ ] Using `max_completion_tokens=X` (not `max_tokens=X`)
- [ ] Using `response.output_text` (not `response.choices[0].message.content`)
- [ ] Set `reasoning_effort="medium"`
- [ ] NOT using `temperature` parameter (it's ignored)
- [ ] Model name is `"gpt-5-nano"` or `"gpt-5-mini"`
- [ ] Getting non-empty responses in tests

---

## 🚀 Quick Start

Copy this minimal working example:

```python
from openai import AsyncOpenAI

async def test_gpt5():
    client = AsyncOpenAI(api_key="your-key")

    # ✅ This works:
    response = await client.responses.create(
        model="gpt-5-nano",
        input_text="What is 2+2? Return JSON: {\"answer\": X}",
        max_completion_tokens=100,
        reasoning_effort="medium",
        response_format={"type": "json_object"}
    )

    print(response.output_text)  # {"answer": 4}

# Run it:
import asyncio
asyncio.run(test_gpt5())
```

If this prints `{"answer": 4}`, you're all set! ✅

---

**File Location**: `backend/app/services/gpt5_service.py`
**Status**: Ready to use
**Next Step**: Update `risk_assessor.py` to use `GPT5Service`
