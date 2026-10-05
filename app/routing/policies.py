import re
from typing import Any
from app.core.constants import MODEL_CODE, MODEL_ANALYSIS, MODEL_FAST

# Deterministic heuristic patterns for nvirya-auto
CODE_PATTERNS = re.compile(
    r"\b(code|function|endpoint|python|javascript|typescript|bug|debug|refactor|class|def|import|sql|api|fastapi|html|css|json|script|algorithm|regex|test|git)\b",
    re.IGNORECASE,
)

ANALYSIS_PATTERNS = re.compile(
    r"\b(search|find current|summarize|compare|analysis|synthesize|news|latest|report|research|sources|articles|overview)\b",
    re.IGNORECASE,
)

def classify_prompt_intent(messages: list[dict[str, Any]]) -> str:
    """Classifies user messages to pick the best model alias."""
    # Concatenate text from recent user messages
    text_parts = []
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
        if len(text_parts) >= 3:
            break

    full_text = " ".join(text_parts)
    if not full_text.strip():
        return MODEL_FAST

    # Check coding keywords
    if CODE_PATTERNS.search(full_text):
        return MODEL_CODE

    # Check search / analysis keywords
    if ANALYSIS_PATTERNS.search(full_text):
        return MODEL_ANALYSIS

    # For short simple chat queries (e.g. < 60 characters)
    if len(full_text.strip()) < 60:
        return MODEL_FAST

    return MODEL_CODE
