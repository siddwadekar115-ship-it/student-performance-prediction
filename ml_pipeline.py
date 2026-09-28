"""Student performance prediction.

Reads the UCI dataset of 145 students and trains five classifiers.
Grade, CGPA, course id and sex are not used as inputs.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=r"The `probability` parameter was deprecated",
    category=FutureWarning,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "uci_student_performance.csv"
RESULTS_DIR = ROOT / "results"

CATEGORIES = ["Excellent", "Average", "Poor"]
GRADE_TO_LETTER = {
    0: "Fail",
    1: "DD",
    2: "DC",
    3: "CC",
    4: "CB",
    5: "BB",
    6: "BA",
    7: "AA",
}
LETTER_TO_CATEGORY = {
    "AA": "Excellent",
    "BA": "Excellent",
    "BB": "Average",
    "CB": "Average",
    "CC": "Average",
    "DC": "Average",
    "DD": "Poor",
    "Fail": "Poor",
}

# UCI variable numbers, in file order. Codes are the published data dictionary.
COLUMN_SPECS = [
    ("1", "Student_Age", {1: "18-21", 2: "22-25", 3: "Above 26"}),
    ("2", "Sex", {1: "Female", 2: "Male"}),
    ("3", "High_School_Type", {1: "Private", 2: "State", 3: "Other"}),
    ("4", "Scholarship", {1: "None", 2: "25%", 3: "50%", 4: "75%", 5: "Full"}),
    ("5", "Additional_Work", {1: "Yes", 2: "No"}),
    ("6", "Sports_Activity", {1: "Yes", 2: "No"}),
    ("7", "Partner", {1: "Yes", 2: "No"}),
    (
        "8",
        "Salary",
        {
            1: "USD 135-200",
            2: "USD 201-270",
            3: "USD 271-340",
            4: "USD 341-410",
            5: "Above USD 410",
        },
    ),
    (
        "9",
        "Transportation",
        {1: "Bus", 2: "Private car or taxi", 3: "Bicycle", 4: "Other"},
    ),
    (
        "10",
        "Accommodation",
        {1: "Rental", 2: "Dormitory", 3: "With family", 4: "Other"},
    ),
    (
        "11",
        "Mother_Education",
        {
            1: "Primary school",
            2: "Secondary school",
            3: "High school",
            4: "University",
            5: "MSc",
            6: "PhD",
        },
    ),
    (
        "12",
        "Father_Education",
        {
            1: "Primary school",
            2: "Secondary school",
            3: "High school",
            4: "University",
            5: "MSc",
            6: "PhD",
        },
    ),
    ("13", "Siblings", {1: "1", 2: "2", 3: "3", 4: "4", 5: "5 or above"}),
    (
        "14",
        "Parental_Status",
        {1: "Married", 2: "Divorced", 3: "One or both parents died"},
    ),
    (
        "15",
        "Mother_Occupation",
        {
            1: "Retired",
            2: "Housewife",
            3: "Government officer",
            4: "Private sector employee",
            5: "Self-employment",
            6: "Other",
        },
    ),
    (
        "16",
        "Father_Occupation",
        {
            1: "Retired",
            2: "Government officer",
            3: "Private sector employee",
            4: "Self-employment",
            5: "Other",
        },
    ),
    (
        "17",
        "Weekly_Study_Hours",
        {
            1: "None",
            2: "Less than 5 hours",
            3: "6-10 hours",
            4: "11-20 hours",
            5: "More than 20 hours",
        },
    ),
    (
        "18",
        "Reading_Non_Scientific",
        {1: "None", 2: "Sometimes", 3: "Often"},
    ),
    (
        "19",
        "Reading_Scientific",
        {1: "None", 2: "Sometimes", 3: "Often"},
    ),
    ("20", "Seminar_Attendance", {1: "Yes", 2: "No"}),
    (
        "21",
        "Project_Impact",
        {1: "Positive", 2: "Negative", 3: "Neutral"},
    ),
    (
        "22",
        "Class_Attendance",
        {1: "Always", 2: "Sometimes", 3: "Never"},
    ),
    (
        "23",
        "Midterm_Preparation_Company",
        {1: "Alone", 2: "With friends", 3: "Not applicable"},
    ),
    (
        "24",
        "Midterm_Preparation_Timing",
        {
            1: "Closest date to the exam",
            2: "Regularly during the semester",
            3: "Never",
        },
    ),
    ("25", "Taking_Notes", {1: "Never", 2: "Sometimes", 3: "Always"}),
    ("26", "Listening_in_Class", {1: "Never", 2: "Sometimes", 3: "Always"}),
    ("27", "Discussion", {1: "Never", 2: "Sometimes", 3: "Always"}),
    (
        "28",
        "Flip_Classroom",
        {1: "Not useful", 2: "Useful", 3: "Not applicable"},
    ),
    (
        "29",
        "Last_Semester_CGPA",
        {
            1: "Below 2.00",
            2: "2.00-2.49",
            3: "2.50-2.99",
            4: "3.00-3.49",
            5: "Above 3.49",
        },
    ),
    (
        "30",
        "Expected_Graduation_CGPA",
        {
            1: "Below 2.00",
            2: "2.00-2.49",
            3: "2.50-2.99",
            4: "3.00-3.49",
            5: "Above 3.49",
        },
    ),
]

# Grade and both CGPA fields are outcomes. Course ID memorizes which class
# the student sat. Sex is not an academic action a teacher can take.
EXCLUDED_FROM_MODEL = [
    "Student_ID",
    "Grade",
    "Performance_Category",
    "Last_Semester_CGPA",
    "Expected_Graduation_CGPA",
    "Course_ID",
    "Sex",
]

RANDOM_STATE = 42


def load_raw_frame(path: Path | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path or DATA_FILE)
    if "GRADE" not in frame.columns:
        raise ValueError("The CSV must contain the UCI GRADE column.")
    return frame


def decode_frame(raw: pd.DataFrame) -> pd.DataFrame:
    decoded = pd.DataFrame()
    decoded["Student_ID"] = raw["STUDENT ID"].astype(str)
    for source, name, mapping in COLUMN_SPECS:
        decoded[name] = raw[source].map(mapping)
        unknown = decoded[name].isna() & raw[source].notna()
        if unknown.any():
            bad = sorted(raw.loc[unknown, source].unique().tolist())
            raise ValueError(f"Column {name} has codes outside the UCI dictionary: {bad}")
    decoded["Course_ID"] = raw["COURSE ID"].map(lambda value: f"Course {int(value)}")
    decoded["Grade"] = raw["GRADE"].map(GRADE_TO_LETTER)
    if decoded["Grade"].isna().any():
        raise ValueError("GRADE contains a code outside 0-7.")
    decoded["Performance_Category"] = decoded["Grade"].map(LETTER_TO_CATEGORY)
    return decoded


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in EXCLUDED_FROM_MODEL]


def build_models() -> dict[str, object]:
    return {
        "Decision Tree": DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Naive Bayes": GaussianNB(),
        "SVM": SVC(
            kernel="rbf",
            class_weight="balanced",
            probability=True,
            random_state=RANDOM_STATE,
        ),
    }


def make_pipeline(classifier, columns: list[str]) -> Pipeline:
    encoder = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocessor = ColumnTransformer([("cat", encoder, columns)])
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )


def _scores(y_true, y_pred) -> dict[str, float]:
    labels = CATEGORIES
    poor_recall = recall_score(
        y_true,
        y_pred,
        labels=["Poor"],
        average="macro",
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(
            precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "recall_macro": float(
            recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "f1_macro": float(
            f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        ),
        "poor_recall": float(poor_recall),
    }


def evaluate(frame: pd.DataFrame | None = None) -> dict:
    data = frame if frame is not None else decode_frame(load_raw_frame())
    columns = feature_columns(data)
    features = data[columns]
    target = data["Performance_Category"]
    counts = target.value_counts().to_dict()
    majority = max(CATEGORIES, key=lambda label: int(counts.get(label, 0)))

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    train_x, test_x, train_y, test_y = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=target,
    )

    model_reports = {}
    for name, classifier in build_models().items():
        fold_rows = []
        for train_index, test_index in cv.split(features, target):
            pipe = make_pipeline(classifier, columns)
            pipe.fit(features.iloc[train_index], target.iloc[train_index])
            predicted = pipe.predict(features.iloc[test_index])
            fold_rows.append(_scores(target.iloc[test_index], predicted))

        holdout_pipe = make_pipeline(classifier, columns)
        holdout_pipe.fit(train_x, train_y)
        holdout_pred = holdout_pipe.predict(test_x)
        matrix = confusion_matrix(test_y, holdout_pred, labels=CATEGORIES).tolist()
        cv_summary = {
            metric: {
                "mean": float(np.mean([row[metric] for row in fold_rows])),
                "std": float(np.std([row[metric] for row in fold_rows], ddof=1)),
            }
            for metric in fold_rows[0]
        }
        model_reports[name] = {
            "cv": cv_summary,
            "holdout": _scores(test_y, holdout_pred),
            "confusion_matrix": matrix,
            "holdout_size": int(len(test_y)),
        }

    best_name = max(
        model_reports,
        key=lambda name: (
            model_reports[name]["cv"]["f1_macro"]["mean"],
            model_reports[name]["cv"]["poor_recall"]["mean"],
        ),
    )

    baseline_folds = []
    for _, test_index in cv.split(features, target):
        predicted = np.full(len(test_index), majority)
        baseline_folds.append(_scores(target.iloc[test_index], predicted))

    top_features = _top_features(data, columns, best_name)
    tree_features = _top_features(data, columns, "Decision Tree")
    sensitivity = {
        "deployed_features": _cv_macro_f1(data, columns),
        "plus_course_id": _cv_macro_f1(data, columns + ["Course_ID"]),
        "plus_last_semester_cgpa": _cv_macro_f1(
            data, columns + ["Last_Semester_CGPA"]
        ),
    }

    return {
        "dataset": "UCI Higher Education Students Performance Evaluation (id 856)",
        "citation": "Yilmaz, N. and Sekeroglu, B. (2019). https://doi.org/10.24432/C51G82",
        "n_rows": int(len(data)),
        "class_counts": {label: int(counts.get(label, 0)) for label in CATEGORIES},
        "majority_class": majority,
        "majority_baseline_cv_accuracy": {
            "mean": float(np.mean([row["accuracy"] for row in baseline_folds])),
            "std": float(np.std([row["accuracy"] for row in baseline_folds], ddof=1)),
        },
        "features": columns,
        "excluded_from_model": EXCLUDED_FROM_MODEL,
        "label_rule": {
            "Excellent": "AA, BA",
            "Average": "BB, CB, CC, DC",
            "Poor": "DD, Fail",
        },
        "validation": {
            "primary": "5-fold stratified cross-validation, shuffle, random_state=42",
            "secondary": "80/20 stratified holdout, random_state=42",
            "selection": "Highest mean macro-F1. Tie broken by mean recall of Poor.",
        },
        "models": model_reports,
        "best_model": best_name,
        "top_features": top_features,
        "decision_tree_features": tree_features,
        "sensitivity": sensitivity,
    }


def _cv_macro_f1(data: pd.DataFrame, columns: list[str]) -> dict[str, float]:
    target = data["Performance_Category"]
    features = data[columns]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    summary = {}
    for name, classifier in build_models().items():
        scores = []
        accuracies = []
        for train_index, test_index in cv.split(features, target):
            pipe = make_pipeline(classifier, columns)
            pipe.fit(features.iloc[train_index], target.iloc[train_index])
            predicted = pipe.predict(features.iloc[test_index])
            scores.append(
                f1_score(
                    target.iloc[test_index],
                    predicted,
                    labels=CATEGORIES,
                    average="macro",
                    zero_division=0,
                )
            )
            accuracies.append(accuracy_score(target.iloc[test_index], predicted))
        summary[name] = {
            "f1_macro_mean": float(np.mean(scores)),
            "accuracy_mean": float(np.mean(accuracies)),
        }
    return summary


def _top_features(data: pd.DataFrame, columns: list[str], model_name: str) -> list[dict]:
    classifier = build_models()[model_name]
    pipe = make_pipeline(classifier, columns)
    pipe.fit(data[columns], data["Performance_Category"])
    model = pipe.named_steps["classifier"]
    if not hasattr(model, "feature_importances_"):
        return []
    names = pipe.named_steps["preprocessor"].get_feature_names_out()
    pairs = sorted(
        zip(names, model.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )[:8]
    cleaned = []
    for name, value in pairs:
        label = str(name)
        if label.startswith("cat__"):
            label = label[len("cat__") :]
        cleaned.append({"feature": label, "importance": float(value)})
    return cleaned


MARK_COLUMNS = ["internal_marks", "assignment_score", "attendance_percent"]


def _numeric_pipe(classifier) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )


def load_college_frame() -> pd.DataFrame:
    from college_records import list_college

    frame = pd.DataFrame(list_college())
    for column in MARK_COLUMNS + ["exam_percent"]:
        frame[column] = frame[column].astype(float)
    return frame


def evaluate_marks(frame: pd.DataFrame | None = None) -> dict:
    data = frame if frame is not None else load_college_frame()
    features = data[MARK_COLUMNS]
    target = data["actual_category"]
    counts = target.value_counts().to_dict()
    majority = max(CATEGORIES, key=lambda label: int(counts.get(label, 0)))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    model_reports = {}
    oof_by_model = {}
    for name, classifier in build_models().items():
        predicted_all = np.empty(len(data), dtype=object)
        fold_rows = []
        for train_index, test_index in cv.split(features, target):
            pipe = _numeric_pipe(classifier)
            pipe.fit(features.iloc[train_index], target.iloc[train_index])
            predicted = pipe.predict(features.iloc[test_index])
            predicted_all[test_index] = predicted
            fold_rows.append(_scores(target.iloc[test_index], predicted))
        oof_by_model[name] = predicted_all
        model_reports[name] = {
            "cv": {
                metric: {
                    "mean": float(np.mean([row[metric] for row in fold_rows])),
                    "std": float(np.std([row[metric] for row in fold_rows], ddof=1)),
                }
                for metric in fold_rows[0]
            }
        }
    best_name = max(
        model_reports,
        key=lambda name: (
            model_reports[name]["cv"]["f1_macro"]["mean"],
            model_reports[name]["cv"]["poor_recall"]["mean"],
        ),
    )
    baseline_folds = []
    for _, test_index in cv.split(features, target):
        predicted = np.full(len(test_index), majority)
        baseline_folds.append(_scores(target.iloc[test_index], predicted))
    compared = []
    for index, row in data.reset_index(drop=True).iterrows():
        compared.append(
            {
                "student_name": row["student_name"],
                "actual": row["actual_category"],
                "predicted": str(oof_by_model[best_name][index]),
                "exam_percent": float(row["exam_percent"]),
            }
        )
    return {
        "n_rows": int(len(data)),
        "class_counts": {label: int(counts.get(label, 0)) for label in CATEGORIES},
        "majority_class": majority,
        "majority_baseline_cv_accuracy": {
            "mean": float(np.mean([row["accuracy"] for row in baseline_folds])),
            "std": float(np.std([row["accuracy"] for row in baseline_folds], ddof=1)),
        },
        "features": MARK_COLUMNS,
        "label": "exam category from the exam percent",
        "models": model_reports,
        "best_model": best_name,
        "compared": compared,
    }


def fit_marks_model(frame: pd.DataFrame | None = None):
    data = frame if frame is not None else load_college_frame()
    report = evaluate_marks(data)
    pipe = _numeric_pipe(build_models()[report["best_model"]])
    pipe.fit(data[MARK_COLUMNS], data["actual_category"])
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stored = {key: value for key, value in report.items() if key != "compared"}
    (RESULTS_DIR / "marks_metrics.json").write_text(json.dumps(stored, indent=2))
    return pipe, report


def fit_best(frame: pd.DataFrame | None = None):
    data = frame if frame is not None else decode_frame(load_raw_frame())
    report = evaluate(data)
    columns = feature_columns(data)
    model_name = report["best_model"]
    pipe = make_pipeline(build_models()[model_name], columns)
    pipe.fit(data[columns], data["Performance_Category"])
    return pipe, report, data


def save_results(report: dict | None = None) -> dict:
    report = report or evaluate()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(report, indent=2))
    _plot_distribution(report)
    _plot_models(report)
    _plot_confusion(report)
    return report


def _plot_distribution(report: dict) -> None:
    labels = CATEGORIES
    values = [report["class_counts"][label] for label in labels]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color=["#1f4e79", "#5b7c99", "#8d99a6"])
    ax.set_ylabel("Students")
    ax.set_xlabel("Performance category")
    ax.set_title("Students in each performance category (n = 145)")
    for index, value in enumerate(values):
        ax.text(index, value + 0.8, str(value), ha="center")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "class_distribution.png", dpi=140)
    plt.close(fig)


def _plot_models(report: dict) -> None:
    names = list(report["models"])
    means = [report["models"][name]["cv"]["f1_macro"]["mean"] for name in names]
    errors = [report["models"][name]["cv"]["f1_macro"]["std"] for name in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, means, yerr=errors, color="#1f4e79", capsize=4)
    ax.set_ylabel("Mean macro-F1")
    ax.set_xlabel("Algorithm")
    ax.set_ylim(0, 1)
    ax.set_title("Five-fold stratified cross-validation (mean ± sample std)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "model_comparison.png", dpi=140)
    plt.close(fig)


def _plot_confusion(report: dict) -> None:
    name = report["best_model"]
    matrix = np.array(report["models"][name]["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(3), CATEGORIES)
    ax.set_yticks(range(3), CATEGORIES)
    ax.set_xlabel("Predicted category")
    ax.set_ylabel("Actual category")
    ax.set_title(f"Holdout confusion matrix: {name}")
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            ax.text(col, row, int(matrix[row, col]), ha="center", va="center")
    fig.colorbar(image, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    saved = save_results()
    print(f"Best model: {saved['best_model']}")
    best = saved["models"][saved["best_model"]]
    print(
        "CV macro-F1: "
        f"{best['cv']['f1_macro']['mean']:.3f} ± {best['cv']['f1_macro']['std']:.3f}"
    )
    print(f"Wrote {RESULTS_DIR / 'metrics.json'}")
