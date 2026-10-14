"""AI Campus Launch Copilot – Streamlit app.

Enter a city and a sport; get a complete, editable launch kit for a new campus:
positioning, website copy, ads, banners, events, hiring plan, and a dated checklist.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from assets import SIZES, banners_for, bundle_zip, checklist_xlsx, kit_markdown, landing_page, nice_date
from copywriter import DEFAULT_MODEL, generate_copy
from kit import build_kit, input_from_kit, job_post
from planner import GRADES, SPORTS, LaunchInput

st.set_page_config(page_title="AI Campus Launch Copilot", page_icon="🚀", layout="wide")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stMarkdown, .stTextInput, button, input, textarea, select {font-family:"Plus Jakarta Sans", system-ui, sans-serif;}
h1, h2, h3, .serif {font-family:"Fraunces", Georgia, serif !important; letter-spacing:-.01em;}
.block-container {padding-top:2rem; max-width:1240px;}
.hero {background:linear-gradient(135deg,#FFFFFF 0%,#FBF3E2 100%); border:1px solid #ECE8DF; border-radius:22px; padding:30px 34px; margin-bottom:22px; box-shadow:0 2px 6px rgba(20,33,61,.05),0 18px 44px rgba(20,33,61,.08); position:relative; overflow:hidden;}
.hero:after {content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px; border:2px solid rgba(201,151,58,.22); border-radius:50%;}
.hero .eb {font-size:.74rem; letter-spacing:.18em; text-transform:uppercase; color:#7A5A16; font-weight:800;}
.hero h1 {margin:.3rem 0 .4rem; font-size:2.4rem; color:#14213D;}
.hero p {color:#667085; margin:0; max-width:46rem; font-size:1.02rem;}
.card {background:#fff; border:1px solid #ECE8DF; border-radius:16px; padding:18px 20px; box-shadow:0 1px 2px rgba(20,33,61,.04),0 6px 20px rgba(20,33,61,.06); margin-bottom:12px;}
.card h4 {margin:0 0 6px; font-family:"Fraunces", Georgia, serif;}
.muted {color:#667085;}
.pill {display:inline-block; font-size:.74rem; font-weight:700; border-radius:999px; padding:3px 10px; background:#FBF3E2; color:#7A5A16; margin-right:6px;}
.pill.ok {background:#E7F6EE; color:#18794E;}
div[data-testid="stMetric"] {background:#fff; border:1px solid #ECE8DF; border-radius:16px; padding:14px 16px; box-shadow:0 6px 20px rgba(20,33,61,.05); border-left:4px solid #C9973A;}
.stTabs [data-baseweb="tab-list"] {gap:6px;}
.stTabs [data-baseweb="tab"] {border-radius:999px; padding:6px 16px; background:#fff; border:1px solid #ECE8DF;}
.stTabs [aria-selected="true"] {background:#13294B !important; color:#fff !important;}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {border-radius:12px; font-weight:700;}
section[data-testid="stSidebar"] {background:#FFFFFF; border-right:1px solid #ECE8DF;}
</style>""", unsafe_allow_html=True)

# ---------- State ----------
ss = st.session_state
ss.setdefault("kits", {})
ss.setdefault("current", None)


