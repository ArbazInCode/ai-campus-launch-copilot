"""Assemble a complete launch kit from inputs."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from copywriter import DEFAULT_MODEL, generate_copy
from planner import LaunchInput, budget_plan, build_timeline, kpi_targets, staffing_plan, to_dict

ROLE_REQUIREMENTS = {
    "head_coach": ["Collegiate or professional playing or coaching experience", "Builds season plans and leads assistant coaches", "Communicates clearly with athletes and parents", "CPR/First Aid certified or willing to certify"],
    "coach": ["Club, high school, or college coaching or playing experience", "Runs structured, position-specific practices", "Patient and encouraging with young athletes", "CPR/First Aid certified or willing to certify"],
    "guide": ["Experience teaching, tutoring, or mentoring students", "Motivates students to set and reach goals", "Comfortable with learning software and progress data", "Warm, organized, and reliable"],
    "strength": ["Strength and conditioning certification (CSCS or similar)", "Experience training youth or school athletes", "Focus on injury prevention and safe progressions"],
    "admissions": ["Experience in admissions, sales, or customer service", "Organized follow-up with families", "Comfortable with CRM tools and events"],
    "helpdesk": ["End-user tech support experience", "Troubleshoots laptops, tablets, and accounts", "Clear, patient communication with families", "Some weekend availability"],
}


def build_kit(inp: LaunchInput, api_key: str | None = None, model: str = DEFAULT_MODEL, client=None, today: date | None = None) -> dict:
    copy, source = generate_copy(inp, api_key, model, client)
    timeline, note = build_timeline(inp, today)
    return {
        "id": uuid.uuid4().hex[:10],
        "name": inp.name(),
        "created": datetime.now().isoformat(timespec="seconds"),
        "input": {**{k: v for k, v in vars(inp).items() if k != "opening"}, "opening": inp.opening.isoformat()},
        "copy": copy,
        "source": source,
        "timeline": to_dict(timeline),
        "plan_note": note,
        "staffing": staffing_plan(inp),
        "budget": budget_plan(inp),
        "kpis": kpi_targets(inp),
    }


def job_post(kit: dict, role: dict) -> str:
    i, c = kit["input"], kit["copy"]
    reqs = ROLE_REQUIREMENTS.get(role["key"], [])
    return (f"{role['title']} – {kit['name']}\n{role['team']} · {i['city']}, TX · {role['openings']} opening{'s' if role['openings'] > 1 else ''}\n\n"
            f"About the role\n{c['job_blurbs'].get(role['key'], '')}\n\nWhat we're looking for\n" + "\n".join(f"• {r}" for r in reqs) +
            f"\n\nAbout the campus\n{c['positioning']['tagline']} Opening {date.fromisoformat(i['opening']).strftime('%B %Y')}.\n\nHow to apply\nSend your resume and a short note about why you'd be a great fit.")


def input_from_kit(kit: dict) -> LaunchInput:
    i = dict(kit["input"])
    i["opening"] = date.fromisoformat(i["opening"])
    return LaunchInput(**i)
