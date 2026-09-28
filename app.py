"""Website for the student performance project.

Demo logins: admin, teacher and student.
Passwords are only for showing the project on this computer.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
from flask import Flask, flash, redirect, render_template_string, request, session, url_for

from college_records import (
    add_internal,
    add_question,
    add_teacher,
    college_row,
    delete_question,
    ensure_files,
    exam_rank,
    list_attempts,
    list_internals,
    list_questions,
    list_teachers,
    remove_teacher,
    save_attempt,
)
from ml_pipeline import (
    CATEGORIES,
    DATA_FILE,
    EXCLUDED_FROM_MODEL,
    decode_frame,
    feature_columns,
    MARK_COLUMNS,
    fit_best,
    fit_marks_model,
    load_raw_frame,
    save_results,
)

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = "local-viva-demo-only"

USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "teacher": {"password": "teacher123", "role": "Teacher"},
    "student": {"password": "student123", "role": "Student"},
}

FRAME: pd.DataFrame | None = None
MODEL = None
REPORT: dict | None = None
COLUMNS: list[str] = []
MARKS_MODEL = None
MARKS_REPORT: dict | None = None


def boot() -> None:
    global FRAME, MODEL, REPORT, COLUMNS, MARKS_MODEL, MARKS_REPORT
    raw = load_raw_frame(DATA_FILE)
    FRAME = decode_frame(raw)
    MODEL, REPORT, _ = fit_best(FRAME)
    COLUMNS = feature_columns(FRAME)
    save_results(REPORT)
    ensure_files()
    MARKS_MODEL, MARKS_REPORT = fit_marks_model()


def marks_prediction(username: str) -> str:
    row = college_row(username)
    if row is None or MARKS_MODEL is None:
        return "No marks row"
    sample = pd.DataFrame([{column: float(row[column]) for column in MARK_COLUMNS}])
    return str(MARKS_MODEL.predict(sample)[0])


def role() -> str | None:
    return session.get("role")


def logged_in() -> bool:
    return session.get("username") is not None


def allowed(*roles: str) -> bool:
    return logged_in() and role() in roles


BASE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
body{margin:0;font-family:Georgia,serif;background:#f4f6f8;color:#1c2430}
header{background:#1f2937;color:#fff;padding:16px 4%;display:flex;justify-content:space-between;gap:16px;align-items:center}
nav a{color:#fff;margin-right:12px;text-decoration:none}
main{max-width:1100px;margin:24px auto;padding:0 16px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin-bottom:16px}
table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #e5e7eb;text-align:left}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.stat{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px}
label{display:block;font-weight:700;margin:8px 0 4px}
input,select{width:100%;padding:8px;box-sizing:border-box}
button,.btn{background:#1f4e79;color:#fff;border:0;padding:10px 14px;border-radius:6px;text-decoration:none;display:inline-block}
.formgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.flash{background:#fff7ed;border:1px solid #fed7aa;padding:10px;margin-bottom:12px}
.muted{color:#64748b}
footer{text-align:center;color:#64748b;padding:24px}
@media(max-width:800px){.grid,.formgrid{grid-template-columns:1fr}}
</style>
</head>
<body>
{% if logged %}
<header>
  <div><strong>Student Performance Prediction</strong></div>
  <nav>{{ nav|safe }}</nav>
  <div>{{ username }} ({{ userrole }}) · <a href="{{ url_for('logout') }}">Logout</a></div>
</header>
{% endif %}
<main>
{% with messages = get_flashed_messages() %}
  {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
{% endwith %}
{{ body|safe }}
</main>
<footer>BCA project prototype · University of Mysore · local demo</footer>
</body>
</html>
"""


def render_page(title: str, content: str):
    links = [("Dashboard", "dashboard"), ("Predict", "predict"), ("About", "about")]
    if role() == "Student":
        links[2:2] = [("Exam", "exam"), ("My result", "my_result")]
    if role() == "Teacher":
        links[2:2] = [
            ("Students", "students"),
            ("Questions", "questions"),
            ("Internal marks", "internals"),
            ("Evaluation", "evaluation"),
        ]
    if role() == "Admin":
        links[2:2] = [
            ("Students", "students"),
            ("Teachers", "teachers"),
            ("Evaluation", "evaluation"),
        ]
    nav = "".join(
        f'<a href="{url_for(endpoint)}">{escape(label)}</a>' for label, endpoint in links
    )
    return render_template_string(
        BASE,
        title=title,
        body=content,
        logged=logged_in(),
        username=session.get("username"),
        userrole=role(),
        nav=nav,
    )


