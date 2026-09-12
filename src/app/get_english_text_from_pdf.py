import fitz
import re
import json
from pathlib import Path
from typing import Optional


# ============================================================
# Configuration
# ============================================================

PDF_PATH = Path("data/sadany_khalifa.pdf")
OUTPUT_PATH = Path("data/egyptian_civil_code_articles_en.json")


# ============================================================
# Arabic helpers
# ============================================================

ARABIC_RANGES = (
    ("\u0600", "\u06ff"),
    ("\u0750", "\u077f"),
    ("\u08a0", "\u08ff"),
    ("\ufb50", "\ufdff"),
    ("\ufe70", "\ufeff"),
)


def is_arabic_char(char: str) -> bool:
    return any(start <= char <= end for start, end in ARABIC_RANGES)


def arabic_char_count(text: str) -> int:
    return sum(is_arabic_char(c) for c in text)


def latin_char_count(text: str) -> int:
    return sum(("A" <= c <= "Z") or ("a" <= c <= "z") for c in text)


def contains_arabic(text: str) -> bool:
    return arabic_char_count(text) > 0


def is_mostly_english(text: str, threshold: float = 0.65) -> bool:
    """
    Returns True when the meaningful alphabetic characters
    are predominantly Latin/English.
    """
    arabic = arabic_char_count(text)
    latin = latin_char_count(text)

    total = arabic + latin

    if total == 0:
        return False

    return latin / total >= threshold


def is_mostly_arabic(text: str, threshold: float = 0.50) -> bool:
    arabic = arabic_char_count(text)
    latin = latin_char_count(text)

    total = arabic + latin

    if total == 0:
        return False

    return arabic / total >= threshold


# ============================================================
# Text normalization
# ============================================================


def normalize_text(text: str) -> str:
    """
    Normalize PDF-extracted text without destroying useful
    paragraph boundaries.
    """
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    # Normalize various dash characters
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("-", "-")

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def clean_multiline_text(lines: list[str]) -> str:
    """
    Join extracted English lines while preserving paragraph-ish
    structure.
    """
    cleaned = []

    for line in lines:
        line = normalize_text(line)

        if not line:
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


# ============================================================
# Number normalization
# ============================================================

ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)


def normalize_number(value: str) -> int:
    value = value.translate(ARABIC_DIGITS)
    value = re.sub(r"[^\d]", "", value)

    if not value:
        raise ValueError(f"Could not parse number: {value!r}")

    return int(value)


# ============================================================
# Article detection
# ============================================================

# Normal:
# Article 1149
# Article 1149 Some text
ARTICLE_EN_RE = re.compile(
    r"^\s*Article\s+(\d+)\b(?:\s+(.*))?$",
    re.IGNORECASE,
)

# Some PDF extraction produces:
# 1149 Article
ARTICLE_EN_REVERSED = re.compile(
    r"^\s*(\d+)\s+Article\s*$",
    re.IGNORECASE,
)

# Arabic fallback:
# مادة ١١٤٩
# مادة
# ١١٤٩
ARTICLE_AR_RE = re.compile(r"^\s*مادة\s*([٠-٩0-9]+)?\s*$")


# ============================================================
# Hierarchy detection
# ============================================================

BOOK_RE = re.compile(
    r"^\s*BOOK\s+([IVXLCDM]+)\s*$",
    re.IGNORECASE,
)

CHAPTER_RE = re.compile(
    r"^\s*CHAPTER\s+([IVXLCDM]+)\s*$",
    re.IGNORECASE,
)

SECTION_RE = re.compile(
    r"^\s*SECTION\s+([IVXLCDM]+)\s*\.?\s*(.*)$",
    re.IGNORECASE,
)

PART_RE = re.compile(
    r"^\s*(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+PART\s*$",
    re.IGNORECASE,
)

