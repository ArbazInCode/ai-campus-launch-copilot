"""Deterministic launch planning: timelines, staffing, budgets.

AI writes the words; this module does the math, so numbers are always
consistent and testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

GRADES = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
SPORTS = ["Volleyball", "Basketball", "Baseball", "Softball", "Soccer", "Football",
          "Gymnastics", "Swimming", "Track and Field", "Tennis", "Cheer", "Golf"]

IDEAL_RUNWAY_DAYS = 150  # a comfortable launch window

# (task, owner, days before opening at the ideal runway, category)
BASE_TASKS = [
    ("Secure facility lease and city permits", "Campus Director", 150, "Facility"),
    ("Finalize program schedule and tuition", "Campus Director", 140, "Program"),
    ("Publish campus landing page", "AI Operations", 125, "Marketing"),
    ("Post job openings on all channels", "AI Operations", 120, "Hiring"),
    ("Launch Facebook and Instagram campaign", "AI Operations", 115, "Marketing"),
    ("Hiring Day: interview coaches and guides", "Hiring Lead", 100, "Hiring"),
    ("Open House #1", "Admissions", 90, "Events"),
    ("Tryouts", "Head Coach", 75, "Events"),
    ("Parent info session (online school and TEFA)", "Admissions", 65, "Events"),
    ("Send offers to selected staff", "Hiring Lead", 60, "Hiring"),
    ("Open House #2", "Admissions", 45, "Events"),
    ("Enrollment deadline", "Admissions", 30, "Enrollment"),
    ("Staff onboarding and training", "Campus Director", 21, "Hiring"),
    ("Install equipment and set up learning spaces", "Operations", 14, "Facility"),
    ("Family orientation night", "Admissions", 7, "Events"),
    ("First day of school", "Everyone", 0, "Launch"),
]
EVENT_TASKS = {"Open House #1", "Tryouts", "Parent info session (online school and TEFA)",
               "Open House #2", "Family orientation night", "Hiring Day: interview coaches and guides"}


@dataclass
class LaunchInput:
    city: str
    sport: str
    grade_min: str
    grade_max: str
    opening: date
    target_students: int
    ad_budget: int = 1500
    highlights: str = ""
    campus_name: str = ""

    def name(self) -> str:
        return self.campus_name.strip() or f"Texas Sports Academy {self.sport} · {self.city}"

    def validate(self, today: date | None = None) -> list[str]:
        today = today or date.today()
        errs = []
        if len(self.city.strip()) < 2:
            errs.append("Add the city for the new campus.")
        if not self.sport.strip():
            errs.append("Choose a sport.")
        if self.grade_min not in GRADES or self.grade_max not in GRADES:
            errs.append("Choose a valid grade range.")
        elif GRADES.index(self.grade_min) > GRADES.index(self.grade_max):
            errs.append("The grade range must go from low to high.")
        if self.opening <= today + timedelta(days=13):
            errs.append("The opening date must be at least two weeks away.")
        if not (5 <= int(self.target_students) <= 500):
            errs.append("Target enrollment should be between 5 and 500 students.")
        if not (0 <= int(self.ad_budget) <= 100000):
            errs.append("Ad budget should be between $0 and $100,000.")
        return errs


@dataclass
class Task:
    task: str
    owner: str
    due: date
    category: str
    done: bool = False


def build_timeline(inp: LaunchInput, today: date | None = None) -> tuple[list[Task], str | None]:
    """Work backward from the opening date. Compress the plan if the runway is short,
    and never schedule anything before today."""
    today = today or date.today()
    runway = (inp.opening - today).days
    scale = 1.0
    note = None
    if runway < IDEAL_RUNWAY_DAYS:
        scale = max(runway - 1, 1) / IDEAL_RUNWAY_DAYS
        note = (f"Only {runway} days until opening (a {IDEAL_RUNWAY_DAYS}-day runway is ideal), "
                f"so the plan is compressed. Prioritize hiring and enrollment events.")
    tasks: list[Task] = []
    for name, owner, offset, cat in BASE_TASKS:
        due = inp.opening - timedelta(days=round(offset * scale))
        if due < today:
            due = today
        tasks.append(Task(name, owner, due, cat))
    # keep order strictly chronological and unique-ish dates for events
    tasks.sort(key=lambda t: (t.due, -[b[2] for b in BASE_TASKS if b[0] == t.task][0]))
    for i in range(1, len(tasks)):
        if tasks[i].due < tasks[i - 1].due:
            tasks[i].due = tasks[i - 1].due
    # events should land on Saturdays when there is room (families attend weekends)
    for t in tasks:
        if t.task in EVENT_TASKS and t.task != "Parent info session (online school and TEFA)":
            sat = t.due - timedelta(days=(t.due.weekday() - 5) % 7)
            if sat >= today and sat < inp.opening:
                t.due = sat
    tasks.sort(key=lambda t: t.due)
    return tasks, note


ROLE_RULES = [
    # key, title, team, students per person, minimum
    ("head_coach", "Head Coach", "Athletics", 10_000, 1),
    ("coach", "Assistant Coach", "Athletics", 12, 1),
    ("guide", "Academic Guide", "Academics", 15, 1),
    ("strength", "Strength and Conditioning Coach", "Athletics", 60, 1),
    ("admissions", "Admissions Coordinator", "Operations", 120, 1),
    ("helpdesk", "IT Help Desk Technician", "Operations", 150, 1),
]


def staffing_plan(inp: LaunchInput) -> list[dict]:
    n = int(inp.target_students)
    plan = []
    for key, title, team, ratio, minimum in ROLE_RULES:
        count = max(minimum, math.ceil(n / ratio)) if ratio < 10_000 else 1
        if key == "coach":
            count = max(1, math.ceil(n / ratio) - 1)  # head coach covers one group
        t = f"{inp.sport} {title}" if key in ("head_coach", "coach") else title
        plan.append({"key": key, "title": t, "team": team, "openings": count})
    return plan


def budget_plan(inp: LaunchInput) -> list[dict]:
    """Split the ad budget across launch phases. Always sums to the total."""
    total = int(inp.ad_budget)
    split = [("Awareness: campus announcement", 0.35), ("Open House registrations", 0.30),
             ("Tryout registrations", 0.20), ("Retargeting site visitors", 0.15)]
    rows, used = [], 0
    for i, (name, pct) in enumerate(split):
        amt = total - used if i == len(split) - 1 else round(total * pct)
        used += amt
        rows.append({"phase": name, "budget": amt})
    return rows


def kpi_targets(inp: LaunchInput) -> dict:
    n = int(inp.target_students)
    return {
        "enrolled": n,
        "applications": math.ceil(n * 1.6),
        "open_house_families": math.ceil(n * 2.5),
        "leads": math.ceil(n * 6),
        "target_cost_per_lead": round(int(inp.ad_budget) / max(1, math.ceil(n * 6)), 2),
    }


def to_dict(obj):
    if isinstance(obj, list):
        return [to_dict(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        d = asdict(obj)
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items()}
    return obj
