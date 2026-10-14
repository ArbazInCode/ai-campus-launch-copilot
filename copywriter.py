"""Launch-kit copy: Google Gemini when a key is available, polished templates otherwise.

Every AI response is validated and merged over the template, so the kit is always
complete even if the model skips a field or returns malformed JSON.
"""
from __future__ import annotations

import json
import re
from planner import LaunchInput, staffing_plan

DEFAULT_MODEL = "gemini-2.5-flash"


def _grades(inp: LaunchInput) -> str:
    return f"grades {inp.grade_min}–{inp.grade_max}"


def template_copy(inp: LaunchInput) -> dict:
    s, c = inp.sport, inp.city
    sl = s.lower()
    hl = inp.highlights.strip()
    roles = staffing_plan(inp)
    return {
        "positioning": {
            "headline": f"Two hours of class. All afternoon of {sl}.",
            "tagline": f"A new {sl}-focused campus for student-athletes in {c}.",
            "selling_points": [
                "Core academics finished in about two focused hours each morning",
                f"Daily {sl} training built into the school day, not squeezed in after it",
                hl or "Coaches with collegiate and professional playing experience",
            ],
        },
        "website": {
            "hero_headline": f"{c}'s new home for {sl} and academics",
            "hero_sub": (f"Mastery-based learning every morning and serious {sl} training every afternoon "
                         f"for student-athletes in {_grades(inp)}."),
            "pillars": [
                {"title": "Academics", "body": "Personalized, mastery-based lessons so students move forward as soon as they're ready."},
                {"title": s, "body": f"Small-group, position-specific {sl} training every afternoon."},
                {"title": "Strength", "body": "Age-appropriate strength, speed, and injury prevention work."},
                {"title": "Next level", "body": "Film review, showcases, and guidance through the recruiting process."},
            ],
            "faq": [
                {"q": "How can academics fit into two hours?", "a": "Lessons adapt to each student, who moves on after mastering a topic, removing the downtime of a typical school day."},
                {"q": "Who is the campus for?", "a": f"Student-athletes in {_grades(inp)} who want strong academics and daily {sl} training."},
                {"q": "Is club experience required?", "a": "No. Training groups are organized by skill level, and coaches build a plan for each athlete."},
                {"q": "What does tuition cost?", "a": "Contact admissions for tuition, financial aid, and Texas education savings account eligibility."},
                {"q": "How do we get started?", "a": "Register for an open house or tryout, then apply with our admissions team."},
            ],
        },
        "ads": [
            {"name": "The schedule", "primary_text": f"What if school ended by lunch and the rest of the day was {sl}? A new campus is coming to {c}.", "headline": f"Two hours of class. All afternoon of {sl}.", "cta": "Learn more"},
            {"name": "The parent's worry", "primary_text": f"Your athlete shouldn't have to choose between grades and the game. Come see how our {c} campus works.", "headline": "Free Open House: reserve your spot", "cta": "Sign up"},
            {"name": "The goal", "primary_text": f"Serious about playing {sl} at the next level? Train every afternoon with experienced coaches, built into the school day.", "headline": f"Tryouts open in {c}", "cta": "Sign up"},
        ],
        "audience": {
            "summary": f"Parents of {sl} players in {_grades(inp)} within 25 miles of {c}.",
            "age_range": "30–55",
            "interests": [f"{s} (sport)", f"Club {sl}", "Private school", "Homeschooling", "Youth sports"],
        },
        "job_blurbs": {r["key"]: f"Join our new {c} campus as a {r['title']} and help student-athletes grow on and off the court." for r in roles},
        "launch_announcement": (f"We're excited to announce a new Texas Sports Academy {sl} campus in {c}. "
                                f"Students will finish core academics in the morning and train {sl} every afternoon. "
                                f"Join us at an upcoming open house to learn more."),
    }


SCHEMA_HINT = {
    "positioning": {"headline": "str", "tagline": "str", "selling_points": ["str", "str", "str"]},
    "website": {"hero_headline": "str", "hero_sub": "str",
                "pillars": [{"title": "str", "body": "str"}] * 4,
                "faq": [{"q": "str", "a": "str"}] * 5},
    "ads": [{"name": "str", "primary_text": "str", "headline": "str", "cta": "Learn more|Sign up"}] * 3,
    "audience": {"summary": "str", "age_range": "str", "interests": ["str"]},
    "job_blurbs": {"<role key>": "one paragraph"},
    "launch_announcement": "str",
}


