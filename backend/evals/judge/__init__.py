"""LLM-as-judge harness for cross-family evaluation of clause classifications.

Two judges live in this package:

    claude_judge.ClaudeJudge  — primary judge (Anthropic Claude Opus tier).
    openai_judge.OpenAIJudge  — cross-family checker (OpenAI GPT-4o).

The orchestrator in ``runner.py`` runs the primary judge over all (clause,
prediction) pairs and the cross-family checker on a stratified random
sample, then logs any disagreement to ``judge_disagreements.jsonl``.

Cross-family means a DIFFERENT vendor — the openai_judge module is
intentionally walled off from any ``app/services/claude_service`` import
so a Claude model never grades a Claude model under the same harness. The
firewall is enforced both by the file's import hygiene and by the
acceptance grep in the parent Layer 4 brief.
"""
