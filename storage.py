"""
storage.py
----------
Everything to do with files on disk:

  * data/feedback.csv  - one row per feedback submission (CSV module)
  * data/config.json   - application settings and known courses/faculty (JSON module)

Design rules:
  * Missing folders/files are created automatically.
  * New feedback is APPENDED to the CSV, so existing records are never overwritten.
  * A corrupted file is never silently deleted: it is renamed to *_corrupt_<time>
    (a backup) and a fresh file is created, and a warning is returned for the UI.
"""

import csv
import json
import os
from datetime import datetime

from validation import validate_feedback

CSV_FIELDS = [
    "feedback_id", "submitted_at", "student_name", "student_id", "course_name",
    "faculty_name", "course_rating", "teaching_rating", "content_rating", "comments",
]

DEFAULT_CONFIG = {
    "app_title": "Course Feedback Analyzer",
    "institution": "Everyday Innovators College",
    "rating_min": 1,
    "rating_max": 5,
    "min_comment_length": 10,
    "max_comment_length": 500,
    "courses": [],
    "faculty": [],
}


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_corrupt_file(path):
    """Rename a damaged file so it is kept for inspection. Returns the backup path."""
    base, ext = os.path.splitext(path)
    backup = f"{base}_corrupt_{_timestamp()}{ext}"
    os.replace(path, backup)
    return backup


# ---------------------------------------------------------------- config (JSON)

def save_config(path, config):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def load_config(path):
    """
    Load config.json. Missing keys are filled from DEFAULT_CONFIG.
    Returns (config, warnings).
    """
    warnings = []
    if not os.path.exists(path):
        save_config(path, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG), warnings

    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("config must be a JSON object")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        backup = backup_corrupt_file(path)
        save_config(path, DEFAULT_CONFIG)
        warnings.append(f"config.json was invalid ({error}). It was backed up to "
                        f"{os.path.basename(backup)} and default settings were restored.")
        return dict(DEFAULT_CONFIG), warnings

    config = dict(DEFAULT_CONFIG)
    config.update(data)
    return config, warnings


# ---------------------------------------------------------------- feedback (CSV)

def create_feedback_file(path):
    """Create an empty feedback CSV containing only the header row."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=CSV_FIELDS).writeheader()


def load_feedback(path, config=None):
    """
    Read all feedback records from the CSV file.

    Returns (records, warnings). Each record is a dictionary with ratings
    already converted to integers. Invalid rows are skipped (with a warning)
    instead of crashing the program.
    """
    warnings = []
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        create_feedback_file(path)
        return [], warnings

    try:
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            header = reader.fieldnames or []
            missing = [field for field in CSV_FIELDS if field not in header]
            if missing:
                raise ValueError(f"missing column(s): {', '.join(missing)}")
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError, ValueError) as error:
        backup = backup_corrupt_file(path)
        create_feedback_file(path)
        warnings.append(f"feedback.csv could not be read ({error}). It was backed up to "
                        f"{os.path.basename(backup)} and a new empty file was created.")
        return [], warnings

    records, seen_ids, seen_pairs = [], set(), set()
    for line_number, row in enumerate(rows, start=2):  # line 1 is the header
        if None in row or any(value is None for value in row.values()):
            warnings.append(f"Line {line_number}: wrong number of columns - skipped.")
            continue
        clean, errors = validate_feedback(row, config)
        if errors:
            warnings.append(f"Line {line_number}: {'; '.join(errors.values())} - skipped.")
            continue
        feedback_id = (row.get("feedback_id") or "").strip()
        pair = (clean["student_id"], clean["course_name"].casefold())
        if not feedback_id or feedback_id in seen_ids:
            warnings.append(f"Line {line_number}: missing or repeated feedback ID - skipped.")
            continue
        if pair in seen_pairs:
            warnings.append(f"Line {line_number}: duplicate feedback for {pair[0]} in "
                            f"{clean['course_name']} - skipped.")
            continue
        clean["feedback_id"] = feedback_id
        clean["submitted_at"] = (row.get("submitted_at") or "").strip()
        seen_ids.add(feedback_id)
        seen_pairs.add(pair)
        records.append(clean)
    return records, warnings


def append_feedback(path, record):
    """Add ONE record to the end of the CSV file (existing rows are untouched)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        create_feedback_file(path)
    with open(path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writerow({field: record.get(field, "") for field in CSV_FIELDS})