@app.route("/", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("dashboard"))
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and user["password"] == password:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        error = "<p>Invalid username or password.</p>"
    content = f"""
    <div class="card" style="max-width:420px;margin:40px auto">
      <h1>Login</h1>
      <p class="muted">Demo accounts are printed here for the academic viva only.</p>
      {error}
      <form method="post">
        <label>Username</label><input name="username" required>
        <label>Password</label><input type="password" name="password" required>
        <p><button>Login</button></p>
      </form>
      <p>Admin: admin / admin123<br>Teacher: teacher / teacher123<br>Student: student / student123</p>
    </div>
    """
    return render_page("Login", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))
    counts = REPORT["class_counts"]
    total = REPORT["n_rows"]
    best = REPORT["best_model"]
    f1 = REPORT["models"][best]["cv"]["f1_macro"]
    accuracy = REPORT["models"][best]["cv"]["accuracy"]["mean"]
    baseline = REPORT["majority_baseline_cv_accuracy"]["mean"]
    cards = "".join(
        f'<div class="stat"><div class="muted">{escape(label)}</div><strong style="font-size:28px">{counts[label]}</strong></div>'
        for label in CATEGORIES
    )
    teacher_links = ""
    if role() in ("Admin", "Teacher"):
        teacher_links = f'<p><a class="btn" href="{url_for("evaluation")}">Open evaluation</a></p>'
    content = f"""
    <div class="card"><h1>Dashboard</h1>
      <p>Total students: {total}. Categories are made from the course grade in the dataset.</p>
    </div>
    <div class="grid">
      <div class="stat"><div class="muted">Students</div><strong style="font-size:28px">{total}</strong></div>
      {cards}
    </div>
    <div class="card">
      <h2>Selected model</h2>
      <p>Selected model: <strong>{escape(best)}</strong>. It was selected using macro-F1
      ({f1['mean']*100:.1f}%). Accuracy is {accuracy*100:.1f}%.
      If every student is marked {escape(REPORT['majority_class'])}, accuracy is
      {baseline*100:.1f}%. So this model is not better than that simple guess.</p>
      <p><a class="btn" href="{url_for('predict')}">Predict a profile</a></p>
      {teacher_links}
    </div>
    """
    return render_page("Dashboard", content)


def _options(column: str, current: str) -> str:
    values = sorted(FRAME[column].dropna().astype(str).unique().tolist())
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == current else ""}>{escape(value)}</option>'
        for value in values
    )


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if not logged_in():
        return redirect(url_for("login"))
    result = ""
    if request.method == "POST":
        row = {column: request.form.get(column, "") for column in COLUMNS}
        missing = [column for column, value in row.items() if not value]
        if missing:
            flash("Every field is required.")
        else:
            predicted = MODEL.predict(pd.DataFrame([row], columns=COLUMNS))[0]
            scores = ""
            if hasattr(MODEL, "predict_proba"):
                probabilities = MODEL.predict_proba(pd.DataFrame([row], columns=COLUMNS))[0]
                order = sorted(
                    zip(MODEL.classes_, probabilities),
                    key=lambda item: item[1],
                    reverse=True,
                )
                scores = "<ul>" + "".join(
                    f"<li>{escape(str(label))}: {prob * 100:.1f}%</li>" for label, prob in order
                ) + "</ul>"
            result = f"""
            <div class="card">
              <p class="muted">Model: {escape(REPORT['best_model'])}</p>
              <h2>{escape(str(predicted))}</h2>
              <p>Class percentage from the model. If two values are close, the result is not sure.</p>
              {scores}
            </div>
            """
    fields = "".join(
        f'<div><label>{escape(column.replace("_", " "))}</label>'
        f'<select name="{escape(column)}" required><option value="">Select</option>'
        f'{_options(column, request.form.get(column, ""))}</select></div>'
        for column in COLUMNS
    )
    content = f"""
    <div class="card">
      <h1>Predict performance</h1>
      <p class="muted">Fill the study and background details. Grade and CGPA are not asked here.</p>
      <form method="post"><div class="formgrid">{fields}</div><p><button>Predict</button></p></form>
    </div>
    {result}
    """
    return render_page("Predict", content)


