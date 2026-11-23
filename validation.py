"""
validation.py
-------------
Checks every piece of user input before it is saved.

Each validate_* function either:
  * returns a cleaned-up value (extra spaces removed, ID upper-cased, etc.), or
  * raises ValidationError with a message that can be shown to the user.

validate_feedback() runs all checks together and returns every error at once,
so the user can fix all mistakes in one go.
"""

import re

# Default limits (can be overridden from data/config.json)
RATING_MIN = 1
RATING_MAX = 5
MIN_COMMENT_LENGTH = 10
MAX_COMMENT_LENGTH = 500
MAX_NAME_LENGTH = 60
MAX_COURSE_LENGTH = 80

# Comments made only of one of these words are treated as "empty"
PLACEHOLDER_COMMENTS = {"na", "n/a", "nil", "none", "nothing", "no", "ok", "okay",
                        "test", "abc", "xyz", "asdf", "null", "-", "."}

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")
STUDENT_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9/-]{2,19}$")
COURSE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &()+.,:/'-]*$")

RATING_FIELDS = {
    "course_rating": "Course rating",
    "teaching_rating": "Teaching quality rating",
    "content_rating": "Course content rating",
}


class ValidationError(ValueError):
    """Raised when an input value is not acceptable."""


def clean_text(value):
    """Turn any value into a string and collapse repeated whitespace."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def validate_person_name(value, label="Name"):
    name = clean_text(value)
    if not name:
        raise ValidationError(f"{label} cannot be empty.")
    if len(name) < 2:
        raise ValidationError(f"{label} must have at least 2 characters.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"{label} must be at most {MAX_NAME_LENGTH} characters.")
    if not NAME_PATTERN.match(name):
        raise ValidationError(f"{label} can only contain letters, spaces, dots (.), apostrophes (') and hyphens (-).")
    return name


def validate_student_name(value):
    return validate_person_name(value, "Student name")


def validate_faculty_name(value):
    return validate_person_name(value, "Faculty name")


def validate_student_id(value):
    student_id = clean_text(value).upper().replace(" ", "")
    if not student_id:
        raise ValidationError("Student ID cannot be empty.")
    if not STUDENT_ID_PATTERN.match(student_id):
        raise ValidationError("Student ID must be 3-20 characters using letters, digits, '-' or '/' (e.g. 23CS1045).")
    return student_id


def validate_course_name(value):
    course = clean_text(value)
    if not course:
        raise ValidationError("Course name cannot be empty.")
    if len(course) < 2:
        raise ValidationError("Course name must have at least 2 characters.")
    if len(course) > MAX_COURSE_LENGTH:
        raise ValidationError(f"Course name must be at most {MAX_COURSE_LENGTH} characters.")
    if not COURSE_PATTERN.match(course):
        raise ValidationError("Course name contains invalid characters.")
    return course


def validate_rating(value, label="Rating", low=RATING_MIN, high=RATING_MAX):
    """A rating must be a whole number between low and high (default 1-5)."""
    if value is None or isinstance(value, bool) or clean_text(value) == "":
        raise ValidationError(f"{label} is required (enter a number from {low} to {high}).")

    if isinstance(value, float):
        if not value.is_integer():
            raise ValidationError(f"{label} must be a whole number, not {value}.")
        rating = int(value)
    elif isinstance(value, int):
        rating = value
    else:
        text = clean_text(value)
        if not re.fullmatch(r"[+-]?\d+", text):
            raise ValidationError(f"{label} must be a whole number from {low} to {high} (you entered '{text}').")
        rating = int(text)

    if rating < low or rating > high:
        raise ValidationError(f"{label} must be between {low} and {high} (you entered {rating}).")
    return rating


def validate_comments(value, min_length=MIN_COMMENT_LENGTH, max_length=MAX_COMMENT_LENGTH):
    comment = clean_text(value)
    if not comment:
        raise ValidationError("Comments cannot be empty. Please share at least one sentence.")
    if comment.lower().strip(".!?") in PLACEHOLDER_COMMENTS:
        raise ValidationError(f"'{comment}' is not a meaningful comment. Please describe your experience.")
    if not re.search(r"[A-Za-z]{2,}", comment):
        raise ValidationError("Comments must contain words, not only numbers or symbols.")
    if len(comment) < min_length:
        raise ValidationError(f"Comments must be at least {min_length} characters long.")
    if len(comment) > max_length:
        raise ValidationError(f"Comments must be at most {max_length} characters (currently {len(comment)}).")
    return comment


def validate_feedback(raw, config=None):
    """
    Validate a whole feedback entry (a dictionary of raw inputs).

    Returns a tuple (clean_data, errors):
      * clean_data - dictionary of cleaned values for fields that passed
      * errors     - dictionary {field_name: error message}; empty if all is valid
    """
    config = config or {}
    low = config.get("rating_min", RATING_MIN)
    high = config.get("rating_max", RATING_MAX)
    min_len = config.get("min_comment_length", MIN_COMMENT_LENGTH)
    max_len = config.get("max_comment_length", MAX_COMMENT_LENGTH)

    checks = {
        "student_name": lambda v: validate_student_name(v),
        "student_id": lambda v: validate_student_id(v),
        "course_name": lambda v: validate_course_name(v),
        "faculty_name": lambda v: validate_faculty_name(v),
    }
    for field, label in RATING_FIELDS.items():
        checks[field] = lambda v, label=label: validate_rating(v, label, low, high)
    checks["comments"] = lambda v: validate_comments(v, min_len, max_len)

    clean_data, errors = {}, {}
    for field, check in checks.items():
        try:
            clean_data[field] = check(raw.get(field))
        except ValidationError as error:
            errors[field] = str(error)
    return clean_data, errors