def build_prompt(inp: LaunchInput) -> str:
    roles = ", ".join(f"{r['key']} ({r['title']})" for r in staffing_plan(inp))
    return f"""You write launch copy for Texas Sports Academy, a K-12 private school network for student-athletes.
Students finish core academics in about two hours each morning with mastery-based learning, then train their sport in the afternoon.

New campus: {inp.name()}
City: {inp.city}, Texas
Sport: {inp.sport}
Grades: {inp.grade_min} to {inp.grade_max}
Opening: {inp.opening.strftime('%B %Y')}
What makes it special: {inp.highlights or 'not specified'}
Roles to hire (use these exact keys in job_blurbs): {roles}

Rules: warm, confident, specific to {inp.sport} and {inp.city}. Do not invent prices, scholarships, coach names, rankings, or statistics.
Ad primary_text under 125 characters, ad headlines under 40 characters. FAQ answer about tuition must say to contact admissions.
Return ONLY JSON matching this shape exactly:
{json.dumps(SCHEMA_HINT)}"""


def _extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _s(v, limit=600) -> str | None:
    return v.strip()[:limit] if isinstance(v, str) and v.strip() else None


def merge_ai(base: dict, ai: dict) -> dict:
    """Overlay valid AI fields on the template; ignore anything malformed."""
    out = json.loads(json.dumps(base))
    if not isinstance(ai, dict):
        return out
    p = ai.get("positioning") or {}
    if isinstance(p, dict):
        for k in ("headline", "tagline"):
            if _s(p.get(k), 140):
                out["positioning"][k] = _s(p.get(k), 140)
        sp = [x for x in (p.get("selling_points") or []) if _s(x, 200)]
        if len(sp) >= 3:
            out["positioning"]["selling_points"] = [_s(x, 200) for x in sp[:3]]
    w = ai.get("website") or {}
    if isinstance(w, dict):
        for k in ("hero_headline", "hero_sub"):
            if _s(w.get(k), 300):
                out["website"][k] = _s(w.get(k), 300)
        pil = [x for x in (w.get("pillars") or []) if isinstance(x, dict) and _s(x.get("title"), 40) and _s(x.get("body"), 300)]
        if len(pil) >= 3:
            out["website"]["pillars"] = [{"title": _s(x["title"], 40), "body": _s(x["body"], 300)} for x in pil[:4]]
        faq = [x for x in (w.get("faq") or []) if isinstance(x, dict) and _s(x.get("q"), 160) and _s(x.get("a"), 500)]
        if len(faq) >= 3:
            out["website"]["faq"] = [{"q": _s(x["q"], 160), "a": _s(x["a"], 500)} for x in faq[:6]]
    ads = [x for x in (ai.get("ads") or []) if isinstance(x, dict) and _s(x.get("primary_text")) and _s(x.get("headline"))]
    if len(ads) >= 2:
        out["ads"] = [{"name": _s(x.get("name"), 40) or f"Version {i+1}", "primary_text": _s(x["primary_text"], 220),
                       "headline": _s(x["headline"], 60), "cta": x.get("cta") if x.get("cta") in ("Learn more", "Sign up") else "Learn more"}
                      for i, x in enumerate(ads[:3])]
    a = ai.get("audience") or {}
    if isinstance(a, dict):
        if _s(a.get("summary"), 200):
            out["audience"]["summary"] = _s(a.get("summary"), 200)
        if _s(a.get("age_range"), 20):
            out["audience"]["age_range"] = _s(a.get("age_range"), 20)
        ints = [_s(x, 40) for x in (a.get("interests") or []) if _s(x, 40)]
        if ints:
            out["audience"]["interests"] = ints[:8]
    jb = ai.get("job_blurbs") or {}
    if isinstance(jb, dict):
        for k in out["job_blurbs"]:
            if _s(jb.get(k), 700):
                out["job_blurbs"][k] = _s(jb.get(k), 700)
    if _s(ai.get("launch_announcement"), 800):
        out["launch_announcement"] = _s(ai.get("launch_announcement"), 800)
    return out


def generate_copy(inp: LaunchInput, api_key: str | None, model: str = DEFAULT_MODEL, client=None) -> tuple[dict, str]:
    """Returns (copy, source) where source explains what produced it."""
    base = template_copy(inp)
    if not api_key and client is None:
        return base, "Built-in templates (add a Gemini API key for AI-written copy)"
    try:
        if client is None:
            from google import genai
            client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model, contents=build_prompt(inp),
            config={"response_mime_type": "application/json", "temperature": 0.8})
        data = _extract_json(getattr(resp, "text", "") or "")
        return merge_ai(base, data), f"Google Gemini ({model})"
    except Exception as e:  # network, quota, bad key, malformed JSON
        msg = str(e)
        reason = ("the free-tier limit was reached" if "429" in msg or "RESOURCE_EXHAUSTED" in msg
                  else "the API key was rejected" if "API key" in msg or "401" in msg or "403" in msg or "PERMISSION" in msg
                  else "the model name wasn't found" if "404" in msg or "NOT_FOUND" in msg
                  else "the AI response couldn't be read")
        return base, f"Built-in templates ({reason}; try again later)"
