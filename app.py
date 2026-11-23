"""
app.py - Course Feedback Analyzer (Streamlit web interface)

Run with:   streamlit run app.py

Pages (chosen from the sidebar):
  1. Home Dashboard    - key numbers, course-wise and faculty-wise tables, suggestions
  2. Submit Feedback   - validated feedback form
  3. View Feedback     - search by student ID, filter by course/faculty, view one record
  4. Analyze Feedback  - averages, best/worst course, charts, themes, keywords
  5. Generate Reports  - build a timestamped report and export it as TXT/CSV/JSON
"""

import os

import streamlit as st

from analysis import analyze, classify_sentiment, overall_score
from feedback_manager import FeedbackManager, DEFAULT_DATA_DIR
from report_generator import (DEFAULT_REPORTS_DIR, export_report, generate_report,
                              report_to_csv, report_to_json, report_to_text)

# Folders can be changed with environment variables (used by the automated tests)
DATA_DIR = os.environ.get("FEEDBACK_DATA_DIR", DEFAULT_DATA_DIR)
REPORTS_DIR = os.environ.get("FEEDBACK_REPORTS_DIR", DEFAULT_REPORTS_DIR)

PAGES = ["🏠 Home Dashboard", "📝 Submit Feedback", "🔍 View Feedback",
         "📊 Analyze Feedback", "📄 Generate Reports"]
OTHER = "➕ Other (type a new name)"
ALL_COURSES, ALL_FACULTY = "All courses", "All faculty"
# Empty value for every input on the Submit page (used to clear the form after saving)
FORM_DEFAULTS = {"student_name": "", "student_id": "", "course_choice": None, "course_new": "",
                 "faculty_choice": None, "faculty_new": "", "course_rating": None,
                 "teaching_rating": None, "content_rating": None, "comments": ""}

st.set_page_config(page_title="Course Feedback Analyzer", page_icon="📊", layout="wide")


# ------------------------------------------------------------------ helpers

def records_to_rows(records):
    """Convert records into friendly table rows for display."""
    return [{
        "ID": r["feedback_id"],
        "Submitted": r["submitted_at"],
        "Student": r["student_name"],
        "Student ID": r["student_id"],
        "Course": r["course_name"],
        "Faculty": r["faculty_name"],
        "Course ⭐": r["course_rating"],
        "Teaching ⭐": r["teaching_rating"],
        "Content ⭐": r["content_rating"],
        "Overall": overall_score(r),
        "Sentiment": classify_sentiment(r),
        "Comments": r["comments"],
    } for r in records]


def empty_state(message="No feedback has been submitted yet."):
    st.info(f"{message} Go to **📝 Submit Feedback** to add the first entry.")


def filter_selectors(manager, key_prefix):
    """Course and faculty dropdowns used by several pages."""
    col1, col2 = st.columns(2)
    course = col1.selectbox("Course", [ALL_COURSES] + manager.courses(), key=f"{key_prefix}_course")
    faculty = col2.selectbox("Faculty", [ALL_FACULTY] + manager.faculty(), key=f"{key_prefix}_faculty")
    return (None if course == ALL_COURSES else course,
            None if faculty == ALL_FACULTY else faculty)


def stars(value):
    return "⭐" * int(value)


# ------------------------------------------------------------------ page 1: dashboard

