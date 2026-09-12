import os
import json
import unicodedata
from pathlib import Path

from lxml import html


# ============================================================
# Configuration
# ============================================================

DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
    "data",
)

OUTPUT_FILE = Path(DATA_DIR, "egyptian_civil_law_131_1948.json")

FILE_PATH = Path(DATA_DIR, "egyptian_civil_law_131_1948.html")


# ============================================================
# XPath definitions
# ============================================================

XPATH_ALL_ELEMENTS = (
    "//div[contains(@class, " "'facts_title_wrap_change_bg1')]"
)

XPATH_LAW_NUM = "./div[@class='box']/div[@class='ribbon-2']"

XPATH_LAW_CONTENT = "./div[@class='box']/p[@class='original_text']"

XPATH_LAW_CONTENT_REPEALED = "./div[@class='box']/p[@class='text_final']"

XPATH_LAW_HEAD_REPEALED = "./div[@class='box']/h3[@class='title_final'][2]"

XPATH_LAW_TITLE = (
    "./div/h3[@class='title-comm']" "/span[@class='title-holder']"
)


# ============================================================
# Text normalization
# ============================================================


def normalize_arabic_text(text):
    """
    Normalize Arabic Unicode text without changing its
    logical RTL character order.

    Important:
        - Does NOT reverse the string.
        - Does NOT reshape Arabic characters.
        - Does NOT convert Arabic-Indic numerals.
        - Preserves Unicode Arabic text for LLM processing.
    """

    if not text:
        return ""

    # Unicode canonical normalization.
    #
    # This makes visually identical Unicode representations
    # consistent where possible.
    text = unicodedata.normalize("NFC", text)

    # Normalize whitespace.
    #
    # This converts sequences of spaces/newlines/tabs into
    # a single space.
    text = " ".join(text.split())

    return text.strip()


# ============================================================
# Optional digit normalization
# ============================================================


def convert_arabic_indic_digits(text):
    """
    Optional:
        ١٢٣٤٥٦٧٨٩٠ -> 1234567890

    Currently NOT used because preserving the original
    legal text is preferable for the training dataset.
    """

    translation_table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

    return text.translate(translation_table)


def convert_persian_digits(text):
    """
    Optional:
        ۱۲۳۴۵۶۷۸۹۰ -> 1234567890

    Currently NOT used.
    """

    translation_table = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

    return text.translate(translation_table)


# ============================================================
# Helper functions
# ============================================================
def convert_to_arabic_indic_digits(text):
    if not text:
        return ""

    translation_table = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

    return text.translate(translation_table)


def get_text(element):
    if element is None:
        return ""

    text = element.text_content()

    text = unicodedata.normalize("NFC", text)

    text = " ".join(text.split())

    text = convert_to_arabic_indic_digits(text)

    return text.strip()


def get_first_text(element, xpath):
    """
    Return the text of the first element matching xpath.
    """

    elements = element.xpath(xpath)

    if not elements:
        return ""

    return get_text(elements[0])


# ============================================================
# Load HTML
# ============================================================


def load_page(file_path):
    """
    Parse the downloaded EastLaws HTML file.
    """

    if not file_path.exists():
        raise FileNotFoundError(f"HTML file not found: {file_path}")

    print(f"Loading: {file_path}")

    tree = html.parse(str(file_path))

    return tree


# ============================================================
# Extract laws
# ============================================================


def extract_laws(tree):
    """
    Extract law number, content and title.

    Each facts_title_wrap_change_bg1 element is treated
    independently.
    """

    all_elements = tree.xpath(XPATH_ALL_ELEMENTS)

    print(
        f"Found {len(all_elements)} " "facts_title_wrap_change_bg1 elements."
    )

    # Skip the first four non-law elements.
    laws_elements = all_elements[4:]

    laws = []
    law_title = ""

    for index, element in enumerate(laws_elements, start=1):
        # ----------------------------------------------------
        # Law number
        # ----------------------------------------------------

        law_number = get_first_text(element, XPATH_LAW_NUM)

        # ----------------------------------------------------
        # Main law content
        # ----------------------------------------------------

        law_content = get_first_text(element, XPATH_LAW_CONTENT)

        # ----------------------------------------------------
        # Law title
        # ----------------------------------------------------
        title = get_first_text(element, XPATH_LAW_TITLE)
        if title != "":
            law_title = title

        # ----------------------------------------------------
        # Repealed content
        # ----------------------------------------------------

        law_head_repealed = get_first_text(element, XPATH_LAW_HEAD_REPEALED)

        law_content_repealed = get_first_text(
            element, XPATH_LAW_CONTENT_REPEALED
        )

        # If this article has repealed/replaced content,
        # append it to the original content.
        if law_head_repealed and law_content_repealed:
            law_content = (
                f"{law_content}\n\n"
                f"{law_head_repealed}\n"
                f"{law_content_repealed}"
            )

            law_content = normalize_arabic_text(law_content)

        # ----------------------------------------------------
        # Create record
        # ----------------------------------------------------

        laws.append(
            {
                "law_number": law_number,
                "content": law_content,
                "title": law_title,
            }
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if index % 100 == 0:
            print(f"Processed {index} laws...")

    return laws


# ============================================================
# Save JSON
# ============================================================


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


# ============================================================
# Main
# ============================================================


def main():
    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    tree = load_page(FILE_PATH)

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    laws = extract_laws(tree)

    print()
    print(f"Extracted {len(laws)} laws.")

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_json(OUTPUT_FILE, laws)

    print(f"Saved JSON to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
