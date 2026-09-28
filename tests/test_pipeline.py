import unittest

import app as webapp
from ml_pipeline import (
    CATEGORIES,
    EXCLUDED_FROM_MODEL,
    LETTER_TO_CATEGORY,
    decode_frame,
    evaluate,
    feature_columns,
    load_raw_frame,
)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_raw_frame()
        cls.frame = decode_frame(cls.raw)
        cls.report = evaluate(cls.frame)

    def test_row_count_and_labels(self):
        self.assertEqual(len(self.frame), 145)
        self.assertEqual(set(self.frame["Performance_Category"]), set(CATEGORIES))
        self.assertEqual(sum(self.report["class_counts"].values()), 145)

    def test_grade_map_matches_synopsis_bands(self):
        self.assertEqual(LETTER_TO_CATEGORY["AA"], "Excellent")
        self.assertEqual(LETTER_TO_CATEGORY["DC"], "Average")
        self.assertEqual(LETTER_TO_CATEGORY["Fail"], "Poor")

    def test_leakage_columns_are_not_features(self):
        columns = feature_columns(self.frame)
        for banned in (
            "Grade",
            "Last_Semester_CGPA",
            "Expected_Graduation_CGPA",
            "Student_ID",
            "Course_ID",
            "Sex",
        ):
            self.assertNotIn(banned, columns)
        self.assertIn("Class_Attendance", columns)
        self.assertIn("Weekly_Study_Hours", columns)

    def test_every_code_decodes(self):
        self.assertFalse(self.frame.drop(columns=[]).isna().any().any())

    def test_five_models_and_a_selected_winner(self):
        self.assertEqual(
            set(self.report["models"]),
            {"Decision Tree", "Logistic Regression", "Random Forest", "Naive Bayes", "SVM"},
        )
        self.assertIn(self.report["best_model"], self.report["models"])
        winner = self.report["models"][self.report["best_model"]]
        self.assertGreater(winner["cv"]["f1_macro"]["mean"], 0)
        self.assertEqual(len(winner["confusion_matrix"]), 3)

    def test_excluded_list_documents_cgpa(self):
        self.assertIn("Last_Semester_CGPA", EXCLUDED_FROM_MODEL)
        self.assertIn("Expected_Graduation_CGPA", EXCLUDED_FROM_MODEL)


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.boot()
        cls.client = webapp.app.test_client()

    def test_student_cannot_open_records(self):
        self.client.post("/", data={"username": "student", "password": "student123"})
        response = self.client.get("/students", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"limited to Admin and Teacher", response.data)
        self.client.get("/logout")

    def test_teacher_can_open_evaluation(self):
        self.client.post("/", data={"username": "teacher", "password": "teacher123"})
        response = self.client.get("/evaluation")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Macro-F1", response.data)
        self.client.get("/logout")

    def test_prediction_returns_a_known_category(self):
        self.client.post("/", data={"username": "admin", "password": "admin123"})
        row = self.client.get("/predict")
        self.assertEqual(row.status_code, 200)
        sample = {
            column: webapp.FRAME[column].iloc[0]
            for column in webapp.COLUMNS
        }
        response = self.client.post("/predict", data=sample)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertTrue(any(label in body for label in CATEGORIES))
        self.client.get("/logout")

    def test_student_exam_and_blocked_question_editor(self):
        self.client.post("/", data={"username": "student", "password": "student123"})
        exam = self.client.get("/exam")
        self.assertEqual(exam.status_code, 200)
        self.assertIn(b"Student exam", exam.data)
        blocked = self.client.get("/questions", follow_redirects=True)
        self.assertIn(b"question bank", blocked.data.lower())
        self.client.get("/logout")

    def test_teacher_internal_marks_page(self):
        self.client.post("/", data={"username": "teacher", "password": "teacher123"})
        page = self.client.get("/internals")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Internal marks", page.data)
        self.client.get("/logout")

    def test_admin_teacher_list(self):
        self.client.post("/", data={"username": "admin", "password": "admin123"})
        page = self.client.get("/teachers")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Teachers", page.data)
        self.client.get("/logout")

    def test_result_shows_prediction_and_rank(self):
        from college_records import list_questions

        self.client.post("/", data={"username": "student", "password": "student123"})
        answers = {row["question_id"]: row["answer"] for row in list_questions()}
        response = self.client.post("/exam", data=answers, follow_redirects=True)
        body = response.get_data(as_text=True)
        self.assertIn("Predicted", body)
        self.assertIn("Rank", body)
        self.assertIn("Actual", body)
        self.client.get("/logout")

    def test_teacher_sees_predicted_and_actual(self):
        self.client.post("/", data={"username": "teacher", "password": "teacher123"})
        page = self.client.get("/internals")
        self.assertIn(b"Predicted and actual", page.data)
        self.client.get("/logout")

    def test_bad_login_is_rejected(self):
        response = self.client.post(
            "/",
            data={"username": "admin", "password": "wrong"},
        )
        self.assertIn(b"Invalid username or password", response.data)


if __name__ == "__main__":
    unittest.main()
