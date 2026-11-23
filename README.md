# 📊 Course Feedback Analyzer

**Project #7 · Everyday Innovators Hackathon · Domain: Education & Student Life**

A beginner-friendly Python web application that collects student feedback about courses, validates every entry, stores it in local CSV/JSON files, analyses ratings and comments, and produces summary reports. The app runs entirely on your own computer. It needs no internet connection, database, paid API or cloud hosting.

---

## 1. Problem Statement

Colleges often collect student feedback on paper or in scattered spreadsheets and then summarise it by hand. This causes:

- calculation errors when averages are worked out manually,
- lost or duplicated entries,
- slow insight, because results arrive long after the semester ends.

Existing survey and LMS tools are often enterprise-grade, expensive or complicated to set up for a quick local workflow.

**Course Feedback Analyzer** solves this with a focused, easy-to-use Python application that streamlines data handling, validates entries and presents actionable summaries.

## 2. Objectives

1. Collect structured feedback: student, course, faculty, three ratings and comments.
2. Apply strict input validation so that only clean, meaningful data is stored.
3. Persist data reliably in local files (CSV for records, JSON for configuration).
4. Automatically calculate averages, best/worst courses, sentiment and common themes.
5. Present the results on a clear dashboard and as exportable, timestamped reports.

## 3. Features

| Area | What it does |
|---|---|
| **Feedback collection** | Form for student name, student ID, course, faculty, course / teaching / content ratings (1–5) and comments. Courses and faculty are picked from a list, or added with **"Other"**. |
| **Input validation** | Rejects empty fields, ratings outside 1–5 or not whole numbers, names containing digits or symbols, and placeholder comments such as "na" or "ok". Blocks duplicate feedback from one student for one course. Every error is shown at once with a clear message. |
| **Data storage** | `data/feedback.csv` holds the records. New feedback is appended, so old records are never overwritten. `data/config.json` holds settings and the course/faculty lists. Missing files are created automatically. Corrupted files are backed up and replaced, and the app keeps running. |
| **Analysis** | Total submissions, average course / teaching / content rating, highest- and lowest-rated course, submissions per course, rating distribution, positive/neutral/negative sentiment, common themes, top keywords, repeated phrases and student suggestions. |
| **Dashboard** | Key metrics, course-wise table and chart, faculty-wise summary, positive/negative counts and common suggestions. |
| **Search & filter** | Search by full or partial student ID, filter by course and/or faculty, and open any single record in a detail card. |
| **Reports** | Generate a report for everything or for one course/faculty, with the date and time it was generated. View it on screen, download it as TXT/CSV/JSON, or save all three to `reports/`. |

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.9+ (tested on 3.14) | Main language |
| Streamlit | Web interface (the only external package) |
| `csv` module | Reading and appending feedback records |
| `json` module | Configuration file and JSON report export |
| `re`, `collections.Counter` | Validation patterns and text analysis |
| `datetime`, `os`, `io` | Timestamps, files and folders |
| `unittest` + `streamlit.testing` | Automated tests (41 tests) |

## 5. Project Folder Structure

```
course-feedback-analyzer/
│
├── app.py                  # Streamlit interface: 5 pages (dashboard, submit, view, analyze, reports)
├── feedback_manager.py     # FeedbackManager class: submit, duplicate check, search, filter
├── validation.py           # Input validation rules and error messages
├── storage.py              # CSV/JSON reading and writing, auto-create, corruption handling
├── analysis.py             # Averages, best/worst course, sentiment, themes, keywords, suggestions
├── report_generator.py     # Builds timestamped reports; exports TXT / CSV / JSON
│
├── data/
│   ├── feedback.csv        # Feedback records (pre-loaded with 30 sample records)
│   ├── sample_feedback.csv # Clean copy of the sample data (to reset the demo)
│   └── config.json         # Settings + list of courses and faculty
│
├── reports/                # Generated reports (sample TXT/CSV/JSON included)
├── tests/
│   ├── test_core.py        # 32 tests: validation, storage, analysis, reports, search
│   └── test_app_ui.py      # 9 tests that click through the real Streamlit app
├── docs/
│   ├── PROJECT_EXPLANATION.md  # How it works + Python concepts + viva questions
│   ├── TEST_RESULTS.md         # Test cases and their results
│   └── SCREENSHOTS.md          # Which screenshots to capture for submission
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 6. Installation (Windows PowerShell)

Open PowerShell inside the `course-feedback-analyzer` folder and run:

```powershell
# 1. Check Python is installed (3.9 or newer)
python --version

# 2. (Recommended) create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install the dependency
pip install -r requirements.txt
```

> If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip step 2 and install globally.

## 7. How to Run

```powershell
python -m streamlit run app.py
```

The app opens in your browser at **http://localhost:8501**. Stop it with **Ctrl + C** in PowerShell.

Run the automated tests:

```powershell
python -m unittest discover -s tests -v
```

Reset the demo data back to the 30 sample records:

```powershell
Copy-Item data\sample_feedback.csv data\feedback.csv -Force
```

## 8. How to Use Each Feature

1. **🏠 Home Dashboard.** Opens first. It shows total feedback, the overall average, positive/negative counts, course-wise ratings with a chart, the faculty summary and the most common suggestions.
2. **📝 Submit Feedback.** Fill in every field and click **Submit Feedback**.
   - Choose a course or faculty member from the list, or pick **"➕ Other"** to type a new one.
   - If anything is wrong, the feedback is not saved and every problem is listed.
   - On success you get a feedback ID (e.g. `FB0031`) and the form clears.
3. **🔍 View Feedback.** Type a student ID (or part of one, e.g. `23CS`) and/or pick a course and faculty. The table updates instantly. Choose a record under **View Individual Record** to see all its details.
4. **📊 Analyze Feedback.** Shows the averages, the highest/lowest course, submissions per course, rating distribution, sentiment, themes, keywords and repeated phrases. Use the filters to analyse one course or one faculty member.
5. **📄 Generate Reports.** Optionally choose filters, then click **Generate Report**. Use **⬇️ TXT / CSV / JSON** to download, or **💾 Save all** to write all three into `reports/`.

## 9. Expected Output

With the included sample data (30 records, 5 courses):

```
Total feedback submissions : 30
Average course rating      : 3.60 / 5
Average teaching rating    : 3.73 / 5
Average content rating     : 3.63 / 5
Overall average rating     : 3.66 / 5
Highest-rated course       : Python Programming (4.61)
Lowest-rated course        : Engineering Mathematics III (2.33)
Positive / Neutral / Negative feedback : 16 / 8 / 6
Top suggestions: practice problems (4), solved examples (4), lab programs (3)
```

Full sample reports are in [`reports/`](reports/). Test results are in [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md).

## 10. Validation Rules

| Field | Rule |
|---|---|
| Student / Faculty name | Required, 2–60 characters, letters, spaces, `.` `'` `-` only |
| Student ID | Required, 3–20 characters, letters/digits/`-`/`/`, stored in upper case |
| Course name | Required, 2–80 characters. A different spelling of an existing course (e.g. "data structures") is merged into it. |
| Ratings (×3) | Required, whole number from 1 to 5 |
| Comments | Required, 10–500 characters, must contain words; "na", "ok", "-" and similar are rejected |
| Duplicate | Each student ID can submit feedback for each course only once |

## 11. Future Improvements

- Login for administrators, so that only staff can see reports.
- An anonymous feedback option.
- Semester and academic-year fields, to compare trends over time.
- PDF export and emailing reports to department heads.
- An SQLite database for very large datasets.
- More advanced sentiment analysis (e.g. NLTK VADER) and charts in the exported reports.