def get_secret_key() -> str:
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 🚀 Launch Copilot")
    st.caption("Concept tool by Arbaz Abdul for Texas Sports Academy. Sample planning only.")
    st.divider()
    st.markdown("**AI settings**")
    secret_key = get_secret_key()
    if secret_key:
        st.success("Gemini key loaded from app secrets.", icon="🔐")
        api_key = secret_key
    else:
        api_key = st.text_input("Google Gemini API key", type="password", help="Free key from Google AI Studio. Leave empty to use built-in templates.")
    model = st.text_input("Model", value=DEFAULT_MODEL, help="Change this if Google releases a newer model.")
    st.caption("No key? The copilot still works with polished built-in templates.")
    st.divider()
    st.markdown("**Your launches**")
    if ss.kits:
        names = {k: v["name"] for k, v in ss.kits.items()}
        choice = st.radio("Open a launch", options=["__new__"] + list(names), format_func=lambda k: "➕ New launch" if k == "__new__" else names[k],
                          index=0 if ss.current is None else (["__new__"] + list(names)).index(ss.current) if ss.current in names else 0, label_visibility="collapsed")
        ss.current = None if choice == "__new__" else choice
    else:
        st.caption("No launches yet.")
    up = st.file_uploader("Restore a saved launch (kit.json)", type=["json"])
    if up is not None:
        try:
            k = json.loads(up.getvalue().decode("utf-8"))
            assert {"id", "name", "input", "copy", "timeline", "staffing", "budget", "kpis"} <= set(k)
            if k["id"] not in ss.kits:
                ss.kits[k["id"]] = k
                ss.current = k["id"]
                st.rerun()
        except Exception:
            st.error("That file isn't a valid launch kit.")

# ---------- Header ----------
st.markdown("""<div class="hero"><span class="eb">AI Campus Launch Copilot</span>
<h1>Launch a new campus in one click.</h1>
<p>Enter a city and a sport. Get positioning, website copy, Facebook ads, banners, an event plan, a hiring plan, and a dated launch checklist, ready to review and export.</p></div>""",
            unsafe_allow_html=True)


# ---------- New launch form ----------
def new_launch_form():
    with st.form("new"):
        st.markdown("#### New campus")
        c1, c2, c3 = st.columns(3)
        city = c1.text_input("City", placeholder="e.g. Round Rock")
        sport = c2.selectbox("Sport", SPORTS)
        name = c3.text_input("Campus name (optional)", placeholder="Auto-generated if empty")
        c4, c5, c6 = st.columns(3)
        gmin = c4.selectbox("Grades from", GRADES, index=GRADES.index("6"))
        gmax = c5.selectbox("Grades to", GRADES, index=GRADES.index("12"))
        opening = c6.date_input("Opening date", value=date.today() + timedelta(days=210), min_value=date.today() + timedelta(days=14))
        c7, c8 = st.columns(2)
        target = c7.number_input("Target enrollment (students)", min_value=5, max_value=500, value=40, step=5)
        budget = c8.number_input("Launch ad budget (USD)", min_value=0, max_value=100000, value=2000, step=250)
        highlights = st.text_area("What makes this campus special? (optional)", placeholder="e.g. Partnered with a top local club; new indoor facility with two courts")
        go = st.form_submit_button("✨ Generate launch kit", type="primary", width="stretch")
    if go:
        inp = LaunchInput(city=city.strip(), sport=sport, grade_min=gmin, grade_max=gmax, opening=opening,
                          target_students=int(target), ad_budget=int(budget), highlights=highlights.strip(), campus_name=name.strip())
        errs = inp.validate()
        if errs:
            for e in errs:
                st.error(e)
            return
        with st.spinner("Building your launch kit…"):
            kit = build_kit(inp, api_key or None, model.strip() or DEFAULT_MODEL)
        ss.kits[kit["id"]] = kit
        ss.current = kit["id"]
        st.rerun()