@app.route("/students")
def students():
    if not allowed("Admin", "Teacher"):
        flash("Student records are limited to Admin and Teacher.")
        return redirect(url_for("dashboard"))
    rows = []
    for _, record in FRAME.head(145).iterrows():
        rows.append(
            "<tr>"
            f"<td>{escape(str(record['Student_ID']))}</td>"
            f"<td>{escape(str(record['Class_Attendance']))}</td>"
            f"<td>{escape(str(record['Weekly_Study_Hours']))}</td>"
            f"<td>{escape(str(record['Grade']))}</td>"
            f"<td>{escape(str(record['Performance_Category']))}</td>"
            "</tr>"
        )
    content = f"""
    <div class="card">
      <h1>Student records</h1>
      <p class="muted">{len(FRAME)} records from the dataset. Student login cannot open this page.</p>
      <table>
        <tr><th>ID</th><th>Class attendance</th><th>Weekly study hours</th><th>Grade</th><th>Category</th></tr>
        {''.join(rows)}
      </table>
    </div>
    """
    return render_page("Students", content)


@app.route("/evaluation")
def evaluation():
    if not allowed("Admin", "Teacher"):
        flash("Evaluation is limited to Admin and Teacher.")
        return redirect(url_for("dashboard"))
    rows = []
    for name, metrics in REPORT["models"].items():
        mark = " (selected)" if name == REPORT["best_model"] else ""
        cv = metrics["cv"]
        rows.append(
            "<tr>"
            f"<td>{escape(name + mark)}</td>"
            f"<td>{cv['accuracy']['mean']*100:.1f}</td>"
            f"<td>{cv['precision_macro']['mean']*100:.1f}</td>"
            f"<td>{cv['recall_macro']['mean']*100:.1f}</td>"
            f"<td>{cv['f1_macro']['mean']*100:.1f}</td>"
            f"<td>{cv['poor_recall']['mean']*100:.1f}</td>"
            "</tr>"
        )
    baseline = REPORT["majority_baseline_cv_accuracy"]["mean"] * 100
    content = f"""
    <div class="card">
      <h1>Model evaluation</h1>
      <p>These values are the average of 5 folds. If the model always says
      {escape(REPORT['majority_class'])}, accuracy is about {baseline:.1f}%.</p>
      <table>
        <tr><th>Model</th><th>Accuracy</th><th>Macro precision</th><th>Macro recall</th><th>Macro-F1</th><th>Poor recall</th></tr>
        {''.join(rows)}
      </table>
      <p class="muted">All figures are percentages. Macro-F1 is the selection metric.</p>
    </div>
    """
    return render_page("Evaluation", content)


@app.route("/about")
def about():
    if not logged_in():
        return redirect(url_for("login"))
    excluded = ", ".join(EXCLUDED_FROM_MODEL)
    content = f"""
    <div class="card">
      <h1>About this project</h1>
      <p>Dataset: {escape(REPORT['dataset'])}.</p>
      <p>Excellent = AA or BA. Average = BB, CB, CC or DC. Poor = DD or Fail.</p>
      <p>Columns not used in the model: {escape(excluded)}.</p>
      <p>Selected model: {escape(REPORT['best_model'])}. It is selected by macro-F1.</p>
      <p>This prediction is only for the project demo. It is not an official mark.</p>
    </div>
    """
    return render_page("About", content)


