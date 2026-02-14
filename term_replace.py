#!/usr/bin/env python3
"""Replace keywords in text based on a CSV mapping file.

This module provides both an importable function (``apply_replacements``)
and a CLI entry point.  It is used by server.py to post-process LLM output
with per-user term replacements, and can also be invoked standalone:

    python term_replace.py keywords.txt "some text to process"

CSV format (one replacement per line):
    original_keyword,replacement_keyword
"""

import argparse
import csv
import os


def apply_replacements(keywords_file: str, text: str) -> str:
    """Apply all keyword replacements defined in *keywords_file* to *text*.

    Each line in the CSV file maps an original term to its replacement::

        人工智慧,人工智能
        OpenAi,OpenAI

    Replacements are applied sequentially in file order using simple string
    substitution, so earlier replacements may affect later ones.

    Args:
        keywords_file: Path to a CSV file with ``orig,new`` rows.
        text: The input text to transform.

    Returns:
        The text after all replacements.  If *keywords_file* does not exist
        or contains no valid rows, *text* is returned unchanged.
    """
    if not os.path.isfile(keywords_file):
        return text

    with open(keywords_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        replacements = [(row[0], row[1]) for row in reader if len(row) >= 2]

    result = text
    for orig, new in replacements:
        result = result.replace(orig, new)

    return result


def main():
    """CLI entry point: read a keywords CSV and apply replacements to text.

    Usage:
        python term_replace.py <keywords_file> <orig_content>

    Prints the transformed text to stdout.
    """
    parser = argparse.ArgumentParser(
        description="Replace keywords in text using a CSV mapping file.",
    )
    parser.add_argument("keywords_file", help="CSV file with orig_keyword,new_keyword per line")
    parser.add_argument("orig_content", help="Text to perform replacements on")
    args = parser.parse_args()

    print(apply_replacements(args.keywords_file, args.orig_content))


if __name__ == "__main__":
    main()
