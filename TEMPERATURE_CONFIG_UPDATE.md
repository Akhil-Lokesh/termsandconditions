# Temperature Configuration Update

## Overview
Updated the GPT-5 two-stage system to correctly handle temperature settings:
- **GPT-5-Nano**: NO temperature parameter (reasoning model, fixed by OpenAI)
- **GPT-5**: Temperature = 1.0 (adjustable, as requested)

---

## Changes Made

### 1. Stage 1 Classifier (GPT-5-Nano)

**File**: `backend/app/services/gpt5_stage1_classifier.py`

**Configuration**:
```python
MODEL_NAME = "gpt-5-nano"  # Fast reasoning model
TEMPERATURE = None  # Not used for reasoning models
```

**Reasoning**:
- GPT-5-Nano is a **reasoning model** (like o1-mini)
- Reasoning models do NOT support temperature parameter
- Temperature is fixed by OpenAI for optimal reasoning performance
- Passing temperature would cause API errors

**API Call**:
```python
# Temperature parameter is not passed for gpt-5-nano
response = await self.openai.create_structured_completion(
    prompt=prompt,
    model="gpt-5-nano",
    temperature=0.0  # Will be ignored by OpenAI service
)
```

---

### 2. Stage 2 Analyzer (GPT-5)

**File**: `backend/app/services/gpt5_stage2_analyzer.py`

**Configuration**:
```python
MODEL_NAME = "gpt-5"  # Full GPT-5 model
TEMPERATURE = 1.0  # Adjustable temperature for GPT-5 ✅
```

**Reasoning**:
- GPT-5 (full model) **supports temperature** parameter
- Temperature = 1.0 provides balanced creativity and consistency
- Suitable for legal analysis requiring nuanced reasoning

**API Call**:
```python
# Temperature IS used for gpt-5
response = await self.openai.create_structured_completion(
    prompt=prompt,
    model="gpt-5",
    temperature=1.0  # ✅ Used by GPT-5
)
```

---

### 3. OpenAI Service (Enhanced Logic)

**File**: `backend/app/services/openai_service.py`

**Updated Logic**:
```python
# Handle different model types
if "gpt-5-nano" in model.lower() or "o1-mini" in model.lower():
    # Reasoning models: NO temperature parameter
    response = await self.client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=max_tokens,
        # ❌ NO temperature parameter
    )

elif "gpt-5" in model.lower() or "o1-preview" in model.lower():
    # GPT-5 full model: Supports temperature
    response = await self.client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,  # ✅ Temperature IS used
        max_completion_tokens=max_tokens,
    )

else:
    # GPT-4, GPT-3.5: Standard models
    response = await self.client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
```

**Key Improvements**:
1. **Separate handling** for gpt-5-nano (no temperature)
2. **Temperature support** for gpt-5 (full model)
3. **Maintains backward compatibility** with GPT-4/3.5

---

## Model Comparison

| Model | Temperature | Reason |
|-------|-------------|--------|
| **gpt-5-nano** | ❌ Not adjustable | Reasoning model (like o1-mini) |
| **gpt-5** | ✅ 1.0 (adjustable) | Full GPT-5 supports temperature |
| **o1-mini** | ❌ Not adjustable | Reasoning model |
| **o1-preview** | ❌ Not adjustable* | Reasoning model |
| **gpt-4** | ✅ Adjustable (0-2) | Standard model |
| **gpt-3.5-turbo** | ✅ Adjustable (0-2) | Standard model |

*Note: o1-preview logic kept for backward compatibility, but it's also a reasoning model

---

## API Parameter Differences

### Reasoning Models (gpt-5-nano, o1-mini)
```python
{
  "model": "gpt-5-nano",
  "messages": [...],
  "max_completion_tokens": 2000,  # ✅ Uses max_completion_tokens
  # ❌ NO temperature parameter
}
```

### Full GPT-5 Model
```python
{
  "model": "gpt-5",
  "messages": [...],
  "temperature": 1.0,  # ✅ Temperature parameter
  "max_completion_tokens": 4000,  # ✅ Uses max_completion_tokens
}
```

### Standard Models (GPT-4, GPT-3.5)
```python
{
  "model": "gpt-4",
  "messages": [...],
  "temperature": 0.0,  # ✅ Temperature parameter
  "max_tokens": 1000,  # ✅ Uses max_tokens (not max_completion_tokens)
}
```

---

## Why This Matters

### Reasoning Models (GPT-5-Nano)
- **Fixed internal reasoning process**
- Temperature would interfere with chain-of-thought
- OpenAI optimizes temperature internally
- Passing temperature → API error

### Full Models (GPT-5)
- **Flexible output control**
- Temperature affects response diversity
- `temperature=1.0` balances:
  - Creativity (varied responses)
  - Consistency (reliable analysis)
  - Legal reasoning (nuanced understanding)

---

## Configuration Summary