# Examples:
#
# 1- General Privileges and Special Privileges over Movables
# 2- Special Privileges over Immovables
#
# 1. Elements of Contracts
#
NUMBERED_SUBTOPIC_RE = re.compile(r"^\s*(\d+)\s*[-.]\s*(.+?)\s*$")


# ============================================================
# Repealed ranges
# ============================================================

REPEALED_RANGE_RE = re.compile(
    r"Articles?\s+(\d+)\s*-\s*(\d+)\s+repealed",
    re.IGNORECASE,
)

REPEALED_SINGLE_RE = re.compile(
    r"Article\s+(\d+)\s+repealed",
    re.IGNORECASE,
)


# ============================================================
# Line extraction
# ============================================================


def extract_page_lines(page: fitz.Page) -> list[str]:
    """
    Extract text lines in their natural PDF reading order.

    We use blocks rather than page.get_text("text") because blocks
    preserve the relationship between Arabic and English sections
    more reliably.
    """

    blocks = page.get_text("blocks")

    # block tuple:
    # x0, y0, x1, y1, text, block_no, block_type
    blocks = sorted(
        blocks,
        key=lambda b: (round(b[1], 2), round(b[0], 2)),
    )

    lines = []

    for block in blocks:
        block_type = block[6]

        # Ignore images
        if block_type != 0:
            continue

        block_text = block[4]

        for raw_line in block_text.splitlines():
            line = normalize_text(raw_line)

            if line:
                lines.append(line)

    return lines


# ============================================================
# Heading helpers
# ============================================================


def looks_like_heading(text: str) -> bool:
    """
    Conservative heading detector.

    This intentionally does NOT classify arbitrary English text
    as a heading.
    """

    if not text:
        return False

    if contains_arabic(text):
        return False

    if not is_mostly_english(text):
        return False

    # Avoid treating long legal paragraphs as headings.
    if len(text) > 140:
        return False

    return True


def combine_heading_lines(
    lines: list[str],
    start_index: int,
    max_lines: int = 3,
) -> tuple[str, int]:
    """
    Collect a heading that may be split across multiple PDF lines.

    Example:

        2- Special Privileges over
        Immovables

    becomes:

        2- Special Privileges over Immovables
    """

    collected = []

    i = start_index

    while i < len(lines) and len(collected) < max_lines:
        candidate = normalize_text(lines[i])

        if not candidate:
            i += 1
            continue

        if not looks_like_heading(candidate):
            break

        # Never absorb another structural element or article.
        if (
            BOOK_RE.match(candidate)
            or CHAPTER_RE.match(candidate)
            or SECTION_RE.match(candidate)
            or ARTICLE_EN_RE.match(candidate)
            or ARTICLE_EN_REVERSED.match(candidate)
        ):
            break

        collected.append(candidate)
        i += 1

        # Usually one or two lines are enough.
        if candidate.endswith((".", ":")):
            break

    return " ".join(collected).strip(), i


# ============================================================
# Hierarchy state
# ============================================================


class Hierarchy:
    def __init__(self):
        self.book: Optional[str] = None
        self.chapter: Optional[str] = None
        self.section: Optional[str] = None
        self.subtopic: Optional[str] = None

        # Temporary state used when a structural heading's
        # title appears on the following line.
        self.pending_book = False
        self.pending_chapter = False
        self.pending_section = False

        # Used for Arabic heading followed by English heading.
        self.pending_arabic_structure = None

    def reset_after_book(self):
        self.chapter = None
        self.section = None
        self.subtopic = None

    def reset_after_chapter(self):
        self.section = None
        self.subtopic = None

    def reset_after_section(self):
        self.subtopic = None


# ============================================================
# Structural heading parsing
# ============================================================


