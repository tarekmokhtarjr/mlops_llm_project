#!/usr/bin/env python3
"""
Extract Articles from Egypt's Civil Code (Law No. 131 of 1948) PDF.

Input:
    Law-no-131-of-1948.pdf

Output:
    egyptian_civil_code_131.json

Each article has:
    article_number, book, chapter, section, topic, text_en,
    is_repealed, source_page, citation

Dependency:
    pip install pymupdf
"""

import argparse
import json
import re
from pathlib import Path

import fitz  # PyMuPDF


ARTICLE_RE = re.compile(
    r"^\s*Article\s*\(\s*(\d+)\s*\)\s*:\s*(.*)$",
    re.IGNORECASE,
)

PART_RE = re.compile(r"^\s*Part\s+(?:One|Two|Three|Four|Five|\d+)\s*:\s*(.+?)\s*$", re.I)
BOOK_RE = re.compile(r"^\s*Book\s+(?:One|Two|Three|Four|Five|\d+)\s*:\s*(.+?)\s*$", re.I)
CHAPTER_RE = re.compile(r"^\s*Chapter\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|\d+)\s*:\s*(.+?)\s*$", re.I)
SECTION_RE = re.compile(r"^\s*Section\s+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|\d+)\s*:\s*(.+?)\s*$", re.I)
NUMBERED_TOPIC_RE = re.compile(r"^\s*\d+\s*[-–—]\s*(.+?)\s*$")


def clean_line(line: str) -> str:
    """Normalize PDF line noise without changing the legal wording."""
    line = line.replace("\u00ad", "")  # soft hyphen
    line = line.replace("\u2011", "-")
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def clean_text(lines):
    """
    Join PDF-wrapped lines into readable paragraphs while preserving bullet
    markers and article text. Repeated page labels are removed.
    """
    out = []
    for line in lines:
        line = clean_line(line)
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        if re.fullmatch(r"Page\s*\|\s*\d+", line, re.I):
            continue
        out.append(line)

    # Collapse excessive blank lines.
    result = []
    for line in out:
        if line == "" and (not result or result[-1] == ""):
            continue
        result.append(line)

    # Join ordinary wrapped lines. Keep bullets as separate lines.
    paragraphs = []
    current = ""

    for line in result:
        if line == "":
            if current:
                paragraphs.append(current)
                current = ""
            paragraphs.append("")
            continue

        is_bullet = bool(re.match(r"^[•●▪◦*-]\s+", line))
        if is_bullet:
            if current:
                paragraphs.append(current)
                current = ""
            paragraphs.append(line)
            continue

        if not current:
            current = line
        else:
            # Preserve a space between PDF lines; do not alter wording.
            current += " " + line

    if current:
        paragraphs.append(current)

    # Reconstruct with paragraphs separated by newlines.
    text = "\n".join(paragraphs)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def structural_match(line):
    """
    Return (field, value) for a recognized hierarchy heading.
    Part is intentionally not emitted because the requested JSON schema
    starts at Book.
    """
    for field, regex in (
        ("book", BOOK_RE),
        ("chapter", CHAPTER_RE),
        ("section", SECTION_RE),
    ):
        m = regex.match(line)
        if m:
            return field, m.group(1).strip()

    m = NUMBERED_TOPIC_RE.match(line)
    if m:
        return "topic", m.group(1).strip()

    return None, None


def is_likely_unnumbered_topic(line):
    """
    Detect headings such as 'General Provisions' and 'Definition of Mortgage'.
    These occur as short standalone headings between a section/chapter heading
    and the next Article in the supplied PDF.

    This deliberately uses conservative heuristics to avoid treating normal
    article text as a topic.
    """
    if not line or len(line) > 90:
        return False
    if line.lower().startswith(("page|", "article ", "part ", "book ", "chapter ", "section ")):
        return False
    if re.search(r"[.;:!?]$", line):
        return False
    if re.match(r"^[•●▪◦*-]\s+", line):
        return False
    # Headings in this PDF are generally title-cased or short all-caps labels.
    words = line.split()
    if not (2 <= len(words) <= 10):
        return False
    titlecase_words = sum(
        1 for w in words
        if w[:1].isupper() or w.isupper() or w[:1].isdigit()
    )
    return titlecase_words / len(words) >= 0.60


