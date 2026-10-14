"""запуск расчета результатов сессии."""

from pathlib import Path

from calc import make_rating, subject_totals
from data_io import load_data
from report import save_chart, save_tables, summary_text


def main():
    """читает папку data и сохраняет результаты в output."""
    base = Path(__file__).resolve().parent
    data, out = base / "data", base / "output"
    out.mkdir(exist_ok=True)
    students, plan, grades, rules = load_data(
        data / "plan.csv", data / "students.csv", data / "grades.csv",
        data / "rules.json", out / "errors.log",
    )
    rows = make_rating(students, plan, grades, rules)
    subjects = subject_totals(students, plan, grades, rules)
    save_tables(rows, out)
    save_chart(subjects, out / "average_grades.png")
    summary = summary_text(rows, subjects)
    (out / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