def parse_structural_heading(
    lines: list[str],
    index: int,
    hierarchy: Hierarchy,
) -> Optional[int]:
    """
    Process a structural English heading at `index`.

    Returns the next index when a heading was consumed,
    otherwise None.
    """

    line = normalize_text(lines[index])

    # --------------------------------------------------------
    # BOOK
    # --------------------------------------------------------

    match = BOOK_RE.match(line)

    if match:
        roman = match.group(1).upper()

        # Try to get the English title immediately after BOOK.
        title = None
        next_index = index + 1

        while next_index < len(lines):
            candidate = normalize_text(lines[next_index])

            if not candidate:
                next_index += 1
                continue

            if (
                ARTICLE_EN_RE.match(candidate)
                or ARTICLE_EN_REVERSED.match(candidate)
                or BOOK_RE.match(candidate)
                or CHAPTER_RE.match(candidate)
                or SECTION_RE.match(candidate)
            ):
                break

            if is_mostly_english(candidate) and len(candidate) <= 120:
                title = candidate
                next_index += 1

            break

        if title:
            hierarchy.book = f"BOOK {roman} - {title}"
        else:
            hierarchy.book = f"BOOK {roman}"

        hierarchy.reset_after_book()

        return next_index

    # --------------------------------------------------------
    # CHAPTER
    # --------------------------------------------------------

    match = CHAPTER_RE.match(line)

    if match:
        roman = match.group(1).upper()

        title = None
        next_index = index + 1

        while next_index < len(lines):
            candidate = normalize_text(lines[next_index])

            if not candidate:
                next_index += 1
                continue

            if (
                ARTICLE_EN_RE.match(candidate)
                or ARTICLE_EN_REVERSED.match(candidate)
                or BOOK_RE.match(candidate)
                or CHAPTER_RE.match(candidate)
                or SECTION_RE.match(candidate)
            ):
                break

            if is_mostly_english(candidate) and len(candidate) <= 120:
                title = candidate
                next_index += 1

            break

        if title:
            hierarchy.chapter = f"Chapter {roman} - {title}"
        else:
            hierarchy.chapter = f"Chapter {roman}"

        hierarchy.reset_after_chapter()

        return next_index

    # --------------------------------------------------------
    # SECTION
    # --------------------------------------------------------

    match = SECTION_RE.match(line)

    if match:
        roman = match.group(1).upper()
        inline_title = normalize_text(match.group(2))

        if inline_title:
            hierarchy.section = f"Section {roman} - {inline_title}"
            hierarchy.reset_after_section()
            return index + 1

        # Section title may be on the next English line.
        title = None
        next_index = index + 1

        while next_index < len(lines):
            candidate = normalize_text(lines[next_index])

            if not candidate:
                next_index += 1
                continue

            if (
                ARTICLE_EN_RE.match(candidate)
                or ARTICLE_EN_REVERSED.match(candidate)
                or BOOK_RE.match(candidate)
                or CHAPTER_RE.match(candidate)
                or SECTION_RE.match(candidate)
            ):
                break

            if is_mostly_english(candidate) and len(candidate) <= 120:
                title = candidate
                next_index += 1

            break

        if title:
            hierarchy.section = f"Section {roman} - {title}"
        else:
            hierarchy.section = f"Section {roman}"

        hierarchy.reset_after_section()

        return next_index

    return None


# ============================================================
# Subtopic parsing
# ============================================================


def parse_numbered_subtopic(
    lines: list[str],
    index: int,
    hierarchy: Hierarchy,
) -> Optional[int]:
    line = normalize_text(lines[index])

    match = NUMBERED_SUBTOPIC_RE.match(line)

    if not match:
        return None

    number = match.group(1)
    title = match.group(2).strip()

    # We only want English numbered headings.
    if not is_mostly_english(line):
        return None

    # Article references such as "1- Article 200..." are not
    # headings.
    if re.search(r"\bArticle\s+\d+\b", title, re.IGNORECASE):
        return None

    # Collect a continuation line if it is clearly part of
    # the heading.
    next_index = index + 1

    continuation = []

    while next_index < len(lines):
        candidate = normalize_text(lines[next_index])

        if not candidate:
            next_index += 1
            continue

        if (
            ARTICLE_EN_RE.match(candidate)
            or ARTICLE_EN_REVERSED.match(candidate)
            or BOOK_RE.match(candidate)
            or CHAPTER_RE.match(candidate)
            or SECTION_RE.match(candidate)
            or NUMBERED_SUBTOPIC_RE.match(candidate)
        ):
            break

        if is_mostly_english(candidate) and len(candidate) <= 100:
            continuation.append(candidate)
            next_index += 1

        break

    if continuation:
        title = f"{title} {' '.join(continuation)}"

    hierarchy.subtopic = f"{number}- {title}"

    return next_index


