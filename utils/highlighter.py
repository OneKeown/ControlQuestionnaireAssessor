import re
from html import escape


def highlight_terms(text: str, expected_terms: list[str], fail_terms: list[str]) -> str:
    """
    Highlights:
    - expected_terms in green
    - fail_terms in red
    Returns HTML string for Streamlit rendering.
    """

    if not text:
        return ""

    # Escape HTML so we don't break rendering
    text = escape(text)

    # Sort longer terms first (avoids partial overlaps)
    expected_terms = sorted(set(expected_terms), key=len, reverse=True)
    fail_terms = sorted(set(fail_terms), key=len, reverse=True)

    # 🔴 Highlight fail terms first
    for term in fail_terms:
        if not term.strip():
            continue

        pattern = re.compile(re.escape(term), re.IGNORECASE)

        text = pattern.sub(
            lambda m: f"<span style='background-color:#ffcccc; padding:2px 4px; border-radius:4px;'>{m.group(0)}</span>",
            text
        )

    # 🟢 Highlight expected terms
    for term in expected_terms:
        if not term.strip():
            continue

        pattern = re.compile(re.escape(term), re.IGNORECASE)

        text = pattern.sub(
            lambda m: f"<span style='background-color:#d4edda; padding:2px 4px; border-radius:4px;'>{m.group(0)}</span>",
            text
        )

    # Preserve line breaks
    return text.replace("\n", "<br>")