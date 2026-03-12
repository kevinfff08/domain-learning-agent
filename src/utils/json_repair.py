"""Shared JSON repair utilities for parsing LLM-generated JSON."""

from __future__ import annotations

import json
import re


def repair_json(raw: str) -> dict:
    """Attempt multiple strategies to parse LLM-generated JSON object.

    LLMs often return slightly malformed JSON (trailing commas, markdown
    fences, truncated output).  This helper tries progressively more
    aggressive repair strategies.
    """
    text = _strip_fences(raw)

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract outermost { ... } block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError(f"No JSON object found in LLM response: {raw[:300]}")
    text = text[start:end]

    # 3. Try parse the extracted block
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Fix trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 5. Close unbalanced brackets/braces
    balanced = _close_brackets(fixed)
    if balanced != fixed:
        try:
            return json.loads(balanced)
        except json.JSONDecodeError:
            pass

    # 6. Truncate to last valid }
    for i in range(len(fixed) - 1, 0, -1):
        if fixed[i] == "}":
            try:
                return json.loads(fixed[: i + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Failed to parse LLM JSON after all repair attempts. First 500 chars: {raw[:500]}")


def repair_json_array(raw: str) -> list:
    """Attempt multiple strategies to parse LLM-generated JSON array."""
    text = _strip_fences(raw)

    # 1. Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Extract outermost [ ... ] block
    start = text.find("[")
    if start < 0:
        raise ValueError(f"No JSON array found in LLM response: {raw[:300]}")
    end = text.rfind("]") + 1
    if end <= start:
        # No closing ] — try closing brackets first
        text = text[start:]
        text = _close_brackets(text)
    else:
        text = text[start:end]

    # 3. Try parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. Fix trailing commas
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 5. Close unbalanced brackets
    balanced = _close_brackets(fixed)
    if balanced != fixed:
        try:
            return json.loads(balanced)
        except json.JSONDecodeError:
            pass

    # 6. Truncate to last valid ]
    for i in range(len(fixed) - 1, 0, -1):
        if fixed[i] == "]":
            try:
                return json.loads(fixed[: i + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Failed to parse LLM JSON array after all repair attempts. First 500 chars: {raw[:500]}")


def _strip_fences(raw: str) -> str:
    """Strip markdown code fences and whitespace."""
    text = raw.strip()
    # Remove opening fence (```json, ```JSON, ``` json, etc.)
    text = re.sub(r"^`{3,}\s*(?:json|JSON)?\s*\n?", "", text)
    # Remove closing fence (may not exist if output was truncated)
    text = re.sub(r"\n?\s*`{3,}\s*$", "", text)
    return text.strip()


def _close_brackets(text: str) -> str:
    """Append missing closing brackets/braces in correct nesting order."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()
    # Close in reverse nesting order
    if stack:
        text += "".join(reversed(stack))
    return text