# ============================================================
# Article extraction
# ============================================================


def parse_article_header(
    line: str,
) -> Optional[tuple[int, str]]:
    """
    Returns:

        (article_number, text_after_header)

    or None.
    """

    match = ARTICLE_EN_RE.match(line)

    if match:
        number = int(match.group(1))
        remainder = normalize_text(match.group(2) or "")

        return number, remainder

    match = ARTICLE_EN_REVERSED.match(line)

    if match:
        number = int(match.group(1))
        return number, ""

    return None


# ============================================================
# Main parser
# ============================================================


def parse_pdf(pdf_path: Path) -> list[dict]:
    doc = fitz.open(pdf_path)

    articles = []

    hierarchy = Hierarchy()

    current_article = None
    current_article_lines = []
    current_article_page = None

    # Arabic article marker waiting for its English counterpart.
    pending_arabic_article_number = None

    # Repealed article numbers.
    repealed_articles = set()

    # --------------------------------------------------------
    # First pass: extract pages
    # --------------------------------------------------------

    pages = []

    for page_number, page in enumerate(doc, start=1):
        lines = extract_page_lines(page)
        pages.append((page_number, lines))

    # --------------------------------------------------------
    # Second pass: parse document
    # --------------------------------------------------------

    def finalize_article():
        nonlocal current_article
        nonlocal current_article_lines
        nonlocal current_article_page

        if current_article is None:
            return

        text_en = clean_multiline_text(current_article_lines)

        if not text_en:
            current_article = None
            current_article_lines = []
            current_article_page = None
            return

        article_number = current_article

        article = {
            "article_number": article_number,
            "book": hierarchy.book,
            "chapter": hierarchy.chapter,
            "section": hierarchy.section,
            "subtopic": hierarchy.subtopic,
            "text_en": text_en,
            "is_repealed": (article_number in repealed_articles),
            "source_page": current_article_page,
            "citation": (f"Egyptian Civil Code, Article " f"{article_number}"),
        }

        articles.append(article)

        current_article = None
        current_article_lines = []
        current_article_page = None

    # --------------------------------------------------------
    # Walk every page
    # --------------------------------------------------------

    for page_number, lines in pages:
        i = 0

        while i < len(lines):
            line = normalize_text(lines[i])

            if not line:
                i += 1
                continue

            # =================================================
            # Repealed range
            # =================================================

            match = REPEALED_RANGE_RE.search(line)

            if match:
                start = int(match.group(1))
                end = int(match.group(2))

                repealed_articles.update(range(start, end + 1))

                i += 1
                continue

            match = REPEALED_SINGLE_RE.search(line)

            if match:
                repealed_articles.add(int(match.group(1)))

                i += 1
                continue

            # =================================================
            # English article header
            # =================================================

            article_header = parse_article_header(line)

            if article_header:
                article_number, remainder = article_header

                # Finalize previous article.
                finalize_article()

                current_article = article_number
                current_article_lines = []
                current_article_page = page_number

                # If text follows "Article N" on same line,
                # preserve it.
                if remainder:
                    current_article_lines.append(remainder)

                pending_arabic_article_number = None

                i += 1
                continue

            # =================================================
            # Arabic article marker
            #
            # Do NOT immediately start an article.
            #
            # In this PDF the Arabic marker normally comes
            # before the English "Article N", so we wait for
            # the English marker.
            # =================================================

            arabic_match = ARTICLE_AR_RE.match(line)

            if arabic_match:
                number_text = arabic_match.group(1)

                if number_text:
                    pending_arabic_article_number = normalize_number(
                        number_text
                    )

                i += 1
                continue

            # =================================================
            # Structural headings
            # =================================================

            structural_next = parse_structural_heading(
                lines,
                i,
                hierarchy,
            )

            if structural_next is not None:
                # Structural headings terminate any accidental
                # article collection.
                finalize_article()

                i = structural_next
                continue

            # =================================================
            # Numbered subtopic
            # =================================================

            subtopic_next = parse_numbered_subtopic(
                lines,
                i,
                hierarchy,
            )

            if subtopic_next is not None:
                # Do not terminate a currently open article
                # unless the heading occurs outside article text.
                if current_article is None:
                    i = subtopic_next
                    continue

                # A heading after an article normally means the
                # article has ended.
                finalize_article()

                i = subtopic_next
                continue

            # =================================================
            # English text
            # =================================================

            if current_article is not None:
                # Only retain English text.
                #
                # This is deliberately based on script ratio,
                # rather than:
                #
                #     if not contains_arabic(...)
                #
                # because PDF extraction can occasionally mix
                # punctuation and characters.
                if is_mostly_english(line):
                    current_article_lines.append(line)

            i += 1

    # Final article.
    finalize_article()

    doc.close()

    return articles


