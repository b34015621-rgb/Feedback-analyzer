"""
analysis.py
-----------
Turns a list of feedback records into statistics. Uses only the Python
standard library (no machine learning), so every number can be explained:

  * averages        - sum of ratings / number of ratings
  * best/worst      - course with the highest/lowest overall average
  * sentiment       - rating score + simple positive/negative word counting
  * themes          - comments are matched against keyword lists (e.g. "Pace")
  * suggestions     - sentences containing words like "should", "more", "please"
"""

import re
from collections import Counter

RATING_FIELDS = ["course_rating", "teaching_rating", "content_rating"]

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has
have having he her here hers him his how i if in into is it its itself just me my more most no
nor not now of off on once only or other our out over own same she should so some such than that
the their them then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your yours sir madam mam maam
course class subject really much lot lots get got bit like feel felt think thought make made
overall one way also well even every many need needs needed please us able always sometimes
add give would like
""".split())

POSITIVE_WORDS = set("""
good great excellent amazing clear clearly helpful engaging interesting love loved enjoyed enjoy
best awesome useful organized organised fun patient supportive knowledgeable fantastic nice easy
approachable inspiring perfect wonderful informative effective friendly valuable
motivating relevant structured simple understandable thorough brilliant liked beneficial
""".split())

NEGATIVE_WORDS = set("""
bad poor boring confusing confused unclear hard difficult slow fast rushed late disorganized
disorganised useless worst hate hated terrible unhelpful heavy stressful tough unfair rude outdated
vague monotonous monotone lengthy complicated lacking insufficient irrelevant dull difficulty
issue issues struggle struggled overloaded tiring
""".split())

NEGATION_WORDS = {"not", "no", "never", "hardly", "isnt", "wasnt", "dont", "didnt", "cannot", "cant"}

# A comment belongs to a theme if it contains one of the theme's keywords.
# A keyword ending in "*" matches any word starting with it ("explain*" -> explained,
# explanation); other keywords must match the whole word (or its plural with "s").
THEMES = {
    "Teaching & explanations": ["explain*", "clear*", "clarity", "teach*", "lecture*", "concept*", "understand*"],
    "Pace of teaching": ["pace", "fast", "slow", "rush*", "speed", "hurried"],
    "Assignments & workload": ["assignment*", "homework", "workload", "deadline*", "project*"],
    "Labs & practical work": ["lab", "practical*", "hands", "coding", "programming", "implementation", "experiment*"],
    "Notes & study material": ["material*", "notes", "slide*", "content", "syllabus", "textbook*", "resource*", "reference*"],
    "Examples & practice": ["example*", "practice", "problem*", "exercise*", "question*", "quiz*", "tutorial*"],
    "Exams & evaluation": ["exam", "exams", "test", "marks", "grading", "evaluation", "assessment*", "internal*"],
    "Doubt support & interaction": ["doubt*", "office", "support*", "interact*", "discussion*", "approachable", "help*"],
    "Real-world relevance": ["industry", "real", "application*", "relevant", "outdated", "modern", "case"],
}


def matches_keyword(word, keyword):
    if keyword.endswith("*"):
        return word.startswith(keyword[:-1])
    return word == keyword or word == keyword + "s"


SUGGESTION_CUES = {"should", "could", "please", "suggest", "suggestion", "more", "need", "needs",
                   "would", "improve", "add", "better", "less", "fewer", "wish", "recommend",
                   "instead", "include", "provide", "reduce", "increase"}


# ------------------------------------------------------------------ helpers

def average(values):
    """Average rounded to 2 decimals. Returns 0.0 for an empty list (no crash)."""
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def overall_score(record):
    """A record's overall score = average of its three ratings."""
    return average(record[field] for field in RATING_FIELDS)


def tokenize(text):
    """Lower-case words only: "Great labs, NOT boring!" -> ['great', 'labs', 'not', 'boring']"""
    return re.findall(r"[a-z]+", (text or "").lower().replace("'", ""))


def keyword_score(comment):
    """+1 for each positive word, -1 for each negative word. "not" flips the next word."""
    words = tokenize(comment)
    score = 0
    for index, word in enumerate(words):
        value = 1 if word in POSITIVE_WORDS else -1 if word in NEGATIVE_WORDS else 0
        if value and index > 0 and words[index - 1] in NEGATION_WORDS:
            value = -value
        if word in ("fast", "slow") and index > 0 and words[index - 1] == "too":
            value = -1
        score += value
    return score


def classify_sentiment(record):
    """
    Positive / Negative / Neutral.

    combined = (overall rating - 3) + 0.5 x keyword score
      * combined >= 1   -> Positive
      * combined <= -1  -> Negative
      * otherwise         -> Neutral
    The rating matters most; the comment words adjust it.
    """
    combined = (overall_score(record) - 3) + 0.5 * keyword_score(record.get("comments", ""))
    if combined >= 1:
        return "Positive"
    if combined <= -1:
        return "Negative"
    return "Neutral"


def content_words(text):
    return [w for w in tokenize(text) if w not in STOPWORDS and len(w) > 2]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|;\s*", text or "") if len(s.strip()) > 3]


# ------------------------------------------------------------------ text analysis

def top_keywords(records, limit=10):
    """Most common meaningful words. Each word counts once per comment."""
    counter = Counter()
    for record in records:
        counter.update(set(content_words(record["comments"])))
    return counter.most_common(limit)


