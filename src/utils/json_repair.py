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
    if start < 0:
        raise ValueError(f"No JSON object found in LLM response: {raw[:300]}")
    if end <= start:
        # No closing brace — likely truncated, extract from { to end
        text = text[start:]
    else:
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

    # 5. Close unclosed strings, then unbalanced brackets/braces
    #    (critical for truncated LLM output that cuts off mid-string)
    closed_str = _close_unclosed_string(fixed)
    balanced = _close_brackets(closed_str)
    if balanced != fixed:
        # Remove trailing incomplete key-value pair, then try parse
        cleaned = _trim_trailing_partial(balanced)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Try without trimming
        try:
            return json.loads(balanced)
        except json.JSONDecodeError:
            pass

    # 6. Truncate to last valid }
    for i in range(len(fixed) - 1, 0, -1):
        if fixed[i] == "}":
            candidate = fixed[: i + 1]
            candidate = _close_unclosed_string(candidate)
            candidate = _close_brackets(candidate)
            try:
                return json.loads(candidate)
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
        text = _close_unclosed_string(text)
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
    closed_str = _close_unclosed_string(fixed)
    balanced = _close_brackets(closed_str)
    if balanced != fixed:
        cleaned = _trim_trailing_partial(balanced)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(balanced)
        except json.JSONDecodeError:
            pass

    # 6. Truncate to last valid ]
    for i in range(len(fixed) - 1, 0, -1):
        if fixed[i] == "]":
            candidate = fixed[: i + 1]
            candidate = _close_unclosed_string(candidate)
            candidate = _close_brackets(candidate)
            try:
                return json.loads(candidate)
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


def _close_unclosed_string(text: str) -> str:
    """If text ends inside an unclosed JSON string, close it.

    This is critical for truncated LLM output where the response was cut
    off mid-value (e.g. a long LaTeX string).  Without closing the string
    first, _close_brackets will think all remaining text is inside the
    string and fail to count brackets correctly.
    """
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        # Remove any trailing incomplete escape sequence
        if text.endswith("\\"):
            text = text[:-1]
        text += '"'
    return text


def _trim_trailing_partial(text: str) -> str:
    """Remove trailing incomplete key-value pairs after the last complete value.

    When JSON is truncated and we've closed strings/brackets, there may be
    a dangling partial entry like:  ..."complete_key": "value", "partial_k"]}
    This tries to remove the incomplete trailing entry before the closing brackets.
    """
    # Find the closing brackets/braces we appended
    # Try removing content after the last complete value + comma
    # Pattern: find last complete string/number/bool/null value followed by comma,
    #          then remove everything between that comma and closing brackets
    match = re.search(
        r'((?:"[^"]*"|true|false|null|\d+(?:\.\d+)?|\}|\])\s*,)\s*"[^"]*"\s*:\s*"[^"]*"(\s*[}\]]+\s*)$',
        text,
    )
    if match:
        # Remove the trailing partial entry
        return text[: match.start(1) + len(match.group(1))] + match.group(2)
    return text


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
        if ch == '"':
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
