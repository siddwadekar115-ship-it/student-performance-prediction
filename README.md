# Student Performance Prediction

BCA project for Siddhant Krushnasa Wadekar (BCA22773), University of Mysore.

The program trains five classifiers on the UCI Higher Education Students Performance Evaluation dataset (145 students) and serves a local Admin / Teacher / Student demo.

## Run

From this folder, with the dependencies in `requirements.txt` installed:

```bash
python -m unittest tests.test_pipeline -v
python app.py
```

Open http://127.0.0.1:8080

Demo logins, for a viva on this machine only:

- admin / admin123
- teacher / teacher123
- student / student123

## What the result actually is

The deployed model does not use the course grade, either CGPA field, course ID, or sex. On five-fold stratified cross-validation it does not beat a baseline that always predicts Average. Chapter VII of `Project_Report.docx` reports the measured figures. Do not describe the model as an accurate early-warning system.

## Report

`Project_Report.pdf` is the report for the portal. `Self_Declaration.pdf` is the separate declaration. The Word files with the same names are the editable copies. `Project final.docx` is the old file and is left unchanged.

The teacher login has the question bank and internal marks. The student login has the exam. Those marks are not used to train the model.

Regenerate after a training run with:

```bash
python report/build_report.py
python report/to_pdf.py
```

Sign the declaration only after the department plagiarism check. Do not write a percentage before that check. Print the report on one side and hard-bind it in black, blue, or brown. Post that copy to the Department of Online Programs, Moulya Bhavan, Manasagangothri, Mysuru, within 15 days of the portal upload.
