from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "question",
    "reference",
    "relevant_document_ids",
    "category",
    "difficulty",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSON array/object or newline-delimited JSON records."""
    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError(f"Input file is empty: {path}")

    try:
        parsed = json.loads(text)

        if isinstance(parsed, list):
            records = parsed
        elif isinstance(parsed, dict):
            # Also allow {"data": [...]} as a convenience.
            if isinstance(parsed.get("data"), list):
                records = parsed["data"]
            else:
                records = [parsed]
        else:
            raise ValueError("JSON input must be an object or an array.")

    except json.JSONDecodeError:
        records = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

    if not records:
        raise ValueError(f"No dataset records found in {path}")

    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Every dataset record must be a JSON object.")

    return records


def normalize_record(
    record: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    """Validate and normalize one evaluation record."""
    missing = REQUIRED_FIELDS - record.keys()
    if missing:
        raise ValueError(
            f"Record {index}: missing fields: {sorted(missing)}"
        )

    case_id = str(record["id"]).strip()
    question = str(record["question"]).strip()
    reference = str(record["reference"]).strip()
    category = str(record["category"]).strip()
    difficulty = str(record["difficulty"]).strip().lower()

    if not case_id:
        raise ValueError(f"Record {index}: id cannot be empty.")
    if not question:
        raise ValueError(f"{case_id}: question cannot be empty.")
    if not reference:
        raise ValueError(f"{case_id}: reference cannot be empty.")
    if not category:
        raise ValueError(f"{case_id}: category cannot be empty.")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"{case_id}: difficulty must be one of "
            f"{sorted(VALID_DIFFICULTIES)}."
        )

    raw_ids = record["relevant_document_ids"]
    if not isinstance(raw_ids, list):
        raise ValueError(
            f"{case_id}: relevant_document_ids must be a list."
        )

    document_ids: list[str] = []
    for document_id in raw_ids:
        normalized_id = str(document_id).strip()
        if not normalized_id:
            raise ValueError(
                f"{case_id}: relevant document IDs cannot be empty."
            )
        if normalized_id not in document_ids:
            document_ids.append(normalized_id)

    normalized = {
        "id": case_id,
        "question": question,
        "reference": reference,
        "relevant_document_ids": document_ids,
        "category": category,
        "difficulty": difficulty,
    }

    # Preserve optional reviewer notes or source metadata.
    for optional_field in ("notes", "source", "verified"):
        if optional_field in record:
            normalized[optional_field] = record[optional_field]

    return normalized


def build_dataset(
    input_path: Path,
    output_path: Path,
) -> list[dict[str, Any]]:
    raw_records = load_json_or_jsonl(input_path)

    records = [
        normalize_record(record, index)
        for index, record in enumerate(raw_records, start=1)
    ]

    ids = [record["id"] for record in records]
    duplicates = sorted(
        {case_id for case_id in ids if ids.count(case_id) > 1}
    )
    if duplicates:
        raise ValueError(
            f"Duplicate evaluation case IDs: {duplicates}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

    print(f"Validated {len(records)} evaluation cases.")
    print(f"Output: {output_path.resolve()}")

    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and normalize a RAG evaluation dataset."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("evaluation/datasets/civil_code_eval.json"),
        help="Input JSON array or JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/datasets/civil_code_eval.jsonl"),
        help="Output JSONL file.",
    )
    args = parser.parse_args()

    try:
        build_dataset(args.input, args.output)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
