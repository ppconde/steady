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


def _span(d: int) -> str:
    return "week" if d == 7 else f"{d // 7} weeks" if d % 7 == 0 else f"{d} days"


def _weight(w) -> str | None:
    if w.latest is None:
        return None  # never weighs in: say nothing
    if w.avg is None:
        return "Not enough weigh-ins lately to judge weight."
    s = f"Weight averaged {_num(w.avg)} kg over the last {w.recent_days} days"
    if w.target is None:
        return s + ". Set a weight goal in Garmin Connect to count it as progress."
    goal = f"your {_num(w.target)} kg target"
    if w.status == "on_track":
        return f"{s}, on track for {goal}."
    if w.status in ("closer", "further"):
        moved = _num(round(abs(w.before - w.avg), 1))
        return f"{s}, {moved} kg {w.status} {'to' if w.status == 'closer' else 'from'} {goal} than the {_span(w.before_days)} before."
    if w.status == "steady":
        return f"{s}, {_num(round(abs(w.avg - w.target), 1))} kg from {goal} and holding."
    return "Not enough weigh-ins lately to judge weight."


def hm(s: float) -> str:
    m = round(s / 60)
    return f"{m // 60}h {m % 60:02d}m"


def _sleep(s) -> str | None:
    if s.avg_s is None:
        return None
    line = f"Sleep averaged {hm(s.avg_s)} over the last {s.recent_days} nights"
    if s.before_s is not None:
        d = round((s.avg_s - s.before_s) / 60)
        line += (f", about the same as the {_span(s.before_days)} before" if abs(d) < 10
                 else f", {abs(d)} min {'more' if d > 0 else 'less'} than the {_span(s.before_days)} before")
    if s.avg_score is not None:
        line += f"; sleep score {round(s.avg_score)}"
    return line + "."


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
        out.append(f"{st.up} of {st.total} exercises up vs the previous {_span(r.compare_days)} ({top}).")

    if line := _weight(r.weight):
        out.append(line)

    if line := _sleep(r.sleep):
        out.append(line)

    g = _GAUGE[r.gauge]
    if r.gauge in ("normal", "strained") and r.off_signals:
        g += f" Outside your usual range: {', '.join(r.off_signals)}."
    out.append(g)
    if r.gauge != "building_baseline" and r.missing_nights:
        out.append("No sleep or HRV data for the last 3 nights, so recovery can't be judged." if r.missing_nights == 3
                   else f"No sleep or HRV data for {r.missing_nights} of the last 3 nights.")

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
