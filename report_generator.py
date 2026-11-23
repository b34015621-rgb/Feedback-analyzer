"""
report_generator.py
-------------------
Builds a summary report from the analysis results and exports it as
plain text (.txt), CSV (.csv) or JSON (.json) into the reports/ folder.
Every report records the date and time it was generated.
"""

import csv
import io
import json
import os
from datetime import datetime

from analysis import analyze

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LINE = "=" * 78
THIN = "-" * 78


def generate_report(records, course=None, faculty=None, title="Course Feedback Summary Report"):
    """Analyse the given records and wrap the results with report details."""
    now = datetime.now()
    return {
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "file_stamp": now.strftime("%Y%m%d_%H%M%S"),
        "filters": {"course": course or "All courses", "faculty": faculty or "All faculty"},
        "analysis": analyze(records),
    }


# ------------------------------------------------------------------ text report

def _cell(value):
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def _table(rows, columns):
    """Format a list of dictionaries as a fixed-width text table."""
    widths = {c: max(len(c), *(len(_cell(r[c])) for r in rows)) for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    lines = [header, "  ".join("-" * widths[c] for c in columns)]
    for row in rows:
        lines.append("  ".join(_cell(row[c]).ljust(widths[c]) for c in columns).rstrip())
    return lines


def report_to_text(report):
    a = report["analysis"]
    lines = [LINE, report["title"].upper().center(78), LINE,
             f"Generated on : {report['generated_at']}",
             f"Course filter: {report['filters']['course']}",
             f"Faculty filter: {report['filters']['faculty']}", ""]

    if a["total"] == 0:
        lines += ["No feedback records found for the selected filters.",
                  "Submit feedback first, then generate the report again.", LINE]
        return "\n".join(lines)

    best, worst = a["highest_rated_course"], a["lowest_rated_course"]
    s = a["sentiment"]
    lines += [
        "1. OVERALL SUMMARY", THIN,
        f"Total feedback submissions : {a['total']}",
        f"Average course rating      : {a['avg_course_rating']:.2f} / 5",
        f"Average teaching rating    : {a['avg_teaching_rating']:.2f} / 5",
        f"Average content rating     : {a['avg_content_rating']:.2f} / 5",
        f"Overall average rating     : {a['overall_average']:.2f} / 5",
        f"Highest-rated course       : {best['Course']} ({best['Overall Average']:.2f})",
        f"Lowest-rated course        : {worst['Course']} ({worst['Overall Average']:.2f})",
        f"Positive / Neutral / Negative feedback : {s['Positive']} / {s['Neutral']} / {s['Negative']}",
        "",
        "2. COURSE-WISE RATINGS", THIN,
        *_table(a["course_summary"], ["Course", "Submissions", "Avg Course Rating",
                                      "Avg Teaching Rating", "Avg Content Rating", "Overall Average"]),
        "",
        "3. FACULTY-WISE SUMMARY", THIN,
        *_table(a["faculty_summary"], ["Faculty", "Submissions", "Avg Teaching Rating",
                                       "Overall Average", "Positive", "Negative"]),
        "",
        "4. COMMON FEEDBACK THEMES (number of comments mentioning each)", THIN,
    ]
    lines += [f"  {theme:<32} {count}" for theme, count in a["themes"]] or ["  (none found)"]

    lines += ["", "5. MOST FREQUENT WORDS AND PHRASES", THIN,
              "  Keywords: " + ", ".join(f"{w} ({n})" for w, n in a["top_keywords"])]
    if a["common_phrases"]:
        lines.append("  Phrases : " + ", ".join(f'"{p}" ({n})' for p, n in a["common_phrases"]))
    if a["frequent_comments"]:
        lines.append("  Repeated comments:")
        lines += [f'    "{c}" - {n} times' for c, n in a["frequent_comments"]]

    lines += ["", "6. COMMON STUDENT SUGGESTIONS", THIN]
    lines += [f"  {topic:<32} mentioned {n} times" for topic, n in a["common_suggestions"]] \
        or ["  (no repeated suggestions)"]
    if a["suggestions"]:
        lines.append("  Sample suggestions:")
        lines += [f"    - {item['suggestion']}  [{item['course_name']}]" for item in a["suggestions"][:8]]

    lines += ["", LINE, "End of report".center(78), LINE]
    return "\n".join(lines)


# ------------------------------------------------------------------ CSV / JSON

def report_to_csv(report):
    """CSV text with several labelled sections (opens cleanly in Excel)."""
    a = report["analysis"]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([report["title"]])
    writer.writerow(["Generated on", report["generated_at"]])
    writer.writerow(["Course filter", report["filters"]["course"]])
    writer.writerow(["Faculty filter", report["filters"]["faculty"]])
    writer.writerow([])

    if a["total"] == 0:
        writer.writerow(["Total feedback submissions", 0])
        return buffer.getvalue()

    writer.writerow(["SUMMARY"])
    writer.writerow(["Metric", "Value"])
    for label, value in [
        ("Total feedback submissions", a["total"]),
        ("Average course rating", a["avg_course_rating"]),
        ("Average teaching rating", a["avg_teaching_rating"]),
        ("Average content rating", a["avg_content_rating"]),
        ("Overall average rating", a["overall_average"]),
        ("Highest-rated course", a["highest_rated_course"]["Course"]),
        ("Lowest-rated course", a["lowest_rated_course"]["Course"]),
        ("Positive feedback", a["sentiment"]["Positive"]),
        ("Neutral feedback", a["sentiment"]["Neutral"]),
        ("Negative feedback", a["sentiment"]["Negative"]),
    ]:
        writer.writerow([label, value])

    for section, rows in [("COURSE-WISE RATINGS", a["course_summary"]),
                          ("FACULTY-WISE SUMMARY", a["faculty_summary"])]:
        writer.writerow([])
        writer.writerow([section])
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            writer.writerow(list(row.values()))

    for section, header, pairs in [("COMMON THEMES", ["Theme", "Comments"], a["themes"]),
                                   ("TOP KEYWORDS", ["Keyword", "Comments"], a["top_keywords"]),
                                   ("COMMON SUGGESTIONS", ["Topic", "Mentions"], a["common_suggestions"])]:
        writer.writerow([])
        writer.writerow([section])
        writer.writerow(header)
        writer.writerows(pairs)
    return buffer.getvalue()


def report_to_json(report):
    data = {key: value for key, value in report.items() if key != "file_stamp"}
    return json.dumps(data, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------ saving

def export_report(report, file_format, reports_dir=DEFAULT_REPORTS_DIR):
    """Save the report as 'txt', 'csv' or 'json'. Returns the saved file path."""
    converters = {"txt": report_to_text, "csv": report_to_csv, "json": report_to_json}
    if file_format not in converters:
        raise ValueError(f"Unsupported format '{file_format}'. Use txt, csv or json.")
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, f"feedback_report_{report['file_stamp']}.{file_format}")
    with open(path, "w", newline="", encoding="utf-8") as file:
        file.write(converters[file_format](report))
    return path
