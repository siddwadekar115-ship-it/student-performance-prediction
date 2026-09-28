"""Question bank, internal marks and exam attempts for the demo website."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
QUESTIONS = DATA / "questions.csv"
INTERNALS = DATA / "internal_marks.csv"
ATTEMPTS = DATA / "exam_attempts.csv"
TEACHERS = DATA / "teachers.csv"
COLLEGE = DATA / "college_marks.csv"

QUESTION_FIELDS = [
    "question_id",
    "topic",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "answer",
]
INTERNAL_FIELDS = [
    "record_id",
    "student_name",
    "subject",
    "internal_marks",
    "assignment_score",
    "attendance_percent",
    "percent",
    "category",
]
ATTEMPT_FIELDS = ["attempt_id", "username", "topic", "score", "total", "percent", "category"]
TEACHER_FIELDS = ["teacher_name", "subject"]
COLLEGE_FIELDS = [
    "student_name",
    "internal_marks",
    "assignment_score",
    "attendance_percent",
    "exam_percent",
    "actual_category",
]

SEED_QUESTIONS = [
    ("Study habits", "How many hours of self study are generally suggested on a working day?", "Less than 1 hour", "1 to 2 hours", "No study is needed", "Only before the exam night", "B"),
    ("Attendance", "Regular class attendance mainly helps a student to", "Skip the textbook", "Follow the class topics on time", "Avoid all assignments", "Reduce study hours to zero", "B"),
    ("Notes", "Taking notes in class is useful because", "Notes replace the final exam", "Notes help revision later", "Notes are submitted as the only mark", "Notes are optional for every subject", "B"),
    ("Assignment", "An assignment score is used by a teacher to", "Replace attendance", "See how the student completed the given work", "Decide the bus route", "Remove the internal exam", "B"),
    ("Internal marks", "Internal assessment is conducted", "Only after the degree is finished", "During the semester, before the final exam", "By the student alone at home with no record", "Instead of all classes", "B"),
    ("Revision", "Reading the notes before a test helps a student to", "Forget the topic", "Recall the points taught in class", "Skip the question paper", "Change the syllabus", "B"),
    ("Time", "A weekly study plan is prepared so that", "Every subject gets some time", "Only one subject is opened", "The exam date can be ignored", "Attendance is not required", "A"),
    ("Support", "If a student is weak in one subject, the useful step is", "Hide the marks", "Ask the teacher and revise that subject", "Stop attending all classes", "Copy another student's paper", "B"),
]


def _read(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def ensure_files() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if not QUESTIONS.exists():
        rows = []
        for index, item in enumerate(SEED_QUESTIONS, start=1):
            topic, question, a, b, c, d, answer = item
            rows.append(
                {
                    "question_id": f"Q{index}",
                    "topic": topic,
                    "question": question,
                    "option_a": a,
                    "option_b": b,
                    "option_c": c,
                    "option_d": d,
                    "answer": answer,
                }
            )
        _write(QUESTIONS, QUESTION_FIELDS, rows)
    if not INTERNALS.exists():
        _write(INTERNALS, INTERNAL_FIELDS, [])
    if not ATTEMPTS.exists():
        _write(ATTEMPTS, ATTEMPT_FIELDS, [])
    if not TEACHERS.exists():
        _write(
            TEACHERS,
            TEACHER_FIELDS,
            [{"teacher_name": "Class Teacher", "subject": "General"}],
        )
    if not COLLEGE.exists():
        _write(COLLEGE, COLLEGE_FIELDS, _sample_college_rows())


def _sample_college_rows() -> list[dict]:
    """Sample marks for the college module. Not the UCI file."""
    import numpy as np

    rng = np.random.default_rng(42)
    count = 90
    internal = rng.integers(6, 31, count)
    assignment = rng.integers(2, 21, count)
    attendance = rng.integers(35, 101, count)
    signal = (internal / 30) * 45 + (assignment / 20) * 25 + (attendance / 100) * 30
    exam = np.clip(signal + rng.normal(0, 14, count), 0, 100)
    rows = []
    for index in range(count):
        name = "student" if index == 0 else f"S{index:02d}"
        percent = float(exam[index])
        rows.append(
            {
                "student_name": name,
                "internal_marks": str(int(internal[index])),
                "assignment_score": str(int(assignment[index])),
                "attendance_percent": str(int(attendance[index])),
                "exam_percent": f"{percent:.1f}",
                "actual_category": category_from_percent(percent),
            }
        )
    return rows


def list_college() -> list[dict]:
    ensure_files()
    return _read(COLLEGE, COLLEGE_FIELDS)


def college_row(student_name: str) -> dict | None:
    for row in list_college():
        if row["student_name"] == student_name:
            return row
    return None


def exam_rank(percent: float, student_name: str) -> tuple[int, int]:
    others = [row for row in list_college() if row["student_name"] != student_name]
    better = sum(1 for row in others if float(row["exam_percent"]) > percent)
    return better + 1, len(others) + 1


def category_from_percent(percent: float) -> str:
    if percent >= 75:
        return "Excellent"
    if percent >= 40:
        return "Average"
    return "Poor"


def list_questions() -> list[dict]:
    ensure_files()
    return _read(QUESTIONS, QUESTION_FIELDS)


def add_question(topic, question, option_a, option_b, option_c, option_d, answer) -> None:
    rows = list_questions()
    next_id = f"Q{len(rows) + 1}"
    rows.append(
        {
            "question_id": next_id,
            "topic": topic.strip(),
            "question": question.strip(),
            "option_a": option_a.strip(),
            "option_b": option_b.strip(),
            "option_c": option_c.strip(),
            "option_d": option_d.strip(),
            "answer": answer.strip().upper(),
        }
    )
    _write(QUESTIONS, QUESTION_FIELDS, rows)


def delete_question(question_id: str) -> None:
    rows = [row for row in list_questions() if row["question_id"] != question_id]
    _write(QUESTIONS, QUESTION_FIELDS, rows)


def list_internals() -> list[dict]:
    ensure_files()
    return _read(INTERNALS, INTERNAL_FIELDS)


def add_internal(student_name, subject, internal_marks, assignment_score, attendance_percent) -> dict:
    rows = list_internals()
    internal = float(internal_marks)
    assignment = float(assignment_score)
    attendance = float(attendance_percent)
    # Internal is out of 30, assignment out of 20. Attendance is already a percent.
    academic = ((internal / 30) * 50) + ((assignment / 20) * 30) + ((attendance / 100) * 20)
    record = {
        "record_id": f"I{len(rows) + 1}",
        "student_name": student_name.strip(),
        "subject": subject.strip(),
        "internal_marks": internal_marks,
        "assignment_score": assignment_score,
        "attendance_percent": attendance_percent,
        "category": category_from_percent(academic),
        "percent": f"{academic:.1f}",
    }
    rows.append(record)
    _write(INTERNALS, INTERNAL_FIELDS, rows)
    return record


def list_attempts(username: str | None = None) -> list[dict]:
    ensure_files()
    rows = _read(ATTEMPTS, ATTEMPT_FIELDS)
    if username is None:
        return rows
    return [row for row in rows if row["username"] == username]


def save_attempt(username: str, topic: str, score: int, total: int) -> dict:
    rows = list_attempts()
    percent = (score / total * 100) if total else 0
    record = {
        "attempt_id": f"A{len(rows) + 1}",
        "username": username,
        "topic": topic,
        "score": str(score),
        "total": str(total),
        "percent": f"{percent:.1f}",
        "category": category_from_percent(percent),
    }
    rows.append(record)
    _write(ATTEMPTS, ATTEMPT_FIELDS, rows)
    return record


def list_teachers() -> list[dict]:
    ensure_files()
    return _read(TEACHERS, TEACHER_FIELDS)


def add_teacher(teacher_name: str, subject: str) -> None:
    rows = list_teachers()
    rows.append({"teacher_name": teacher_name.strip(), "subject": subject.strip()})
    _write(TEACHERS, TEACHER_FIELDS, rows)


def remove_teacher(teacher_name: str) -> None:
    rows = [row for row in list_teachers() if row["teacher_name"] != teacher_name]
    _write(TEACHERS, TEACHER_FIELDS, rows)
