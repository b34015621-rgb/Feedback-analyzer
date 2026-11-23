"""
feedback_manager.py
-------------------
The FeedbackManager class connects validation and storage.

The user interface (app.py) only talks to this class. It never reads or
writes files directly, which keeps the code modular and easy to test.
"""

import os
from datetime import datetime

import storage
from validation import validate_feedback, clean_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")


class FeedbackManager:
    """Loads, validates, stores, searches and filters feedback records."""

    def __init__(self, data_dir=DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        self.csv_path = os.path.join(data_dir, "feedback.csv")
        self.config_path = os.path.join(data_dir, "config.json")
        self.records = []
        self.warnings = []
        self.config = {}
        self.load()

    # ------------------------------------------------------------ loading
    def load(self):
        """(Re)load the configuration and every saved record from disk."""
        os.makedirs(self.data_dir, exist_ok=True)
        self.config, config_warnings = storage.load_config(self.config_path)
        self.records, data_warnings = storage.load_feedback(self.csv_path, self.config)
        self.warnings = config_warnings + data_warnings

    # ------------------------------------------------------------ submitting
    def submit(self, raw):
        """
        Validate and save one feedback entry.

        Returns (record, errors):
          * on success: (the saved record, {})
          * on failure: (None, {field: message})
        """
        clean, errors = validate_feedback(raw, self.config)
        if errors:
            return None, errors

        # Re-use the existing spelling so "data structures" and
        # "Data Structures" are counted as the same course.
        clean["course_name"] = self._match_existing(clean["course_name"], self.courses())
        clean["faculty_name"] = self._match_existing(clean["faculty_name"], self.faculty())

        if self.is_duplicate(clean["student_id"], clean["course_name"]):
            return None, {"duplicate": (f"Student {clean['student_id']} has already submitted feedback "
                                        f"for '{clean['course_name']}'. Only one submission per course is allowed.")}

        clean["feedback_id"] = self._next_id()
        clean["submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        storage.append_feedback(self.csv_path, clean)
        self.records.append(clean)
        return clean, {}

    def is_duplicate(self, student_id, course_name):
        student_id = clean_text(student_id).upper().replace(" ", "")
        course_key = clean_text(course_name).casefold()
        return any(r["student_id"] == student_id and r["course_name"].casefold() == course_key
                   for r in self.records)

    def _next_id(self):
        numbers = [int(r["feedback_id"][2:]) for r in self.records
                   if r["feedback_id"].startswith("FB") and r["feedback_id"][2:].isdigit()]
        return f"FB{(max(numbers) + 1 if numbers else 1):04d}"

    @staticmethod
    def _match_existing(value, existing):
        for item in existing:
            if item.casefold() == value.casefold():
                return item
        return value

    # ------------------------------------------------------------ lists for dropdowns
    def courses(self):
        names = list(self.config.get("courses", [])) + [r["course_name"] for r in self.records]
        return self._unique_sorted(names)

    def faculty(self):
        names = list(self.config.get("faculty", [])) + [r["faculty_name"] for r in self.records]
        return self._unique_sorted(names)

    @staticmethod
    def _unique_sorted(names):
        unique = {}
        for name in names:
            name = clean_text(name)
            if name and name.casefold() not in unique:
                unique[name.casefold()] = name
        return sorted(unique.values(), key=str.casefold)

    # ------------------------------------------------------------ search & filter
    def search_by_student_id(self, student_id):
        """Records whose student ID contains the search text (case-insensitive)."""
        text = clean_text(student_id).upper().replace(" ", "")
        if not text:
            return []
        return [r for r in self.records if text in r["student_id"]]

    def filter_records(self, course=None, faculty=None, student_id=None):
        """Combine any of the three filters. Empty filters are ignored."""
        results = self.records
        if student_id:
            text = clean_text(student_id).upper().replace(" ", "")
            results = [r for r in results if text in r["student_id"]]
        if course:
            results = [r for r in results if r["course_name"].casefold() == clean_text(course).casefold()]
        if faculty:
            results = [r for r in results if r["faculty_name"].casefold() == clean_text(faculty).casefold()]
        return list(results)

    def get_by_id(self, feedback_id):
        for record in self.records:
            if record["feedback_id"] == clean_text(feedback_id).upper():
                return record
        return None