def extract_pages(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for page_no, page in enumerate(doc, start=1):
        pages.append((page_no, page.get_text("text")))
    doc.close()
    return pages


def parse_articles(pdf_path):
    pages = extract_pages(pdf_path)

    # Current hierarchy. Part is tracked only internally; the requested output
    # does not contain a part field.
    book = None
    chapter = None
    section = None
    topic = None

    articles = []
    current = None

    for page_no, raw_text in pages:
        raw_lines = [clean_line(x) for x in raw_text.splitlines()]

        # Remove page labels and blank noise.
        raw_lines = [
            x for x in raw_lines
            if x and not re.fullmatch(r"Page\s*\|\s*\d+", x, re.I)
        ]

        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]

            # Handle hierarchy headings, including a wrapped Section heading.
            field, value = structural_match(line)

            if field is None and re.match(r"^\s*Section\b", line, re.I):
                # The PDF contains at least one section heading split over two
                # physical lines. Join the continuation if present.
                if i + 1 < len(raw_lines):
                    combined = clean_line(line + " " + raw_lines[i + 1])
                    m = SECTION_RE.match(combined)
                    if m:
                        field, value = "section", m.group(1).strip()
                        i += 1

            if field == "book":
                book = value
                # A new book starts a new chapter/section/topic hierarchy.
                chapter = None
                section = None
                topic = None
                i += 1
                continue

            if field == "chapter":
                chapter = value
                section = None
                topic = None
                i += 1
                continue

            if field == "section":
                section = value
                topic = None
                i += 1
                continue

            if field == "topic":
                topic = value
                i += 1
                continue

            # Article starts.
            m = ARTICLE_RE.match(line)
            if m:
                # Finish previous article.
                if current is not None:
                    current["text_en"] = clean_text(current.pop("_text_lines"))
                    articles.append(current)

                number = int(m.group(1))
                remainder = m.group(2).strip()

                current = {
                    "article_number": number,
                    "book": book,
                    "chapter": chapter,
                    "section": section,
                    "topic": topic,
                    "_text_lines": [],
                    "is_repealed": False,
                    "source_page": page_no,
                    "citation": f"Egyptian Civil Code, Article {number}",
                }

                if remainder:
                    current["_text_lines"].append(remainder)

                i += 1
                continue

            if current is not None:
                # Do not let repeated hierarchy headings become article text.
                # They are already processed above, but this also filters a few
                # duplicated PDF heading artifacts.
                if structural_match(line)[0] is not None:
                    i += 1
                    continue

                # Explicit repealed marker belongs to the article.
                if re.search(r"\brepealed\b", line, re.I):
                    current["is_repealed"] = True

                current["_text_lines"].append(line)

            i += 1

    if current is not None:
        current["text_en"] = clean_text(current.pop("_text_lines"))
        articles.append(current)

    # Remove accidental trailing structural text from article bodies and
    # detect repealed articles from the complete text.
    for article in articles:
        article["is_repealed"] = bool(
            article["is_repealed"]
            or re.search(r"\(\s*Repealed\b", article["text_en"], re.I)
        )

        # Normalize whitespace but keep paragraph/bullet boundaries.
        article["text_en"] = re.sub(r"[ \t]+", " ", article["text_en"])
        article["text_en"] = re.sub(r"\n{3,}", "\n\n", article["text_en"]).strip()

    # Sort by article number in case a PDF page boundary produced unusual order.
    articles.sort(key=lambda x: (x["article_number"], x["source_page"]))

    return articles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, help="Path to Law No. 131 of 1948 PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("egyptian_civil_code_131.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    articles = parse_articles(args.pdf)

    with args.output.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(articles)} articles.")
    print(f"Saved: {args.output}")
    if articles:
        print("First:", json.dumps(articles[0], ensure_ascii=False))
        print("Last :", json.dumps(articles[-1], ensure_ascii=False))


if __name__ == "__main__":
    main()