def common_phrases(records, limit=10, min_count=2):
    """Two-word phrases (inside one sentence) that appear in at least `min_count` comments."""
    counter = Counter()
    for record in records:
        phrases = set()
        for sentence in split_sentences(record["comments"]):
            words = content_words(sentence)
            phrases |= {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}
        counter.update(phrases)
    return [(p, n) for p, n in counter.most_common(limit) if n >= min_count]


def frequent_comments(records, limit=5):
    """Exact comments (ignoring case and punctuation) written by more than one student."""
    counter, original = Counter(), {}
    for record in records:
        key = " ".join(tokenize(record["comments"]))
        counter[key] += 1
        original.setdefault(key, record["comments"])
    return [(original[k], n) for k, n in counter.most_common(limit) if n > 1]


def theme_counts(records):
    """How many comments mention each theme, most common first."""
    counter = Counter()
    for record in records:
        words = tokenize(record["comments"])
        for theme, stems in THEMES.items():
            if any(matches_keyword(word, kw) for word in words for kw in stems):
                counter[theme] += 1
    return counter.most_common()


def extract_suggestions(records):
    """Sentences that sound like a request or an improvement idea."""
    suggestions = []
    for record in records:
        for sentence in split_sentences(record["comments"]):
            if SUGGESTION_CUES & set(tokenize(sentence)):
                suggestions.append({
                    "suggestion": sentence,
                    "course_name": record["course_name"],
                    "faculty_name": record["faculty_name"],
                    "feedback_id": record["feedback_id"],
                })
    return suggestions


def common_suggestions(records, limit=8):
    """Most repeated topics inside suggestion sentences, e.g. ('practice problems', 4)."""
    counter = Counter()
    for item in extract_suggestions(records):
        words = [w for w in content_words(item["suggestion"]) if w not in SUGGESTION_CUES]
        topics = {" ".join(words[i:i + 2]) for i in range(len(words) - 1)} or set(words)
        counter.update(topics)
    repeated = [(t, n) for t, n in counter.most_common() if n >= 2]
    if not repeated:  # fall back to single words when no phrase repeats
        word_counter = Counter()
        for item in extract_suggestions(records):
            word_counter.update(set(content_words(item["suggestion"])) - SUGGESTION_CUES)
        repeated = [(t, n) for t, n in word_counter.most_common() if n >= 2]
    return repeated[:limit]


# ------------------------------------------------------------------ grouped statistics

def _group_by(records, field):
    groups = {}
    for record in records:
        groups.setdefault(record[field], []).append(record)
    return groups


def course_summary(records):
    """One row per course, best course first."""
    rows = []
    for course, items in _group_by(records, "course_name").items():
        sentiments = Counter(classify_sentiment(r) for r in items)
        rows.append({
            "Course": course,
            "Faculty": ", ".join(sorted({r["faculty_name"] for r in items})),
            "Submissions": len(items),
            "Avg Course Rating": average(r["course_rating"] for r in items),
            "Avg Teaching Rating": average(r["teaching_rating"] for r in items),
            "Avg Content Rating": average(r["content_rating"] for r in items),
            "Overall Average": average(overall_score(r) for r in items),
            "Positive": sentiments["Positive"],
            "Negative": sentiments["Negative"],
        })
    rows.sort(key=lambda row: (-row["Overall Average"], -row["Submissions"], row["Course"].casefold()))
    return rows


def faculty_summary(records):
    """One row per faculty member, best rated first."""
    rows = []
    for faculty, items in _group_by(records, "faculty_name").items():
        sentiments = Counter(classify_sentiment(r) for r in items)
        themes = theme_counts(items)
        rows.append({
            "Faculty": faculty,
            "Courses": ", ".join(sorted({r["course_name"] for r in items})),
            "Submissions": len(items),
            "Avg Teaching Rating": average(r["teaching_rating"] for r in items),
            "Overall Average": average(overall_score(r) for r in items),
            "Positive": sentiments["Positive"],
            "Negative": sentiments["Negative"],
            "Most Discussed Theme": themes[0][0] if themes else "-",
        })
    rows.sort(key=lambda row: (-row["Overall Average"], row["Faculty"].casefold()))
    return rows


def rating_distribution(records):
    """{field: {1: count, 2: count, ...}} for each rating field."""
    return {field: {star: sum(1 for r in records if r[field] == star) for star in range(1, 6)}
            for field in RATING_FIELDS}


# ------------------------------------------------------------------ everything together

def analyze(records):
    """Run every calculation and return the results in one dictionary."""
    records = list(records)
    if not records:
        return {"total": 0}

    courses = course_summary(records)
    sentiments = Counter(classify_sentiment(r) for r in records)
    return {
        "total": len(records),
        "avg_course_rating": average(r["course_rating"] for r in records),
        "avg_teaching_rating": average(r["teaching_rating"] for r in records),
        "avg_content_rating": average(r["content_rating"] for r in records),
        "overall_average": average(overall_score(r) for r in records),
        "highest_rated_course": courses[0],
        "lowest_rated_course": courses[-1],
        "course_summary": courses,
        "faculty_summary": faculty_summary(records),
        "submissions_per_course": {row["Course"]: row["Submissions"] for row in courses},
        "sentiment": {label: sentiments.get(label, 0) for label in ("Positive", "Neutral", "Negative")},
        "rating_distribution": rating_distribution(records),
        "top_keywords": top_keywords(records),
        "common_phrases": common_phrases(records),
        "frequent_comments": frequent_comments(records),
        "themes": theme_counts(records),
        "common_suggestions": common_suggestions(records),
        "suggestions": extract_suggestions(records),
    }
