"""Plain-sentence findings from a Report; the template review is just these joined."""
from .analysis.report import Report

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_GAUGE = {"fresh": "You look fresh: recovery is in your normal range and load is at or below usual.",
          "normal": "Training stress looks normal for you.",
          "strained": "Recovery looks strained.",
          "building_baseline": "Building your baseline: a couple more weeks of sleep data are needed to judge recovery."}


def pace(s: float) -> str:
    s = round(s)
    return f"{s // 60}:{s % 60:02d}/km"


def _num(x: float) -> str:
    return f"{x:g}"


def hard_pairs(r: Report) -> list[tuple[int, int]]:
    hard = [c.effort == "hard" for c in r.week]
    return [(d, d + 1) for d in range(6) if hard[d] and hard[d + 1]]


def findings(r: Report) -> list[str]:
    out = []
    run = r.running
    if run.current is None:
        out.append("No comparable runs this period.")
    elif run.change is None:
        out.append(f"Pace at 140 bpm is {pace(run.current)}; not enough runs yet to show a trend.")
    else:
        word = "faster" if run.change < 0 else "slower"
        out.append(f"Pace at 140 bpm is {pace(run.current)}, {abs(round(run.change))} s/km {word} "
                   f"than at the start of the period.")

    st = r.strength
    if st.total == 0:
        out.append("Not enough exercise data yet.")
    else:
        top = ", ".join(f"{c.exercise.split('/')[-1].replace('_', ' ').lower()} "
                        f"{_num(c.before)} → {_num(c.after)} {c.unit}" for c in st.changes[:3])
        d = r.compare_days
        span = "week" if d == 7 else f"{d // 7} weeks" if d % 7 == 0 else f"{d} days"
        out.append(f"{st.up} of {st.total} exercises up vs the previous {span} ({top}).")

    g = _GAUGE[r.gauge]
    if r.gauge in ("normal", "strained") and r.off_signals:
        g += f" Outside your usual range: {', '.join(r.off_signals)}."
    out.append(g)

    for a, b in hard_pairs(r):
        pair = f"{DAYS[a]} → {DAYS[b]}"
        if (a, b) in r.usual_pairs:
            how = "and recovery handled it" if r.gauge != "strained" else "and recovery is lagging this time"
            out.append(f"{pair} is your usual hard stretch, {how}.")
        else:
            out.append(f"{pair} were both hard days this week.")
    return out


def template_text(fs: list[str]) -> str:
    return " ".join(fs)