def page_dashboard(manager):
    st.title("🏠 Home Dashboard")
    st.caption(f"{manager.config.get('institution', '')} · live summary of all saved feedback")

    if not manager.records:
        empty_state()
        return
    a = analyze(manager.records)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Feedback", a["total"])
    c2.metric("Overall Average", f"{a['overall_average']:.2f} / 5")
    c3.metric("Positive Feedback", a["sentiment"]["Positive"])
    c4.metric("Negative Feedback", a["sentiment"]["Negative"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Course Rating", f"{a['avg_course_rating']:.2f}")
    c2.metric("Avg Teaching Rating", f"{a['avg_teaching_rating']:.2f}")
    c3.metric("Avg Content Rating", f"{a['avg_content_rating']:.2f}")
    c4.metric("Courses Reviewed", len(a["course_summary"]))

    st.subheader("📚 Course-wise Ratings")
    st.dataframe(a["course_summary"], hide_index=True, width="stretch")
    st.bar_chart({"Course": [r["Course"] for r in a["course_summary"]],
                  "Overall Average": [r["Overall Average"] for r in a["course_summary"]]},
                 x="Course", y="Overall Average", height=280)

    st.subheader("👩‍🏫 Faculty-wise Summary")
    st.dataframe(a["faculty_summary"], hide_index=True, width="stretch")

    st.subheader("💡 Common Student Suggestions")
    if a["common_suggestions"]:
        for topic, count in a["common_suggestions"]:
            st.markdown(f"- **{topic}** — mentioned in {count} suggestions")
    else:
        st.write("No repeated suggestions yet.")
    if a["suggestions"]:
        with st.expander(f"Show all {len(a['suggestions'])} suggestion sentences"):
            st.dataframe([{"Suggestion": s["suggestion"], "Course": s["course_name"],
                           "Faculty": s["faculty_name"], "ID": s["feedback_id"]}
                          for s in a["suggestions"]], hide_index=True, width="stretch")


# ------------------------------------------------------------------ page 2: submit

def choose_or_type(label, options, choice_key, new_key):
    """Dropdown of known names plus an 'Other' option that shows a text box."""
    choice = st.selectbox(label, options + [OTHER], key=choice_key,
                          placeholder=f"Select {label.lower()}")
    if choice == OTHER:
        return st.text_input(f"New {label.lower()}", key=new_key)
    return choice or ""


def page_submit(manager):
    st.title("📝 Submit Feedback")
    st.caption("All fields are required. Ratings: 1 = Very poor, 2 = Poor, 3 = Average, 4 = Good, 5 = Excellent.")

    if st.session_state.pop("clear_form", False):
        for key, empty_value in FORM_DEFAULTS.items():
            st.session_state[key] = empty_value
    for key, empty_value in FORM_DEFAULTS.items():
        st.session_state.setdefault(key, empty_value)  # inputs start empty
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    low, high = manager.config["rating_min"], manager.config["rating_max"]
    with st.container(border=True):
        st.markdown("**Student details**")
        col1, col2 = st.columns(2)
        student_name = col1.text_input("Student Name", key="student_name", placeholder="e.g. Ananya Sharma")
        student_id = col2.text_input("Student ID", key="student_id", placeholder="e.g. 23CS1045")

        st.markdown("**Course details**")
        col1, col2 = st.columns(2)
        with col1:
            course = choose_or_type("Course Name", manager.courses(), "course_choice", "course_new")
        with col2:
            faculty = choose_or_type("Faculty Name", manager.faculty(), "faculty_choice", "faculty_new")

        st.markdown(f"**Ratings ({low}–{high})**")
        col1, col2, col3 = st.columns(3)
        rating_box = dict(step=1, placeholder=f"{low}-{high}")
        course_rating = col1.number_input("Course Rating", key="course_rating", **rating_box)
        teaching_rating = col2.number_input("Teaching Quality Rating", key="teaching_rating", **rating_box)
        content_rating = col3.number_input("Course Content Rating", key="content_rating", **rating_box)

        comments = st.text_area("Student Comments", key="comments", height=110,
                                max_chars=manager.config["max_comment_length"],
                                placeholder="What went well? What should be improved?")

        submitted = st.button("Submit Feedback", type="primary", width="stretch")

    if submitted:
        record, errors = manager.submit({
            "student_name": student_name, "student_id": student_id,
            "course_name": course, "faculty_name": faculty,
            "course_rating": course_rating, "teaching_rating": teaching_rating,
            "content_rating": content_rating, "comments": comments,
        })
        if errors:
            st.error(f"Feedback was **not saved**. Please fix {len(errors)} problem(s):")
            for message in errors.values():
                st.warning(message)
        else:
            st.session_state["flash"] = (f"✅ Thank you, {record['student_name']}! Feedback {record['feedback_id']} "
                                         f"for {record['course_name']} was saved.")
            st.session_state["clear_form"] = True
            st.rerun()


# ------------------------------------------------------------------ page 3: view

def page_view(manager):
    st.title("🔍 View Feedback")
    if not manager.records:
        empty_state()
        return

    student_id = st.text_input("Search by Student ID", key="view_student_id",
                               placeholder="Type a full or partial ID, e.g. 23CS")
    course, faculty = filter_selectors(manager, "view")
    results = manager.filter_records(course=course, faculty=faculty, student_id=student_id)

    if not results:
        st.warning("No feedback matches these filters." +
                   (f" No records found for student ID '{student_id.strip().upper()}'." if student_id.strip() else ""))
        return

    st.caption(f"Showing {len(results)} of {len(manager.records)} feedback records")
    st.dataframe(records_to_rows(results), hide_index=True, width="stretch")

    st.subheader("📋 View Individual Record")
    labels = {f"{r['feedback_id']} — {r['student_name']} — {r['course_name']}": r["feedback_id"] for r in results}
    chosen = st.selectbox("Select a feedback record", list(labels), key="view_record")
    record = manager.get_by_id(labels[chosen])
    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Feedback ID:** {record['feedback_id']}  \n"
                      f"**Submitted:** {record['submitted_at']}  \n"
                      f"**Student:** {record['student_name']} ({record['student_id']})")
        col2.markdown(f"**Course:** {record['course_name']}  \n"
                      f"**Faculty:** {record['faculty_name']}  \n"
                      f"**Sentiment:** {classify_sentiment(record)}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Course", f"{record['course_rating']} / 5")
        c2.metric("Teaching", f"{record['teaching_rating']} / 5")
        c3.metric("Content", f"{record['content_rating']} / 5")
        c4.metric("Overall", f"{overall_score(record):.2f}")
        st.markdown(f"**Comments:** {record['comments']}")


# ------------------------------------------------------------------ page 4: analyze

def page_analyze(manager):
    st.title("📊 Analyze Feedback")
    if not manager.records:
        empty_state()
        return

    course, faculty = filter_selectors(manager, "analyze")
    records = manager.filter_records(course=course, faculty=faculty)
    if not records:
        st.warning("No feedback matches these filters.")
        return
    a = analyze(records)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Submissions", a["total"])
    c2.metric("Avg Course Rating", f"{a['avg_course_rating']:.2f}")
    c3.metric("Avg Teaching Rating", f"{a['avg_teaching_rating']:.2f}")
    c4.metric("Avg Content Rating", f"{a['avg_content_rating']:.2f}")

    best, worst = a["highest_rated_course"], a["lowest_rated_course"]
    col1, col2 = st.columns(2)
    col1.success(f"🏆 **Highest-rated course:** {best['Course']} — {best['Overall Average']:.2f} / 5 "
                 f"({best['Submissions']} submissions)")
    col2.error(f"⚠️ **Lowest-rated course:** {worst['Course']} — {worst['Overall Average']:.2f} / 5 "
               f"({worst['Submissions']} submissions)")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Submissions per Course")
        st.bar_chart({"Course": list(a["submissions_per_course"]),
                      "Submissions": list(a["submissions_per_course"].values())},
                     x="Course", y="Submissions", height=280)
    with col2:
        st.subheader("Rating Distribution")
        dist = a["rating_distribution"]
        st.bar_chart({"Stars": [f"{n}★" for n in range(1, 6)],
                      "Course": [dist["course_rating"][n] for n in range(1, 6)],
                      "Teaching": [dist["teaching_rating"][n] for n in range(1, 6)],
                      "Content": [dist["content_rating"][n] for n in range(1, 6)]},
                     x="Stars", y=["Course", "Teaching", "Content"], stack=False, height=280)

    st.subheader("😊 Sentiment of Feedback")
    s = a["sentiment"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive", s["Positive"])
    c2.metric("Neutral", s["Neutral"])
    c3.metric("Negative", s["Negative"])
    st.caption("Sentiment = (overall rating − 3) + 0.5 × (positive words − negative words). "
               "≥ 1 is Positive, ≤ −1 is Negative, otherwise Neutral.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🧩 Common Feedback Themes")
        if a["themes"]:
            st.dataframe([{"Theme": t, "Comments mentioning it": n} for t, n in a["themes"]],
                         hide_index=True, width="stretch")
        else:
            st.write("No themes detected.")
    with col2:
        st.subheader("🔑 Most Frequent Keywords")
        st.dataframe([{"Keyword": w, "Comments": n} for w, n in a["top_keywords"]],
                     hide_index=True, width="stretch")

    st.subheader("💬 Common Phrases & Repeated Comments")
    if a["common_phrases"]:
        st.write(" · ".join(f"**{p}** ({n})" for p, n in a["common_phrases"]))
    else:
        st.write("No phrase appears in more than one comment.")
    for comment, count in a["frequent_comments"]:
        st.markdown(f'> "{comment}" — written {count} times')

    st.subheader("📚 Course-wise Breakdown")
    st.dataframe(a["course_summary"], hide_index=True, width="stretch")


# ------------------------------------------------------------------ page 5: reports

def page_reports(manager):
    st.title("📄 Generate Reports")
    st.caption("Choose filters and click Generate Report. Then download it (⬇️) or click 💾 Save all to store "
               "TXT, CSV and JSON copies in the reports/ folder.")
    course, faculty = filter_selectors(manager, "report")

    if st.button("Generate Report", type="primary"):
        records = manager.filter_records(course=course, faculty=faculty)
        st.session_state["report"] = generate_report(records, course, faculty)
        st.session_state.pop("saved_paths", None)

    report = st.session_state.get("report")
    if not report:
        st.info("Click **Generate Report** to create a summary report.")
    else:
        st.success(f"Report generated on {report['generated_at']} "
                   f"({report['analysis']['total']} feedback records).")
        st.code(report_to_text(report), language=None)

        name = f"feedback_report_{report['file_stamp']}"
        col1, col2, col3, col4 = st.columns(4)
        col1.download_button("⬇️ TXT", report_to_text(report), f"{name}.txt", "text/plain", width="stretch")
        col2.download_button("⬇️ CSV", report_to_csv(report), f"{name}.csv", "text/csv", width="stretch")
        col3.download_button("⬇️ JSON", report_to_json(report), f"{name}.json",
                             "application/json", width="stretch")
        if col4.button("💾 Save all", width="stretch"):
            try:
                st.session_state["saved_paths"] = [export_report(report, fmt, REPORTS_DIR)
                                                   for fmt in ("txt", "csv", "json")]
            except OSError as error:
                st.error(f"Could not save the report: {error}")
        for path in st.session_state.get("saved_paths", []):
            st.write(f"Saved: `{os.path.relpath(path)}`")

    if os.path.isdir(REPORTS_DIR):
        saved = sorted((f for f in os.listdir(REPORTS_DIR) if f.startswith("feedback_report_")), reverse=True)
        if saved:
            with st.expander(f"Previously saved reports ({len(saved)})"):
                for file_name in saved:
                    st.write(f"📁 reports/{file_name}")


# ------------------------------------------------------------------ main

def main():
    # A fresh manager on every interaction = always shows the latest saved data
    manager = FeedbackManager(DATA_DIR)

    with st.sidebar:
        st.title("📊 Course Feedback Analyzer")
        st.caption("Project #7 · Education & Student Life")
        page = st.radio("Navigate", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.metric("Saved feedback records", len(manager.records))
        st.caption(f"Data file: data/{os.path.basename(manager.csv_path)}")
        for warning in manager.warnings:
            st.warning(warning)

    pages = {
        PAGES[0]: page_dashboard, PAGES[1]: page_submit, PAGES[2]: page_view,
        PAGES[3]: page_analyze, PAGES[4]: page_reports,
    }
    pages[page](manager)


main()
