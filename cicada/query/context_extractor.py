"""
Utilities for extracting and formatting contextual text snippets from matched keywords.

This module provides functions to:
- Extract paragraphs containing matched keywords
- Highlight keywords with bold/color formatting
- Smart truncation of long strings
- Combine multiple keyword matches into unified excerpts
"""

import re


def extract_paragraph(text: str, keyword: str) -> str | None:
    """
    Extract the paragraph containing the given keyword.

    A paragraph is defined as text between double newlines or the entire text
    if no paragraph breaks exist.

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

    # Split text into paragraphs (double newline or single newline in markdown)
    # We treat both single and double newlines as paragraph breaks for flexibility
    paragraphs = re.split(r"\n\n+", text)

    # If no paragraph breaks, treat entire text as one paragraph
    if len(paragraphs) == 1:
        return text.strip()

    # Find the paragraph containing the keyword
    for para in paragraphs:
        if keyword_lower in para.lower():
            return para.strip()

    return None


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

    # Split into paragraphs
    paragraphs = re.split(r"\n\n+", text)
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
        score = sum(1 for kw in keywords if kw.lower() in para_lower)

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

    # Sort keywords by length (longest first) to avoid partial matches
    sorted_keywords = sorted(keywords, key=len, reverse=True)

    # Choose the delimiter based on output format
    if use_ansi:
        start_mark = "\033[1;33m"
        end_mark = "\033[0m"
    else:
        start_mark = "**"
        end_mark = "**"

    result = text
    for keyword in sorted_keywords:
        # Case-insensitive pattern that avoids matching text already inside markers
        # Use negative lookbehind to avoid matching inside already-highlighted text
        escaped_keyword = re.escape(keyword)

        # Build a pattern that won't match if the keyword is already highlighted
        # For markdown: avoid matching between ** markers
        # For ANSI: avoid matching between escape codes
        if use_ansi:
            # Don't match if preceded by ANSI start code
            pattern = re.compile(rf"(?<!\033\[1;33m)({escaped_keyword})(?!\033\[0m)", re.IGNORECASE)
        else:
            # Don't match if already between ** markers
            # This is a simplified approach - we just avoid double-wrapping
            pattern = re.compile(escaped_keyword, re.IGNORECASE)

        replacement = f"{start_mark}\\g<0>{end_mark}"

        # For non-ANSI, we need to be more careful about not double-highlighting
        if not use_ansi:
            # Find all positions where this keyword appears (not already highlighted)
            matches = []
            for match in pattern.finditer(result):
                # Check if this match is inside ** markers
                start = match.start()
                # Look for ** before this position
                before_text = result[:start]
                # Count ** markers before this position
                marker_count = before_text.count("**")
                # If odd number of **, we're inside a highlight
                if marker_count % 2 == 0:
                    matches.append(match)

            # Replace in reverse order to preserve positions
            for match in reversed(matches):
                result = (
                    result[: match.start()]
                    + f"{start_mark}{match.group()}{end_mark}"
                    + result[match.end() :]
                )
        else:
            result = pattern.sub(replacement, result)

    return result


def smart_truncate_string(text: str, max_length: int = 150, line_number: int | None = None) -> str:
    """
    Smart truncation of string literals with ellipsis.

    - If text is <= max_length, return as-is
    - If longer, truncate at word boundary and add ellipsis
    - Always include line number if provided

    Args:
        text: The string to potentially truncate
        max_length: Maximum length before truncation (default: 150)
        line_number: Optional line number to append

    Returns:
        Truncated string with optional line number
    """
    if not text:
        return '""'

    # If text is short enough, return as-is (maybe with line number)
    if len(text) <= max_length:
        if line_number is not None:
            return f'"{text}" (line {line_number})'
        return f'"{text}"'

    # Truncate at word boundary
    truncated = text[:max_length]

    # Find last space to avoid cutting mid-word
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:  # Only use space if it's not too far back
        truncated = truncated[:last_space]

    # Add ellipsis and line number
    if line_number is not None:
        return f'"{truncated}..." (line {line_number})'
    return f'"{truncated}..."'


def format_matched_context(
    matched_keywords: list[str],
    keyword_sources: dict[str, str],
    doc_text: str | None,
    string_sources: list[dict] | None,
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
    if doc_keywords and doc_text:
        para = extract_multiple_keywords(doc_text, doc_keywords)
        if para:
            highlighted = highlight_keywords(para, doc_keywords, use_ansi)
            sections.append(f"Matched in documentation:\n> {highlighted}")

    # Format string literal matches
    if string_keywords and string_sources:
        # Filter string sources that contain any of our keywords
        relevant_strings = []
        for source in string_sources:
            string_text = source.get("string", "")
            if any(kw.lower() in string_text.lower() for kw in string_keywords):
                relevant_strings.append(source)

        if relevant_strings:
            string_lines = []
            for source in relevant_strings[:3]:  # Limit to 3 string matches
                string_text = source.get("string", "")
                line_num = source.get("line")

                # Highlight keywords in the string
                highlighted = highlight_keywords(string_text, string_keywords, use_ansi)
                truncated = smart_truncate_string(highlighted, line_number=line_num)
                string_lines.append(f"> {truncated}")

            if string_lines:
                sections.append("Matched in strings:\n" + "\n".join(string_lines))

    return "\n\n".join(sections)
