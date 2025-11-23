"""
Utilities for extracting and formatting contextual text snippets from matched keywords.

This module provides functions to:
- Extract paragraphs containing matched keywords
- Highlight keywords with bold/color formatting
- Smart truncation of long strings
- Combine multiple keyword matches into unified excerpts
"""

import re

from cicada.query.types import StringSource


def extract_paragraph(text: str, keyword: str) -> str | None:
    """
    Extract the paragraph containing the given keyword.

    A paragraph is defined as text between single or double newlines or the
    entire text if no paragraph breaks exist.

    Args:
        text: The full text to search
        keyword: The keyword to find

    Returns:
        The paragraph containing the keyword, or None if keyword not found
    """
    if not text or not keyword:
        return None

    # Normalize the text and keyword for case-insensitive matching
    text_lower = text.lower()
    keyword_lower = keyword.lower()

    if keyword_lower not in text_lower:
        return None

    paragraphs = re.split(r"\n\n+|\n", text)

    # If no paragraph breaks, treat entire text as one paragraph
    if len(paragraphs) == 1:
        return text.strip()

    return next(
        (para.strip() for para in paragraphs if keyword_lower in para.lower()),
        None,
    )


def extract_multiple_keywords(text: str, keywords: list[str]) -> str | None:
    """
    Extract text containing multiple keywords, preferring paragraphs that contain
    the most keywords.

    Args:
        text: The full text to search
        keywords: List of keywords to find

    Returns:
        The best paragraph containing the most keywords, or None if no keywords found
    """
    if not text or not keywords:
        return None

    paragraphs = re.split(r"\n\n+|\n", text)
    if len(paragraphs) == 1:
        # Single paragraph - return if it contains any keyword
        text_lower = text.lower()
        if any(kw.lower() in text_lower for kw in keywords):
            return text.strip()
        return None

    # Score each paragraph by number of keywords it contains
    best_para = None
    best_score = 0

    for para in paragraphs:
        para_lower = para.lower()
        score = sum(bool(kw.lower() in para_lower) for kw in keywords)

        if score > best_score:
            best_score = score
            best_para = para

    return best_para.strip() if best_para else None


def highlight_keywords(text: str, keywords: list[str], use_ansi: bool = True) -> str:
    """
    Highlight keywords in text using bold formatting or ANSI colors.

    Args:
        text: The text to highlight keywords in
        keywords: List of keywords to highlight
        use_ansi: If True, use ANSI color codes; if False, use markdown bold

    Returns:
        Text with highlighted keywords
    """
    if not text or not keywords:
        return text

    sorted_keywords = sorted(keywords, key=len, reverse=True)

    start_mark = "\033[1;33m" if use_ansi else "**"
    end_mark = "\033[0m" if use_ansi else "**"

    result = text
    for keyword in sorted_keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        matches = []
        for match in pattern.finditer(result):
            start = match.start()
            before_text = result[:start]

            if use_ansi:
                start_count = before_text.count(start_mark)
                end_count = before_text.count(end_mark)
                if start_count > end_count:
                    continue
            else:
                if before_text.count(start_mark) % 2 == 1:
                    continue

            matches.append(match)

        for match in reversed(matches):
            result = (
                result[: match.start()]
                + f"{start_mark}{match.group()}{end_mark}"
                + result[match.end() :]
            )

    return result


def smart_truncate_string(
    text: str,
    max_length: int = 150,
    line_number: int | None = None,
    keywords: list[str] | None = None,
) -> str:
    """
    Smart truncation of string literals with ellipsis.

    - If text is <= max_length, return as-is
    - If longer, center the snippet around the first matching keyword when
      available to preserve relevant context
    - Always include line number if provided

    Args:
        text: The string to potentially truncate
        max_length: Maximum length before truncation (default: 150)
        line_number: Optional line number to append
        keywords: Optional list of keywords to keep in view when truncating

    Returns:
        Truncated string with optional line number
    """
    if not text:
        return '""'

    keywords = keywords or []
    text_lower = text.lower()

    # If text is short enough, return as-is (maybe with line number)
    if len(text) <= max_length:
        if line_number is not None:
            return f'"{text}" (line {line_number})'
        return f'"{text}"'

    def find_focus_index() -> int | None:
        positions = [text_lower.find(kw.lower()) for kw in keywords if kw]
        positions = [pos for pos in positions if pos != -1]
        return min(positions) if positions else None

    focus_index = find_focus_index()

    if focus_index is None or focus_index <= max_length:
        start = 0
    else:
        start = max(focus_index - max_length // 2, 0)

    end = start + max_length
    if end > len(text):
        end = len(text)
        start = max(0, end - max_length)

    snippet = text[start:end]
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    quoted = f'"{prefix}{snippet}{suffix}"'

    if line_number is not None:
        quoted = f"{quoted} (line {line_number})"

    return quoted


def format_matched_context(
    matched_keywords: list[str],
    keyword_sources: dict[str, str],
    doc_text: str | None,
    string_sources: list[StringSource] | None,
    use_ansi: bool = True,
) -> str:
    """
    Format the complete matched context section for a search result.

    This combines documentation and string literal matches into a unified,
    readable format with highlighted keywords.

    Args:
        matched_keywords: List of keywords that matched
        keyword_sources: Dict mapping keyword -> source ("docs", "strings", "both")
        doc_text: The documentation text (if available)
        string_sources: List of string literal sources (if available)
        use_ansi: Whether to use ANSI color codes (True) or markdown bold (False)

    Returns:
        Formatted string with matched context, or empty string if no context available
    """
    sections = []

    # Separate keywords by source
    doc_keywords = [kw for kw in matched_keywords if keyword_sources.get(kw) in ("docs", "both")]
    string_keywords = [
        kw for kw in matched_keywords if keyword_sources.get(kw) in ("strings", "both")
    ]

    # Format documentation matches
    if doc_keywords and doc_text and (para := extract_multiple_keywords(doc_text, doc_keywords)):
        highlighted = highlight_keywords(para, doc_keywords, use_ansi)
        sections.append(f"Matched in documentation:\n> {highlighted}")
    # Format string literal matches
    if string_keywords and string_sources:
        relevant_strings = []
        for source in string_sources:
            string_text = source.get("string")
            if not isinstance(string_text, str):
                continue
            if any(kw.lower() in string_text.lower() for kw in string_keywords):
                relevant_strings.append(source)

        if relevant_strings:
            string_lines = []
            for source in relevant_strings[:3]:  # Limit to 3 string matches
                string_text = source.get("string")
                if not isinstance(string_text, str):
                    continue
                line_num = source.get("line")

                truncated = smart_truncate_string(
                    string_text,
                    line_number=line_num,
                    keywords=string_keywords,
                )
                highlighted = highlight_keywords(truncated, string_keywords, use_ansi)
                string_lines.append(f"> {highlighted}")

            if string_lines:
                sections.append("Matched in strings:\n" + "\n".join(string_lines))

    return "\n\n".join(sections)
