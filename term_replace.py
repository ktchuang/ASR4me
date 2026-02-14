#!/usr/bin/env python3
"""Replace keywords in text based on a CSV mapping file."""

import argparse
import csv
import os


def apply_replacements(keywords_file: str, text: str) -> str:
    """Read a CSV mapping file and apply all replacements to *text*.

    If the keywords file does not exist or is empty, returns *text* unchanged.
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
    parser = argparse.ArgumentParser(description="Replace keywords in text using a CSV mapping file.")
    parser.add_argument("keywords_file", help="CSV file with orig_keyword,new_keyword per line")
    parser.add_argument("orig_content", help="Text to perform replacements on")
    args = parser.parse_args()

    print(apply_replacements(args.keywords_file, args.orig_content))


if __name__ == "__main__":
    main()
