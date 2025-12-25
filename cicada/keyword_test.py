"""
Interactive keyword extraction testing module.

Provides an interactive REPL for testing keyword extraction methods.
"""

import sys


def run_expansion_interactive(
    expansion_type: str = "lemmi",
    extraction_method: str = "regular",
    extraction_threshold: float | None = 0.3,
    expansion_threshold: float = 0.2,
    min_score: float = 0.5,
):
    """
    Interactive keyword expansion testing mode.

    Shows the full pipeline: Text → Extracted Keywords → Expanded Keywords

    Args:
        expansion_type: Expansion strategy ('lemmi')
        extraction_method: Extraction method ('regular')
        extraction_threshold: Minimum score for extraction (default: 0.3)
        expansion_threshold: Minimum similarity score for expansion (default: 0.2)
        min_score: Minimum score threshold for keywords (default: 0.5)
    """
    print(f"\n{'='*70}")
    print("🔄 Cicada Interactive Keyword Pipeline Test")
    print(f"{'='*70}")

    # Map extraction method to display name
    extraction_display = "REGULAR (token-based)"
    print(f"Extraction: {extraction_display}")
    print(f"Expansion: {expansion_type.upper()}")
    if extraction_threshold is not None:
        print(f"Extraction threshold: {extraction_threshold}")
    if min_score > 0.0:
        print(f"Min score: {min_score}")
    print(f"Expansion threshold: {expansion_threshold}")

    # Show strategy description
    expansion_descriptions = {
        "lemmi": "Inflected forms only (run → running, runs, ran)",
    }
    print(f"Strategy: {expansion_descriptions.get(expansion_type, 'Unknown')}")

    print("\nEnter text, then press Ctrl-D (Unix) or Ctrl-Z+Enter (Windows)")
    print("Press Ctrl-C to exit.\n")
    print(f"{'='*70}\n")

    # Initialize keyword extractor
    try:
        if extraction_method == "regular":
            from cicada.extractors.keyword import RegularKeywordExtractor

            extractor = RegularKeywordExtractor(verbose=True)
        else:
            raise ValueError(
                f"Unknown extraction method: {extraction_method} (only 'regular' is supported)"
            )
        print()  # Add newline after initialization
    except Exception as e:
        print(f"Error initializing keyword extractor: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize keyword expander
    try:
        from cicada.keyword_expander import KeywordExpander

        expander = KeywordExpander(expansion_type=expansion_type, verbose=True)
        print()  # Add newline after initialization
    except Exception as e:
        print(f"Error initializing keyword expander: {e}", file=sys.stderr)
        sys.exit(1)

    # Interactive loop
    stdin_closed = False
    try:
        while True:
            print("📝 Enter text (Ctrl-D or Ctrl-Z+Enter when done):")
            print("-" * 70)

            # Read multi-line input until EOF
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                if not lines and stdin_closed:
                    print("\n👋 No more input available. Exiting.")
                    return
                stdin_closed = True

            text = "\n".join(lines)

            if not text.strip():
                print("\n⚠️  Empty input. Please enter some text.\n")
                continue

            # Full pipeline display
            print("\n" + "=" * 70)
            print("🔄 KEYWORD PIPELINE:")
            print("=" * 70)

            try:
                # Step 1: Show input text
                print("\n1️⃣  INPUT TEXT:")
                print("-" * 70)
                preview = text[:200] + "..." if len(text) > 200 else text
                print(f"{preview}\n")

                # Step 2: Extract keywords
                print("2️⃣  EXTRACTED KEYWORDS:")
                print("-" * 70)
                results = extractor.extract_keywords(text, top_n=15, min_score=min_score)
                top_keywords = results.get("top_keywords", [])

                # Apply extraction threshold if specified
                if extraction_threshold is not None and top_keywords:
                    filtered_keywords = [
                        item
                        for item in top_keywords
                        if isinstance(item, (list, tuple))
                        and len(item) >= 2
                        and item[1] >= extraction_threshold
                    ]
                    if len(filtered_keywords) < len(top_keywords):
                        removed_count = len(top_keywords) - len(filtered_keywords)
                        print(
                            f"⚠️  Filtered out {removed_count} keywords below threshold {extraction_threshold}\n"
                        )
                    top_keywords = filtered_keywords

                extracted_keywords = []
                extraction_scores = {}  # Map keywords to their extraction scores
                code_identifiers_lower = [
                    ident.lower() for ident in results.get("code_identifiers", [])
                ]
                code_split_words_lower = [
                    word.lower() for word in results.get("code_split_words", [])
                ]

                if top_keywords and isinstance(top_keywords, list):
                    for i, item in enumerate(top_keywords, 1):
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            keyword, score = item[0], item[1]
                            extracted_keywords.append(keyword)
                            extraction_scores[keyword.lower()] = score  # Store extraction score

                            # Determine if this keyword was boosted
                            boost_label = ""
                            if keyword.lower() in code_identifiers_lower:
                                boost_label = " [10x boost]"
                            elif keyword.lower() in code_split_words_lower:
                                boost_label = " [3x boost]"

                            print(f"  {i:2}. {keyword:20s} (score: {score:.4f}){boost_label}")

                if not extracted_keywords:
                    print("  No keywords extracted.")
                    print("\n" + "=" * 70 + "\n")
                    continue

                print(f"\nTotal extracted: {len(extracted_keywords)} keywords")
                if code_identifiers_lower or code_split_words_lower:
                    print(f"  • Code identifiers (10x): {len(code_identifiers_lower)}")
                    print(f"  • Code split words (3x): {len(code_split_words_lower)}")
                print()

                # Step 3: Expand keywords
                print("3️⃣  EXPANDED KEYWORDS:")
                print("-" * 70)
                print("Note: Expansion scores = extraction score × similarity score")
                print("Note: Code identifiers are NOT inflected or expanded (kept exact)\n")
                result = expander.expand_keywords(
                    extracted_keywords,
                    top_n=3,
                    threshold=expansion_threshold,
                    keyword_scores=extraction_scores,
                    min_score=min_score,
                    code_identifiers=results.get("code_identifiers", []),
                )

                # Extract detailed and simple lists
                if isinstance(result, dict):
                    expanded_with_scores = result["words"]
                    expanded = result["simple"]
                else:
                    # Fallback if return_scores wasn't supported
                    expanded = result
                    expanded_with_scores = []

                # Group by source type
                by_source = {
                    "original": [],
                    "split": [],
                    "inflection": [],
                    "embedding": [],
                    "embedding_inflection": [],
                }

                for item in expanded_with_scores:
                    source = item.get("source", "unknown")
                    by_source.setdefault(source, []).append(item)

                # Display originals
                if by_source["original"]:
                    print(f"\nFrom extraction ({len(by_source['original'])}):")
                    for item in by_source["original"][:20]:
                        score = item.get("score", 1.0)
                        print(f"  ✓ {item['word']:25s} (score: {score:.3f})")

                # Display splits
                if by_source["split"]:
                    print(f"\nFrom splitting ({len(by_source['split'])}):")
                    for item in by_source["split"][:10]:
                        parent = item.get("parent", "")
                        score = item.get("score", 1.0)
                        print(f"  → {item['word']:25s} (split from '{parent}', score: {score:.3f})")

                # Display inflections
                if by_source["inflection"]:
                    print(f"\nFrom inflection ({len(by_source['inflection'])}):")
                    for item in by_source["inflection"][:15]:
                        parent = item.get("parent", "")
                        score = item.get("score", 1.0)
                        print(
                            f"  ~ {item['word']:25s} (inflection of '{parent}', score: {score:.3f})"
                        )
                    if len(by_source["inflection"]) > 15:
                        print(f"  ... and {len(by_source['inflection']) - 15} more")

                # Display embeddings (semantic expansion)
                if by_source["embedding"]:
                    print(
                        f"\nFrom semantic expansion ({len(by_source['embedding'])}) [extraction × similarity]:"
                    )
                    for item in by_source["embedding"][:15]:
                        score = item.get("score", 0)
                        parent = item.get("parent", "")
                        print(
                            f"  + {item['word']:25s} (similar to '{parent}', final score: {score:.3f})"
                        )
                    if len(by_source["embedding"]) > 15:
                        print(f"  ... and {len(by_source['embedding']) - 15} more")

                # Display embedding inflections
                if by_source["embedding_inflection"]:
                    print(
                        f"\nFrom semantic expansion inflections ({len(by_source['embedding_inflection'])}) [inherits final score]:"
                    )
                    for item in by_source["embedding_inflection"][:10]:
                        score = item.get("score", 0)
                        parent = item.get("parent", "")
                        print(
                            f"  ≈ {item['word']:25s} (inflection of '{parent}', final score: {score:.3f})"
                        )
                    if len(by_source["embedding_inflection"]) > 10:
                        print(f"  ... and {len(by_source['embedding_inflection']) - 10} more")

                # Show statistics
                print("\n📊 STATISTICS:")
                print("-" * 70)
                print(f"  • Extracted: {len(extracted_keywords)} keywords")
                print(f"  • Expanded:  {len(expanded)} keywords")
                expansion_ratio = (
                    len(expanded) / len(extracted_keywords) if extracted_keywords else 0
                )
                print(f"  • Ratio:     {expansion_ratio:.1f}x expansion")
                print("\n  Breakdown by source:")
                print(f"    - Original:               {len(by_source['original'])}")
                print(f"    - Split:                  {len(by_source['split'])}")
                print(f"    - Inflections:            {len(by_source['inflection'])}")
                print(f"    - Semantic (embeddings):  {len(by_source['embedding'])}")
                print(f"    - Semantic inflections:   {len(by_source['embedding_inflection'])}")

                # Show expansion info
                info = expander.get_expansion_info()
                if "embedding_vocab_size" in info:
                    print("\n🧠 Model Info:")
                    print(f"  • Vocabulary size: {info['embedding_vocab_size']:,}")
                    print(f"  • Vector dimensions: {info['embedding_vector_size']}")

                # Show complete sorted list of all keywords with scores
                if expanded_with_scores:
                    print("\n📋 ALL EXPANDED KEYWORDS (sorted by score):")
                    print("-" * 70)
                    # Sort by score descending
                    sorted_keywords = sorted(
                        expanded_with_scores, key=lambda x: x.get("score", 0), reverse=True
                    )
                    # Show top 50
                    for i, item in enumerate(sorted_keywords[:50], 1):
                        word = item["word"]
                        score = item.get("score", 0)
                        print(f"  {i:3}. {word:25s} (score: {score:.4f})")
                    if len(sorted_keywords) > 50:
                        print(f"\n  ... and {len(sorted_keywords) - 50} more keywords")
                        print(
                            f"  Score range: {sorted_keywords[-1].get('score', 0):.4f} - {sorted_keywords[0].get('score', 0):.4f}"
                        )

            except Exception as e:
                print(f"\n❌ Error in pipeline: {e}", file=sys.stderr)
                import traceback

                traceback.print_exc()

            print("\n" + "=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n👋 Exiting interactive mode. Goodbye!")
        sys.exit(0)


def run_keywords_interactive(method: str = "regular", extraction_threshold: float | None = None):
    """
    Interactive keyword extraction testing mode.

    Allows users to paste text and see extracted keywords in real-time
    using the specified extraction method.

    Args:
        method: Extraction method ('regular')
        extraction_threshold: Minimum score for extraction (None = no filtering)
    """
    print(f"\n{'='*70}")
    print("🔍 Cicada Interactive Keyword Extraction Test")
    print(f"{'='*70}")

    # Map extraction method to display name
    method_display = "REGULAR (token-based)"
    print(f"Method: {method_display}")
    if extraction_threshold is not None:
        print(f"Extraction threshold: {extraction_threshold}")
    print("\nPaste or type text, then press Ctrl-D (Unix) or Ctrl-Z+Enter (Windows)")
    print("to extract keywords. Press Ctrl-C to exit.\n")
    print(f"{'='*70}\n")

    # Initialize keyword extractor
    try:
        if method != "regular":
            raise ValueError(f"Unknown extraction method: {method} (only 'regular' is supported)")

        from cicada.extractors.keyword import RegularKeywordExtractor

        extractor = RegularKeywordExtractor(verbose=True)
        print()  # Add newline after initialization
    except Exception as e:
        print(f"Error initializing keyword extractor: {e}", file=sys.stderr)
        sys.exit(1)

    # Interactive loop
    stdin_closed = False
    try:
        while True:
            print("📝 Enter text (Ctrl-D or Ctrl-Z+Enter when done):")
            print("-" * 70)

            # Read multi-line input until EOF
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                # Check if this is the first EOF (stdin just closed)
                if not lines and stdin_closed:
                    # stdin is exhausted and we have no input - exit gracefully
                    print("\n👋 No more input available. Exiting.")
                    return
                stdin_closed = True

            text = "\n".join(lines)

            if not text.strip():
                # If stdin is closed and input is empty, exit
                if stdin_closed:
                    print("\n👋 No more input available. Exiting.")
                    return
                print("\n⚠️  Empty input. Please enter some text.\n")
                continue

            # Extract keywords
            print("\n" + "=" * 70)
            print("🔑 EXTRACTED KEYWORDS:")
            print("=" * 70)

            try:
                # Get detailed results
                results = extractor.extract_keywords(text, top_n=15)

                # Display top keywords with scores
                top_keywords = results.get("top_keywords", [])

                # Apply extraction threshold if specified
                if extraction_threshold is not None and top_keywords:
                    filtered_keywords = [
                        item
                        for item in top_keywords
                        if isinstance(item, (list, tuple))
                        and len(item) >= 2
                        and item[1] >= extraction_threshold
                    ]
                    if len(filtered_keywords) < len(top_keywords):
                        removed_count = len(top_keywords) - len(filtered_keywords)
                        print(
                            f"\n⚠️  Filtered out {removed_count} keywords below threshold {extraction_threshold}"
                        )
                    top_keywords = filtered_keywords

                # Get code identifiers and split words for boost detection
                code_identifiers = results.get("code_identifiers", [])
                code_split_words = results.get("code_split_words", [])
                code_identifiers_lower = [ident.lower() for ident in code_identifiers]
                code_split_words_lower = [word.lower() for word in code_split_words]

                if top_keywords and isinstance(top_keywords, list):
                    print("\n📊 Top Keywords (with weighted scores):")
                    for i, item in enumerate(top_keywords, 1):
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            keyword, score = item[0], item[1]

                            # Determine if this keyword was boosted
                            boost_label = ""
                            if keyword.lower() in code_identifiers_lower:
                                boost_label = " [10x boost]"
                            elif keyword.lower() in code_split_words_lower:
                                boost_label = " [3x boost]"

                            print(f"  {i:2}. {keyword:20s} (score: {score:.4f}){boost_label}")
                else:
                    print("  No keywords extracted.")

                # Display code identifiers if any
                if code_identifiers and isinstance(code_identifiers, list):
                    print(f"\n💻 Code Identifiers ({len(code_identifiers)} found, 10x weight):")
                    for ident in code_identifiers[:10]:
                        print(f"  • {ident}")
                    if len(code_identifiers) > 10:
                        print(f"  ... and {len(code_identifiers) - 10} more")

                # Display code split words if any
                if code_split_words and isinstance(code_split_words, list):
                    print(f"\n🔤 Code Split Words ({len(code_split_words)} found, 3x weight):")
                    for word in code_split_words[:10]:  # Limit to 10
                        print(f"  • {word}")
                    if len(code_split_words) > 10:
                        print(f"  ... and {len(code_split_words) - 10} more")

                # Display statistics
                stats = results.get("stats")
                if stats and isinstance(stats, dict):
                    print("\n📈 Statistics:")
                    print(f"  • Total tokens: {stats.get('total_tokens', 0)}")
                    print(f"  • Total words: {stats.get('total_words', 0)}")
                    print(f"  • Unique words: {stats.get('unique_words', 0)}")
                    if "sentences" in stats:
                        print(f"  • Sentences: {stats['sentences']}")

            except Exception as e:
                print(f"\n❌ Error extracting keywords: {e}", file=sys.stderr)

            print("\n" + "=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n👋 Exiting interactive mode. Goodbye!")
        sys.exit(0)