@app.route("/questions", methods=["GET", "POST"])
def questions():
    if role() != "Teacher":
        flash("The question bank is limited to the Teacher login.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "delete":
            delete_question(request.form.get("question_id", ""))
        else:
            add_question(
                request.form.get("topic", ""),
                request.form.get("question", ""),
                request.form.get("option_a", ""),
                request.form.get("option_b", ""),
                request.form.get("option_c", ""),
                request.form.get("option_d", ""),
                request.form.get("answer", "A"),
            )
        return redirect(url_for("questions"))
    rows = "".join(
        "<tr>"
        f"<td>{escape(row['question_id'])}</td>"
        f"<td>{escape(row['topic'])}</td>"
        f"<td>{escape(row['question'])}</td>"
        f"<td>{escape(row['answer'])}</td>"
        "<td><form method='post'><input type='hidden' name='action' value='delete'>"
        f"<input type='hidden' name='question_id' value='{escape(row['question_id'])}'>"
        "<button>Remove</button></form></td></tr>"
        for row in list_questions()
    )
    content = f"""
    <div class="card">
      <h1>Question bank</h1>
      <p>The teacher adds or removes questions. The student exam reads this list.</p>
      <table>
        <tr><th>Id</th><th>Topic</th><th>Question</th><th>Answer</th><th></th></tr>
        {rows}
      </table>
      <h2>Add a question</h2>
      <form method="post">
        <label>Topic</label><input name="topic" required>
        <label>Question</label><input name="question" required>
        <label>Option A</label><input name="option_a" required>
        <label>Option B</label><input name="option_b" required>
        <label>Option C</label><input name="option_c" required>
        <label>Option D</label><input name="option_d" required>
        <label>Correct option (A, B, C or D)</label><input name="answer" value="A" required>
        <p><button>Save question</button></p>
      </form>
    </div>
    """
    return render_page("Questions", content)


@app.route("/internals", methods=["GET", "POST"])
def internals():
    if role() != "Teacher":
        flash("Internal marks are limited to the Teacher login.")
        return redirect(url_for("dashboard"))
    message = ""
    if request.method == "POST":
        try:
            record = add_internal(
                request.form.get("student_name", ""),
                request.form.get("subject", ""),
                request.form.get("internal_marks", "0"),
                request.form.get("assignment_score", "0"),
                request.form.get("attendance_percent", "0"),
            )
            message = (
                f"<p>Saved. Combined score {escape(record['percent'])}% "
                f"falls in <strong>{escape(record['category'])}</strong>.</p>"
            )
        except ValueError:
            message = "<p>Enter numbers for marks and attendance.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(row['student_name'])}</td>"
        f"<td>{escape(row['subject'])}</td>"
        f"<td>{escape(row['internal_marks'])}</td>"
        f"<td>{escape(row['assignment_score'])}</td>"
        f"<td>{escape(row['attendance_percent'])}</td>"
        f"<td>{escape(row['percent'])}</td>"
        f"<td>{escape(row['category'])}</td></tr>"
        for row in list_internals()
    )
    ranked = sorted(
        (MARKS_REPORT or {}).get("compared", []),
        key=lambda item: item["exam_percent"],
        reverse=True,
    )
    compared = "".join(
        "<tr>"
        f"<td>{escape(item['student_name'])}</td>"
        f"<td>{item['exam_percent']:.1f}</td>"
        f"<td>{escape(item['actual'])}</td>"
        f"<td>{escape(item['predicted'])}</td>"
        f"<td>{index}</td></tr>"
        for index, item in enumerate(ranked, start=1)
    )
    content = f"""
    <div class="card">
      <h1>Internal marks</h1>
      <p>Internal marks are out of 30, assignment out of 20, and attendance is a percent.
      The score on this form is 50% internal, 30% assignment and 20% attendance.
      The table under the form is the sample marks file. Predicted is the out-of-fold category from those three inputs. Actual is the exam category.</p>
      {message}
      <table>
        <tr><th>Student</th><th>Subject</th><th>Internal</th><th>Assignment</th><th>Attendance</th><th>Score</th><th>Category</th></tr>
        {rows}
      </table>
      <form method="post">
        <label>Student name</label><input name="student_name" required>
        <label>Subject</label><input name="subject" required>
        <label>Internal marks (out of 30)</label><input name="internal_marks" required>
        <label>Assignment (out of 20)</label><input name="assignment_score" required>
        <label>Attendance percent</label><input name="attendance_percent" required>
        <p><button>Save marks</button></p>
      </form>
      <h2>Predicted and actual</h2>
      <table>
        <tr><th>Student</th><th>Exam %</th><th>Actual</th><th>Predicted</th><th>Rank</th></tr>
        {compared}
      </table>
    </div>
    """
    return render_page("Internal marks", content)