def kit_view(kit: dict):
    i, c = kit["input"], kit["copy"]
    top = st.columns([3, 1])
    top[0].markdown(f"## {kit['name']}")
    top[0].markdown(f"<span class='pill'>{i['sport']}</span><span class='pill'>Grades {i['grade_min']}–{i['grade_max']}</span>"
                    f"<span class='pill'>Opens {date.fromisoformat(i['opening']).strftime('%B %d, %Y')}</span>"
                    f"<span class='pill ok'>{kit['source']}</span>", unsafe_allow_html=True)
    with top[1]:
        if st.button("✨ Rewrite copy with AI", width="stretch", disabled=not api_key, help=None if api_key else "Add a Gemini key in the sidebar"):
            with st.spinner("Rewriting with Gemini…"):
                copy, src = generate_copy(input_from_kit(kit), api_key, model.strip() or DEFAULT_MODEL)
            kit["copy"], kit["source"] = copy, src
            (st.success if "Gemini" in src else st.warning)(src)
            st.rerun()
        if st.button("🗑 Delete launch", width="stretch"):
            del ss.kits[kit["id"]]
            ss.current = None
            st.rerun()
    if kit.get("plan_note"):
        st.warning(kit["plan_note"])

    tabs = st.tabs(["Overview", "Website", "Ads & budget", "Banners", "Events & checklist", "Hiring", "Export"])

    with tabs[0]:
        k = kit["kpis"]
        m = st.columns(5)
        m[0].metric("Enrollment goal", k["enrolled"])
        m[1].metric("Applications needed", k["applications"])
        m[2].metric("Open house families", k["open_house_families"])
        m[3].metric("Leads needed", k["leads"])
        m[4].metric("Target cost per lead", f"${k['target_cost_per_lead']:.2f}")
        st.markdown(f"<div class='card'><h4>{c['positioning']['headline']}</h4><p class='muted'>{c['positioning']['tagline']}</p>"
                    + "".join(f"<p>✓ {p}</p>" for p in c["positioning"]["selling_points"]) + "</div>", unsafe_allow_html=True)
        st.markdown("**Launch announcement**")
        st.code(c["launch_announcement"], language=None, wrap_lines=True)
        done = sum(1 for t in kit["timeline"] if t.get("done"))
        st.progress(done / len(kit["timeline"]), text=f"Launch checklist: {done} of {len(kit['timeline'])} tasks done")

    with tabs[1]:
        w = c["website"]
        st.markdown(f"<div class='card'><h4>{w['hero_headline']}</h4><p class='muted'>{w['hero_sub']}</p></div>", unsafe_allow_html=True)
        cols = st.columns(len(w["pillars"]))
        for col, p in zip(cols, w["pillars"]):
            col.markdown(f"<div class='card'><h4>{p['title']}</h4><p class='muted'>{p['body']}</p></div>", unsafe_allow_html=True)
        for q in w["faq"]:
            with st.expander(q["q"]):
                st.write(q["a"])
        page = landing_page(kit)
        st.download_button("⬇ Download ready-to-host landing page (index.html)", page, file_name="index.html", mime="text/html", width="stretch")
        with st.expander("Preview the landing page"):
            if hasattr(st, "iframe"):
                st.iframe(page, height=700)  # all content is HTML-escaped in landing_page()
            else:
                components.html(page, height=700, scrolling=True)

    with tabs[2]:
        a = c["audience"]
        st.markdown(f"<div class='card'><h4>Audience</h4><p>{a['summary']}</p><p class='muted'>Ages {a['age_range']} · Interests: {', '.join(a['interests'])}</p></div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for col, ad in zip(cols, c["ads"]):
            with col:
                st.markdown(f"<div class='card'><span class='pill'>{ad['name']}</span><h4 style='margin-top:8px'>{ad['headline']}</h4><p>{ad['primary_text']}</p><p class='muted'>Button: {ad['cta']}</p></div>", unsafe_allow_html=True)
        st.markdown("**Ad budget by phase**")
        bdf = pd.DataFrame(kit["budget"])
        st.altair_chart(alt.Chart(bdf).mark_bar(cornerRadiusEnd=6, color="#C9973A").encode(
            x=alt.X("budget:Q", title="Budget (USD)"), y=alt.Y("phase:N", sort=None, title=None), tooltip=["phase", "budget"]).properties(height=200), width="stretch")
        st.caption(f"Total ${sum(b['budget'] for b in kit['budget']):,} · target cost per lead ${kit['kpis']['target_cost_per_lead']:.2f}")

    with tabs[3]:
        bn = banners_for(kit)
        cols = st.columns([1, .62, 1.2])
        for col, (k2, img) in zip(cols, bn.items()):
            with col:
                st.image(img, caption=f"{k2.title()} · {SIZES[k2][0]}×{SIZES[k2][1]}", width="stretch")
                st.download_button(f"⬇ {k2.title()} PNG", img, file_name=f"{k2}-banner.png", mime="image/png", width="stretch", key=f"dl-{k2}")

    with tabs[4]:
        df = pd.DataFrame(kit["timeline"])
        df["due"] = pd.to_datetime(df["due"]).dt.date
        edited = st.data_editor(df, hide_index=True, width="stretch", key=f"ed-{kit['id']}",
                                column_config={"due": st.column_config.DateColumn("Due", format="MMM D, YYYY"), "task": st.column_config.TextColumn("Task", width="large"),
                                               "owner": "Owner", "category": st.column_config.SelectboxColumn("Category", options=sorted(df["category"].unique())),
                                               "done": st.column_config.CheckboxColumn("Done")}, num_rows="dynamic")
        clean = edited.dropna(subset=["task", "due"])
        new_tl = [{"task": str(r.task), "owner": "" if pd.isna(r.owner) else str(r.owner), "due": pd.Timestamp(r.due).date().isoformat(), "category": "Other" if pd.isna(r.category) else str(r.category), "done": bool(r.done) if not pd.isna(r.done) else False} for r in clean.itertuples()]
        new_tl.sort(key=lambda t: t["due"])
        if new_tl != kit["timeline"]:
            kit["timeline"] = new_tl
        if new_tl:
            ch = pd.DataFrame(new_tl)
            ch["due"] = pd.to_datetime(ch["due"])
            chart = alt.Chart(ch).mark_circle(size=180, opacity=.9).encode(
                x=alt.X("due:T", title=None), y=alt.Y("category:N", title=None),
                color=alt.Color("category:N", legend=None, scale=alt.Scale(range=["#13294B", "#C9973A", "#2457C5", "#18794E", "#6941C6", "#C2362B", "#667085"])),
                tooltip=["task", "owner", alt.Tooltip("due:T", format="%b %d, %Y")])
            rule = alt.Chart(pd.DataFrame({"d": [pd.Timestamp(date.today())]})).mark_rule(color="#C2362B", strokeDash=[4, 4]).encode(x="d:T")
            st.altair_chart((chart + rule).properties(height=260), width="stretch")
            st.caption("Red dashed line = today. Events are moved to Saturdays when possible so families can attend.")

    with tabs[5]:
        total = sum(r["openings"] for r in kit["staffing"])
        st.markdown(f"**{total} hires** for a {i['target_students']}-student campus, based on staffing ratios (1 coach per 12 athletes, 1 guide per 15 students).")
        st.dataframe(pd.DataFrame(kit["staffing"])[["title", "team", "openings"]].rename(columns={"title": "Role", "team": "Team", "openings": "Openings"}), hide_index=True, width="stretch")
        posts = []
        for r in kit["staffing"]:
            jp = job_post(kit, r)
            posts.append(jp)
            with st.expander(f"Job post: {r['title']}"):
                st.code(jp, language=None, wrap_lines=True)
        st.download_button("⬇ Download all job posts", "\n\n" + ("\n\n" + "─" * 40 + "\n\n").join(posts), file_name="job-posts.txt", width="stretch")

    with tabs[6]:
        st.markdown("Everything in one place, ready to hand off.")
        c1, c2 = st.columns(2)
        c1.download_button("📦 Full launch kit (ZIP)", bundle_zip(kit), file_name=f"launch-kit-{kit['id']}.zip", mime="application/zip", width="stretch", type="primary")
        c2.download_button("📊 Checklist, hiring and budget (Excel)", checklist_xlsx(kit), file_name="launch-checklist.xlsx", width="stretch")
        c3, c4 = st.columns(2)
        c3.download_button("📝 Launch kit (Markdown)", kit_markdown(kit), file_name="launch-kit.md", width="stretch")
        c4.download_button("💾 Save this launch (kit.json)", json.dumps(kit, indent=2), file_name="kit.json", mime="application/json", width="stretch")
        st.caption("Tip: download kit.json to keep your launch. Upload it in the sidebar anytime to continue where you left off.")


current = ss.kits.get(ss.current) if ss.current else None
if current:
    kit_view(current)
else:
    new_launch_form()
