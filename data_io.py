"""чтение справочников и проверка экзаменационных ведомостей."""

import csv
import json
from datetime import date
from pathlib import Path


def log_error(log, source, line, student, discipline, reason):
    """записывает причину проблемы, студента, дисциплину и номер строки."""
    log.write(
        f"{source}:{line}; студент={student or '-'}; "
        f"дисциплина={discipline or '-'}; {reason}\n"
    )


def read_csv(path, fields, log):
    """читает строки CSV, убирает пробелы и отмечает ошибки структуры."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        if reader.fieldnames != fields:
            raise ValueError(f"В {path.name} ожидаются: {';'.join(fields)}")
        for line, row in enumerate(reader, 2):
            args = (log, path.name, line, row.get("student_id"),
                    row.get("discipline"))
            if None in row or None in row.values():
                log_error(*args, "Неверное количество полей; строка пропущена")
                continue
            for key, value in row.items():
                row[key] = value.strip()
                if row[key] != value:
                    log_error(*args, f"Удалены пробелы в поле {key}")
            yield line, row


def read_rules(path):
    """загружает обозначения оценок и правила назначения стипендий."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_plan(path, rules, log):
    """читает план, пропуская пустые, неизвестные и повторные дисциплины."""
    plan = {}
    kinds = ("экзамен", rules["credit_aliases"]["зачет"])
    for line, row in read_csv(path, ["discipline", "type"], log):
        name, kind = row["discipline"], row["type"].casefold()
        if not name or kind not in kinds or name in plan:
            log_error(log, Path(path).name, line, "", name,
                      "Пустая, повторная дисциплина или неверный вид контроля")
        else:
            plan[name] = kind
    return plan


def read_students(path, log):
    """читает студентов, проверяя заполнение полей и уникальность номера."""
    students = {}
    fields = ["student_id", "fio", "group", "funding"]
    for line, row in read_csv(path, fields, log):
        sid = row["student_id"]
        if not all(row.values()) or sid in students:
            log_error(log, Path(path).name, line, sid, "",
                      "Пустое поле или повтор номера; строка пропущена")
        else:
            row["funding"] = row["funding"].casefold()
            students[sid] = row
    return students


def parse_mark(raw, kind, rules):
    """возвращает допустимую оценку и признак изменения обозначения."""
    value = raw.casefold()
    key = "grade_aliases" if kind == "экзамен" else "credit_aliases"
    aliases = {key.casefold(): val for key, val in rules[key].items()}
    if value == rules["absent_mark"].casefold():
        return rules["absent_mark"], raw != rules["absent_mark"]
    if value in aliases:
        return aliases[value], True
    if kind == "экзамен":
        try:
            mark = int(value)
        except ValueError:
            return None, False
        if mark in rules["valid_grades"]:
            return mark, raw != str(mark)
    else:
        for mark in rules["credit_values"]:
            if value == mark.casefold():
                return mark, raw != mark
    return None, False


def read_grades(path, students, plan, rules, log):
    """проверяет попытки и оставляет последнюю допустимую по каждой паре."""
    grades = {}
    fields = ["student_id", "discipline", "date", "grade"]
    passed = rules["credit_aliases"]["зачет"]
    for line, row in read_csv(path, fields, log):
        sid, subject = row["student_id"], row["discipline"]
        args = (log, Path(path).name, line, sid, subject)
        if sid not in students or subject not in plan:
            log_error(*args, "Неизвестный студент или дисциплина; пропущено")
            continue
        value, changed = parse_mark(row["grade"], plan[subject], rules)
        try:
            day = date.fromisoformat(row["date"])
        except ValueError:
            day = None
            log_error(*args, "Некорректная дата; строка пропущена")
        if value is None:
            log_error(*args, f"Недопустимая оценка {row['grade']!r}")
        if value is None or day is None:
            continue
        if changed:
            log_error(*args, f"Оценка {row['grade']!r} заменена на {value!r}")
        key = (sid, subject)
        prev = grades.get(key)
        if prev and day == prev["date"]:
            log_error(*args, "Повтор даты; попытка выбрана по правилам")
        new_key = (day, line)
        old_key = (prev["date"], prev["line"]) if prev else ()
        if prev and not rules["last_attempt_counts"]:
            old = prev["grade"]
            score = value if isinstance(value, int) else int(value == passed)
            old_score = old if isinstance(old, int) else int(old == passed)
            new_key, old_key = (score, *new_key), (old_score, *old_key)
        if not prev or new_key > old_key:
            grades[key] = {"grade": value, "date": day, "line": line}
    return grades


def load_data(plan_file, students_file, grades_file, rules_file, log_file):
    """загружает четыре файла и отмечает отсутствующие результаты."""
    with Path(log_file).open("w", encoding="utf-8") as log:
        rules = read_rules(rules_file)
        plan = read_plan(plan_file, rules, log)
        students = read_students(students_file, log)
        grades = read_grades(grades_file, students, plan, rules, log)
        for sid in students:
            for subject in plan:
                if (sid, subject) not in grades:
                    log_error(log, Path(grades_file).name, "-", sid, subject,
                              "Нет допустимой записи по дисциплине")
    return students, plan, grades, rules