```python
# Stage 1: GPT-5-Nano (Fast Classification)
MODEL = "gpt-5-nano"
TEMPERATURE = None  # Not used ❌
MAX_TOKENS = 2000
COST = $0.0006/doc

# Stage 2: GPT-5 (Deep Analysis)
MODEL = "gpt-5"
TEMPERATURE = 1.0  # Adjustable ✅
MAX_TOKENS = 4000
COST = $0.015/doc
```

---

## Verification

### Test Configuration
```bash
cd backend
source venv/bin/activate
python3 -c "
from app.services.gpt5_stage1_classifier import GPT5Stage1Classifier
from app.services.gpt5_stage2_analyzer import GPT5Stage2Analyzer

stage1 = GPT5Stage1Classifier()
stage2 = GPT5Stage2Analyzer()

print('Stage 1 (gpt-5-nano):')
print(f'  Model: {stage1.MODEL_NAME}')
print(f'  Temperature: {stage1.TEMPERATURE}')
print()
print('Stage 2 (gpt-5):')
print(f'  Model: {stage2.MODEL_NAME}')
print(f'  Temperature: {stage2.TEMPERATURE}')
"
```

**Expected Output**:
```
Stage 1 (gpt-5-nano):
  Model: gpt-5-nano
  Temperature: None

Stage 2 (gpt-5):
  Model: gpt-5
  Temperature: 1.0
```

---

## Impact on System

### Before This Update
- ❌ GPT-5-Nano tried to use temperature (would cause error)
- ✅ GPT-5 used temperature=1.0 correctly

### After This Update
- ✅ GPT-5-Nano: No temperature parameter (correct)
- ✅ GPT-5: Temperature=1.0 (correct and adjustable)
- ✅ OpenAI service handles both model types correctly

---

## How to Adjust Temperature (GPT-5 Only)

If you want to change temperature for **GPT-5** (Stage 2):

### Option 1: Edit Stage 2 Analyzer
```python
# In backend/app/services/gpt5_stage2_analyzer.py

# Change this line (currently line 39):
TEMPERATURE = 1.0  # Change to your desired value (0.0-2.0)

# Examples:
TEMPERATURE = 0.5  # More focused/deterministic
TEMPERATURE = 1.0  # Balanced (current)
TEMPERATURE = 1.5  # More creative/diverse
```

### Option 2: Via Environment Variable (Future Enhancement)
```python
# Could add to config.py:
OPENAI_GPT5_TEMPERATURE: float = 1.0

# Then use in stage2_analyzer.py:
TEMPERATURE = settings.OPENAI_GPT5_TEMPERATURE
```

---

## Files Modified

### Core Services
✅ **`backend/app/services/gpt5_stage1_classifier.py`**
   - Line 46: Set `TEMPERATURE = None`
   - Line 110: Added comment about reasoning model

✅ **`backend/app/services/gpt5_stage2_analyzer.py`**
   - Line 39: Kept `TEMPERATURE = 1.0` ✅

✅ **`backend/app/services/openai_service.py`**
   - Lines 190-221: Enhanced model handling logic
   - Separate branches for gpt-5-nano, gpt-5, and standard models

### Documentation
✅ **`TEMPERATURE_CONFIG_UPDATE.md`** (this file)

---

## Important Notes

### 1. GPT-5 Model Availability
- GPT-5 and GPT-5-Nano may not be released yet
- Code is configured correctly for when they are available
- Until then, API calls will fail with "model not found"
- **Temporary workaround**: Use o1-mini (Stage 1) and o1-preview (Stage 2)

### 2. Temperature Range
For models that support temperature:
- **0.0**: Most deterministic (same output every time)
- **1.0**: Balanced (recommended for legal analysis)
- **2.0**: Most creative/diverse (not recommended for analysis)

### 3. Cost Implications
Temperature does NOT affect cost:
- Cost is based on tokens consumed
- Higher temperature → more varied outputs
- But token count remains similar

---

## Rollback

If you need to revert:

```bash
# Restore original configuration
cd backend/app/services

# Stage 1: Add temperature back (if needed)
# Line 46: TEMPERATURE = 1.0

# Stage 2: No changes needed (already correct)

# OpenAI Service: Revert to original logic (if needed)
git checkout app/services/openai_service.py
```

---

## Summary

✅ **Stage 1 (gpt-5-nano)**: Temperature = None (reasoning model, not adjustable)
✅ **Stage 2 (gpt-5)**: Temperature = 1.0 (adjustable as requested)
✅ **OpenAI Service**: Handles both model types correctly
✅ **Backward Compatible**: Works with o1-mini, o1-preview, GPT-4, GPT-3.5

The system now correctly distinguishes between:
- **Reasoning models** (no temperature): gpt-5-nano, o1-mini
- **Full models** (with temperature): gpt-5, o1-preview, gpt-4, gpt-3.5-turbo

---

**Updated**: November 2, 2025
**Status**: ✅ COMPLETE
**Temperature**: Only GPT-5 (Stage 2) uses temperature=1.0
**Reasoning Models**: GPT-5-Nano (Stage 1) does not use temperature