@app.route("/exam", methods=["GET", "POST"])
def exam():
    if role() != "Student":
        flash("The exam page is for the Student login.")
        return redirect(url_for("dashboard"))
    questions_now = list_questions()
    if request.method == "POST":
        score = 0
        for row in questions_now:
            chosen = request.form.get(row["question_id"], "").strip().upper()
            if chosen == row["answer"].strip().upper():
                score += 1
        attempt = save_attempt(session["username"], "Question bank", score, len(questions_now))
        return redirect(url_for("my_result", latest=attempt["attempt_id"]))
    blocks = []
    for row in questions_now:
        options = "".join(
            f"<label><input type='radio' name='{escape(row['question_id'])}' value='{letter}' required> "
            f"{letter}. {escape(row[field])}</label>"
            for letter, field in (
                ("A", "option_a"),
                ("B", "option_b"),
                ("C", "option_c"),
                ("D", "option_d"),
            )
        )
        blocks.append(
            f"<div class='card'><p><strong>{escape(row['question_id'])}. {escape(row['question'])}</strong></p>{options}</div>"
        )
    content = f"""
    <div class="card">
      <h1>Student exam</h1>
      <p>Answer every question and submit. The percentage is the actual result: Excellent from 75, Average from 40, and Poor below 40.
      My result also shows the predicted category from internal marks, assignment and attendance, and the rank by exam percent.</p>
    </div>
    <form method="post">{''.join(blocks)}<p><button>Submit exam</button></p></form>
    """
    return render_page("Exam", content)


@app.route("/my-result")
def my_result():
    if role() != "Student":
        flash("Exam results are shown on the Student login.")
        return redirect(url_for("dashboard"))
    username = session["username"]
    predicted = marks_prediction(username)
    model_name = (MARKS_REPORT or {}).get("best_model", "model")
    attempt_rows = list_attempts(username)
    rows = []
    for row in attempt_rows:
        rank, total = exam_rank(float(row["percent"]), username)
        rows.append(
            "<tr>"
            f"<td>{escape(row['attempt_id'])}</td>"
            f"<td>{escape(row['score'])}/{escape(row['total'])}</td>"
            f"<td>{escape(row['percent'])}</td>"
            f"<td>{escape(row['category'])}</td>"
            f"<td>{escape(predicted)}</td>"
            f"<td>{rank} of {total}</td></tr>"
        )
    content = f"""
    <div class="card">
      <h1>My exam result</h1>
      <p>Actual is the exam percentage band. Predicted is the {escape(model_name)} category from this login's internal marks, assignment and attendance. Rank uses the exam percent.</p>
      <table>
        <tr><th>Attempt</th><th>Score</th><th>Percent</th><th>Actual</th><th>Predicted</th><th>Rank</th></tr>
        {''.join(rows) or "<tr><td colspan='6'>No exam submitted yet.</td></tr>"}
      </table>
      <p><a href="{url_for('exam')}">Take the exam</a> or <a href="{url_for('predict')}">open the questionnaire prediction</a>.</p>
    </div>
    """
    return render_page("My result", content)


@app.route("/teachers", methods=["GET", "POST"])
def teachers():
    if role() != "Admin":
        flash("Adding a teacher is limited to the Admin login.")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        if request.form.get("action") == "remove":
            remove_teacher(request.form.get("teacher_name", ""))
        else:
            add_teacher(request.form.get("teacher_name", ""), request.form.get("subject", ""))
        return redirect(url_for("teachers"))
    rows = "".join(
        "<tr>"
        f"<td>{escape(row['teacher_name'])}</td>"
        f"<td>{escape(row['subject'])}</td>"
        "<td><form method='post'><input type='hidden' name='action' value='remove'>"
        f"<input type='hidden' name='teacher_name' value='{escape(row['teacher_name'])}'>"
        "<button>Remove</button></form></td></tr>"
        for row in list_teachers()
    )
    content = f"""
    <div class="card">
      <h1>Teachers</h1>
      <p>The admin keeps the list of class teachers. Login passwords stay in the demo accounts on the login page.</p>
      <table><tr><th>Name</th><th>Subject</th><th></th></tr>{rows}</table>
      <form method="post">
        <label>Teacher name</label><input name="teacher_name" required>
        <label>Subject</label><input name="subject" required>
        <p><button>Add teacher</button></p>
      </form>
    </div>
    """
    return render_page("Teachers", content)


if __name__ == "__main__":
    boot()
    # Port 5000 is taken by macOS AirPlay Receiver, which answers with HTTP 403.
    app.run(host="127.0.0.1", port=8080, debug=False)
