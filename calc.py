"""итоги сессии, рейтинг и условия стипендии."""


def is_debt(mark, rules):
    """проверяет, остается ли по дисциплине задолженность."""
    return mark in (
        None, rules["grade_aliases"]["неуд"],
        rules["credit_aliases"]["незачет"], rules["absent_mark"],
    )


def student_total(student, plan, grades, rules):
    """считает средний балл, долги и выплату одного студента."""
    marks = {
        name: grades.get((student["student_id"], name), {}).get("grade")
        for name in plan
    }
    scores = [m for name, m in marks.items()
              if plan[name] == "экзамен" and isinstance(m, int)]
    debts = [name for name, m in marks.items() if is_debt(m, rules)]
    level, amount = "нет", 0
    funded = (
        student["funding"].casefold() == rules["eligible_funding"].casefold()
    )
    if funded and not debts and scores:
        for key, label in (("increased", "повышенная"),
                           ("academic", "академическая")):
            if min(scores) >= rules["stipend"][key]["min_grade"]:
                level, amount = label, rules["stipend"][key]["amount"]
                break
    return {
        **student, "marks": marks, "debts": debts,
        "average": sum(scores) / len(scores) if scores else None,
        "stipend": level, "amount": amount,
    }


def stipend_advice(result, plan, rules):
    """перечисляет необходимые действия для следующего уровня выплаты."""
    if result["funding"].casefold() != rules["eligible_funding"].casefold():
        return "Не претендует"
    if result["stipend"] == "повышенная":
        return "Повышенная стипендия уже назначена"
    key = "academic" if result["stipend"] == "нет" else "increased"
    label = "академической" if key == "academic" else "повышенной"
    target = rules["stipend"][key]["min_grade"]
    actions = []
    for name, kind in plan.items():
        mark = result["marks"][name]
        if kind == "экзамен" and (not isinstance(mark, int) or mark < target):
            missing = mark in (None, rules["absent_mark"])
            verb = "сдать" if missing else "пересдать"
            actions.append(f"{name} - {verb} на {target}")
        elif kind != "экзамен" and name in result["debts"]:
            actions.append(f"{name} - получить зачет")
    if not actions:
        return "В плане нет экзаменов: расчет стипендии невозможен"
    return f"Для {label} стипендии: " + "; ".join(actions)


def make_rating(students, plan, grades, rules):
    """сортирует студентов по баллу, числу долгов и ФИО."""
    rows = [student_total(s, plan, grades, rules) for s in students.values()]
    rows.sort(key=lambda r: (
        r["average"] is None,
        -r["average"] if r["average"] is not None else 0,
        len(r["debts"]), r["fio"].casefold(), r["student_id"],
    ))
    for row in rows:
        row["advice"] = stipend_advice(row, plan, rules)
    return rows


def subject_totals(students, plan, grades, rules):
    """считает средние и доли неудовлетворительных результатов по предметам."""
    rows = []
    for name, kind in plan.items():
        marks = [grades.get((sid, name), {}).get("grade") for sid in students]
        scores = [m for m in marks if isinstance(m, int)]
        bad = scores.count(rules["grade_aliases"]["неуд"])
        debts = sum(is_debt(m, rules) for m in marks)
        rows.append({
            "discipline": name, "type": kind, "graded": len(scores),
            "average": sum(scores) / len(scores) if scores else None,
            "failed_grades": bad,
            "failed_share": bad / len(scores) if scores else None,
            "debts": debts, "debt_share": debts / len(marks) if marks else 0,
        })
    return rows
