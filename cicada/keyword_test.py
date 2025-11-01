"""
Interactive keyword extraction testing module.

Provides an interactive REPL for testing keyword extraction methods.
"""

import sys


def run_keywords_interactive(method: str = "lemminflect", tier: str = "regular"):
    """
    Interactive keyword extraction testing mode.

    Allows users to paste text and see extracted keywords in real-time
    using the specified extraction method.

    Args:
        method: Extraction method ('lemminflect' or 'bert')
        tier: Model tier ('fast', 'regular', or 'max')
    """
    print(f"\n{'='*70}")
    print("🔍 Cicada Interactive Keyword Extraction Test")
    print(f"{'='*70}")
    print(f"Method: {method.upper()}")
    print(f"Tier: {tier}")
    print("\nPaste or type text, then press Ctrl-D (Unix) or Ctrl-Z+Enter (Windows)")
    print("to extract keywords. Press Ctrl-C to exit.\n")
    print(f"{'='*70}\n")

    # Initialize keyword extractor
    try:
        if method == "bert":
            from cicada.keybert_extractor import KeyBERTExtractor

            extractor = KeyBERTExtractor(model_tier=tier, verbose=True)
        else:
            from cicada.lightweight_keyword_extractor import LightweightKeywordExtractor

            extractor = LightweightKeywordExtractor(verbose=True)
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
                if top_keywords and isinstance(top_keywords, list):
                    print("\n📊 Top Keywords (with scores):")
                    for i, item in enumerate(top_keywords, 1):
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            keyword, score = item[0], item[1]
                            print(f"  {i:2}. {keyword:20s} (score: {score:.4f})")
                else:
                    print("  No keywords extracted.")

                # Display code identifiers if any
                code_identifiers = results.get("code_identifiers")
                if code_identifiers and isinstance(code_identifiers, list):
                    print("\n💻 Code Identifiers (10x weight):")
                    for ident in code_identifiers:
                        print(f"  • {ident}")

                # Display code split words if any
                code_split_words = results.get("code_split_words")
                if code_split_words and isinstance(code_split_words, list):
                    print("\n🔤 Code Split Words (3x weight):")
                    for word in code_split_words[:10]:  # Limit to 10
                        print(f"  • {word}")

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
