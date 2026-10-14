"""таблицы, текстовая сводка и диаграмма."""

import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

cyber = True

if cyber:
    plt.style.use("dark_background")
    plt.rcParams.update({
        "axes.facecolor": "#212946", "figure.facecolor": "#212946",
    })


def write_csv(path, fields, rows):
    """сохраняет CSV с BOM и разделителем ';'."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(fields)
        writer.writerows(rows)


def save_tables(results, out):
    """записывает рейтинг и список задолжников."""
    rating, debtors = [], []
    for place, r in enumerate(results, 1):
        avg = "" if r["average"] is None else f"{r['average']:.2f}"
        rating.append([
            place, r["student_id"], r["fio"], r["group"], avg,
            len(r["debts"]), r["stipend"], r["amount"],
        ])
        if r["debts"]:
            debtors.append([
                r["student_id"], r["fio"], len(r["debts"]),
                " | ".join(r["debts"]),
            ])
    write_csv(out / "rating.csv", [
        "place", "student_id", "fio", "group", "average", "debt_count",
        "stipend", "amount",
    ], rating)
    write_csv(out / "debtors.csv", [
        "student_id", "fio", "debt_count", "debts",
    ], debtors)


def summary_text(results, subjects):
    """составляет сводку по выплатам, предметам и необходимым пересдачам."""
    lines = [f"Студентов: {len(results)}"]
    for kind in ("академическая", "повышенная", "нет"):
        count = sum(r["stipend"] == kind for r in results)
        lines.append(f"Стипендия, {kind}: {count}")
    fund = sum(r["amount"] for r in results)
    debts = sum(bool(r["debts"]) for r in results)
    lines.append(f"Общий стипендиальный фонд: {fund:g} руб.")
    lines.append(f"Студентов с задолженностями: {debts}")
    lines.append("\nИтоги по дисциплинам")
    for r in subjects:
        if r["type"] == "экзамен":
            avg, share = "нет оценок", "нет оценок"
            if r["average"] is not None:
                avg, share = f"{r['average']:.2f}", f"{r['failed_share']:.1%}"
            lines.append(
                f"{r['discipline']}: средний балл {avg}; "
                f"доля двоек среди числовых оценок {share}; "
                f"задолженностей {r['debts']}"
            )
        else:
            lines.append(
                f"{r['discipline']}: задолженностей {r['debts']} "
                f"({r['debt_share']:.1%} студентов); "
                "средний балл не применяется"
            )
    lines.append("\nУсловия стипендии")
    lines.extend(f"{r['fio']}: {r['advice']}" for r in results)
    return "\n".join(lines)


def save_chart(subjects, path):
    """сохраняет средние баллы по экзаменам в столбчатой диаграмме."""
    rows = [r for r in subjects
            if r["type"] == "экзамен" and r["average"] is not None]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    if rows:
        bars = ax.bar(
            [r["discipline"].replace(" ", "\n") for r in rows],
            [r["average"] for r in rows],
            color="#08f7fe" if cyber else None, width=0.6,
        )
        ax.bar_label(bars, fmt="%.2f", padding=4)
        ax.set_ylim(0, max(r["average"] for r in rows) * 1.18)
        ax.tick_params(axis="x", labelsize=9)
    else:
        ax.text(0.5, 0.5, "Нет числовых экзаменационных оценок",
                ha="center", va="center")
    ax.set_ylabel("Средний балл")
    ax.set_title("Результаты экзаменов")
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=180, metadata={"Software": "Matplotlib"})
    plt.close(fig)