# ============================================================
# Validation
# ============================================================


def validate_articles(articles: list[dict]):
    numbers = [article["article_number"] for article in articles]

    print("\n========== VALIDATION ==========")

    print(f"Extracted articles : {len(articles)}")

    if numbers:
        print(f"First article      : {min(numbers)}")
        print(f"Last article       : {max(numbers)}")

    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})

    if duplicates:
        print(
            "Duplicate articles:",
            duplicates,
        )
    else:
        print("Duplicate articles: none")

    # Show gaps.
    if numbers:
        expected = set(
            range(
                min(numbers),
                max(numbers) + 1,
            )
        )

        missing = sorted(expected - set(numbers))

        # The PDF intentionally contains repealed ranges.
        # We still display the gaps so they can be inspected.
        if missing:
            print(
                "Missing article numbers:",
                missing,
            )
        else:
            print("Missing article numbers: none")


# ============================================================
# Hierarchy debugging
# ============================================================


def print_hierarchy_samples(
    articles: list[dict],
    article_numbers: list[int],
):
    print("\n========== HIERARCHY SAMPLES ==========")

    lookup = {article["article_number"]: article for article in articles}

    for number in article_numbers:
        article = lookup.get(number)

        if not article:
            print(f"\nArticle {number}: NOT FOUND")
            continue

        print(f"\nArticle {number}")

        print(
            "  Book    :",
            article["book"],
        )

        print(
            "  Chapter :",
            article["chapter"],
        )

        print(
            "  Section :",
            article["section"],
        )

        print(
            "  Subtopic:",
            article["subtopic"],
        )

        print(
            "  Page    :",
            article["source_page"],
        )

        print("  Text    :", article["text_en"][:250], "...")


# ============================================================
# JSON output
# ============================================================


def save_json(
    articles: list[dict],
    output_path: Path,
):
    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            articles,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nJSON written to: {output_path}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    articles = parse_pdf(PDF_PATH)

    validate_articles(articles)

    print_hierarchy_samples(
        articles,
        [
            1,
            89,
            303,
            418,
            646,
            798,
            802,
            1030,
            1111,
            1130,
            1137,
            1141,
            1147,
            1148,
            1149,
        ],
    )

    save_json(
        articles,
        OUTPUT_PATH,
    )
